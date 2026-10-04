# GTM source-aware candidate retrieval: development probe

Pinned input: `dbt_metric_branches_report.json` (SHA-256 `0b3a6a785f38baab97305f8f107f3559eae18d35ab5de3abda90387c70831a6c`), `jross21/gtm-funnel-analytics` at `a71232c123a5fb78da9b52d4246950ee48591c00`, `models/marts/metrics/fct_metric_values.sql`.
Algorithm `gtm_source_aware_candidates_v1`; existing lexical functions `development_name_baselines_v1`. All 55 unordered pairs of 11 unique `metric_name@grain` branches are below. Every query ranks the same other 10 branches.

## Fixed scoring rules

Name-only exact, token Jaccard, Jaro–Winkler and Soundex use the existing baseline functions on `metric_name` only. The source-aware score gives **1/7 each** to name token Jaccard and literal equality of source ref, value expression, local WHERE, period-start expression, segment expression and grain. SQL text is not parsed or normalized again. Both absent local WHERE clauses earn syntactic credit. Any field containing Jinja on either side is unscored and contributes zero with the fixed denominator. Scores are rounded to six decimals before ranking; positive ties share a rank range. Zero and abstained scores have no rank. Display ties use branch ID order.

All source-aware decisions abstain on equivalence. The pinned branches contain unexpanded syntax and untraced field lineage; each pair carries an evidence status, flags and per-feature scores in JSON. Unsupported extraction or missing required source fields would abstain from source scoring. No labels, pair IDs, reviewer results or sampled values enter any score.

## All unordered pairs

Scores are retrieval clues, not pair labels. Full bidirectional rank ranges and the ten-candidate list for every query and method are in JSON.

