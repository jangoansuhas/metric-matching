# Conditional method comparison on public development cases

Same label-free packet SHA-256 `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`; 11 cards and 55 pairs.
Methods see the same cards and candidate pairs. Decisions are source-backed **candidates**, not gold relationships.

| Method | Decisions | Evidence status |
| --- | --- | --- |
| `normalized_sql_lineage_baseline` | abstain: 50, related_candidate: 3, scope_variant_candidate: 2 | needs_review: 55 |
| `constraint_aware_full_context_v2` | abstain: 50, conditional_candidate: 2, related_candidate: 3 | needs_review: 55 |
| `proposed_conditional_explanation` | abstain: 53, conditional_candidate: 2 | needs_review: 55 |

## Development examples after outputs were fixed

| Pair | `normalized_sql_lineage_baseline` | `constraint_aware_full_context_v2` | `proposed_conditional_explanation` |
| --- | --- | --- | --- |
| `pipeline_created@month` ↔ `pipeline_created@window` | `scope_variant_candidate` (needs_review) | `conditional_candidate` (needs_review) | `conditional_candidate` (needs_review) |
| `mql_volume@month` ↔ `mql_volume@window` | `scope_variant_candidate` (needs_review) | `conditional_candidate` (needs_review) | `conditional_candidate` (needs_review) |
| `mql_to_sal_rate@window` ↔ `sal_to_sql_rate@window` | `related_candidate` (needs_review) | `related_candidate` (needs_review) | `abstain` (needs_review) |
| `pipeline_created@window` ↔ `sla_compliance@window` | `abstain` (needs_review) | `abstain` (needs_review) | `abstain` (needs_review) |

## Row checks kept outside the methods

The local GTM synthetic build covers 2025-09-01, 2025-10-01, 2025-11-01, 2025-12-01, 2026-01-01, 2026-02-01, 2026-03-01. The table sums rounded monthly pipeline cents and counts monthly MQLs before comparing each window scalar. The bounded sum uses only the displayed seven-month range; all-month sum uses every available monthly row.

| Metric | Segment | Month rows | Missing months | Extra months | Bounded sum | All-month sum | Window | Bounded difference | Unit |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| `pipeline_created` | All | 7 | none | none | 688438139 | 688438139 | 688438139 | 0 | cents |
| `pipeline_created` | Enterprise | 6 | 2025-09-01 | none | 256670190 | 256670190 | 256670190 | 0 | cents |
| `pipeline_created` | Mid-Market | 7 | none | none | 271773687 | 271773687 | 271773687 | 0 | cents |
| `pipeline_created` | SMB | 7 | none | none | 159994262 | 159994262 | 159994262 | 0 | cents |
| `mql_volume` | All | 7 | none | none | 2546 | 2546 | 2546 | 0 | count |
| `mql_volume` | Enterprise | 7 | none | none | 230 | 230 | 230 | 0 | count |
| `mql_volume` | Mid-Market | 7 | none | none | 673 | 673 | 673 | 0 | count |
| `mql_volume` | SMB | 7 | none | none | 1643 | 1643 | 1643 | 0 | count |

The pipeline window has the same explicit date predicate as its month branch. The MQL window has no explicit date filter or time key; its constant period label does not bound source rows. No extra MQL month occurs in this build, so the bounded and all-month sums coincide only on this sample. An added out-of-range MQL row could change the window value while leaving the proposed bounded monthly sum unchanged.

The separate Jaffle development check has 483 orders without items: 483 order-level NULL-versus-zero differences before an outer join and COALESCE, 0 afterward; 0 differing daily totals across 365 dates. It is not part of the GTM pair universe or any method's input.

**Interpretation:** Differences in candidate outputs show decisions under bounded syntax and unknown prerequisites, not method accuracy or incremental novelty. A real comparison needs a frozen method, stronger baselines at the same input budget, and independent adjudication on held-out complete anchor universes.

Reproduce with DuckDB 1.4.4 and PyYAML after the pinned GTM build and Jaffle clone: `python3 metric_matching_pilot/compare_conditional_development.py --check`.
