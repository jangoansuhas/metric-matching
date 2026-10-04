#!/usr/bin/env python3
"""Conservative, full-context lexical SQL/lineage comparator for the shared packet.

Only this packet supplies comparison inputs. IDs route results; names, review flags,
provenance and any external outcomes never influence a decision. Run normally to
write the two reports, or with --check to self-test and verify existing reports.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys
from typing import Any


BASE = Path(__file__).resolve().parent
PACKET = BASE / "conditional_evidence_packet.json"
JSON_REPORT = BASE / "normalized_sql_lineage_report.json"
MD_REPORT = BASE / "normalized_sql_lineage_report.md"
METHOD = "normalized_sql_lineage_baseline"

CARD_FIELDS = frozenset(
    ("id", "metric_name", "grain", "source_ref", "value_expr", "where_expr",
     "period_expr", "segment_expr", "group_by", "time_key",
     "value_input_fields", "filter_input_fields", "source_location",
     "compiled_location", "review_flags", "unknown_semantics")
)
UNKNOWN_FIELDS = (
    "join_cardinality", "null_policy", "missing_groups", "time_zone",
    "units", "snapshot", "grouping_set_expansion",
)
SQL_FIELDS = (
    "source_ref", "value_expr", "where_expr", "period_expr",
    "segment_expr", "group_by", "time_key",
)
SCALAR_FIELDS = SQL_FIELDS + ("grain", "value_input_fields", "filter_input_fields")
EXPRESSION_FIELDS = set(SQL_FIELDS) - {"source_ref"}
NUMERIC = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


class UnsupportedSQL(ValueError):
    """Syntax whose harmless normalization cannot be established lexically."""


def tokenize(sql: str) -> tuple[tuple[str, str], ...]:
    """Remove SQL comments/whitespace, retaining exact remaining token text.

    Tokens distinguish numbers, identifiers, strings, operators and punctuation.
    Unknown or ambiguous syntax is rejected rather than equated.
    """
    result: list[tuple[str, str]] = []
    pos = 0
    length = len(sql)
    while pos < length:
        c = sql[pos]
        if c.isspace():
            pos += 1
            continue
        if sql.startswith("--", pos):
            end = sql.find("\n", pos + 2)
            pos = length if end < 0 else end
            continue
        if sql.startswith("/*", pos):
            end = sql.find("*/", pos + 2)
            if end < 0:
                raise UnsupportedSQL("unterminated block comment")
            if "/*" in sql[pos + 2:end]:
                raise UnsupportedSQL("nested block comment has dialect-dependent meaning")
            pos = end + 2
            continue
        if c in "'\"`":
            start, quote = pos, c
            pos += 1
            while pos < length:
                if sql[pos] == "\\":
                    raise UnsupportedSQL("backslash in quoted text has dialect-dependent meaning")
                if sql[pos] == quote:
                    if pos + 1 < length and sql[pos + 1] == quote:
                        pos += 2
                    else:
                        pos += 1
                        break
                else:
                    pos += 1
            else:
                raise UnsupportedSQL("unterminated quoted text")
            result.append(("literal" if quote == "'" else "quoted_identifier", sql[start:pos]))
            continue
        if c == "$":
            delim = re.match(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$", sql[pos:])
            if delim:
                marker = delim.group()
                end = sql.find(marker, pos + len(marker))
                if end < 0:
                    raise UnsupportedSQL("unterminated dollar-quoted literal")
                result.append(("literal", sql[pos:end + len(marker)]))
                pos = end + len(marker)
                continue
        if c.isalpha() or c == "_":
            start = pos
            pos += 1
            while pos < length and (sql[pos].isalnum() or sql[pos] in "_$"):
                pos += 1
            result.append(("word", sql[start:pos]))
            continue
        if c.isdigit() or (c == "." and pos + 1 < length and sql[pos + 1].isdigit()):
            match = NUMERIC.match(sql, pos)
            assert match is not None
            result.append(("number", match.group()))
            pos = match.end()
            continue
        if c in "(),.;[]":
            result.append(("punctuation", c))
            pos += 1
            continue
        if c in "+-*/%<>=!~^|&:#?@":
            start = pos
            pos += 1
            while pos < length and sql[pos] in "+-*/%<>=!~^|&:#?@":
                # A comment marker begins a new lexical unit.
                if sql.startswith("--", pos) or sql.startswith("/*", pos):
                    break
                pos += 1
            result.append(("operator", sql[start:pos]))
            continue
        raise UnsupportedSQL(f"unrecognized character U+{ord(c):04X}")
    return tuple(result)


def is_identifier(token: tuple[str, str]) -> bool:
    return token[0] in {"word", "quoted_identifier"}


def relation_end(tokens: tuple[tuple[str, str], ...], start: int) -> int:
    """End of a simple, possibly qualified SQL table identifier."""
    if start >= len(tokens) or not is_identifier(tokens[start]):
        return start
    end = start + 1
    while end + 1 < len(tokens) and tokens[end] == ("punctuation", ".") and is_identifier(tokens[end + 1]):
        end += 2
    return end


def drop_optional_table_as(tokens: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    """Drop AS only in `relation AS alias` or `FROM/JOIN relation AS alias`."""
    remove: set[int] = set()
    end = relation_end(tokens, 0)
    if (end and end + 2 == len(tokens) and tokens[end][0] == "word"
            and tokens[end][1].upper() == "AS" and is_identifier(tokens[end + 1])):
        remove.add(end)
    # Keyword recognition for the clause is case-insensitive; the compared
    # identifier and all other token spelling remains exact.
    for i, token in enumerate(tokens):
        if token[0] != "word" or token[1].upper() not in {"FROM", "JOIN"}:
            continue
        end = relation_end(tokens, i + 1)
        if end > i + 1 and end + 1 < len(tokens) and tokens[end][0] == "word" and tokens[end][1].upper() == "AS" and is_identifier(tokens[end + 1]):
            remove.add(end)
    return tuple(token for i, token in enumerate(tokens) if i not in remove)


def normalized_sql(raw: str | None, *, source_ref: bool = False) -> tuple[tuple[str, str], ...] | None:
    if raw is None:
        return None
    tokens = tokenize(raw)
    return drop_optional_table_as(tokens) if source_ref else tokens


def printable(value: Any) -> str:
    """Report representation; token boundaries remain in the comparison key."""
    if isinstance(value, tuple):
        return " ".join(token[1] for token in value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def unique_object(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise ValueError(f"duplicate JSON property: {key}")
        out[key] = value
    return out


def validate_packet(packet: Any) -> None:
    if not isinstance(packet, dict) or set(packet) != {"schema_version", "provenance", "cards", "pairs"}:
        raise ValueError("packet must have exactly the four contract top-level fields")
    if packet["schema_version"] != 1 or not isinstance(packet["provenance"], dict):
        raise ValueError("unsupported packet schema/provenance")
    cards, pairs = packet["cards"], packet["pairs"]
    if not isinstance(cards, list) or len(cards) != 11 or not isinstance(pairs, list) or len(pairs) != 55:
        raise ValueError("expected exactly 11 cards and 55 pairs")
    ids: set[str] = set()
    for card in cards:
        if not isinstance(card, dict) or set(card) != CARD_FIELDS:
            raise ValueError("card has missing or extra fields")
        if any(not isinstance(card[k], str) or not card[k] for k in ("id", "metric_name", "grain", "source_ref", "value_expr", "period_expr", "segment_expr")):
            raise ValueError("invalid required card text")
        if card["id"] != f"{card['metric_name']}@{card['grain']}" or card["id"] in ids:
            raise ValueError("card IDs must be unique metric_name@grain values")
        ids.add(card["id"])
        if any(card[k] is not None and not isinstance(card[k], str) for k in ("where_expr", "group_by", "time_key")):
            raise ValueError("invalid nullable card text")
        for field in ("value_input_fields", "filter_input_fields"):
            values = card[field]
            if not isinstance(values, list) or any(not isinstance(x, str) for x in values) or values != sorted(set(values)):
                raise ValueError(f"{field} must be a sorted unique string list")
        if any(not isinstance(card[k], dict) for k in ("source_location", "compiled_location")):
            raise ValueError("source/compiled locations must be objects")
        if not isinstance(card["review_flags"], list) or any(not isinstance(x, str) for x in card["review_flags"]):
            raise ValueError("review_flags must be strings")
        if not isinstance(card["unknown_semantics"], dict) or set(card["unknown_semantics"]) != set(UNKNOWN_FIELDS):
            raise ValueError("unknown_semantics must have the seven contract keys")
    observed: set[frozenset[str]] = set()
    for pair in pairs:
        if not isinstance(pair, dict) or set(pair) != {"left_id", "right_id"}:
            raise ValueError("pairs must have only left_id and right_id")
        left, right = pair["left_id"], pair["right_id"]
        if left not in ids or right not in ids or left == right:
            raise ValueError("invalid pair IDs")
        unordered = frozenset((left, right))
        if unordered in observed:
            raise ValueError("duplicate unordered pair")
        observed.add(unordered)
    if observed != {frozenset(p) for p in itertools.combinations(ids, 2)}:
        raise ValueError("pairs do not enumerate the complete unordered card universe")


def compared_value(card: dict[str, Any], field: str) -> Any:
    value = card[field]
    if field in SQL_FIELDS:
        return normalized_sql(value, source_ref=(field == "source_ref"))
    if field.endswith("_input_fields"):
        return frozenset(value)
    return value


def pair_result(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    equal: dict[str, bool] = {}
    differences: list[str] = []
    for field in SCALAR_FIELDS:
        left_error = right_error = None
        try:
            lv = compared_value(left, field)
        except UnsupportedSQL as exc:
            lv, left_error = None, str(exc)
        try:
            rv = compared_value(right, field)
        except UnsupportedSQL as exc:
            rv, right_error = None, str(exc)
        both_supported = left_error is None and right_error is None
        equal[field] = both_supported and lv == rv
        status = "unknown" if not both_supported else ("verified_from_source" if equal[field] else "contradicted")
        evidence = {"left": left[field], "right": right[field]}
        if field in SQL_FIELDS:
            evidence["normalized_left"] = None if left_error else printable(lv)
            evidence["normalized_right"] = None if right_error else printable(rv)
        if left_error:
            evidence["left_unsupported"] = left_error
        if right_error:
            evidence["right_unsupported"] = right_error
        conditions[field + "_alignment"] = {"status": status, "source_evidence": evidence}
        if not equal[field]:
            differences.append(field)

    # Unknown semantics are source-reported metadata, never inferred from
    # expression equality, a matching source name or a sample of built rows.
    for field in UNKNOWN_FIELDS:
        lv, rv = left["unknown_semantics"][field], right["unknown_semantics"][field]
        if lv is None or rv is None:
            status = "unknown"
        else:
            status = "verified_from_source" if lv == rv else "contradicted"
        conditions[field] = {
            "status": status,
            "source_evidence": {"left": lv, "right": rv},
        }

    supported = all(conditions[field + "_alignment"]["status"] != "unknown" for field in SCALAR_FIELDS)
    if not supported:
        decision = "abstain"
    elif not differences:
        decision = "direct_candidate"
    elif (all(equal[f] for f in ("source_ref", "value_expr", "where_expr", "segment_expr",
                                      "value_input_fields", "filter_input_fields"))
          and any(not equal[f] for f in ("grain", "period_expr", "group_by"))):
        # Time key may change when a period is rolled into a window. This
        # reports a scope difference, never that a rollup is valid.
        decision = "scope_variant_candidate"
    elif (all(equal[f] for f in ("source_ref", "value_expr", "period_expr", "segment_expr",
                                      "group_by", "grain", "time_key", "value_input_fields"))
          and not equal["where_expr"]):
        # Even identical value projections can represent different populations.
        decision = "related_candidate"
    else:
        decision = "abstain"

    statuses = [v["status"] for v in conditions.values()]
    evidence_status = ("sufficient_for_source_candidate" if decision == "direct_candidate"
                       and all(x == "verified_from_source" for x in statuses) else "needs_review")
    if decision == "direct_candidate":
        reasons = ["All compared source dimensions match after the documented lexical normalization; this is only a source candidate."]
    elif decision == "scope_variant_candidate":
        reasons = ["Value, filter, segment, source and field sets match; period/grain/grouping scope differs. No aggregation, zero-fill or equivalence is inferred."]
    elif decision == "related_candidate":
        reasons = ["Value projection and source context match, but the filter/population differs; this is only a related source candidate."]
    else:
        reasons = ["Lexical source evidence does not support a direct or scoped candidate; abstain."]
    for field in differences:
        item = conditions[field + "_alignment"]
        why = "unsupported syntax" if item["status"] == "unknown" else "different"
        evidence = item["source_evidence"]
        reasons.append(f"{field} {why}: left={evidence['left']!r}; right={evidence['right']!r}")
    unknown = [name for name in UNKNOWN_FIELDS if conditions[name]["status"] == "unknown"]
    if unknown:
        reasons.append("Independently unverified semantics: " + ", ".join(unknown) + ".")
    if decision == "scope_variant_candidate":
        reasons.append("Any month-to-window transformation, including nonadditive AVG/median/ratio behavior, requires separate proof.")
    return {
        "left_id": left["id"], "right_id": right["id"],
        "decision": decision, "evidence_status": evidence_status,
        "conditions": conditions, "reasons": reasons,
        "locations": {
            "left": {"source": left["source_location"], "compiled": left["compiled_location"]},
            "right": {"source": right["source_location"], "compiled": right["compiled_location"]},
        },
    }


def build_report(packet: dict[str, Any], digest: str) -> dict[str, Any]:
    validate_packet(packet)
    by_id = {c["id"]: c for c in packet["cards"]}
    results = [pair_result(by_id[p["left_id"]], by_id[p["right_id"]]) for p in packet["pairs"]]
    return {
        "method": METHOD, "input_sha256": digest, "results": results,
        "counts": {
            "total": len(results),
            "by_decision": dict(sorted(Counter(r["decision"] for r in results).items())),
            "by_evidence_status": dict(sorted(Counter(r["evidence_status"] for r in results).items())),
        },
    }


def as_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def md_text(s: Any) -> str:
    return str(s).replace("|", "\\|").replace("`", "\\`").replace("\n", " ")


def as_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Normalized SQL/lineage baseline (full context)", "",
        f"Input packet SHA-256: `{report['input_sha256']}`. All {report['counts']['total']} unordered pairs are reported.", "",
        "## Exact normalization policy", "",
        "- Skip SQL whitespace, `--` line comments and nonnested `/* ... */` comments outside quoted text. Compare sequences of typed tokens; whitespace removal never joins identifiers or numbers.",
        "- Retain exact spelling and contents of single-quoted strings, quoted identifiers, dollar-quoted strings, numeric literals, operators and every other token. No constant folding, keyword/identifier case folding, predicate rewriting, NULL rewriting, date-boundary rewriting or field-name synonym matching.",
        "- In `source_ref` only, omit optional `AS` in a simple `table AS alias` or `FROM/JOIN table AS alias` form. `AS` in values, casts, predicates, grouping and other clauses is retained. No alias-resolution or table-identity inference.",
        "- Compare `value_expr`, `where_expr`, `period_expr`, `segment_expr`, `group_by`, `time_key` and `source_ref` as typed token sequences (including `null` versus nonnull). Compare `grain` literally and each supplied input-field list as a set. Preserve grouping expression order and `GROUPING SETS` syntax.",
        "- Unsupported/dialect-dependent characters, nested or unclosed comments, unclosed quoted text and backslashes inside quotes produce an abstention. Neither card names, review flags, provenance, labels nor row outcomes are scoring inputs. IDs only route results.", "",
        "## Decision policy and limits", "",
        "An exact match across compared dimensions is a `direct_candidate`; a matching source/value/filter/segment/field context with period, grain or grouping differences is a `scope_variant_candidate`; a matching context with a changed filter is a `related_candidate`. All other pairs abstain. These categories are source suggestions, never unqualified equivalence assertions. The baseline identifies no transformation and emits no `conditional_candidate` decision.", "",
        "Every mismatch is a contradicted prerequisite. Packet `unknown_semantics` remain unknown unless both cards independently provide the same verified value. Scope candidates always need review; a direct candidate with any unknown semantics also needs review. In particular, grouping-set expansion, join cardinality, NULL behavior, missing month groups, time zones, units and snapshot alignment cannot be inferred from identical SQL. No additive rollup, zero-fill, rounding alignment or nonadditive aggregation is proved.", "",
        "## Counts", "",
        "| Decision | Pairs |", "|---|---:|",
    ]
    for name in ("direct_candidate", "conditional_candidate", "scope_variant_candidate", "related_candidate", "abstain"):
        lines.append(f"| `{name}` | {report['counts']['by_decision'].get(name, 0)} |")
    lines += ["", "| Evidence status | Pairs |", "|---|---:|"]
    for name in ("sufficient_for_source_candidate", "needs_review"):
        lines.append(f"| `{name}` | {report['counts']['by_evidence_status'].get(name, 0)} |")
    lines += ["", "## All pairs", "", "| Left | Right | Decision | Evidence | Different dimensions |", "|---|---|---|---|---|"]
    for result in report["results"]:
        differences = [key.removesuffix("_alignment") for key, value in result["conditions"].items()
                       if key.endswith("_alignment") and value["status"] != "verified_from_source"]
        lines.append("| " + " | ".join(md_text(x) for x in
                     (result["left_id"], result["right_id"], result["decision"],
                      result["evidence_status"], ", ".join(differences) or "none")) + " |")
    lines += ["", "## Dimension differences", "",
              "The JSON report records the full raw and normalized expressions, prerequisite statuses and both source/compiled locations for every pair. Differences below preserve the original literals and predicates.", ""]
    for result in report["results"]:
        changed = [(key.removesuffix("_alignment"), value) for key, value in result["conditions"].items()
                   if key.endswith("_alignment") and value["status"] != "verified_from_source"]
        if not changed:
            continue
        lines.append(f"### {result['left_id']} / {result['right_id']}")
        lines.append("")
        for name, item in changed:
            ev = item["source_evidence"]
            lines.append(f"- **{name}** ({item['status']}): left `{md_text(json.dumps(ev['left'], ensure_ascii=False))}`; right `{md_text(json.dumps(ev['right'], ensure_ascii=False))}`.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def fixture(**changes: Any) -> dict[str, Any]:
    card: dict[str, Any] = {
        "id": "synthetic", "source_ref": "FROM sales AS s", "value_expr": "sum(amount)",
        "where_expr": "stage = 'First'", "period_expr": "month_key",
        "segment_expr": "segment", "group_by": "grouping sets ((month_key, segment))",
        "grain": "month", "time_key": "month_key", "value_input_fields": ["amount"],
        "filter_input_fields": ["stage"], "unknown_semantics": dict.fromkeys(UNKNOWN_FIELDS),
        "source_location": {"path": "synthetic.sql", "start_line": 1, "end_line": 1},
        "compiled_location": {"path": "synthetic.sql", "start_line": 1, "end_line": 1},
    }
    card.update(changes)
    return card


def self_check() -> None:
    # Lexical invariants and counterfactual changes are deliberately synthetic;
    # they do not select or tune to any packet pair or known outcome.
    assert normalized_sql("sum( amount /* note */ ) -- tail\n") == normalized_sql("sum(amount)")
    assert normalized_sql("'a  -- /* b' /* comment */") == normalized_sql("'a  -- /* b'")
    assert normalized_sql("'A  B'") != normalized_sql("'A B'")
    assert normalized_sql("2.0") != normalized_sql("2")
    assert normalized_sql("x IS NULL") != normalized_sql("x = NULL")
    assert normalized_sql("CAST(x AS DATE)") != normalized_sql("CAST(x DATE)")
    assert normalized_sql("FROM sales AS s", source_ref=True) == normalized_sql("FROM sales s", source_ref=True)
    assert normalized_sql("sales AS s", source_ref=True) == normalized_sql("sales s", source_ref=True)
    assert normalized_sql("sales as s", source_ref=True) == normalized_sql("sales s", source_ref=True)
    assert normalized_sql("stage = 'First'") != normalized_sql("stage = 'Second'")
    assert normalized_sql("grouping sets ((month_key, segment))") != normalized_sql("grouping sets ((segment), ())")
    for bad in ("x /* unclosed", "x /* outer /* nested */", "'unterminated", "'back\\'slash'"):
        try:
            normalized_sql(bad)
        except UnsupportedSQL:
            pass
        else:
            raise AssertionError(f"ambiguous SQL accepted: {bad!r}")

    left = fixture(id="left")
    direct = pair_result(left, fixture(id="right", source_ref="FROM sales s", value_expr="sum( /* ok */ amount)"))
    assert direct["decision"] == "direct_candidate" and direct["evidence_status"] == "needs_review"
    stage = pair_result(left, fixture(id="right", where_expr="stage = 'Second'"))
    assert stage["decision"] == "related_candidate" and stage["evidence_status"] == "needs_review"
    assert stage["conditions"]["where_expr_alignment"]["status"] == "contradicted"
    null_filter = pair_result(left, fixture(id="right", where_expr="stage IS NULL"))
    assert null_filter["decision"] not in {"direct_candidate", "scope_variant_candidate", "conditional_candidate"}
    scope = pair_result(left, fixture(id="right", grain="window", period_expr="cast('2025-01-01' as date)",
                                      group_by="grouping sets ((segment), ())", time_key=None))
    assert scope["decision"] == "scope_variant_candidate" and scope["evidence_status"] == "needs_review"
    assert all(scope["conditions"][k + "_alignment"]["status"] == "contradicted"
               for k in ("grain", "period_expr", "group_by", "time_key"))
    assert pair_result(left, fixture(id="right", source_ref="other_source"))["decision"] == "abstain"
    assert pair_result(left, fixture(id="right", value_expr="avg(amount)"))["decision"] == "abstain"


def read_packet() -> tuple[dict[str, Any], str]:
    raw = PACKET.read_bytes()
    packet = json.loads(raw, object_pairs_hook=unique_object)
    return packet, hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run synthetic self-checks and verify saved reports against the packet")
    args = parser.parse_args()
    self_check()
    packet, digest = read_packet()
    report = build_report(packet, digest)
    desired = ((JSON_REPORT, as_json(report)), (MD_REPORT, as_markdown(report)))
    if args.check:
        for path, content in desired:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"missing or stale report: {path.name}")
        print(f"PASS: synthetic self-checks; {len(report['results'])} packet pairs; SHA-256 {digest}; reports match")
    else:
        for path, content in desired:
            path.write_text(content, encoding="utf-8")
        print(f"Wrote {len(report['results'])} results, SHA-256 {digest}: {JSON_REPORT.name}, {MD_REPORT.name}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, UnsupportedSQL, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
