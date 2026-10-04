#!/usr/bin/env python3
"""Source-bounded conditional metric explanations over one shared evidence packet.

The packet is the only data input. No labels, built rows, reconciliations, or other
reports are read. This is a deliberately conservative, syntax-bounded method:
candidate means a reviewable hypothesis, never an equivalence assertion.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PACKET = HERE / "conditional_evidence_packet.json"
JSON_REPORT = HERE / "conditional_decision_report.json"
MD_REPORT = HERE / "conditional_decision_report.md"
METHOD = "proposed_conditional_explanation"
DECISIONS = {
    "direct_candidate", "conditional_candidate", "scope_variant_candidate",
    "related_candidate", "abstain",
}
STATUSES = {"verified_from_source", "unknown", "contradicted", "not_applicable"}
CARD_FIELDS = {
    "id", "metric_name", "grain", "source_ref", "value_expr", "where_expr",
    "period_expr", "segment_expr", "group_by", "time_key",
    "value_input_fields", "filter_input_fields", "source_location",
    "compiled_location", "review_flags", "unknown_semantics",
}
UNKNOWN_FIELDS = {
    "join_cardinality", "null_policy", "missing_groups", "time_zone",
    "units", "snapshot", "grouping_set_expansion",
}
TOKEN = re.compile(
    r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`(?:``|[^`])*`|"
    r"[A-Za-z_][A-Za-z_0-9$]*|\d+(?:\.\d+)?|::|<=|>=|!=|<>|[^\s]",
    re.DOTALL,
)
NONADDITIVE = re.compile(
    r"\b(avg|average|median|percentile_cont|percentile_disc|approx_quantile|"
    r"quantile|stddev|variance|corr|ratio|safe_divide)\s*\(", re.I,
)
TIME_FUNCTIONS = {
    "date", "timestamp", "datetime", "time", "date_trunc", "dateadd",
    "date_add", "date_sub", "extract", "cast", "try_cast", "as", "interval",
    "month", "year", "day", "week", "quarter", "and", "or", "not", "between",
    "is", "null", "at", "zone", "current_date", "current_timestamp",
    "to_date", "date_part", "trunc", "floor", "from_unixtime", "epoch",
    "true", "false",
}


def tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(t if t.startswith(("'", '"', "`")) else t.lower()
                 for t in TOKEN.findall(str(value)))


def same(a: Any, b: Any) -> bool:
    return tokens(a) == tokens(b)


def label(a: Any) -> str:
    return "NULL" if a is None else str(a)


def condition(status: str, evidence: str, locations: list[Any] | None = None) -> dict:
    assert status in STATUSES
    return {"status": status, "evidence": evidence, "locations": locations or []}


def locations(a: dict, b: dict) -> dict:
    return {
        "left": {"source": a["source_location"], "compiled": a["compiled_location"]},
        "right": {"source": b["source_location"], "compiled": b["compiled_location"]},
    }


def source_locs(a: dict, b: dict) -> list[Any]:
    return [a["source_location"], b["source_location"]]


def compiled_locs(a: dict, b: dict) -> list[Any]:
    return [a["compiled_location"], b["compiled_location"]]


def verified_metadata(a: dict, b: dict, key: str) -> dict | None:
    """Non-null entries are independently source verified by the packet contract.

    Explicit negative/status values are not promoted to a verified prerequisite.
    The text is retained so a reviewer can inspect what was actually established.
    """
    x, y = (c["unknown_semantics"][key] for c in (a, b))
    if x is None or y is None:
        return None
    if isinstance(x, dict) and x.get("status") == "contradicted":
        return condition("contradicted", f"Left source evidence: {x}; right: {y}", source_locs(a, b))
    if isinstance(y, dict) and y.get("status") == "contradicted":
        return condition("contradicted", f"Left source evidence: {x}; right: {y}", source_locs(a, b))
    if x != y:
        return condition("unknown", f"Both sides have source evidence, but compatibility is unestablished: {x!r} versus {y!r}.", source_locs(a, b))
    return condition("verified_from_source", f"Both cards record the same independently verified {key}: {x!r}.", source_locs(a, b))


def split_top_level(text: Any, delimiter: str) -> list[str]:
    """Split conjunctions/commas outside parentheses and quoted SQL literals."""
    if not text:
        return []
    ts = tokens(text)
    out: list[list[str]] = [[]]
    depth = 0
    for t in ts:
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
        if depth == 0 and t == delimiter:
            out.append([])
        else:
            out[-1].append(t)
    return [" ".join(part) for part in out]


def group_parts(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return split_top_level(value, ",")


def outer_call(expr: Any) -> tuple[str, tuple[str, ...]] | None:
    ts = tokens(expr)
    while len(ts) >= 2 and ts[0] == "(" and ts[-1] == ")":
        depth = 0
        encloses = True
        for i, t in enumerate(ts):
            depth += (t == "(") - (t == ")")
            if depth == 0 and i != len(ts) - 1:
                encloses = False
                break
        if not encloses:
            break
        ts = ts[1:-1]
    if len(ts) < 4 or ts[1] != "(" or ts[-1] != ")":
        return None
    depth = 0
    for i, t in enumerate(ts[1:], 1):
        depth += (t == "(") - (t == ")")
        if depth == 0 and i != len(ts) - 1:
            return None
        if depth < 0:
            return None
    return (ts[0], ts[2:-1]) if depth == 0 else None


def value_family(expr: Any) -> str:
    text = label(expr)
    if NONADDITIVE.search(text) or re.search(r"\b(?:count|sum)\s*\(\s*distinct\b", text, re.I):
        return "nonadditive"
    call = outer_call(expr)
    if call and call[0] in {"sum", "count"}:
        # A division inside SUM can be additive as an observed per-row value,
        # but could be a preaggregated ratio. Do not infer its grain here.
        if "/" in call[1] or re.search(r"\b(over|grouping|rollup|cube)\b", text, re.I):
            return "unsupported"
        return "additive"
    if call and call[0] == "round":
        arguments = split_top_level(" ".join(call[1]), ",")
        if len(arguments) == 2 and value_family(arguments[0]) == "additive" and re.fullmatch(r"-?\d+", arguments[1].strip()):
            return "rounded_additive"
    # A postfix numeric cast does not change the row partition. Precision can
    # change the answer, so it remains a separate unknown prerequisite.
    ts = tokens(expr)
    if len(ts) >= 6 and ts[1] == "(":
        depth = 0
        for i, t in enumerate(ts[1:], 1):
            depth += (t == "(") - (t == ")")
            if depth == 0:
                if (ts[i + 1:i + 2] == ("::",) and i + 3 == len(ts)
                        and ts[i + 2] in {"double", "float", "integer", "bigint", "decimal", "numeric"}
                        and value_family(" ".join(ts[:i + 1])) == "additive"):
                    return "cast_additive"
                break
    return "unsupported"


def field_tail(value: Any) -> str:
    ids = [t for t in tokens(value) if re.fullmatch(r"[a-z_][a-z_0-9$]*", t)]
    return ids[-1] if ids else ""


def temporal_clause(text: str, time_key: Any) -> bool:
    """Recognize only simple date constraints; a changed stage field fails closed."""
    key = field_tail(time_key)
    ts = tokens(text)
    if not key or key not in ts or not any(t in ts for t in (">", "<", "<=", ">=", "=", "between")):
        return False
    identifiers = [t for t in ts if re.fullmatch(r"[a-z_][a-z_0-9$]*", t)]
    # A qualifier immediately before .time_key is a table alias, not a filter
    # dimension. Other identifiers must be date syntax, never stage predicates.
    qualifier = {ts[i - 2] for i, t in enumerate(ts) if t == key and i >= 2 and ts[i - 1] == "."}
    return all(t == key or t in TIME_FUNCTIONS or t in qualifier for t in identifiers)


def filter_relation(a: dict, b: dict) -> tuple[str, str]:
    x, y = a["where_expr"], b["where_expr"]
    if same(x, y):
        return "same", "Compiled WHERE expressions are token identical."
    if not a["time_key"] or not same(a["time_key"], b["time_key"]):
        return "different", "WHERE differs and the time key is unavailable or differs."
    xa, ya = split_top_level(x, "and"), split_top_level(y, "and")
    xt = [z for z in xa if temporal_clause(z, a["time_key"])]
    yt = [z for z in ya if temporal_clause(z, b["time_key"])]
    xn = Counter(tokens(z) for z in xa if z not in xt)
    yn = Counter(tokens(z) for z in ya if z not in yt)
    if (xt or yt) and xn == yn:
        return "time_only", f"Non-time conjuncts match; temporal conjuncts differ: {xt!r} versus {yt!r}."
    return "different", f"Non-time predicates or unsupported compound predicates differ: {label(x)} versus {label(y)}."


def filter_fields_compatible(a: dict, b: dict) -> bool:
    left, right = set(a["filter_input_fields"]), set(b["filter_input_fields"])
    if left == right:
        return True
    key = field_tail(a["time_key"])
    return bool(key and same(a["time_key"], b["time_key"]) and
                {field_tail(v) for v in left ^ right} == {key})


def grouping_relation(a: dict, b: dict, month_window: bool) -> tuple[bool, str]:
    if not month_window:
        match = tokens(a["group_by"]) == tokens(b["group_by"])
        return match, ("Compiled GROUP BY clauses match exactly." if match else
                       "Compiled GROUP BY clauses differ at the same grain.")

    month = a if str(a["grain"]).lower() == "month" else b
    window = b if month is a else a
    month_key = tokens(month["period_expr"])
    if not month_key:
        return False, "The monthly period key is missing."

    def parse(card: dict) -> tuple[str, list[tuple[tuple[str, ...], ...]]] | None:
        ts = tokens(card["group_by"])
        if ts[:2] == ("grouping", "sets"):
            if ts[:3] != ("grouping", "sets", "(") or ts[-1:] != (")",):
                return None
            groups = []
            for group in split_top_level(" ".join(ts[3:-1]), ","):
                gt = tokens(group)
                if len(gt) < 2 or gt[0] != "(" or gt[-1] != ")":
                    return None
                members = tuple(tokens(z) for z in split_top_level(" ".join(gt[1:-1]), ","))
                if any(not member for member in members):
                    return None
                groups.append(members)
            return ("grouping_sets", groups) if groups else None
        members = tuple(tokens(z) for z in group_parts(card["group_by"]))
        return ("ordinary", [members]) if all(members) else None

    left, right = parse(month), parse(window)
    if left is None or right is None or left[0] != right[0]:
        return False, "Unsupported or mismatched monthly/window grouping syntax."
    monthly, windowed = left[1], right[1]
    if any(group.count(month_key) != 1 for group in monthly):
        return False, "Each monthly grouping set/group must contain the month key exactly once."
    if any(month_key in group for group in windowed):
        return False, "The month key remains in a window grouping set/group."
    reduced = [tuple(member for member in group if member != month_key) for group in monthly]

    # A one-to-one reduction retains every other key and every grouping level.
    # Duplicate grouping sets would create extra rows and are not accepted.
    def canonical(group: tuple[tuple[str, ...], ...]) -> tuple[tuple[str, ...], ...]:
        return tuple(sorted(group))

    reduced_keys = [canonical(group) for group in reduced]
    window_keys = [canonical(group) for group in windowed]
    if (len(reduced_keys) != len(window_keys) or len(set(reduced_keys)) != len(reduced_keys)
            or len(set(window_keys)) != len(window_keys)
            or Counter(reduced_keys) != Counter(window_keys)):
        return False, "Removing exactly one month key per monthly group does not give a unique one-to-one match to window groups."
    return True, ("Each monthly group contains exactly one month key; removing it gives a unique "
                  f"one-to-one window group: {month['group_by']!r} → {window['group_by']!r}.")


def blank_result(a: dict, b: dict) -> dict:
    return {
        "left_id": a["id"], "right_id": b["id"], "decision": "abstain",
        "evidence_status": "needs_review", "conditions": {}, "reasons": [],
        "locations": locations(a, b),
    }


def decide(a: dict, b: dict) -> dict:
    result = blank_result(a, b)
    reasons, conditions = result["reasons"], result["conditions"]
    loc = compiled_locs(a, b)
    family_a, family_b = value_family(a["value_expr"]), value_family(b["value_expr"])
    source_same = same(a["source_ref"], b["source_ref"])
    value_same = same(a["value_expr"], b["value_expr"])
    inputs_same = a["value_input_fields"] == b["value_input_fields"]
    filter_kind, filter_detail = filter_relation(a, b)
    filter_fields_ok = filter_fields_compatible(a, b)
    month_window = {str(a["grain"]).lower(), str(b["grain"]).lower()} == {"month", "window"}
    group_ok, group_detail = grouping_relation(a, b, month_window)

    conditions["symbolic_source_ref"] = condition(
        "verified_from_source" if source_same else "contradicted",
        f"Compiled source_ref: {a['source_ref']!r} versus {b['source_ref']!r}. "
        "A matching relation name does not establish identical runtime rows.", source_locs(a, b) + loc,
    )
    conditions["source_membership"] = condition(
        "unknown" if source_same and filter_kind != "different" and filter_fields_ok else "contradicted",
        f"source_ref: {a['source_ref']!r} versus {b['source_ref']!r}; {filter_detail} "
        f"filter input fields: {a['filter_input_fields']!r} versus {b['filter_input_fields']!r}. "
        "Actual monthly/window row membership, including window date coverage, is not established by a matching source ref. "
        f"Source time keys: {a['time_key']!r} versus {b['time_key']!r}.",
        source_locs(a, b) + loc,
    )
    conditions["filter_alignment"] = condition(
        "verified_from_source" if filter_kind == "same" else ("unknown" if filter_kind == "time_only" else "contradicted"),
        filter_detail, loc,
    )
    conditions["additive_behavior"] = condition(
        "verified_from_source" if family_a == family_b and family_a in {"additive", "rounded_additive", "cast_additive"} and value_same and inputs_same else
        ("contradicted" if "nonadditive" in (family_a, family_b) else "unknown"),
        f"Value families: {family_a}, {family_b}; compiled values: {a['value_expr']!r} versus {b['value_expr']!r}; "
        f"value inputs: {a['value_input_fields']!r} versus {b['value_input_fields']!r}. "
        "Only identical SUM/COUNT operands, optionally followed by explicit ROUND or numeric cast, are treated as additive before final output conversion across disjoint partitions.", loc,
    )
    conditions["partition_keys"] = condition(
        "verified_from_source" if same(a["segment_expr"], b["segment_expr"]) and group_ok else "contradicted",
        f"segment_expr: {a['segment_expr']!r} versus {b['segment_expr']!r}; {group_detail}", loc,
    )
    conditions["time_key_alignment"] = condition(
        "verified_from_source" if a["time_key"] and same(a["time_key"], b["time_key"]) else "unknown",
        f"Source time keys: {a['time_key']!r} versus {b['time_key']!r}; "
        f"compiled period expressions: {a['period_expr']!r} versus {b['period_expr']!r}. "
        "An absent window time key does not verify that its literal period label covers monthly buckets.", source_locs(a, b) + loc,
    )
    conditions["period_boundaries"] = condition(
        "unknown" if month_window else "not_applicable",
        "The month buckets must form an exact, disjoint partition of each window "
        "with identical lower/upper inclusivity and no time shift. Source expressions alone "
        f"do not establish coverage: {a['period_expr']!r} versus {b['period_expr']!r}.", loc,
    )
    conditions["partition_coverage"] = condition(
        "unknown" if month_window else "not_applicable",
        "Every source row in the window must appear in exactly one monthly partition "
        "for the same segment; no out-of-window rows may be included.", source_locs(a, b) + loc,
    )
    for out_key, meta_key, description in (
        ("join_cardinality", "join_cardinality", "Fanout or dropped rows from upstream joins must match."),
        ("null_vs_zero", "null_policy", "An absent group, a present zero, and a present all-NULL SUM group are distinct; COUNT(*) counts rows even when other columns are NULL."),
        ("missing_months_zero_fill", "missing_groups", "Construct the required month × segment grid; zero-fill an absent month only if absence means zero, preserving NULL groups separately."),
        ("time_zone", "time_zone", "Monthly and window boundaries must use the same time zone."),
        ("units", "units", "Both measures must use the same units and conversions."),
        ("snapshot", "snapshot", "Source membership must be compared at the same data snapshot."),
    ):
        conditions[out_key] = verified_metadata(a, b, meta_key) or condition(
            "unknown" if month_window else "not_applicable",
            description + " No compatible source-verified evidence is present on both cards.", source_locs(a, b),
        )
    seg_text = label(a["segment_expr"]) + " " + label(b["segment_expr"])
    all_risk = bool(re.search(r"(?:'all'|\"All\"|\bgrouping\s*\(|\brollup\b|\bcube\b)", seg_text, re.I))
    conditions["segment_all_collision"] = (
        verified_metadata(a, b, "grouping_set_expansion") or condition(
            "unknown" if all_risk else "not_applicable",
            "A literal segment named All may collide with an expanded grouping-set All; "
            "deduplicate or tag grouping-set level before summing. "
            f"segment expressions: {a['segment_expr']!r} versus {b['segment_expr']!r}; "
            f"review flags: {a['review_flags']!r} / {b['review_flags']!r}.", source_locs(a, b) + loc,
        )
    )
    explicit_round = bool(re.search(r"\bround\s*\(", label(a["value_expr"]) + " " + label(b["value_expr"]), re.I))
    conditions["rounding"] = condition(
        "unknown",
        "ROUND is applied after each aggregate. The source-supported transform sums unrounded monthly aggregates "
        "and rounds once at the window; summing published rounded monthly values requires separately proving zero rounding discrepancy."
        if family_a == family_b == "rounded_additive" else
        ("An explicit cast/ROUND appears in the common value; verify numeric precision and conversion stage."
         if explicit_round or family_a == "cast_additive" or family_b == "cast_additive" else
         "No explicit ROUND in compiled values; verify casts, numeric precision, and final display rounding."),
        loc,
    )

    if month_window:
        blockers = []
        if family_a not in {"additive", "rounded_additive", "cast_additive"} or family_a != family_b:
            blockers.append("Nonadditive or unsupported value family; do not sum monthly AVG, median, ratio, distinct count, or unexplained calculations.")
        if not value_same or not inputs_same:
            blockers.append("Value expressions or their input fields differ; no common additive operand is established.")
        if not source_same:
            blockers.append("Different source references do not establish the same row membership.")
        if filter_kind == "different":
            blockers.append("Stage or other non-time filter differs; no rollup relationship follows.")
        if not filter_fields_ok:
            blockers.append("Filter input field sets differ beyond the source time key.")
        if not same(a["segment_expr"], b["segment_expr"]) or not group_ok:
            blockers.append("Segment or grouping keys differ beyond an explicit period key.")
        month_card = a if str(a["grain"]).lower() == "month" else b
        window_card = b if month_card is a else a
        if (not a["period_expr"] or not b["period_expr"] or not month_card["time_key"]
                or (window_card["time_key"] and not same(month_card["time_key"], window_card["time_key"]))):
            blockers.append("The month source time key and both period expressions are required; an explicit different window time key blocks rollup.")
        if blockers:
            reasons.extend(blockers)
            return result
        month = a if str(a["grain"]).lower() == "month" else b
        window = b if month is a else a
        result["decision"] = "conditional_candidate"
        if family_a == "rounded_additive":
            equation = ("window_value(W,s) = ROUND(SUM_{m∈M(W)} unrounded_month_aggregate(m,s), "
                        "the compiled scale); SUM(published_rounded_month_value) is not guaranteed equal")
        elif family_a == "cast_additive":
            equation = ("window_value(W,s) = CAST(SUM_{m∈M(W)} raw_month_count_or_sum(m,s) "
                        "AS the compiled numeric type); cast precision must be checked")
        else:
            equation = "window_value(W,s) = SUM_{m∈M(W)} month_value(m,s)"
        reasons.append(
            "Conditional month→window source transform: for each window W and segment s, "
            f"form its exact constituent months M(W); {equation}. "
            f"The common compiled operand is {month['value_expr']!r}. Build a month × segment "
            "grid and zero-fill absent monthly groups only if absence means zero; keep present "
            "all-NULL groups separate. Tag true segment 'All' separately from grouping-set "
            "totals. This equation holds only after all listed unknown prerequisites are verified. "
            f"Month source {month['source_location']!r}, compiled {month['compiled_location']!r}; "
            f"window source {window['source_location']!r}, compiled {window['compiled_location']!r}."
        )
        if filter_kind == "time_only":
            reasons.append("Different temporal WHERE bounds require explicit month/window boundary validation.")
        return result

    # Exact same-grain source signatures can be reviewable direct candidates;
    # the unknown source/runtime semantics still prevent an equivalence claim.
    exact = (str(a["grain"]).lower() == str(b["grain"]).lower()
             and source_same and value_same and inputs_same and filter_kind == "same"
             and same(a["period_expr"], b["period_expr"])
             and same(a["segment_expr"], b["segment_expr"]) and group_ok
             and same(a["time_key"], b["time_key"])
             and a["filter_input_fields"] == b["filter_input_fields"])
    if exact and family_a != "unsupported":
        result["decision"] = "direct_candidate"
        reasons.append("Identical compiled source/value/filter/period/segment/grouping signatures at the same grain; a source candidate only, with runtime conditions still requiring review.")
    else:
        reasons.append("No source-supported exact-grain or additive month→window transform established; abstain.")
    return result


def load_packet(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    packet = json.loads(raw)
    if not isinstance(packet, dict) or not isinstance(packet.get("cards"), list) or not isinstance(packet.get("pairs"), list):
        raise ValueError("Packet must contain cards and pairs arrays")
    if len(packet["cards"]) != 11 or len(packet["pairs"]) != 55:
        raise ValueError("Expected exactly 11 cards and 55 pairs")
    cards = packet["cards"]
    if any(not isinstance(c, dict) or not CARD_FIELDS <= c.keys() for c in cards):
        raise ValueError("A card is missing contract fields")
    if any(not isinstance(c["unknown_semantics"], dict) or not UNKNOWN_FIELDS <= c["unknown_semantics"].keys() for c in cards):
        raise ValueError("A card is missing unknown_semantics fields")
    ids = [c["id"] for c in cards]
    if any(not isinstance(i, str) or i != f"{c['metric_name']}@{c['grain']}" for i, c in zip(ids, cards)) or len(set(ids)) != 11:
        raise ValueError("Card ids must be unique metric_name@grain")
    seen = set()
    for pair in packet["pairs"]:
        if not isinstance(pair, dict) or not {"left_id", "right_id"} <= pair.keys():
            raise ValueError("Pair is missing ids")
        x, y = pair["left_id"], pair["right_id"]
        if x == y or x not in ids or y not in ids:
            raise ValueError("Pair refers to missing/self card")
        seen.add(frozenset((x, y)))
    if len(seen) != 55 or seen != {frozenset(p) for p in itertools.combinations(ids, 2)}:
        raise ValueError("Pairs must cover each unordered pair exactly once")
    return packet, hashlib.sha256(raw).hexdigest()


def build(packet: dict, sha: str) -> dict:
    cards = {c["id"]: c for c in packet["cards"]}
    results = [decide(cards[p["left_id"]], cards[p["right_id"]]) for p in packet["pairs"]]
    counts = {d: sum(r["decision"] == d for r in results) for d in sorted(DECISIONS)}
    assert len(results) == 55 and sum(counts.values()) == 55
    assert all(r["evidence_status"] in {"sufficient_for_source_candidate", "needs_review"} for r in results)
    assert all(c["status"] in STATUSES for r in results for c in r["conditions"].values())
    return {"method": METHOD, "input_sha256": sha, "results": results, "counts": counts}


def render_md(report: dict) -> str:
    out = [
        "# Proposed conditional explanation — GTM development packet", "",
        f"Input SHA-256: `{report['input_sha256']}`. One result for each of 55 unordered pairs. "
        "These are source candidates, not adjudicated relationships or unconditional equivalences.", "",
        "| Decision | Count |", "|---|---:|",
    ]
    out += [f"| {name} | {number} |" for name, number in report["counts"].items()]
    out += [
        "", "## Decision method", "",
        "Token-identical source/value/filter and explicit grain/grouping constraints identify candidates. "
        "For month→window, the common SUM or COUNT operand must be additive, "
        "with a matching symbolic source ref, value inputs, non-time filters, a monthly "
        "time key and segment grouping. Every monthly group must contain exactly one "
        "month key and reduce one-to-one to a window group without that key. "
        "Different stage predicates, distinct counts, AVG/median/ratio expressions, and "
        "unsupported arithmetic cannot be rolled up by this method. Post-aggregate rounding "
        "requires unrounded monthly aggregates and a single final window ROUND. "
        "Only simple, source-time-key conjuncts may differ as temporal filters. "
        "Token comparison lowercases unquoted identifiers and ignores whitespace; it does not "
        "rewrite literals, predicates, operators, NULL behavior, or constants.", "",
        "The candidate equation is `window_value(W,s) = SUM(month_value(m,s) for m in M(W))` "
        "for bare additive outputs. For ROUND(SUM(...)), sum raw monthly aggregates then round "
        "at the window; for COUNT(*)::double, sum raw counts before casting. Both require "
        "precision review. Every equation is conditional on source membership, exact time partition and bounds, segment grouping, "
        "month × segment coverage, All/grouping-set disambiguation, absent-group zero-fill "
        "versus present NULL, additive behavior, join cardinality, units, rounding, time zone "
        "and snapshot conditions have been reviewed. Unresolved prerequisites keep candidate "
        "evidence_status at needs_review. The JSON contains each prerequisite's "
        "status, evidence and source locations.", "",
        "## Pair outputs", "",
        "| Pair | Decision | Evidence status | Unresolved prerequisites |", "|---|---|---|---|",
    ]
    for r in report["results"]:
        outstanding = [k for k, v in r["conditions"].items() if v["status"] in {"unknown", "contradicted"}]
        pair = f"{r['left_id']} ↔ {r['right_id']}".replace("|", "\\|")
        out.append(f"| {pair} | {r['decision']} | {r['evidence_status']} | {', '.join(outstanding) or 'none'} |")
    out += ["", "## Conditional transforms", ""]
    candidates = [r for r in report["results"] if r["decision"] == "conditional_candidate"]
    if not candidates:
        out.append("No additive month→window transform passed the source-syntax gates.")
    for r in candidates:
        out += [f"### {r['left_id']} ↔ {r['right_id']}", "", r["reasons"][0], ""]
    out += [
        "", "## Manual review and limits", "",
        "This is a development exercise on the shared pinned packet. The method reads no "
        "built rows, labels, reconciliations, prior decisions, or separate sources. "
        "Unknown metadata stays unknown. Simple token comparison and bounded SUM/COUNT "
        "recognition do not prove SQL equivalence; aliases, casts, nested calculations, "
        "complex OR filters and arbitrary date rewrites may cause abstention. Manual review "
        "must establish the month-to-window period map, actual source membership, joins, "
        "missing/null groups, All level identity, numeric rounding/units and snapshot. "
        "No accuracy, incremental gain, or held-out result is claimed.", "",
    ]
    return "\n".join(out)


def synthetic_checks() -> None:
    """Counterfactuals exercise decision gates and value-level failure mechanisms."""
    base = {
        "id": "synthetic@month", "metric_name": "synthetic", "grain": "month",
        "source_ref": "events", "value_expr": "SUM(amount)",
        "where_expr": "stage = 'created'", "period_expr": "date_trunc('month', event_at)",
        "segment_expr": "coalesce(segment, 'All')",
        "group_by": ["date_trunc('month', event_at)", "segment"],
        "time_key": "event_at", "value_input_fields": ["amount"],
        "filter_input_fields": ["stage"], "source_location": "synthetic:source",
        "compiled_location": "synthetic:compiled", "review_flags": [],
        "unknown_semantics": {k: None for k in UNKNOWN_FIELDS},
    }
    month = dict(base)
    window = dict(base, id="synthetic@window", grain="window", period_expr="'window'",
                  group_by=["segment"])
    good = decide(month, window)
    assert good["decision"] == "conditional_candidate"
    assert decide(window, month)["decision"] == "conditional_candidate"
    assert good["evidence_status"] == "needs_review"
    assert good["conditions"]["symbolic_source_ref"]["status"] == "verified_from_source"
    assert good["conditions"]["source_membership"]["status"] == "unknown"
    assert good["conditions"]["partition_keys"]["status"] == "verified_from_source"
    assert good["conditions"]["partition_coverage"]["status"] == "unknown"
    assert good["conditions"]["segment_all_collision"]["status"] == "unknown"
    assert good["conditions"]["null_vs_zero"]["status"] == "unknown"
    assert good["conditions"]["missing_months_zero_fill"]["status"] == "unknown"
    assert "zero-fill" in good["reasons"][0] and "all-NULL" in good["reasons"][0]

    # Same grouping at both grains is not a rollup: the month key survived.
    identical_list_grouping = dict(window, group_by=month["group_by"])
    bad_list = decide(month, identical_list_grouping)
    assert bad_list["decision"] == "abstain"
    assert decide(identical_list_grouping, month)["decision"] == "abstain"
    assert bad_list["conditions"]["partition_keys"]["status"] == "contradicted"
    missing_month_list = dict(month, group_by=["segment"])
    assert decide(missing_month_list, window)["decision"] == "abstain"
    duplicate_month_list = dict(month, group_by=[month["period_expr"], month["period_expr"], "segment"])
    assert decide(duplicate_month_list, window)["decision"] == "abstain"

    # A window with no recorded time key or date filter remains a hypothesis.
    unbounded_month = dict(month, where_expr=None, filter_input_fields=[])
    unbounded_window = dict(window, where_expr=None, filter_input_fields=[], time_key=None)
    unbounded = decide(unbounded_month, unbounded_window)
    assert unbounded["decision"] == "conditional_candidate"
    assert unbounded["evidence_status"] == "needs_review"
    assert unbounded["conditions"]["source_membership"]["status"] == "unknown"
    assert unbounded["conditions"]["time_key_alignment"]["status"] == "unknown"

    changed_time = dict(window, time_key="settled_at")
    assert decide(month, changed_time)["decision"] == "abstain"
    changed_stage = dict(window, where_expr="stage = 'won'")
    assert decide(month, changed_stage)["decision"] == "abstain"
    changed_stage_with_date = dict(window, where_expr="stage = 'won' AND event_at >= DATE '2025-01-01'")
    assert decide(month, changed_stage_with_date)["decision"] == "abstain"
    changed_date_only = dict(window, where_expr="stage = 'created' AND event_at < DATE '2025-04-01'")
    assert decide(month, changed_date_only)["decision"] == "conditional_candidate"
    assert decide(month, changed_date_only)["conditions"]["period_boundaries"]["status"] == "unknown"
    changed_ratio = dict(window, value_expr="AVG(amount)")
    assert decide(month, changed_ratio)["decision"] == "abstain"
    changed_distinct = dict(window, value_expr="COUNT(DISTINCT account_id)")
    assert decide(month, changed_distinct)["decision"] == "abstain"
    funnel_a = dict(window, value_expr="conversion_rate", where_expr="stage = 'SAL'")
    funnel_b = dict(window, value_expr="conversion_rate", where_expr="stage = 'SQL'")
    assert decide(funnel_a, funnel_b)["decision"] == "abstain"
    mismatched_filter_fields = dict(window, filter_input_fields=["other_stage"])
    assert decide(month, mismatched_filter_fields)["decision"] == "abstain"
    both_rounded = (dict(month, value_expr="ROUND(SUM(amount), 2)"),
                    dict(window, value_expr="ROUND(SUM(amount), 2)"))
    rounded = decide(*both_rounded)
    assert rounded["decision"] == "conditional_candidate"
    assert rounded["conditions"]["rounding"]["status"] == "unknown"
    assert "unrounded_month_aggregate" in rounded["reasons"][0]
    casted = (dict(month, value_expr="count(*)::double"), dict(window, value_expr="count(*)::double"))
    assert decide(*casted)["decision"] == "conditional_candidate"
    grouped = (dict(month, group_by="grouping sets ((event_at, segment), (event_at))", period_expr="event_at"),
               dict(window, group_by="grouping sets ((segment), ())"))
    assert decide(*grouped)["decision"] == "conditional_candidate"
    identical_grouping_sets = dict(grouped[1], group_by=grouped[0]["group_by"])
    assert decide(grouped[0], identical_grouping_sets)["decision"] == "abstain"
    missing_month_set = dict(grouped[0], group_by="grouping sets ((event_at, segment), (segment))")
    assert decide(missing_month_set, grouped[1])["decision"] == "abstain"
    window_month_set = dict(grouped[1], group_by="grouping sets ((segment), (event_at))")
    assert decide(grouped[0], window_month_set)["decision"] == "abstain"
    duplicate_reduction = dict(grouped[0], group_by="grouping sets ((event_at, segment), (segment, event_at))")
    assert decide(duplicate_reduction, dict(grouped[1], group_by="grouping sets ((segment), (segment))"))["decision"] == "abstain"

    # Same numeric rows can change meaning under a moved window edge.
    month_values = {"Jan": 4, "Feb": 6, "Mar": 8}
    assert sum(month_values[m] for m in ("Jan", "Feb")) != sum(month_values[m] for m in ("Feb", "Mar"))
    # Absence and a present all-NULL group are different SQL states; COALESCE
    # would erase that distinction and cannot be silently inserted.
    sql_sum = lambda values: None if not values or all(v is None for v in values) else sum(v for v in values if v is not None)
    assert sql_sum([None]) is None and sql_sum([None]) != 0
    groups = {"Jan": 3}
    assert "Feb" not in groups and sum(groups.values()) == 3
    assert sum(groups.get(m, 0) for m in ("Jan", "Feb")) == 3  # only if absence means zero
    # Rounding monthly outputs can differ from rounding the unrounded sum.
    x = Decimal("0.045")
    round_cent = lambda z: z.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert round_cent(x) + round_cent(x) != round_cent(x + x)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="run synthetic checks and verify current reports against the packet")
    args = parser.parse_args()
    synthetic_checks()
    if not PACKET.exists():
        if args.check:
            print("Synthetic counterfactual checks passed; packet not present yet.")
            return
        raise SystemExit(f"Shared packet not present: {PACKET}")
    packet, sha = load_packet(PACKET)
    report = build(packet, sha)
    json_text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    md_text = render_md(report)
    if args.check:
        if not JSON_REPORT.exists() or not MD_REPORT.exists():
            raise SystemExit("Reports missing; run without --check first")
        if JSON_REPORT.read_text() != json_text or MD_REPORT.read_text() != md_text:
            raise SystemExit("Reports are stale or modified relative to the packet/method")
        print(f"Checks passed: {len(report['results'])} pairs, SHA-256 {sha}, counts {report['counts']}")
    else:
        JSON_REPORT.write_text(json_text)
        MD_REPORT.write_text(md_text)
        print(f"Wrote 55 decisions, SHA-256 {sha}, counts {report['counts']}")


if __name__ == "__main__":
    main()
