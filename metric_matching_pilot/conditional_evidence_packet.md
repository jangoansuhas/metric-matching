# Label-free GTM conditional-decision input

Pinned `jross21/gtm-funnel-analytics@a71232c123a5fb78da9b52d4246950ee48591c00`; dbt 1.11.6.
11 branch cards and 55 unordered pairs. The packet has no labels, row totals, or reconciliation outcomes.

| ID | Source ref | Value expression | WHERE | Grain / grouping | Review |
| --- | --- | --- | --- | --- | --- |
| `avg_sales_cycle_days@window` | `fct_opportunities` | `round(percentile_cont(0.5) within group (order by sales_cycle_days), 1)` | `is_won and sales_cycle_days is not null` | `grouping sets ((segment), ())` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `mql_to_sal_rate@window` | `fct_funnel_conversion` | `conversion_rate` | `stage = 'SAL'` | `—` | field_lineage_not_traced, jinja_not_expanded |
| `mql_volume@month` | `fct_mqls` | `count(*)::double` | `—` | `grouping sets ((cohort_month, segment), (cohort_month))` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded |
| `mql_volume@window` | `fct_mqls` | `count(*)::double` | `—` | `grouping sets ((segment), ())` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `pipeline_created@month` | `fct_opportunities` | `round(sum(opp_amount), 2)` | `is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)` | `grouping sets ((created_month, segment), (created_month))` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `pipeline_created@window` | `fct_opportunities` | `round(sum(opp_amount), 2)` | `is_net_new_pipeline and created_month between cast('2025-09-01' as date) and cast('2026-03-31' as date)` | `grouping sets ((segment), ())` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `sal_to_sql_rate@window` | `fct_funnel_conversion` | `conversion_rate` | `stage = 'SQL'` | `—` | field_lineage_not_traced, jinja_not_expanded |
| `sla_compliance@window` | `fct_leads` | `round(avg(case when met_sla then 1.0 else 0.0 end), 4)` | `met_sla is not null` | `grouping sets ((segment), ())` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `speed_to_lead_median_min@window` | `fct_leads` | `round(percentile_cont(0.5) within group (order by response_minutes), 1)` | `response_minutes is not null` | `grouping sets ((segment), ())` | field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded |
| `sql_to_opp_rate@window` | `fct_funnel_conversion` | `conversion_rate` | `stage = 'Opportunity'` | `—` | field_lineage_not_traced, jinja_not_expanded |
| `win_rate@window` | `fct_opportunities` | `round((count(*) filter (where is_won))::double / nullif(count(*), 0), 4)` | `is_closed and opp_amount >= 1000       and          (date_diff('day', created_date::timestamp, close_date::timestamp ))      >= 7` | `grouping sets ((segment), ())` | dbt_macro_not_expanded, field_lineage_not_traced, grouping_sets_not_expanded, grouping_sets_row_groups_not_expanded, jinja_not_expanded, source_macro_compiled_expansion_requires_review |

Each card also records the source and compiled lines, period and segment expressions, field-use names and seven explicitly unknown semantics in JSON. Refs and headers are syntactic provenance, and unexpanded grouping and unknown time/NULL/rounding rules prevent an equivalence assertion.

The package requires the pinned repository and local dbt compiled artifacts to reproduce; these are outside the ZIP. See `conditional_method_contract.md` for the method boundary. Neither this table nor its ordering is a gold label or method feature.
