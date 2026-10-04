# Independent AST mask baseline — Jaffle I1 development packet

This baseline reads the unchanged `compiled_jaffle_i1_packet.json` (SHA-256
`78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`),
at public source commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`.
The packet contains **19 cards and all 171 unordered pairs**, pair-set SHA-256
`0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`.
The existing `verify_packet()` checks pinned local source against Git blobs,
compiled and model hashes, source spans, pair order, and scope metadata. The
new comparator imports that integrity check only; its AST parser, mask rule,
documentation gate, and decisions are independent of `probe_signal()` and
`scoped_mask_decision.py`. It reads neither their results nor any labels.

## Rule and coverage

The dependency-free parser tokenizes SQL and builds explicit `Column`, `Case`,
and `SumSelect` nodes. It accepts only a single ungrouped `SELECT SUM(expr) AS
name FROM relation alias`, where `expr` is one column or one `CASE WHEN flag
THEN column ELSE 0 END`. It rejects extra clauses, projections, nested
expressions, and unsupported syntax. Both generated arguments must match
their source-declared measure-expression ASTs; the generated relation and
output alias must match the unique source owner and metric name. The pair must
have the same semantic model, model node, relation, aggregation time, and
source-model content. The flag must have one `is_<term>_item` domain term
(excluding obvious `no`/`non`/`not` prefixes) and appear as a bare qualified
field projection in the pinned owner model, rather than a `NOT` or `OR`
expression at that boundary.
Both metrics must be simple, unfiltered sums without fill or timespine rules.

The masked metric's **pinned declaration description** must name the base
metric concept and a meaningful flag term (for example, `revenue` and
`drink`/`drinks`). Both descriptions are checked against their exact pinned
declaration spans. Only then does the rule emit
`temporal_or_scope_variant`. This is a class prediction about a changed
contribution scope at the **ungrouped compiled scope**, not an equality,
numeric subset, or safe substitution assertion.

| Output/reason | Pairs |
| --- | ---: |
| `temporal_or_scope_variant` (`documented_ast_mask`) | 2 |
| `abstain`: unsupported card shape | 147 |
| `abstain`: incompatible compiled scope | 18 |
| `abstain`: unsupported AST shape | 3 |
| `abstain`: other mask pairing | 1 |
| **Total** | **171** |

Across the 19 cards, three have the supported source-aligned AST shape, one
simple card has unsupported syntax, and 15 are outside the narrowly specified
card shape. Every pair remains in the denominator; failures abstain. The
18 mixed-scope pairs are never compared as if the compiled query had a common
grouping. This is exact-pattern parser coverage, not general SQL AST coverage.

| Pair and output | Pinned source-linked evidence |
| --- | --- |
| `drink_revenue` / `revenue`: `temporal_or_scope_variant` | [`case when is_drink_item then product_price else 0 end`, measure lines 79–82](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L79-L82) versus [`product_price`, measure lines 71–74](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L71-L74); metric descriptions at [114–119](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L114-L119) and [90–95](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L90-L95). The masked description says “The revenue from drinks in each order.” |
| `food_revenue` / `revenue`: `temporal_or_scope_variant` | [`case when is_food_item then product_price else 0 end`, measure lines 75–78](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L75-L78) versus [`product_price`, measure lines 71–74](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L71-L74); metric descriptions at [108–113](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L108-L113) and [90–95](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml#L90-L95). The masked description says “The revenue from food in each order.” |

Both use the pinned [`order_items.sql` owner model](../public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.sql#L43-L53), SHA-256
`f6268350d0266dc7b23e662349e4c94a9e1d9f4689765055ba7c5ea07d82a06c`,
and the same `order_item` semantic model, `"dev"."main"."order_items"`
relation, and `ordered_at` aggregation time. Generated SQL hashes are
`3e1d04e6f6a6ac412fdab159503b76feb0ae180b59f8a63900c293e0bf09d613`
for drink, `682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110`
for food, and `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134`
for base revenue.

## Comparison and claim boundary

**Exact development tie:** the separate scoped-mask rule reports the same
two pair IDs and the same **2 class outputs / 169 abstentions** on this packet.
AST recognition of this `CASE` mask plus linked declarations and a description
gate therefore yields no distinct output or incremental coverage here. The
pattern, source linkage, and abstention alone do not establish method novelty.
What remains testable is a versioned metric-maintenance decision with explicit
unmet prerequisites and measured human-correct actions on an independently
judged evaluation; this static I1 comparison does not test that claim.

**Guard caveat:** this baseline's lexical description rule is broader than an
exact Jaffle description or literal food/drink flag whitelist. Another
single-domain `is_<term>_item` flag with matching prose could pass the lexical
check. A direct projection in `order_items.sql` does **not** verify how that
field was defined in the upstream products/staging model. A misleadingly named
flag or a negated/composite upstream definition could therefore support a
wrong class prediction on another packet. The pinned source and text checks
support only this bounded structural reading, not a general affirmative flag
semantics guarantee. The rule does not verify boolean truth/NULL behavior.
Aligned grouped MetricFlow SQL,
time grain, missing-group handling, price sign, and any numeric ordering are
also unresolved. Food and drink exhaustiveness is unproven. These outputs are
method predictions, **not human gold, accuracy, or a superiority result**.
No held-out source, worksheet, built values, or proposed-method output was used
as a decision input.

## Reproduction

Run `python3 -B metric_matching_pilot/ast_mask_baseline.py` from the workspace
root. It prints all 171 pair outcomes as JSON to stdout and writes no other
files. Bounded counterfactual checks confirmed that extra `WHERE`, `JOIN`,
`GROUP BY`, or projection syntax, an altered `ELSE`, or a missing/edited
description makes the selected comparison abstain. In-memory adversarial
mutations of the **paired cards**, without changing the pinned packet, gave:

| Mutation | Pair-function result |
| --- | --- |
| `CASE WHEN NOT is_food_item` | `abstain`, `unsupported_ast` |
| `CASE WHEN is_food_item OR is_drink_item` (also parenthesized) | `abstain`, `unsupported_ast` |
| Owner-model projection `NOT products.is_food_item AS is_food_item` | `abstain`, `flag_not_directly_projected` |
| Owner-model projection `products.is_food_item OR products.is_drink_item AS is_food_item` | `abstain`, `flag_not_directly_projected` |
| Flag names `is_not_food_item` and `is_food_or_drink_item` | `abstain`, `non_atomic_or_negative_flag_name` |

These checks exercise the supported boundary and do not establish upstream
classification. The pinned packet and
source integrity check passed, and the two selected pair IDs were verified
against the full denominator.
