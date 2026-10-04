# Selected dbt lineage paths at pinned revision

Public corpus: `dbt-labs/jaffle-shop` at `5beb145b00f5465ec759cfcdd9745e858818cf95`.
The script traces three selected metrics through a documented SQL subset and records candidate origins. It does not compile dbt, execute source rows, validate join cardinality, or assign metric relationship labels.

| Metric | Observed candidate path | Remaining uncertainty |
| --- | --- | --- |
| `order_total` | `orders.order_total` → `stg_orders.order_total` → `ecom.raw_orders.order_total` | `cents_to_dollars` is adapter-dispatched; star pass-through is inspected only in this subset. |
| `revenue` | `order_items.product_price` → `stg_products.product_price` → `ecom.raw_products.price` | Join `order_items.product_id = products.product_id` has no row-level cardinality check; conversion macro uncompiled. |
| `new_customer_orders` | `SUM(1)` filtered by `customer_order_number = 1`, whose SQL expression is `row_number() over (partition by customer_id order by ordered_at asc)` | MetricFlow Dimension binding and tie behavior remain unverified. |

All three relationships to other metrics remain `not_evaluated`. These manually selected probes are not extraction coverage or matcher accuracy estimates. Detailed file and CTE evidence appears in `public_lineage_report.json`.