| Branch A | Branch B | Exact | Jaccard | Jaro–Winkler | Soundex | Source-aware |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `avg_sales_cycle_days@window` | `mql_to_sal_rate@window` | 0.000000 | 0.000000 | 0.553704 | 0.000000 | 0.142857 |
| `avg_sales_cycle_days@window` | `mql_volume@month` | 0.000000 | 0.000000 | 0.450000 | 0.000000 | 0.142857 |
| `avg_sales_cycle_days@window` | `mql_volume@window` | 0.000000 | 0.000000 | 0.450000 | 0.000000 | 0.285714 |
| `avg_sales_cycle_days@window` | `pipeline_created@month` | 0.000000 | 0.000000 | 0.476786 | 0.000000 | 0.285714 |
| `avg_sales_cycle_days@window` | `pipeline_created@window` | 0.000000 | 0.000000 | 0.476786 | 0.000000 | 0.428571 |
| `avg_sales_cycle_days@window` | `sal_to_sql_rate@window` | 0.000000 | 0.000000 | 0.572222 | 0.000000 | 0.142857 |
| `avg_sales_cycle_days@window` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.549471 | 0.000000 | 0.285714 |
| `avg_sales_cycle_days@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.488889 | 0.000000 | 0.285714 |
| `avg_sales_cycle_days@window` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.438889 | 0.000000 | 0.142857 |
| `avg_sales_cycle_days@window` | `win_rate@window` | 0.000000 | 0.000000 | 0.397222 | 0.000000 | 0.428571 |
| `mql_to_sal_rate@window` | `mql_volume@month` | 0.000000 | 0.200000 | 0.833333 | 0.000000 | 0.028571 |
| `mql_to_sal_rate@window` | `mql_volume@window` | 0.000000 | 0.200000 | 0.833333 | 0.000000 | 0.171429 |
| `mql_to_sal_rate@window` | `pipeline_created@month` | 0.000000 | 0.000000 | 0.480556 | 0.000000 | 0.000000 |
| `mql_to_sal_rate@window` | `pipeline_created@window` | 0.000000 | 0.000000 | 0.480556 | 0.000000 | 0.142857 |
| `mql_to_sal_rate@window` | `sal_to_sql_rate@window` | 0.000000 | 0.600000 | 0.811111 | 0.000000 | 0.657143 |
| `mql_to_sal_rate@window` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.639087 | 0.000000 | 0.142857 |
| `mql_to_sal_rate@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.125000 | 0.527778 | 0.000000 | 0.160714 |
| `mql_to_sal_rate@window` | `sql_to_opp_rate@window` | 0.000000 | 0.333333 | 0.776768 | 0.000000 | 0.619048 |
| `mql_to_sal_rate@window` | `win_rate@window` | 0.000000 | 0.200000 | 0.413889 | 0.000000 | 0.171429 |
| `mql_volume@month` | `mql_volume@window` | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.714286 |
| `mql_volume@month` | `pipeline_created@month` | 0.000000 | 0.000000 | 0.329167 | 0.000000 | 0.285714 |
| `mql_volume@month` | `pipeline_created@window` | 0.000000 | 0.000000 | 0.329167 | 0.000000 | 0.142857 |
| `mql_volume@month` | `sal_to_sql_rate@window` | 0.000000 | 0.000000 | 0.611111 | 0.000000 | 0.000000 |
| `mql_volume@month` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.565079 | 0.000000 | 0.142857 |
| `mql_volume@month` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.469444 | 0.000000 | 0.142857 |
| `mql_volume@month` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.611111 | 0.000000 | 0.000000 |
| `mql_volume@month` | `win_rate@window` | 0.000000 | 0.000000 | 0.483333 | 0.000000 | 0.142857 |
| `mql_volume@window` | `pipeline_created@month` | 0.000000 | 0.000000 | 0.329167 | 0.000000 | 0.142857 |
| `mql_volume@window` | `pipeline_created@window` | 0.000000 | 0.000000 | 0.329167 | 0.000000 | 0.285714 |
| `mql_volume@window` | `sal_to_sql_rate@window` | 0.000000 | 0.000000 | 0.611111 | 0.000000 | 0.142857 |
| `mql_volume@window` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.565079 | 0.000000 | 0.285714 |
| `mql_volume@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.469444 | 0.000000 | 0.285714 |
| `mql_volume@window` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.611111 | 0.000000 | 0.142857 |
| `mql_volume@window` | `win_rate@window` | 0.000000 | 0.000000 | 0.483333 | 0.000000 | 0.285714 |
| `pipeline_created@month` | `pipeline_created@window` | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.571429 |
| `pipeline_created@month` | `sal_to_sql_rate@window` | 0.000000 | 0.000000 | 0.452778 | 0.000000 | 0.000000 |
| `pipeline_created@month` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.523810 | 0.000000 | 0.142857 |
| `pipeline_created@month` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.563889 | 0.000000 | 0.142857 |
| `pipeline_created@month` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.468056 | 0.000000 | 0.000000 |
| `pipeline_created@month` | `win_rate@window` | 0.000000 | 0.000000 | 0.627976 | 0.000000 | 0.285714 |
| `pipeline_created@window` | `sal_to_sql_rate@window` | 0.000000 | 0.000000 | 0.452778 | 0.000000 | 0.142857 |
| `pipeline_created@window` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.523810 | 0.000000 | 0.285714 |
| `pipeline_created@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.563889 | 0.000000 | 0.285714 |
| `pipeline_created@window` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.468056 | 0.000000 | 0.142857 |
| `pipeline_created@window` | `win_rate@window` | 0.000000 | 0.000000 | 0.627976 | 0.000000 | 0.428571 |
| `sal_to_sql_rate@window` | `sla_compliance@window` | 0.000000 | 0.000000 | 0.659921 | 0.000000 | 0.142857 |
| `sal_to_sql_rate@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.125000 | 0.544444 | 0.000000 | 0.160714 |
| `sal_to_sql_rate@window` | `sql_to_opp_rate@window` | 0.000000 | 0.600000 | 0.840000 | 0.000000 | 0.657143 |
| `sal_to_sql_rate@window` | `win_rate@window` | 0.000000 | 0.200000 | 0.413889 | 0.000000 | 0.171429 |
| `sla_compliance@window` | `speed_to_lead_median_min@window` | 0.000000 | 0.000000 | 0.626804 | 0.000000 | 0.428571 |
| `sla_compliance@window` | `sql_to_opp_rate@window` | 0.000000 | 0.000000 | 0.655556 | 0.000000 | 0.142857 |
| `sla_compliance@window` | `win_rate@window` | 0.000000 | 0.000000 | 0.418651 | 0.000000 | 0.285714 |
| `speed_to_lead_median_min@window` | `sql_to_opp_rate@window` | 0.000000 | 0.125000 | 0.561111 | 0.000000 | 0.160714 |
| `speed_to_lead_median_min@window` | `win_rate@window` | 0.000000 | 0.000000 | 0.430556 | 0.000000 | 0.285714 |
| `sql_to_opp_rate@window` | `win_rate@window` | 0.000000 | 0.200000 | 0.461111 | 0.000000 | 0.171429 |

## Requested month/window diagnostic

`pipeline_created@month` ↔ `pipeline_created@window` is selected **after scoring** for inspection; it is not a judged success. The source ref and value expression match literally, as does the segment projection. The local WHERE includes unexpanded Jinja and receives no credit; period-start expressions and grain differ. GROUPING SETS remain unexpanded, so matching projected segment text does not establish matching segment rows. Month and window are distinct aggregations.

| Query → target | Method | Score | Target rank range | First three positive candidates (score; rank range) |
| --- | --- | ---: | ---: | --- |
| `pipeline_created@month` → `pipeline_created@window` | `exact` | 1.000000 | 1 | `pipeline_created@window` (1.000000; 1) |
| `pipeline_created@month` → `pipeline_created@window` | `token_jaccard` | 1.000000 | 1 | `pipeline_created@window` (1.000000; 1) |
| `pipeline_created@month` → `pipeline_created@window` | `jaro_winkler` | 1.000000 | 1 | `pipeline_created@window` (1.000000; 1), `win_rate@window` (0.627976; 2), `speed_to_lead_median_min@window` (0.563889; 3) |
| `pipeline_created@month` → `pipeline_created@window` | `soundex` | 1.000000 | 1 | `pipeline_created@window` (1.000000; 1) |
| `pipeline_created@month` → `pipeline_created@window` | `source_aware` | 0.571429 | 1 | `pipeline_created@window` (0.571429; 1), `avg_sales_cycle_days@window` (0.285714; 2–4), `mql_volume@month` (0.285714; 2–4) |
| `pipeline_created@window` → `pipeline_created@month` | `exact` | 1.000000 | 1 | `pipeline_created@month` (1.000000; 1) |
| `pipeline_created@window` → `pipeline_created@month` | `token_jaccard` | 1.000000 | 1 | `pipeline_created@month` (1.000000; 1) |
| `pipeline_created@window` → `pipeline_created@month` | `jaro_winkler` | 1.000000 | 1 | `pipeline_created@month` (1.000000; 1), `win_rate@window` (0.627976; 2), `speed_to_lead_median_min@window` (0.563889; 3) |
| `pipeline_created@window` → `pipeline_created@month` | `soundex` | 1.000000 | 1 | `pipeline_created@month` (1.000000; 1) |
| `pipeline_created@window` → `pipeline_created@month` | `source_aware` | 0.571429 | 1 | `pipeline_created@month` (0.571429; 1), `avg_sales_cycle_days@window` (0.428571; 2–3), `win_rate@window` (0.428571; 2–3) |

## Limits

- No complete judged-anchor set for these 11 queries is supplied to this probe; do not calculate accuracy, precision or Recall@k.
- Pair scores retrieve candidates only. All relationship decisions abstain, including identical names or source text.
- Refs identify source relations, not field lineage; upstream filters, cardinality and SQL semantics are not traced.
- GROUPING SETS, Jinja declarations and dbt macros remain unexpanded. Matching segment projections do not prove matching segment rows.
- Month and window are separate aggregation grains; this report uses no sampled values or reconciliation outcomes.
- Equal feature weights and zero credit for unexpanded fields are development heuristics, not learned or calibrated parameters.

This universe has no complete set of judged anchors. No accuracy, precision, Recall@k or effectiveness estimate is reported. Scores and rank positions alone cannot establish cross-grain equivalence.

Reproduce: `python3 metric_matching_pilot/rank_source_aware_candidates.py`. Verify without writing: `python3 metric_matching_pilot/rank_source_aware_candidates.py --check`.
