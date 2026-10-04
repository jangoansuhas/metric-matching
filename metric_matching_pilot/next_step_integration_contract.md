# Development integration contract — September 27, 2026

This page fixes the interpretation of the three concurrent implementation probes **before** their reports are combined. It does not freeze the proposed method, the held-out search frame, a classification threshold, or an evaluation claim. Previously inspected Jaffle, Sidemantic, GTM, and Rill projects remain development cases. No additional repository may be relabeled held-out after inspection.

## Common unit and provenance

- For GTM's long-format table, identify a branch by `(metric_name, grain)` at one pinned Git revision. A branch outputs a scalar `value` within its explicit period and segment scope. Its source relation, query filter, grouping sets and input fields are evidence attributes, not relationship labels.
- Compiled dbt SQL and `manifest.json` are artifacts from a local dbt 1.11.6 build of GTM commit `a71232c123a5fb78da9b52d4246950ee48591c00`. The manifest's compiled code for `fct_metric_values` matches its compiled SQL file. Record an artifact hash and avoid treating that local compilation as a native semantic-engine evaluation or independent gold label.
- The two versioned GTM source revisions `f387f822ab65f94bb2d04691ed0288ec3cdb17a2` and `a4c122762b910a6a1c847e3d1a4999a5162db00a` are adjacent. `fct_metric_values.sql` has no Git source diff across that edge. The earlier model-level report finds a changed-token upstream path from `int_leads__unified.sql` to `fct_metric_values.sql`: `from contacts c` became `from contacts as c`. This appears syntactically cosmetic but has not been compiled or executed at both revisions. Stable local branch text serves as a negative control for *local* source edits and cannot prove identical runtime outputs when upstream dependencies change.

## Acceptance checks for the separate outputs

| Output | Check | If missing |
| --- | --- | --- |
| Compiled field provenance | All emitted branch IDs correspond to the pinned source branch inventory; cite both source and compiled artifact provenance; distinguish a traced field from a relation-level `ref()` and retain ambiguous stars, joins, macros and grouping semantics for review. | Report partial coverage and an explicit unsupported/review status; do not infer source-row equivalence. |
| Source-aware candidates | Enumerate the entire 11-branch universe and give the same candidates to each name-only and source-aware retriever. Expose features, weights, ties and abstention without reading selected labels, fixture outcomes, or source-row equality as a scoring signal. | Keep diagnostic examples outside a measured Recall@k or accuracy claim. |
| Versioned branches | Read both pinned Git trees, enumerate branches and link only explicit stable IDs. Record both source locations and whether expression/filter/grain/time/grouping changed; source equality cannot imply behavior preservation through dependencies. | Mark unresolved events, not observed runtime changes. |

## Synthesis rule

The separate reviewer should inspect raw reports and code, then state what the three outputs establish together, where they disagree, and which unresolved feature prevents the next claim. This is an **AI integration review**, not independent human annotation, an accuracy evaluation, or conference peer review. Revise overclaims in the paper and scripts before packaging. The next gate is a source-aware method and context-fair baselines frozen on development projects, followed by a dated search-result manifest, independent human judgments on complete anchor candidate universes, and held-out evaluation. An industrial benefit claim additionally needs approved private sampling and measured maintainer decisions.
