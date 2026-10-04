# Final separate integration review — conditional metric matching

**27 September 2026. AI review, not gold or peer review.** The pinned GTM packet remains 11 cards and all 55 unordered pairs, SHA-256 `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`. All three methods read that packet and report its hash and complete pair order. The packet contains no labels, built values, reconciliations, or prior judgments; static inspection finds no outcome-file reads in the decision methods. This establishes no direct runtime label leakage, but does not establish independence from earlier development knowledge.

## Resolution of the earlier defects

- **Grouping false suggestion: resolved for the tested counterfactual.** `conditional_decision_method.py:238–290` now requires every monthly grouping set to contain exactly one month key and a unique one-to-one reduction to window sets without that key. Its positive list-form fixture now removes the key; negative list-form and `GROUPING SETS` fixtures cover retained, missing, and duplicate keys. Independently substituting each real monthly `group_by` into its window card now yields `abstain` and `partition_keys=contradicted` for both MQL and pipeline; the constraint baseline also abstains. This is a bounded syntax check, not a general SQL proof.
- **MQL bounded-window overstatement: resolved as an explicit unknown, not by changing source semantics.** Pinned `models/marts/metrics/fct_metric_values.sql:29–37` still counts all `fct_mqls` without a date predicate; the window's literal start-date label is not a filter. The proposed method separates verified `symbolic_source_ref` from unknown actual `source_membership`, and records `time_key_alignment`, boundaries, and coverage as unknown. The constraint baseline records `window_time_filter`, `time_partition`, and membership as unknown. Both retain an additive `conditional_candidate` but set its evidence status to `needs_review`. The comparison now displays explicit filter evidence, missing and extra months, bounded and all-month sums, and states that an out-of-range MQL would break the claimed bounded rollup. No extra MQL month occurs in the finite build.
- **Status and check-mode overstatement: resolved.** Both conditional candidates and every other result from all three methods are `needs_review` (55/55 each); neither strong method marks the bounded MQL or rounded pipeline mapping sufficient. `constraint_aware_baseline.py --check` now compares regenerated JSON and Markdown bytes and writes only in its non-check branch. The proposed method and comparison also keep `--check` read-only.

## Final same-input results

| Method | Direct | Conditional | Scope variant | Related | Abstain | `needs_review` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Normalized SQL/lineage | 0 | 0 | 2 | 3 | 50 | 55 |
| Constraint-aware v2 | 0 | 2 | 0 | 3 | 50 | 55 |
| Proposed conditional explanation | 0 | 2 | 0 | 0 | 53 | 55 |

Both strong methods propose the same `mql_volume@month/window` and `pipeline_created@month/window` additive hypotheses. The constraint baseline and normalized baseline call the three different-stage funnel pairs related; the proposed method abstains. All three abstain on the other 50 pairs. Different candidate coverage is not a measured accuracy or safety advantage.

## Remaining limits and next gate

The pipeline branches independently compute `ROUND(SUM(opp_amount), 2)` (`fct_metric_values.sql:41–52`). Summing unrounded monthly aggregates and rounding once is a source-level hypothesis requiring inputs other than the published rounded month values; exact equality of displayed values remains unresolved. `COALESCE(segment, 'All')` with `GROUPING SETS` also requires level disambiguation, missing-group and NULL-versus-zero policy. Join cardinality, source membership, time boundaries/zones, units, and snapshot rules remain unknown. The sample comparison has zero bounded deltas, including one absent Enterprise September pipeline group, but finite rows do not prove these rules. The separate Jaffle check has 483 zero-item orders with NULL-sensitive order-level differences before outer join and `COALESCE`; it is outside the 55-pair universe.

No unqualified equivalence or incremental method gain is demonstrated. Freeze syntax support, decisions, input budgets, and review thresholds on development data before a dated held-out manifest. Then use two independent domain-human judgments with adjudication on complete anchor candidate universes, and measure unsafe suggestions, coverage, reviewer effort, and cost by project. Private maintenance claims require authorized owner and outcome evidence.

## Checks performed

- Read-only `--check` passed for the evidence builder, normalized baseline, proposed method, and repaired constraint baseline. Their saved packet/reports matched regeneration.
- The exact requested offline command passed: `uv run --offline --with 'duckdb==1.4.4' --with 'pyyaml==6.0.3' python -B metric_matching_pilot/compare_conditional_development.py --check` → `3 methods, 55 GTM pairs; verified`. It regenerated the GTM DuckDB observations and Jaffle seed check without changing the comparison reports.
- Independent assertions confirmed the common SHA/pair order, **55/55** `needs_review` statuses per method, both repaired grouping counterfactuals, MQL unknown membership/time evidence, and the comparison's explicit MQL no-filter flag and zero extra-month sample observation.

**Changed file:** `metric_matching_pilot/conditional_method_review.md` only. No worker or parent files edited in this review.
