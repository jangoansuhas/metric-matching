# Independent public metric-pair review

Repository: [dbt-labs/jaffle-shop at pinned commit](https://github.com/dbt-labs/jaffle-shop/tree/5beb145b00f5465ec759cfcdd9745e858818cf95).

Choose one label for each pair **before opening `public_pair_proposals.json`**. These metrics occur naturally in the repository. Review SQL and YAML at the linked lines; do not assume a value match from names. Record why the label holds, or what evidence is missing. This is an unfilled sheet, not a completed independent annotation.

Labels: `direct_equivalent` (same quantity/rules), `cross_grain_equivalent` (proved aligned additive transformation), `temporal_or_scope_variant` (same base concept, changed time/population), `related` (shared domain without safe substitution), `conflicting_definition` (same identity/name used for incompatible meanings), `non_match` (different business quantity), `needs_review` (decisive evidence missing).

## JS-001: `orders.order_total` versus `order_items.revenue`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `order_total` | `unspecified` | `order_id` | `ordered_at` |
| right | `sum` | `product_price` | `unspecified` | `order_item_id` | `ordered_at` |

Evidence locations: [models/marts/orders.yml:37-65](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L37-L65); [models/marts/order_items.yml:39-45](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/order_items.yml#L39-L45); [models/marts/orders.sql:18-27](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.sql#L18-L27).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-002: `orders.orders` versus `orders.new_customer_orders`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `1` | `unspecified` | `order_id` | `ordered_at` |
| right | `sum` | `1` | `{{ Dimension('order_id__customer_order_number') }} = 1` | `order_id` | `ordered_at` |

Evidence locations: [models/marts/orders.yml:66-79](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L66-L79); [models/marts/orders.sql:57-68](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.sql#L57-L68).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-003: `orders.orders` versus `orders.large_orders`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `1` | `unspecified` | `order_id` | `ordered_at` |
| right | `sum` | `1` | `{{ Dimension('order_id__order_total_dim') }} >= 20` | `order_id` | `ordered_at` |

Evidence locations: [models/marts/orders.yml:37-41](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L37-L41); [models/marts/orders.yml:66-71](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L66-L71); [models/marts/orders.yml:80-87](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L80-L87).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-004: `order_items.revenue` versus `order_items.food_revenue`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `product_price` | `unspecified` | `order_item_id` | `ordered_at` |
| right | `sum` | `case when is_food_item then product_price else 0 end` | `unspecified` | `order_item_id` | `ordered_at` |

Evidence locations: [models/marts/order_items.yml:39-51](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/order_items.yml#L39-L51); [models/staging/stg_products.sql:17-24](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/staging/stg_products.sql#L17-L24).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-005: `order_items.food_revenue` versus `order_items.drink_revenue`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `case when is_food_item then product_price else 0 end` | `unspecified` | `order_item_id` | `ordered_at` |
| right | `sum` | `case when is_drink_item then product_price else 0 end` | `unspecified` | `order_item_id` | `ordered_at` |

Evidence locations: [models/marts/order_items.yml:46-57](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/order_items.yml#L46-L57); [models/staging/stg_products.sql:17-24](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/staging/stg_products.sql#L17-L24).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-006: `order_items.revenue` versus `order_items.median_revenue`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `product_price` | `unspecified` | `order_item_id` | `ordered_at` |
| right | `median` | `product_price` | `unspecified` | `order_item_id` | `ordered_at` |

Evidence locations: [models/marts/order_items.yml:39-45](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/order_items.yml#L39-L45); [models/marts/order_items.yml:58-63](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/order_items.yml#L58-L63).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-007: `customers.customers` versus `orders.orders`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `count_distinct` | `customer_id` | `unspecified` | `customer_id` | `first_ordered_at` |
| right | `sum` | `1` | `unspecified` | `order_id` | `ordered_at` |

Evidence locations: [models/marts/customers.yml:50-56](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L50-L56); [models/marts/orders.yml:66-71](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L66-L71); [models/marts/customers.sql:20-26](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.sql#L20-L26).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-008: `customers.lifetime_spend` versus `customers.lifetime_spend_pretax`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `lifetime_spend` | `unspecified` | `customer_id` | `first_ordered_at` |
| right | `sum` | `lifetime_spend_pretax` | `unspecified` | `customer_id` | `first_ordered_at` |

Evidence locations: [models/marts/customers.yml:7-10](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L7-L10); [models/marts/customers.yml:36-41](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L36-L41); [models/marts/customers.yml:62-71](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L62-L71); [models/marts/customers.sql:24-26](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.sql#L24-L26).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-009: `customers.customers` versus `locations.average_tax_rate`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `count_distinct` | `customer_id` | `unspecified` | `customer_id` | `first_ordered_at` |
| right | `average` | `tax_rate` | `unspecified` | `location_id` | `opened_date` |

Evidence locations: [models/marts/customers.yml:50-56](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L50-L56); [models/marts/locations.yml:1-26](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/locations.yml#L1-L26).

Reviewer label: ______  Reason / missing evidence: ____________________

## JS-010: `orders.order_total` versus `customers.lifetime_spend`

| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |
| --- | --- | --- | --- | --- | --- |
| left | `sum` | `order_total` | `unspecified` | `order_id` | `ordered_at` |
| right | `sum` | `lifetime_spend` | `unspecified` | `customer_id` | `first_ordered_at` |

Evidence locations: [models/marts/orders.yml:2-6](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L2-L6); [models/marts/orders.yml:60-65](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/orders.yml#L60-L65); [models/marts/customers.yml:2-6](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L2-L6); [models/marts/customers.yml:67-71](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.yml#L67-L71); [models/marts/customers.sql:15-30](https://github.com/dbt-labs/jaffle-shop/blob/5beb145b00f5465ec759cfcdd9745e858818cf95/models/marts/customers.sql#L15-L30).

Reviewer label: ______  Reason / missing evidence: ____________________
