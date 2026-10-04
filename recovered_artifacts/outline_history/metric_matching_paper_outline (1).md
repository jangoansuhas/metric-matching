# Draft Paper Outline — SANER 2027

## Working title

**Detecting Metric Definition Drift Across Evolving Data Models**

Alternative title:

**When Do Metrics Mean the Same Thing? Detecting Cross-Grain Equivalence in Evolving Enterprise Data Systems**

### Active direction and venue checkpoint (September 27, 2026)

The research object is a **versioned metric definition in a SQL/dbt project**, with narrow public Rill and dbt adapters used to develop the version-comparison path. The maintenance task is to flag definition drift, find duplicated calculations across layers, and identify when two different-grain metrics can be reconciled by an explicit transformation. Section 11 is the current method specification; Sections 12–20 record synthetic and public development evidence; Section 21 records a separate AI agent's source-blind review and manuscript critique; Section 22 fixes a prospective sampling protocol; Section 23 runs an automated Rill commit comparison; Section 24 records a bounded dbt version check and the supported interim conclusions; Section 25 records parallel branch extraction, name baselines, and an evaluation contract; Section 26 integrates compiled field provenance, source-aware retrieval, a versioned branch control and a separate AI review; Section 27 compares a conditional method with two full-context baselines on the same development pairs. Earlier framework and evaluation sections are background that must be revised around measured evidence.

SANER 2027 Research Track required a mandatory abstract by September 21; its paper deadline is September 25. The Industrial Track has a mandatory abstract deadline of October 19 and paper deadline of October 23. The Industrial Track is the working SANER 2027 route if an industrial evaluation can be completed; the Short Papers track shares the October dates and could fit a smaller public study. Industrial review is single blind; Short Papers review is double anonymous. No acceptance or submission is assumed. Official calls: https://conf.researchr.org/track/saner-2027/saner-2027-papers , https://conf.researchr.org/track/saner-2027/saner-2027-industrial-track , https://conf.researchr.org/track/saner-2027/saner-2027-short-papers-and-posters-track .

**Venue recheck, September 27.** The Industrial full-paper call asks for a systematic evaluation or investigation in real-world applications (ten pages plus up to two reference pages); the Short Papers call asks for original unpublished results (six pages including references). The Registered Report track is a separate plan-first route: October 30 abstract and November 6 initial report, six pages plus one reference page. Its Stage 1 report is **not published in the SANER proceedings**; the later study/publication path depends on the track outcome. If a defensible industrial evaluation or original short-paper result is not ready by the October deadlines, a sufficiently precise study design might suit that separate route. Track choice remains open until the evidence and method are reviewable. Official calls: https://conf.researchr.org/track/saner-2027/saner-2027-industrial-track , https://conf.researchr.org/track/saner-2027/saner-2027-short-papers-and-posters-track , https://conf.researchr.org/track/saner-2027/saner-2027-registered-report-track .

## Paper decision

This is a paper about **enterprise metric matching**, not generic student-record deduplication. Student records may later serve as a small external validation, but they will not be part of the main claim.

The paper must not claim that Jaccard, Jaro-Winkler, Soundex, direct matching, or Mistral Large are novel. The proposed technical contribution is to extract and compare **versioned, typed metric signatures** from SQL and lineage, produce an explicit reconciliation or drift explanation, and measure whether that helps maintain data models. Its novelty and effectiveness still require comparison with close prior work and completed experiments.

## One-sentence thesis

Changes to SQL/dbt models can preserve a metric's name while altering its grain, filters, time semantics, or source lineage; comparing versioned metric signatures could expose these maintenance risks and explain when two metrics are equivalent or require reconciliation.

## Current evidence and hypotheses

### Evidence already provided

- Approximately 5,000 enterprise metrics exist in the industrial setting, calculated over petabyte-scale data.
- The candidate approaches are direct matching, Soundex, Jaro-Winkler, Jaccard, and Snowflake-hosted Mistral Large.
- Preliminary observations are that Mistral Large is more useful when rich context is centralized in one table; Jaccard is more useful when relevant tokens are scattered across tables; and Jaro-Winkler is useful for sequential files with deterministic naming rules.
- The present public evidence uses pinned SQL/dbt repositories, published seeds, and local DuckDB execution. Public Snowflake data could extend a later evaluation; the current record contains no Snowflake benchmark. Industrial data must remain private, with only permissioned and anonymized aggregate results considered for publication.

### Hypotheses to test, not claims to make yet

- H1: Including metric grain, snapshot semantics, hierarchy, filters, and lineage improves classification over name-only matching.
- H2: A typed signature that includes SQL expression structure and lineage improves detection of changed definitions across commits compared with text-only and LLM-only baselines.
- H3: An explicit grain/time reconciliation check reduces false-equivalence decisions on tempting pairs such as current product value versus frozen booking value.
- H4: Ranking findings by downstream model impact and sending incomplete signatures to review reduces maintenance review effort at a controlled false-equivalence rate.

## Draft abstract structure (150–200 words)

1. **Problem:** Large enterprises accumulate multiple metric definitions across source, foundational, functional, and presentation data layers. Similar names often hide different grains, filters, time semantics, or business states; conversely, equivalent metrics can be implemented in different tables and at different grains.
2. **Gap:** Existing schema matching and entity matching techniques do not explicitly classify enterprise metric relationships such as cross-grain equivalence, temporal variants, and definition conflicts.
3. **Approach:** Introduce a metric-definition representation and a topology-aware matching framework that combines direct, phonetic, lexical, and LLM-based methods with a human-review path.
4. **Evaluation:** Evaluate the framework on a public, reproducible Snowflake-derived benchmark and an anonymized industrial validation involving approximately 5,000 metrics.
5. **Contribution:** Report effectiveness, cost, and scalability by relationship type and data topology; provide the benchmark generator, labels, code, prompts, and raw experimental outputs.

## 1. Introduction (about 1 page)

### 1.1 Motivation

- A business concept such as revenue, ARR, or pipeline is frequently defined more than once across teams and data layers.
- Multiple definitions create reconciliation work, incorrect reporting, duplicate logic, inconsistent backfills, and difficulty promoting trusted definitions to a shared foundational layer.
- Existing metadata catalogs typically make names discoverable but do not determine whether two metrics are equivalent, related, conflicting, or safe to substitute.

### 1.2 Concrete motivating example

Use anonymized versions of the supplied metrics:

- `account_net_revenue`: account-grain ARR for an account hierarchy, including discounts and excluding fraud accounts.
- `crm_revenue_net`: opportunity-grain ARR, rolled up across the same account hierarchy, restricted to opportunity stages 7 and 8 and excluding fraud opportunities.

The intended relationship is not row-level duplication. It is **cross-grain equivalence**: after rolling the opportunity metric to the account hierarchy and aligning snapshot dates, the values are expected to agree.

### 1.3 Research problem

Given a set of metric definitions distributed across tables, models, files, and versions, identify the relationship between each candidate pair:

- Direct equivalent
- Cross-grain equivalent
- Temporal or scope variant
- Related but not interchangeable
- Conflicting definition
- Non-match
- Ambiguous / needs human review

### 1.4 Contributions

Write these conservatively after results exist:

1. A versioned metric-signature representation and a bounded comparison procedure that issues evidence-backed relationship and definition-change labels.
2. A public set of metric-definition changes and reconciliations that tests maintenance decisions rather than name matching alone.
3. A completed comparison against lexical, LLM-only, and SQL/lineage baselines, with an anonymized industrial validation if feasible.

## 2. Background and Problem Formulation (about 1 page)

### 2.1 Metric-definition representation

Represent a metric as:

`m = (name, description, formula, source, grain, hierarchy, time_semantics, filters, lineage)`

The framework should never treat a name match as proof of metric equivalence.

### 2.2 Relationship taxonomy

Define each label precisely and give a positive and negative example. In particular:

- **Direct equivalent:** Same quantity under the same grain, scope, and time semantics.
- **Cross-grain equivalent:** Same quantity after an explicit, valid transformation such as grouping opportunity-level values to an account hierarchy.
- **Temporal/scope variant:** Same general concept, but different as-of date, snapshot rule, period, population, or filter.
- **Related but not interchangeable:** Shared business domain without a safe substitution rule; for example, booked revenue and pipeline revenue.
- **Conflicting definition:** Similar label but incompatible business meaning; for example, a metric called “booked revenue” that actually measures cash received.
- **Non-match:** No meaningful shared definition; for example, customer count and product count.
- **Ambiguous:** Insufficient metadata or organization-specific language; for example, position name and role name.

### 2.3 Cross-grain equivalence example

For account `a` and snapshot `t`, the two metrics are cross-grain equivalent only if the same account hierarchy, time rule, fraud exclusions, discount treatment, and opportunity-stage semantics are applied. This is a testable reconciliation rule, not a string-similarity judgment.

### 2.4 Data topology

Classify the context available to a matcher:

- **Centralized:** Rich name, description, formula, and lineage context in one table/model.
- **Fragmented:** The relevant signals are distributed across models, tables, lineage edges, or repository files.
- **Sequential/evolutionary:** Definitions occur in file or version sequences with deterministic naming conventions and historical change.

## 3. Related Work and Boundary of Novelty (about 1 page)

### 3.1 Schema matching and data discovery

- Rahm and Bernstein survey automatic schema matching.
- Cupid is a classic schema-matching system.
- Valentine provides scenarios, benchmark fabrication, and large-scale evaluation for tabular schema matching.

### 3.2 Entity resolution

- DeepMatcher and Ditto evaluate learned entity matching.
- Recent LLM entity-matching work studies pairwise, comparative, and selection strategies.

### 3.3 LLM schema matching

