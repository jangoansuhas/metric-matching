# Normalized SQL/lineage baseline (full context)

Input packet SHA-256: `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`. All 55 unordered pairs are reported.

## Exact normalization policy

- Skip SQL whitespace, `--` line comments and nonnested `/* ... */` comments outside quoted text. Compare sequences of typed tokens; whitespace removal never joins identifiers or numbers.
- Retain exact spelling and contents of single-quoted strings, quoted identifiers, dollar-quoted strings, numeric literals, operators and every other token. No constant folding, keyword/identifier case folding, predicate rewriting, NULL rewriting, date-boundary rewriting or field-name synonym matching.
- In `source_ref` only, omit optional `AS` in a simple `table AS alias` or `FROM/JOIN table AS alias` form. `AS` in values, casts, predicates, grouping and other clauses is retained. No alias-resolution or table-identity inference.
- Compare `value_expr`, `where_expr`, `period_expr`, `segment_expr`, `group_by`, `time_key` and `source_ref` as typed token sequences (including `null` versus nonnull). Compare `grain` literally and each supplied input-field list as a set. Preserve grouping expression order and `GROUPING SETS` syntax.
- Unsupported/dialect-dependent characters, nested or unclosed comments, unclosed quoted text and backslashes inside quotes produce an abstention. Neither card names, review flags, provenance, labels nor row outcomes are scoring inputs. IDs only route results.

## Decision policy and limits

An exact match across compared dimensions is a `direct_candidate`; a matching source/value/filter/segment/field context with period, grain or grouping differences is a `scope_variant_candidate`; a matching context with a changed filter is a `related_candidate`. All other pairs abstain. These categories are source suggestions, never unqualified equivalence assertions. The baseline identifies no transformation and emits no `conditional_candidate` decision.

Every mismatch is a contradicted prerequisite. Packet `unknown_semantics` remain unknown unless both cards independently provide the same verified value. Scope candidates always need review; a direct candidate with any unknown semantics also needs review. In particular, grouping-set expansion, join cardinality, NULL behavior, missing month groups, time zones, units and snapshot alignment cannot be inferred from identical SQL. No additive rollup, zero-fill, rounding alignment or nonadditive aggregation is proved.

## Counts

| Decision | Pairs |
|---|---:|
| `direct_candidate` | 0 |
| `conditional_candidate` | 0 |
| `scope_variant_candidate` | 2 |
| `related_candidate` | 3 |
| `abstain` | 50 |

| Evidence status | Pairs |
|---|---:|
| `sufficient_for_source_candidate` | 0 |
| `needs_review` | 55 |

## All pairs

