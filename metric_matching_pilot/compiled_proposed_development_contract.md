# Compiled-metric proposed method: development contract

**Development rule fixed on September 29, 2026, before the final checked report.**
This is a public Jaffle development diagnostic, not held-out evaluation or
human gold. The input remains `compiled_jaffle_i1_packet.json` v2, SHA-256
`78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`;
the complete 19-declaration frame has 171 unordered pairs and pair-set digest
`0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`.
No selected pair, worksheet, row reconciliation, or prior method output enters
the input. The existing two I1 comparators and this method see the same cards
on 153 ungrouped-scope pairs; a common harness hard-gates the 18 mixed-scope
pairs. I0 methods see names only.

## Numeric declaration gate

Apply the existing generic `generic_metric_eligibility.eligibility` rule to
each exposed metric, with the uniquely owned input measure's declared
aggregation supplied only for a simple metric. First check the generated SQL
hash, source-model digest, unique measure owner, and an exact manifest edge
to that semantic-model resource within the supported packet shape. Jinja in the declaration
or filter, derived/ratio/cumulative type, an ambiguous owner, unsupported
aggregation, or an explicit nonnumeric declared type yields **unknown**. The
positive state is `eligible_declaration_only`, not `certified_numeric`:
SQL generation did not execute rows or establish runtime input types.
Eligibility is reported for all 19 cards; no pair is removed. The older
manifest-only inventory is a comparison point, not a label source or an input.

## Source-backed review hypotheses

Parse the generated SQL with SQLGlot 30.20.0 in DuckDB dialect. Validate its
hash, source-model raw-code digests, and unique measure ownership. A parse or
binding failure abstains with no score. Normalized AST and source evidence may
prioritize review, but cannot assert one of the six semantic relationship
classes without authenticated grain, time, population, join, missing-group,
NULL, units, and snapshot evidence. The fixed rule uses the **first** matching
case; scores are ordinal review priorities, not probabilities:

| Priority | Evidence condition | Review signal | Score |
| --- | --- | --- | ---: |
| 1 | Same normalized ungrouped AST and uniquely owned declared measure, but one declaration is cumulative and the other simple | `time_semantics_review` | 1.0 |
| 2 | Exact manifest metric dependency **and** a matching declared derived/ratio input reference | `declared_input_review` | 0.8 |
| 3 | Same uniquely owned declared measure and differing declared metric filters | `filter_scope_review` | 0.6 |
| 4 | Same normalized AST and uniquely owned declared measure, outside case 1 | `same_ast_review` | 0.5 |
| 5 | Shared uniquely owned declared measure with different AST | `shared_measure_review` | 0.4 |
| 6 | Same nonempty source-model node set, without a shared measure | `same_model_review` (weak co-location signal only; no hypothesis text) | 0.2 |
| 7 | Otherwise | `insufficient_relation_evidence` | 0.0 |

For each signal, record source-linked fields, observed SQL AST/predicate facts,
and a named **unknown** proof obligation (at minimum numeric runtime type,
grain, time, population/filter meaning, join cardinality, missing-group rule,
NULL policy, units, and snapshot). The conditional statement is a question or
test recipe, never an equality or subset assertion. In particular, the
ungrouped `cumulative_revenue` query cannot establish cumulative behavior;
same-measure filtered counts cannot establish population inclusion merely
from a shared declaration; a derived input edge cannot establish equivalence.
Unique measure ownership and a matching physical source relation do **not**
verify compiled field-level lineage; keep that proof obligation unknown.
No semantic taxonomy class is emitted from this packet: `decision=abstain`
for all pairs, regardless of priority score.

Rank all 153 same-scope pair scores globally and separately per each of 18
anchors; break ties lexically by pair ID or candidate metric ID, respectively.
Retain 18 null-score, abstaining mixed-scope pairs in the 171-pair decision
denominator. Report signal and score coverage, but **no** Recall@k, precision,
F1, unsafe-equivalence rate, significance or method superiority without
independently adjudicated reference decisions. A future driver must authenticate
any external evidence artifact's bytes and reviewer provenance before accepting
non-abstaining semantic decisions. No new held-out source may be opened on the
strength of this development run alone.
