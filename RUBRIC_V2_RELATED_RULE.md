# Rubric v2 — related/non_match rule (FROZEN on author approval 2026-10-12)

Applies to all v2 labeling and the Study 1 re-label. Class definitions otherwise unchanged from v1 (Table I).

## 2. Rubric v2 — written `related` rule (the v1 boundary)

Classes and their v1 wording are unchanged. Only the `related` vs `non_match` boundary is made explicit. The rule
is **computational**: every condition is checkable from cited source lines, consistent with the task's
evidence-linked definition. Conceptual or business links that cannot be cited do not count.

A pair that is not an equivalence, variant or conflicting definition is **`related`** iff at least one holds at
the pinned commit:

- **R1 Input dependency.** One metric is an input of the other (derived/ratio/cumulative `input_metrics`,
  `numerator`, `denominator`), directly or transitively through other declared metrics.
- **R2 Shared input metric.** Both metrics take the same declared metric as an input (e.g. two ratios with the same
  denominator metric).
- **R3 Shared measure.** Both metrics resolve (after expanding R1 chains) to at least one common semantic-layer
  measure (same semantic model and measure name).
- **R4 Same measure expression.** Both resolve to measures whose `expr` reads the same column of the same
  semantic model, with a different aggregation or filter (e.g. `SUM(amount)` vs `COUNT(amount)`), and the
  difference is not a scope variant.

Otherwise **`non_match`**. In particular, none of these alone makes a pair `related`:
- same semantic model, entity, time dimension or upstream dbt model, with different measures and columns;
- a business-concept link (e.g. both are "unit economics", one is a cost and one a revenue);
- similar names or descriptions.

Tie-breaks: equivalence/variant/conflict classes take precedence over `related`. If whether R1–R4 holds depends on
evidence the packet lacks, use `needs_review` instead of guessing.

Worked examples are taken **only from Jaffle Shop (DEV)**; none is a held-out pair.

