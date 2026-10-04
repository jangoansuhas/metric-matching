#!/usr/bin/env python3
"""I1 SQL AST source-candidate sidecar for the frozen GTM evidence packet.

Only conditional_evidence_packet.json supplies decisions. The existing constraint
report is read *after* all 55 decisions are fixed, solely for reporting a
same-input comparison. No labels, built rows, or external source are read.

Dependency: sqlglot==30.20.0 (Python package, exact version). Without that
version, every pair is emitted as an abstention with explicit parse coverage.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PACKET = HERE / "conditional_evidence_packet.json"
CONSTRAINT = HERE / "constraint_aware_report.json"
JSON_REPORT = HERE / "ast_source_baseline_report.json"
MD_REPORT = HERE / "ast_source_baseline_report.md"
METHOD = "sqlglot_ast_source_i1_v1"
SQLGLOT_PIN = "30.20.0"
DIALECT = "duckdb"
PINNED_COMMIT = "a71232c123a5fb78da9b52d4246950ee48591c00"
DECISIONS = ("direct_candidate", "conditional_candidate", "scope_variant_candidate",
             "related_candidate", "abstain")
STATUSES = ("verified_from_source", "unknown", "contradicted", "not_applicable")
SQL_FIELDS = ("value_expr", "where_expr", "period_expr", "segment_expr", "group_by", "time_key")
UNKNOWN_KEYS = ("join_cardinality", "null_policy", "missing_groups", "time_zone",
                "units", "snapshot", "grouping_set_expansion")
CARD_KEYS = {"id", "metric_name", "grain", "source_ref", *SQL_FIELDS,
             "value_input_fields", "filter_input_fields", "source_location",
             "compiled_location", "review_flags", "unknown_semantics"}

try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.dialects import DuckDB
except ImportError:
    sqlglot = None
    exp = None
    DuckDB = None

PARSER_READY = sqlglot is not None and sqlglot.__version__ == SQLGLOT_PIN


@dataclass(frozen=True)
class Parsed:
    node: Any = None
    sensitive_tokens: tuple[tuple[str, str], ...] = ()
    error: str | None = None


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def validate_packet(packet: dict) -> None:
    if not isinstance(packet, dict) or set(packet) != {"schema_version", "provenance", "cards", "pairs"}:
        raise ValueError("Packet top-level schema differs")
    if packet["schema_version"] != 1 or packet["provenance"].get("commit") != PINNED_COMMIT:
        raise ValueError("Packet version or pinned commit differs")
    cards, pairs = packet["cards"], packet["pairs"]
    if not isinstance(cards, list) or len(cards) != 11 or not isinstance(pairs, list) or len(pairs) != 55:
        raise ValueError("Expected 11 cards and 55 pairs")
    ids: set[str] = set()
    for card in cards:
        if not isinstance(card, dict) or set(card) != CARD_KEYS:
            raise ValueError("Card fields differ from the I1 packet")
        if card["id"] != f"{card['metric_name']}@{card['grain']}" or card["id"] in ids:
            raise ValueError("Invalid or duplicate card ID")
        if card["grain"] not in {"month", "window"} or not isinstance(card["source_ref"], str):
            raise ValueError("Invalid grain or source reference")
        if any(card[f] is not None and not isinstance(card[f], str) for f in SQL_FIELDS):
            raise ValueError("Invalid SQL expression type")
        if any(card[f] != sorted(set(card[f])) for f in ("value_input_fields", "filter_input_fields")):
            raise ValueError("Input fields are not sorted and unique")
        if set(card["unknown_semantics"]) != set(UNKNOWN_KEYS):
            raise ValueError("Unknown semantics keys differ")
        ids.add(card["id"])
    observed: set[tuple[str, str]] = set()
    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {"left_id", "right_id"}:
            raise ValueError("Pair contains fields beyond IDs")
        a, b = pair["left_id"], pair["right_id"]
        if a == b or a not in ids or b not in ids:
            raise ValueError("Invalid pair IDs")
        observed.add(tuple(sorted((a, b))))
    if len(observed) != 55 or observed != set(itertools.combinations(sorted(ids), 2)):
        raise ValueError("Not the complete 55 unordered pairs")


def parse_field(raw: str | None, field: str) -> Parsed:
    if raw is None:
        return Parsed()  # An absent optional filter/group/time key is supported.
    if not PARSER_READY:
        found = sqlglot.__version__ if sqlglot is not None else "unavailable"
        return Parsed(error=f"Requires sqlglot=={SQLGLOT_PIN}; found {found}")
    try:
        if field == "group_by":
            statement = f"SELECT 1 GROUP BY {raw}"
        elif field == "where_expr":
            statement = f"SELECT 1 WHERE {raw}"
        else:
            statement = f"SELECT {raw}"
        statements = sqlglot.parse(statement, read=DIALECT, error_level="RAISE")
        if len(statements) != 1 or not isinstance(statements[0], exp.Select):
            raise ValueError("Not one SELECT expression")
        select = statements[0]
        if field == "group_by":
            node = select.args.get("group")
        elif field == "where_expr":
            where = select.args.get("where")
            node = where.this if where is not None else None
        else:
            node = select.expressions[0] if len(select.expressions) == 1 else None
        if node is None:
            raise ValueError("Expected expression was not parsed")
        if any(isinstance(part, exp.Anonymous) for part in node.walk()):
            raise ValueError("Unknown SQL function is outside the supported AST vocabulary")
        # SQLGlot can rewrite syntax internally (notably :: and IS NOT NULL).
        # Keep the original literal spelling/order and NULL/date operators in
        # the comparison key, as well as in the source evidence below.
        guarded = {"STRING", "NUMBER", "IS", "NOT", "NULL", "BETWEEN",
                   "GT", "GTE", "LT", "LTE"}
        tokens = DuckDB.Tokenizer().tokenize(raw)
        sensitive = tuple((t.token_type.name, t.text) for t in tokens
                          if t.token_type.name in guarded)
        return Parsed(node, sensitive)
    except (ValueError, IndexError, sqlglot.errors.SqlglotError) as exc:
        return Parsed(error=f"{type(exc).__name__}: {str(exc)[:180]}")


def same(a: Parsed, b: Parsed) -> bool:
    return (a.error is None and b.error is None and a.node == b.node
            and a.sensitive_tokens == b.sensitive_tokens)


def source(card: dict, field: str) -> dict:
    if field.startswith("unknown_semantics."):
        expression = card["unknown_semantics"][field.split(".", 1)[1]]
    else:
        expression = card[field]
    return {"card_id": card["id"], "field": field, "expression": expression,
            "source_location": card["source_location"],
            "compiled_location": card["compiled_location"]}


def condition(status: str, *items: dict, detail: str = "") -> dict:
    assert status in STATUSES
    result: dict[str, Any] = {"status": status, "source_evidence": list(items)}
    if detail:
        result["detail"] = detail
    return result


def compare(a: dict, b: dict, field: str, pa: dict, pb: dict) -> dict:
    if field in SQL_FIELDS:
        x, y = pa[field], pb[field]
        state = "unknown" if x.error or y.error else "verified_from_source" if same(x, y) else "contradicted"
        detail = "AST parsing unsupported on at least one side." if state == "unknown" else "Syntactic source comparison only; no SQL equivalence proof."
    else:
        state = "verified_from_source" if a[field] == b[field] else "contradicted"
        detail = "Source field comparison only."
    return condition(state, source(a, field), source(b, field), detail=detail)


def column_name(node: Any) -> str | None:
    if exp is None:
        return None
    if not isinstance(node, exp.Column) or node.args.get("table") or not isinstance(node.this, exp.Identifier):
        return None
    return node.this.this if not node.this.args.get("quoted") else None


def date_literal(node: Any) -> str | None:
    if exp is None:
        return None
    if not isinstance(node, exp.Cast) or not isinstance(node.to, exp.DataType):
        return None
    literal = node.this
    if node.to.this != exp.DataType.Type.DATE or not isinstance(literal, exp.Literal) or not literal.is_string:
        return None
    return literal.this


def grouping_sets(node: Any) -> tuple[tuple[str, ...], ...] | None:
    if exp is None:
        return None
    if not isinstance(node, exp.Group) or len(node.expressions) != 1:
        return None
    grouping = node.expressions[0]
    if not isinstance(grouping, exp.GroupingSets) or not grouping.expressions:
        return None
    groups: list[tuple[str, ...]] = []
    for item in grouping.expressions:
        if isinstance(item, exp.Tuple):
            members = item.expressions
        elif isinstance(item, exp.Paren):
            members = [item.this]
        else:
            return None
        names = tuple(column_name(member) for member in members)
        if None in names or len(names) != len(set(names)):
            return None
        groups.append(names)
    if len(groups) != len(set(groups)):
        return None
    return tuple(groups)


def group_reduction(month: dict, window: dict, pm: dict, pw: dict) -> bool:
    key = column_name(pm["time_key"].node)
    mg = grouping_sets(pm["group_by"].node)
    wg = grouping_sets(pw["group_by"].node)
    if key is None or mg is None or wg is None or not all(key in group for group in mg):
        return False
    removed = tuple(tuple(item for item in group if item != key) for group in mg)
    return len(removed) == len(set(removed)) and sorted(removed) == sorted(wg)


def bounds_on_key(filter_node: Any, key: str) -> tuple[str, str] | None:
    if exp is None:
        return None
    # AND is deliberately not commuted or simplified. This merely locates one
    # visible literal BETWEEN; other predicates remain part of the exact AST.
    terms = [filter_node]
    between = []
    while terms:
        item = terms.pop()
        if isinstance(item, exp.And):
            terms.extend((item.this, item.expression))
        elif isinstance(item, exp.Between) and column_name(item.this) == key:
            low, high = date_literal(item.args.get("low")), date_literal(item.args.get("high"))
            if low is None or high is None:
                return None
            between.append((low, high))
    return between[0] if len(between) == 1 else None


def measure_shape(node: Any) -> dict[str, Any]:
    if node is None:
        return {"family": "parse_unsupported", "additive": False}
    rounding = None
    cast = None
    core = node
    if isinstance(core, exp.Round):
        precision = core.args.get("decimals")
        if not isinstance(precision, exp.Literal) or precision.is_string or not precision.this.isdigit():
            return {"family": "unsupported_round", "additive": False}
        rounding = int(precision.this)
        core = core.this
    if isinstance(core, exp.Cast):
        cast = core.to.sql(dialect=DIALECT)
        core = core.this
    if isinstance(core, exp.Count) and isinstance(core.this, exp.Star) and rounding is None:
        return {"family": "count", "additive": True, "core": "COUNT(*)",
                "rounding": rounding, "cast": cast}
    if isinstance(core, exp.Sum) and column_name(core.this) is not None and cast is None:
        return {"family": "sum", "additive": True,
                "core": f"SUM({column_name(core.this)})", "rounding": rounding, "cast": cast}
    if isinstance(node, exp.Column):
        family = "field"
    elif node.find(exp.PercentileCont) or node.find(exp.PercentileDisc):
        family = "percentile"
    elif node.find(exp.Avg):
        family = "avg"
    elif node.find(exp.Div):
        family = "ratio"
    else:
        family = "unsupported_value_shape"
    return {"family": family, "additive": False}


def stage_literal(node: Any) -> str | None:
    if exp is None:
        return None
    if not isinstance(node, exp.EQ) or column_name(node.this) != "stage":
        return None
    literal = node.expression
    return literal.this if isinstance(literal, exp.Literal) and literal.is_string else None


def decide(a: dict, b: dict, pa: dict, pb: dict) -> dict:
    c = {name: compare(a, b, field, pa, pb) for name, field in (
        ("source_relation", "source_ref"), ("value_projection", "value_expr"),
        ("value_input_fields", "value_input_fields"),
        ("filter_predicate", "where_expr"), ("filter_input_fields", "filter_input_fields"),
        ("segment_projection", "segment_expr"), ("grain", "grain"),
        ("period_projection", "period_expr"), ("grouping_projection", "group_by"),
        ("time_key", "time_key"))}
    c["upstream_field_lineage"] = condition(
        "unknown", source(a, "review_flags"), source(b, "review_flags"),
        detail="Input field names do not verify upstream field identity.")
    for key in UNKNOWN_KEYS:
        x, y = a["unknown_semantics"][key], b["unknown_semantics"][key]
        state = "unknown" if x is None or y is None else "verified_from_source" if x == y else "contradicted"
        c[key] = condition(state, source(a, "unknown_semantics." + key),
                           source(b, "unknown_semantics." + key),
                           detail="Not independently source verified." if state == "unknown" else "")

    parse_errors = [(card["id"], field, parsed[field].error)
                    for card, parsed in ((a, pa), (b, pb)) for field in SQL_FIELDS
                    if parsed[field].error]
    cross = {a["grain"], b["grain"]} == {"month", "window"}
    month, window, pm, pw = (a, b, pa, pb) if a["grain"] == "month" else (b, a, pb, pa)
    ma, mb = measure_shape(pa["value_expr"].node), measure_shape(pb["value_expr"].node)
    mm, mw = measure_shape(pm["value_expr"].node), measure_shape(pw["value_expr"].node)
    same_source = c["source_relation"]["status"] == "verified_from_source"
    same_value = c["value_projection"]["status"] == "verified_from_source"
    same_filter = c["filter_predicate"]["status"] == "verified_from_source"
    same_segment = c["segment_projection"]["status"] == "verified_from_source"
    same_inputs = all(c[k]["status"] == "verified_from_source"
                      for k in ("value_input_fields", "filter_input_fields"))
    same_period = c["period_projection"]["status"] == "verified_from_source"
    same_group = c["grouping_projection"]["status"] == "verified_from_source"
    same_key = c["time_key"]["status"] == "verified_from_source"
    key = column_name(pm["time_key"].node) if cross else None
    period_shape = bool(cross and key and column_name(pm["period_expr"].node) == key
                        and date_literal(pw["period_expr"].node) is not None
                        and (window["time_key"] is None or
                             same(pw["time_key"], pm["time_key"])))
    groups_reduce = cross and group_reduction(month, window, pm, pw)
    bounds = bounds_on_key(pw["where_expr"].node, key) if key else None
    matched_bounds = bool(bounds and same_filter and
                          bounds_on_key(pm["where_expr"].node, key) == bounds)

    if cross:
        c["grain"] = condition("verified_from_source", source(a, "grain"), source(b, "grain"),
                               detail="Month to window is a proposed aggregation, not identical grain.")
        c["time_partition"] = condition(
            "verified_from_source" if period_shape and matched_bounds else "unknown",
            source(month, "period_expr"), source(window, "period_expr"),
            source(month, "time_key"), source(window, "where_expr"),
            detail="Matching month key and literal window BETWEEN are visible; coverage is unknown."
            if matched_bounds else "A period label alone does not bound the window population.")
        c["grouping_reduction"] = condition(
            "verified_from_source" if groups_reduce else "unknown",
            source(month, "group_by"), source(window, "group_by"),
            detail="Removing the month key matches the grouping-set shapes; emitted rows are unverified."
            if groups_reduce else "No supported grouping-set reduction.")
        c["window_time_filter"] = condition(
            "verified_from_source" if matched_bounds else "unknown",
            source(window, "where_expr"), source(window, "time_key"),
            detail="Literal BETWEEN on the month key is present on both sides."
            if matched_bounds else "No matching explicit literal date bound verified.")
        c["window_time_key_alignment"] = condition(
            "verified_from_source" if key and window["time_key"] is not None and
            same(pw["time_key"], pm["time_key"]) else "unknown",
            source(month, "time_key"), source(window, "time_key"),
            detail="A missing window time key leaves alignment unverified.")
        c["partition_coverage"] = condition(
            "unknown", source(month, "time_key"), source(window, "where_expr"),
            detail="Complete disjoint month partitions and row coverage are not established.")
        c["zero_fill_absent_month_groups"] = condition(
            "unknown", source(month, "group_by"), source(window, "group_by"),
            detail="Missing month/segment rows need explicit zero fill for a complete comparison.")
        c["segment_all_collision"] = condition(
            "unknown", source(month, "segment_expr"), source(window, "segment_expr"),
            detail="COALESCE(segment, 'All') can collide with a real 'All' segment or the total label.")
        c["rounding"] = condition(
            "unknown" if any(shape.get("rounding") is not None or shape.get("cast")
                             for shape in (mm, mw)) else "not_applicable",
            source(month, "value_expr"), source(window, "value_expr"),
            detail="Sum unrounded cores and round once; displayed rounded month values or a DOUBLE cast need review.")
    else:
        for k in ("time_partition", "grouping_reduction", "window_time_filter",
                  "window_time_key_alignment", "partition_coverage",
                  "zero_fill_absent_month_groups", "segment_all_collision", "rounding"):
            c[k] = condition("not_applicable")
    c["period_boundaries"] = condition(
        "unknown", source(a, "period_expr"), source(b, "period_expr"),
        detail="Source syntax does not establish full inclusive boundary semantics.")
    c["source_membership"] = condition(
        "unknown", source(a, "source_ref"), source(b, "source_ref"),
        detail="A shared source name does not establish identical upstream populations.")

    if parse_errors:
        decision, status = "abstain", "needs_review"
        reasons = ["Required SQL AST parsing unsupported: " + "; ".join(
            f"{id_}.{field}: {error}" for id_, field, error in parse_errors)]
    elif (not cross and a["grain"] == b["grain"] and same_source and same_value
          and same_filter and same_segment and same_inputs and same_period and
          same_group and same_key):
        decision, status = "direct_candidate", "sufficient_for_source_candidate"
        reasons = ["The visible ASTs, source, field inputs, period, grain, and grouping agree.",
                   "This is a source candidate only; runtime semantics remain unknown."]
    elif (cross and same_source and same_value and same_filter and same_segment
          and same_inputs and period_shape and groups_reduce and ma["additive"]
          and mb["additive"] and ma["core"] == mb["core"]):
        decision, status = "conditional_candidate", "needs_review"
        reasons = [
            f"Additive core {ma['core']} permits a proposed month-to-window sum over separate grouping sets; sum unrounded cores and apply any outer ROUND once.",
            "Zero fill absent month groups; verify NULL versus zero, source membership, partition coverage, period bounds, grouping expansion, units, snapshot, and join cardinality.",
            "This is conditional source evidence, not a SQL equivalence proof or a claim about built rows.",
        ]
        if not matched_bounds:
            reasons.append("The window has no verified literal date bound on the month key; its period label is not a row filter.")
        if c["rounding"]["status"] == "unknown":
            reasons.append("Rounding or DOUBLE cast can prevent equality of published monthly sums and the window value.")
    elif (not cross and a["grain"] == b["grain"] and same_source and same_value
          and same_segment and same_inputs and same_period and same_group and same_key
          and not same_filter):
        x, y = stage_literal(pa["where_expr"].node), stage_literal(pb["where_expr"].node)
        if x is not None and y is not None and x != y and ma["family"] == "field" and "stage" in a["filter_input_fields"]:
            decision = "related_candidate"
            reasons = ["The same source field is selected by different stage literals; these are related steps, not interchangeable populations.",
                       "The filter prerequisite is contradicted; no value or row equivalence follows."]
        else:
            decision = "scope_variant_candidate"
            reasons = ["Visible value and source agree, but the filter AST differs; review the scope difference."]
        status = "needs_review"
    else:
        decision, status = "abstain", "needs_review"
        reasons = []
        if not same_source:
            reasons.append("Source relations differ; common membership is unverified.")
        if not same_value:
            reasons.append("Value ASTs or literal tokens differ; no value transformation is established.")
        if not same_filter:
            reasons.append("Filter ASTs or sensitive tokens differ; scopes cannot be equated.")
        if cross and (not ma["additive"] or not mb["additive"]):
            reasons.append("A nonadditive or opaque value shape cannot be summed across month outputs.")
        if cross and (not period_shape or not groups_reduce):
            reasons.append("The month partition or grouping-set reduction is unsupported.")
        if not same_inputs:
            reasons.append("Input field lists differ; deeper lineage remains unknown.")
        if not reasons:
            reasons.append("No supported direct or conditional source relationship is established.")

    return {"left_id": a["id"], "right_id": b["id"], "decision": decision,
            "evidence_status": status, "conditions": c, "reasons": reasons,
            "locations": {
                "left": {"source": a["source_location"], "compiled": a["compiled_location"],
                         "review_flags": a["review_flags"]},
                "right": {"source": b["source_location"], "compiled": b["compiled_location"],
                          "review_flags": b["review_flags"]}}}


def compare_constraint(results: list[dict], input_sha: str) -> dict:
    # This function runs only after results have been computed. It cannot
    # affect candidate rules, AST parsing, or any per-pair condition.
    previous = json.loads(CONSTRAINT.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if previous["input_sha256"] != input_sha:
        raise ValueError("Constraint baseline did not read the same packet bytes")
    old = previous["results"]
    if [(r["left_id"], r["right_id"]) for r in old] != [
        (r["left_id"], r["right_id"]) for r in results]:
        raise ValueError("Constraint baseline does not cover the same ordered 55 pairs")
    disagreements = [{"left_id": r["left_id"], "right_id": r["right_id"],
                      "ast_decision": r["decision"], "constraint_decision": x["decision"]}
                     for r, x in zip(results, old) if r["decision"] != x["decision"]]
    return {"method": previous["method"], "input_sha256": previous["input_sha256"],
            "by_decision": previous["counts"]["by_decision"],
            "agreement": len(results) - len(disagreements), "disagreements": disagreements}


def run(packet: dict, sha: str) -> dict:
    validate_packet(packet)
    cards = {card["id"]: card for card in packet["cards"]}
    parsed = {id_: {field: parse_field(card[field], field) for field in SQL_FIELDS}
              for id_, card in cards.items()}
    results = [decide(cards[p["left_id"]], cards[p["right_id"]],
                      parsed[p["left_id"]], parsed[p["right_id"]]) for p in packet["pairs"]]
    if len(results) != 55 or any(r["decision"] not in DECISIONS or
        any(c["status"] not in STATUSES for c in r["conditions"].values()) for r in results):
        raise AssertionError("Invalid 55-pair result")
    counts = Counter(r["decision"] for r in results)
    evidences = Counter(r["evidence_status"] for r in results)
    coverage = {}
    unsupported = []
    for field in SQL_FIELDS:
        populated = [(card["id"], parsed[card["id"]][field]) for card in packet["cards"]
                     if card[field] is not None]
        errors = [(id_, value.error) for id_, value in populated if value.error]
        coverage[field] = {"non_null": len(populated), "parsed": len(populated) - len(errors),
                           "unsupported": len(errors), "absent": len(cards) - len(populated)}
        unsupported.extend({"card_id": id_, "field": field, "reason": error} for id_, error in errors)
    shapes = Counter(measure_shape(parsed[id_]["value_expr"].node)["family"] for id_ in cards)
    output = {
        "method": METHOD, "input_sha256": sha, "dependency": {
            "package": "sqlglot", "exact_pin": f"sqlglot=={SQLGLOT_PIN}",
            "installed_version": sqlglot.__version__ if sqlglot is not None else None,
            "available_at_exact_pin": PARSER_READY, "dialect": DIALECT},
        "parser_coverage": {"by_field": coverage, "unsupported_count": len(unsupported),
                            "unsupported": unsupported, "value_shapes": dict(sorted(shapes.items()))},
        "results": results,
        "counts": {"total": len(results), "by_decision": {k: counts[k] for k in DECISIONS},
                   "by_evidence_status": {k: evidences[k] for k in
                                          ("sufficient_for_source_candidate", "needs_review")}},
    }
    output["constraint_baseline_comparison"] = compare_constraint(results, sha)
    return output


def markdown(report: dict) -> str:
    cov = report["parser_coverage"]
    comp = report["constraint_baseline_comparison"]
    counts = report["counts"]["by_decision"]
    old = comp["by_decision"]
    lines = [
        "# I1 SQL AST source baseline — GTM development packet", "",
        f"Method: `{METHOD}`. Same packet bytes: SHA-256 `{report['input_sha256']}`. "
        "The packet has 11 cards and all 55 unordered pairs; outcomes are source candidates or abstentions.",
        "",
        "## Dependency and parser coverage", "",
        f"Exact dependency: `sqlglot=={SQLGLOT_PIN}`; DuckDB parser. "
        f"Installed version: `{report['dependency']['installed_version'] or 'unavailable'}`. "
        "Install with `python -m pip install 'sqlglot==30.20.0'`. "
        "A missing or different version makes all 55 outputs abstentions.",
        "", "| Packet expression field | Non-null | AST parsed | Unsupported | Absent |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for field, x in cov["by_field"].items():
        lines.append(f"| `{field}` | {x['non_null']} | {x['parsed']} | {x['unsupported']} | {x['absent']} |")
    lines += ["", f"Parser unsupported occurrences: **{cov['unsupported_count']}**. "
              "Absent optional fields are tracked separately and are not parser failures.", ""]
    if cov["unsupported"]:
        lines += ["Unsupported card fields:", ""]
        lines += [f"- `{x['card_id']}` `{x['field']}`: {x['reason']}" for x in cov["unsupported"]]
        lines.append("")
    lines += [
        "Parsed value shapes: " + ", ".join(f"`{k}` {v}" for k, v in cov["value_shapes"].items()) + ".",
        "The percentile, AVG, and ratio shapes parse but do not qualify for additive rollup. "
        "A field projection alone is also not an additive aggregate.", "",
        "## Same-input comparison with the existing constraint baseline", "",
        "| Decision | SQL AST I1 | Constraint-aware I1 |", "| --- | ---: | ---: |",
    ]
    lines += [f"| `{k}` | {counts[k]} | {old.get(k, 0)} |" for k in DECISIONS]
    lines += ["", f"Decision agreement: {comp['agreement']}/55. "
              f"Decision disagreements: {len(comp['disagreements'])}.", ""]
    if comp["disagreements"]:
        lines += ["| Left | Right | AST | Constraint |", "| --- | --- | --- | --- |"]
        lines += [f"| `{r['left_id']}` | `{r['right_id']}` | `{r['ast_decision']}` | `{r['constraint_decision']}` |"
                  for r in comp["disagreements"]]
        lines.append("")
    else:
        lines += ["There is no demonstrated incremental candidate gain over the constraint baseline.", ""]
    lines += [
        "## Decision scope and limits", "",
        "The parser reads compiled value, filter, period, segment, grouping, and optional time-key "
        "expressions from the same packet used by the other I1 methods. It retains the original "
        "expression and source/compiled locations in every pair's evidence. AST comparison keeps "
        "string and numeric literal tokens in order, plus NULL and inequality/date-bound operators. "
        "SQLGlot interprets DuckDB casts (`::`), `IS NOT NULL`, and grouping parentheses; "
        "the method does not commute predicates, change stage literals or dates, or prove SQL equivalence.",
        "",
        "A cross-grain candidate requires identical source, value AST, filter AST, segment AST, "
        "input fields, a month period key, a constant date window label, and grouping sets that "
        "reduce after removing that key. Only `COUNT(*)` and a simple `SUM(column)` core are "
        "treated as additive. Literal `BETWEEN` bounds are evidence of syntax, not coverage. "
        "A rounded `SUM` requires aggregation of unrounded cores followed by one final rounding; "
        "a `DOUBLE` cast leaves numeric equality open.",
        "",
        "Visible stage equalities with different case-sensitive string literals may be related "
        "candidates, with a contradicted filter prerequisite. Neither stage populations nor "
        "upstream field lineage are established by the packet. Unknown join cardinality, NULL "
        "policy, missing groups and zero fill, time zone, units, snapshot, grouping expansion, "
        "period coverage, and source membership remain explicit conditions. Source candidates "
        "are not verified equivalences, accuracy results, or built-row reconciliations.", "",
        "## Reproduction", "",
        "From the workspace root: `python metric_matching_pilot/ast_source_baseline.py` writes only "
        "the two sidecar reports. `python metric_matching_pilot/ast_source_baseline.py --check` "
        "reads the packet and existing reports, validates exact output bytes, and writes nothing.", "",
    ]
    return "\n".join(lines)


def self_check() -> None:
    if not PARSER_READY:
        return
    def different(a: str, b: str, field: str) -> None:
        assert not same(parse_field(a, field), parse_field(b, field)), (a, b)
    different("stage = 'SAL'", "stage = 'SQL'", "where_expr")
    different("stage = 'SAL'", "stage = 'sal'", "where_expr")
    different("x IS NULL", "x IS NOT NULL", "where_expr")
    different("x BETWEEN DATE '2025-01-01' AND DATE '2025-01-31'",
              "x BETWEEN DATE '2025-01-01' AND DATE '2025-02-01'", "where_expr")
    different("x >= 7", "x > 7", "where_expr")
    different("ROUND(SUM(x), 2)", "ROUND(SUM(x), 4)", "value_expr")
    assert measure_shape(parse_field("AVG(x)", "value_expr").node)["additive"] is False
    assert measure_shape(parse_field("SUM(x)", "value_expr").node)["additive"] is True
    assert grouping_sets(parse_field("grouping sets ((month_key, segment), (month_key))", "group_by").node)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only self-check and byte comparison")
    args = parser.parse_args()
    raw = PACKET.read_bytes()
    packet = json.loads(raw, object_pairs_hook=unique_object)
    report = run(packet, hashlib.sha256(raw).hexdigest())
    json_bytes = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    md_bytes = markdown(report).encode("utf-8")
    if args.check:
        self_check()
        for path, expected in ((JSON_REPORT, json_bytes), (MD_REPORT, md_bytes)):
            if not path.exists() or path.read_bytes() != expected:
                raise SystemExit(f"Missing or stale report: {path}")
        print("Read-only check passed: 55 pairs, parser guards, exact report bytes.")
    else:
        JSON_REPORT.write_bytes(json_bytes)
        MD_REPORT.write_bytes(md_bytes)
        print(f"Wrote {JSON_REPORT.name} and {MD_REPORT.name}: {report['counts']['by_decision']}")


if __name__ == "__main__":
    main()
