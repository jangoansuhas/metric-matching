# Scoped aggregate-mask class output (development only)

The unchanged I1 packet SHA-256 is `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`; its complete
19-metric/171-pair set SHA-256 is `0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`. The source and
generated SQL hashes and declaration spans are rechecked by
`development_decision_probe.py` before this rule runs. It consumes the same two
I1 cards per pair as the frozen comparators; the 18 mixed-scope pairs abstain.

**Method outputs:** 2
`temporal_or_scope_variant` decisions and 169
abstentions, at the cards' **ungrouped compiled scope only**. These are method
predictions, not human gold or accuracy estimates. The earlier conservative
runner is still frozen and has zero decisions; this is a separately versioned
development rule, not a retroactive change to its results.

**Selected pair IDs:** `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.revenue`, `metric.jaffle_shop.food_revenue||metric.jaffle_shop.revenue`.

| Pair | Scoped class output | Source-linked evidence and remaining numerical obligations |
| --- | --- | --- |
| `drink_revenue` / `revenue` | `temporal_or_scope_variant` | Published descriptions: 'The revenue from drinks in each order' / 'Sum of the product revenue for each order item. Excludes tax.'. `case when is_drink_item then product_price else 0 end` at `models/marts/order_items.yml:79–82` vs `product_price` at `models/marts/order_items.yml:71–74`; flag `is_drink_item`; same owner/model/time `order_item` / `"dev"."main"."order_items"` / `ordered_at`; generated SQL hashes `3e1d04e6f6a6ac412fdab159503b76feb0ae180b59f8a63900c293e0bf09d613` / `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134`; owner model `models/marts/order_items.sql` SHA-256 `f6268350d0266dc7b23e662349e4c94a9e1d9f4689765055ba7c5ea07d82a06c` mentions the flag. |
| `food_revenue` / `revenue` | `temporal_or_scope_variant` | Published descriptions: 'The revenue from food in each order' / 'Sum of the product revenue for each order item. Excludes tax.'. `case when is_food_item then product_price else 0 end` at `models/marts/order_items.yml:75–78` vs `product_price` at `models/marts/order_items.yml:71–74`; flag `is_food_item`; same owner/model/time `order_item` / `"dev"."main"."order_items"` / `ordered_at`; generated SQL hashes `682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110` / `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134`; owner model `models/marts/order_items.sql` SHA-256 `f6268350d0266dc7b23e662349e4c94a9e1d9f4689765055ba7c5ea07d82a06c` mentions the flag. |

The class means that both declarations sum the same base expression from the
same semantic model, and one uses an explicit CASE predicate to zero masked
row contributions. Under the packet's broad rubric, this documents a shared
revenue concept with changed contribution scope. It says **nothing** about
numeric subset order, equivalence, whether food and drink exhaust all product
types, NULL-to-zero policy, or substitution at a different grain or time rule.
Fresh day-grain MetricFlow queries and upstream flag tracing are separate
development checks; they are not inputs to this packet-only rule. If they
contradict the scope interpretation, retract or narrow this rule before any
held-out study. The source links remain text-located and parser coverage is
restricted to the exact `SUM(CASE WHEN flag THEN x ELSE 0 END)` versus `SUM(x)`
shape. The additional lexical guard accepts only `is_food_item` or
`is_drink_item` with an affirmative full-description match to “the
<base metric> from <category>[s] in each order.” It also requires the base
card's full “sum of the product <base metric> for each order item. Excludes
tax.” wording and checks both exact descriptions in their pinned declaration
spans. This deliberately narrow development vocabulary abstains on other
categories and alternate legitimate descriptions. It rejects negated and
multi-category flags, missing or contradictory descriptions, and reversed
CASE polarity. `python -B metric_matching_pilot/scoped_mask_guard_checks.py`
checks nine in-memory adversarial card mutations and the exact 2/171 output;
no pinned packet or source file is changed. All other relationships abstain.
No new held-out source or worksheet was inspected, and no method-superiority
claim follows.
