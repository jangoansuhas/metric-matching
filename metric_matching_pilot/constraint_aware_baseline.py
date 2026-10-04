#!/usr/bin/env python3
"""Conservative, full-context source candidates from a shared evidence packet.

The input is the *only* project evidence used by this method.  In particular,
neither labels nor built rows are read.  A candidate describes a source-level
relationship to review; it never asserts that observed metric values are equal.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PACKET = HERE / "conditional_evidence_packet.json"
JSON_REPORT = HERE / "constraint_aware_report.json"
MD_REPORT = HERE / "constraint_aware_report.md"
METHOD = "constraint_aware_full_context_v2"
PINNED_COMMIT = "a71232c123a5fb78da9b52d4246950ee48591c00"
DECISIONS = (
    "direct_candidate", "conditional_candidate", "scope_variant_candidate",
    "related_candidate", "abstain",
)
STATUSES = ("verified_from_source", "unknown", "contradicted", "not_applicable")
UNKNOWN_KEYS = (
    "join_cardinality", "null_policy", "missing_groups", "time_zone",
    "units", "snapshot", "grouping_set_expansion",
)
CARD_KEYS = (
    "id", "metric_name", "grain", "source_ref", "value_expr", "where_expr",
    "period_expr", "segment_expr", "group_by", "time_key",
    "value_input_fields", "filter_input_fields", "source_location",
    "compiled_location", "review_flags", "unknown_semantics",
)


def sql_text(value: Any) -> str:
    """Collapse whitespace and case outside single-quoted SQL literals only."""
    if value is None:
        return ""
    s = str(value).strip()
    out: list[str] = []
    in_quote = False
    pending_space = False
    i = 0
    while i < len(s):
        char = s[i]
        if char == "'":
            if pending_space and out:
                out.append(" ")
            pending_space = False
            out.append(char)
            if in_quote and i + 1 < len(s) and s[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            in_quote = not in_quote
        elif in_quote:
            out.append(char)
        elif char.isspace():
            pending_space = True
        else:
            if pending_space and out:
                out.append(" ")
            pending_space = False
            out.append(char.lower())
        i += 1
    return "".join(out)


def split_top_level(s: str) -> list[str] | None:
    """Split a small SQL argument/grouping list; reject unbalanced syntax."""
    parts: list[str] = []
    depth = 0
    in_quote = False
    start = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "'":
            if in_quote and i + 1 < len(s) and s[i + 1] == "'":
                i += 2
                continue
            in_quote = not in_quote
        elif not in_quote:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth < 0:
                    return None
            elif c == "," and depth == 0:
                parts.append(s[start:i].strip())
                start = i + 1
        i += 1
    if depth != 0 or in_quote:
        return None
    parts.append(s[start:].strip())
    return parts


def call(s: str) -> tuple[str, list[str]] | None:
    match = re.fullmatch(r"([a-z_][\w]*)\s*\((.*)\)", s, re.DOTALL)
    if not match:
        return None
    args = split_top_level(match.group(2))
    return (match.group(1), args) if args is not None else None


def measure(expr: str) -> dict[str, Any]:
    """Whitelist additive SQL aggregates; all other families cannot be summed."""
    s = sql_text(expr)
    rounding = None
    outer = call(s)
    if outer and outer[0] == "round":
        if len(outer[1]) != 2 or not re.fullmatch(r"-?\d+", outer[1][1]):
            return {"family": "unsupported", "additive": False, "rounding": None}
        rounding = int(outer[1][1])
        s = outer[1][0]
    cast = re.search(r"::\s*(double(?: precision)?|real|float\d*|numeric|decimal)$", s)
    if cast:
        s = s[:cast.start()].strip()
    inner = call(s)
    if inner and len(inner[1]) == 1:
        name, (arg,) = inner
        if name == "count" and (
            arg == "*" or re.fullmatch(r"[a-z_][\w]*(?:\.[a-z_][\w]*)?", arg)
        ):
            return {"family": "count", "additive": True, "core": arg,
                    "rounding": rounding, "cast": cast.group(1) if cast else None}
        if name == "sum" and re.fullmatch(r"[a-z_][\w]*(?:\.[a-z_][\w]*)?", arg):
            return {"family": "sum", "additive": True, "core": arg,
                    "rounding": rounding, "cast": cast.group(1) if cast else None}
        if name in {"avg", "median", "percentile_cont", "percentile_disc"}:
            return {"family": "median" if name.startswith("percentile_") else name,
                    "additive": False, "rounding": rounding}
    if re.search(r"\b(percentile_cont|percentile_disc|median)\s*\(", s):
        family = "median"
    elif re.search(r"\bavg\s*\(", s):
        family = "avg"
    elif "/" in s:
        family = "ratio"
    elif re.fullmatch(r"[a-z_][\w]*(?:\.[a-z_][\w]*)?", s):
        family = "field"
    else:
        family = "unsupported"
    return {"family": family, "additive": False, "rounding": rounding}


def grouping_sets(expr: Any) -> list[tuple[str, ...]] | None:
    s = sql_text(expr)
    match = re.fullmatch(r"grouping\s+sets\s*\((.*)\)", s, re.DOTALL)
    if not match:
        return None
    pieces = split_top_level(match.group(1))
    if not pieces:
        return None
    groups = []
    for piece in pieces:
        if not (piece.startswith("(") and piece.endswith(")")):
            return None
        members = split_top_level(piece[1:-1])
        if members is None or any(not x for x in members if piece[1:-1].strip()):
            return None
        group = tuple(sql_text(x) for x in members if x)
        if len(group) != len(set(group)):
            return None
        groups.append(group)
    return groups if len(groups) == len(set(groups)) else None


def rollup_grouping(month: dict, window: dict) -> bool:
    key = sql_text(month["time_key"])
    groups_m = grouping_sets(month["group_by"])
    groups_w = grouping_sets(window["group_by"])
    if not key or not groups_m or not groups_w or not all(key in g for g in groups_m):
        return False
    remainder = [tuple(x for x in g if x != key) for g in groups_m]
    return sorted(remainder) == sorted(groups_w) and len(remainder) == len(set(remainder))


def constant_period(expr: Any) -> bool:
    s = sql_text(expr)
    return bool(
        re.fullmatch(r"cast\s*\(\s*'[^']+'\s+as\s+date\s*\)", s)
        or re.fullmatch(r"date\s*'[^']+'", s)
        or re.fullmatch(r"'[^']+'\s*::\s*date", s)
        or re.fullmatch(r"\{\{\s*window_start\s*\}\}", s)
    )


def explicit_window_time_filter(month: dict, window: dict) -> bool:
    """Recognize only a literal BETWEEN on the same month partition key."""
    key = sql_text(month["time_key"])
    if not key or sql_text(window["time_key"]) != key:
        return False
    date = r"(?:cast\s*\(\s*'[^']+'\s+as\s+date\s*\)|date\s*'[^']+'|'[^']+'\s*::\s*date)"
    return bool(re.search(rf"\b{re.escape(key)}\s+between\s+{date}\s+and\s+{date}(?=\s|$|\))",
                          sql_text(window["where_expr"])))


def stage_literal(predicate: Any) -> str | None:
    """A source-declared stage equality, without claiming stage populations overlap."""
    match = re.fullmatch(r"(?:[a-z_][\w]*\.)?stage\s*=\s*'((?:''|[^'])*)'",
                         sql_text(predicate))
    return match.group(1) if match else None


def evidence(card: dict, field: str, value: Any = None) -> dict:
    return {
        "card_id": card["id"],
        "source_location": card["source_location"],
        "compiled_location": card["compiled_location"],
        "field": field,
        "expression": card.get(field) if value is None else value,
    }


def condition(status: str, *items: dict, detail: str = "") -> dict:
    assert status in STATUSES
    result: dict[str, Any] = {"status": status, "source_evidence": list(items)}
    if detail:
        result["detail"] = detail
    return result


def eq_condition(a: dict, b: dict, field: str, *, sql: bool = True) -> dict:
    left, right = a.get(field), b.get(field)
    status = "verified_from_source" if (
        sql_text(left) == sql_text(right) if sql else left == right
    ) else "contradicted"
    return condition(status, evidence(a, field), evidence(b, field),
                     detail="Visible expressions agree." if status == "verified_from_source"
                     else "Visible expressions differ; no predicate or value equivalence is inferred.")


def unknown_condition(a: dict, b: dict, key: str) -> dict:
    left = a["unknown_semantics"][key]
    right = b["unknown_semantics"][key]
    ev = (evidence(a, "unknown_semantics." + key, left),
          evidence(b, "unknown_semantics." + key, right))
    if left is None or right is None:
        return condition("unknown", *ev, detail="No independent source verification for both sides.")
    if left == right:
        return condition("verified_from_source", *ev)
    return condition("contradicted", *ev, detail="Source-verified semantics differ.")


def decide(left: dict, right: dict) -> dict:
    a, b = left, right
    ma, mb = measure(a["value_expr"]), measure(b["value_expr"])
    cross_grain = {a["grain"], b["grain"]} == {"month", "window"}
    month, window = (a, b) if a["grain"] == "month" else (b, a)
    same_source = bool(a["source_ref"]) and a["source_ref"] == b["source_ref"]
    same_value = sql_text(a["value_expr"]) == sql_text(b["value_expr"])
    same_filter = sql_text(a["where_expr"]) == sql_text(b["where_expr"])
    same_segment = sql_text(a["segment_expr"]) == sql_text(b["segment_expr"])
    same_value_fields = a["value_input_fields"] == b["value_input_fields"]
    same_filter_fields = a["filter_input_fields"] == b["filter_input_fields"]
    same_period = sql_text(a["period_expr"]) == sql_text(b["period_expr"])
    same_group = sql_text(a["group_by"]) == sql_text(b["group_by"])
    same_time_key = sql_text(a["time_key"]) == sql_text(b["time_key"])
    time_shape = (cross_grain and sql_text(month["period_expr"]) == sql_text(month["time_key"])
                  and bool(month["time_key"]) and constant_period(window["period_expr"])
                  and (not window["time_key"] or
                       sql_text(window["time_key"]) == sql_text(month["time_key"])))
    bounded_window = bool(cross_grain and explicit_window_time_filter(month, window))
    group_shape = cross_grain and rollup_grouping(month, window)

    conditions = {
        "source_relation": eq_condition(a, b, "source_ref", sql=False),
        "value_family": condition(
            "verified_from_source" if ma["family"] == mb["family"] and ma["family"] != "unsupported"
            else "unknown" if "unsupported" in {ma["family"], mb["family"]}
            else "contradicted",
            evidence(a, "value_expr", ma["family"]), evidence(b, "value_expr", mb["family"]),
            detail="Only COUNT and simple SUM are accepted as additive for rollup."),
        "value_projection": eq_condition(a, b, "value_expr"),
        "value_input_fields": eq_condition(a, b, "value_input_fields", sql=False),
        "filter_predicate": eq_condition(a, b, "where_expr"),
        "filter_input_fields": eq_condition(a, b, "filter_input_fields", sql=False),
        "upstream_field_lineage": condition(
            "unknown", evidence(a, "review_flags"), evidence(b, "review_flags"),
            detail="Matching input field names do not prove matching upstream derivations; the packet does not supply a verified deep-lineage identity."),
        "segment_projection": eq_condition(a, b, "segment_expr"),
        "grain": condition(
            "verified_from_source" if a["grain"] == b["grain"] or cross_grain else "contradicted",
            evidence(a, "grain"), evidence(b, "grain"),
            detail="Month to window is a proposed aggregation, not an identical grain."
            if cross_grain else ""),
        "time_partition": condition(
            "verified_from_source" if (time_shape and bounded_window) or
            (not cross_grain and same_period and same_time_key)
            else "unknown" if cross_grain else "contradicted",
            evidence(a, "period_expr"), evidence(b, "period_expr"),
            evidence(month, "time_key") if cross_grain else evidence(a, "time_key"),
            detail="The month key and explicit window time filter align syntactically; full partition coverage remains unverified."
            if bounded_window else
            "A constant window label does not bound source rows; the window time filter/key is absent or unsupported."
            if cross_grain else ""),
        "grouping_projection": condition(
            "verified_from_source" if group_shape or (not cross_grain and same_group)
            else "unknown" if cross_grain else "contradicted",
            evidence(a, "group_by"), evidence(b, "group_by"),
            detail="Removing the month key yields the window grouping sets; row expansion is unverified."
            if group_shape else ""),
    }
    for key in UNKNOWN_KEYS:
        conditions[key] = unknown_condition(a, b, key)

    if cross_grain:
        conditions["partition_coverage"] = condition(
            "unknown", evidence(month, "time_key"), evidence(window, "period_expr"),
            detail="Every contributing month must cover the same window rows and boundaries.")
        conditions["period_boundaries"] = condition(
            "unknown", evidence(month, "where_expr"), evidence(window, "where_expr"),
            detail="A constant window label does not establish inclusive bounds or month coverage.")
        conditions["zero_fill_absent_month_groups"] = condition(
            "unknown", evidence(month, "group_by"), evidence(window, "group_by"),
            detail="Zero-fill absent month/segment keys before comparing a complete rollup; do not infer missing rows are zero from the packet.")
        collision = "coalesce(" in sql_text(month["segment_expr"]) and "'All'" in month["segment_expr"]
        conditions["segment_all_collision"] = condition(
            "unknown" if collision else "not_applicable",
            evidence(month, "segment_expr"), evidence(window, "segment_expr"),
            detail="A real segment named 'All' or NULL could collide with the grand-total display label."
            if collision else "")
        conditions["window_time_key_alignment"] = condition(
            "verified_from_source" if window["time_key"] and
            sql_text(window["time_key"]) == sql_text(month["time_key"]) else "unknown",
            evidence(month, "time_key"), evidence(window, "time_key"),
            detail="No explicit window time key is supplied; membership and coverage need review."
            if not window["time_key"] else "")
        conditions["window_time_filter"] = condition(
            "verified_from_source" if bounded_window else "unknown",
            evidence(window, "where_expr"), evidence(window, "time_key"),
            detail="A literal date BETWEEN on the matching time key is visible; actual membership remains unverified."
            if bounded_window else
            "No source-supported date bound on the matching window time key; the period label is not a row filter.")
        conditions["source_membership"] = condition(
            "unknown", evidence(a, "source_ref"), evidence(b, "source_ref"),
            detail="The same source and visible predicate do not prove full partition coverage or upstream row membership.")
        conditions["rounding"] = condition(
            "unknown" if ma.get("rounding") is not None or ma.get("cast") else "not_applicable",
            evidence(month, "value_expr"), evidence(window, "value_expr"),
            detail="Sum unrounded monthly aggregates and round once; summing displayed rounded values is unverified."
            if ma.get("rounding") is not None else
            "A floating-point cast can affect exact numeric equality." if ma.get("cast") else "")
    else:
        for key in ("partition_coverage", "zero_fill_absent_month_groups", "segment_all_collision",
                    "window_time_key_alignment", "window_time_filter"):
            conditions[key] = condition("not_applicable")
        conditions["period_boundaries"] = condition(
            "unknown", evidence(a, "period_expr"), evidence(b, "period_expr"),
            detail="Matching labels alone do not establish time-boundary semantics.")
        conditions["source_membership"] = condition(
            "unknown", evidence(a, "source_ref"), evidence(b, "source_ref"),
            detail="Source identity and predicate syntax alone do not verify upstream row membership.")
        conditions["rounding"] = condition("not_applicable", detail="No rollup of rounded outputs is proposed.")

    reasons: list[str]
    if (not cross_grain and a["grain"] == b["grain"] and same_source and same_value
            and same_filter and same_segment and same_value_fields and same_filter_fields
            and same_period and same_group and same_time_key):
        decision = "direct_candidate"
        status = "sufficient_for_source_candidate"
        reasons = ["Visible source, value, predicate, field inputs, time, grain, and grouping agree.",
                   "This is a source candidate only; unknown runtime semantics still require review."]
    elif (cross_grain and same_source and same_value and same_filter and same_segment
          and same_value_fields and same_filter_fields and time_shape and group_shape
          and ma["additive"] and mb["additive"] and ma["family"] == mb["family"]
          and ma.get("core") == mb.get("core")):
        decision = "conditional_candidate"
        status = ("sufficient_for_source_candidate" if bounded_window and
                  conditions["rounding"]["status"] == "not_applicable" else "needs_review")
        core = "COUNT(" + ma["core"] + ")" if ma["family"] == "count" else "SUM(" + ma["core"] + ")"
        if ma["rounding"] is not None:
            transformation = (f"Source-supported additive core {core}: sum unrounded month-level "
                              f"{core} for each separate segment/grand-total grouping set, then "
                              f"ROUND once to {ma['rounding']} places for the window. Summing displayed "
                              "rounded monthly outputs is unverified.")
        else:
            transformation = (f"Source-supported transformation: sum monthly {core} outputs across "
                              "complete, nonoverlapping month partitions for each separate "
                              "segment/grand-total grouping set.")
        reasons = [transformation,
                   "Zero-fill absent month/segment keys for a complete comparison; NULL versus zero and segment 'All' collisions need review.",
                   "Source membership, period boundaries, join cardinality, time zone, units, snapshot, and grouping-set expansion are unresolved conditions; no unconditional equivalence follows."]
        if not bounded_window:
            reasons.append("No source-verified window date filter on the month key: the constant period label does not establish bounded row membership.")
        if conditions["rounding"]["status"] == "unknown":
            reasons.append("Published monthly values may not sum exactly to the window value; rounding or floating-point cast behavior requires review.")
    elif (not cross_grain and a["grain"] == b["grain"] and same_source and same_value
          and same_segment and same_value_fields and same_period and same_group
          and same_time_key and not same_filter):
        stage_a, stage_b = stage_literal(a["where_expr"]), stage_literal(b["where_expr"])
        stage_indexed_field = (ma["family"] == "field" and stage_a is not None and
                               stage_b is not None and stage_a != stage_b and
                               "stage" in a["filter_input_fields"])
        decision = "related_candidate" if stage_indexed_field else "scope_variant_candidate"
        status = "needs_review"
        if stage_indexed_field:
            reasons = ["The same source value field is indexed by different stage predicates: these are related conversion steps, not a single measure with an interchangeable scope.",
                       "The filter prerequisite is contradicted; stage-specific values and row membership cannot be equated."]
        else:
            reasons = ["The value projection and source agree, but the WHERE predicates differ; the filter prerequisite is contradicted.",
                       "This is a scope variant for review, never an equivalence assertion."]
    else:
        decision = "abstain"
        status = "needs_review"
        reasons = []
        if not same_source:
            reasons.append("Different source relations; common membership is not established.")
        if not same_value:
            reasons.append("Value projections differ; no value transformation is established.")
        if not same_filter:
            reasons.append("WHERE predicates differ; their scopes cannot be equated.")
        if cross_grain and (not ma["additive"] or not mb["additive"]):
            reasons.append("Nonadditive or unsupported value family: monthly AVG, median, ratio, or opaque outputs cannot be summed into a window output.")
        if cross_grain and (not time_shape or not group_shape):
            reasons.append("The month partition or grouping-set reduction is not identifiable from the source expressions.")
        if not same_value_fields or not same_filter_fields:
            reasons.append("Value or filter input fields/lineage differ.")
        if not reasons:
            reasons.append("No supported direct or additive conditional relationship is established.")

    return {
        "left_id": a["id"], "right_id": b["id"], "decision": decision,
        "evidence_status": status, "conditions": conditions, "reasons": reasons,
        "locations": {
            "left": {"source": a["source_location"], "compiled": a["compiled_location"],
                     "review_flags": a["review_flags"]},
            "right": {"source": b["source_location"], "compiled": b["compiled_location"],
                      "review_flags": b["review_flags"]},
        },
    }


def validate_packet(packet: dict) -> None:
    if set(packet) != {"schema_version", "provenance", "cards", "pairs"}:
        raise ValueError("Packet top-level schema differs from contract")
    if packet["schema_version"] != 1 or packet["provenance"].get("commit") != PINNED_COMMIT:
        raise ValueError("Packet schema version or pinned source commit differs from contract")
    cards, pairs = packet["cards"], packet["pairs"]
    if len(cards) != 11 or len(pairs) != 55:
        raise ValueError("Expected exactly 11 cards and 55 pairs")
    ids = set()
    for card in cards:
        if not set(CARD_KEYS).issubset(card):
            raise ValueError("Card is missing contract fields")
        if card["id"] != f"{card['metric_name']}@{card['grain']}" or card["id"] in ids:
            raise ValueError("Invalid or duplicate card ID")
        if card["grain"] not in {"month", "window"}:
            raise ValueError("Unsupported grain in this packet")
        if set(card["unknown_semantics"]) != set(UNKNOWN_KEYS):
            raise ValueError("unknown_semantics keys differ from contract")
        for field in ("value_input_fields", "filter_input_fields"):
            if card[field] != sorted(card[field]):
                raise ValueError(f"{field} must be sorted")
        ids.add(card["id"])
    observed = []
    for pair in pairs:
        if set(pair) != {"left_id", "right_id"}:
            raise ValueError("Pairs must contain identifiers only")
        x, y = pair["left_id"], pair["right_id"]
        if x == y or x not in ids or y not in ids:
            raise ValueError("Invalid pair IDs")
        observed.append(tuple(sorted((x, y))))
    if len(set(observed)) != 55 or set(observed) != set(itertools.combinations(sorted(ids), 2)):
        raise ValueError("Pairs do not form the complete unordered universe")


def run(packet: dict, sha256: str) -> dict:
    validate_packet(packet)
    cards = {card["id"]: card for card in packet["cards"]}
    results = [decide(cards[p["left_id"]], cards[p["right_id"]]) for p in packet["pairs"]]
    by_decision = Counter(r["decision"] for r in results)
    by_status = Counter(r["evidence_status"] for r in results)
    output = {
        "method": METHOD, "input_sha256": sha256, "results": results,
        "counts": {
            "total": len(results),
            "by_decision": {k: by_decision[k] for k in DECISIONS},
            "by_evidence_status": {k: by_status[k] for k in
                                   ("sufficient_for_source_candidate", "needs_review")},
        },
    }
    if len(results) != 55 or any(
        (r["left_id"], r["right_id"]) != (p["left_id"], p["right_id"])
        for p, r in zip(packet["pairs"], results)
    ):
        raise AssertionError("Output did not preserve every packet pair")
    for r in results:
        if r["decision"] not in DECISIONS or any(
            c["status"] not in STATUSES for c in r["conditions"].values()
        ):
            raise AssertionError("Invalid output decision or prerequisite status")
    return output


def synthetic_card(grain: str, expr: str, where: str | None = None) -> dict:
    time = "cohort_month" if grain == "month" else None
    return {
        "id": f"synthetic_{grain}@{grain}", "metric_name": f"synthetic_{grain}",
        "grain": grain, "source_ref": "synthetic_source", "value_expr": expr,
        "where_expr": where,
        "period_expr": time if time else "cast('2025-01-01' as date)",
        "segment_expr": "coalesce(segment, 'All')",
        "group_by": "grouping sets ((cohort_month, segment), (cohort_month))"
        if time else "grouping sets ((segment), ())",
        "time_key": time, "value_input_fields": [], "filter_input_fields": [],
        "source_location": {"path": "synthetic.sql", "start_line": 1, "end_line": 1},
        "compiled_location": {"path": "synthetic_compiled.sql", "start_line": 1, "end_line": 1},
        "review_flags": [], "unknown_semantics": {k: None for k in UNKNOWN_KEYS},
    }


def self_check() -> list[str]:
    month, window = synthetic_card("month", "count(*)"), synthetic_card("window", "count(*)")
    result = decide(month, window)
    assert result["decision"] == "conditional_candidate"
    assert result["evidence_status"] == "needs_review"
    assert result["conditions"]["source_relation"]["status"] == "verified_from_source"
    assert result["conditions"]["source_membership"]["status"] == "unknown"
    assert result["conditions"]["window_time_filter"]["status"] == "unknown"
    assert result["conditions"]["time_partition"]["status"] == "unknown"
    assert result["conditions"]["missing_groups"]["status"] == "unknown"
    assert result["conditions"]["zero_fill_absent_month_groups"]["status"] == "unknown"
    assert "Zero-fill" in " ".join(result["reasons"])
    assert result["conditions"]["null_policy"]["status"] == "unknown"
    # One missing month/segment row is a hole in coverage, not an observed zero.
    present_month_keys = {(1, "A"), (2, "B")}
    required_month_keys = {(m, s) for m in (1, 2) for s in ("A", "B")}
    assert required_month_keys - present_month_keys == {(1, "B"), (2, "A")}
    checked = ["unbounded window and missing-group/zero-fill prerequisites"]
    for expr in ("avg(amount)", "median(amount)", "sum(amount)/nullif(count(*), 0)"):
        x, y = synthetic_card("month", expr), synthetic_card("window", expr)
        x["value_input_fields"] = y["value_input_fields"] = ["amount"]
        result = decide(x, y)
        assert result["decision"] == "abstain", expr
        assert any("Nonadditive" in reason for reason in result["reasons"]), expr
    checked.append("AVG/median/ratio nonadditive rejection")
    x, y = synthetic_card("month", "round(sum(amount), 2)"), synthetic_card("window", "round(sum(amount), 2)")
    x["value_input_fields"] = y["value_input_fields"] = ["amount"]
    bound = "cohort_month between cast('2025-01-01' as date) and cast('2025-02-28' as date)"
    x["where_expr"] = y["where_expr"] = bound
    x["filter_input_fields"] = y["filter_input_fields"] = ["cohort_month"]
    y["time_key"] = "cohort_month"
    result = decide(x, y)
    assert result["decision"] == "conditional_candidate"
    assert result["evidence_status"] == "needs_review"
    assert result["conditions"]["window_time_filter"]["status"] == "verified_from_source"
    assert result["conditions"]["rounding"]["status"] == "unknown"
    assert "unrounded" in " ".join(result["reasons"])
    checked.append("rounded SUM additive core with unresolved rounding")
    x, y = synthetic_card("window", "conversion_rate", "stage = 'A'"), synthetic_card("window", "conversion_rate", "stage = 'B'")
    y["id"] = "synthetic_other@window"
    x["filter_input_fields"] = y["filter_input_fields"] = ["stage"]
    result = decide(x, y)
    assert result["decision"] == "related_candidate"
    assert result["conditions"]["filter_predicate"]["status"] == "contradicted"
    checked.append("different conversion-step predicates remain contradicted")
    return checked


def markdown(output: dict, checks: list[str]) -> str:
    counts = output["counts"]
    lines = [
        "# Constraint-aware full-context baseline",
        "",
        f"Method: `{output['method']}`. Input SHA-256: `{output['input_sha256']}`.",
        "The input contains 11 cards and every one of their 55 unordered pairs. "
        "Decisions are source candidates or abstentions, never equivalence claims.",
        "",
        "## Decision counts",
        "",
        "| Decision | Pairs |",
        "| --- | ---: |",
    ]
    lines += [f"| `{k}` | {v} |" for k, v in counts["by_decision"].items()]
    lines += [
        "",
        f"Evidence status: {counts['by_evidence_status']['sufficient_for_source_candidate']} "
        "sufficient for a *source candidate*; "
        f"{counts['by_evidence_status']['needs_review']} need review.",
        "",
        "## Method and limits",
        "",
        "The method requires identical source references, visible predicates, value projections, "
        "field inputs, and segment projections for a month-to-window candidate. It accepts only "
        "a simple `COUNT(*)`/`COUNT(field)` or `SUM(field)` additive core, a constant window "
        "period label, and grouping sets that match after removing the month key. It treats "
        "`ROUND(SUM(field), n)` as an additive *core* with an unresolved rounding condition. "
        "SQL comparison changes case and whitespace outside string literals only; it does not "
        "rewrite predicates, literals, NULL operators, date bounds, or aliases.",
        "",
        "The transformation sums each month partition within its own segment or grand-total "
        "grouping set. Missing month/segment keys require explicit zero-fill for a complete "
        "comparison; an absent row is not evidence of a zero. A rounded `SUM` requires "
        "unrounded monthly inputs and one final rounding operation, unless a reviewer verifies "
        "that displayed monthly rounding is harmless. The packet's unbounded count "
        "window has no time key or date filter: its period label does not constrain "
        "row membership, so the rollup remains a hypothesis needing review. The "
        "rounded SUM rollup also needs review because published monthly values may "
        "not add exactly to the window value.",
        "",
        "A shared source and `conversion_rate` value field with different single "
        "`stage =` predicates describes related conversion steps. They receive "
        "`related_candidate`, with the filter prerequisite contradicted. This "
        "taxonomy does not equate their populations or rates; other same-value "
        "predicate differences remain scope variants.",
        "",
        "The packet leaves deep upstream field lineage, join cardinality, NULL policy, "
        "missing groups, time zone, units, "
        "snapshot, and grouping-set row expansion unverified. Window membership, period "
        "boundaries, segment `All` collisions, and rounding stay explicit conditions in "
        "the JSON. A matching source reference does not prove upstream row membership. "
        "The parser abstains on unrecognized grouping or aggregate syntax, complex SUM "
        "arguments, nonconstant window labels, and nonadditive AVG, median, and ratio rollups. "
        "Jinja and macro expansion, grouping-set rows, and deep field lineage require "
        "manual source review wherever the packet flags them. Reviewers must also verify "
        "month coverage and window membership, NULL versus zero handling, zero-fill, "
        "segment collisions, numeric rounding, upstream joins, units, time-zone boundaries, "
        "and snapshot alignment before using any transformation. Source review flags "
        "appear with each pair's locations; they are not silently cleared.",
        "",
        "No labels, built rows, row reconciliations, selected pair IDs, or tuned thresholds "
        "were used. This development output alone does not establish accuracy, a gain "
        "over another comparator, or a general equivalence.",
        "",
        "## Synthetic checks",
        "",
    ]
    lines += [f"- Passed: {item}." for item in checks]
    lines += [
        "",
        "## Complete pair decisions",
        "",
        "Source and compiled file/line evidence and all prerequisite statuses are in the JSON.",
        "",
        "| Left | Right | Decision | Evidence status | Immediate reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in output["results"]:
        reason = r["reasons"][0].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{r['left_id']}` | `{r['right_id']}` | `{r['decision']}` | "
                     f"`{r['evidence_status']}` | {reason} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=PACKET,
                        help="shared conditional evidence packet")
    parser.add_argument("--check", action="store_true",
                        help="read-only: run assertions and compare regenerated reports byte-for-byte")
    args = parser.parse_args()
    checks = self_check()
    if not args.packet.is_file():
        parser.error(f"packet not found: {args.packet}")
    raw = args.packet.read_bytes()
    output = run(json.loads(raw), hashlib.sha256(raw).hexdigest())
    generated = {
        JSON_REPORT: (json.dumps(output, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        MD_REPORT: markdown(output, checks).encode("utf-8"),
    }
    if args.check:
        mismatches = [str(path) for path, content in generated.items()
                      if not path.is_file() or path.read_bytes() != content]
        if mismatches:
            raise SystemExit("Saved report missing or differs from regenerated output: " +
                             ", ".join(mismatches))
    else:
        for path, content in generated.items():
            path.write_bytes(content)
    print(f"{len(checks)} synthetic checks passed; {output['counts']['total']} pairs; "
          f"decisions={output['counts']['by_decision']}; SHA-256={output['input_sha256']}; "
          f"reports {'verified unchanged' if args.check else 'regenerated'}")


if __name__ == "__main__":
    main()
