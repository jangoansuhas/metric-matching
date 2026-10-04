# Independent review: same-input baseline diagnostic

The v1 review below is retained as a historical record. The current review is **v2, dated 2026-09-28 UTC**, at the end of this file. Its hashes supersede the v1 hashes.

Date: 2026-09-28 UTC. Scope: existing synthetic development fixture and the final observed baseline bytes only. This is an engineering review, not human gold or an empirical effectiveness result. No new held-out repository source was inspected, and no worker file was edited.

## Reviewed artifacts

| Artifact | SHA-256 |
| --- | --- |
| `generic_same_input_baselines.py` | `2cdb811473c683070e1a6d578029f8e852113e23ea773169eb8111d65b1e1017` |
| `generic_same_input_baselines_report.json` | `fdba2be0dbfd524764e5137eb2cf316c93311406b769322abfd61bb35d1ad91e` |
| `generic_sql_inventory_report.json` | `ba30b7e95083d3a4db542a1a86d6fc40cf4c56cbc0c57afcff756795d03b2438` |

## Result

**Narrow development diagnostic: PASS. Broader generic compiled-provenance, complete-universe and fair comparative-evaluation gate: PENDING.**

| Check | Independent finding |
| --- | --- |
| Read-only regeneration | `python -B metric_matching_pilot/generic_same_input_baselines.py --check` exited 0 and reported that the frozen input and both reports agree. The JSON and Markdown report modification times and sizes were identical before and after this command. |
| Pair universe | The raw SQL inventory has 24 emitted outputs and 276 unordered pairs. The harness explicitly selects the 12 `.value` outputs in this *development fixture* and emits all 66 unordered pair IDs in sorted order. Every emitted eligible pair exists in the raw inventory. This is a complete universe of the selected emitted IDs only. |
| Same input | Both I1 method records declare the identical inventory digest `ba30b7e95083d3a4db542a1a86d6fc40cf4c56cbc0c57afcff756795d03b2438`, eligible pair-set digest `4eff0ecb816a0268adef5e285531362b3f6787c86865bdc7765753127a9100fb`, and canonical packet digest `6e575c9fd3b8d3021eb6a3adaff1a677a91ad0c8fc47107a41879e5d2219bff9`. I independently recomputed the pair and packet hashes from the raw inventory and matched both reported hashes. All six methods carry the same pair-set hash, and each has one row for every eligible pair. |
| Label separation | The script reads the one frozen inventory JSON and whitelists fields for its I1 packet. Its score and syntax paths do not read human labels, author decisions, reconciliation outcomes, or adjudicated prerequisites. No such top-level inventory fields were present. This check does not establish that future inputs are automatically safe; a future packet needs an explicit recursive label audit. |
| Semantic caution | The AST/source and constraint-aware paths have identical syntax-signal counts: one `same_source_signature`, five `source_difference`, and 60 `abstain`. Their semantic decision is `abstain` on all 66 pairs. Different syntax is not called a semantic contradiction, and matching syntax is not called equivalence. Unknown grain, time, NULL policy, join cardinality and snapshot semantics remain unknown. |
| I0 name methods | Raw exact, normalized exact, Jaro-Winkler and token Jaccard score all 66 eligible pairs from view/metric names rather than output IDs. The raw-exact and normalized-exact references score zero positive pairs because this fixture's view names are unique; Jaro-Winkler has nonzero scores on 66 pairs and token Jaccard on 22. These scores are uncalibrated retrieval diagnostics, not decisions. |

## Remaining defects and limits

1. **Eligibility is fixture-specific.** The `.value` alias rule is hard-coded for the development fixture. The raw 24/276 count includes 12 `entity_key` projections, while an aliasless parse failure can have unknown projection arity and regex alias recovery can invent IDs. Neither the 12/66 nor 24/276 set proves a complete metric universe on a new repository.
2. **The two I1 paths are not evidence of incremental utility.** Both call the same `source_signal` logic; the constraint-aware path adds only a missing-semantics list and still abstains universally. There is no measured advantage, and no candidate ranking, Recall@k, F1 or review-effort result.
3. **Compiled provenance remains absent.** The input is source-only synthetic `CREATE VIEW` SQL. There is no compiled dbt artifact hash, verified source-to-compiled mapping, pinned real project commit, or generic compiled-source adapter. The held-out source gate remains closed.
4. **The full fair comparison remains pending.** The prospective comparison still needs a fixed generic eligible-definition rule, a label-free I1 packet with provenance, identical budgets and pair IDs for normalized SQL/lineage, AST, constraint-aware and proposed paths, plus a context-fair LLM if included. Independent human annotation and adjudication are required before empirical match-quality claims. Exact candidate Recall@k requires a complete target universe.

