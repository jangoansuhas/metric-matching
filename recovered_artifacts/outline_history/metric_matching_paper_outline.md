# Draft Paper Outline — SANER 2027

## Working title

**Topology-Aware Matching of Enterprise Metric Definitions: A Reproducible Study of Lexical, Contextual, and LLM-Based Methods**

Alternative title:

**When Do Metrics Mean the Same Thing? Detecting Cross-Grain Equivalence in Evolving Enterprise Data Systems**

## Paper decision

This is a paper about **enterprise metric matching**, not generic student-record deduplication. Student records may later serve as a small external validation, but they will not be part of the main claim.

The paper must not claim that Jaccard, Jaro-Winkler, Soundex, direct matching, or Mistral Large are novel. Its contribution is a metric-specific problem formulation, a relationship taxonomy, a reproducible benchmark, and evidence on when each approach should be used.

## One-sentence thesis

Enterprise metrics cannot be matched reliably from names alone: correctly detecting equivalent, overlapping, conflicting, and ambiguous definitions requires their grain, time semantics, hierarchy, filters, SQL logic, and lineage, and the most useful matching strategy depends on how that information is distributed across the data system.

## Current evidence and hypotheses

### Evidence already provided

- Approximately 5,000 enterprise metrics exist in the industrial setting, calculated over petabyte-scale data.
- The candidate approaches are direct matching, Soundex, Jaro-Winkler, Jaccard, and Snowflake-hosted Mistral Large.
- Preliminary observations are that Mistral Large is more useful when rich context is centralized in one table; Jaccard is more useful when relevant tokens are scattered across tables; and Jaro-Winkler is useful for sequential files with deterministic naming rules.
- The public benchmark will use public Snowflake data. The industrial data will remain private; only anonymized, aggregate validation results may appear in the paper.

### Hypotheses to test, not claims to make yet

- H1: Including metric grain, snapshot semantics, hierarchy, filters, and lineage improves classification over name-only matching.
- H2: A topology-aware router outperforms a single matcher across centralized, fragmented, and sequential metric-definition settings.
- H3: Cheap lexical methods can safely eliminate or accept a meaningful subset of pairs, reserving LLM calls for ambiguous pairs and reducing cost.
- H4: Cross-grain equivalence is a frequent and practically important relationship that standard schema or entity matching labels do not capture well enough.

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

1. A formal, metric-specific taxonomy that includes cross-grain equivalence and definition conflicts.
2. A topology-aware matching pipeline using direct match, Soundex, Jaro-Winkler, Jaccard, and Mistral Large.
3. A public benchmark generator and labeled metric-pair dataset built from public Snowflake data.
4. A reproducible empirical evaluation plus an anonymized industrial validation.

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

### 3.4 SQL/computation equivalence

- Query-equivalence work, such as GEqO, targets semantic equivalence of executable SQL subexpressions at scale.

### 3.5 Our boundary

The paper must not claim to replace schema matching, entity resolution, or formal SQL verification. Its intended scope is matching **business metric definitions** with multi-signal metadata, including relationship classes that matter for data-system maintenance and metric governance.

## 4. Proposed Framework (about 1.5 pages)

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

## 5. Benchmark Construction and Artifacts (about 1.25 pages)

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

## 6. Evaluation Design (about 1.25 pages)

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

1. Freeze the relationship taxonomy and metric-card schema.
2. Label 20–30 metric pairs, beginning with the supplied account/opportunity cross-grain-equivalence pair.
3. Select the public Snowflake source and write the benchmark-construction protocol.
4. Implement and validate the five baseline methods before proposing the router.
5. Run the public experiments, then the anonymized industrial validation.
6. Write only completed results into the final paper; mark design ideas as future work until tested.

## First next task for the user

Confirm the proposed paper scope in one sentence:

> “We will study topology-aware matching of enterprise metric definitions, with cross-grain equivalence as a primary relationship type.”

After confirmation, the next task will be a compact metric-card template for labeling the remaining examples.

## References to verify and cite

- E. Rahm and P. A. Bernstein, “A Survey of Approaches to Automatic Schema Matching,” *VLDB Journal*, 2001.
- J. Madhavan, P. A. Bernstein, and E. Rahm, “Generic Schema Matching with Cupid,” *VLDB*, 2001.
- C. Koutras et al., “Valentine: Evaluating Matching Techniques for Dataset Discovery,” *ICDE*, 2021. https://arxiv.org/abs/2010.07386
- Y. Li et al., “Deep Entity Matching with Pre-Trained Language Models,” *PVLDB*, 2021. https://arxiv.org/pdf/2004.00584
- M. Parciak et al., “Schema Matching with Large Language Models: an Experimental Study,” *VLDB TaDA Workshop*, 2024. https://www.vldb.org/workshops/2024/proceedings/TaDA/TaDA.8.pdf
- B. Haynes et al., “GEqO: ML-Accelerated Semantic Equivalence Detection,” 2024 preprint. https://arxiv.org/pdf/2401.01280
