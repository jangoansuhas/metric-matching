# Independent Review: Metric Matching Study Protocol

**Reviewer:** Independent Automated Review (Person-2)
**Date:** 2026-10-03
**Repository:** `jangoansuhas/metric-matching`
**Scope:** Study protocol, rubric, calibration packet, and experimental reproducibility

---

## Verdict: Minor Revision Required

This study protocol describes an inter-rater reliability study for labelling semantic relationships between dbt metric pairs. The protocol is well-designed, methodologically sound, and the practice calibration pairs are fully reproducible. However, the study is **incomplete** (only calibration materials are present; main evaluation packets are missing), and there are several rubric clarity issues and methodological concerns that should be addressed before publication.

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Reproducibility** | PASS | All 3 calibration pairs reproduced exactly |
| **Methodology** | Sound | Standard inter-rater design with adjudication |
| **Rubric Clarity** | Issues Found | 3 ambiguity risks identified in label definitions |
| **Completeness** | Incomplete | Missing main packets, results, and paper manuscript |

---

## 1. Experiment Results

### 1.1 Environment Verification

All setup checks passed exactly as documented:

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Jaffle-shop commit | `7be2c58...` | `7be2c58...` | PASS |
| dbt-core version | 1.12.5 | 1.12.5 | PASS |
| dbt-duckdb version | 1.11.0 | 1.11.0 | PASS |
| dbt seed | PASS=6 ERROR=0 | PASS=6 ERROR=0 | PASS |
| dbt build | PASS=43 ERROR=0 TOTAL=46 | PASS=43 ERROR=0 TOTAL=46 | PASS |
| Metric count | 19 metrics | 19 metrics | PASS |

### 1.2 CAL-01: `revenue` vs `food_revenue`

| Property | `revenue` | `food_revenue` |
|----------|-----------|----------------|
| Source file | order_items.yml L90-95 | order_items.yml L108-113 |
| Measure expression | `SUM(product_price)` | `SUM(CASE WHEN is_food_item THEN product_price ELSE 0 END)` |
| Semantic model | order_item (order_items table) | order_item (order_items table) |
| Grain | One row per order item | One row per order item |
| Time dimension | ordered_at | ordered_at |
| Filter | None | Inline CASE (food items only) |
| Overall total | 637,444 | 240,877 |

**Key facts:** `food_revenue` is a strict subset of `revenue`. Verified: `revenue = food_revenue + drink_revenue` (637,444 = 240,877 + 396,567). Same table, same grain, same time dimension, but `food_revenue` applies an inline CASE filter restricting to food items only. Values differ at every month.

**My label:** `temporal_or_scope_variant` — shared measure concept (`SUM(product_price)`) with a changed population filter (food items only). Evidence status: `sufficient`.

### 1.3 CAL-02: `lifetime_spend_pretax` vs `order_total`

| Property | `lifetime_spend_pretax` | `order_total` |
|----------|------------------------|---------------|
| Source file | customers.yml L73-78 | orders.yml L124-129 |
| Measure expression | `SUM(lifetime_spend_pretax)` | `SUM(order_total)` |
| Semantic model | customers (customers table) | orders (orders table) |
| Grain | One row per customer | One row per order |
| Time dimension | `first_ordered_at` | `ordered_at` |
| What it sums | Pre-tax subtotals (=637,444) | Order totals including tax (=671,425) |
| Overall total | 637,444 | 671,425 |

**Key facts:** These metrics differ in **three fundamental ways**:
1. **Different grain:** Customer-level vs order-level
2. **Different values:** Pre-tax (637,444) vs including tax (671,425); difference = 33,981 in tax
3. **Different time dimension:** `first_ordered_at` (customer's first order) vs `ordered_at` (each order's date); monthly breakdowns are completely incomparable

**My label:** `related` — both derive from order subtotals, but differ in tax inclusion, grain, and time dimension. Too many differences for `cross_grain_equivalent`. Evidence status: `sufficient`.

> **Rubric stress test:** This pair is the most interesting for testing the rubric. A reviewer might be tempted to call it `cross_grain_equivalent` or `temporal_or_scope_variant`. The rubric should explicitly address pairs with *multiple simultaneous differences*.

### 1.4 CAL-03: `order_total` vs `order_cost`

| Property | `order_total` | `order_cost` |
|----------|---------------|--------------|
| Source file | orders.yml L124-129 | order_items.yml L96-101 |
| Measure expression | `SUM(order_total)` | `SUM(order_cost)` |
| Semantic model | orders (orders table) | orders (orders table) |
| Grain | One row per order | One row per order |
| Time dimension | ordered_at | ordered_at |
| What it sums | Revenue + tax per order | Supply cost per order |
| Overall total | 671,425 | 131,788 |

**Key facts:** `order_total` is customer-facing revenue (subtotal + tax), while `order_cost` is supplier-facing cost. Completely different economic concepts. Same grain and time dimension. Their difference is approximately the gross profit (a derived metric already defined in the project).

**Note:** `order_cost` is declared in `order_items.yml` (L96-101) but references the `order_cost` measure from the `orders` semantic model (`orders.yml` L119-121). This cross-file reference could confuse reviewers.

**My label:** `related` — documented semantic connection via gross profit, but fundamentally different economic concepts. Evidence status: `sufficient`.

