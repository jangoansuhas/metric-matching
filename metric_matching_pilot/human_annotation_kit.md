# Blinded domain-human annotation kit (template)

**Status:** prospective operating template for the public held-out study. No repositories, pairs, events, human judgments, or gold labels are supplied here. Use with `evaluation_contract.md`, `heldout_sampling_protocol.md`, and `annotation_schema.json` (schema version `1.0`). The contract controls if this kit is incomplete. Prior development cases and the AI review in `conditional_method_review.md` may inform rubric calibration **on development material only**; neither is human gold.

## 1. Freeze the run before distributing work

The coordinator completes and versions this run sheet before opening new held-out source or system outputs. Leave an unfilled field as pending, not as an implicit default. Preserve the earlier protocol and append dated reasons for amendments.

| Run setting | Fill before the relevant gate |
| --- | --- |
| Rubric version, approval UTC, coordinator | ___ |
| Search-result manifest ID, digest, UTC snapshot, page limit, eligibility/selection-table digests | ___ |
| Definition extractor/ID policy, tie/merge-parent rules, project/version and submodule pins | ___ |
| Pair frame digest; lexical/lineage/random quotas, hash/order, deduplication and inclusion-probability rules | ___ |
| Anchor hash/order, per-project quota, eligible ID-list digests, `universe_id` convention | ___ |
| Retrieval targets: direct at stated scope; conditional cross-grain target scope and whether discovery alone or a transform proposal counts; preregistered `k` | ___ |
| Pair, event and third-review timeboxes; total human-minute budget; prespecified agreement-audit fraction and selection hash | ___ |
| Reviewer rates/currency and cost policy (paid active minutes, checks, rework, adjudication); stop/escalation rule | ___ |

Follow the contract's manifest-first search and eligibility order. Pin versions, select the four pair-eligible unrelated projects by the frozen rule, then enumerate their eligible scalar IDs and all within-project unordered pairs before drawing the fixed samples. Calibrate reviewers with **development** cases; freeze instructions and time budgets using development sizes before test inspection. Up to 25 sampled pairs and 10 adjacent-commit events per project serve the classification/audit sample, not exhaustive retrieval recall. Log failed extraction/builds as coverage outcomes. Discovered positives go to a marked supplement outside test denominators. No private or company source is required.

**Budget calculation:** freeze an anchor quota and a deterministic hash-order fallback using development-project sizes before held-out inspection. After enumerating pinned eligible IDs but before pair review, calculate distinct exhaustive tasks as the union of `{unordered(anchor, candidate): anchor selected, candidate any other eligible ID}` over each project, plus sampled tasks not already in that union. Budget `2 × first-pass minutes + forecast third-review/audit minutes + packet/check overhead`; record the assumptions and maximum paid minutes. If the exact frame exceeds the frozen budget, apply the predeclared fallback to reduce the **number of anchors** before any pair labels or system results are seen. Do not prune candidates, favor likely positives, or change quotas after labels. Record actual overruns and unresolved work without silently replacing selected anchors.

## 2. Roles, packet and blinding

