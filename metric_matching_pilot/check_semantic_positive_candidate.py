#!/usr/bin/env python3
"""Execute POS-001's two source-defined measures through Sidemantic 0.8.2."""

import argparse
import importlib.metadata
import json
from decimal import Decimal
from pathlib import Path

from sidemantic import SemanticLayer, load_from_directory

from verify_public_positive_candidate import verify


ROOT = Path(__file__).resolve().parent
VERSION = "0.8.2"
QUERIES = {
    "orders.subtotal": "SELECT orders.ordered_at, orders.subtotal FROM orders ORDER BY orders.ordered_at",
    "order_items.revenue": "SELECT order_items.ordered_at, order_items.revenue FROM order_items ORDER BY order_items.ordered_at",
}


def run(repo):
    repo = repo.resolve()
    source = verify(repo)  # validates both pinned commits and the semantic definitions
    version = importlib.metadata.version("sidemantic")
    if version != VERSION:
        raise ValueError(f"This check was recorded with sidemantic {VERSION}; found {version}")
    database = repo / "jaffle_shop.duckdb"
    if not database.is_file():
        raise ValueError("Build the public dbt project into jaffle_shop.duckdb first")

    layer = SemanticLayer(connection=f"duckdb:///{database}")
    load_from_directory(layer, str(repo / "models"))
    values = {}
    compiled = {}
    for measure, query in QUERIES.items():
        model, field = measure.split(".")
        compiled[measure] = layer.compile(metrics=[measure], dimensions=[f"{model}.ordered_at"])
        if f"SUM({model}_cte.{field}_raw)" not in compiled[measure]:
            raise ValueError(f"Unexpected compiled aggregation for {measure}")
        rows = layer.sql(query).pl().to_dicts()
        by_day = {row["ordered_at"].date().isoformat(): row[field] for row in rows}
        if len(by_day) != len(rows) or any(value is None for value in by_day.values()):
            raise ValueError(f"Duplicate date or NULL daily measure in {measure}")
        values[measure] = by_day

    left, right = values.values()
    days = sorted(left.keys() | right.keys())
    mismatches = [day for day in days if left.get(day) != right.get(day)]
    result = {
        "candidate_id": "POS-001",
        "semantic_commit": source["semantic_commit"],
        "dbt_submodule_commit": source["dbt_submodule_commit"],
        "engine": "Sidemantic unified semantic layer importing MetricFlow and Cube definitions",
        "engine_version": version,
        "queries": QUERIES,
        "compiled_sql": compiled,
        "daily": {
            "dates_compared": len(days),
            "first_date": days[0], "last_date": days[-1],
            "dates_missing_from_either": sum(day not in left or day not in right for day in days),
            "dates_with_different_values": len(mismatches),
            "example_mismatched_dates": mismatches[:5],
            "orders_subtotal_dollars": str(sum(left.values(), Decimal(0))),
            "order_items_revenue_dollars": str(sum(right.values(), Decimal(0))),
        },
        "status": "observed_daily_equality_in_unified_engine_conditional_order_grain_not_gold",
        "limit": "Sidemantic imports both YAML formats into one engine; neither the native MetricFlow nor the native Cube service was run. At order grain 483 zero-item orders have NULL/absent item sums; equality requires an explicit left join and COALESCE. A finite demonstration sample cannot prove future or independent equivalence.",
    }
    return result


def markdown(result):
    d = result["daily"]
    return "\n".join([
        "# POS-001: Executed semantic measures by day", "",
        f"The two pre-existing public measures were imported from MetricFlow and Cube YAML into Sidemantic **{result['engine_version']}** and executed on the pinned dbt-built DuckDB tables. This check uses one unified semantic engine, not the native MetricFlow or Cube runtimes.", "",
        "| Comparison | Result |", "| --- | ---: |",
        f"| Compared dates | {d['dates_compared']} ({d['first_date']} through {d['last_date']}) |",
        f"| Dates absent from either measure | {d['dates_missing_from_either']} |",
        f"| Dates with differing values | {d['dates_with_different_values']} |",
        f"| Sum of `orders.subtotal` daily values | ${d['orders_subtotal_dollars']} |",
        f"| Sum of `order_items.revenue` daily values | ${d['order_items_revenue_dollars']} |", "",
        "The compiler generates `SUM(subtotal)` over `main.orders` and `SUM(product_price)` over `main.order_items`, both grouped by `DATE_TRUNC('DAY', ordered_at)`. The complete generated SQL and source queries are in `public_positive_semantic_check.json`.", "",
        "**Scope.** Agreement is empirical at aligned **daily** grain in this curated sample. It does not establish interchangeability at order grain: 483 orders have no items and an unfilled item sum is NULL, although the order subtotal is zero. The separate null-aware dbt check documents this difference. Sidemantic translates both YAML formats; native MetricFlow and Cube execution and independent gold annotation remain open.", "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run(args.repo)
    daily = result["daily"]
    if args.check:
        assert daily["dates_compared"] == 365
        assert daily["dates_missing_from_either"] == daily["dates_with_different_values"] == 0
        assert daily["orders_subtotal_dollars"] == daily["order_items_revenue_dollars"] == "637444.00"
    (ROOT / "public_positive_semantic_check.json").write_text(json.dumps(result, indent=2) + "\n")
    (ROOT / "public_positive_semantic_check.md").write_text(markdown(result))
    print(f"Sidemantic {result['engine_version']}: {daily['dates_compared']} dates, "
          f"{daily['dates_with_different_values']} differences, "
          f"${daily['orders_subtotal_dollars']} each"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
