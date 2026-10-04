# Compiled Jaffle numeric declaration eligibility (development only)

Frozen packet SHA-256: `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`. Rules and source hashes are in JSON.
19 exposed declarations; 171 unordered pairs retained.

| Declaration state | Metrics |
| --- | ---: |
| `eligible_declaration_only` | 9 |
| `unknown` | 10 |

| Pair state | Pairs |
| --- | ---: |
| `at_least_one_unknown` | 135 |
| `both_eligible_declaration_only` | 36 |

`eligible_declaration_only` means a simple metric has one measure entry, a unique owner with an exact semantic-model manifest dependency, a declared numeric aggregate, and no unresolved template in the relevant declaration. The frozen packet authenticates extraction, but a card alone does not independently verify that measure's name in the source YAML. It is **not** `certified_numeric`. Derived, ratio, cumulative and templated declarations remain unknown. The generated SQL was not executed; no semantic pair label, accuracy, or candidate Recall@k follows.
