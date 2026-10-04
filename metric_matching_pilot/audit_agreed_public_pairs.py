#!/usr/bin/env python3
"""Audit the six initially agreed public pair labels against pinned YAML/SQL source."""

import argparse
import json
from pathlib import Path

from build_public_pair_review import metric_index
from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent
CASES = {
    "JS-002": {
        "label": "temporal_or_scope_variant",
        "left": ("sum", 1, None),
        "right": ("sum", 1, "{{ Dimension('order_id__customer_order_number') }} = 1"),
        "reason": "The same order-row count acquires a first-order filter. The model computes a row number per customer.",
        "execution_limit": "MetricFlow dimension binding and ordering of tied timestamps were not executed.",
        "anchors": {"models/marts/orders.sql": ["partition by customer_id", "as customer_order_number"]},
    },
    "JS-003": {
        "label": "temporal_or_scope_variant",
        "left": ("sum", 1, None),
        "right": ("sum", 1, "{{ Dimension('order_id__order_total_dim') }} >= 20"),
        "reason": "The same order-row count acquires a threshold on tax-inclusive order total.",
        "execution_limit": "The MetricFlow dimension filter, threshold unit conversion, and null behavior were not executed.",
        "anchors": {"models/marts/orders.yml": ["name: order_total_dim"],
                    "models/staging/stg_orders.sql": ["cents_to_dollars('order_total')"]},
    },
    "JS-004": {
        "label": "temporal_or_scope_variant",
        "left": ("sum", "product_price", None),
        "right": ("sum", "case when is_food_item then product_price else 0 end", None),
        "reason": "The same item price SUM includes every item versus food items with zero for other items.",
        "execution_limit": "CASE execution and row preservation through the item/product join were not compiled or proven here.",
        "anchors": {"models/marts/order_items.sql": ["products.product_price", "products.is_food_item"],
                    "models/staging/stg_products.sql": ["type = 'jaffle'"]},
    },
    "JS-006": {
        "label": "related",
        "left": ("sum", "product_price", None),
        "right": ("median", "product_price", None),
        "reason": "Both consume item price, but SUM and MEDIAN are different aggregations.",
        "execution_limit": "Native median implementation was not run; the distinct aggregation definitions establish the label.",
        "anchors": {},
    },
    "JS-008": {
        "label": "related",
        "left": ("sum", "lifetime_spend", None),
        "right": ("sum", "lifetime_spend_pretax", None),
        "reason": "Customer lifetime totals include versus exclude tax. A separate tax component is summed directly, so location-rate reconstruction is not required.",
        "execution_limit": "The declared customer-level dbt test was not run; the relationship is supported by visible SQL and the pinned raw-order checks.",
        "anchors": {"models/marts/customers.sql": ["sum(orders.subtotal) as lifetime_spend_pretax",
                                                    "sum(orders.tax_paid) as lifetime_tax_paid",
                                                    "sum(orders.order_total) as lifetime_spend"],
                    "models/marts/customers.yml": ["lifetime_spend_pretax + lifetime_tax_paid = lifetime_spend"]},
    },
    "JS-009": {
        "label": "non_match",
        "left": ("count_distinct", "customer_id", None),
        "right": ("average", "tax_rate", None),
        "reason": "Customer count and average location tax rate differ in entity, unit, and business question.",
        "execution_limit": "The average-tax-rate metric was not executed; its source field is present in staging SQL.",
        "anchors": {"models/staging/stg_locations.sql": ["tax_rate,"]},
    },
}


def signature(metric):
    return (metric["agg"], metric.get("expr", metric["name"]),
            " ".join(metric["filter"].split()) if metric.get("filter") else None)


def audit(repo):
    proposals = json.loads((ROOT / "public_pair_proposals.json").read_text(encoding="utf-8"))
    comparison = json.loads((ROOT / "public_pair_review_comparison.json").read_text(encoding="utf-8"))
    commit = repository_commit(repo)
    if commit != proposals["commit"] or commit != comparison["commit"]:
        raise ValueError("Public repository revisions differ")
    index = metric_index(repo)
    by_id = {pair["id"]: pair for pair in proposals["pairs"]}
    reviewed = {row["id"]: row for row in comparison["rows"]}
    rows = []
    for pair_id, case in CASES.items():
        pair, reviewed_pair = by_id[pair_id], reviewed[pair_id]
        if not reviewed_pair["agreement"] or reviewed_pair["first_label"] != case["label"]:
            raise ValueError(f"Initial labels do not agree as expected: {pair_id}")
        for side in ("left", "right"):
            node = pair[side]
            actual = index[(node["model"], node["metric"])]
            if signature(actual["metric"]) != case[side]:
                raise ValueError(f"Definition changed: {pair_id} {side}")
        anchors = []
        for rel, snippets in case["anchors"].items():
            lines = (repo / rel).read_text(encoding="utf-8").splitlines()
            for snippet in snippets:
                matches = [n for n, line in enumerate(lines, 1) if snippet in line]
                if not matches:
                    raise ValueError(f"Missing evidence: {pair_id} {rel} {snippet}")
                anchors.append({"path": rel, "line": matches[0], "snippet": snippet})
        rows.append({"id": pair_id, "first_and_second_label": case["label"],
                     "status": "source_supported_not_executed_or_gold",
                     "reason": case["reason"], "execution_limit": case["execution_limit"],
                     "proposal_evidence": pair["evidence"], "additional_evidence": anchors})
    return {"corpus": proposals["corpus"], "commit": commit, "rows": rows,
            "status": "six_source_supported_initial_agreements_not_gold_or_matcher_accuracy"}


def markdown(report):
    lines = ["# Audit of six initially agreed public metric pairs", "",
             f"Pinned `dbt-labs/jaffle-shop` revision: `{report['commit']}`. Each pair received the same first and submitted label. This audit checks the relevant YAML signatures and cited SQL statements in that revision. It does not run dbt/MetricFlow, prove all execution semantics, or establish independent ground truth.", "",
             "| Pair | Agreed label | Source-backed reason | Remaining execution limit |",
             "| --- | --- | --- | --- |"]
    for row in report["rows"]:
        lines.append(f"| {row['id']} | `{row['first_and_second_label']}` | {row['reason']} | {row['execution_limit']} |")
    lines += ["", "## Evidence locations", ""]
    for row in report["rows"]:
        refs = [f"`{e['path']}:{e['start']}-{e['end']}`" for e in row["proposal_evidence"]]
        refs += [f"`{e['path']}:{e['line']}`" for e in row["additional_evidence"]]
        lines.append(f"- {row['id']}: " + ", ".join(refs) + ".")
    lines += ["", "The submitted rationale for JS-008 mentioned adjusting location tax rates. The visible `customers.sql` instead sums `orders.tax_paid` directly. That distinction does not change the `related` label. The six labels remain source-supported development annotations; confirm them under a frozen rubric and document adjudicator provenance before treating them as a benchmark.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = audit(args.repo.resolve())
    if args.check:
        assert len(report["rows"]) == 6
        assert {row["id"] for row in report["rows"]} == set(CASES)
        assert all(row["proposal_evidence"] for row in report["rows"])
    (ROOT / "public_agreed_pair_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_agreed_pair_audit.md").write_text(markdown(report), encoding="utf-8")
    print("Audited six initially agreed labels against pinned YAML/SQL source"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
