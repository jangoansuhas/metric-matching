# Combined AI integration review — September 27, 2026

**Final integrated disposition:** The two implementation defects identified in the initial review are fixed and verified. The three outputs are coherent development diagnostics for a pinned GTM example: branch enumeration, bounded provenance, complete candidate generation, and a source-level version comparison. They do **not** establish semantic equivalence, a technically novel method relative to prior methods, retrieval effectiveness, observed version impact, or an industrial benefit. This is an AI integration review, not human gold, peer review, or held-out evaluation.

## Findings by severity

### High — Effectiveness and novelty claims are not supported

The source-aware script scores all 55 unordered pairs and gives each of 11 queries the same ten candidates under four name-only methods and one source-aware method. Its 1/7-per-feature weights are development heuristics; all 55 relationship decisions abstain. There is no complete judged anchor universe, so rank positions cannot become Recall@k, accuracy, or evidence of improvement. In the highlighted `pipeline_created@month` ↔ `pipeline_created@window` case, exact name matching already ranks the other branch first in both directions; the source-aware score is 0.571429. This example neither demonstrates superiority nor establishes cross-grain equivalence. See `rank_source_aware_candidates.py:111–230`, `source_aware_candidates_report.json` (`diagnostic`, `limits`).

The version probe's seven `potential_metric_change` assessments all arise from a declared model-level path to one token edit, `from contacts c` → `from contacts as c`. The other four assessments abstain. All 11 local branch SQL bodies are identical across the adjacent revisions. Neither revision was compiled or executed for this comparison, and a syntactically cosmetic alias cannot be reported as seven observed metric changes. The local dbt 1.11.6 compiled evidence belongs to later commit `a71232c123a5fb78da9b52d4246950ee48591c00`; it is not a before/after execution of `f387f822ab65f94bb2d04691ed0288ec3cdb17a2` and `a4c122762b910a6a1c847e3d1a4999a5162db00a`. See `analyze_versioned_dbt_branches.py:319–345, 371–397`, `versioned_dbt_branches_report.json` (`negative_control`, `linked_branches`).

### Medium — Unresolved upstream assessment gap (fixed)

For these pinned trees, the corrected resolver treats seeds as terminals: **97 resolved seed-ref occurrences across the 11 branch walks, pointing to nine unique CSV paths, at each commit**, and **zero unresolved upstream refs** on linked paths. These counts are consistent with the JSON paths and the Git trees; seed occurrences are repeated across branch walks, not 97 distinct sources. The `--check` gate verifies the pinned zero count.

**Initial finding:** The earlier formula recorded unresolved refs but chose its assessment solely from direct facets and source edits. An in-memory seed-plus-missing-ref walk showed that the resolver could record a missing edge without that edge qualifying the assessment. The pinned 7/4 count was unaffected because both trees had zero unresolved linked upstream refs.

**Repair verified:** `assess_branch()` now reads unresolved lists from both commits and emits `assessment_qualifier: incomplete_upstream` and `upstream_incomplete: true` (`analyze_versioned_dbt_branches.py:319–345, 380–397`). Without a detected edit it explicitly abstains and says absence of change cannot be inferred; with a detected edit it retains `potential_metric_change` but says additional changes cannot be ruled out. The script's self-check exercises missing and ambiguous refs in either commit, with unchanged, upstream-edited, and direct-value-edited cases (`:596–624`). An independent in-memory check of both commit directions passed. The regenerated JSON/Markdown reports retain **7 potential, 4 abstentions, 0 incomplete upstream pairs** for the pinned trees and describe this policy. This fixes the identified gap; a qualifier does not turn source-path evidence into observed row impact.

### Medium — Source-text similarities can over-credit distinct scopes

`mql_to_sal_rate@window` versus `sal_to_sql_rate@window` scores **0.657143** because the same relation, `conversion_rate` text, segment projection, and grain outweigh their different `stage` filters. The compiled trace separately records `stage` as the branch filter and different underlying conversion counts; the union traversal still has review stops. `mql_volume@month` versus `mql_volume@window` scores **0.714286**, including syntactic credit for two absent local WHERE clauses, although their period expressions and grouping sets differ. These are useful candidate clues and plausible false positives for equivalence. Keep stage predicates, aggregation grain, time scope, and row-group semantics explicit in any method definition; do not turn a score into a relationship label. See `rank_source_aware_candidates.py:96–156`, `source_aware_candidates_report.json` (`pairs`), and compiled branches 1–2 and 9–11.

No scoring-path label or outcome leakage was found: `generate()` enumerates the pinned source inventory, calls name-only `scores()` on the two branch names and `source_score()` on source fields, and creates the selected diagnostic after scoring. The imported baseline `scores()` uses names alone. The chosen features and weights remain development-informed design choices, so this check does not substitute for a frozen method or held-out judgments.

### Medium — Compiled field traces are partial provenance, not row equivalence

The compiled reporter aligns 11/11 source and compiled branch identities, identifies nine scalar value field uses and 15 branch WHERE field uses, and leaves **all 11 branches `needs_review`**. The corrected `win_rate@window` row includes `is_won` from `count(*) FILTER (WHERE is_won)` as a value input, alongside `count(*)` row-set dependence; its branch WHERE inputs are `is_closed`, `opp_amount`, `created_date`, and `close_date`. This is supported by the compiled SQL, JSON, Markdown table, and parser self-check (`trace_compiled_metric_fields.py:115–144, 524–545, 667–671, 723–729`).