| Left | Right | Decision | Evidence | Different dimensions |
|---|---|---|---|---|
| avg_sales_cycle_days@window | mql_to_sal_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | mql_volume@month | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | mql_volume@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | pipeline_created@month | abstain | needs_review | value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | pipeline_created@window | abstain | needs_review | value_expr, where_expr, time_key, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | sal_to_sql_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| avg_sales_cycle_days@window | win_rate@window | abstain | needs_review | value_expr, where_expr, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | mql_volume@month | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | mql_volume@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | pipeline_created@month | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | pipeline_created@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, time_key, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | sal_to_sql_rate@window | related_candidate | needs_review | where_expr |
| mql_to_sal_rate@window | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_to_sal_rate@window | sql_to_opp_rate@window | related_candidate | needs_review | where_expr |
| mql_to_sal_rate@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_volume@month | mql_volume@window | scope_variant_candidate | needs_review | period_expr, group_by, time_key, grain |
| mql_volume@month | pipeline_created@month | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, value_input_fields, filter_input_fields |
| mql_volume@month | pipeline_created@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@month | sal_to_sql_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@month | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@month | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@month | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@month | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@window | pipeline_created@month | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| mql_volume@window | pipeline_created@window | abstain | needs_review | source_ref, value_expr, where_expr, time_key, value_input_fields, filter_input_fields |
| mql_volume@window | sal_to_sql_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_volume@window | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| mql_volume@window | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| mql_volume@window | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| mql_volume@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| pipeline_created@month | pipeline_created@window | scope_variant_candidate | needs_review | period_expr, group_by, grain |
| pipeline_created@month | sal_to_sql_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| pipeline_created@month | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| pipeline_created@month | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| pipeline_created@month | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, period_expr, segment_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| pipeline_created@month | win_rate@window | abstain | needs_review | value_expr, where_expr, period_expr, group_by, time_key, grain, value_input_fields, filter_input_fields |
| pipeline_created@window | sal_to_sql_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, time_key, value_input_fields, filter_input_fields |
| pipeline_created@window | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, time_key, value_input_fields, filter_input_fields |
| pipeline_created@window | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, time_key, value_input_fields, filter_input_fields |
| pipeline_created@window | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, time_key, value_input_fields, filter_input_fields |
| pipeline_created@window | win_rate@window | abstain | needs_review | value_expr, where_expr, time_key, value_input_fields, filter_input_fields |
| sal_to_sql_rate@window | sla_compliance@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| sal_to_sql_rate@window | speed_to_lead_median_min@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| sal_to_sql_rate@window | sql_to_opp_rate@window | related_candidate | needs_review | where_expr |
| sal_to_sql_rate@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| sla_compliance@window | speed_to_lead_median_min@window | abstain | needs_review | value_expr, where_expr, value_input_fields, filter_input_fields |
| sla_compliance@window | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| sla_compliance@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| speed_to_lead_median_min@window | sql_to_opp_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |
| speed_to_lead_median_min@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, value_input_fields, filter_input_fields |
| sql_to_opp_rate@window | win_rate@window | abstain | needs_review | source_ref, value_expr, where_expr, segment_expr, group_by, value_input_fields, filter_input_fields |

## Dimension differences

The JSON report records the full raw and normalized expressions, prerequisite statuses and both source/compiled locations for every pair. Differences below preserve the original literals and predicates.

### avg_sales_cycle_days@window / mql_to_sal_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"stage = 'SAL'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["stage"]`.

### avg_sales_cycle_days@window / mql_volume@month

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_mqls"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"count(*)::double"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `null`.
- **period_expr** (contradicted): left `"cast('2025-09-01' as date)"`; right `"cohort_month"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `"grouping sets ((cohort_month, segment), (cohort_month))"`.
- **time_key** (contradicted): left `null`; right `"cohort_month"`.
- **grain** (contradicted): left `"window"`; right `"month"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `[]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `[]`.

### avg_sales_cycle_days@window / mql_volume@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_mqls"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"count(*)::double"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `null`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `[]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `[]`.

### avg_sales_cycle_days@window / pipeline_created@month

- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **period_expr** (contradicted): left `"cast('2025-09-01' as date)"`; right `"created_month"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `"grouping sets ((created_month, segment), (created_month))"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **grain** (contradicted): left `"window"`; right `"month"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["created_month", "is_net_new_pipeline"]`.

### avg_sales_cycle_days@window / pipeline_created@window

- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["created_month", "is_net_new_pipeline"]`.

### avg_sales_cycle_days@window / sal_to_sql_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"stage = 'SQL'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["stage"]`.

### avg_sales_cycle_days@window / sla_compliance@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"met_sla is not null"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["met_sla"]`.

### avg_sales_cycle_days@window / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"response_minutes is not null"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["response_minutes"]`.

### avg_sales_cycle_days@window / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"stage = 'Opportunity'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["stage"]`.

### avg_sales_cycle_days@window / win_rate@window

- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"is_won and sales_cycle_days is not null"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **value_input_fields** (contradicted): left `["sales_cycle_days"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["is_won", "sales_cycle_days"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### mql_to_sal_rate@window / mql_volume@month

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_mqls"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"count(*)::double"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `null`.
- **period_expr** (contradicted): left `"cast('2025-09-01' as date)"`; right `"cohort_month"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((cohort_month, segment), (cohort_month))"`.
- **time_key** (contradicted): left `null`; right `"cohort_month"`.
- **grain** (contradicted): left `"window"`; right `"month"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `[]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `[]`.

### mql_to_sal_rate@window / mql_volume@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_mqls"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"count(*)::double"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `null`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `[]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `[]`.

