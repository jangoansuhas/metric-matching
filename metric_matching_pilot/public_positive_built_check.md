# POS-001: Materialized dbt check

The public Jaffle Shop submodule at `7be2c5838dbdeca8e915d4e46db70e910753d7f6` was built locally with dbt 1.12.5 and DuckDB. The declared `order_items_subtotal = subtotal` dbt test reports `pass` with 0 failures, but its compiled SQL uses `where not(order_items_subtotal = subtotal)`.

| Built table comparison | Observed |
| --- | ---: |
| Orders / items | 61,948 / 90,900 |
| Order subtotal / item price total (dollars) | 637444.00 / 637444.00 |
| Orders with no items | 483 |
| Order-level NULL-aware mismatches before COALESCE | 483 |
| Order-level mismatches after COALESCE | 0 |
| Materialized order_items_subtotal versus subtotal NULL-aware mismatches | 483 |
| Dates with different daily totals | 0 of 365 |

The ordinary dbt test misses 483 NULL-versus-zero discrepancies because SQL `NOT(NULL = 0)` is NULL and a WHERE clause discards it. A null-aware predicate such as `subtotal IS DISTINCT FROM order_items_subtotal` detects them. This does not affect all-time or aligned daily totals in the built sample. It limits any order-grain equivalence claim unless the item side is outer-joined and COALESCEd to zero.

This section checks built dbt tables, not native MetricFlow or Cube runtimes. The companion Sidemantic check translates and queries both definitions through one engine; neither check produces a gold benchmark label.