Two `mql_volume` values use `count(*)` without scalar field inputs; tracing named fields does not establish which rows are counted. The JSON records 16 `union_field_without_discriminator` stops across traversals, while grouping sets, joins, macros, and upstream row predicates require review. A CSV-header terminal verifies a field name's presence, not value correctness or row provenance. The compiled artifact identifies one local build and its dependencies; it is neither a native semantic-engine test nor an independent relationship label.

### Low — Compiled coverage denominator wording (fixed)

**Initial finding:** The earlier Markdown put “38 seed-header endpoints” next to “21 of those field paths,” suggesting a 21/38 denominator. The script had actually computed **21 reviewed root paths out of 24 value/branch-WHERE field uses** (9 + 15), separately from 38 seed-header terminal occurrences.

**Repair verified:** The generator now renders these as separate sentences (`trace_compiled_metric_fields.py:610–613`), and `compiled_metric_fields_report.md:7` says “Of 24 root value/branch-WHERE field-use paths, 21 carry a review marker. Separately, 38 seed-header terminal occurrences were reached along those paths.” The JSON counts remain 24, 21, and 38. This corrects the wording, not the bounded tracing coverage.

## Cross-agent evidence and status synthesis

| Common evidence | Independent check | Interpretation |
| --- | --- | --- |
| Branch universe | The source extractor, compiled branches, candidate universe, both version snapshots, and 11 explicit version links have the same 11 `metric_name@grain` IDs. Candidate JSON has 55 pairs and ten candidates per query under each of five methods. | Same development units; complete enumeration is not judged retrieval performance. |
| Pinned artifacts | The metric SQL SHA-256 is `62bac0c8…45536ead7f5` at all three cited commits; the adjacent Git trees have no diff for that file. Manifest SHA-256 is `16c739b2…646fe95`; its metric `compiled_code` equals the compiled file, SHA-256 `9af5d9c5…5c676deb39`, byte for byte. | Strong local source/compiled identity at `a71232c…`; no runtime or cross-revision equivalence follows. |
| `pipeline_created@month/window` | Name-only exact 1.0 and source-aware 0.571429; compiled `opp_amount`, `is_net_new_pipeline`, `created_month` fields; both version assessments abstain after only trivia edits on their resolved model paths. | The candidate relationship abstains; compiled review and version abstention address different questions. |
| `mql_volume@month/window` and funnel rates | The former are row counts with different grains and score 0.714286 against each other. The three stage rates share a relation and projection but have different stage filters. These five IDs are among the seven version `potential_metric_change` paths through `int_leads__unified`; all 11 pinned links have `supported_upstream_refs_resolved`. | The common path flags possible dependency exposure, not five observed value changes or five equivalent pairs. |
| `win_rate@window` | `is_won` is traced from the FILTER clause; the four branch WHERE inputs are recorded. Version comparison abstains; compiled review remains. | The corrected field table addresses FILTER syntax while leaving aggregation and row semantics open. |

Status vocabulary must remain scoped: candidate `abstain` is a **relationship decision**; compiled `needs_review` is a **field/row-provenance limitation**; version `potential_metric_change` or `abstention`, with its resolved/incomplete upstream qualifier, is a **source-path assessment**. None contradicts the others. The source-aware ranking reads the uncompiled branch inventory, so its `field_lineage_not_traced` flag remains accurate for its own input even though the separate compiled probe traces selected field names. The three outputs should not be presented as one end-to-end evaluated matcher.

## Remaining work before manuscript integration

1. Limit claims to the observed development diagnostic. Do not report accuracy, Recall@k, semantic equivalence, seven runtime changes, prior-art novelty, or maintainer benefit from these artifacts. A defensible statement is: *On one pinned GTM development model, three bounded probes enumerated 11 branch IDs, generated complete source-text rankings, traced selected compiled field inputs with review stops, and identified seven branch IDs with a potential path to one changed upstream SQL token.*
2. Specify how stage filters, time scope, grain, grouping sets, joins, and uncertain lineage affect source-aware ranking and abstention. Freeze the resulting method and context-fair baselines on development projects before any held-out evaluation; the present equal weights are uncalibrated.
3. Preserve the corrected `win_rate` FILTER field and separate 21/24 versus 38-occurrence denominators in manuscript tables. Mark `count(*)`, stars/unions, seed-header terminals, grouping sets, macros, and join cardinality as reviewable limits. Keep the local `a71232c…` compilation separate from the adjacent-commit source comparison.

## Next research gate

Freeze a source-aware method and context-fair baselines on development projects. Then create a **dated search-result manifest**, obtain **independent human judgments on complete anchor candidate universes**, and evaluate on a genuinely held-out set selected before inspection. An industrial benefit claim additionally requires approved private sampling and measured maintainer decisions. No new repository inspected for this review becomes held-out retrospectively.

## Verification performed

The initial review read all three scripts and JSON/Markdown reports, the integration contract, source branch inventory, pinned Git objects, manifest, compiled metric SQL, and relevant upstream SQL. All three initial read-only `--check` commands passed. Independent assertions checked the common 11 IDs, 55 pairs, complete candidate lists, statuses, `win_rate` FILTER and WHERE fields, artifact hashes, and seed counts. For this repair review, both affected scripts' read-only `--check` commands passed against their final reports. Additional in-memory assertions verified the Markdown's 21/24 and separate 38 counts; unresolved input in either commit now qualifies both no-edit and detected-edit assessments; pinned counts remain 7/4/0. Only this review file was updated.
