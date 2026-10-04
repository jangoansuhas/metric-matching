#!/usr/bin/env python3
"""Bounded, development-only CREATE VIEW aggregate inventory.

Requires sqlglot==30.20.0. This is source syntax evidence, not a compiled dbt
adapter, equivalence proof, or held-out evaluator. Only the selected SQL file is
read; default output is the two adjacent generic_sql_inventory_report files.
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

import sqlglot
from sqlglot import exp


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "sql" / "metric_views.sql"
FIXTURE = HERE / "generic_sql_fixture_negative.sql"
JSON_OUT = HERE / "generic_sql_inventory_report.json"
MD_OUT = HERE / "generic_sql_inventory_report.md"
PIN = "30.20.0"
DIALECT = "duckdb"
AGGREGATES = (exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max, exp.Median)
UNKNOWN = {key: "unknown" for key in
           ("grain", "time", "null_policy", "join_cardinality", "snapshot")}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(node: exp.Expression | None) -> str | None:
    return node.sql(dialect=DIALECT) if node is not None else None


def statements_with_lines(source: str) -> list[tuple[str, int]]:
    """Split on SQLGlot semicolon tokens, preserving exact source offsets."""
    tokens = sqlglot.Tokenizer(dialect=DIALECT).tokenize(source)
    chunks = []
    start = 0
    for token in tokens:
        if token.token_type.name == "SEMICOLON":
            chunk = source[start:token.end + 1]
            if chunk.strip():
                chunks.append((chunk, source.count("\n", 0, start) + 1))
            start = token.end + 1
    if source[start:].strip():
        chunks.append((source[start:], source.count("\n", 0, start) + 1))
    return chunks


def aliases_and_lines(chunk: str, base_line: int, query: exp.Select | None) -> list[tuple[str, int]]:
    if query is None:
        # Do not guess output aliases from unparseable SQL: `CAST(x AS DECIMAL)`
        # would otherwise create a spurious DECIMAL projection. A view-level
        # unresolved placeholder is emitted by inventory() instead.
        return []
    result = []
    cursor = 0
    for index, projection in enumerate(query.expressions):
        alias = projection.alias or f"_output_{index + 1}"
        pattern = re.compile(r"\bAS\s+" + re.escape(alias) + r"\b", re.I)
        match = pattern.search(chunk, cursor)
        if match:
            cursor = match.end()
            line = base_line + chunk.count("\n", 0, match.start())
        else:
            line = base_line + chunk.count("\n", 0, cursor)
        result.append((alias, line))
    return result


def source_tables(query: exp.Select) -> list[str]:
    return sorted({canonical(table.this) for table in query.find_all(exp.Table)})


def blockers(query: exp.Select, projection: exp.Expression) -> list[str]:
    reasons = []
    if query.find(exp.Join):
        reasons.append("join")
    if query.find(exp.With):
        reasons.append("cte")
    if query.find(exp.Window) or projection.find(exp.Window):
        reasons.append("window")
    if query.find(exp.Subquery) or query.find(exp.Union):
        reasons.append("nested_query")
    if query.find(exp.Anonymous):
        reasons.append("unknown_function")
    return reasons


def inventory(source: str, source_path: str) -> dict:
    if sqlglot.__version__ != PIN:
        raise RuntimeError(f"Requires sqlglot=={PIN}; found {sqlglot.__version__}")
    views = []
    outputs = []
    for chunk, base_line in statements_with_lines(source):
        view_match = re.search(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([\w.]+)", chunk, re.I)
        name = view_match.group(1) if view_match else f"_unparsed_statement_{len(views) + 1}"
        view_line = base_line + chunk.count("\n", 0, view_match.start()) if view_match else base_line
        error = None
        statement = None
        query = None
        if re.search(r"\{[{%#]|[%#}]\}", chunk):
            error = "unsupported_jinja"
        else:
            try:
                parsed = sqlglot.parse(chunk, read=DIALECT, error_level="RAISE")
                if len(parsed) != 1 or not isinstance(parsed[0], exp.Create) or parsed[0].args.get("kind") != "VIEW":
                    error = "unsupported_statement"
                elif not isinstance(parsed[0].expression, exp.Select):
                    error = "unsupported_query_shape"
                else:
                    statement = parsed[0]
                    query = statement.expression
            except (sqlglot.errors.SqlglotError, ValueError) as exc:
                error = f"parse_error:{type(exc).__name__}"
        view = {"name": name, "line": view_line, "statement_sha256": digest(chunk.encode()),
                "status": "parsed" if error is None else error}
        views.append(view)
        locations = aliases_and_lines(chunk, base_line, query)
        unresolved_projection = False
        if not locations:
            # Reserve one abstaining ID so the failed statement participates in
            # the pair universe. Its true projection count is still unknown.
            view["status"] = error or "no_projected_outputs"
            view["output_recovery"] = "placeholder_for_unresolved_projection"
            select_match = re.search(r"\bSELECT\b", chunk, re.I)
            line = base_line + chunk.count("\n", 0, select_match.start()) if select_match else view_line
            locations = [("_unresolved_output_1", line)]
            unresolved_projection = True
        tables = source_tables(query) if query is not None else []
        where = canonical(query.args.get("where").this) if query is not None and query.args.get("where") else None
        group = [canonical(x) for x in query.args.get("group").expressions] if query is not None and query.args.get("group") else []
        for i, (alias, line) in enumerate(locations):
            projection = query.expressions[i] if query is not None else None
            value = projection.this if isinstance(projection, exp.Alias) else projection
            aggregate = value if isinstance(value, AGGREGATES) else None
            nested_aggregate = value.find(*AGGREGATES) if value is not None and aggregate is None else None
            reasons = [error] if error else blockers(query, projection)
            if unresolved_projection:
                reasons.append("unresolved_projection")
            if nested_aggregate is not None:
                reasons.append("non_direct_aggregate_expression")
            if value is not None and value.find(exp.Window) and "window" not in reasons:
                reasons.append("window")
            if aggregate is None and not reasons:
                reasons.append("non_aggregate")
            operator = aggregate.key.upper() if aggregate is not None else None
            item = {
                "id": f"{name}.{alias}", "view": name, "output_alias": alias,
                "source_file": source_path, "source_line": line,
                "expression": canonical(value),
                "expression_sha256": digest(canonical(value).encode()) if value is not None else None,
                "expression_ast": type(value).__name__ if value is not None else None,
                "ast_operator": operator,
                "aggregate_argument": canonical(aggregate.this) if aggregate is not None else None,
                "aggregate_argument_ast": type(aggregate.this).__name__ if aggregate is not None else None,
                "source_table_refs": tables, "where": where, "group_by": group,
                "status": "supported_aggregate" if aggregate is not None and not reasons else "abstain",
                "failure_reasons": sorted(set(reasons)), "unknown_semantics": dict(UNKNOWN),
            }
            outputs.append(item)
    if len({x["id"] for x in outputs}) != len(outputs):
        raise ValueError("Duplicate view/output IDs")
    pairs = []
    for left, right in itertools.combinations(sorted(outputs, key=lambda x: x["id"]), 2):
        if left["status"] != "supported_aggregate" or right["status"] != "supported_aggregate":
            reason = "unsupported_output"
            decision = "abstain"
        else:
            checks = (("ast_operator", "different_operator"),
                      ("source_table_refs", "different_source_tables"),
                      ("aggregate_argument", "different_argument"),
                      ("where", "different_where"), ("group_by", "different_group_by"))
            reason = next((label for field, label in checks if left[field] != right[field]),
                          "same_source_signature")
            decision = "source_candidate" if reason == "same_source_signature" else "source_difference"
        pairs.append({"left_id": left["id"], "right_id": right["id"],
                      "decision": decision, "reason": reason})
    return {
        "schema_version": 1, "scope": "development_only_generic_create_view_source_inventory",
        "parser": {"package": "sqlglot", "version": PIN, "dialect": DIALECT},
        "input": {"path": source_path, "sha256": digest(source.encode())},
        "coverage": {"views": len(views), "outputs": len(outputs), "unordered_pairs": len(pairs),
                     "unresolved_output_placeholders": sum(x["output_alias"].startswith("_unresolved_output_") for x in outputs),
                     "supported_aggregate_outputs": sum(x["status"] == "supported_aggregate" for x in outputs),
                     "recognized_aggregate_outputs": sum(x["ast_operator"] is not None for x in outputs),
                     "output_failure_reasons": dict(sorted(Counter(r for x in outputs for r in x["failure_reasons"]).items())),
                     "pair_decisions": dict(sorted(Counter(x["decision"] for x in pairs).items())),
                     "pair_reasons": dict(sorted(Counter(x["reason"] for x in pairs).items()))},
        "views": views, "outputs": outputs, "pairs": pairs,
        "limitations": ["Source syntax only; no compiled dbt or dependency expansion.",
                        "Same source signature is a review candidate, not value equivalence.",
                        "A source difference is not a semantic contradiction; transformations may reconcile outputs.",
                        "Grain, time, NULL policy, join cardinality and snapshot are unknown.",
                        "Joins, CTEs, windows, nested queries and Jinja abstain.",
                        "Unparseable views receive one abstaining placeholder rather than guessed aliases; their true projection count remains unknown.",
                        "Pair completeness is over emitted output IDs, including placeholders; unknown projection arity cannot be inferred."],
    }


def fixture_evidence(report: dict) -> None:
    raw = FIXTURE.read_text(encoding="utf-8")
    fixture = inventory(raw, FIXTURE.relative_to(HERE).as_posix())
    by_id = {x["id"]: x for x in fixture["outputs"]}
    by_pair = {frozenset((x["left_id"], x["right_id"])): x for x in fixture["pairs"]}
    cases = []
    for a, b in (("sum_orders.value", "median_orders.value"),
                 ("count_orders.value", "count_customers.value"),
                 ("sum_orders.value", "sum_orders_coalesced.value")):
        pair = by_pair[frozenset((a, b))]
        cases.append({
            "left_id": a, "right_id": b, "decision": pair["decision"], "reason": pair["reason"],
            "left_expression": by_id[a]["expression"], "right_expression": by_id[b]["expression"],
            "left_expression_ast": by_id[a]["expression_ast"],
            "right_expression_ast": by_id[b]["expression_ast"],
            "left_argument_ast": by_id[a]["aggregate_argument_ast"],
            "right_argument_ast": by_id[b]["aggregate_argument_ast"],
            "left_null_policy": by_id[a]["unknown_semantics"]["null_policy"],
            "right_null_policy": by_id[b]["unknown_semantics"]["null_policy"],
        })
    report["negative_fixture"] = {
        "path": fixture["input"]["path"], "sha256": fixture["input"]["sha256"],
        "coverage": fixture["coverage"], "cases": cases,
        "unsupported_examples": [{"id": by_id[i]["id"], "failure_reasons": by_id[i]["failure_reasons"]}
                                 for i in ("joined_orders.value", "templated_orders._unresolved_output_1",
                                           "templated_aliasless._unresolved_output_1")],
        "interpretation": "AST differences are source evidence only; NULL behavior and value equivalence are not inferred.",
    }


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# Generic SQL aggregate inventory (development only)", "",
             f"Input: `{report['input']['path']}` (SHA256 `{report['input']['sha256']}`).", "",
             f"Parser: sqlglot {PIN}, `{DIALECT}` dialect. Views: {c['views']}; projected outputs: {c['outputs']}; complete unordered pairs: {c['unordered_pairs']}.",
             f"Recognized aggregate outputs: {c['recognized_aggregate_outputs']}; supported aggregate outputs: {c['supported_aggregate_outputs']}; unresolved placeholders: {c['unresolved_output_placeholders']}.", "",
             "## Coverage", "", "| Item | Count |", "| --- | ---: |"]
    for name, count in c["output_failure_reasons"].items():
        lines.append(f"| Output reason: `{name}` | {count} |")
    for name, count in c["pair_reasons"].items():
        lines.append(f"| Pair reason: `{name}` | {count} |")
    lines += ["", "## Aggregate outputs", "", "| Output | Line | Operator | Sources | Status / reason |",
              "| --- | ---: | --- | --- | --- |"]
    for x in report["outputs"]:
        if x["ast_operator"]:
            lines.append(f"| `{x['id']}` | {x['source_line']} | {x['ast_operator']} | `{', '.join(x['source_table_refs'])}` | {x['status']}; {', '.join(x['failure_reasons']) or 'none'} |")
    lines += ["", "## Source comparison examples", ""]
    for p in report["pairs"]:
        if p["reason"] == "same_source_signature" or ("number_of_customers.value" in (p["left_id"], p["right_id"]) and "num_of_products.value" in (p["left_id"], p["right_id"])):
            lines.append(f"- `{p['left_id']}` / `{p['right_id']}`: {p['decision']} ({p['reason']}).")
    if "negative_fixture" in report:
        fixture = report["negative_fixture"]
        lines += ["", "## Synthetic negative fixture", "",
                  f"`{fixture['path']}` (SHA256 `{fixture['sha256']}`).",
                  "", "| Pair | Expression AST and argument AST | Decision / reason | NULL policy |",
                  "| --- | --- | --- | --- |"]
        for x in fixture["cases"]:
            ast = (f"`{x['left_expression']}` ({x['left_expression_ast']} / {x['left_argument_ast']}) vs "
                   f"`{x['right_expression']}` ({x['right_expression_ast']} / {x['right_argument_ast']})")
            lines.append(f"| `{x['left_id']}` / `{x['right_id']}` | {ast} | {x['decision']}; {x['reason']} | {x['left_null_policy']} / {x['right_null_policy']} |")
        lines += ["", fixture["interpretation"]]
        lines += ["", f"Fixture inventory: {fixture['coverage']['views']} views, {fixture['coverage']['outputs']} emitted outputs, {fixture['coverage']['unordered_pairs']} unordered pairs, including {fixture['coverage']['unresolved_output_placeholders']} unresolved placeholders."]
        for example in fixture["unsupported_examples"]:
            lines.append(f"- `{example['id']}`: abstain ({', '.join(example['failure_reasons'])}).")
    lines += ["", "## Limits", ""]
    lines += [f"- {limit}" for limit in report["limitations"]]
    lines += ["", "`python generic_sql_inventory.py --check` verifies both report bytes without writing files.",
              "`python generic_sql_inventory.py --input generic_sql_fixture_negative.sql --stdout` inspects the synthetic counterfactual without writing files.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--check", action="store_true", help="compare generated bytes to reports; write nothing")
    parser.add_argument("--stdout", action="store_true", help="print JSON; write nothing")
    args = parser.parse_args()
    if args.check and args.stdout:
        parser.error("--check and --stdout are mutually exclusive")
    if args.input.resolve() != DEFAULT_INPUT.resolve() and not args.stdout:
        parser.error("alternate input requires --stdout")
    source = args.input.read_text(encoding="utf-8")
    try:
        path = args.input.resolve().relative_to(HERE).as_posix()
    except ValueError:
        parser.error("input must be within metric_matching_pilot")
    report = inventory(source, path)
    if args.input.resolve() == DEFAULT_INPUT.resolve():
        fixture_evidence(report)
    js = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode()
    md = markdown(report).encode()
    if args.stdout:
        sys.stdout.buffer.write(js)
    elif args.check:
        for target, expected in ((JSON_OUT, js), (MD_OUT, md)):
            if not target.exists() or target.read_bytes() != expected:
                print(f"MISMATCH: {target}", file=sys.stderr)
                return 1
        print("OK: both report files match regenerated bytes")
    else:
        JSON_OUT.write_bytes(js)
        MD_OUT.write_bytes(md)
        print(f"Wrote {JSON_OUT} and {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
