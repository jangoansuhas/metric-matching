# First-annotator public pair proposals

Pinned revision: `5beb145b00f5465ec759cfcdd9745e858818cf95`. These ten labels were proposed by one analyst using repository metadata and selected source SQL. No second independent label, adjudication, data reconciliation, or matcher result exists yet.

| ID | Pair | Proposed label | Reason / condition |
| --- | --- | --- | --- |
| JS-001 | `orders.order_total` / `order_items.revenue` | `related` | Both concern monetary order activity, but the order-level total includes tax while the item-level revenue sums product prices; no safe substitution or rollup is established. |
| JS-002 | `orders.orders` / `orders.new_customer_orders` | `temporal_or_scope_variant` | Both sum one per order, but the second has a first-order filter based on customer_order_number. |
| JS-003 | `orders.orders` / `orders.large_orders` | `temporal_or_scope_variant` | Both count order rows, but large_orders keeps only orders whose total dimension meets the threshold. |
| JS-004 | `order_items.revenue` / `order_items.food_revenue` | `temporal_or_scope_variant` | Both sum product price at item grain, while food_revenue contributes zero for non-food items. |
| JS-005 | `order_items.food_revenue` / `order_items.drink_revenue` | `temporal_or_scope_variant` | The metrics sum the same product price field but use distinct food and drink conditions; they are not interchangeable. |
| JS-006 | `order_items.revenue` / `order_items.median_revenue` | `related` | Both use product_price at item grain, but SUM and MEDIAN answer different questions and cannot be reconciled by an ordinary additive rollup. |
| JS-007 | `customers.customers` / `orders.orders` | `related` | One counts distinct customer IDs and the other counts order rows; a customer may have multiple orders. |
| JS-008 | `customers.lifetime_spend` / `customers.lifetime_spend_pretax` | `related` | Both sum customer lifetime spend at customer grain, but one includes tax and the other excludes it; the model also carries a tax component. |
| JS-009 | `customers.customers` / `locations.average_tax_rate` | `non_match` | Distinct-customer count and average tax rate have different entities, units, and aggregation meaning. |
| JS-010 | `orders.order_total` / `customers.lifetime_spend` | `needs_review` | Customer lifetime_spend sums order_total across orders for a customer, suggesting a possible all-time customer rollup. However, the metrics' default time dimensions are ordered_at and first_ordered_at, so time-series equality is not established. |

Distribution: needs_review=1, non_match=1, related=4, temporal_or_scope_variant=4.

There are no confirmed equivalent pairs in this naturally occurring sample. Do not use this pack as an accuracy benchmark until an independent reviewer submits blind labels and disagreements are adjudicated. The pair selection is small and intentionally enriched for difficult relationships, so its label distribution is not representative of enterprise metrics.
