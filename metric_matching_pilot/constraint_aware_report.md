# Constraint-aware full-context baseline

Method: `constraint_aware_full_context_v2`. Input SHA-256: `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`.
The input contains 11 cards and every one of their 55 unordered pairs. Decisions are source candidates or abstentions, never equivalence claims.

## Decision counts

| Decision | Pairs |
| --- | ---: |
| `direct_candidate` | 0 |
| `conditional_candidate` | 2 |
| `scope_variant_candidate` | 0 |
| `related_candidate` | 3 |
| `abstain` | 50 |

Evidence status: 0 sufficient for a *source candidate*; 55 need review.

## Method and limits

The method requires identical source references, visible predicates, value projections, field inputs, and segment projections for a month-to-window candidate. It accepts only a simple `COUNT(*)`/`COUNT(field)` or `SUM(field)` additive core, a constant window period label, and grouping sets that match after removing the month key. It treats `ROUND(SUM(field), n)` as an additive *core* with an unresolved rounding condition. SQL comparison changes case and whitespace outside string literals only; it does not rewrite predicates, literals, NULL operators, date bounds, or aliases.

The transformation sums each month partition within its own segment or grand-total grouping set. Missing month/segment keys require explicit zero-fill for a complete comparison; an absent row is not evidence of a zero. A rounded `SUM` requires unrounded monthly inputs and one final rounding operation, unless a reviewer verifies that displayed monthly rounding is harmless. The packet's unbounded count window has no time key or date filter: its period label does not constrain row membership, so the rollup remains a hypothesis needing review. The rounded SUM rollup also needs review because published monthly values may not add exactly to the window value.

A shared source and `conversion_rate` value field with different single `stage =` predicates describes related conversion steps. They receive `related_candidate`, with the filter prerequisite contradicted. This taxonomy does not equate their populations or rates; other same-value predicate differences remain scope variants.

The packet leaves deep upstream field lineage, join cardinality, NULL policy, missing groups, time zone, units, snapshot, and grouping-set row expansion unverified. Window membership, period boundaries, segment `All` collisions, and rounding stay explicit conditions in the JSON. A matching source reference does not prove upstream row membership. The parser abstains on unrecognized grouping or aggregate syntax, complex SUM arguments, nonconstant window labels, and nonadditive AVG, median, and ratio rollups. Jinja and macro expansion, grouping-set rows, and deep field lineage require manual source review wherever the packet flags them. Reviewers must also verify month coverage and window membership, NULL versus zero handling, zero-fill, segment collisions, numeric rounding, upstream joins, units, time-zone boundaries, and snapshot alignment before using any transformation. Source review flags appear with each pair's locations; they are not silently cleared.

No labels, built rows, row reconciliations, selected pair IDs, or tuned thresholds were used. This development output alone does not establish accuracy, a gain over another comparator, or a general equivalence.

## Synthetic checks

- Passed: unbounded window and missing-group/zero-fill prerequisites.
- Passed: AVG/median/ratio nonadditive rejection.
- Passed: rounded SUM additive core with unresolved rounding.
- Passed: different conversion-step predicates remain contradicted.

## Complete pair decisions

Source and compiled file/line evidence and all prerequisite statuses are in the JSON.

| Left | Right | Decision | Evidence status | Immediate reason |
| --- | --- | --- | --- | --- |
| `avg_sales_cycle_days@window` | `mql_to_sal_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `mql_volume@month` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `mql_volume@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `pipeline_created@month` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `avg_sales_cycle_days@window` | `pipeline_created@window` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `avg_sales_cycle_days@window` | `sal_to_sql_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `avg_sales_cycle_days@window` | `win_rate@window` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `mql_to_sal_rate@window` | `mql_volume@month` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `mql_volume@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `pipeline_created@month` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `pipeline_created@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `sal_to_sql_rate@window` | `related_candidate` | `needs_review` | The same source value field is indexed by different stage predicates: these are related conversion steps, not a single measure with an interchangeable scope. |
| `mql_to_sal_rate@window` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_to_sal_rate@window` | `sql_to_opp_rate@window` | `related_candidate` | `needs_review` | The same source value field is indexed by different stage predicates: these are related conversion steps, not a single measure with an interchangeable scope. |
| `mql_to_sal_rate@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `mql_volume@window` | `conditional_candidate` | `needs_review` | Source-supported transformation: sum monthly COUNT(*) outputs across complete, nonoverlapping month partitions for each separate segment/grand-total grouping set. |
| `mql_volume@month` | `pipeline_created@month` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `pipeline_created@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `sal_to_sql_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@month` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `pipeline_created@month` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `pipeline_created@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `sal_to_sql_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `mql_volume@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@month` | `pipeline_created@window` | `conditional_candidate` | `needs_review` | Source-supported additive core SUM(opp_amount): sum unrounded month-level SUM(opp_amount) for each separate segment/grand-total grouping set, then ROUND once to 2 places for the window. Summing displayed rounded monthly outputs is unverified. |
| `pipeline_created@month` | `sal_to_sql_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@month` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@month` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@month` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@month` | `win_rate@window` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `pipeline_created@window` | `sal_to_sql_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@window` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@window` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `pipeline_created@window` | `win_rate@window` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `sal_to_sql_rate@window` | `sla_compliance@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `sal_to_sql_rate@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `sal_to_sql_rate@window` | `sql_to_opp_rate@window` | `related_candidate` | `needs_review` | The same source value field is indexed by different stage predicates: these are related conversion steps, not a single measure with an interchangeable scope. |
| `sal_to_sql_rate@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `sla_compliance@window` | `speed_to_lead_median_min@window` | `abstain` | `needs_review` | Value projections differ; no value transformation is established. |
| `sla_compliance@window` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `sla_compliance@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `speed_to_lead_median_min@window` | `sql_to_opp_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `speed_to_lead_median_min@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
| `sql_to_opp_rate@window` | `win_rate@window` | `abstain` | `needs_review` | Different source relations; common membership is not established. |
