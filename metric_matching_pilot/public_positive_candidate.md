# POS-001: Conditional public cross-grain candidate

Source: `sidequery/jaffle-shop-sidemantic@8686fe3ea0fd4ceffa08e523a422331bd228ac32` with dbt Labs Jaffle Shop submodule `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. Both measure definitions already exist in this public demonstration repository; neither was added by this pilot.

| Property | orders.subtotal | order_items.revenue |
| --- | --- | --- |
| Semantic format | MetricFlow | Cube |
| Native grain | One order | One order item |
| Aggregation and field | SUM(subtotal) | SUM(product_price) |
| Aligned time | ordered_at (default, day) | ordered_at (explicit time dimension from joined order) |

**Explicit mapping.** For order-level equivalence, LEFT JOIN each order to SUM(item.product_price) GROUP BY item.order_id, COALESCE missing item sums to 0, and compare with order.subtotal; for daily totals, sum each measure by the aligned orders.ordered_at date. The item-to-order relationship is declared `many_to_one`. The order model builds `order_items_subtotal` by summing item `product_price` grouped by `order_id`, and its YAML declares an equality test to order `subtotal`.

**Pinned raw-seed check.** 61,948 orders, 90,900 items, 10 products. 483 orders have no items, giving NULL/absent item groups versus a zero subtotal. Consequently 483 orders differ before null handling and 0 differ after an outer join and COALESCE. Both all-time totals equal 63,744,400 cents; daily sums agree on all 365 dates (0 mismatches). No item mapping or key-uniqueness failures were found.

**Status.** Conditional cross-grain candidate: matching daily totals on the pinned data, with order-level equality only after an explicit outer join and COALESCE. This raw-row calculation is supplemented by `public_positive_built_check.md` for materialized dbt tables and `public_positive_semantic_check.md` for execution of both measures through Sidemantic. This curated demonstration shares Jaffle Shop data and cannot alone establish performance on independent repositories or industrial metrics.

## Pinned source locations

- [semantic `models/metricflow/orders.yml:12`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/metricflow/orders.yml#L12) — `agg_time_dimension: ordered_at`
- [semantic `models/metricflow/orders.yml:55`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/metricflow/orders.yml#L55) — `name: subtotal`
- [semantic `models/metricflow/orders.yml:57`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/metricflow/orders.yml#L57) — `expr: subtotal`
- [semantic `models/cube/order_items.yml:3`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/cube/order_items.yml#L3) — `sql_table: main.order_items`
- [semantic `models/cube/order_items.yml:28`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/cube/order_items.yml#L28) — `name: revenue`
- [semantic `models/cube/order_items.yml:29`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/cube/order_items.yml#L29) — `sql: product_price`
- [semantic `models/cube/order_items.yml:48`](https://github.com/sidequery/jaffle-shop-sidemantic/blob/8686fe3ea0fd4ceffa08e523a422331bd228ac32/models/cube/order_items.yml#L48) — `relationship: many_to_one`
- [dbt `models/marts/orders.sql:21`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.sql#L21) — `sum(product_price) as order_items_subtotal`
- [dbt `models/marts/orders.sql:48`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.sql#L48) — `order_items_summary.order_items_subtotal`
- [dbt `models/marts/order_items.sql:46`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.sql#L46) — `orders.ordered_at`
- [dbt `models/marts/order_items.sql:49`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.sql#L49) — `products.product_price`
- [dbt `models/marts/order_items.sql:57`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.sql#L57) — `left join orders on order_items.order_id = orders.order_id`
- [dbt `models/marts/order_items.sql:59`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.sql#L59) — `left join products on order_items.product_id = products.product_id`
- [dbt `models/marts/orders.yml:6`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L6) — `order_items_subtotal = subtotal`
- [dbt `models/staging/stg_orders.sql:22`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/staging/stg_orders.sql#L22) — `cents_to_dollars('subtotal')`
- [dbt `models/staging/stg_orders.sql:27`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/staging/stg_orders.sql#L27) — `as ordered_at`
- [dbt `models/staging/stg_products.sql:23`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/staging/stg_products.sql#L23) — `cents_to_dollars('price')`
- [dbt `macros/cents_to_dollars.sql:7`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/macros/cents_to_dollars.sql#L7) — `default__cents_to_dollars`
- [dbt `macros/cents_to_dollars.sql:8`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/macros/cents_to_dollars.sql#L8) — `100)::numeric(16, 2)`

Remaining gates: independently annotate this candidate, find unrelated public examples, and verify the two native semantic runtimes before any cross-engine portability claim. An ordinary dbt `expression_is_true` test can miss NULL versus zero because `NOT(NULL = 0)` is NULL. Keep this candidate separate from the ten earlier development pairs and from any held-out test set.
