#!/usr/bin/env python3
"""Check materialized DuckDB tables and dbt test evidence for POS-001."""

import argparse
import json
from pathlib import Path

import duckdb

from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent
SEMANTIC_COMMIT = "8686fe3ea0fd4ceffa08e523a422331bd228ac32"
DBT_COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"


def count(conn, query):
    return conn.execute(query).fetchone()[0]


def check(repo):
    repo = repo.resolve()
    dbt_repo = repo / "jaffle-shop"
    if repository_commit(repo) != SEMANTIC_COMMIT or repository_commit(dbt_repo) != DBT_COMMIT:
        raise ValueError("Pinned repository revision changed")
    db_file = repo / "jaffle_shop.duckdb"
    result_file = dbt_repo / "target/run_results.json"
    if not db_file.is_file() or not result_file.is_file():
        raise ValueError("Missing local dbt DuckDB build or run-results artifact")
    results = json.loads(result_file.read_text(encoding="utf-8"))
    target_tests = [entry for entry in results["results"]
                    if "dbt_utils_expression_is_true_orders_order_items_subtotal_subtotal" in entry["unique_id"]]
    if len(target_tests) != 1 or target_tests[0]["status"] != "pass":
        raise ValueError("The dbt subtotal equality test did not pass exactly once")
    predicate = "where not(order_items_subtotal = subtotal)"
    compiled_matches = [path for path in (dbt_repo / "target/compiled").rglob("*.sql")
                        if predicate in " ".join(path.read_text(encoding="utf-8").lower().split())]
    if len(compiled_matches) != 1:
        raise ValueError("Could not identify exactly one compiled dbt test predicate")

    conn = duckdb.connect(str(db_file), read_only=True)
    try:
        base = """FROM main.orders o LEFT JOIN
                  (SELECT order_id, SUM(product_price) item_sum FROM main.order_items GROUP BY order_id) i
                  ON i.order_id = o.order_id"""
        order_mismatch = count(conn, f"SELECT COUNT(*) {base} WHERE o.subtotal IS DISTINCT FROM i.item_sum")
        missing_item_order = count(conn, f"SELECT COUNT(*) {base} WHERE i.order_id IS NULL")
        coalesced_mismatch = count(conn, f"SELECT COUNT(*) {base} WHERE o.subtotal IS DISTINCT FROM COALESCE(i.item_sum, 0)")
        model_mismatch = count(conn, "SELECT COUNT(*) FROM main.orders WHERE subtotal IS DISTINCT FROM order_items_subtotal")
        daily_mismatch = count(conn, """SELECT COUNT(*) FROM
          (SELECT ordered_at, SUM(subtotal) total_value FROM main.orders GROUP BY 1) o
          FULL OUTER JOIN
          (SELECT ordered_at, SUM(product_price) total_value FROM main.order_items GROUP BY 1) i
          USING (ordered_at) WHERE o.total_value IS DISTINCT FROM i.total_value""")
        summary = {"orders": count(conn, "SELECT COUNT(*) FROM main.orders"),
                   "items": count(conn, "SELECT COUNT(*) FROM main.order_items"),
                   "dates": count(conn, "SELECT COUNT(DISTINCT ordered_at) FROM main.orders"),
                   "order_total": str(conn.execute("SELECT SUM(subtotal) FROM main.orders").fetchone()[0]),
                   "item_total": str(conn.execute("SELECT SUM(product_price) FROM main.order_items").fetchone()[0]),
                   "orders_without_items": missing_item_order,
                   "orders_mismatching_before_coalesce": order_mismatch,
                   "orders_mismatching_after_coalesce": coalesced_mismatch,
                   "orders_mismatching_materialized_item_sum": model_mismatch,
                   "daily_mismatches": daily_mismatch}
    finally:
        conn.close()
    return {"candidate_id": "POS-001", "semantic_commit": SEMANTIC_COMMIT,
            "dbt_submodule_commit": DBT_COMMIT,
            "dbt_version": results["metadata"].get("dbt_version"),
            "dbt_build_total_nodes": len(results["results"]),
            "dbt_declared_equality_test": {"unique_id": target_tests[0]["unique_id"],
                                            "status": target_tests[0]["status"],
                                            "failures": target_tests[0].get("failures")},
            "compiled_test_predicate": predicate,
            "duckdb": summary,
            "status": "dbt_build_exposes_483_null_vs_zero_cases_semantic_engines_unverified",
            "inference": "The declared dbt expression test passes while 483 zero-subtotal orders have NULL item sums: SQL WHERE NOT(NULL = 0) filters them out. Use IS DISTINCT FROM or an explicit null-aware test. Conditional order-level equality requires a left join plus COALESCE; aligned daily totals match in the built sample."}


def markdown(report):
    s = report["duckdb"]
    return "\n".join(["# POS-001: Materialized dbt check", "",
        f"The public Jaffle Shop submodule at `{report['dbt_submodule_commit']}` was built locally with dbt {report['dbt_version']} and DuckDB. The declared `order_items_subtotal = subtotal` dbt test reports `{report['dbt_declared_equality_test']['status']}` with {report['dbt_declared_equality_test']['failures']} failures, but its compiled SQL uses `{report['compiled_test_predicate']}`.", "",
        "| Built table comparison | Observed |", "| --- | ---: |",
        f"| Orders / items | {s['orders']:,} / {s['items']:,} |",
        f"| Order subtotal / item price total (dollars) | {s['order_total']} / {s['item_total']} |",
        f"| Orders with no items | {s['orders_without_items']:,} |",
        f"| Order-level NULL-aware mismatches before COALESCE | {s['orders_mismatching_before_coalesce']:,} |",
        f"| Order-level mismatches after COALESCE | {s['orders_mismatching_after_coalesce']:,} |",
        f"| Materialized order_items_subtotal versus subtotal NULL-aware mismatches | {s['orders_mismatching_materialized_item_sum']:,} |",
        f"| Dates with different daily totals | {s['daily_mismatches']} of {s['dates']} |", "",
        "The ordinary dbt test misses 483 NULL-versus-zero discrepancies because SQL `NOT(NULL = 0)` is NULL and a WHERE clause discards it. A null-aware predicate such as `subtotal IS DISTINCT FROM order_items_subtotal` detects them. This does not affect all-time or aligned daily totals in the built sample. It limits any order-grain equivalence claim unless the item side is outer-joined and COALESCEd to zero.", "",
        "This section checks built dbt tables, not native MetricFlow or Cube runtimes. The companion Sidemantic check translates and queries both definitions through one engine; neither check produces a gold benchmark label.", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = check(args.repo)
    if args.check:
        s = result["duckdb"]
        assert (s["orders"], s["items"], s["dates"]) == (61948, 90900, 365)
        assert s["orders_without_items"] == s["orders_mismatching_before_coalesce"] == 483
        assert s["orders_mismatching_after_coalesce"] == s["daily_mismatches"] == 0
        assert s["orders_mismatching_materialized_item_sum"] == 483
        assert s["order_total"] == s["item_total"]
    (ROOT / "public_positive_built_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_positive_built_check.md").write_text(markdown(result), encoding="utf-8")
    print(f"dbt test {result['dbt_declared_equality_test']['status']}; null-aware order mismatches "
          f"{result['duckdb']['orders_mismatching_before_coalesce']}; daily differences "
          f"{result['duckdb']['daily_mismatches']}"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
