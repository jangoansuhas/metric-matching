# Evidence-Linked Metric Relationship Decisions in SQL/dbt Repositories

**SANER 2027 paper outline — public-repository study**  
**Updated:** September 28, 2026  
**Status:** Working manuscript outline. A completed held-out evaluation, independent adjudication, and a defensible contribution beyond strong baselines are still required. No outcome is presumed.

## Paper at a glance

**Software maintenance problem.** Analytics teams maintain SQL models and semantic metric declarations over time. Two definitions can have similar names but differ in grain, filter, time, business state, or NULL handling. A definition can also change across commits without a corresponding name change. A useful maintenance tool must explain the relationship, identify missing evidence, and avoid unsafe equivalence assertions.

**Primary study objects.** Numeric metric declarations and their source SQL at pinned revisions of public dbt/SQL repositories. Within-project pairs at one revision form the primary relationship task. Adjacent parent–child commits are a separate, prospective change-analysis task and must not be advertised as a measured drift result unless evaluated. A named measure and a published metric are distinct objects unless a verified binding connects them. The study does not use employer definitions, proprietary findings, or student-record deduplication.

**Claim to test.** Evidence-linked comparison with explicit grain, time, scope, and value-semantics prerequisites may reduce unsafe equivalence decisions beyond lexical, AST/lineage, and constraint-aware methods given the same source context and decision coverage. This is a hypothesis. A tie or a negative result must narrow the claim to a transparent investigation of where public metric analysis succeeds, abstains, or fails.

