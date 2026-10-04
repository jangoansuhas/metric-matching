# Metric expression trace: pinned public development checkout

- Repository: Jaffle/Sidemantic `7be2c5838dbdeca8e915d4e46db70e910753d7f6`.
- Manifest SHA-256: `1467a9a6a71de14f196adbab89927083adcc2b9f680f7e9b6256a0720b40fb24`.
- Eligibility report SHA-256: `0e2d601f1dbde17c62716192f6410d78a28f6b76fe21468cca9b6eb5596b8af7`.
- Model provenance report SHA-256: `cec3f3770a9ddbc97c5b2f309c543953a4cec19e8b62a327968e21469fce1f15`.
- SQL parser: `sqlglot 30.20.0`, `duckdb` dialect.
- Local package lock differs from pinned package lock: True (pinned SHA-256 `a1d44d11c893f4d68e722ef8479bd3c4d2f632202f1ef7bd4ade6a14986b50db`; local SHA-256 `67ecfc0a7ebdcc03b8e2f38c86d7b283e72c5d58fb9a7de9b4f30aa2a3a01eef`). This is separate build provenance uncertainty; it does not establish the cause of the model checksum mismatch.
- Declarations: 32 (19 metrics, 13 measures); 10 unknown numeric eligibility.
- Exact manifest measure paths: 32; unique model candidates: 31. These are candidate mappings, not equivalence labels.
- Compiled metric expressions verified: 0; needs review: 32.

## Stop reasons by affected declaration

| Reason | Declarations |
| --- | ---: |
| `build_commit_unverified` | 32 |
| `compiled_metric_query_unavailable` | 32 |
| `cte_projection_boundary` | 32 |
| `join_field_owner_ambiguous` | 31 |
| `literal_measure_has_no_field_owner` | 6 |
| `manifest_source_checksum_mismatch` | 32 |
| `metric_filter_requires_compiled_metric_query` | 4 |
| `metric_transformation_requires_compiled_metric_query` | 6 |
| `missing_explicit_field_projection` | 4 |
| `model_source_checksum_or_mapping_needs_review` | 32 |
| `multiple_model_candidates` | 1 |
| `multiple_projection_candidates` | 9 |
| `numeric_eligibility_unknown` | 10 |
| `unexpanded_select_star` | 32 |
| `window_projection_boundary` | 12 |

## Distinct declarations

| ID | Model candidate | Measure paths | Expression status |
| --- | --- | ---: | --- |
| `manifest:measure:semantic_model.jaffle_shop.customers:measures[0]` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.customers:measures[1]` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.customers:measures[2]` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.customers:measures[3]` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.locations:measures[0]` | `model.jaffle_shop.locations` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.order_item:measures[0]` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.order_item:measures[1]` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.order_item:measures[2]` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.order_item:measures[3]` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.orders:measures[0]` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.orders:measures[1]` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.orders:measures[2]` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:measure:semantic_model.jaffle_shop.orders:measures[3]` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.average_order_value` | `model.jaffle_shop.customers` | 2 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.count_lifetime_orders` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.cumulative_revenue` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.drink_orders` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.drink_revenue` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.drink_revenue_pct` | `model.jaffle_shop.order_items` | 2 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.food_orders` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.food_revenue` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.food_revenue_pct` | `model.jaffle_shop.order_items` | 2 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.large_orders` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.lifetime_spend_pretax` | `model.jaffle_shop.customers` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.median_revenue` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.new_customer_orders` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.order_cost` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.order_gross_profit` | `unresolved/multiple` | 2 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.order_total` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.orders` | `model.jaffle_shop.orders` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.revenue` | `model.jaffle_shop.order_items` | 1 | `needs_review` |
| `manifest:metric:metric.jaffle_shop.revenue_growth_mom` | `model.jaffle_shop.order_items` | 1 | `needs_review` |

## Interpretation

The source YAML and compiled model hash references are in the JSON report. The compiled SQL files match their manifest text in the prior model provenance audit, but Jaffle model source checksums do not reconcile; the manifest build commit is unverified. The selected compiled models contain CTEs and unexpanded stars, with join ambiguity for some fields. No compiled metric query is present, so a measure-to-model mapping is never promoted to a verified metric expression.

The 32 IDs remain separate; derived dependencies never collapse measures into metrics. Nothing here measures matching accuracy or establishes semantic equivalence.

Reproduce from the workspace root: `python3 -B metric_matching_pilot/generic_metric_expression_trace.py --check`.
