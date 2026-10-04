# Synthetic pilot evidence

All seven cases are constructed; their labels are not an accuracy estimate.

| Case | Decision | Sample values | Key observation |
| --- | --- | --- | --- |
| Opportunity booking passthrough and `total_` alias | `direct_equivalent` | O1: 100 = 100 | Cards identify one source measure and aligned rules; sample rows agree |
| Account ARR and filtered opportunity ARR rollup | `provisional_cross_grain_equivalent` | R1: 150 = 150 | One mapping per eligible opportunity and matching sample rollup; source rules and historical snapshots still need independent validation |
| Updated live product quote and frozen booking | `temporal_or_scope_variant` | P1: 120 vs 100 | Annotated rules differ: business_state, time_rule, filters |
| Pipeline stage filter expanded in simulated v1 | `candidate_definition_drift` | O1: None vs 100 | Simulated version change; changed signature fields: filters |
| Rollup using a duplicated hierarchy mapping | `needs_review` | R1: 150 vs 250 | Eligible detail rows lack exactly one hierarchy mapping |
| Account views agree, but one card omits time | `needs_review` | R1: 150 = 150 | Missing card fields: right.time_rule |
| Customer and product counts happen to agree | `non_match` | all: 2 = 2 | Distinct annotated business concepts; sample counts may coincide |

The alias is supported by supplied cards and SQL in this fixture. The cross-grain decision is **provisional**: the mapping check and matching rows establish only a sample result. The fanout and missing-time cases abstain. The pipeline change is a **candidate** drift, not a claim that the change was unintended.

Downstream models flagged for the constructed pipeline change: `sales_pipeline_dashboard`, `executive_forecast`. This dependency graph was provided by hand.

Run `python3 pilot.py --check` to recreate the machine-readable `report.json`. See `README.md` for scope and limitations.