1. The coordinator assigns two different domain-capable **humans** (H1/H2) per unit, records pseudonym, relevant SQL/dbt/semantic-layer expertise, conflict declarations and task assignments, and checks that neither authored the system predictions or development judgments being hidden. A third, distinct domain-aware human (H3) handles disagreement and the prespecified agreement audit. The same people may work on multiple units subject to the declared conflict policy; no one adjudicates their own label.
2. Give H1 and H2 the **same** read-only, versioned packet and rubric with a digest. Show pinned source links and reproducible checks, but conceal all model outputs, ranks, scores, method explanations, previous analyst labels, reconciliation summaries that encode an answer, and each other's submissions. Use separate submission channels; do not discuss a unit until both timestamps and digests are locked. A neutral packet may contain source, declarations, compiled artifacts and unlabeled observations with provenance. Do not include hand-curated gold fields or a suggested transformation from a matcher.
3. Packet header: `record_id`, project `owner/repo@SHA`, `source_frame_id`/frame digest, `sample_role`, selection stratum/order/inclusion probability or reason unknown, `anchor_id`/`universe_id` when applicable, rubric version, packet version/digest, source access instructions, and permitted check budget. For a pair, include both stable metric IDs, commit SHAs, scalar fields, measure expressions with immutable file/line references, native grains, grouping/time keys and periods, filters, population/business state, snapshot, unit/currency and value/NULL rules. Declare **one fixed comparison scope** (including target grain, population, time window and compared scalar fields) before assigning reviewers. Record unknown metadata as unknown rather than guessing it. For events add adjacent parent/child SHAs, parent index, metric link/rename evidence, dependency and consumer source links.
4. Keep a versioned data dictionary of metric IDs, expressions, source/artifact digests and extraction failures. Evidence items have stable IDs, kind (`source`, `semantic_declaration`, `compiled`, `row_check`, `test`, `owner_assertion`, `issue_or_change_ticket`, `consumer_observation`), artifact/immutable locator, finding and limitation. Record check engine/version, input snapshot, exact command/query, output digest, inspected files and outcome; a finite row comparison is an observation over those rows, not a general proof. Owner assertions show intended semantics, not independent truth.
5. Reviewers may inspect pinned source and run checks within the same declared allowance. Log every opened artifact and check. Send new decisive evidence to the coordinator for a **symmetric**, versioned packet update to both reviewers; preserve already submitted judgments and append an independent revision after the updated packet is issued. Never expose predictions or the other submission during this process.

## 3. Independent pair worksheet: one scalar at one scope

Complete one worksheet per unordered pair and fixed comparison scope. A grouped scalar is still a scalar claim over identified keys. A matching alias or numeric total does not establish whole-row equality. If a whole-row task is separately commissioned, mark `claim_level=whole_row` and enumerate projected columns, keys/uniqueness, multiplicity, joins and NULL/absent-row policy; keep its results out of scalar pair scores.

**Header to fill:** record ID ___; packet digest ___; reviewer pseudonym/expertise ___; start/end UTC ___; active minutes ___; source/check minutes ___; scope grain ___; fields left/right ___/___; grouping keys ___; time key/rule/period/zone ___; population and filters ___; snapshot/state ___; unit/conversion/rounding ___; NULL/absent-row rule ___; left/right metric IDs, SHAs and source refs ___/___; opened evidence IDs ___; check log refs ___.

Choose the **primary relationship at that exact scope** and evidence status independently:

| Primary label | Use only with source-supported reasoning |
| --- | --- |
| `direct_equivalent` | Same scalar meaning at the recorded grain, time, population, unit and value rules, with supported equality. |
| `cross_grain_equivalent` | A specified, **established** map and aggregation yields equality at this recorded target scope; attach the established conditional claim for this scope. |
| `temporal_or_scope_variant` | Same identified conceptual quantity with a different time rule, state, filter, population or hierarchy; coherent disjoint slices may qualify. |
| `related` | Linked quantities that cannot be substituted, without an established single variant rule; counts of different linked entities may fall here. |
| `conflicting_definition` | Same asserted identity/name used for incompatible meanings with no coherent scope-variant explanation; name similarity alone is insufficient. |
| `non_match` | Source supports distinct quantities with no defined meaningful link in the available project context; this is not a universal proof. |

When a name conflict is explained by a coherent scope variant, choose the variant and note the naming issue. Similar formulae with different populations, missing lineage, or one equal total do not prove equivalence. A claim at a different grain, period or population belongs in a separate conditional claim or unit; it does not change the primary label at this scope.

**Decision fields to fill:** relationship label ___; evidence status (`sufficient` / `needs_review`) ___; confidence (`high` / `medium` / `low`) ___; source-backed rationale ___; decisive evidence IDs/locators ___; missing evidence and attempted check ___; optional tentative label (unscored) ___; conditional claim worksheets or none ___; submission UTC ___. Embed full conditional claim objects in the schema record, not just worksheet IDs. With `needs_review`, put `relationship_label=null`, list nonempty decisive gaps, and put any hunch in `tentative_label`. With `sufficient`, choose exactly one of the six labels, leave `missing_evidence=[]`, and do not use a tentative label. Confidence never upgrades missing evidence.

### Conditional-claim worksheet (repeat for each proposed target)

