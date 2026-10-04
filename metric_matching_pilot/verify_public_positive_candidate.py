#!/usr/bin/env python3
"""Check a public cross-grain candidate at pinned semantic and dbt revisions."""

import argparse
import csv
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent
SEMANTIC_COMMIT = "8686fe3ea0fd4ceffa08e523a422331bd228ac32"
DBT_COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def anchor(repo, relative, snippet):
    lines = (repo / relative).read_text(encoding="utf-8").splitlines()
    hits = [number for number, line in enumerate(lines, 1) if snippet in line]
    if not hits:
        raise ValueError(f"Missing expected source evidence: {relative} / {snippet}")
    return {"path": relative, "line": hits[0], "snippet": snippet}


def verify(repo):
    repo = repo.resolve()
    dbt_repo = repo / "jaffle-shop"
    if repository_commit(repo) != SEMANTIC_COMMIT or repository_commit(dbt_repo) != DBT_COMMIT:
        raise ValueError("Wrong semantic or dbt project revision")
    entry = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "HEAD", "jaffle-shop"], text=True)
    if f"commit {DBT_COMMIT}\tjaffle-shop" not in entry:
        raise ValueError("Submodule pin does not match the checked-out dbt project")

    mf = yaml.safe_load((repo / "models/metricflow/orders.yml").read_text(encoding="utf-8"))
    order_model = next(model for model in mf["semantic_models"] if model["name"] == "orders")
    subtotal = next(measure for measure in order_model["measures"] if measure["name"] == "subtotal")
    cube = yaml.safe_load((repo / "models/cube/order_items.yml").read_text(encoding="utf-8"))
    item_model = next(model for model in cube["cubes"] if model["name"] == "order_items")
    revenue = next(measure for measure in item_model["measures"] if measure["name"] == "revenue")
    item_time = next(d for d in item_model["dimensions"] if d["name"] == "ordered_at")
    item_join = next(join for join in item_model["joins"] if join["name"] == "orders")
    if (subtotal["agg"], subtotal["expr"], order_model["defaults"]["agg_time_dimension"]) != (
        "sum", "subtotal", "ordered_at"
    ) or (revenue["type"], revenue["sql"], item_time["type"]) != (
        "sum", "product_price", "time"
    ) or item_model["sql_table"] != "main.order_items":
        raise ValueError("Semantic measure, source table, or time definitions changed")
    if item_join["relationship"] != "many_to_one" or "order_id" not in item_join["sql"]:
        raise ValueError("Declared item-to-order relationship changed")

    evidence = []
    for base, path, snippets in [
        (repo, "models/metricflow/orders.yml", ["agg_time_dimension: ordered_at", "name: subtotal", "expr: subtotal"]),
        (repo, "models/cube/order_items.yml", ["sql_table: main.order_items", "name: revenue", "sql: product_price", "relationship: many_to_one"]),
        (dbt_repo, "models/marts/orders.sql", ["sum(product_price) as order_items_subtotal", "order_items_summary.order_items_subtotal"]),
        (dbt_repo, "models/marts/order_items.sql", ["orders.ordered_at", "products.product_price", "left join orders on order_items.order_id = orders.order_id", "left join products on order_items.product_id = products.product_id"]),
        (dbt_repo, "models/marts/orders.yml", ["order_items_subtotal = subtotal"]),
        (dbt_repo, "models/staging/stg_orders.sql", ["cents_to_dollars('subtotal')", "as ordered_at"]),
        (dbt_repo, "models/staging/stg_products.sql", ["cents_to_dollars('price')"]),
        (dbt_repo, "macros/cents_to_dollars.sql", ["default__cents_to_dollars", "100)::numeric(16, 2)"])
    ]:
        for snippet in snippets:
            evidence.append({"repository": "semantic" if base == repo else "dbt",
                             **anchor(base, path, snippet)})

    seed = dbt_repo / "seeds/jaffle-data"
    raw_orders = rows(seed / "raw_orders.csv")
    raw_items = rows(seed / "raw_items.csv")
    raw_products = rows(seed / "raw_products.csv")
    products = {row["sku"]: int(row["price"]) for row in raw_products}
    orders = {row["id"]: row for row in raw_orders}
    item_ids = {row["id"] for row in raw_items}
    duplicate_counts = {"order_ids": len(raw_orders) - len(orders),
                        "item_ids": len(raw_items) - len(item_ids),
                        "product_skus": len(raw_products) - len(products)}
    if any(duplicate_counts.values()):
        raise ValueError(f"Duplicate raw keys: {duplicate_counts}")
    per_order = defaultdict(int)
    missing_product = missing_order = 0
    for item in raw_items:
        if item["sku"] not in products:
            missing_product += 1
        elif item["order_id"] not in orders:
            missing_order += 1
        else:
            per_order[item["order_id"]] += products[item["sku"]]
    if missing_product or missing_order:
        raise ValueError("Some items lack products or orders")
    no_item_orders = [order_id for order_id in orders if order_id not in per_order]
    bad_orders_without_coalesce = [order_id for order_id, row in orders.items()
                                   if per_order.get(order_id) != int(row["subtotal"])]
    bad_orders_with_coalesce = [order_id for order_id, row in orders.items()
                                if per_order.get(order_id, 0) != int(row["subtotal"])]
    order_day, item_day = Counter(), Counter()
    for order_id, row in orders.items():
        day = row["ordered_at"][:10]
        order_day[day] += int(row["subtotal"])
        item_day[day] += per_order.get(order_id, 0)
    days = set(order_day) | set(item_day)
    daily_mismatches = [day for day in days if order_day[day] != item_day[day]]
    total = sum(order_day.values())
    return {
        "candidate_id": "POS-001", "corpus": "sidequery/jaffle-shop-sidemantic",
        "semantic_commit": SEMANTIC_COMMIT, "dbt_submodule_commit": DBT_COMMIT,
        "pair": ["orders.subtotal (MetricFlow measure, order grain)",
                 "order_items.revenue (Cube measure, item grain)"],
        "time_rule": "MetricFlow defaults to ordered_at at day grain; Cube exposes ordered_at as a time dimension inherited from the order join and must be explicitly grouped by that day",
        "transformation": "For order-level equivalence, LEFT JOIN each order to SUM(item.product_price) GROUP BY item.order_id, COALESCE missing item sums to 0, and compare with order.subtotal; for daily totals, sum each measure by the aligned orders.ordered_at date",
        "sample": {"orders": len(raw_orders), "items": len(raw_items), "products": len(raw_products),
                   "orders_without_items": len(no_item_orders),
                   "orders_with_null_sensitive_item_subtotal_mismatch": len(bad_orders_without_coalesce),
                   "orders_with_coalesced_item_subtotal_mismatch": len(bad_orders_with_coalesce),
                   "dates_compared": len(days), "dates_with_different_values": len(daily_mismatches),
                   "sum_order_subtotal_cents": total,
                   "sum_item_price_cents": sum(per_order.values()),
                   "missing_order_items": missing_order, "missing_product_items": missing_product,
                   "duplicate_keys": duplicate_counts},
        "source_evidence": evidence,
        "status": "conditional_cross_grain_candidate_daily_equality_order_equality_requires_coalesce_not_gold",
        "limits": ["This raw-seed stage reads the YAML definitions without executing them; the companion Sidemantic check runs both measures through one translating engine, not the two native runtimes.",
                   "Orders with no items have subtotal 0 but no grouped item row; SUM(item.price) is NULL until an outer join and COALESCE are applied.",
                   "The declared dbt equality test uses ordinary SQL equality and can pass NULL comparisons; the companion materialized check demonstrates this, so a null-aware test is required.",
                   "This source-only check does not compile the adapter-dispatched currency macro; see the companion materialized dbt check.",
                   "Finite rows and declared joins cannot prove cardinality for future or unseen data.",
                   "The repo is an intentionally curated Jaffle Shop demonstration, not independent industrial duplication."]}


