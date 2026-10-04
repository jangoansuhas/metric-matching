# Audit of six initially agreed public metric pairs

Pinned `dbt-labs/jaffle-shop` revision: `5beb145b00f5465ec759cfcdd9745e858818cf95`. Each pair received the same first and submitted label. This audit checks the relevant YAML signatures and cited SQL statements in that revision. It does not run dbt/MetricFlow, prove all execution semantics, or establish independent ground truth.

| Pair | Agreed label | Source-backed reason | Remaining execution limit |
| --- | --- | --- | --- |
| JS-002 | `temporal_or_scope_variant` | The same order-row count acquires a first-order filter. The model computes a row number per customer. | MetricFlow dimension binding and ordering of tied timestamps were not executed. |
| JS-003 | `temporal_or_scope_variant` | The same order-row count acquires a threshold on tax-inclusive order total. | The MetricFlow dimension filter, threshold unit conversion, and null behavior were not executed. |
| JS-004 | `temporal_or_scope_variant` | The same item price SUM includes every item versus food items with zero for other items. | CASE execution and row preservation through the item/product join were not compiled or proven here. |
| JS-006 | `related` | Both consume item price, but SUM and MEDIAN are different aggregations. | Native median implementation was not run; the distinct aggregation definitions establish the label. |
| JS-008 | `related` | Customer lifetime totals include versus exclude tax. A separate tax component is summed directly, so location-rate reconstruction is not required. | The declared customer-level dbt test was not run; the relationship is supported by visible SQL and the pinned raw-order checks. |
| JS-009 | `non_match` | Customer count and average location tax rate differ in entity, unit, and business question. | The average-tax-rate metric was not executed; its source field is present in staging SQL. |

## Evidence locations

- JS-002: `models/marts/orders.yml:66-79`, `models/marts/orders.sql:57-68`, `models/marts/orders.sql:69`, `models/marts/orders.sql:71`.
- JS-003: `models/marts/orders.yml:37-41`, `models/marts/orders.yml:66-71`, `models/marts/orders.yml:80-87`, `models/marts/orders.yml:41`, `models/staging/stg_orders.sql:24`.
- JS-004: `models/marts/order_items.yml:39-51`, `models/staging/stg_products.sql:17-24`, `models/marts/order_items.sql:49`, `models/marts/order_items.sql:50`, `models/staging/stg_products.sql:26`.
- JS-006: `models/marts/order_items.yml:39-45`, `models/marts/order_items.yml:58-63`.
- JS-008: `models/marts/customers.yml:7-10`, `models/marts/customers.yml:36-41`, `models/marts/customers.yml:62-71`, `models/marts/customers.sql:24-26`, `models/marts/customers.sql:24`, `models/marts/customers.sql:25`, `models/marts/customers.sql:26`, `models/marts/customers.yml:10`.
- JS-009: `models/marts/customers.yml:50-56`, `models/marts/locations.yml:1-26`, `models/staging/stg_locations.sql:20`.

The submitted rationale for JS-008 mentioned adjusting location tax rates. The visible `customers.sql` instead sums `orders.tax_paid` directly. That distinction does not change the `related` label. The six labels remain source-supported development annotations; confirm them under a frozen rubric and document adjudicator provenance before treating them as a benchmark.
