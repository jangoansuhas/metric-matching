# Separate AI review of the paper's readiness

Date: September 27, 2026. After completing the source-only blind review of five development cases, the same separate AI agent read the paper outline and existing public audit reports as a skeptical reviewer. This second phase was **not blind to our manuscript or analyses**. It is an internal critique, not peer review, a human expert judgment, or evidence of conference acceptance.

## What the reviewer found promising

1. The maintenance question is specific: compare versioned metric definitions, explain changes and conditional reconciliations, and identify potentially affected downstream models. The Section 11 signature includes grain, filters, join cardinality, time, units, and incomplete evidence.
2. The public examples expose concrete failure modes. The Jaffle check finds 483 zero-item orders that an ordinary equality test misses under SQL NULL semantics; GTM provides a designed rollup and a direct lineage alias; Rill provides a real expression change whose observed source-row impact has not been measured.
3. The paper already distinguishes candidate retrieval from classification and proposes false-equivalence, abstention, and ablation measurements. These remain proposed experiments.

## Main blockers, ordered by priority

| Priority | Problem in the current record | Minimum convincing next artifact |
| --- | --- | --- |
| 1 | The 5,000-metric, petabyte setting is user-reported context. There is no systematic industrial sample, verified historical incident set, or measured reviewer benefit. | With appropriate access, collect anonymized *versioned definitions and maintenance decisions*; have domain reviewers examine alerts and consumer effects; report misses, false equivalences, effort, and scale in definitions and candidates. Data volume is not matcher throughput. |
| 2 | No end-to-end pipeline has run on the proposed task. The fixture parser covered 0/13 Jaffle model SQL files, 7/23 YAML definitions yielded partial signatures, the classifier consumes handwritten cards, and the real Rill change was inspected manually. | Support a declared SQL/dbt subset from two pinned commits through extraction, candidate retrieval, relationship/change decision, evidence, and consumer impact. Report unsupported cases and extraction coverage on projects not used to develop it. |
| 3 | Selected development controls and a second AI review are not representative ground truth. Original Jaffle proposals had 6/10 initial label agreement and author decisions on four disagreements. Positive controls were selected after inspection. | Freeze a repository/commit sampling protocol before looking at future cases; collect real positives, hard near misses, unchanged refactors, and changes; seek two blind human labels and independent adjudication. Record compared field/row scopes and exact transformation conditions. |
| 4 | Distinct novelty over existing constraint-aware matching and SQL equivalence approaches has not been demonstrated. | Compare prior work by task, inputs, outputs, supported transformations, and evidence; implement/adapt credible constraint and SQL-lineage comparators; show cases where versioned and conditional maintenance evidence changes a reviewer decision. If this fails, report a narrower empirical failure-mode contribution. |
| 5 | No fair comparative effectiveness results exist. Name-only methods and an LLM supplied full metric cards cannot be compared as if they saw the same evidence. | Evaluate candidate Recall@k, classification on given candidates, and end-to-end performance separately on held-out projects. Control context, tune only on development data, and report false equivalence, abstention, cost, and uncertainty across repositories. |

## Decision and changes made

**Assessment:** promising research program, not a submission-ready paper. The evidence supports a feasibility pilot, selected public controls, and a real source change. It does not support matching accuracy, superiority, prevalence, a quantified industrial benefit, or cross-engine portability. The separate agent's review does not make the examples gold labels. Venue fit and deadlines should be checked against the official call before submission decisions.

The companion `heldout_sampling_protocol.md` fixes a *provisional selection and evaluation plan* before new public cases are inspected. The paper outline now distinguishes an unqualified relationship from its conditional transformed counterpart, a metric field from an entire row, and `needs_review` (insufficient evidence) from a business relationship. The next implementation target is one source-linked, commit-to-commit path on a documented SQL/dbt subset, followed by evaluation on newly selected public projects. An industrial claim requires separate permissioned validation.

This is a condensed record of the agent's second-phase review; the five-case source-only review is retained separately in `blind_second_agent_review.md`, with frozen prior labels in `first_labels_for_second_review.json` and an explicit comparison in `second_agent_comparison.md`.
