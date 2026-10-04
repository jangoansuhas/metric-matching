# Detecting Metric Definition Drift Across Evolving Data Models

**SANER 2027 paper outline — public-repository study**  
**Updated:** September 28, 2026  
**Status:** Working manuscript outline. A completed held-out evaluation, independent adjudication, and a defensible contribution beyond strong baselines are still required. No outcome is presumed.

## Paper at a glance

**Software maintenance problem.** Analytics teams maintain SQL models and semantic metric declarations over time. Two definitions can have similar names but differ in grain, filter, time, business state, or NULL handling. A definition can also change across commits without a corresponding name change. A useful maintenance tool must explain the relationship, identify missing evidence, and avoid unsafe equivalence assertions.

**Primary study objects.** Versioned numeric metric declarations and their source SQL in public dbt/SQL repositories. Within-project pairs at one pinned revision form the matching task; adjacent parent–child commits form a separate change-analysis task. A named measure and a published metric are distinct objects unless a verified binding connects them. The study does not use employer definitions, proprietary findings, or student-record deduplication.

**Claim to test.** Evidence-linked, version-aware comparison with explicit grain, time, scope, and value-semantics prerequisites may improve safe maintenance decisions beyond lexical, AST/lineage, and constraint-aware methods given the same source context. This is a hypothesis. A tie or a negative result must narrow the claim to a transparent investigation of where public metric analysis succeeds, abstains, or fails.