**Submission route.** Target a SANER 2027 Industrial Track full paper only if the public repositories have documented practical use and the study completes a sound, maintenance-relevant evaluation. The [official Industrial call](https://conf.researchr.org/track/saner-2027/saner-2027-industrial-track) allows practitioner-driven real-world cases and calls for systematic investigation; its mandatory abstract is due **October 19, 2026** and the full paper **October 23, 2026** (AoE). The [Registered Report track](https://conf.researchr.org/track/saner-2027/saner-2027-registered-report-track) is a separate plan-first route if completed results are unavailable. A track decision is not a claim of acceptance.

**Space plan:** the Industrial full-paper limit is ten pages of text, figures and appendices, plus up to two reference pages. Allocate roughly one page to the introduction, one to prior work and problem definition, two to method, two to corpus and evaluation, two to results, and one to discussion/conclusion, leaving room for a figure and tables. Rebalance after results exist.

## Proposed abstract (write after results)

1. **Problem:** Similar names and expressions do not establish that two published metrics can be substituted at a stated scope.
2. **Gap:** Prior schema matching, context-guided matching, and SQL equivalence address adjacent tasks, while maintenance decisions additionally depend on target scope and evidence for proposed reconciliation.
3. **Method:** Extract pinned metric signatures and produce a relationship hypothesis with source links, explicit prerequisites, and an abstention when decisive evidence is missing.
4. **Study:** Evaluate naturally occurring metric definitions in selected public repositories; compare methods using identical pair frames and matched evidence budgets, with two independent human judgments and distinct adjudication. Report commit-change analysis only if separately completed.
5. **Results and contribution:** Insert only observed extraction coverage, retrieval, decision safety, maintenance utility, uncertainty, and strongest-baseline comparisons. Do not write a superiority sentence until the held-out study supports it.

## 1. Introduction and motivating failure mode

- Establish the maintenance task: deciding whether one published metric can replace another at a stated scope and which apparent duplicates warrant review. An adjacent-commit change task may follow if independently executed. Avoid any claim that private metric volume or data volume was evaluated.
- Use a pinned **public development illustration**: an observed Jaffle Shop order-subtotal versus item-revenue comparison agrees in aggregate yet differs at order grain when an order has no items. In the inspected finite sample, 483 such orders require an explicit missing-group and NULL-to-zero rule for reconciliation. This illustrates a proof obligation; it is not held-out performance or universal equality.
- Distinguish the primary question, “Do these definitions represent the same scoped scalar?”, from the prospective question, “Did this definition preserve behavior across a commit?” Similar names or finite equal totals do not settle the primary question.
- End with three conditional contributions: (i) a traceable metric relationship representation with explicit proof obligations; (ii) a reproducible public evaluation protocol and, if completed, adjudicated corpus; and (iii) measured safety against strong baselines. Include change-analysis or practical-utility claims only if separately demonstrated.

## 2. Task definition and relationship taxonomy

**Comparison unit.** One identified numeric scalar output from each of two version-pinned definitions under a declared target grain, population, time window, snapshot/business state, unit, grouping, and value rule. Whole-row equivalence is outside this scalar task unless separately specified and checked.

**Primary relationship classes at the stated scope:**

| Class | Decision criterion (verbatim from the distributed practice packet) |
| --- | --- |
| `direct_equivalent` | Same defined output under aligned grain, inputs, time, units, and population, without a grain-changing transform. |
| `cross_grain_equivalent` | A specified deterministic, valid rollup maps one grain to the other under aligned inputs, time, units, and population, including missing-group and NULL handling. |
| `temporal_or_scope_variant` | Documented shared measure concept with a changed time rule, filter, state, or population. |
| `conflicting_definition` | The same or materially similar published name is used for incompatible documented meanings. |
| `related` | Documented semantic connection, but the defined outputs do not meet a more specific label. |
| `non_match` | No supported semantic relationship for the compared outputs. |

**Boundary guidance for future, identically distributed packets.** Tax included versus tax excluded changes the computed quantity and can be `related` when the documented relation is “before/after tax”; do not automatically treat it as a population or time-scope change. Sharing a file, model, grain, or similar name alone is not a documented semantic connection: a source-supported computational link, shared documented measure concept, or derivation is needed. For example, a cost and a customer price on the same orders table may be `non_match` at the stated scalar scope if no such link is documented. A constructed `conflicting_definition` control could use two published metrics both named `net_revenue`, one documented as discounted recurring contract value and the other as recognized invoice revenue; this is a proposed rubric exercise, not a natural observation or additional practice label. No conflicting-definition case appeared among the three distributed practice pairs. Freeze any expanded rubric before distributing it equally to new reviewers; do not reinterpret the original practice worksheets under a revised rubric.

**Evidence axis.** Use the packet rule verbatim: If a fact needed to decide the relationship is missing, mark `needs_review`, leave the relationship blank if necessary, and say exactly what evidence is missing. Do not guess a label from names alone. A missing fact that cannot affect a source-supported decision can be recorded as a limitation while `sufficient` remains justified; the annotator must explain why it is immaterial. The disputed CAL-03 measure-to-metric binding has not been verified, so its practice disagreement remains unresolved until third-person adjudication. For a conditional relation at a different target scope, name the transform and separately record its prerequisites as verified, inapplicable with reason, assumed, unknown, or contradicted.

**Prospective across-version task.** If resources allow, link one scalar between adjacent commits by a source-supported ID or rename. Distinguish behavior-preserving, behavior-changing, and unresolved changes. Record a source-level affected input domain or counterexample and any finite observed-row evidence separately. Dependencies and potential consumers do not establish observed downstream impact. This task requires its own gold, baseline, and results before the paper can claim drift detection.

## 3. Related work and novelty test

- [Valentine: Evaluating Matching Techniques for Dataset Discovery](https://arxiv.org/abs/2010.07386) supplies schema-matching scenarios, benchmarks, and evaluation practices. The [PVLDB Valentine demonstration](https://www.vldb.org/pvldb/vol14/p2871-koutras.pdf) is a separate demo, not the main empirical paper.
- [ConStruM](https://arxiv.org/abs/2601.20482) demonstrates structure-guided context for LLM schema matching. [Constraint-Guided Enterprise Data Mapping](https://arxiv.org/abs/2608.24218) combines constraints, ranking, and LLM disambiguation. Context packing, constraints, abstention, and an LLM are therefore prior ideas.
- [GEqO: ML-Accelerated Semantic Equivalence Detection](https://arxiv.org/abs/2401.01280) studies scalable equivalence of executable computations. AST/lineage tools supply a practical strong source-context comparator. Business-scoped metric relationships and maintenance effects still require separate evaluation.
- The falsifiable added-value hypothesis is that **explicit reconciliation prerequisites reduce unsafe equivalence assertions at matched decision coverage** on the same I1 pairs and source evidence versus the strongest AST/lineage and constraint-aware comparator. Count an unsafe assertion when a method outputs `direct_equivalent` or `cross_grain_equivalent` at the stated scope but an independent adjudicated reference rejects that assertion or a required prerequisite is contradicted; separately count unsupported/unknown assertions. Compare selective risk across coverage levels within projects, using a frozen score/tie rule. At zero decisions or no adjudicated examples, this hypothesis is untestable, not supported. If the strong baseline ties, narrow the novelty claim to the grounded dataset/protocol or failure analysis. Across-commit novelty requires a separate study.

## 4. Method: versioned, evidence-linked decisions

1. **Inventory.** Enumerate all eligible numeric metric declarations at a pinned revision, retaining unsupported and unknown numeric eligibility. Keep declared measures separate from exposed metrics; record source positions, stable IDs, and extraction failures.
2. **Provenance.** Link each declaration to its referenced measure, model, compiled scalar expression, field owners, dependencies, and build revision only when each link is verified. On the already inspected development checkout, reproduce `dbt parse` and a MetricFlow metric SQL generation (`mf query --explain` for self-hosted dbt v1, or an appropriate `--compile` path) in an isolated, same-commit build; record dependency lock, adapter, invocation, artifact hashes, and any warehouse-connection requirement. Parsing a semantic manifest or finding a same-named measure is not proof of the executable metric expression; a compiled model file is not by itself a compiled metric query. Report missing links explicitly.
3. **Signature.** Record name/aliases, expression, source lineage, native and target grains, grouping, population/filter, business state/snapshot, time semantics, units/conversion, NULL/absent-row and rounding behavior, plus immutable evidence references.
4. **Candidate retrieval.** Rank within-project pairs at a pinned version. Keep across-version linkage as a separate task. Use the complete enumerated ID frame, including ranking failures, for each method.
5. **Decision.** Compare typed signatures; emit a scoped relationship hypothesis, supporting source lines, an explicit transform where justified, and named missing prerequisites. Abstain when source binding, additivity, joins, or value semantics remain unknown. Add version-diff classification only in the separately evaluated change task.
6. **Consumer context.** Record source-linked potential downstream dependencies. Assert measured consumer changes or maintenance actions only if separately observed.

## 5. Public data, sampling, and human reference judgments

- **Development only:** the already inspected Jaffle Shop/Sidemantic, GTM, and Rill revisions and controlled synthetic fixtures support parser work, rule calibration, and examples. Keep their cases and practice worksheets outside held-out denominators.
- **Held-out selection:** a dated, complete metadata-only search frame has been recorded. After the generic adapter, numeric eligibility policy, pair IDs, context-matched baselines, and annotation budget are fixed on development inputs, apply the preregistered eligibility and hash-selection rules to public repositories. Do not choose projects or commits based on interesting positive matches. No new held-out source has yet been opened.
- **Study frames:** record every eligible metric ID and within-project unordered pair at the pinned commit. Freeze strata, pair quotas, candidate budgets, and inclusion rules before outcomes are seen. Enumerate linked adjacent-commit events, including unchanged controls, only if the separate drift study is staffed and preregistered.
- **Human labels:** two distinct qualified domain reviewers independently inspect an identical versioned, prediction-free source packet. A third distinct qualified reviewer adjudicates label, scope, evidence-sufficiency, and conditional-prerequisite disagreements after both originals are locked. A predeclared fraction of agreements receives an adjudication audit. Preserve originals and time logs; the three public **practice** pairs only calibrate instructions and do not create held-out gold.
- **Anchor completeness:** exact Recall@k requires every eligible candidate for each selected anchor to be judged for the particular target relation. If the budget cannot support this, reduce anchor count by a predeclared rule before labels, or report explicitly named judged-pool retrieval results rather than exact recall.
- **Annotation budget estimate and fallback (planning figure; not a frozen allocation):** the two three-pair practice worksheets report about 38 and 60 active minutes, or 98/6 = **16.3 minutes per person per pair judgment**. At that pace, 100 pairs judged twice require about **54 reviewer-hours** before adjudication, audits, packet preparation, or slow held-out cases. A hypothetical 24-hour envelope (18 first-pass, four adjudication/audit, two coordination) would fund only about 33 twice-reviewed pairs at the practice pace. Before any held-out source is opened, obtain a real reviewer-hour commitment, select a smaller complete-anchor frame if feasible, and freeze its selection rule, disagreement/audit allowance, and fallback to explicitly named judged-pool retrieval if complete anchors do not fit. Do not report exact Recall@k on an incomplete universe. This estimate does not authenticate practice reviewers or imply a staffing commitment.

## 6. Fair baselines and evaluation plan

| Comparison | Same evidence and pair frame | Purpose |
| --- | --- | --- |
| Names only (I0) | Raw/normalized exact match, Jaro–Winkler, token Jaccard, Soundex over the same names and IDs | Limited-input candidate retrieval reference. |
| Source context (I1) | Normalized expression/AST and column-lineage comparator; constraint-aware grain/filter/time comparator; proposed method, all given the same pinned SQL/YAML, compiled evidence where verified, and check budget | Test incremental safety and useful conditional decisions. |
| Version context (I2) | Paired source revisions, aligned diffs/dependencies for baseline and proposed change detectors | Test behavior-change triage; do not compare against an I1-only baseline as if contexts were equal. |
| Optional LLM | Same I1 packet, candidate list, output schema, prompt budget and frozen model/version, if accessible | Context-fair comparison; no claim that Mistral Large or any LLM was run on the public test set. |

**Measures:** (a) eligible-definition and verified-expression coverage; (b) Recall@k only on complete, resolved anchor universes, separately for direct and conditional positives; (c) six-class confusion and precision/recall on the same adjudicated sampled pairs when sample counts support them; (d) unsafe equivalence assertions **at matched decision coverage**, conditional-prerequisite errors, abstention, and review coverage by project; (e) adjacent-commit change classifications only if separately evaluated; and (f) runtime/API cost and human review effort where measured.

Reviewer effort requires a **separate randomized, evidence-matched review study** against concealed adjudicated judgments; time spent creating gold labels alone does not show that a method saves maintenance work. Report per-project denominators and uncertainty; do not treat correlated pairs as independent projects. An empty positive class, unresolved target universe, or wide uncertainty limits the conclusion.

## 7. Results structure — fill only after held-out execution

1. Corpus flow: search/eligibility counts, selected public projects and commits, extraction and compiled-provenance coverage, unsupported syntax, and annotation denominators.
2. Retrieval: project-level candidate frames, complete-anchor Recall@k or explicitly qualified judged-pool results, cost and missed candidates.
3. Relationship decisions: fixed-pair confusion, unsafe-equivalence rate at matched coverage, abstention, and prerequisite failures. Include change decisions only if the separate task is completed.
4. Practical maintenance outcomes: reviewer accuracy/effort against the strong baseline if the separate reviewer study runs; otherwise omit a time-saved claim.
5. Failure analysis: NULL versus zero, missing groups, ambiguous measure binding, changed filters or temporal scopes, SQL compilation and lineage limits, and comparator ties.
6. Ablations: omit provenance or conditional prerequisites only if the frozen analysis and sample size support interpretable contrasts; omit version only in a separately executed change study.

Do not promote practice answers, an AI implementation review, a constructed positive, same-file co-location, or matching finite totals to natural held-out labels or method superiority.

## 8. Discussion, validity, and ethics

Discuss when source-only maintenance signals are useful; when precise relation claims require compiled metric queries, runtime data, or domain-owner evidence; and when abstention is the safe output. Address public-project selection bias, repository dependence, limited numeric eligibility, Jinja/macros/CTEs/windows, changed dependencies, sparse natural positives, annotator agreement and conflict, and finite-row/engine portability. A public repository can be industrially relevant without claiming it is a private enterprise deployment. Use only publicly releasable artifacts and check licenses and source links.

## 9. Conclusion

Summarize only supported maintenance findings: which relationships can be explained from pinned public sources, which remain unresolved, and how the strongest comparator performs at the same evidence budget and decision coverage. Mention definition changes only if the separate change study produces results. If the proposed method ties a simpler method, state that plainly and present the grounded benchmark or failure-mode result instead of asserting a novel win.

## 10. Data Availability

After the conclusion, state where vetted public code, project/commit manifests, prompts when used, annotation protocol, permitted public evidence and aggregated results can be obtained. Explain any unreleased material and the reason; do not include private development fixtures or identifiable reviewer records in a public artifact.

## Current evidence and next gate (author planning note; not manuscript results)

| Completed development work | What it does and does not establish |
| --- | --- |
| Pinned public Jaffle/Sidemantic declaration inventory: 19 metrics and 13 measures, 496 unordered emitted-ID pairs (171 exposed-metric pairs). | The frame is complete over emitted IDs; 10 declarations have unknown numeric eligibility. No natural-pair gold labels follow. |
| Same-input development diagnostic: three source-context methods saw identical I1 packet/pair IDs and abstained on all 496 semantic decisions. | Plumbing and conservative coverage are demonstrated. **Zero** declared metrics have verified compiled metric-expression provenance; no AST semantic comparison or proposed-method advantage is established. |
| Pinned GTM development comparison: 11 cards, 55 pairs. | The proposed and strong constraint-aware methods surfaced the same two conditional hypotheses; neither has human-adjudicated correctness. |
| Two received public practice worksheets on three development pairs; one relationship/evidence-status disagreement identified for third-person review. | Instruction calibration only. Reviewer qualification/adjudication and held-out human reference judgments are incomplete. Practice responses stay outside scored test results. |
| Metadata-only held-out search frame: 65 ordered occurrences, 62 distinct pinned HEADs. | Search provenance exists. **No new held-out repository source has been inspected.** A fixed generic compiled-metric adapter and fair same-input baselines remain the gate before selecting and opening any source. |

**Immediate work:** on the already inspected Jaffle development project, reproduce a same-commit dbt/MetricFlow build with pinned dependencies, trace CAL-03's `order_cost` declaration through the semantic-model measure and compiled metric SQL to model expression and field owners, and rerun credible AST/lineage, constraint-aware, and proposed methods on the identical full evidence packet. The existing `target/semantic_manifest.json` contains a same-name `order_cost` measure under `orders`, but its build revision is unattested and this is **name-level evidence only**. The cached `target/manifest.json` reports dbt 1.12.5 with a DuckDB adapter; the local checkout's package lock differs from the pinned Git commit. The current environment lacks dbt and MetricFlow, and an isolated offline dependency attempt failed because `dbt-core` is not cached. A clean same-commit rebuild and SQL-generation/connection check remain open. Independently complete development calibration with a third reviewer and test a constructed conflicting-definition control in an equally distributed future packet. Freeze extraction coverage, comparison rules, prompts if used, and affordable anchor/human budgets before applying the precommitted held-out project selection. Until then, this is a paper outline with development diagnostics, **not** a completed empirical paper.
