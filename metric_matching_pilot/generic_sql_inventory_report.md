# Generic SQL aggregate inventory (development only)

Input: `sql/metric_views.sql` (SHA256 `6fe38b9546d251a01a2ed60128733f7267390554b0f49b4e8ba07322c466800b`).

Parser: sqlglot 30.20.0, `duckdb` dialect. Views: 12; projected outputs: 24; complete unordered pairs: 276.
Recognized aggregate outputs: 6; supported aggregate outputs: 4; unresolved placeholders: 0.

## Coverage

| Item | Count |
| --- | ---: |
| Output reason: `join` | 4 |
| Output reason: `non_aggregate` | 16 |
| Pair reason: `different_operator` | 4 |
| Pair reason: `different_source_tables` | 1 |
| Pair reason: `same_source_signature` | 1 |
| Pair reason: `unsupported_output` | 270 |

## Aggregate outputs

| Output | Line | Operator | Sources | Status / reason |
| --- | ---: | --- | --- | --- |
| `account_net_revenue.value` | 14 | SUM | `account_arr_daily_snapshot` | supported_aggregate; none |
| `crm_revenue_net_rollup.value` | 20 | SUM | `account_hierarchy, opportunity_snapshot` | abstain; join |
| `crm_revenue_net_fanout.value` | 28 | SUM | `account_hierarchy_bad, opportunity_snapshot` | abstain; join |
| `account_net_revenue_undocumented.value` | 36 | SUM | `account_arr_daily_snapshot` | supported_aggregate; none |
| `number_of_customers.value` | 63 | COUNT | `customer` | supported_aggregate; none |
| `num_of_products.value` | 66 | COUNT | `product` | supported_aggregate; none |

## Source comparison examples

- `account_net_revenue.value` / `account_net_revenue_undocumented.value`: source_candidate (same_source_signature).
- `num_of_products.value` / `number_of_customers.value`: source_difference (different_source_tables).

## Synthetic negative fixture

`generic_sql_fixture_negative.sql` (SHA256 `0cdf53a7542d6a5f2037e1c1daf0289b48046b44f5d65771d43d3e39b7464ff5`).

| Pair | Expression AST and argument AST | Decision / reason | NULL policy |
| --- | --- | --- | --- |
| `sum_orders.value` / `median_orders.value` | `SUM(amount)` (Sum / Column) vs `MEDIAN(amount)` (Median / Column) | source_difference; different_operator | unknown / unknown |
| `count_orders.value` / `count_customers.value` | `COUNT(*)` (Count / Star) vs `COUNT(*)` (Count / Star) | source_difference; different_source_tables | unknown / unknown |
| `sum_orders.value` / `sum_orders_coalesced.value` | `SUM(amount)` (Sum / Column) vs `SUM(COALESCE(amount, 0))` (Sum / Coalesce) | source_difference; different_argument | unknown / unknown |

AST differences are source evidence only; NULL behavior and value equivalence are not inferred.

Fixture inventory: 8 views, 12 emitted outputs, 66 unordered pairs, including 2 unresolved placeholders.
- `joined_orders.value`: abstain (join).
- `templated_orders._unresolved_output_1`: abstain (unresolved_projection, unsupported_jinja).
- `templated_aliasless._unresolved_output_1`: abstain (unresolved_projection, unsupported_jinja).

## Limits

- Source syntax only; no compiled dbt or dependency expansion.
- Same source signature is a review candidate, not value equivalence.
- A source difference is not a semantic contradiction; transformations may reconcile outputs.
- Grain, time, NULL policy, join cardinality and snapshot are unknown.
- Joins, CTEs, windows, nested queries and Jinja abstain.
- Unparseable views receive one abstaining placeholder rather than guessed aliases; their true projection count remains unknown.
- Pair completeness is over emitted output IDs, including placeholders; unknown projection arity cannot be inferred.

`python generic_sql_inventory.py --check` verifies both report bytes without writing files.
`python generic_sql_inventory.py --input generic_sql_fixture_negative.sql --stdout` inspects the synthetic counterfactual without writing files.