**Submission route.** Target a SANER 2027 Industrial Track full paper only if the public repositories have documented practical use and the study completes a sound, maintenance-relevant evaluation. The [official Industrial call](https://conf.researchr.org/track/saner-2027/saner-2027-industrial-track) allows practitioner-driven real-world cases and calls for systematic investigation; its mandatory abstract is due **October 19, 2026** and the full paper **October 23, 2026** (AoE). The [Registered Report track](https://conf.researchr.org/track/saner-2027/saner-2027-registered-report-track) is a separate plan-first route if completed results are unavailable. A track decision is not a claim of acceptance.

**Space plan:** the Industrial full-paper limit is ten pages of text, figures and appendices, plus up to two reference pages. Allocate roughly one page to the introduction, one to prior work and problem definition, two to method, two to corpus and evaluation, two to results, and one to discussion/conclusion, leaving room for a figure and tables. Rebalance after results exist.

## Proposed abstract (write after results)

1. **Problem:** Metric names and expressions change across analytics repositories; simple similarity cannot establish safe reuse or detect consequential drift.
2. **Gap:** Prior schema matching, context-guided matching, and SQL equivalence address adjacent tasks, while maintenance decisions additionally depend on version, target scope, and evidence for proposed reconciliation.
3. **Method:** Extract versioned metric signatures and produce a relationship or change hypothesis with source links, explicit prerequisites, and an abstention when decisive evidence is missing.
4. **Study:** Evaluate naturally occurring definitions and commit changes in selected public repositories; compare methods using identical pair frames and matched evidence budgets, with two independent human judgments and distinct adjudication.
5. **Results and contribution:** Insert only observed extraction coverage, retrieval, decision safety, maintenance utility, uncertainty, and strongest-baseline comparisons. Do not write a superiority sentence until the held-out study supports it.

## 1. Introduction and motivating failure mode

- Establish the maintenance task: deciding whether a metric can replace another, whether a definition changed materially, and which changes warrant review. Avoid any claim that private metric volume or data volume was evaluated.
- Use a pinned **public development illustration**: an observed Jaffle Shop order-subtotal versus item-revenue comparison agrees in aggregate yet differs at order grain when an order has no items. In the inspected finite sample, 483 such orders require an explicit missing-group and NULL-to-zero rule for reconciliation. This illustrates a proof obligation; it is not held-out performance or universal equality.
- Distinguish two questions: “Do these definitions represent the same scoped scalar?” and “Did this definition preserve behavior across a commit?” Similar names, finite equal totals, or a SQL diff do not settle either question.
- End with three conditional contributions: (i) a traceable metric relationship and change representation; (ii) a reproducible public evaluation protocol and, if completed, adjudicated corpus; and (iii) measured safety and practical utility against strong baselines. State any failure to establish one of these.

## 2. Task definition and relationship taxonomy

**Comparison unit.** One identified numeric scalar output from each of two version-pinned definitions under a declared target grain, population, time window, snapshot/business state, unit, grouping, and value rule. Whole-row equivalence is outside this scalar task unless separately specified and checked.

**Primary relationship classes at the stated scope:**

| Class | Decision criterion |
| --- | --- |
| Direct equivalent | Supported equality of the defined scalar at aligned grain, time, population, units, and value semantics. |
| Cross-grain equivalent | A specified, established transformation maps the definitions to the same target scope, including join multiplicity, absent groups, and NULL rules. |
| Temporal or scope variant | The same identified quantity with a changed time rule, state, filter, hierarchy, or population. |
| Related | A documented semantic link without safe substitution or an established single variant rule. |
| Conflicting definition | The same asserted identity or materially similar published name denotes incompatible meanings, with no coherent scope variant explaining it. |
| Non-match | Source-supported distinct quantities with no meaningful defined link in the available project context. |

**Evidence axis.** Separately record sufficient versus needs_review; missing evidence is not a seventh relationship. Leave the relationship undecided when decisive binding, lineage, scope, or execution evidence is absent. For a conditional relation at a different target scope, name the transform and separately record its prerequisites as verified, inapplicable with reason, assumed, unknown, or contradicted.

**Across-version task.** Link one scalar between adjacent commits by a source-supported ID or rename. Distinguish behavior-preserving, behavior-changing, and unresolved changes. Record a source-level affected input domain or counterexample and any finite observed-row evidence separately. Dependencies and potential consumers do not establish observed downstream impact.

## 3. Related work and novelty test

- [Valentine: Evaluating Matching Techniques for Dataset Discovery](https://arxiv.org/abs/2010.07386) supplies schema-matching scenarios, benchmarks, and evaluation practices. The [PVLDB Valentine demonstration](https://www.vldb.org/pvldb/vol14/p2871-koutras.pdf) is a separate demo, not the main empirical paper.
- [ConStruM](https://arxiv.org/abs/2601.20482) demonstrates structure-guided context for LLM schema matching. [Constraint-Guided Enterprise Data Mapping](https://arxiv.org/abs/2608.24218) combines constraints, ranking, and LLM disambiguation. Context packing, constraints, abstention, and an LLM are therefore prior ideas.
- [GEqO: ML-Accelerated Semantic Equivalence Detection](https://arxiv.org/abs/2401.01280) studies scalable equivalence of executable computations. AST/lineage tools supply a practical strong source-context comparator. Business-scoped metric relationships and maintenance effects still require separate evaluation.
- The possible added value is a **measured, version-aware maintenance decision with explicit reconciliation prerequisites**, rather than a new similarity metric. If a context-fair AST or constraint baseline gives the same safe decisions and effort, report that finding and narrow the novelty claim.

## 4. Method: versioned, evidence-linked decisions

1. **Inventory.** Enumerate all eligible numeric metric declarations at a pinned revision, retaining unsupported and unknown numeric eligibility. Keep declared measures separate from exposed metrics; record source positions, stable IDs, and extraction failures.
2. **Provenance.** Link each declaration to its referenced measure, model, compiled scalar expression, field owners, dependencies, and build revision only when each link is verified. A compiled model file is not by itself a compiled metric query. Report the missing links explicitly.
3. **Signature.** Record name/aliases, expression, source lineage, native and target grains, grouping, population/filter, business state/snapshot, time semantics, units/conversion, NULL/absent-row and rounding behavior, plus immutable evidence references.
4. **Candidate retrieval.** Rank within-project pairs at a pinned version. Keep across-version linkage as a separate task. Use the complete enumerated ID frame, including ranking failures, for each method.
5. **Decision.** Compare typed signatures and version diffs; emit a scoped class or change hypothesis, supporting source lines, an explicit transform where justified, and named missing prerequisites. Abstain when source binding, additivity, joins, or value semantics remain unknown.
6. **Consumer context.** Record source-linked potential downstream dependencies. Assert measured consumer changes or maintenance actions only if separately observed.

## 5. Public data, sampling, and human reference judgments

- **Development only:** the already inspected Jaffle Shop/Sidemantic, GTM, and Rill revisions and controlled synthetic fixtures support parser work, rule calibration, and examples. Keep their cases and practice worksheets outside held-out denominators.
- **Held-out selection:** a dated, complete metadata-only search frame has been recorded. After the generic adapter, numeric eligibility policy, pair IDs, context-matched baselines, and annotation budget are fixed on development inputs, apply the preregistered eligibility and hash-selection rules to public repositories. Do not choose projects or commits based on interesting positive matches. No new held-out source has yet been opened.
- **Study frames:** record every eligible metric ID and within-project unordered pair at the pinned commit; separately enumerate linked adjacent-commit events, including unchanged controls, unsupported definitions, and failed builds. Freeze strata, pair quotas, candidate budgets, and inclusion rules before outcomes are seen.
- **Human labels:** two distinct qualified domain reviewers independently inspect an identical versioned, prediction-free source packet. A third distinct qualified reviewer adjudicates label, scope, evidence-sufficiency, and conditional-prerequisite disagreements after both originals are locked. A predeclared fraction of agreements receives an adjudication audit. Preserve originals and time logs; the three public **practice** pairs only calibrate instructions and do not create held-out gold.
- **Anchor completeness:** exact Recall@k requires every eligible candidate for each selected anchor to be judged for the particular target relation. If the budget cannot support this, reduce anchor count by a predeclared rule before labels, or report explicitly named judged-pool retrieval results rather than exact recall.

## 6. Fair baselines and evaluation plan

| Comparison | Same evidence and pair frame | Purpose |
| --- | --- | --- |
| Names only (I0) | Raw/normalized exact match, Jaro–Winkler, token Jaccard, Soundex over the same names and IDs | Limited-input candidate retrieval reference. |
| Source context (I1) | Normalized expression/AST and column-lineage comparator; constraint-aware grain/filter/time comparator; proposed method, all given the same pinned SQL/YAML, compiled evidence where verified, and check budget | Test incremental safety and useful conditional decisions. |
| Version context (I2) | Paired source revisions, aligned diffs/dependencies for baseline and proposed change detectors | Test behavior-change triage; do not compare against an I1-only baseline as if contexts were equal. |
| Optional LLM | Same I1 packet, candidate list, output schema, prompt budget and frozen model/version, if accessible | Context-fair comparison; no claim that Mistral Large or any LLM was run on the public test set. |

**Measures:** (a) eligible-definition and verified-expression coverage; (b) Recall@k only on complete, resolved anchor universes, separately for direct and conditional positives; (c) six-class confusion and precision/recall on the same adjudicated sampled pairs when sample counts support them; (d) unsafe equivalence assertions, conditional-prerequisite errors, abstention, and review coverage by project; (e) adjacent-commit change classifications, source counterexamples, and verified consumer effects if available; and (f) runtime/API cost and human review effort where measured.

Reviewer effort requires a **separate randomized, evidence-matched review study** against concealed adjudicated judgments; time spent creating gold labels alone does not show that a method saves maintenance work. Report per-project denominators and uncertainty; do not treat correlated pairs as independent projects. An empty positive class, unresolved target universe, or wide uncertainty limits the conclusion.

## 7. Results structure — fill only after held-out execution

1. Corpus flow: search/eligibility counts, selected public projects and commits, extraction and compiled-provenance coverage, unsupported syntax, and annotation denominators.
2. Retrieval: project-level candidate frames, complete-anchor Recall@k or explicitly qualified judged-pool results, cost and missed candidates.
3. Relationship and drift decisions: fixed-pair confusion, unsafe-equivalence rate, abstention and prerequisite failures, behavior-change evidence.
4. Practical maintenance outcomes: reviewer accuracy/effort against the strong baseline if the separate reviewer study runs; otherwise omit a time-saved claim.
5. Failure analysis: NULL versus zero, missing groups, ambiguous measure binding, changed filters or temporal scopes, SQL compilation and lineage limits, and comparator ties.
6. Ablations: omit version, provenance, or conditional prerequisites only if the frozen analysis and sample size support interpretable contrasts.

Do not promote practice answers, an AI implementation review, a constructed positive, same-file co-location, or matching finite totals to natural held-out labels or method superiority.

## 8. Discussion, validity, and ethics

Discuss when source-only maintenance signals are useful; when precise relation claims require compiled metric queries, runtime data, or domain-owner evidence; and when abstention is the safe output. Address public-project selection bias, repository dependence, limited numeric eligibility, Jinja/macros/CTEs/windows, changed dependencies, sparse natural positives, annotator agreement and conflict, and finite-row/engine portability. A public repository can be industrially relevant without claiming it is a private enterprise deployment. Use only publicly releasable artifacts and check licenses and source links.

## 9. Conclusion

Summarize only supported maintenance findings: which relationships and definition changes can be explained from public versioned sources, which remain unresolved, and how the strongest comparator performs at the same evidence budget. If the proposed method ties a simpler method, state that plainly and present the grounded benchmark or failure-mode result instead of asserting a novel win.

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

**Immediate work:** on an already inspected development project, reproduce a same-commit build with pinned dependencies, trace a declared metric to an actual compiled scalar expression and field owners, and rerun credible AST/lineage, constraint-aware, and proposed methods on the identical full evidence packet. Independently complete development calibration with a third reviewer. Freeze extraction coverage, comparison rules, prompts if used, and affordable anchor/human budgets before applying the precommitted held-out project selection. Until then, this is a paper outline with development diagnostics, **not** a completed empirical paper.
