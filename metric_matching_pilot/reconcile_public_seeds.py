#!/usr/bin/env python3
"""Check two proposed cross-grain claims on pinned Jaffle Shop CSV seed rows."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent


def csv_rows(root, name):
    with (root / f"{name}.csv").open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


def reconcile(repo, expected_commit):
    commit = repository_commit(repo)
    if commit != expected_commit:
        raise ValueError(f"Expected {expected_commit}, got {commit}")
    seeds = repo / "seeds/jaffle-data"
    product_rows = list(csv_rows(seeds, "raw_products"))
    customer_rows = list(csv_rows(seeds, "raw_customers"))
    order_rows = list(csv_rows(seeds, "raw_orders"))
    prices = {r["sku"]: int(r["price"]) for r in product_rows}
    customer_ids = {r["id"] for r in customer_rows}
    orders = {r["id"]: {"customer": r["customer"], "date": r["ordered_at"][:10],
                        "subtotal": int(r["subtotal"]), "tax": int(r["tax_paid"]),
                        "gross": int(r["order_total"])}
              for r in order_rows}

    per_order_items = defaultdict(int)
    missing_product, missing_order = 0, 0
    for row in csv_rows(seeds, "raw_items"):
        if row["sku"] not in prices:
            missing_product += 1
            continue
        if row["order_id"] not in orders:
            missing_order += 1
            continue
        per_order_items[row["order_id"]] += prices[row["sku"]]

    subtotal_mismatches = sum(per_order_items.get(key, 0) != o["subtotal"] for key, o in orders.items())
    gross_rule_mismatches = sum(o["subtotal"] + o["tax"] != o["gross"] for o in orders.values())
    order_by_date, customer_lifetime, customer_first_date = Counter(), Counter(), {}
    unmapped_customer_orders = 0
    for order in orders.values():
        order_by_date[order["date"]] += order["gross"]
        customer = order["customer"]
        if customer not in customer_ids:
            unmapped_customer_orders += 1
            continue
        customer_lifetime[customer] += order["gross"]
        customer_first_date[customer] = min(customer_first_date.get(customer, order["date"]), order["date"])
    lifetime_by_first_date = Counter()
    for customer, total in customer_lifetime.items():
        lifetime_by_first_date[customer_first_date[customer]] += total
    dates = sorted(set(order_by_date) | set(lifetime_by_first_date))
    different_dates = [day for day in dates if order_by_date[day] != lifetime_by_first_date[day]]

    return {
        "corpus": "dbt-labs/jaffle-shop", "commit": commit,
        "method": "raw CSV integer cents; reproduces simple price/order/customer grouping without compiling dbt or MetricFlow",
        "row_counts": {"orders": len(orders), "customers": len(customer_ids), "products": len(prices)},
        "data_quality": {"duplicate_product_skus": len(product_rows) - len(prices),
                         "duplicate_customer_ids": len(customer_rows) - len(customer_ids),
                         "duplicate_order_ids": len(order_rows) - len(orders),
                         "missing_product_items": missing_product, "missing_order_items": missing_order,
                         "unmapped_customer_orders": unmapped_customer_orders,
                         "orders_where_item_sum_differs_from_subtotal": subtotal_mismatches,
                         "orders_where_subtotal_plus_tax_differs_from_order_total": gross_rule_mismatches},
        "js001": {"item_revenue_cents": sum(per_order_items.values()),
                  "order_subtotal_cents": sum(o["subtotal"] for o in orders.values()),
                  "order_total_cents": sum(o["gross"] for o in orders.values()),
                  "tax_paid_cents": sum(o["tax"] for o in orders.values()),
                  "orders_with_nonzero_tax": sum(o["tax"] != 0 for o in orders.values())},
        "js010": {"all_time_order_total_cents": sum(o["gross"] for o in orders.values()),
                  "all_time_customer_lifetime_spend_cents": sum(customer_lifetime.values()),
                  "daily_dates_compared": len(dates), "daily_dates_with_different_values": len(different_dates),
                  "first_different_date": different_dates[0] if different_dates else None,
                  "first_different_date_order_total_cents": order_by_date[different_dates[0]] if different_dates else None,
                  "first_different_date_lifetime_spend_cents": lifetime_by_first_date[different_dates[0]] if different_dates else None}
    }


def check(report):
    assert report["row_counts"]["orders"] == 61948
    assert all(n == 0 for n in report["data_quality"].values())
    a, b = report["js001"], report["js010"]
    assert a["item_revenue_cents"] == a["order_subtotal_cents"]
    assert a["order_total_cents"] - a["item_revenue_cents"] == a["tax_paid_cents"] > 0
    assert b["all_time_order_total_cents"] == b["all_time_customer_lifetime_spend_cents"]
    assert b["daily_dates_with_different_values"] > 0


def markdown(report):
    a, b = report["js001"], report["js010"]
    return "\n".join([
        "# Public seed reconciliation for disputed pair labels", "",
        f"Pinned repository: `dbt-labs/jaffle-shop@{report['commit']}`. Values below are integer cents from raw CSV seeds, grouped according to the visible source model expressions; dbt and MetricFlow were not run.", "",
        "| Check | Observed |", "| --- | ---: |",
        f"| Order rows | {report['row_counts']['orders']:,} |",
        f"| Orders with nonzero tax | {a['orders_with_nonzero_tax']:,} |",
        f"| JS-001 sum of item prices / order subtotals (cents) | {a['item_revenue_cents']:,} / {a['order_subtotal_cents']:,} |",
        f"| JS-001 sum of order totals / taxes (cents) | {a['order_total_cents']:,} / {a['tax_paid_cents']:,} |",
        f"| JS-010 all-time order totals / customer lifetime sums (cents) | {b['all_time_order_total_cents']:,} / {b['all_time_customer_lifetime_spend_cents']:,} |",
        f"| JS-010 dates with different daily totals | {b['daily_dates_with_different_values']} of {b['daily_dates_compared']} |", "",
        f"For example, on {b['first_different_date']}, order-day total is {b['first_different_date_order_total_cents']:,} cents while the value allocated to customers' first-order date is {b['first_different_date_lifetime_spend_cents']:,} cents. All item sums match order subtotals and all orders satisfy subtotal + tax = order_total in these seed rows. No product, order, or customer mappings were missing. These finite checks do not prove universal equivalence or exact behavior after dbt compilation.", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = reconcile(args.repo.resolve(), args.expected_commit)
    if args.check:
        check(result)
    (ROOT / "public_seed_reconciliation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_seed_reconciliation.md").write_text(markdown(result), encoding="utf-8")
    print(f"Seed checks: JS-001 tax difference {result['js001']['tax_paid_cents']} cents; "
          f"JS-010 daily differences {result['js010']['daily_dates_with_different_values']}/"
          f"{result['js010']['daily_dates_compared']} dates"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
