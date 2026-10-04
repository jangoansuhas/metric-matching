#!/usr/bin/env python3
"""Aggressive, syntax-only I1 comparator for the fixed public Jaffle packet.

The pair decision uses only the two generated SQL statements and their scopes.
For two ungrouped queries, equality of the complete SQLGlot AST after cosmetic
output/relation alias normalization asserts ``direct_equivalent``. It does not
consult declared metric type, time semantics, source lineage, rows, or labels.
All other pairs abstain. This intentionally permissive prediction is distinct
from the guarded ast_mask_baseline.py and is not a proof of metric equivalence.

Run with sqlglot==30.20.0: python -B aggressive_ast_equivalence_baseline.py
Use --write-report to reproduce the Markdown report, or --check to verify it.
Only the pinned packet in this directory is read; only the named report is
written by --write-report. No held-out input is involved.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PACKET = HERE / "compiled_jaffle_i1_packet.json"
REPORT = HERE / "aggressive_ast_equivalence_report.md"
PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"
PAIR_SET_SHA256 = "0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0"
SOURCE_COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
SQLGLOT_PIN = "30.20.0"
DIALECT = "duckdb"
EVIDENCE_SCOPE = "ungrouped_scalar"
ASSERTION_SCOPE = "general_metric_substitution"

try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.optimizer.scope import traverse_scope
except ImportError:
    sqlglot = None
    exp = None
    traverse_scope = None


def load_packet() -> dict[str, Any]:
    raw = PACKET.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACKET_SHA256:
        raise ValueError("Pinned I1 packet bytes changed")
    packet = json.loads(raw)
    if (packet["packet_version"] != "compiled_jaffle_i1_packet_v2"
            or packet["source_commit"] != SOURCE_COMMIT
            or packet["pair_set_sha256"] != PAIR_SET_SHA256
            or packet["metric_count"] != 19 or packet["pair_count"] != 171):
        raise ValueError("Pinned packet identity or frame changed")
    cards, pairs = packet["cards"], packet["pairs"]
    ids = [card["metric_id"] for card in cards]
    if len(cards) != 19 or len(set(ids)) != 19 or len(pairs) != 171:
        raise ValueError("Expected 19 distinct metrics and 171 pairs")
    by_id = {card["metric_id"]: card for card in cards}
    for card in cards:
        sql = card["compiled_sql"]
        if (not isinstance(sql, str) or not sql
                or hashlib.sha256(sql.encode("utf-8")).hexdigest()
                != card["compiled_sql_sha256"]
                or card["sql_scope"] not in {"ungrouped", "metric_time"}):
            raise ValueError("Malformed generated SQL, hash, or scope")
    observed = set()
    for pair in pairs:
        a, b = pair["a"], pair["b"]
        if (a not in by_id or b not in by_id or a >= b
                or pair["pair_id"] != a + "||" + b):
            raise ValueError("Invalid pair ID")
        same_scope = by_id[a]["sql_scope"] == by_id[b]["sql_scope"]
        if (pair["scope_compatible"] is not same_scope
                or pair["target_scope"] != (by_id[a]["sql_scope"] if same_scope else None)):
            raise ValueError("Pair scope metadata disagrees with cards")
        observed.add((a, b))
    if observed != set(itertools.combinations(sorted(ids), 2)):
        raise ValueError("Pair frame is not the complete unordered set")
    return packet


def normalized_ast(sql: str) -> Any:
    """Compare full query structure, changing only cosmetic aliases.

    Relation aliases are alpha-renamed by bound scope and source order. The
    outer output alias is removed only where no outer clause could reference
    it. Nested projections, predicates, joins, grouping, windows, literals,
    CTEs, and physical table names remain in the AST.
    """
    statements = sqlglot.parse(sql, read=DIALECT, error_level="RAISE")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("expected one SELECT")
    tree = statements[0]
    if any(isinstance(n, (exp.Placeholder, exp.Command)) for n in tree.walk()):
        raise ValueError("unresolved SQL construct")
    for node in tree.walk():
        node.comments = None
    for scope in traverse_scope(tree):
        sources = scope.selected_sources
        aliases = {alias: f"__relation_{i}" for i, alias in enumerate(sources, 1)}
        for column in scope.columns:
            if column.table in aliases:
                column.set("table", exp.to_identifier(aliases[column.table]))
        for alias, (source_node, _) in sources.items():
            binding = source_node.parent if isinstance(source_node.parent, exp.Subquery) else source_node
            if not isinstance(binding, (exp.Table, exp.Subquery)):
                raise ValueError("unsupported relation binding")
            binding.set("alias", exp.TableAlias(this=exp.to_identifier(aliases[alias])))
    if not any(tree.args.get(k) for k in ("order", "group", "having", "qualify")):
        tree.set("expressions", [projection.unalias().copy() for projection in tree.expressions])
    return tree


def compare(a: dict[str, Any], b: dict[str, Any]) -> dict[str, str]:
    """Two-card decision; no packet, reference outcome, or time-rule lookup."""
    if a["sql_scope"] != b["sql_scope"]:
        return {"decision": "abstain", "reason": "incompatible_generated_scope"}
    if a["sql_scope"] != "ungrouped":
        return {"decision": "abstain", "reason": "outside_ungrouped_scope"}
    if sqlglot is None or sqlglot.__version__ != SQLGLOT_PIN:
        return {"decision": "abstain", "reason": "unsupported_parser"}
    try:
        left = normalized_ast(a["compiled_sql"])
        right = normalized_ast(b["compiled_sql"])
    except (ValueError, sqlglot.errors.SqlglotError):
        return {"decision": "abstain", "reason": "unsupported_ast"}
    if left == right:
        return {"decision": "direct_equivalent", "reason": "same_ungrouped_ast_modulo_alias"}
    return {"decision": "abstain", "reason": "different_ungrouped_ast"}


def run() -> dict[str, Any]:
    packet = load_packet()
    cards = {card["metric_id"]: card for card in packet["cards"]}
    rows = []
    for pair in packet["pairs"]:
        a, b = cards[pair["a"]], cards[pair["b"]]
        outcome = compare(a, b)
        rows.append({"pair_id": pair["pair_id"], **outcome,
                     "evidence_scope": EVIDENCE_SCOPE if a["sql_scope"] == b["sql_scope"] == "ungrouped" else None,
                     "assertion_scope": ASSERTION_SCOPE if outcome["decision"] == "direct_equivalent" else None})
    decisions = Counter(row["decision"] for row in rows)
    reasons = Counter(row["reason"] for row in rows)
    assert len(rows) == len({row["pair_id"] for row in rows}) == 171
    assert sum(decisions.values()) == sum(reasons.values()) == 171
    return {"packet_sha256": PACKET_SHA256, "pair_set_sha256": PAIR_SET_SHA256,
            "sqlglot_version": sqlglot.__version__ if sqlglot else None,
            "dialect": DIALECT, "denominator": 171,
            "rule_evidence_scope": EVIDENCE_SCOPE,
            "rule_assertion_scope": ASSERTION_SCOPE,
            "decisions": dict(sorted(decisions.items())),
            "reasons": dict(sorted(reasons.items())), "rows": rows}


def render_report(result: dict[str, Any]) -> str:
    if (result["sqlglot_version"] != SQLGLOT_PIN
            or result["decisions"] != {"abstain": 170, "direct_equivalent": 1}
            or result["reasons"] != {
                "different_ungrouped_ast": 152,
                "incompatible_generated_scope": 18,
                "same_ungrouped_ast_modulo_alias": 1,
            }):
        raise ValueError("Parser or expected pinned-packet output differs; no report written")
    positive = [row for row in result["rows"] if row["decision"] == "direct_equivalent"]
    assert [row["pair_id"] for row in positive] == [
        "metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue"]
    lines = [
        "# Aggressive AST equivalence on pinned Jaffle I1",
        "",
        "## Rule and input boundary",
        "",
        "The baseline compares the complete MetricFlow-generated DuckDB SQL AST for "
        "two **ungrouped** cards. It alpha-renames bound relation aliases and "
        "discards a cosmetic outer output alias, then asserts `direct_equivalent` "
        "as **general metric substitutability** from that ungrouped AST identity. "
        "The JSON records `evidence_scope=ungrouped_scalar` and "
        "`assertion_scope=general_metric_substitution`. It does not check "
        "declared cumulative type, time "
        "semantics, grouped queries, row results, or numeric eligibility. A "
        "different AST is an abstention, not a `non_match`. This deliberately "
        "permissive two-card method is independent of `ast_mask_baseline.py`.",
        "",
        f"Pinned public Jaffle commit `{SOURCE_COMMIT}`; packet SHA-256 "
        f"`{PACKET_SHA256}`; pair-set SHA-256 `{PAIR_SET_SHA256}`. "
        "The packet has 19 declared metrics and **all 171 unordered pairs**. "
        "Generated SQL covers 18 ungrouped metrics (153 common-scope pairs); "
        "the other metric has only a `metric_time` query (18 incompatible-scope "
        "pairs). SQLGlot `30.20.0`, DuckDB dialect. Packet and SQL hashes are "
        "checked before comparison. No held-out source or labels are read.",
        "",
        "## Full-frame results",
        "",
        "| Decision | Count / 171 | Reason |",
        "| --- | ---: | --- |",
        "| `direct_equivalent` | 1 | identical ungrouped AST modulo alias |",
        "| `abstain` | 152 | different ungrouped AST |",
        "| `abstain` | 18 | incompatible generated scopes |",
        "",
        "The sole asserted pair is "
        "`metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue`: "
        "`direct_equivalent` / `same_ungrouped_ast_modulo_alias`. The two "
        "ungrouped queries select `SUM(product_price)` from "
        '`"dev"."main"."order_items"`; only the output aliases differ. '
        "The **evidence** is limited to this ungrouped scalar; the deliberately "
        "broader assertion is a method prediction, not an all-grain proof.",
        "",
        "## Existing month-grouped counterexample",
        "",
        "The existing `experiment_cumulative_revenue_report.md` (SHA-256 "
        "`1ae15f4734134d4a60e10a59876a75fdbe45a4f4cab048f95902e3bbb64a988f`) "
        "records a separate bounded `metric_time__month` compilation and "
        "execution for 2024-09-01 through 2025-08-31 on reconstructed public "
        "seed relations. Both ungrouped queries returned $637,444.00 there. "
        "In October 2024, monthly `revenue` was $19,422.00 while "
        "MetricFlow `cumulative_revenue` was $15,670.00 (the running amount "
        "through October 1 under that query's `FIRST_VALUE` rule). The direct "
        "end-of-October control was $34,640.00. Thus the method's general "
        "substitution assertion is **conditionally refuted** for the month "
        "scope on that bounded reconstructed input. A claim explicitly limited "
        "to the ungrouped scalar is not refuted by a month result. The generated "
        "month SQL and execution are outside this "
        "baseline's decision inputs. The reconstruction was not a full dbt "
        "build, and this observation is **not an adjudicated gold label** or "
        "a measured error rate on 171 reference labels.",
        "",
        "## Exact pair outputs",
        "",
        "The following table includes every pair, including all 18 scope "
        "abstentions. IDs are the packet's exact lexical pair IDs.",
        "",
        "| Pair ID | Decision | Reason |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{row['pair_id']}` | `{row['decision']}` | `{row['reason']}` |"
                 for row in result["rows"])
    lines.extend([
        "",
        "## Reproduce",
        "",
        "From this directory, run "
        "`/workspace/scratch/e767b9d6f697/metric_matching_dev_build_20260928/venv/bin/python "
        "-B aggressive_ast_equivalence_baseline.py` for JSON with all 171 "
        "outputs; add `--check` to verify this Markdown byte for byte. "
        "`--write-report` writes only this report. With missing or differently "
        "versioned SQLGlot, same-scope pairs abstain and report generation "
        "fails closed. No other files are written.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write-report", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    if args.write_report:
        REPORT.write_text(render_report(result), encoding="utf-8")
    elif args.check:
        if REPORT.read_bytes() != render_report(result).encode("utf-8"):
            raise ValueError("Report differs from the pinned baseline output")
        print("OK: 171 pair outputs and report match")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
