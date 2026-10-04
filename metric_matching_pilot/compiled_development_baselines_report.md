# Compiled Jaffle same-input comparison (development only)

Frozen I1 packet SHA-256: `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`. Pair-set SHA-256: `0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`.
Method file hashes are recorded in the JSON report.
The full frame contains 171 pairs over 19 declared metrics. Three I1 methods run on the 153 same-scope pairs. The common harness retains 18 incompatible-scope pairs and records an abstention for each method.

Declaration-only numeric eligibility: eligible_declaration_only: 9, unknown: 10. No runtime numeric certification follows.

| I1 method | Semantic decisions | Abstentions | Syntax/other signals |
| --- | ---: | ---: | --- |
| `ast_lineage_i1` | 0 | 171 | different_ast_or_lineage_review: 128, different_ast_shared_lineage_review: 24, incompatible_generated_scope: 18, same_ast_and_lineage_review: 1 |
| `constraint_aware_i1` | 0 | 171 | cross_model_source_expression: 108, different_measures_same_model: 34, documented_filter_variant: 10, incompatible_generated_scope: 18, shared_measure_different_definition: 1 |
| `proposed_i1` | 0 | 171 | declared_input_review: 8, filter_scope_review: 10, incompatible_generated_scope: 18, insufficient_relation_evidence: 103, same_model_review: 25, shared_measure_review: 6, time_semantics_review: 1 |

Common decided pairs: **0**.

Proposed source-linked review prompts: **25**; these are questions or test recipes, not semantic decisions. The weaker same-model scores add no prompt.

Candidate-score coverage on the 153 common ungrouped-scope pairs (global ties use lexical pair ID; per-anchor ties use candidate ID):

| Method | Scored pairs | Positive scores |
| --- | ---: | ---: |
| `i0_raw_exact` | 153 / 153 | 0 |
| `i0_normalized_name_exact` | 153 / 153 | 0 |
| `i0_jaro_winkler` | 153 / 153 | 153 |
| `i0_token_jaccard` | 153 / 153 | 47 |
| `i0_soundex` | 153 / 153 | 10 |
| `i1_ast_lineage` | 153 / 153 | 47 |
| `i1_constraint_aware` | 153 / 153 | 11 |
| `i1_proposed` | 153 / 153 | 50 |

Both exact-name rankers score zero on every comparable pair; their recorded order is entirely the lexical tie break.

I0 name scores (exact, normalized exact, Jaro–Winkler, token Jaccard, Soundex) are recorded on the same pair IDs as retrieval signals, not semantic decisions. All I1 methods receive identical label-free cards on the same-scope pairs. The JSON also records per-anchor rankings for the 18 ungrouped declarations. A shared absent metric filter is only declaration-level agreement; base population stays unknown and gives no cross-measure score credit. No human labels or held-out sources enter this report. Syntax agreement, an abstention, and a compiler-generated query are not evidence of classification accuracy, candidate Recall@k, or improved maintenance outcomes. The compiled SQL is DuckDB-only and was not executed.