- Recent work evaluates LLM schema matching using names and descriptions and compares it with string similarity, including Jaro-Winkler.
- ConStruM packs structured, query-specific context for an LLM given a candidate shortlist; supplying context to an LLM is therefore prior work, not our novelty (https://arxiv.org/abs/2601.20482).

### 3.4 SQL/computation equivalence

- Query-equivalence work, such as GEqO, targets semantic equivalence of executable SQL subexpressions at scale.

### 3.5 Our boundary

The paper must not claim to replace schema matching, entity resolution, or formal SQL verification. Its intended scope is matching **business metric definitions** with multi-signal metadata, including relationship classes that matter for data-system maintenance and metric governance. Constraint-Guided Enterprise Data Mapping already uses structural/granularity constraints and bounded LLM disambiguation (https://arxiv.org/abs/2608.24218); ConStruM organizes context for candidate selection (https://arxiv.org/abs/2601.20482); GEqO studies equivalent computations (https://arxiv.org/abs/2401.01280); and Valentine supplies schema-matching evaluation methodology (https://arxiv.org/abs/2010.07386). The possible added value here is *versioned maintenance evidence*: which SQL change altered a metric, which consumers are affected, and whether a documented cross-grain reconciliation still holds. Compare task, inputs, outputs, transformations, and evidence against these systems, then show on held-out cases that the versioned/conditional outputs change a decision. This difference remains a hypothesis, not an established novelty claim.

## 4. Earlier framework sketch (to be revised after Section 11 pilot; about 1.5 pages)

### 4.1 Input normalization

Create a metric card from metadata and code:

- normalized name and aliases
- natural-language definition
- source model/table
- SQL or simplified formula
- grain
- hierarchy relationship
- snapshot/period semantics
- filters and exclusions
- lineage/dependencies

### 4.2 Candidate generation

Use inexpensive methods to avoid exhaustive pairwise LLM calls:

- Direct normalized-name and identifier match
- Soundex for phonetic/naming variants
- Jaro-Winkler for near-string variants and sequential naming conventions
- Jaccard over token sets from names, descriptions, lineage, and formulas

Measure candidate-generation recall separately from final classification accuracy.

### 4.3 Context-aware classification

- Build pair-level context from the metric cards.
- Use Mistral Large only where sufficient context exists and the candidate cannot be safely resolved by lexical rules.
- Require structured output: label, confidence, evidence fields, and a human-review recommendation.

### 4.4 Topology-aware router

The proposed router uses context completeness, number of source objects, lineage depth, and sequential-version signals to select or combine matchers. This is a proposed contribution and needs empirical validation.

### 4.5 Validation and human review

- Verify cross-grain equivalence through specified aggregation and reconciliation rules.
- Route ambiguous and conflicting pairs to human review.
- Record reviewer decisions as new labeled data, but do not claim active learning unless it is actually implemented and evaluated.

## 5. Earlier benchmark sketch (to be revised after Section 11 pilot; about 1.25 pages)

### 5.1 Public reproducible benchmark

- Use public Snowflake data for scale and reproducibility.
- Construct metric definitions and controlled variants from public tables; Snowflake sample data alone does not provide ground-truth duplicate metric definitions.
- Produce centralized, fragmented, and sequential scenarios.
- Inject documented transformations: renames, abbreviations, token reordering, source/table changes, grain changes, time-window changes, hierarchy rollups, and filter changes.

### 5.2 Ground truth

- Define labels before running models.
- Have at least two annotators independently label naturally occurring examples, with adjudication for disagreement.
- Separate constructed labels from manually curated labels in the results.

### 5.3 Industrial validation

- Use an anonymized enterprise corpus of approximately 5,000 metrics over petabyte-scale data.
- Do not publish raw data, schema names, customer identifiers, or internal code.
- Publish only aggregated results, a sanitized methodology, and reproducible public substitutes.

### 5.4 Open-science artifact

Release an anonymous repository containing the benchmark generator, input schema, labels, code, SQL, prompts, model/version settings, raw outputs, tests, and reproduction instructions.

## 6. Earlier evaluation sketch (to be revised after Section 11 pilot; about 1.25 pages)

### Research questions

- **RQ1:** How accurately do direct matching, Soundex, Jaro-Winkler, Jaccard, and Mistral Large classify metric relationships across the topology categories?
- **RQ2:** Does the topology-aware router improve macro-F1 and reduce review burden compared with any single method?
- **RQ3:** What are the runtime, warehouse-compute cost, and candidate-reduction trade-offs at increasing corpus sizes?
- **RQ4:** To what extent do results on the public benchmark transfer to the private industrial validation?

### Baselines

- Direct matching
- Soundex
- Jaro-Winkler
- Jaccard
- Mistral Large with a fixed structured prompt
- At least one strong schema-matching baseline or a documented reason it cannot be applied fairly

### Measures

- Per-label precision, recall, F1, and macro-F1
- Candidate-generation recall
- False-equivalence rate, especially for related-but-not-interchangeable pairs
- Human-review rate and reviewer agreement
- Runtime, throughput, Snowflake credits/cost, and LLM invocation count
- Sensitivity to missing descriptions, lineage, and formulas

### Experimental controls

- Keep public and industrial evaluation sets separate.
- Prevent leakage between templated or version-related metric definitions.
- Pin model name/version, prompt, structured-output schema, region, temperature, and run date.
- Report confidence intervals or repeated runs where model output is nondeterministic.

## 7. Results (about 1.25 pages)

This section must contain completed experiments, not planned claims.

Suggested tables and figures:

1. Dataset and label distribution.
2. Accuracy by method and relationship label.
3. Accuracy by topology category.
4. Candidate-reduction, runtime, and cost results.
5. Router ablation: without topology, without lineage, without formula, and without LLM.
6. Error analysis of representative false positives and false negatives.
7. Anonymized industrial-validation summary.

## 8. Discussion, Threats to Validity, and Maintenance Implications (about 0.75 pages)

- Constructed public data may not fully represent industrial naming and governance practices.
- Public metadata may have appeared in LLM training data.
- Business definitions may be organization-specific and require review.
- Model availability, behavior, and pricing can change; fully document the run configuration.
- Cross-grain equivalence depends on correct hierarchy and snapshot alignment.
- Explain how the approach supports data-system evolution: metric promotion, refactoring, reconciliation, ownership, and prevention of duplicate logic.

## 9. Conclusion (about 0.25 pages)

Restate the measured findings, the practical implications for maintaining evolving data systems, and the availability of the public benchmark and artifacts. Do not make general claims beyond the evaluated topologies and datasets.

## Page budget for a 10-page SANER paper

| Section | Target pages |
| --- | ---: |
| Introduction | 1.0 |
| Background/problem formulation | 1.0 |
| Related work | 1.0 |
| Framework | 1.5 |
| Benchmark/artifacts | 1.25 |
| Evaluation design | 1.25 |
| Results | 1.25 |
| Discussion/threats | 0.5 |
| Conclusion | 0.25 |
| **Total** | **9.0** |

Reserve the remaining page for figure/table expansion and ensure references fit within SANER's additional reference-page allowance.

## Immediate next steps

1. Completed: run the small, public, synthetic SQLite pilot in Section 12; this is a feasibility check, not a SQL/dbt implementation or evaluation result.
2. Completed: the metric owner confirmed the account/opportunity business rule on September 27; production history has not been checked. The initial fixture-only SQL extractor is described in Section 13.
3. Completed the pinned public-project diagnostic, three bounded lineage probes, ten first-analyst pair proposals, a comparison with a user-submitted second label set, and a pinned-source audit of the six initial agreements in Sections 14–18. The author decided all four initial disagreements. Section 19 records a *conditional* cross-grain candidate from a second public repo using the same Jaffle Shop data: a built dbt test misses 483 NULL-versus-zero order discrepancies, and both declared measures agree across 365 dates when queried via Sidemantic 0.8.2. Section 20 adds executed positive controls from a different synthetic GTM repo and an actual Rill commit that changed zero-denominator handling. Section 21 records a separate AI source-only review of five development cases and a subsequent paper-readiness critique. These are not human labels or a held-out evaluation.
4. Written a prospective public sampling protocol (Section 22), before selecting further test repositories. Implemented a narrow automated real Rill two-commit source path (Section 23): 16 measures linked by declared ID, two changes classified, and dashboard declarations located. This does not parse arbitrary dbt SQL, perform cross-view matching, or establish row impact.
5. Completed a bounded dbt SQL token/ref source check on a real formatting-heavy commit (Section 24). Section 25 adds individual metric-branch source extraction, name-only candidate diagnostics, and an annotation contract. Section 26 adds limited compiled field provenance, all-pair source-aware ranking and metric-branch linking across a real commit pair. Next build **a source-aware decision method** that resolves or abstains on grain, joins, missing groups, time and dependencies; compare it to normalized SQL/lineage, constraint-aware, and context-fair LLM baselines on development projects. Freeze the method, search frame, and thresholds before opening held-out projects, then obtain independent human judgments. An Industrial Track effectiveness claim additionally needs permissioned decisions and measured maintainer outcomes.

## Next collaborative step

The separate AI agent's blind review and manuscript critique are in Section 21; Section 22 fixes a prospective public sampling plan. Section 23 executes a **narrow Rill two-commit adapter**; Section 24 checks a real dbt SQL commit for token-preserving refactors and unresolved source changes. Section 25 extracts bounded GTM metric branches, compares four name-only rankers on selected cases, and audits the evaluation protocol. Section 26 traces some compiled field paths, ranks all 55 GTM branch pairs, compares 11 branches across adjacent Git revisions, and records a separate AI synthesis. **Next: make a source-aware conditional decision on supported development cases and audit likely cosmetic edit alerts against stronger normalized-SQL baselines; then freeze configuration and the search-result manifest before inspecting new held-out projects.** Domain-aware humans must independently judge complete anchor universes and disputed cases. This step needs no company code or Snowflake account. A comparative or industrial conclusion remains conditional on new evidence.

## References to verify and cite

- E. Rahm and P. A. Bernstein, “A Survey of Approaches to Automatic Schema Matching,” *VLDB Journal*, 2001.
- J. Madhavan, P. A. Bernstein, and E. Rahm, “Generic Schema Matching with Cupid,” *VLDB*, 2001.
- C. Koutras et al., “Valentine: Evaluating Matching Techniques for Dataset Discovery,” *ICDE*, 2021. https://arxiv.org/abs/2010.07386
- C. Koutras et al., “Valentine in Action: Matching Tabular Data at Scale,” *PVLDB*, 2021. https://www.vldb.org/pvldb/vol14/p2871-koutras.pdf
- Y. Li et al., “Deep Entity Matching with Pre-Trained Language Models,” *PVLDB*, 2021. https://arxiv.org/pdf/2004.00584
- M. Parciak et al., “Schema Matching with Large Language Models: an Experimental Study,” *VLDB TaDA Workshop*, 2024. https://www.vldb.org/workshops/2024/proceedings/TaDA/TaDA.8.pdf
- B. Haynes et al., “GEqO: ML-Accelerated Semantic Equivalence Detection,” 2024 preprint. https://arxiv.org/pdf/2401.01280
- H. Chen, Z. Zhang, and H. V. Jagadish, “ConStruM: A Structure-Guided LLM Framework for Context-Aware Schema Matching,” 2026 preprint. https://arxiv.org/abs/2601.20482
- S. Monka et al., “Constraint-Guided Enterprise Data Mapping with Large Language Models,” 2026 preprint. https://arxiv.org/abs/2608.24218

## 10. Metric-Card and Labeling Protocol

This protocol describes *candidate annotations* for a possible public benchmark and anonymized industrial validation. Only independent labeling, evidence review, and adjudication can produce ground truth. Apply its decision rules before methods are run so labels do not change to favor an algorithm.

### 10.1 Annotation unit

An annotation unit is a **pair of metric cards**, not merely two metric names. A card may use simplified SQL and redacted object names; it must never contain customer-level data.

### 10.2 Metric-card template

```text
Metric ID:
Metric name and aliases:
Business definition:
Source model/table:
Native grain:
Hierarchy rule:
Time/snapshot semantics:
Formula or simplified SQL logic:
Filters/exclusions:
Dimensions or grouping keys:
Lineage/dependencies:
Known owner/team (optional and anonymized for publication):
Evidence source (documentation, model code, test, or reconciliation query):
```

### 10.3 Pair-label template

```text
Pair ID:
Metric A ID:
Metric B ID:
Compared scalar / grouping keys / row scope:
Relationship label:
Evidence status: sufficient / needs_review (missing fields):
Expected transformation, if any:
Transformation preconditions (time, filters, joins, missing rows, units):
Expected value relationship:
Evidence supporting the label:
Known exceptions or assumptions:
Annotation confidence: high / medium / low
First annotator:
Second annotator:
Adjudication decision:
```

### 10.4 Label decision rules

| Label | Use only when | Do not use when |
| --- | --- | --- |
| Direct equivalent | Both metrics measure the same quantity at the same grain, scope, and time semantics. | A rollup, time alignment, or filter change is required. |
| Cross-grain equivalent | A documented, deterministic transformation makes the metrics equal for aligned inputs. | The relationship is only approximately correlated or expected to differ by design. |
| Temporal/scope variant | The same business concept differs because of snapshot, period, population, hierarchy, or filters. | The definitions are incompatible rather than scoped differently. |
| Related but not interchangeable | The metrics share a business domain but cannot be substituted safely. | A deterministic equivalence transformation exists. |
| Conflicting definition | Similar names or documentation assert the same concept, but the calculation means something materially different. | The names merely happen to be similar. |
| Non-match | The metrics do not share a meaningful business definition. | Organization-specific context could establish a relationship. |

`needs_review` / ambiguous is an **evidence status**, not a seventh business relationship. Record it separately with the missing grain, source mapping, population, time rule, or runtime evidence. A pair may be `related` at its unqualified native outputs and conditionally cross-grain equivalent after a documented transformation; record both scopes rather than forcing one unconditional equivalence label. `temporal_or_scope_variant` requires evidence of one conceptual measure with a changed time, state, population, or filter. Mere shared domain without that explicit variation is `related`.

### 10.5 General annotation rules

1. A name match is never sufficient evidence of equivalence.
2. Grain, snapshot semantics, hierarchy, filters, and exclusions must be compared before issuing an equivalence label.
3. If a metric requires a transformation, write the transformation explicitly. Do not use “same after aggregation” without specifying the aggregation keys and filters.
4. If the evidence is incomplete, label the pair **ambiguous / human review** rather than guessing.
5. Record the reason a pair is a non-match. Random negative examples alone are not enough.
6. Keep constructed public labels separate from naturally occurring industrial labels in the reported results.
7. When possible, two people should label each naturally occurring pair independently; disagreements require a documented adjudication decision.
8. State whether the annotation concerns a scalar field, a grouped output, or a whole row. Keep similarly named employee attributes such as job position and job role out of the *metric-definition* evaluation population unless an explicit separate attribute-matching task is declared.

### 10.6 First completed pair: owner-confirmed rule, provisional data-validation record

#### Metric A

```text
Metric ID: M-001
Metric name: account_net_revenue
Business definition: Total ARR of an account and its child accounts, including discounts.
Source model/table: crm_accounts_revenue
Native grain: account
Hierarchy rule: target account plus child accounts
Time/snapshot semantics: four years of daily snapshots
Formula: SUM(arr) over the account hierarchy
Filters/exclusions: fraud accounts excluded
```

#### Metric B

```text
Metric ID: M-002
Metric name: crm_revenue_net
Business definition: Total ARR of opportunities for an account and its child accounts, including discounts.
Source model/table: crm_opportunity
Native grain: opportunity
Hierarchy rule: target account plus child accounts
Formula: SUM(opportunity_arr) GROUP BY account hierarchy
Filters/exclusions: opportunity stage IN (7, 8); fraud opportunities excluded
Time/snapshot semantics: must be aligned with Metric A's daily snapshot date before comparison
```

#### Pair record

```text
Pair ID: P-001
Metric A ID: M-001
Metric B ID: M-002
Relationship label: provisional cross-grain equivalent
Expected transformation: roll M-002 from opportunity grain to the account hierarchy for the same snapshot date
Expected value relationship: account_net_revenue(a, t) = crm_revenue_net_rollup(a, t)
Evidence: the metric owner confirmed on September 27, 2026 that each eligible stage 7/8 opportunity maps to exactly one parent account at the same daily snapshot, with discounts and fraud rules aligned to account ARR. The constructed public fixture also reconciles, but it cannot validate historical industrial data.
Known assumptions: the stated rule is implemented consistently across the production snapshot history; independent aggregate reconciliation still pending
Annotation confidence: high for the intended business rule, provisional for empirical equivalence across real snapshots
```

### 10.6b Second pair: provisional temporal/state-variant record

#### Metric A

```text
Metric ID: M-003
Metric name: product_arr
Business definition: Current product ARR value, used in pipeline reporting; it can reflect later quote/product changes even after a booking is reported.
Source model/table: current opportunity-product/CPQ view (exact lineage not yet captured)
Native grain: aggregation over product records (exact reporting grouping key still to be captured)
Time/snapshot semantics: live/current product value
Formula: SUM(current_product_arr) under the reporting grouping and filters
Filters/exclusions: not yet captured
```

#### Metric B

```text
Metric ID: M-004
Metric name: product_booking_arr
Business definition: Sum of booking ARR allocated to products when the opportunity booking is reported.
Source model/table: product-level booking allocation model; reported booking values are frozen
Native grain: aggregation over product records (exact reporting grouping key still to be captured)
Time/snapshot semantics: frozen reported booking value
Formula: SUM(product_booking_allocation_arr) for reported bookings
Filters/exclusions: not yet captured
```

#### Pair record

```text
Pair ID: P-002
Metric A ID: M-003
Metric B ID: M-004
Relationship label: provisional temporal/state variant
Expected transformation: none assumed
Expected value relationship: no general equality requirement; a later quote/product change may change M-003 after M-004 has been frozen
Evidence: the latest owner clarification says product booking ARR matches the product-level booking allocation and is frozen after reporting, while product ARR continues to reflect subsequent updates
Known assumptions: product-level grouping, booking reporting event, source lineage, and exact filters must be confirmed before final publication
Annotation confidence: medium
```

### 10.6c Third pair: provisional related-but-not-interchangeable record

#### Metric A

```text
Metric ID: M-005
Metric name: total_annual_revenue_booked
Business definition: Total current-year revenue that has already been received by the organization, based on the initial business description.
Source model/table: not yet captured
Native grain: not yet captured
Time/snapshot semantics: current-year realized value
Formula: not yet captured
Filters/exclusions: not yet captured
Terminology note: confirm whether “booked” means cash received, invoiced revenue, or an organization-specific finance-booking state before publication.
```

#### Metric B

```text
Metric ID: M-006
Metric name: total_pipeline_revenue
Business definition: Current revenue of opportunities; opportunities can later be lost or cancelled, including after an earlier booking event.
Source model/table: not yet captured
Native grain: not yet captured
Time/snapshot semantics: live/current opportunity state
Formula: not yet captured
Filters/exclusions: not yet captured
```

#### Pair record

```text
Pair ID: P-003
Metric A ID: M-005
Metric B ID: M-006
Relationship label: provisional related but not interchangeable
Expected transformation: none assumed
Expected value relationship: no equality requirement; M-006 is a live opportunity measure that can increase, decrease, be lost, or be cancelled, while M-005 represents a realized current-year value
Evidence: the two metrics are both revenue-related but encode different business states and different time behavior
Known assumptions: the exact finance meaning of “booked” must be confirmed; source, grain, and formula details are still required for the final benchmark card
Annotation confidence: medium
```

### 10.6d Fourth pair: non-match record

#### Metric A

```text
Metric ID: M-007
Metric name: number_of_customers
Business definition: Count of customers.
Source model/table: not yet captured
Native grain: aggregate count
```

#### Metric B

```text
Metric ID: M-008
Metric name: num_of_products
Business definition: Count of products.
Source model/table: not yet captured
Native grain: aggregate count
```

#### Pair record

```text
Pair ID: P-004
Metric A ID: M-007
Metric B ID: M-008
Relationship label: non-match
Expected transformation: none
Expected value relationship: no meaningful equality, rollup, or substitution rule
Evidence: the metrics count different business entities; shared numeric naming is superficial
Annotation confidence: high
```

### 10.6e Fifth pair: metadata-resolved related-attribute record

#### Metric A

```text
Metric ID: M-009
Metric name: user_position_name
Business definition: Current job title and seniority level, for example Senior Account Executive or Principal Executive.
Source model/table: not yet captured
Native grain: user
```

#### Metric B

```text
Metric ID: M-010
Metric name: user_role_name
Business definition: Current job function or market-segment role, for example SMB Account Executive, Enterprise Account Executive, or Digital Account Executive.
Source model/table: not yet captured
Native grain: user
```

#### Pair record

```text
Pair ID: P-005
Metric A ID: M-009
Metric B ID: M-010
Relationship label: related but not interchangeable
Expected transformation: none
Expected value relationship: no equality requirement; title/seniority and function/market segment capture different attributes of the same user
Evidence: the names alone are ambiguous, but the supplied definitions distinguish job level from job function or market segment
Annotation confidence: high with the supplied descriptions; ambiguous if descriptions are unavailable
```

### 10.6f Extension case: conflicting semantic-attribute definition

This case is useful for motivation and a possible future extension, but it should not be counted in the primary **metric** benchmark because `market_segment` is a dimension/semantic attribute rather than a numeric metric.

```text
Semantic attribute: market_segment
Definition variant A: Segment derived from sales territory.
Definition variant B: Segment derived from the employee count of the company.
Relationship label: conflicting definition if both variants are published under the same unqualified name, market_segment
Why it matters: the same label can encode different business rules, so name similarity should not cause automatic consolidation
Review rule: if lineage or documentation does not state the derivation source, the system must abstain and request human review
```

### 10.6g Sixth pair: direct-equivalent alias record

This is a true direct-equivalent case. The two metric names refer to the same opportunity-level value; `total_` is an explanatory alias, not a separate aggregation.

#### Metric A

```text
Metric ID: M-011
Metric name: opportunity_booking_arr_usd
Business definition: Booking ARR in USD recorded directly on the opportunity source object.
Source table/model: Salesforce Opportunity object (generic public-safe representation)
Native grain: opportunity
Time rule: inherited from the source model; not yet documented
Formula or simplified logic: direct passthrough of the opportunity booking-ARR field
Filters/exclusions: inherited from the source model; not yet documented
```

#### Metric B

```text
Metric ID: M-012
Metric name: total_opportunity_booking_arr_usd
Business definition: Alias for the opportunity's total booking ARR in USD, named to communicate the amount obtained by summing the SKUs sold on that opportunity.
Source table/model: same Salesforce Opportunity object as Metric A (generic public-safe representation)
Native grain: opportunity
Time rule: inherited from the source model; not yet documented
Formula or simplified logic: direct passthrough of the same opportunity booking-ARR field, aliased as total_opportunity_booking_arr_usd
Filters/exclusions: inherited from the source model; not yet documented
```

#### Pair record

```text
Pair ID: P-006
Metric A ID: M-011
Metric B ID: M-012
Relationship label: direct equivalent
Expected transformation: rename/alias only
Expected value relationship: opportunity_booking_arr_usd(o, t) = total_opportunity_booking_arr_usd(o, t)
SKU reconciliation invariant: the opportunity-level value should reconcile to SUM(sku_booking_arr_usd) for the SKUs sold on that opportunity when the same CPQ snapshot, currency conversion, and inclusion rules are used
Evidence: Metric A is a direct passthrough from Salesforce Opportunity; Metric B is the same value aliased as total to communicate the SKU rollup. The production query remains private.
Annotation confidence: high; confirmed by the metric owner using an anonymized, public-safe definition
```

Public-safe illustrative pseudocode (not Zendesk production code):

```sql
SELECT
    opportunity_id,
    booking_arr_usd AS opportunity_booking_arr_usd,
    booking_arr_usd AS total_opportunity_booking_arr_usd
FROM salesforce_opportunity;
```

### 10.7 Initial label-set construction

Build a first set of 30–50 pairs rather than trying to label all 5,000 metrics.

| Pair category | Target count | Purpose |
| --- | ---: | --- |
| Direct equivalent | 5–8 | Test aliases, renames, abbreviations, and exact logic. |
| Cross-grain equivalent | 5–8 | Test explicit rollup and hierarchy reasoning. |
| Temporal/scope variant | 5–8 | Test snapshot, period, and filter awareness. |
| Related / conflicting | 5–8 | Measure false-equivalence risk. |
| Non-match | 5–8 | Measure discrimination against superficial name similarity. |
| Ambiguous | 5–8 | Measure whether the system appropriately escalates to human review. |

### 10.8 Protocol for the first empirical validation

For each candidate pair, compare the methods in this order:

1. Direct normalized match.
2. Soundex candidate generation.
3. Jaro-Winkler name similarity.
4. Jaccard similarity over available metadata and lineage tokens.
5. Mistral Large using a fixed structured prompt and the full metric cards.
6. Proposed topology-aware routing decision.

Record the candidate set, output label, confidence, explanation, runtime, and cost for every method. Evaluate both whether the method finds the pair and whether it assigns the right relationship label.

### 10.9 Next paper task

Section 11 starts the technical work. The `market_segment` derivation example can be used to test abstention on incomplete lineage, but remains a semantic-attribute extension outside the primary numerical-metric benchmark.

## 11. Technical method specification (first research deliverable; September 25, 2026)

**Goal.** Given metric expressions in a SQL/dbt project at versions `v0` and `v1`, return candidate relationships within or across versions, a change classification, a minimal explanation tied to source artifacts, and a list of downstream models potentially affected. The first implementation will support a documented subset of SQL; unsupported expressions must return `needs_review` rather than a guessed equivalence.

**Input.** Source SQL and configuration, model and metric metadata, dependency graphs, optional column types, and version identifiers. In dbt, `manifest.json` contains nodes, sources, metrics, and model dependency maps; optional `catalog.json` supplies types. Model dependencies in the manifest are not automatically column-level lineage. Extract expression-level provenance from compiled SQL where available; otherwise record provenance as incomplete. Capture the exact dbt and manifest schema versions used. Source: https://docs.getdbt.com/reference/artifacts/manifest-json and https://docs.getdbt.com/reference/artifacts/catalog-json .

**Signature.** For each metric `m` in version `v`, extract a typed record:

```text
S(m,v) = (expression, source_measure, aggregation, grain_keys,
          population_filters, join_path_and_cardinality, hierarchy_rule,
          time_key_and_snapshot_rule, business_state, unit_and_currency,
          model_lineage, evidence_location, completeness)
```

`grain_keys` distinguish a product row from an opportunity row; `business_state` distinguishes pipeline from frozen bookings. `completeness` is per field, not one overall confidence score. Canonicalization may normalize aliases, case, and commutative expressions when valid. It must preserve DISTINCT, join type, WHERE predicates, null handling, time boundaries, currency conversions, and aggregation level. An equal-looking SQL expression is not proof of equal business meaning when any of these are unknown.

**Candidate search.** Union candidates from name similarity, shared source-measure lineage, overlapping SQL-expression tokens, and the same metric or affected model across adjacent commits. Keep the highest-ranked `k` per metric and measure whether the gold pair survives this stage. Cross-grain matches can have dissimilar names and different immediate parents, so source-lineage and hierarchy paths must be considered even if names differ. No LLM call is needed for candidate discovery in the first pilot.

**Relationship decision.** Classify `direct_equivalent` only if the same measure, grain, population, business state, time rule, and units are supported by evidence. Classify `cross_grain_equivalent` only if an explicit many-to-one rollup and a valid additive aggregation map one grain to the other without join fanout, duplication, or mismatched hierarchy membership. Record the treatment of absent groups, NULL versus zero, and the compared time dimensions as part of the transformation; use a NULL-aware comparison at the target grain. Classify `temporal_or_scope_variant` when a shared concept differs in snapshot, filter, business state, or population. For similar names with materially different documented meanings, use `conflicting_definition`; for related but non-substitutable measures use `related`; for unrelated measures use `non_match`. Missing information that determines the label yields `needs_review` and an explicit missing-field reason. SQL normalization proves only the transformations it supports; a finite data reconciliation checks examples but cannot prove universal equivalence.

**Maintenance event.** Compare the signature for a metric at `v0` and `v1`. A rename with the same supported semantics is an implementation-only change. A changed filter, grain, unit, business-state or snapshot rule is a *candidate definition drift*. Pair it with the changed SQL expression and affected downstream dbt nodes; a human reviewer determines whether the change was intended and whether consumers need remediation. Changed row counts alone are not evidence of definition drift.

**Worked pilot cases.**

| Case | Expected output | Critical evidence |
| --- | --- | --- |
| Opportunity booking ARR versus its `total_` alias | Direct equivalent | Both are a passthrough of one opportunity field at the same grain and as-of state. |
| Account ARR versus the opportunity ARR rolled to the account hierarchy | Provisional cross-grain equivalent | Same snapshot, additive measure, stages and fraud exclusions, valid hierarchy and no double count; reconcile values after the rollup. |
| Current `product_arr` versus frozen `product_booking_arr` | Temporal/business-state variant | The live value may change after a quote update; the booked value is frozen at the reporting event. |
| A formerly pipeline-only expression changed to include booked opportunities | Candidate definition drift | The population filter changed across commits; inspect downstream models and the intent of the change. |

These are design/test examples, not empirical results. The first three have user-supplied, sanitized business descriptions; the fourth is a constructed change and must be labeled as such.

**Pilot and falsification.** Start with a small public fixture of SQL models and two commits, then add cases for join fanout, a changed fraud exclusion, a period cutoff, an unresolvable macro, and an ambiguous hierarchy. Expected output is a machine-readable pair label plus field-level evidence and `needs_review` when key fields cannot be determined. Compare against a normalized-name baseline, Jaccard/Jaro-Winkler, an LLM given identical context, and a simpler SQL-expression baseline. Separate candidate recall from classification, report false equivalence and abstention rates, and ablate grain, time, and lineage. If the complete method does not materially outperform simpler baselines on realistic held-out cases, narrow the claim to an empirical study of failure modes rather than claiming a superior matcher.

**Publication gate.** A SANER Industrial full paper needs completed industrially relevant validation, measured outcomes, and a direct connection to model maintenance. A public fixture and the six illustrative pairs alone do not meet that bar. The pilot's first deliverable is executable public SQL fixtures and a reviewed evidence table; an external Snowflake account is optional for this local stage.

## 12. Public executable pilot (September 27, 2026)

**Artifact and execution.** `metric_matching_pilot.zip` contains `README.md`, synthetic SQLite source rows and metric views, twelve hand-authored metric cards, seven hand-selected pairs, a guarded classifier in `pilot.py`, and generated `report.json` and `report.md`. Unzip and run `python3 pilot.py --check` in the `metric_matching_pilot` directory. This completed with all seven scenario checks passing locally on September 27, 2026. No Snowflake account, production data, or external Python packages were used.

**Observed fixture evidence.** These are constructed cases, with manually supplied metadata and expected labels; their outcomes are an implementation sanity check, not an accuracy estimate.

| Case | Decision returned | Concrete sample evidence |
| --- | --- | --- |
| Opportunity booking field versus its `total_` alias | `direct_equivalent` | Both views return O1 = 100, O2 = 50, O3 = 70, O5 = 0 from the same source field and snapshot. |
| Account ARR versus filtered opportunity rollup | `provisional_cross_grain_equivalent` | R1 = 150 and R2 = 70 in both views; each eligible opportunity has one mapping in the constructed hierarchy. The metric owner confirmed the intended alignment, but production history is untested. |
| Current product ARR versus frozen booking allocation | `temporal_or_scope_variant` | Product P1 has live ARR 120 after a quote update but booked ARR remains 100. |
| Pipeline ARR v0 versus simulated v1 | `candidate_definition_drift` | v0 contains O5 = 90; v1 also includes O1 = 100, O2 = 50, O3 = 70 after the stage filter expands. Hand-supplied dependencies identify `sales_pipeline_dashboard` and `executive_forecast` for inspection. |
| Opportunity rollup with duplicate hierarchy mapping | `needs_review` | O1 maps twice, making R1 = 250 versus account R1 = 150; unsafe to declare cross-grain equivalence. |
| Same account view with missing snapshot metadata | `needs_review` | The two samples both show R1 = 150, but one manually written card omits its time rule, so the classifier abstains. |
| Customer count versus product count | `non_match` | Both return 2 in this fixture, yet they count different entities. |

**Interpretation and gaps.** This classifier consumes manually written cards, explicitly supplied pair and mapping instructions, and a hand-built downstream dependency graph. The two pipeline views simulate versions, not actual repository commits. It does not parse arbitrary SQL, extract dbt or column lineage, retrieve candidate pairs, run Mistral or other baselines, prove equivalence, test scale, or estimate false-equivalence/abstention rates. The mapping check sees only constructed rows. The owner confirmed intended semantics on September 27, but historical account membership, discount treatment, and source-filter consistency have not been empirically reconciled. The account/opportunity label therefore stays provisional. These outcomes cannot support an industrial effectiveness claim or a SANER submission by themselves.

**Next research action.** See Sections 14–15 for public extraction diagnostics, then independently label realistic version changes and pair relationships before comparing baselines.

## 13. Bounded SQL extraction increment (September 27, 2026)

**Implementation.** The same `metric_matching_pilot.zip` now includes `extract_signatures.py` and `extracted_signatures.json`. Run `python3 extract_signatures.py --check` from its directory. The command generated twelve partial signatures from the twelve synthetic `CREATE VIEW ... AS SELECT` definitions and passed checks for the alias source column, v0/v1 filter difference, and unsafe rollup join-table identity. An unsupported `CASE` expression returns `needs_review` in a boundary check.

**What the SQL reveals.** The two booking views directly read `opportunity_snapshot.booking_arr_usd` with matching filters and snapshot date. The pipeline v0/v1 views read the same `opportunity_snapshot.arr_usd` source but have different stage filters. The two account rollups use different join tables; SQL syntax by itself does not establish whether either join is one-to-one at the eligible opportunity grain. The SQL text supplies the missing snapshot date in the deliberately incomplete manual card example; this shows why extracting provenance can reduce unnecessary review after it is integrated with card validation.

**Extraction boundary.** This is a conservative parser for a documented subset of the fixture: a single SELECT with two simple projections, one source, at most one explicit join, conjunction-only filters, and an optional simple GROUP BY. It does not handle arbitrary SQL, dbt Jinja/macros, nested queries, real repository versions, historical hierarchy validity, currency conversion, or column lineage through model chains. It leaves business state, unit, and join cardinality unresolved. The classifier still uses manually authored cards; the extracted signatures are not yet an end-to-end matcher. Twelve of twelve fixture views yielded **partial** signatures; that number is not a public-corpus coverage rate or a performance result.

**Next engineering gate.** The first public-project extraction diagnostic is in Section 14. Add only needed dbt model and expression constructs with explicit unsupported paths, then have annotators label held-out pairs independently. A publishable result requires a reproducible benchmark and measured baselines, plus industrial validation if submitting to the Industrial Track.

**Public corpus chosen.** dbt Labs' [Jaffle Shop repository](https://github.com/dbt-labs/jaffle-shop) has public model SQL and semantic metric YAML; its [orders metric definitions](https://github.com/dbt-labs/jaffle-shop/blob/main/models/marts/orders.yml) include `order_total`, `orders`, and filtered `new_customer_orders`. Its current README says it requires dbt 2.0 or newer and uses the new semantic-layer YAML format. The adjacent [Jaffle Shop data repository](https://github.com/dbt-labs/jaffle-shop-data) publishes CSV source rows. Section 14 reports the initial extraction diagnostic at a pinned repository commit; Section 17 adds raw-seed checks. Historical semantic changes remain unexamined.

## 14. First pinned public-project extraction test (September 27, 2026)

**Revision and method.** Cloned `dbt-labs/jaffle-shop` at commit `5beb145b00f5465ec759cfcdd9745e858818cf95`. The test harness `run_public_corpus.py` verifies that exact `git rev-parse HEAD`, inventories `models/**/*.sql`, and safely parses `models/**/*.yml` using PyYAML 6.0.3. It writes `public_corpus_report.json` and `public_corpus_report.md` in `metric_matching_pilot.zip`; the public repository itself is not bundled. The `--check` run passed. No dbt compilation, warehouse queries, Snowflake account, row matching, or industrial data were used.

| Diagnostic at pinned commit | Observed |
| --- | ---: |
| dbt SQL model files covered by the fixture `CREATE VIEW` grammar | 0 of 13 |
| Native YAML metric definitions found | 23 |
| Simple metrics | 17 |
| Derived / ratio / cumulative metrics | 3 / 2 / 1 |
| Partial YAML signatures with model, aggregation, grain, time dimension, and simple expression | 7 of 23 |
| YAML metric definitions requiring review for this bounded extractor | 16 of 23 |

**Concrete boundary examples.** `orders.order_total` yielded a partial sum signature at order grain. The `order_items.revenue` expression references `product_price`, but that column is absent from the `order_items` YAML column list, so the initial YAML-only code abstains; Section 15 follows a candidate path through model SQL. `food_revenue` uses a CASE expression, `new_customer_orders` has a templated MetricFlow filter, and `average_order_value` is a derived metric; each is marked `needs_review` by the narrow YAML extractor. These are extraction statuses, not verified relationship labels. Even the seven partial signatures leave unit, business state, and lineage through model SQL unverified at this stage.

**Interpretation.** The fixture SQL parser covers none of this real project's 13 dbt model files because the files are model SELECTs with Jinja and CTEs rather than literal `CREATE VIEW ... AS SELECT` statements. The separate YAML pass demonstrates that basic metric metadata is available but exposes exactly which properties need more parsing or external evidence. The 7/23 count is descriptive coverage on one small public example, not precision, recall, statistical generalization, or evidence that the proposed matcher outperforms existing methods. We have not classified a public metric pair or examined two real commits yet.

**Next implementation and evaluation step.** Section 15 starts a bounded model-SQL trace on selected paths. Extend and validate it with compiled SQL, resolve templated filters and derived-metric dependency edges, then label genuine relationships and semantic changes across pinned commits with independent reviewers. Compare baselines only after that benchmark exists.

## 15. Three selected model-lineage probes (September 27, 2026)

**Method.** `trace_dbt_lineage.py` in the updated pilot checks the same pinned Jaffle Shop commit (`5beb145b00f5465ec759cfcdd9745e858818cf95`) and follows three selected metric references through a documented subset of dbt source SELECTs, CTEs, `ref`/`source` calls, explicit column projections, and resolvable stars. It records CTE and file evidence in `public_lineage_report.json` and a short summary in `public_lineage_report.md`. The pinned-path checks passed. The script does not process all 23 metrics, and these probes are **not** a new coverage estimate.

| Selected metric | Candidate path found | Open proof obligation |
| --- | --- | --- |
| `order_total` | YAML SUM at order grain → `orders.order_total` → `stg_orders.order_total` → `ecom.raw_orders.order_total` | `cents_to_dollars('order_total')` is adapter-dispatched; compiled transformation and data values not checked. The mart query passes the field through stars and a join whose row preservation has not been proven here. |
| `revenue` | YAML SUM at item grain → `order_items.product_price` → joined `products.product_price` → `stg_products.product_price` → `ecom.raw_products.price` | The visible join uses `order_items.product_id = products.product_id`. A unique product key is declared in metadata, but its test and actual row cardinality were not run. The currency conversion macro remains uncompiled. |
| `new_customer_orders` | YAML SUM of constant 1 with first-order filter → `orders.customer_order_number` → SQL `row_number()` over customer ordered by `ordered_at` | The filter's MetricFlow `Dimension(...)` binding is inferred from text and not compiled; tie/order semantics and output values are not validated. |

**Interpretation.** The first two paths reach raw source columns as *candidate lineage*, not as automatically verified equivalence. The third locates the filter calculation without resolving its semantic-layer behavior. All three relationships to other metrics remain `not_evaluated`. An ambiguous star, unsupported expression, unresolved ref, or join condition outside the narrow syntax returns `needs_review`; a visible simple join still needs a cardinality check. dbt documentation states that a SQL model is a SELECT statement and that a simple metric's omitted `expr` defaults to its name: https://docs.getdbt.com/docs/build/sql-models and https://docs.getdbt.com/docs/build/semantic-models .

**Next step toward evaluation.** Select and independently annotate a small set of real public metric pairs and real commit-to-commit definition changes. Expand the parser/compiled lineage only for constructs those cases require, and compare with direct, lexical, and LLM baselines. Do not report matching accuracy from these three selected traces.

## 16. First-analyst public metric-pair set (September 27, 2026)

**Selection and source.** `public_pair_proposals.json` in the updated pilot lists ten naturally occurring metric pairs from `dbt-labs/jaffle-shop` at pinned commit `5beb145b00f5465ec759cfcdd9745e858818cf95`. Each record contains a proposed relationship, specific YAML/SQL file-and-line evidence, a rationale, and an open question. `build_public_pair_review.py --repo <pinned checkout> --check` verifies that both metric definitions and cited line ranges exist, then produces `public_pair_proposals.md` and a separate label-blind `public_pair_blind_review.md`. The standalone `metric_pair_blind_review.md` contains the latter sheet for a second reviewer.

**Status at first annotation.** These were ten **single-analyst proposals**, not independent labels or adjudicated ground truth: four proposed scope variants, four related pairs, one nonmatch negative control, and one unresolved possible cross-grain pair. The set exercises tax inclusion, filtered counts, additive versus median aggregation, entity differences, and time-alignment uncertainty. For example, `order_total` versus item `revenue` requires attention to tax and grain; `orders` versus `new_customer_orders` differs by a first-order filter; `order_total` versus customer `lifetime_spend` could have an all-time rollup but has different default time dimensions. At this stage, the first-analyst labels and rationales were concealed from the second reviewer.

**Benchmark gap.** No direct-equivalent or confirmed cross-grain-equivalent natural pair has been found in this small selection. A few obvious or constructed positive pairs would not make it a realistic benchmark; if needed, use additional public projects and keep intentionally generated mutations in a separately reported test set. Do not compute precision, recall, or relative algorithm performance from this first-analyst sheet.

**Next gate.** A second set of labels has now been submitted; Section 17 records the four initial disagreements, seed checks, and four author-accepted decisions. Section 18 audits the six initially agreed labels against source definitions. Next identify real commit-to-commit metric-definition changes and positive equivalence pairs before baselines.

## 17. Second review and seed-backed adjudication proposal (September 27, 2026)

**Inputs and status.** A completed user-submitted review supplied a second label set for all ten Jaffle Shop pairs at commit `5beb145b00f5465ec759cfcdd9745e858818cf95`. The submission describes its work as independent, but that independence has not been externally verified. The original submission remains separate; `public_second_review.json` is the normalized set of labels. `compare_public_pair_reviews.py --check` compares it to the first proposals and analyst recommendations. First and submitted labels agree on **6 of 10 pairs** and disagree on **4 of 10**. Agreement is a descriptive count on this selected set, not inter-rater reliability for a population or a measure of matching accuracy.

| Pair | First label | Submitted label | Analyst recommendation | Status / issue |
| --- | --- | --- | --- | --- |
| JS-001: order total / item revenue | related | cross-grain equivalent | related | **Accepted by author, September 27**; tax-inclusive total differs from pretax item sum. |
| JS-005: food / drink revenue | scope variant | related | scope variant | **Accepted by author, September 27**; disjoint sibling predicates qualify as scope variants. |
| JS-007: customers / orders counts | related | nonmatch | related | **Accepted by author, September 27**; linked counts are related, but cannot substitute for each other. |
| JS-010: order total / customer lifetime spend | needs review | cross-grain equivalent | scope/time variant | **Accepted by author, September 27**; all-time sums reconcile but default time dimensions differ. |

The other six pairs have matching submitted and first-analyst labels; their labels still require confirmation under the annotation rubric before this becomes a benchmark. JS-010 is a **revision** of the first analyst's earlier `needs_review` proposal after inspecting the submission and sample evidence. The author accepted all four disputed labels in this conversation, but independent adjudicator confirmation has not been recorded; this set is not yet gold labels.

**Numerical checks on public rows.** `reconcile_public_seeds.py --repo <pinned checkout> --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --check` reads the repository's raw CSV seeds and computes integer-cent comparisons implied by the visible model SQL. In 61,948 orders, 61,465 have nonzero tax; item prices and order subtotals each sum to **63,744,400 cents**, whereas tax-inclusive order totals sum to **67,142,537 cents**, a difference of **3,398,137 cents**. Thus JS-001 fails the proposed exact rollup on these rows. All-time order totals and customer lifetime sums both equal **67,142,537 cents**, provided the observed one-customer-per-order mapping; their daily totals differ on **365 of 365** sample dates because `orders.order_total` uses `ordered_at` while `customers.lifetime_spend` uses customers' `first_ordered_at` by default. Thus an unqualified JS-010 cross-grain equivalence is unsafe, although an all-time relationship is possible with explicit time alignment and validated mapping.

**Accepted annotation rules.** For JS-001, tax-inclusive order total and pretax item revenue are `related`, but cannot be exact cross-grain equivalents for the observed rows. For JS-005, a changed category predicate over the same additive input and aggregation qualifies as `temporal_or_scope_variant` even when the two slices are disjoint. For JS-007, counts of different but directly linked entities qualify as `related` when the model explicitly connects them; the two counts remain noninterchangeable. For JS-010, all-time equality under the observed mapping does not imply equality under default daily time rules: `orders.order_total` and `customers.lifetime_spend` are `temporal_or_scope_variant`. An explicitly time-aligned, all-time rollup may be a conditional cross-grain relation but is not the unqualified default pair. For JS-008 the submitted label agrees, but its suggested tax-rate reconstruction is not supported by the visible derivation: the model sums `tax_paid` directly. The finite raw-seed checks do not compile dbt/MetricFlow, prove universal equivalence, or validate metric outputs in a warehouse.

**Reproducible record and next gate.** The updated `metric_matching_pilot.zip` contains `public_seed_reconciliation.{json,md}`, `public_pair_review_comparison.{json,md}`, both scripts, the normalized submitted labels, and `public_pair_author_decisions.json` recording all four decisions and their provenance. The original completed review was not silently overwritten and is not bundled into the pilot. Section 18 checks the six initially agreed labels against source. Document any independent adjudication before calling these gold labels. Then add natural positive pairs and real historical changes, prepare a held-out benchmark, and measure baselines.

## 18. Source audit of the six initially agreed pairs (September 27, 2026)

**Method.** `audit_agreed_public_pairs.py --repo <pinned Jaffle Shop checkout> --check` verifies commit `5beb145b00f5465ec759cfcdd9745e858818cf95`, compares exact metric aggregation, expression, and filter fields in YAML, checks selected model-SQL evidence, and confirms that the first and submitted labels agree. The run passed and writes `public_agreed_pair_audit.{json,md}`. This is a source-level audit of six selected relationships, not a dbt/MetricFlow run, a universal equivalence proof, or independent adjudication. Two important semantic-layer filters remain uncompiled.

| Pair | Agreed label | Source support | Remaining gap |
| --- | --- | --- | --- |
| JS-002: orders / new customer orders | scope variant | Both SUM(1); first-order filter refers to customer order number calculated by `row_number()` per customer. | MetricFlow dimension binding and tied timestamps not executed. |
| JS-003: orders / large orders | scope variant | Both SUM(1); large orders filters on an order-total dimension with a threshold. | MetricFlow binding, conversion macro and null behavior not executed. |
| JS-004: item revenue / food revenue | scope variant | Both SUM item price; food expression contributes zero for nonfood items; product model supplies food flag. | CASE execution and join row preservation not compiled or proven here. |
| JS-006: item revenue / median revenue | related | Same item-price input, different SUM versus MEDIAN aggregation. | Native median execution not tested. |
| JS-008: gross / pretax lifetime spend | related | Customer model sums order total and subtotal separately and has an explicit tax sum; no location tax-rate reconstruction is needed. | Declared customer-level dbt equality test not run. |
| JS-009: customer count / average tax rate | nonmatch | Different customer versus location entities, units, and count versus average operations; location staging has `tax_rate`. | Metric output not executed; label follows definitions. |

**Interpretation.** The six agreed labels are consistent with the pinned source definitions and current annotation rules. Agreement and source support do not make them author-accepted or independent gold labels. Keep `public_pair_proposals.json`, the submitted second labels, author decisions on the four disagreements, and this audit separate in the provenance record. The original ten pairs contain **no confirmed natural direct or cross-grain equivalent**; Section 19 records a separate provisional candidate from a derivative public demonstration. Expanding to independent positive pairs and real historical metric changes remains a prerequisite for a publishable evaluation. The source report includes precise file-and-line evidence for each claim.

## 19. Conditional public cross-grain candidate and NULL-sensitive test gap (September 27, 2026)

**Source and selection.** The separate public repository [sidequery/jaffle-shop-sidemantic](https://github.com/sidequery/jaffle-shop-sidemantic) at commit `8686fe3ea0fd4ceffa08e523a422331bd228ac32` defines `orders.subtotal` in MetricFlow YAML and `order_items.revenue` in Cube YAML. Its Jaffle Shop submodule is pinned to dbt Labs commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. Both definitions predate this pilot and are located in two different models and semantic formats. This is a deliberately curated Jaffle Shop demonstration, however, and its data source is related to the earlier ten pairs; it is **not** an independent held-out corpus or a production organization.

| Property | `orders.subtotal` | `order_items.revenue` |
| --- | --- | --- |
| Native grain | One order | One order item |
| Definition | `SUM(subtotal)` | `SUM(product_price)` |
| Time | MetricFlow defaults to `ordered_at` at day grain | Cube exposes `ordered_at` from the joined order; choose that day explicitly |
| Source | dbt `orders` model based on `stg_orders` | dbt `order_items` model joining orders and products |

**Expected transformation.** Group item prices by `order_id`, **left join to all orders and COALESCE an absent item sum to zero** before comparing order-level amounts. For daily totals, sum both measures on the same `ordered_at` dates. The Cube file declares an item-to-order `many_to_one` relationship; `order_items.sql` gets date from the order and price from the product. The dbt `orders.sql` separately computes `order_items_subtotal = SUM(product_price)` by order; a declared dbt test asserts `order_items_subtotal = subtotal`. Both source amounts are produced by a `cents_to_dollars` macro in the dbt staging models. The NULL handling is an essential condition of this candidate transformation.

**Executed source-row check.** `verify_public_positive_candidate.py --repo <checkout with submodule> --check` verifies both commit IDs, the semantic definitions, key SQL paths, and raw CSV rows. Among **61,948** orders, **90,900** items, and **10** products, **483 orders have no items**. Their order subtotals are zero and their unfilled item sums are absent/NULL; thus a NULL-aware order comparison finds **483 differences before COALESCE and zero afterward**. All-time totals each equal **63,744,400 cents**, and aligned daily sums agree on all **365** dates. No item with an unknown order or product, nor duplicate order/item/product key, appeared in the sample. The run passed and writes `public_positive_candidate.{json,md}` with pinned file-and-line evidence.

**Materialized dbt check.** Built the pinned dbt submodule on DuckDB with dbt 1.12.5 (`PASS=49 WARN=0 ERROR=0 NO-OP=3 TOTAL=52`) and checked the actual `orders` and `order_items` tables with `check_built_positive_candidate.py --repo <checkout> --check`. The declared `order_items_subtotal = subtotal` test reported **pass, zero failures**, but its compiled predicate is `WHERE NOT(order_items_subtotal = subtotal)`. SQL three-valued logic drops the **483 NULL-versus-zero** rows from that predicate. A null-aware `subtotal IS DISTINCT FROM order_items_subtotal` comparison on the materialized `orders` table finds **483 differences**; an order-to-item left join with `COALESCE(item_sum, 0)` finds **zero**. Both full totals are **$637,444.00**, with **zero daily differences across 365 dates**. The companion report and package lock in the pilot record the build and checks; a passing ordinary equality test cannot establish order-grain equivalence here.

**Unified semantic-layer check.** `check_semantic_positive_candidate.py --repo <checkout> --check` loads the pre-existing MetricFlow and Cube YAML into **Sidemantic 0.8.2**, then executes `orders.subtotal` and `order_items.revenue` separately at their respective `ordered_at` daily dimensions against the built DuckDB tables. Its compiler produces `SUM(subtotal)` from `main.orders` and `SUM(product_price)` from `main.order_items`, both grouped by `DATE_TRUNC('DAY', ordered_at)`. From **2024-09-01 through 2025-08-31**, both return **365 dates, zero missing dates, zero differing daily values, and $637,444.00** summed over those daily results. The pinned repository's declared minimum Sidemantic version is 0.8.2; our attempted import under 0.12.0 failed while parsing its OSI product model, so the successful result is explicitly versioned. This is execution through a *single translating engine*, not independent native MetricFlow and Cube services. It does not resolve the 483 order-grain NULL differences.

**Claim limit and next gate.** Label POS-001 `conditional_cross_grain_candidate_daily_equality_order_equality_requires_coalesce_not_gold`, separate from the original ten annotated pairs. The dbt model/test and both Sidemantic-translated measures ran, but neither **native MetricFlow nor native Cube runtime** was queried; there is no independent second annotation. The order-level relationship requires the documented left join and NULL-to-zero rule. Section 20 adds unrelated public *development controls* and a real versioned change. Native runtime checks are needed if we claim portability across semantic engines. Independent annotation and held-out selection remain necessary before a benchmark or matching-accuracy claim. This curated demonstration does not establish industrial effectiveness or novelty by itself.

## 20. Unrelated public positive controls and a real metric-code change (September 27, 2026)

**Selection and provenance.** We inspected several public projects outside Jaffle Shop and selected two demonstrable cases from [jross21/gtm-funnel-analytics](https://github.com/jross21/gtm-funnel-analytics/tree/a71232c123a5fb78da9b52d4246950ee48591c00), plus an actual historical commit in [rilldata/rill-examples](https://github.com/rilldata/rill-examples/commit/10a9bce8f0181623d8c596fbed7df37244666cc4). GTM uses **synthetic Salesforce/HubSpot seed data and deliberately reconciled KPIs**. These examples were chosen after reading the implementation and are development controls, not a random or independent held-out test sample. `audit_unrelated_public.py --gtm-repo <pinned GTM checkout> --rill-repo <pinned Rill checkout> --check` verifies commit IDs, source expressions, dbt build results, DuckDB rows, and the historical change; the report gives file-and-line links.

| Case | Source relationship | Executed result | Interpretation |
| --- | --- | --- | --- |
| GTM `pipeline_created`, `month` versus `window` | Two SQL branches separately sum `opp_amount` with the same net-new and created-month filters; month values roll up to the analysis window by segment. | Four segments reconcile to the cent: `All` has seven monthly rows summing to **$6,884,381.39**, equal to its window value; Enterprise, Mid-Market, and SMB also have zero differences. | Designed **cross-grain positive control** for one KPI implemented in two branches, not two independently created enterprise metrics. |
| GTM `fct_metric_values.pipeline_created` versus reconciliation report's `canonical` row | Report selects the `All` window value from the canonical table and projects `c.value` into both reported value columns. | Each is **$6,884,381.39**, with zero delta; four intentionally naive pipeline variants have nonzero deltas. | Direct **lineage alias control** across two tables, not independent duplicate computation. |
| Rill `ctr` and `ecpm`, parent `3516d3d` to commit `10a9bce` | Both denominator expressions change from `/sum(imp_cnt)` to `/nullif(sum(imp_cnt),0)`. | Source history verified; a *constructed* DuckDB 1.4.4 check gives equal values for `3/4` but `inf` versus NULL for `1/0` (and `nan` versus NULL for `0/0`). | Actual committed **zero-denominator behavior change**, with no claim about observed Rill source-row impact. |

**Missing-month condition observed in the built GTM sample.** Among the 28 possible combinations of seven analysis months and the four reported segments, `pipeline_created` has **27 monthly rows**. The Enterprise segment has no row for September 2025; a read-only check found zero eligible opportunities for that group. A month-to-window sum reconciles with an absent month contributing zero, but the group is missing as a row. This condition matters when comparing complete group sets or interpreting missing as NULL rather than zero; it remains an observation on deliberately synthetic development data.

**Execution boundary.** The GTM project built locally with dbt-core 1.11.6, dbt-duckdb 1.10.1, DuckDB 1.4.4, and one dbt thread: **44 successful nodes, 111 passing tests, 8 no-op exposures**. A local example profile omits its checked-in request to download ICU; the installed DuckDB already provides it. Attempts with four threads left an unreplayable WAL in this environment, so the record uses a fresh one-thread build whose database reopens normally. We did not modify metric SQL or the project's committed source. The Rill project reads remote parquet not loaded here; the division check illustrates DuckDB behavior on invented inputs and is separate from source-data evaluation.

**What this adds and what it does not.** The development record now contains a source-backed and executed rollup, a traceable exact alias, four intentional contrasting pipeline values, and a genuine before/after expression change. It does **not** yet demonstrate independent enterprise metric duplication, frequency of such relationships, algorithm accuracy, or performance at the user's 5,000-metric scale. Section 21 records the subsequent separate AI review; Section 22 records the public sampling plan. The detailed evidence and reproduction commands are in `unrelated_public_audit.{json,md}` and the pilot README.

## 21. Separate AI review of development evidence and paper readiness (September 27, 2026)

**Review design.** A separate AI agent with a fresh context inspected five named cases in the pinned GTM, Sidemantic Jaffle, and Rill public Git checkouts. Its first instruction withheld this outline, the existing audits, and first labels. The case protocol and first labels were saved separately before its response in `metric_matching_pilot/independent_review_protocol.md` and `first_labels_for_second_review.json`; the original reply and comparison are `blind_second_agent_review.md` and `second_agent_comparison.md`. In a *second, distinct phase*, the same agent was allowed to read the outline and reports and critique the manuscript. That review is summarized in `paper_readiness_review.md`. This is a separate AI check, not independent human annotation, gold ground truth, or peer review.

| Case | Blind reviewer judgment | Consequence for the paper |
| --- | --- | --- |
| BR-01 GTM pipeline months versus window | Conditional `cross_grain_equivalent` with an explicit sum; 411 eligible raw-seed opportunities sum to $6,884,381.39 over seven `All` months. | Matches our built-model check only under aligned full months, segment, snapshot, nonoverlapping groups, compatible cent rounding, and zero treatment for absent months. The literal `All` must not collide with a real segment. |
| BR-02 GTM canonical report versus source fact | `direct_equivalent` for the filtered scalar value fields; full rows only `related`. | Field-level passthrough does not make rows interchangeable: the report omits grain, segment, and period. |
| BR-03 Jaffle subtotal versus item revenue | Unqualified `related`; conditionally cross-grain equivalent with aligned order/day scope, valid joins, and zero fill. | Equal daily totals conceal 483 zero-item orders; NULL-aware order comparison needs a left join and `COALESCE`. The positive remains a conditional development candidate, not gold. |
| BR-04 Rill CTR/eCPM change | `behavior_changing` at zero summed impressions; row impact unestablished. | A real source change exists; constructed DuckDB arithmetic cannot establish affected Rill users or source rows. |
| BR-05 Rill average bid floor across auction/bids | Similar formula shape, but equivalence `needs_review`. | Separate parquet populations and independent time shifts prevent an equivalent label without source-row and group alignment. No earlier first label existed; exclude from any agreement statistic. |

The first four conclusions are **compatible under their stated conditions**, rather than four measured successes. The examples were selected after inspection, and reviewer judgments are not human adjudication. The blind agent recomputed GTM counts and amounts from raw CSVs and did not query built DuckDB tables; we separately confirmed its 411/$6,884,381.39 result by a read-only query of the dbt-built GTM fact table. Do not mix raw-seed calculations, materialized checks, constructed arithmetic, and remote Rill observations in one evidence category.

**Manuscript critique.** The agent identified three strengths: a versioned maintenance problem, meaningful public failure modes, and a falsifiable evaluation plan. Its five blocking gaps, in order, are (1) absent systematic industrial decisions and measured reviewer value, (2) absent automated real-commit end-to-end method, (3) selected labels that cannot serve as representative human-adjudicated ground truth, (4) unproven incremental novelty over constraint-aware matching and SQL-equivalence work, and (5) absent held-out, context-fair baseline results. Its verdict is **promising but not submission-ready**. We accept these as research gates and do not report matching accuracy, superiority, prevalence, industrial effort saved, or cross-engine portability from the current evidence. A public-only failure-mode study is a narrower contingency if the proposed matcher or industrial validation cannot meet these gates.

## 22. Prospective sampling and next implementation gate (September 27, 2026)

The companion `metric_matching_pilot/heldout_sampling_protocol.md` was written **before selecting additional public test projects**. It excludes previously inspected Jaffle, Sidemantic, GTM, and Rill code and their related datasets or forks from held-out claims; specifies search-query families, eligibility, commit-window rules, candidate strata, paired human annotation, adjudication, and separate retrieval/classification/end-to-end measurements. The actual search-result snapshot, repository list, and pinned commits **must still be recorded in a sampling-frame manifest before opening any held-out code**. It is an internal prospective plan, not an externally registered protocol or proof that suitable positive cases exist. If a target quota is unattainable, report the actual sample and narrow the claim instead of silently adding hand-picked positives. A candidate Recall@k claim requires completely judged anchor candidate universes, not only sampled pairs.

**Implementation sequence.** Section 23 completes a *narrow* two-commit source analyzer for Rill YAML declarations and explicit dashboard references. Section 24 checks SQL/dbt model-level source changes and `ref()` paths, but not actual metric branches. The next development deliverable is compiled metric definitions, field-level provenance, candidates beyond exact stable IDs, and source-linked downstream impacts, with abstention when grain, joins, population, or time cannot be resolved. Record extraction coverage and manual interventions. Freeze baselines and thresholds before opening held-out projects. Seek a domain-aware human review of disputed development cases and an appropriately permissioned industrial sample before making effectiveness or industrial claims.

## 23. Automated historical change slice and path to the conclusion (September 27, 2026)

**Executable slice.** `analyze_versioned_metrics.py` reads the parent `3516d3d144979d23ceded2a1a72efcbddd452800` and child `10a9bce8f0181623d8c596fbed7df37244666cc4` directly from the pinned `rilldata/rill-examples` Git history. It enumerates each Rill `metrics_view` YAML measure at both versions and links measures by `(metrics_view, measure)` without handwritten pair IDs. For each changed expression it includes commit/path/line evidence, a limited source-model link, and explicit dashboard declarations in the child revision. The output is `metric_matching_pilot/versioned_metrics_report.{json,md}`; the `--check` command in the pilot README verifies the historical case.

| Observed result | What it supports | What it does not support |
| --- | --- | --- |
| 16 measures read in each revision, 16 linked by stable declared ID, 2 expression changes detected (`bids_metrics.ctr`, `.ecpm`). | This source adapter can automate **this adjacent-commit maintenance inspection** without selecting those two pairs by hand. | Recall of renamed/cross-view matches, general SQL/dbt parsing, or an accuracy estimate. |
| Both changes add `NULLIF(sum(imp_cnt),0)` around the denominator. | For a zero grouped denominator the new expression returns NULL; for nonzero denominators the old and new arithmetic agree under matching inputs. | The old division-by-zero value on Rill's engine, the presence of any zero-denominator group in its remote parquet, or an observed user-visible incident. |
| Each changed measure is explicitly named in `bids_explore.yaml` and `executive_overview.yaml`; the explore also has a wildcard measure declaration. | These are **declared potential dashboard consumers**, with exact source locations; `bids_data_model.sql` reads `bids_data_raw` at model level. | Actual dashboard usage, field-level SQL lineage, model join cardinality, or measured downstream impact. |

**Conclusion decision rule.** We will write the paper's conclusion only after the following research questions have actual evidence. The comparisons must use preselected projects and human-adjudicated labels, with thresholds and LLM context fixed on development projects. Avoid inferring success from a single curated commit.

| Research question | Evidence required for a defensible answer |
| --- | --- |
| Can definitions and changes be extracted? | Coverage and error counts across held-out project files, versions, and supported SQL features; unresolved cases and manual interventions reported. |
| Can matching and drift decisions beat useful alternatives? | Candidate Recall@k on fully judged anchor universes; classification given the same candidates and context; end-to-end false equivalence, abstention, per-project uncertainty, runtime/cost, and comparisons with lexical, normalized SQL/lineage, constraint-based, and context-fair LLM methods. |
| Does the explanation help maintenance? | Domain reviewers judge source-linked alerts and affected consumers against actual decisions; measure misses, false alarms, time to decision, and representative redacted examples. |
| Does it apply to the industrial setting? | Permissioned anonymized versioned definitions and owner judgments from the 5,000-metric setting, plus throughput measured in **definitions, candidate pairs, and versions**. Underlying petabyte data volume alone is not matcher-scale evidence. |

If held-out results show a reliable gain at an acceptable false-equivalence and review budget, the conclusion can describe that measured gain and its supported setting. If simpler methods perform similarly, report an empirical account of when grain, NULL, and version context matter without claiming a superior matcher. If labels, data, or coverage remain insufficient, describe a pilot and its limitations rather than an effectiveness conclusion. An Industrial Track claim additionally needs systematic industrial outcomes; a public-only study is a separate, narrower submission decision. These are **planned branches, not results**.

## 24. Bounded dbt source check and interim conclusions (September 27, 2026)

**Second automated development slice.** `analyze_dbt_sql_versions.py` compares public GTM commits `f387f822ab65f94bb2d04691ed0288ec3cdb17a2` and `a4c122762b910a6a1c847e3d1a4999a5162db00a`. It enumerates dbt model SQL files by path, removes only source comments and whitespace outside quoted strings/Jinja, compares the remaining token streams, resolves simple `ref('model')` links to model SQL or declared seeds, and emits potential downstream model paths. It does not compile either revision, interpret UNION ALL metric branches, or prove runtime behavior. The `--check` run passed; its full model list and line-linked graph are in `metric_matching_pilot/dbt_version_report.{json,md}`.

| Observed source result | Supported interpretation |
| --- | --- |
| 30 model SQL files before and 33 after; among the 14 changed or added files, 7 have identical nontrivia tokens, 4 have changed token streams, and 3 are new models. | The source-level analyzer separates formatting/comment changes from changes requiring review in this selected commit. This is **not metric-level accuracy**. |
| `fct_opportunities.sql` has identical nontrivia tokens; its child-commit `ref()` descendants include `fct_metric_values.sql` and `rpt_metric_reconciliation.sql`. | A formatted upstream model has potential metric/reconciliation consumers. Stable source tokens do not establish compiled or row-level equivalence, and a dependency path alone is not evidence that a value changed. |
| `rpt_metric_reconciliation.sql` changes tokens (including explicit alias `AS`) and is `needs_review_sql_changed`; 22 seed refs are resolved and no simple `ref()` edges remain unresolved in this project. | Conservative abstention avoids treating every token change as definition drift. Macros, other SQL dialect constructs, column lineage, and runtime results remain outside this subset. |

**Supported conclusions from the selected development cases, not a general evaluation:**

1. **Comparison scope matters.** In the public Jaffle sample, `orders.subtotal` and item revenue agree across 365 aligned days, while 483 orders have a zero subtotal and no item rows; an order-grain comparison requires an explicit left join and NULL-to-zero rule. This is a counterexample to inferring order-grain equivalence from matching daily totals.
2. **Lineage can make scalar values equal without making records interchangeable.** The synthetic GTM reconciliation report directly projects a filtered canonical pipeline value but drops source grain, segment, and period fields. Its whole report row is a different object from the fact row.
3. **Versioned source code can locate conditional behavior changes and potential consumers.** Rill's `ctr`/`ecpm` definitions add a zero-denominator guard in a real commit; the new expression yields NULL on zero summed impressions. The old runtime outcome and occurrence on Rill source rows are unmeasured. The automated Rill adapter found dashboard declarations, not observed dashboard impacts.
4. **The current method's coverage is bounded.** It can link stable Rill measure IDs and distinguish token-preserving dbt refactors from other source edits. It cannot yet decide whether a renamed metric or two independently authored metrics match, or whether a changed dbt expression changes metric values.

**Interim conclusion wording, suitable only as a case-study finding:** “Across selected public development cases, matching aggregate values or similar names does not by itself establish interchangeable metric definitions: comparison scope, missing groups, lineage, and versioned expressions matter. A narrow automated source analyzer recovered a real guarded-denominator change and potential declared consumers, while leaving unresolved SQL and unobserved runtime effects for review.” Do not present this as a measured win over direct match, Soundex, Jaccard, Jaro-Winkler, or Mistral Large, a frequency estimate, a 5,000-metric scalability result, or a general novel-method validation. The final paper conclusion still needs the held-out, human-adjudicated and baseline evidence specified in Section 23.

## 25. Parallel development results and evaluation contract (September 27, 2026)

Three parallel workstreams produced separate deliverables in the pilot archive. These are **development artifacts**. They neither turn selected cases into a representative benchmark nor establish an incremental contribution over prior matching or SQL-equivalence methods.

| Workstream | Reproducible observation | Boundary |
| --- | --- | --- |
| Bounded dbt metric-branch extraction | `extract_dbt_metric_branches.py` reads pinned GTM `fct_metric_values.sql` at `a71232c123a5fb78da9b52d4246950ee48591c00`. It extracts 11 `UNION ALL` branches and their metric name, `month`/`window` grain, syntactic CTE→`ref()` relation, period, segment, value, WHERE, grouping, and line locations. The 11 unique `(metric_name, grain)` IDs match the 11 distinct IDs in the read-only, built `fct_metric_values` table. | Eight branches have unexpanded `GROUPING SETS`, ten have unexpanded Jinja, one contains an unexpanded dbt macro, and **all 11 lack field lineage**. All are `needs_review`. ID coverage is not semantic extraction accuracy; this is one selected SQL file. The script's `--self-check` passed. |
| Name-only candidate diagnostics | `run_development_baselines.py --check` regenerates exact-normalized-name, token Jaccard, Jaro–Winkler, and Soundex scores and deterministic tie ranges for ten selected public Jaffle pairs (23-name inventory), seven constructed fixture pairs (12-card inventory), and a separate pair-only conditional Jaffle candidate. | All four methods use names only. The public pair selection and fixture are not held-out gold, so no retrieval Recall@k, classification accuracy, or superiority follows. The one pair-only candidate has no complete inventory and therefore no rank. |
| Prospective evaluation audit | `evaluation_contract.md` and `annotation_schema.json` specify a frozen search-result frame, scalar comparison scope, conditional transformation prerequisites, separate evidence status, two independent domain-human judgments and third-person adjudication, complete anchor universes for exact Recall@k, shared candidate sets and evidence budgets for classifiers, and review-cost/unsafe-equivalence endpoints. | This is a design and schema, not completed annotation. The JSON parses and its 47 local references resolve; full Draft 2020-12 validation and operational checks of independence, source truth, and exhaustive candidate coverage remain to be done. The already inspected projects remain development material. |

**Diagnostic examples, not measured errors:** In the selected public Jaffle names, `lifetime_spend` versus `lifetime_spend_pretax` ranks first under Jaccard, Jaro–Winkler and Soundex, although the source-backed proposed relationship is `related` because tax inclusion differs; review independence is unverified. In the constructed fixture, a same-name `pipeline_arr` version pair scores 1.0 under all four methods even though its hand-authored stage filter changed. Conversely the conditional `orders.subtotal` versus `order_items.revenue` case scores zero under all four name methods, while 365 aligned sample daily sums agree subject to explicit order-grain NULL handling. These cases show possible **failure mechanisms** and motivate tests; they do not estimate their prevalence or prove that the proposed system would avoid them.

**Claim test and immediate implementation gate.** Build compiled metric-field provenance and an abstaining source-aware retrieval/classification path on development projects, with name, normalized SQL/lineage, constraint-aware, and context-matched LLM comparisons at fixed inputs and budgets. Lock parsers, thresholds, prompts, project selection, and primary safety/review endpoints before reading a new held-out repository. The sampling-frame manifest and two-human adjudication must precede any held-out effectiveness conclusion; industrial maintenance benefit additionally requires permissioned owner decisions and measured reviewer outcomes. If strong comparators match the benefit or evidence is too sparse, narrow the conclusion accordingly. No SANER paper has yet been submitted or accepted.

## 26. Compiled lineage, source-aware retrieval and branch history (September 27, 2026)

The next three development probes use **the same 11 literal `(metric_name, grain)` GTM branches**. An integration contract in `metric_matching_pilot/next_step_integration_contract.md` was written before their outputs were combined. The extraction, compiled-field, retrieval, and versioned reports agree on all 11 branch IDs. Their source is public, deliberately synthetic GTM data; they do not independently evaluate Zendesk definitions or the 5,000-metric setting.

| Probe | Observed output | Interpretation and unresolved evidence |
| --- | --- | --- |
| Compiled metric-field tracing | The local dbt 1.11.6 manifest and compiled metric SQL agree; source and compiled branch identities align 11/11. The bounded tracer records 9 scalar value-field uses and 15 branch-filter field uses with immediate upstream declarations. It also records three branches using `count(*)`, two of them with no scalar value field, and 38 seed-header endpoint *occurrences* across traced paths. | All 11 branches retain `needs_review`; 21 of 24 root value/filter field paths require review. Sixteen deeper path occurrences stop at UNION fields without a supported discriminator; grouping-set row semantics, join cardinality, macros, and some field ownership are unresolved. A seed-header endpoint is syntactic provenance, not proof of row-level equality. |
| Same-universe candidate ranking | Every one of the 55 unordered GTM branch pairs is scored; each of the 11 query branches sees the same ten candidates under exact-name, token Jaccard, Jaro–Winkler, Soundex, and a fixed seven-feature syntactic source score. `pipeline_created@month` ↔ `pipeline_created@window` ranks first for all five methods. | The source score uses literal source ref, value, WHERE, period, segment and grain features plus name Jaccard, with equal weights. Unexpanded Jinja receives no credit and all pair relationship decisions abstain. This diagnostic shows **no observed retrieval advantage** on the showcased pair; it is not an accuracy or Recall@k estimate because the candidate universe has no complete human judgments. |
| Versioned branch links | In adjacent GTM commits `f387f822ab65f94bb2d04691ed0288ec3cdb17a2` → `a4c122762b910a6a1c847e3d1a4999a5162db00a`, the metric SQL Git blob is identical and all 11 branches link by explicit ID. Seven branch paths receive `potential_metric_change` review triggers because an upstream model changes `FROM contacts c` to `FROM contacts AS c`; four abstain. Previously unresolved paths to nine CSV seeds were resolved. | The seven are **path-level possible-change alerts**, not seven proven metric changes. The `AS` edit appears cosmetic but has not been compiled/executed at both revisions. This analyzer lacks field-level historical impact and cannot infer affected values or actual downstream use from `ref()` paths. Rill's denominator change remains the separate real-change development case. |

**Combined interpretation before evaluation.** We can now reproduce branch enumeration, some compiled field paths, same-universe candidate rankings, and branch-level source-review triggers. The three adapters remain separate and do not yet yield a reliable cross-grain or versioned *maintenance decision*: the ranking returns no equivalence label, the lineage has unresolved row/field semantics, and the versioned check flags a likely harmless alias edit through model-level dependencies. These are concrete implementation findings, including an apparent false-alert mechanism, not measured industrial effectiveness, algorithm superiority, or evidence that source similarity proves equivalence.

**Separate AI synthesis.** `metric_matching_pilot/combined_agent_review.md` inspected the three scripts, reports and pinned artifacts, checked the shared 11 IDs and 55 pair universe, and found no scoring-path label or outcome leakage. It flagged two repairable issues in the first drafts: an unresolved upstream ref did not affect a version assessment, and the compiled report conflated 21 reviewed root field paths with 38 seed-header endpoint occurrences. Both were corrected: unresolved refs now force abstention absent a detected edit or explicitly qualify a potential-change trigger; the report separates the two denominators. The pinned 7/4 assessments and zero unresolved refs are unchanged. The reviewer also observed that source similarity credits stage-conversion rates with different `stage` filters and two `mql_volume` grains with different periods. These examples call for explicit filter/grain/time rules and abstention, not an equivalence label. This is an AI integration review, **not** an independent human judgment or conference review.

**Next gate.** Connect the compiled field evidence to the same candidate records and to a conservative conditional classifier; explicitly normalize straightforward SQL alias refactors while preserving NULL, missing-group, filter, grain, and snapshot conditions. Evaluate that development method against useful normalized SQL/lineage and constraint-aware alternatives without choosing thresholds from future held-out cases. Once the method and costs are fixed, save the complete search-result manifest *before* opening test repositories, obtain two independent domain-human judgments with adjudication and completely judged anchor candidate universes, and report unsafe equivalence and reviewer effort by project. Industrial claims require approved private evidence and actual owner decisions; public example controls do not substitute for them.

## 27. Same-input conditional decision comparison on public development data (September 27, 2026)

**Protocol.** `metric_matching_pilot/conditional_method_contract.md` fixed a development-only comparison before the three method outputs were combined. `build_conditional_evidence.py` checks the pinned GTM revision and local dbt-compiled artifacts and produces a label-free source/compiled evidence packet. All three methods read the identical packet bytes (SHA-256 `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`) containing 11 `(metric_name, grain)` cards and all 55 unordered pairs. The packet records value, filter, period, grouping, source/compiled locations and explicit unknown semantic fields. It contains no row totals, curated answer list, owner labels or earlier review conclusions. This is one intentionally selected synthetic GTM project; it is not a held-out project or a representative test sample. The earlier name-only ranking is a limited-input diagnostic, not a fourth comparable full-context classifier.

| Method (same full-context input) | Candidate decisions among 55 pairs | Abstentions | Claim supported by the output |
| --- | --- | ---: | --- |
| Normalized SQL/lineage baseline | 2 scope variants; 3 related candidates | 50 | Preserves visible expression/filter/grain differences; all 55 require review. |
| Constraint-aware baseline | 2 conditional month→window hypotheses; 3 related conversion-step candidates | 50 | Supplies an additive source hypothesis while leaving semantic prerequisites unresolved; all 55 require review. |
| Proposed conditional explanation | 2 conditional month→window hypotheses | 53 | Makes zero-fill, NULL, partition/time, grouping-set, rounding, units and snapshot prerequisites explicit; all 55 require review. |

Both the constraint-aware baseline and proposed method select `pipeline_created@month` ↔ `pipeline_created@window` and `mql_volume@month` ↔ `mql_volume@window`. The SQL/lineage baseline marks them as scope variants. The three same-grain funnel conversion rates have distinct stage predicates; both baselines call them related, while the proposed method abstains. Those differences cannot be scored without owner judgments. Every pair, including both conditional hypotheses, has `needs_review`: matching source references and an additive core do not verify row membership or exposed-value equivalence.

**Post-output checks.** `compare_conditional_development.py` verifies that each method used the same packet hash and all 55 pairs, then separately inspects the read-only built GTM rows. For the seven-month 2025-09 through 2026-03 displayed range, all four segment values for pipeline and MQL counts equal sums of their observed monthly rows. Enterprise has no September 2025 `pipeline_created` month row (six observed months); this motivates the explicitly unresolved absent-group/zero-fill rule. Critically, the `mql_volume@window` source has **no date predicate or time key**: its constant `2025-09-01` period label does not constrain source rows. This build happens to have no extra MQL months, so its bounded and all-month sums coincide; adding an out-of-range source month can break the displayed-window interpretation. The separate pinned Jaffle Shop development check finds 483 zero-item orders whose item sum is absent/NULL while order subtotal is zero; an outer join with `COALESCE` removes the 483 observed order-grain discrepancies. Jaffle is outside the 55 GTM pairs, and neither method is evaluated on it here. Summing GTM's already rounded published monthly pipeline outputs happens to match the displayed window amount in this finite sample; the general raw-aggregate hypothesis requires summing unrounded inputs and rounding once, with grouping levels and NULL/zero semantics verified separately.

**Conclusion and paper gate.** This step makes the proposed decision path executable and gives a fairer full-context development comparison. A separate AI integration review (`conditional_method_review.md`) found an initial unsafe grouping shortcut, an unbounded MQL window, and a `--check` mode that wrote files. The grouping gate now requires an exact one-to-one month-key removal and passes negative counterfactual checks; MQL membership and pipeline exposed-value rounding remain unknown; the check mode is read-only. This is an AI code review, not a human metric judgment. The method does **not** demonstrate an incremental gain over the strong constraint-aware baseline: both surface the same two conditional hypotheses, with no adjudicated truth, false-equivalence rate, reviewer effort or cost measurement. A precise explanation may still help a reviewer, but that is a hypothesis. A publishable result needs either a verifiable new maintenance capability or an independently judged benchmark/investigation with clear comparison to close prior work. Freeze the implementation, evidence budget, thresholds, prompt choices if any, and a dated full search-result frame **before** opening new held-out projects. Obtain two independent domain-human judgments and adjudication over completely judged anchor candidate universes; report unsafe equivalence, coverage, effort and cost by project. Any Zendesk or 5,000-metric industrial claim additionally requires permissioned evidence and actual owner decisions. No industrial or Snowflake evaluation was run in this step.
