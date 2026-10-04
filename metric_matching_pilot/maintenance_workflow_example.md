# Development illustration: metric substitution in a review

**Public source:** dbt-labs/jaffle-shop commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. This is a hypothetical review of a proposed substitution, not an observed PR, user study, or industrial deployment.

**Proposed change:** replace a use of `revenue` with `food_revenue` in an order-item report. A reviewer needs to know whether the two measures can be used interchangeably for the report's day grouping.

> **Metric scope differs; review this substitution.** Both metrics sum an order-item price on the `order_item` semantic model with `ordered_at` as the time dimension. `revenue` sums `product_price`; `food_revenue` sums `CASE WHEN is_food_item THEN product_price ELSE 0 END` (`models/marts/order_items.yml:71–78`, metric declarations `:90–95` and `:108–113`). On the pinned public seeds, the aligned `2024-09-01` group returns **$470.00** for `revenue` and **$86.00** for `food_revenue` (difference **$384.00**). This is a concrete counterexample to equal values for that day on these rows. Confirm that the report is intended to exclude non-food items before accepting the change.

The system's possible class output is `temporal_or_scope_variant`, with source spans and a finite row witness. A user-facing implementation would link the actual changed expression, source declaration and counterexample query, and permit `needs_review` if a required binding or target scope is unsupported. The comparison makes no general subset-value assertion: NULL/missing groups, price sign and other populations remain separate obligations.

The source expressions, query construction and exact input hashes are in `experiment_food_revenue_report.md`; the development rule and independent AST-mask comparator both produce the same two scope-variant predictions on the 171-pair packet. This workflow text was written after observing that development case, so it cannot serve as held-out usability evidence or a measured maintainer-time result. A real evaluation needs a blinded, prespecified review task and recorded reviewer actions.