def markdown(result):
    s = result["sample"]
    lines = ["# POS-001: Conditional public cross-grain candidate", "",
             f"Source: `sidequery/jaffle-shop-sidemantic@{result['semantic_commit']}` with dbt Labs Jaffle Shop submodule `{result['dbt_submodule_commit']}`. Both measure definitions already exist in this public demonstration repository; neither was added by this pilot.", "",
             "| Property | orders.subtotal | order_items.revenue |", "| --- | --- | --- |",
             "| Semantic format | MetricFlow | Cube |", "| Native grain | One order | One order item |",
             "| Aggregation and field | SUM(subtotal) | SUM(product_price) |",
             "| Aligned time | ordered_at (default, day) | ordered_at (explicit time dimension from joined order) |", "",
             f"**Explicit mapping.** {result['transformation']}. The item-to-order relationship is declared `many_to_one`. The order model builds `order_items_subtotal` by summing item `product_price` grouped by `order_id`, and its YAML declares an equality test to order `subtotal`.", "",
             f"**Pinned raw-seed check.** {s['orders']:,} orders, {s['items']:,} items, {s['products']} products. {s['orders_without_items']} orders have no items, giving NULL/absent item groups versus a zero subtotal. Consequently {s['orders_with_null_sensitive_item_subtotal_mismatch']} orders differ before null handling and {s['orders_with_coalesced_item_subtotal_mismatch']} differ after an outer join and COALESCE. Both all-time totals equal {s['sum_order_subtotal_cents']:,} cents; daily sums agree on all {s['dates_compared']} dates ({s['dates_with_different_values']} mismatches). No item mapping or key-uniqueness failures were found.", "",
             "**Status.** Conditional cross-grain candidate: matching daily totals on the pinned data, with order-level equality only after an explicit outer join and COALESCE. This raw-row calculation is supplemented by `public_positive_built_check.md` for materialized dbt tables and `public_positive_semantic_check.md` for execution of both measures through Sidemantic. This curated demonstration shares Jaffle Shop data and cannot alone establish performance on independent repositories or industrial metrics.", "",
             "## Pinned source locations", ""]
    for item in result["source_evidence"]:
        repo = ("sidequery/jaffle-shop-sidemantic" if item["repository"] == "semantic"
                else "dbt-labs/jaffle-shop")
        commit = result["semantic_commit"] if item["repository"] == "semantic" else result["dbt_submodule_commit"]
        url = f"https://github.com/{repo}/blob/{commit}/{item['path']}#L{item['line']}"
        lines.append(f"- [{item['repository']} `{item['path']}:{item['line']}`]({url}) — `{item['snippet']}`")
    lines += ["", "Remaining gates: independently annotate this candidate, find unrelated public examples, and verify the two native semantic runtimes before any cross-engine portability claim. An ordinary dbt `expression_is_true` test can miss NULL versus zero because `NOT(NULL = 0)` is NULL. Keep this candidate separate from the ten earlier development pairs and from any held-out test set.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Checkout of sidequery/jaffle-shop-sidemantic with submodule initialized")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify(args.repo)
    if args.check:
        sample = result["sample"]
        assert sample["orders"] == 61948
        assert sample["orders_without_items"] == 483
        assert sample["orders_with_null_sensitive_item_subtotal_mismatch"] == 483
        assert sample["orders_with_coalesced_item_subtotal_mismatch"] == 0
        assert sample["dates_with_different_values"] == 0
        assert sample["sum_order_subtotal_cents"] == sample["sum_item_price_cents"]
    (ROOT / "public_positive_candidate.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_positive_candidate.md").write_text(markdown(result), encoding="utf-8")
    print(f"Checked POS-001 on {result['sample']['orders']} orders: "
          f"{result['sample']['orders_with_null_sensitive_item_subtotal_mismatch']} null-sensitive order differences, "
          f"{result['sample']['dates_with_different_values']} daily differences"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
