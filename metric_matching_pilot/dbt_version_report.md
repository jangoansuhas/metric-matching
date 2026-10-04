# Bounded dbt SQL adjacent-commit source analysis

Parent `f387f822ab65f94bb2d04691ed0288ec3cdb17a2`, child `a4c122762b910a6a1c847e3d1a4999a5162db00a`; 30 and 33 model SQL files.

## Source-level changes

The analyzer linked models by file path, removed comments and whitespace *outside* strings and Jinja blocks, compared remaining lexical tokens, and built a model-level `ref()` graph. Only token-identical source is labeled a formatting/comment change; everything else requiring semantic interpretation stays `needs_review`.

| Status | Count |
| --- | ---: |
| `added_model` | 3 |
| `needs_review_sql_changed` | 4 |
| `same_nontrivia_token_stream` | 7 |

## Selected trace: `fct_opportunities` and metric descendants

Source [models/marts/core/fct_opportunities.sql:1](https://github.com/jross21/gtm-funnel-analytics/blob/f387f822ab65f94bb2d04691ed0288ec3cdb17a2/models/marts/core/fct_opportunities.sql#L1) → [models/marts/core/fct_opportunities.sql:1](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/core/fct_opportunities.sql#L1): `same_nontrivia_token_stream`. This records stable SQL tokens across a formatting change, not executed dbt equivalence.

Potential downstream models via declared `ref()` edges:

- Depth 1: [models/marts/attribution/int_attribution__opp_touches.sql:12](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/attribution/int_attribution__opp_touches.sql#L12)
- Depth 1: [models/marts/core/fct_leads.sql:31](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/core/fct_leads.sql#L31)
- Depth 1: [models/marts/core/fct_opportunity_stage.sql:12](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/core/fct_opportunity_stage.sql#L12)
- Depth 1: [models/marts/funnel/fct_cohort_progression.sql:17](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/funnel/fct_cohort_progression.sql#L17)
- Depth 1: [models/marts/metrics/fct_metric_values.sql:17](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/metrics/fct_metric_values.sql#L17)
- Depth 2: [models/marts/attribution/fct_attribution.sql:10](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/attribution/fct_attribution.sql#L10)
- Depth 2: [models/marts/core/fct_mqls.sql:6](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/core/fct_mqls.sql#L6)
- Depth 2: [models/marts/funnel/fct_funnel_conversion.sql:13](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/funnel/fct_funnel_conversion.sql#L13)
- Depth 2: [models/marts/funnel/fct_stage_velocity.sql:6](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/funnel/fct_stage_velocity.sql#L6)
- Depth 2: [models/marts/reconciliation/rpt_metric_reconciliation.sql:13](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/reconciliation/rpt_metric_reconciliation.sql#L13)
- Depth 3: [models/marts/attribution/rpt_attribution_by_campaign.sql:4](https://github.com/jross21/gtm-funnel-analytics/blob/a4c122762b910a6a1c847e3d1a4999a5162db00a/models/marts/attribution/rpt_attribution_by_campaign.sql#L4)

## Boundaries

- No dbt compilation or macro expansion at the earlier commit
- No field-level lineage or metric branch extraction from UNION ALL SQL
- Same token stream is a low-level source observation, not a proof of equal runtime results
- Downstream refs mark possible dependency, not changed values or users
- Different tokens get needs_review, including harmless alias/parenthesis refactors

Resolved seed `ref()` edges: 22; unresolved `ref()` edges: 0. The complete model list, paths, statuses, and graph are in the JSON report. This is a development diagnostic, not a measured metric matcher.
