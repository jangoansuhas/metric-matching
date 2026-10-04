# POS-001: Executed semantic measures by day

The two pre-existing public measures were imported from MetricFlow and Cube YAML into Sidemantic **0.8.2** and executed on the pinned dbt-built DuckDB tables. This check uses one unified semantic engine, not the native MetricFlow or Cube runtimes.

| Comparison | Result |
| --- | ---: |
| Compared dates | 365 (2024-09-01 through 2025-08-31) |
| Dates absent from either measure | 0 |
| Dates with differing values | 0 |
| Sum of `orders.subtotal` daily values | $637444.00 |
| Sum of `order_items.revenue` daily values | $637444.00 |

The compiler generates `SUM(subtotal)` over `main.orders` and `SUM(product_price)` over `main.order_items`, both grouped by `DATE_TRUNC('DAY', ordered_at)`. The complete generated SQL and source queries are in `public_positive_semantic_check.json`.

**Scope.** Agreement is empirical at aligned **daily** grain in this curated sample. It does not establish interchangeability at order grain: 483 orders have no items and an unfilled item sum is NULL, although the order subtotal is zero. The separate null-aware dbt check documents this difference. Sidemantic translates both YAML formats; native MetricFlow and Cube execution and independent gold annotation remain open.
