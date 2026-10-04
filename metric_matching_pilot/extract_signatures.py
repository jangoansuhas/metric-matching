#!/usr/bin/env python3
"""Conservative extractor for this pilot's simple SQLite CREATE VIEW/SELECT subset."""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VIEW = re.compile(r"\bCREATE\s+VIEW\s+(\w+)\s+AS\s+(SELECT\b.*?);", re.I | re.S)
SELECT = re.compile(
    r"^SELECT\s+(?P<key>.*?)\s+AS\s+entity_key\s*,\s*"
    r"(?P<measure>.*?)\s+AS\s+value\s+FROM\s+(?P<rest>.+)$", re.I | re.S)
SIMPLE_COLUMN = re.compile(r"^(?:(\w+)\.)?(\w+)$")
JOIN = re.compile(r"^JOIN\s+(\w+)\s+(\w+)\s+ON\s+((?:\w+\.)?\w+\s*=\s*(?:\w+\.)?\w+)\s*$", re.I)
FROM = re.compile(r"^(\w+)(?:\s+(\w+))?(?:\s+(JOIN\b.*))?$", re.I | re.S)


def compact(value):
    return " ".join(value.split())


def qualified(expr, aliases, primary):
    match = SIMPLE_COLUMN.fullmatch(expr.strip())
    if not match:
        raise ValueError(f"Unsupported column expression: {expr}")
    alias, column = match.groups()
    if alias and alias not in aliases:
        raise ValueError(f"Unresolved alias: {alias}")
    return f"{aliases[alias] if alias else primary}.{column}", column


def extract(name, sql):
    signature = {"view": name, "evidence_location": f"sql/metric_views.sql:{name}",
                 "status": "needs_review", "reason": [], "business_state": None,
                 "unit": None, "join_cardinality": None}
    match = SELECT.fullmatch(compact(sql))
    if not match:
        signature["reason"].append("Unsupported SELECT projection or nested expression")
        return signature

    rest = match["rest"]
    # The subset has at most one JOIN, a conjunction of simple WHERE clauses,
    # and one GROUP BY. No subqueries, CTEs, CASE, OR, or nested SELECT.
    if re.search(r"\b(OR|CASE|SELECT|UNION|HAVING|WINDOW)\b", rest, re.I):
        signature["reason"].append("Unsupported SQL construct")
        return signature
    chunks = re.split(r"\s+(WHERE|GROUP\s+BY)\s+", rest, flags=re.I)
    if len(chunks) not in (1, 3, 5):
        signature["reason"].append("Unsupported clause layout")
        return signature
    source = chunks[0]
    clauses = {}
    for i in range(1, len(chunks), 2):
        kind = compact(chunks[i]).upper()
        if kind in clauses:
            signature["reason"].append("Repeated clause")
            return signature
        clauses[kind] = chunks[i + 1].strip()
    if "GROUP BY" in clauses and not re.fullmatch(r"(?:\w+\.)?\w+", clauses["GROUP BY"]):
        signature["reason"].append("Unsupported group expression")
        return signature

    from_match = FROM.fullmatch(source)
    if not from_match:
        signature["reason"].append("Unsupported FROM/JOIN clause")
        return signature
    primary, alias, join_text = from_match.groups()
    if alias and alias.upper() == "JOIN":
        signature["reason"].append("Join must have an explicit source alias")
        return signature
    aliases = {alias or primary: primary}
    if join_text:
        joined = JOIN.fullmatch(join_text)
        if not joined:
            signature["reason"].append("Unsupported JOIN clause")
            return signature
        table, join_alias, predicate = joined.groups()
        aliases[join_alias] = table
        signature["join"] = {"table": table, "on": compact(predicate),
                             "cardinality": None}
    else:
        signature["join"] = None

    measure = match["measure"].strip()
    agg = re.fullmatch(r"(SUM|COUNT)\s*\(\s*(\*|(?:\w+\.)?\w+)\s*\)", measure, re.I)
    try:
        if agg:
            signature["aggregation"] = agg[1].upper()
            source_measure = (f"{primary}.*" if agg[2] == "*" else
                              qualified(agg[2], aliases, primary)[0])
        else:
            signature["aggregation"] = "PASSTHROUGH"
            source_measure = qualified(measure, aliases, primary)[0]
        signature["source_measure"] = source_measure
        key = match["key"].strip()
        signature["grain_key"] = ("global" if re.fullmatch(r"'[^']+'", key) else
                                  qualified(key, aliases, primary)[0])
        if "GROUP BY" in clauses and clauses["GROUP BY"] != key:
            raise ValueError("Projection and group key differ")
    except ValueError as exc:
        signature["reason"].append(str(exc))
        return signature

    where = clauses.get("WHERE", "")
    filters = [compact(c) for c in re.split(r"\s+AND\s+", where, flags=re.I) if c.strip()]
    signature["filters"] = filters
    snapshot = [m.group(1) for c in filters if (m := re.fullmatch(
        r"(?:\w+\.)?snapshot_date\s*=\s*'(\d{4}-\d{2}-\d{2})'", c, re.I))]
    signature["time_rule"] = f"snapshot_{snapshot[0]}" if len(snapshot) == 1 else None
    signature["status"] = "partial_signature"
    signature["reason"].extend(["Business state and unit require external metadata"])
    if signature["time_rule"] is None:
        signature["reason"].append("Snapshot or event-time rule unavailable from this SELECT")
    if signature["join"]:
        signature["reason"].append("Join cardinality not proven by SQL syntax")
    return signature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = (ROOT / "sql/metric_views.sql").read_text(encoding="utf-8")
    signatures = [extract(name, sql) for name, sql in VIEW.findall(source)]
    if not signatures:
        raise RuntimeError("No views found")
    (ROOT / "extracted_signatures.json").write_text(
        json.dumps(signatures, indent=2) + "\n", encoding="utf-8")
    if args.check:
        by_view = {s["view"]: s for s in signatures}
        a, b = by_view["opportunity_booking_arr_usd"], by_view["total_opportunity_booking_arr_usd"]
        assert a["source_measure"] == b["source_measure"] == "opportunity_snapshot.booking_arr_usd"
        assert a["filters"] == b["filters"] and a["time_rule"] == b["time_rule"]
        v0, v1 = by_view["pipeline_arr_v0"], by_view["pipeline_arr_v1"]
        assert v0["source_measure"] == v1["source_measure"]
        assert v0["filters"] != v1["filters"]
        assert by_view["crm_revenue_net_fanout"]["join"]["table"] == "account_hierarchy_bad"
        assert by_view["account_net_revenue"]["time_rule"] == by_view["crm_revenue_net_rollup"]["time_rule"]
        assert by_view["account_net_revenue_undocumented"]["time_rule"] == "snapshot_2026-09-26"
        assert by_view["product_booking_arr_usd"]["business_state"] is None
        assert by_view["product_booking_arr_usd"]["time_rule"] is None
        assert extract("unsupported_case", "SELECT 'all' AS entity_key, CASE WHEN x THEN 1 ELSE 0 END AS value FROM product")["status"] == "needs_review"
    print(f"Extracted {len(signatures)} partial signatures from fixture views"
          + ("; boundary checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
