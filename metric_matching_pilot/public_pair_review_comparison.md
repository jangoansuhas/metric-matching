# Public metric-pair review comparison

Pinned repository revision: `5beb145b00f5465ec759cfcdd9745e858818cf95`. A user-submitted sheet supplied a second label set; its claimed independence was not externally verified. The proposed labels below are analyst recommendations. The author accepted JS-001, JS-005, JS-007, JS-010 on September 27, 2026; no independent adjudicator confirmation is recorded. These are not benchmark ground truth.

| Pair | First label | Submitted label | Recommended label | Author decision |
| --- | --- | --- | --- | --- |
| JS-001 | `related` | `cross_grain_equivalent` | `related` | accepted by author |
| JS-002 | `temporal_or_scope_variant` | `temporal_or_scope_variant` | `temporal_or_scope_variant` | — |
| JS-003 | `temporal_or_scope_variant` | `temporal_or_scope_variant` | `temporal_or_scope_variant` | — |
| JS-004 | `temporal_or_scope_variant` | `temporal_or_scope_variant` | `temporal_or_scope_variant` | — |
| JS-005 | `temporal_or_scope_variant` | `related` | `temporal_or_scope_variant` | accepted by author |
| JS-006 | `related` | `related` | `related` | — |
| JS-007 | `related` | `non_match` | `related` | accepted by author |
| JS-008 | `related` | `related` | `related` | — |
| JS-009 | `non_match` | `non_match` | `non_match` | — |
| JS-010 | `needs_review` | `cross_grain_equivalent` | `temporal_or_scope_variant` | accepted by author |

Initial agreement: 6/10; disagreements: 4/10. Of the four initial disagreements, 4 have author-accepted decisions and 0 remain open. The first analyst revised 1 proposed label after inspecting the submitted review and seed evidence.

## Disagreements

- **JS-001 (orders.order_total / order_items.revenue):** Author accepted: Reject unqualified cross-grain equality. Order item prices reconcile to pretax subtotal, while order_total adds tax. The pinned seeds differ by 3,398,137 cents overall, with nonzero tax on 61,465 orders.
- **JS-005 (order_items.food_revenue / order_items.drink_revenue):** Author accepted: Apply the scope-variant rule consistently to two sibling category predicates over the same product_price SUM, even when neither category is a subset of the other. They are not interchangeable.
- **JS-007 (customers.customers / orders.orders):** Author accepted: The values count different entities, but the repository models a direct customer-to-order relationship and derives orders per customer. Under this taxonomy, that is related, not an unrelated nonmatch.
- **JS-010 (orders.order_total / customers.lifetime_spend):** Author accepted: Revise the first analyst's needs_review label. All-time totals reconcile in the pinned seeds when every order maps to a customer, but default time dimensions are ordered_at versus first_ordered_at; daily values differ on all 365 sample dates. A cross-grain claim is conditional on dropping or aligning time and validating mapping.

The submitted JS-008 label agrees, but its suggested location-rate adjustment is not required by the visible model: `customers.sql` sums the `tax_paid` order field into `lifetime_tax_paid`. The source-backed reconciliation and daily-time counterexample are in `public_seed_reconciliation.md`.

Author-accepted rules: tax-inclusive order total and pretax item revenue are related but not equivalent across grains (JS-001); identical additive input with disjoint category predicates yields a scope variant (JS-005); counts of distinct but directly linked business entities are related when the model explicitly connects them (JS-007); equal all-time sums with different default daily time assignments are a time-rule variant, not unqualified cross-grain equivalence (JS-010). These pairs are not interchangeable.

Next gate: confirm the six initially agreed labels under the frozen annotation rules and identify natural positive equivalents. Obtain independent adjudication or explicitly state the annotation process before freezing a gold-label version. Until then, do not calculate matcher accuracy.