This is a **second** judgment. Fill target label (`direct_equivalent` or `cross_grain_equivalent`), target scalar fields, grain/grouping, time/period, population, snapshot/unit and NULL rule; write the exact input-to-output transformation, aggregation, join keys/type and handling of unassigned rows. Cite evidence for each condition. If no viable target transformation is found, still complete the target screening below and the §5 ledger with a rationale; an empty `conditional_claims` array by itself does not prove a negative for conditional retrieval.

| Required prerequisite (`annotation_schema.json` key) | Reviewer must check | State / rule / evidence IDs |
| --- | --- | --- |
| `source_mapping` | Source-row identity, input/output fields and mapping coverage | ___ |
| `aggregation_and_additivity` | Aggregation, additive domain and intermediate versus final rounding | ___ |
| `hierarchy_membership` | Partition/rollup membership, overlap, unassigned rows, unique target level | ___ |
| `join_cardinality` | Keys, join type, one-to-many duplication and duplicate policy | ___ |
| `missing_groups_and_null` | Missing group/row, zero versus `NULL`, zero-item entities | ___ |
| `filters_and_population` | Predicate equivalence, exclusions, source membership and business state | ___ |
| `time_and_snapshot` | Time key, boundaries, timezone, completeness and as-of alignment | ___ |
| `units_and_rounding` | Unit/currency conversion, precision and rounding order | ___ |

Each state is `verified`, `not_applicable` **with a reason**, `assumed`, `unknown`, or `contradicted`. Cite an evidence item for `verified`/`contradicted`; explain why a condition is inapplicable. Add separately named prerequisites when decisive (the schema permits extra prerequisite keys). Mark `established` only if **every** decisive prerequisite is verified or demonstrably inapplicable over the declared domain; `assumed`/`unknown` makes the claim `unresolved` with missing evidence; a decisive contradiction makes it `refuted` with a counterexample. Record the outcome, rationale and evidence IDs. Do not promote a monthly sum to an order-level result, a date label to a filter, or a finite zero-delta check to universal or engine-independent equality.

**Target screening, completed independently even when no conditional claim is proposed:** at the frozen target scope, direct-equivalence status ___; conditional cross-grain status ___; for each, `positive` / `resolved_negative` / `unresolved`, reason and evidence IDs ___. This operational worksheet is linked by `record_id` to the schema record; do not add undeclared fields to the JSON schema object. A sufficient primary `related` label does not by itself resolve an unknown conditional target. Use `resolved_negative` only when the source and checked domain rule out the target, and `unresolved` when a plausible map or required evidence remains unknown.

## 4. Independent event worksheet (when an event is in the frozen sample)

Use the same blinding, two humans and third-review process. Confirm one linked scalar at adjacent parent/child commits and document stable ID or evidence-backed rename; unresolved links cannot be scored. Fill parent/child SHA, parent index, supported input domain, before/after expression and dependency refs, checks and observed rows (`change_seen`, `no_change_seen`, `not_run`, `unavailable`). Independently choose `behavior_preserving`, `behavior_changing`, or `null` with `sufficient`/`needs_review`; identify an affected domain or source-level counterexample for a change and an unaffected domain if known. A textual expression change alone does not prove changed behavior; unchanged text with changed dependencies does not prove preservation. Keep developer intent (`intended`, `unintended`, `unknown`) tied to issue/owner evidence and list source-linked **potential** consumers separately from observed changed consumer values or remediation. Log confidence, missing evidence, rationale, citations and minutes. Do not infer preservation from a vanished or renamed ID.

## 5. Submission, adjudication and anchor completeness

Lock H1 and H2 originals separately before comparison. The coordinator compares scope, primary label, evidence status, target-screening outcomes, transformation and all decisive prerequisites, not just label strings. H3 receives both originals and the same source packet after lock; independently checks disputed evidence, records additional evidence/checks and minutes, writes their own rationale and final decision, and never overwrites an original. Send even agreements selected by the prespecified hash/fraction for H3 drift audit. Agreeing on a relationship but disagreeing on its scope, sufficiency or decisive conditional status requires adjudication.

