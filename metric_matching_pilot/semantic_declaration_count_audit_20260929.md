# Semantic declaration count audit — 2026-09-29

## Scope and counting rule

Only the already selected `/workspace/scratch/e767b9d6f697/heldout_screen/rank01` and `rank02` trees were examined. Paths below are relative to `/workspace/scratch/e767b9d6f697`. The on-disk inventory covered every regular `.yml`/`.yaml` and `.sql` file recursively in those two trees, including auxiliary YAML outside the dbt model directory. Every YAML file parsed as a mapping.

A **declared MetricFlow metric** is an entry in a YAML `metrics:` declaration; a **measure** is an entry in `semantic_models[].measures`. These are distinct declaration types. dbt `models[].columns`, descriptions using the word “metric,” and SQL output aliases are not MetricFlow declarations. A recursive check also found no keys named `metrics`, `semantic_models`, or `measures` anywhere in the selected YAML.

For the separate SQL count, one **numeric aggregate output** is one distinct final model column whose defining SQL expression contains `SUM`, `COUNT`, or `AVG` (including a window aggregate or a numeric expression using one). An aggregate calculated in a CTE and carried to the final projection is counted once, at its defining expression. `MIN`/`MAX` of timestamps, `LAG`, and numeric calculations without an aggregate in their defining expression are excluded. This is a source-expression count, not a count of all numeric model columns or a dbt compilation result.

## YAML declaration inventory

| Selected tree | YAML parsed / present | dbt YAML declaration sites and pinned lines | Declared metrics | Semantic models | Measures |
| --- | ---: | --- | ---: | ---: | ---: |
| rank01 | 5 / 5 | `heldout_screen/rank01/dbt_project.yml:17-33` (model and seed configuration); `heldout_screen/rank01/models/marts/customers/schema.yml:1-28` (one model); `heldout_screen/rank01/models/marts/finance/schema.yml:1-30` (one model); `heldout_screen/rank01/models/marts/marketing/schema.yml:1-52` (two models); `heldout_screen/rank01/models/staging/schema.yml:1-137` (five models) | 0 | 0 | 0 |
| rank02 | 6 / 6 | `heldout_screen/rank02/transform/dbt_project.yml:5-36` (project configuration); `heldout_screen/rank02/transform/models/marts/github/_marts.yml:1-25` (two dbt models under `models:`); `heldout_screen/rank02/transform/models/staging/sources.yml:1-10` (one source under `sources:`). Three additional auxiliary YAML files were parsed and contain no declaration keys. | 0 | 0 | 0 |

**Rank2 answer:** zero declared MetricFlow metrics in the selected on-disk YAML, established by a successful parse of all six files. In particular, `_marts.yml:3-25` is a dbt `models:` schema, and `sources.yml:4-10` is a `sources:` schema; neither declares `metrics:` or `semantic_models:`. The zero is not a fallback for an unparsed file. No runtime MetricFlow/dbt manifest was generated or inspected, so runtime registration is outside this audit.

## Numeric SQL aggregate output inventory

| Selected tree | SQL file and aggregate-defining lines | Output aliases counted | Count |
| --- | --- | --- | ---: |
| rank01 | `heldout_screen/rank01/models/marts/finance/mart_monthly_revenue_summary.sql:14-15,26-29,32-38,41` | `new_customers`, `new_arr` (defined as `total_new_customers`, `total_new_arr` in the CTE and projected at lines 52-53); `total_actual_revenue`, `total_modeled_revenue`, `total_base_revenue`, `total_paid_media_revenue`; `brand_search_revenue`, `display_pmax_revenue`, `nonbrand_search_revenue`, `remarketing_revenue`, `meta_prospecting_revenue`, `meta_retargeting_revenue`, `meta_other_revenue`; `avg_model_error_pct`. `m.*` carries the latter 12 at line 49; the final model selects `final` at line 79. | 14 |
| rank01 | `heldout_screen/rank01/models/marts/marketing/mart_mmm_weekly_trends.sql:35-44` (final projection at line 60) | `revenue_4wk_rolling_avg`, `revenue_ytd` | 2 |
| rank01 | `heldout_screen/rank01/models/staging/stg_mta_channel_attribution.sql:27-29` (final projection at line 34) | `shapley_revenue_share_pct` | 1 |
| rank02 | `heldout_screen/rank02/transform/models/marts/github/dim_authors.sql:14-15,22` (final projection at line 29) | `total_prs_submitted`, `total_prs_merged`, `avg_time_to_merge_hours` | 3 |

The remaining SQL files have zero qualifying outputs: `heldout_screen/rank01/models/marts/customers/mart_customer_unit_economics.sql:1-45`, `heldout_screen/rank01/models/marts/marketing/mart_channel_performance.sql:1-80`, `heldout_screen/rank01/models/staging/stg_cac_by_channel.sql:1-41`, `heldout_screen/rank01/models/staging/stg_mmm_channel_summary.sql:1-34`, `heldout_screen/rank01/models/staging/stg_mmm_weekly_decomp.sql:1-50`, `heldout_screen/rank01/models/staging/stg_new_customers_monthly.sql:1-27`; `heldout_screen/rank02/transform/models/intermediate/int_pull_requests_metrics.sql:1-48`, `heldout_screen/rank02/transform/models/marts/github/fct_pull_requests.sql:1-43`, and `heldout_screen/rank02/transform/models/staging/github/stg_github__pull_requests.sql:1-41`. In `rank02/transform/models/marts/github/dim_authors.sql:18-19`, `MIN` and `MAX` yield timestamps and are excluded.

| Selected tree | SQL inspected / present | Numeric aggregate outputs |
| --- | ---: | ---: |
| rank01 | 9 / 9 | 17 |
| rank02 | 4 / 4 | 3 |

## Reproduction and limits

The file denominators come from recursive suffix enumeration under only those two selected trees. YAML was loaded with `yaml.safe_load`; recursive mapping-key occurrences for `metrics`, `semantic_models`, and `measures` were each zero in both trees. The SQL count follows the pinned output aliases and lines above, with CTE outputs traced through the shown final projections. No pairs, observed values, or competing matching methods were examined. Completeness is 5/5 and 6/6 on-disk YAML files and 9/9 and 4/4 on-disk SQL files in the selected trees. Any externally supplied declarations, generated manifest contents, or runtime behavior are unknown.