### mql_to_sal_rate@window / pipeline_created@month

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **period_expr** (contradicted): left `"cast('2025-09-01' as date)"`; right `"created_month"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((created_month, segment), (created_month))"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **grain** (contradicted): left `"window"`; right `"month"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_to_sal_rate@window / pipeline_created@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_to_sal_rate@window / sal_to_sql_rate@window

- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"stage = 'SQL'"`.

### mql_to_sal_rate@window / sla_compliance@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"met_sla is not null"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["met_sla"]`.

### mql_to_sal_rate@window / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"response_minutes is not null"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["response_minutes"]`.

### mql_to_sal_rate@window / sql_to_opp_rate@window

- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"stage = 'Opportunity'"`.

### mql_to_sal_rate@window / win_rate@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"stage = 'SAL'"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### mql_volume@month / mql_volume@window

- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.

### mql_volume@month / pipeline_created@month

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `null`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"created_month"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((created_month, segment), (created_month))"`.
- **time_key** (contradicted): left `"cohort_month"`; right `"created_month"`.
- **value_input_fields** (contradicted): left `[]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_volume@month / pipeline_created@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `null`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"cohort_month"`; right `"created_month"`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_volume@month / sal_to_sql_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `null`; right `"stage = 'SQL'"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `null`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["stage"]`.

### mql_volume@month / sla_compliance@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `null`; right `"met_sla is not null"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["met_sla"]`.

### mql_volume@month / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `null`; right `"response_minutes is not null"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["response_minutes"]`.

### mql_volume@month / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `null`; right `"stage = 'Opportunity'"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `null`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["stage"]`.

### mql_volume@month / win_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `null`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **period_expr** (contradicted): left `"cohort_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((cohort_month, segment), (cohort_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"cohort_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `[]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### mql_volume@window / pipeline_created@month

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `null`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **period_expr** (contradicted): left `"cast('2025-09-01' as date)"`; right `"created_month"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `"grouping sets ((created_month, segment), (created_month))"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **grain** (contradicted): left `"window"`; right `"month"`.
- **value_input_fields** (contradicted): left `[]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_volume@window / pipeline_created@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(sum(opp_amount), 2)"`.
- **where_expr** (contradicted): left `null`; right `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`.
- **time_key** (contradicted): left `null`; right `"created_month"`.
- **value_input_fields** (contradicted): left `[]`; right `["opp_amount"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["created_month", "is_net_new_pipeline"]`.

### mql_volume@window / sal_to_sql_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `null`; right `"stage = 'SQL'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `[]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["stage"]`.

### mql_volume@window / sla_compliance@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `null`; right `"met_sla is not null"`.
- **value_input_fields** (contradicted): left `[]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["met_sla"]`.

### mql_volume@window / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `null`; right `"response_minutes is not null"`.
- **value_input_fields** (contradicted): left `[]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["response_minutes"]`.

### mql_volume@window / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `null`; right `"stage = 'Opportunity'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `[]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["stage"]`.

### mql_volume@window / win_rate@window

- **source_ref** (contradicted): left `"fct_mqls"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"count(*)::double"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `null`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **value_input_fields** (contradicted): left `[]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `[]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### pipeline_created@month / pipeline_created@window

- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `"grouping sets ((segment), ())"`.
- **grain** (contradicted): left `"month"`; right `"window"`.

### pipeline_created@month / sal_to_sql_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"stage = 'SQL'"`.
- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `null`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["stage"]`.

### pipeline_created@month / sla_compliance@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"met_sla is not null"`.
- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["met_sla"]`.

### pipeline_created@month / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"response_minutes is not null"`.
- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["response_minutes"]`.

### pipeline_created@month / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"stage = 'Opportunity'"`.
- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `null`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["stage"]`.

### pipeline_created@month / win_rate@window

- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **period_expr** (contradicted): left `"created_month"`; right `"cast('2025-09-01' as date)"`.
- **group_by** (contradicted): left `"grouping sets ((created_month, segment), (created_month))"`; right `"grouping sets ((segment), ())"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **grain** (contradicted): left `"month"`; right `"window"`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### pipeline_created@window / sal_to_sql_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"stage = 'SQL'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["stage"]`.