Record finalization as `independent_agreement`, `third_adjudication` (with H3 ID), or `unresolved`. Set `gold_eligible=true` only for a sufficient finalized decision under the first two modes; otherwise `unresolved`, `gold_eligible=false`, label `null` and missing reasons. A sufficient six-class primary relationship may coexist with an **unresolved conditional target**: it may be usable for fixed-pair classification, but that pair cannot close the conditional target's anchor denominator. Preserve adjudication notes, additional evidence and any append-only corrections outside immutable submissions. For the core JSON, create one `pairRecord` per scope with exactly two `human_judgments` and one `finalization`; fill all required `sampling` keys (use `null` plus `probability_note` when an inclusion probability is unknown), `scope`, `left`, `right`, and `evidence_sources`. Keep time/check and target-screening ledgers linked by `record_id` outside this strict schema. Validate completed core records against `annotation_schema.json` and separately verify human identity, blinding, packet consistency, source provenance and universe completeness; schema validation alone cannot establish those facts.

**Anchor-universe ledger (one row per anchor–candidate incidence):**

| Project@SHA / universe ID / anchor ID | Candidate ID / unordered pair record ID | Extraction/packet status | H1/H2 lock and finalization | Direct target | Conditional target | Gap / resolution ref |
| --- | --- | --- | --- | --- | --- | --- |
| ___ | ___ | ___ | ___ | ___ | ___ | ___ |

Freeze the eligible metric ID list and each selected anchor's **every other eligible within-project scalar ID**, including extraction failures, with ID-list/universe digests and expected cardinality `N - 1` per anchor. Union and deduplicate symmetric pair annotation tasks, but retain separate incidences for each anchor denominator. Never remove an apparent negative outside lexical/lineage strata, unsupported syntax, failed build, or an unranked candidate. Link each incidence to two independent target screens, source refs, finalization and any third review. Reconcile the ID list, generated incidences, annotated records and final target statuses by ID and count; a blank row is unjudged, never a negative.

For **exact Recall@k**, every candidate for that anchor must have a resolved, sufficient adjudicated status for the **particular target** being scored. Record direct and conditional universes separately; an unresolved prerequisite keeps the conditional anchor unscored even when the primary relationship is sufficient. If a selected anchor has any unresolved/unjudged decisive candidate, show it as unscored with coverage, reasons and sensitivity bounds; do not call a top-25 judged pool exact recall. Reduce anchor count only by the prespecified preinspection budget rule, not after seeing labels. Keep zero-positive anchors in coverage counts, with no per-anchor recall denominator. Freeze `k`; use `min(k, N-1)` and count missing/failed rankings as misses. Keep cross-project and version-link tasks separate unless their own universes were frozen and exhaustively judged.

## 6. Time and reviewer-cost ledger

Start a timer at packet open; pause outside active review. Log active source reading, reproducible checks, decision writing and rework separately; record wall-clock start/end, opened artifact IDs, check commands/results, budget/timebox, overrun reason, reviewer pseudonym/rate, and cost `paid minutes ÷ 60 × frozen hourly rate`. H3 logs evidence review, additional checks and adjudication separately. The coordinator logs packet assembly and quality checks separately, with the same cost policy. If a timebox expires before decisive evidence is obtained, submit `needs_review` with the missing field and stop/escalate per the frozen rule; do not invent a label or silently drop the unit.

| Record ID / stage (`H1`, `H2`, `H3`, packet, QA) | Reviewer ID / expertise | UTC start/end | Read / checks / write / rework / total active minutes | Timebox / overrun | Opened refs / check-log ref | Frozen rate + currency / calculated cost |
| --- | --- | --- | --- | --- | --- | --- |
| ___ | ___ | ___ | ___ | ___ | ___ | ___ |

At close, report pair/event counts, two-human minutes, third-review/audit minutes, packet/QA effort and cost by project and in total; unresolved counts and missing-evidence reasons; raw H1/H2 agreement by **primary relationship, evidence status, conditional-target outcome and event behavior**, including per-class counts and H3 frequency. Report classification on the fixed sampled pairs, retrieval only on complete target-specific anchor universes, and source/extraction coverage. Keep the separate randomized reviewer-effort experiment (baseline versus proposed explanation, counterbalanced order, reviewers distinct from gold adjudicators, same evidence/timebox, opened evidence and edits logged) outside this gold-label workflow. No performance, safety, consumer-effect or gold claim is implied by filling this template.
