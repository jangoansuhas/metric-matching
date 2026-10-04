# I1 same-input packet (public development only)

Algorithm: `generic_i1_same_input_v1`. Integrated final expression trace SHA256: `0c727e08f3bd4f02bab3b475771c8299aef16145bc85432c94e5e250d0861d5c`.
Input eligibility SHA256: `0e2d601f1dbde17c62716192f6410d78a28f6b76fe21468cca9b6eb5596b8af7`. Model provenance SHA256: `cec3f3770a9ddbc97c5b2f309c543953a4cec19e8b62a327968e21469fce1f15`. Manifest SHA256: `1467a9a6a71de14f196adbab89927083adcc2b9f680f7e9b6256a0720b40fb24`.
All 32 emitted declarations (19 metrics, 13 measures): 496 pairs, SHA256 `67cb4648a0a8f866869208db451d7384f86a9bb38e65126de08e4da0114812b2`. The 19 exposed metrics have 171 separate pairs, SHA256 `8232e9567af68c998560e4c49ba0567dabc93655a95ed866a7d4d8b704aab373`.
Shared I1 canonical packet SHA256: `936fdd4ce9a06189e2d35f05587e6894c74074eb7059844f76c6f09fca35c2de`; I0 name-only packet SHA256: `99ad1b1b8f7ea182d1537b0bdfb23a14a924cde4ab7b668bc2d5d09de67fda96`.
Numeric eligibility: 22 eligible, 10 unknown; pair statuses {'eligible': 231, 'unknown': 265}. Unknown records remain in all pairs.
Trace status: {'needs_review': 32}; 31 unique model candidates, 28 unique linked declared measure expressions, 3 declared metric expressions, 4 declared metric filters. Compiled metric expressions reported verified: 0.
Unknown native semantic prerequisites by field (out of 32 declarations): {'source': 32, 'grain': 32, 'time': 32, 'filter': 32, 'null_policy': 32, 'snapshot': 32, 'population': 32, 'unit': 32, 'join_cardinality': 32, 'transformation': 32}.

## Shared inputs and outputs

| Method | Evidence | Pairs | Semantic decisions | Signal summary |
| --- | --- | ---: | ---: | --- |
| raw_exact v1 | names only | 496 | 0 | name score |
| normalized_name_exact v1 | names only | 496 | 0 | name score |
| jaro_winkler v1 | names only | 496 | 0 | name score |
| token_jaccard v1 | names only | 496 | 0 | name score |
| soundex v1 | names only | 496 | 0 | name score |
| normalized_ast_source v1 | same I1 packet | 496 | 0 | abstain_unverified_ast_or_source: 496 |
| constraint_aware v1 | same I1 packet | 496 | 0 | abstain_no_shared_measure_evidence: 485, shared_declared_measure_review_candidate: 11 |
| source_guided_conditional v1 | same I1 packet | 496 | 0 | abstain_no_shared_context: 339, same_declaration_file_review_candidate: 146, shared_declared_measure_review_candidate: 11 |

All three I1 methods receive identical canonical bytes and pair IDs. The five I0 methods receive the same pair IDs with only qualified IDs and names. An exact shared measure reference creates a review signal only. The 146 same-declaration-file review candidates are weak co-location signals and may be noisy: they are NOT transformation suggestions or conditional equivalence. There is no comparison win. Constraint-aware checks list missing semantic prerequisites; source-guided conditional first uses exact measure references, then the declaration file. No thresholds are tuned.

The normalized AST/source method needs a verified compiled metric expression, owner and normalized AST. The trace contains source-declared expressions and filters, not compiled metric queries or normalized SQL ASTs. This implementation does not perform SQLGlot extraction and cannot claim complete SQLGlot or AST coverage from manifest declarations. It abstains on all 496 pairs.

Soundex uses the English letter groups BFPV=1, CGJKQSXZ=2, DT=3, L=4, MN=5, R=6; the first letter is kept, H/W do not reset adjacency, and the code is four characters. Other I0 scores use the local same-input baseline formulas: raw name equality, camel/punctuation normalized equality, Jaro-Winkler (0.1 prefix weight after Jaro >= 0.7), and token-set Jaccard. The full resource ID identifies a pair but is excluded from the score.

Every I1 semantic decision abstains: the supplied reports do not establish compiled metric-expression lineage or verified source mapping, and native grain, time, filter, NULL behavior, snapshot, population, unit, join cardinality, and transformation prerequisites remain unknown. Source-declared expressions, filters, and measure links are preserved as unverified declarations. A trace claiming `verified` cannot override a source checksum mismatch. The 13 Jaffle compiled model sources remain under review even though compiled files match manifest code.

Pair completeness is only over emitted IDs; malformed declarations could hide an unknown number of other IDs. There is no human gold, accuracy, review-effort or superiority estimate. No held-out source was opened.

## Reproduction

Run `python3 -B metric_matching_pilot/generic_i1_same_input.py --check` to verify this final trace-integrated report byte for byte without writing. `--expression-trace PATH` explicitly selects an alternate trace with matching hash references and 32-ID set. `--no-expression-trace` is an unreported diagnostic fallback and does not match this report.