### pipeline_created@window / sla_compliance@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"met_sla is not null"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["met_sla"]`.

### pipeline_created@window / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"response_minutes is not null"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["response_minutes"]`.

### pipeline_created@window / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_opportunities"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"stage = 'Opportunity'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["stage"]`.

### pipeline_created@window / win_rate@window

- **value_expr** (contradicted): left `"round(sum(opp_amount), 2)"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **time_key** (contradicted): left `"created_month"`; right `null`.
- **value_input_fields** (contradicted): left `["opp_amount"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["created_month", "is_net_new_pipeline"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### sal_to_sql_rate@window / sla_compliance@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`.
- **where_expr** (contradicted): left `"stage = 'SQL'"`; right `"met_sla is not null"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["met_sla"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["met_sla"]`.

### sal_to_sql_rate@window / speed_to_lead_median_min@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_leads"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"stage = 'SQL'"`; right `"response_minutes is not null"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["response_minutes"]`.

### sal_to_sql_rate@window / sql_to_opp_rate@window

- **where_expr** (contradicted): left `"stage = 'SQL'"`; right `"stage = 'Opportunity'"`.

### sal_to_sql_rate@window / win_rate@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"stage = 'SQL'"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### sla_compliance@window / speed_to_lead_median_min@window

- **value_expr** (contradicted): left `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`; right `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`.
- **where_expr** (contradicted): left `"met_sla is not null"`; right `"response_minutes is not null"`.
- **value_input_fields** (contradicted): left `["met_sla"]`; right `["response_minutes"]`.
- **filter_input_fields** (contradicted): left `["met_sla"]`; right `["response_minutes"]`.

### sla_compliance@window / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_leads"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"met_sla is not null"`; right `"stage = 'Opportunity'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `["met_sla"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["met_sla"]`; right `["stage"]`.

### sla_compliance@window / win_rate@window

- **source_ref** (contradicted): left `"fct_leads"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"round(avg(case when met_sla then 1.0 else 0.0 end), 4)"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"met_sla is not null"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **value_input_fields** (contradicted): left `["met_sla"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["met_sla"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### speed_to_lead_median_min@window / sql_to_opp_rate@window

- **source_ref** (contradicted): left `"fct_leads"`; right `"fct_funnel_conversion"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`; right `"conversion_rate"`.
- **where_expr** (contradicted): left `"response_minutes is not null"`; right `"stage = 'Opportunity'"`.
- **segment_expr** (contradicted): left `"coalesce(segment, 'All')"`; right `"segment"`.
- **group_by** (contradicted): left `"grouping sets ((segment), ())"`; right `null`.
- **value_input_fields** (contradicted): left `["response_minutes"]`; right `["conversion_rate"]`.
- **filter_input_fields** (contradicted): left `["response_minutes"]`; right `["stage"]`.

### speed_to_lead_median_min@window / win_rate@window

- **source_ref** (contradicted): left `"fct_leads"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"round(percentile_cont(0.5) within group (order by response_minutes), 1)"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"response_minutes is not null"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **value_input_fields** (contradicted): left `["response_minutes"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["response_minutes"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.

### sql_to_opp_rate@window / win_rate@window

- **source_ref** (contradicted): left `"fct_funnel_conversion"`; right `"fct_opportunities"`.
- **value_expr** (contradicted): left `"conversion_rate"`; right `"round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)"`.
- **where_expr** (contradicted): left `"stage = 'Opportunity'"`; right `"is_closed and opp_amount >= 1000\n      and \n        (date_diff('day', created_date::timestamp, close_date::timestamp ))\n     >= 7"`.
- **segment_expr** (contradicted): left `"segment"`; right `"coalesce(segment, 'All')"`.
- **group_by** (contradicted): left `null`; right `"grouping sets ((segment), ())"`.
- **value_input_fields** (contradicted): left `["conversion_rate"]`; right `["is_won"]`.
- **filter_input_fields** (contradicted): left `["stage"]`; right `["close_date", "created_date", "is_closed", "opp_amount"]`.