### 1.5 Data Quality Checks

| Check | Result | Impact |
|-------|--------|--------|
| NULL product_price values | 0 out of 90,900 items | No NULL-handling edge cases |
| NULL supply_cost values | 0 out of 90,900 items | No NULL-handling edge cases |
| Customers without orders | 0 | No LEFT JOIN NULL issues |
| order_total = subtotal + tax_paid | 0 mismatches | Tax decomposition is exact |
| Item type coverage | 20,081 food + 70,819 drink = 90,900 | Perfect partition, no "neither" |

> **Concern:** Practice data is too clean. Zero NULLs in all key columns, perfect partitions. Real dbt projects often have NULLs and ambiguous categorizations. Reviewers won't practice the hardest parts of the rubric during calibration.

---

## 2. Study Design Evaluation

### 2.1 Strengths

- **Rigorous reproducibility controls.** Pinned commit SHA, exact dependency versions, SHA-256 integrity checks on worksheets, and read-only protocol. Above-average for annotation studies.
- **Clear separation of roles.** Reviewer A / B / Adjudicator C design with anonymous codes, no live discussions. Best practices.
- **Well-structured rubric.** Six labels cover the expected relationship space well, from exact equivalence through conflict to non-match. Tie-breaking rules reduce ambiguity.
- **Honest handling of uncertainty.** `needs_review` status and "unresolved" adjudication outcome. Methodologically mature.

### 2.2 Concerns

**C1 (Major): Reviewer A is the paper's first author.** The adjudicator knows which reviewer is the author, creating unconscious anchoring bias. Standard practice is fully blinded codes. **Recommendation:** Blind the adjudicator to reviewer identity, or recruit a second independent reviewer.

**C2: Only DuckDB is supported.** Ties metric behavior to DuckDB SQL semantics. If the paper claims generalizability to "dbt metrics" broadly, this limitation must be stated.

**C3: Sample size unknown.** Only 3 practice pairs from one project. Statistical power depends on unreleased main-round packets.

**C4: No AI restriction is appropriate but limits scalability.** Paper should discuss how the protocol scales and what the downstream use of the labeled dataset is.

**C5: Windows is untested.** Either test the Windows path or restrict to macOS/Linux.

---

## 3. Rubric Evaluation

### 3.1 Label Definition Issues

**R1: `cross_grain_equivalent` is under-specified.** Doesn't specify: (a) who specifies the rollup — must it be documented or can the reviewer infer it? (b) What counts as "aligned time" when grains use different time dimensions?

**R2: `temporal_or_scope_variant` vs `related` boundary is blurry.** What counts as a "shared measure concept"? Are inline CASE expressions in measure `expr` "filters"?

**R3: Multiple simultaneous differences not addressed.** The rubric doesn't guide reviewers when a pair differs on 2+ axes simultaneously. Should add a decision tree.

### 3.2 Missing Rubric Guidance

| Gap | Scenario | Suggested Resolution |
|-----|----------|---------------------|
| Cross-file declarations | Metric in file X, measure in file Y | Add a note about tracing across files |
| Derived metrics as comparands | Pair includes a derived metric | Clarify whether to trace through derivation |
| Default time dimension | `agg_time_dimension` affects monthly comparisons | Document in reviewer guide |
| Measure vs metric filter | CASE in `expr` vs MetricFlow `filter:` | State whether inline CASE counts as "filter" |

---

## 4. Recommendations

### 4.1 Required Changes (before publication)

| # | Issue | Action | Severity |
|---|-------|--------|----------|
| 1 | Author as Reviewer A (C1) | Blind adjudicator or add second independent reviewer | **Major** |
| 2 | Main evaluation packets missing | Add held-out packets | **Major** |
| 3 | `cross_grain_equivalent` under-specified (R1) | Add criteria for "aligned time" and rollup specification | Moderate |
| 4 | Multi-axis difference guidance (R3) | Add decision tree for multi-difference pairs | Moderate |
| 5 | CASE vs filter ambiguity (R2) | Clarify in rubric | Moderate |

### 4.2 Suggested Improvements (not blocking)

| # | Suggestion | Rationale |
|---|-----------|-----------|
| 6 | Test Windows setup or restrict to macOS/Linux | Untested setup = reproducibility risk |
| 7 | Include practice pair with NULL data | Calibrate reviewers for hardest cases |
| 8 | Note about cross-file metric declarations | CAL-03's `order_cost` spans two files |
| 9 | Document `agg_time_dimension` in reviewer guide | Critical for monthly comparison semantics |
| 10 | State DuckDB limitation in paper | Results may not generalize to other SQL engines |
| 11 | Report inter-rater agreement statistics | Cohen's kappa / Krippendorff's alpha needed |
| 12 | Clarify downstream use of labeled dataset | Affects required sample size |

---

## 5. Appendix: Experiment Environment

- **Python:** 3.12.15
- **dbt-core:** 1.12.5
- **dbt-duckdb:** 1.11.0
- **dbt-metricflow:** 0.15.0
- **DuckDB:** 1.5.6
- **OS:** macOS ARM64
- **Jaffle-shop commit:** `7be2c5838dbdeca8e915d4e46db70e910753d7f6`

All experiments run on 2026-10-03. All commands and results are logged in the HTML version of this report.