These findings apply only to the hashes above. Any later code or input revision requires a fresh review.

## V2 independent review — 2026-09-28 UTC

The SQL inventory was regenerated after unsafe alias guessing on unparseable SQL was removed. I reviewed the current baseline code and both current baseline reports, inspected the inventory extractor's failure path, ran read-only regeneration checks, and independently recalculated the pair and packet digests. No worker code or held-out repository source was edited or inspected.

| Current artifact | SHA-256 |
| --- | --- |
| `generic_sql_inventory.py` | `1d01bf9d79cbe15ed27f5d8d8d0e43cde5f9c04df9ae906f23a223ae010af45c` |
| `generic_sql_inventory_report.json` | `fdb68bd980cb425e39140056b3360952d3ccb77b1545523a07e47fad256abfc7` |
| `generic_sql_inventory_report.md` | `a1ee5a752f0efd8b9d29259d70b8b3a7c3d10514d3d8927b6b56a0265a465077` |
| `generic_same_input_baselines.py` | `9851bf85f2e3a187329a2f771946b9c21b336b769bfde6df7b16b2ff7eb2ea2f` |
| `generic_same_input_baselines_report.json` | `d7c510a2f567372055d2b9952fd90315fd0ebaf9cc616af2416115feb3bddf3b` |
| `generic_same_input_baselines_report.md` | `9d32967a1d78ecd77dc00f5561ae73aad894fbc1512d86e7c7faf7d09502d212` |

**Narrow v2 result: PASS.** `python -B metric_matching_pilot/generic_sql_inventory.py --check` and `python -B metric_matching_pilot/generic_same_input_baselines.py --check` both exited 0. Report modification times and sizes were unchanged across the checks. The baseline code pins the current inventory SHA-256 above; the JSON report repeats it.

| V2 check | Independent result |
| --- | --- |
| Main fixture frame | The raw inventory still emits 12 views, 24 output IDs and the exact 276 unordered pairs of those IDs. The fixture-specific `output_alias == value` rule still selects 12 IDs, one per view. Baseline rows equal all 66 expected unordered eligible pairs in sorted order; every pair exists in the raw inventory. |
| Same-input digests | Independently recomputed the canonical eligible pair-set SHA-256 as `4eff0ecb816a0268adef5e285531362b3f6787c86865bdc7765753127a9100fb` and the whitelisted I1 packet SHA-256 as `6e575c9fd3b8d3021eb6a3adaff1a677a91ad0c8fc47107a41879e5d2219bff9`. Both match the report. All six method records carry the same raw inventory and pair-set digests; both I1 methods carry the same packet digest. The eligible packet and pair digests stayed constant across v1/v2 even though the full inventory bytes changed. |
| Signals and abstentions | Both I1 paths yield one `same_source_signature`, five `source_difference` and 60 unsupported `abstain` signals; both abstain on all 66 semantic decisions. Neither claims equivalence or contradiction. I0 nonzero scores remain raw exact 0, normalized exact 0, Jaro-Winkler 66, token Jaccard 22; these are uncalibrated name scores. |
| Unparseable aliases | The extractor now emits one `_unresolved_output_1` placeholder for an unparseable view instead of recovering aliases from its text. The separate negative fixture has 8 views, 12 emitted outputs, 66 pairs and two unresolved placeholders. A regular expression remains for locating aliases **after a successful parse**; it is not the removed unparseable-SQL alias recovery. True projection arity of a failed parse remains unknown. |
| Label boundary | The baseline reads the frozen inventory and derives I1 evidence from a field whitelist. I found no gold, label, outcome or adjudication keys at the inventory top level and no outcome source in the baseline decision path. This is a code/input audit, not independent human annotation or a general guarantee for future packets. |

**Broader gate: PENDING.** The 12/66 frame is valid only for the selected emitted outputs in this synthetic development fixture. The alias eligibility rule is not generic, unparseable projection counts remain unknown, and there is no verified compiled artifact or source-to-compiled mapping. The two I1 paths share syntax logic and abstain universally, so this run gives no evidence of method superiority, Recall@k, F1, or maintenance benefit. A fixed generic adapter and same-context baselines, followed by independent human annotation, are still required before held-out source access and empirical claims.
