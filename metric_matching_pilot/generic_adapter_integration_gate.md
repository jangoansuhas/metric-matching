# Generic adapter integration gate (development only)

Date: 2026-09-28 UTC. This maps the next SQL inventory implementation to the prospective `evaluation_contract.md`. It is a staged engineering gate, not an evaluation result. The only SQL inspected for this gate is the existing synthetic development fixture `sql/metric_views.sql`. The previously frozen held-out search manifest records repository **metadata**; it does not authorize opening repository source until the generic adapter and comparison packet are fixed.

## Source packet required for a fair comparison

One immutable `I1` packet must contain, for every in-scope scalar definition (including extraction failures), a stable ID, project/version SHA, path and line span, input byte digest, parser dialect/version, raw or compiled evidence type, expression AST or explicit parse failure, output field, source relations and field references, aggregate operators, filters, grouping keys, time predicates, and each missing/unsupported field with a reason. Compiled SQL may be recorded only with a real build artifact path/hash and a verified source-to-compiled mapping. Native grain, join cardinality, absent-row and NULL behavior, unit, snapshot alignment, and business meaning are **unknown** unless independently evidenced. A SQL AST does not determine them by itself.

The same packet must enumerate every unordered within-project pair once and carry no human labels, previous author decisions, reconciliation outcomes, or answer-bearing controls into any method input. Store its exact hash and the complete pair-ID list. `I0` name-only methods may use a deliberate subset of this packet, labeled as a different access tier. The full-context AST, normalized-SQL/lineage, constraint-aware, proposed method, and optional LLM must receive the same `I1` fields, fixed pairs, check budget and versioned configuration. A classifier's fixed-pair output is distinct from a retriever's ranking over the full universe.

## Current and required evidence

| Capability | Existing development evidence | Gate still required before held-out source |
| --- | --- | --- |
| Search frame | Three dated metadata-only pages and 62 distinct pinned HEADs, checked by `verify_heldout_search_frame.py` | Preserve this complete manifest and apply eligibility/hash selection only after adapter freeze; record all exclusions. |
| Portable source inventory | Pinned Jaffle YAML inventory and raw-SQL links; GTM packet and a synthetic SQL fixture | Verify the generic extractor on development SQL, including unsupported cases and all pair IDs; publish code/config/digests. |
| Compiled provenance | GTM-specific trace only; zero compiled sources verified in the portable Jaffle report | Build or obtain an actual development dbt compiled artifact, verify its source mapping and hash, and have the generic adapter consume it without hard-coded project names. If unavailable, narrow the study to source-only coverage and do not call it a compiled-source adapter. |
| Semantic safety | Explicit abstentions and source-level controls | Preserve aggregate operator, filters, grouping, `NULL`/`COALESCE`, joins, date windows, and unknown fanout. A parse success cannot by itself support equivalence. |
| Fair baselines | GTM AST and constraint baselines used the same 55 development pairs and produced identical decisions | Run all full-context methods on the **same new packet and pair universe**; verify ID/hash equality, source access, and coverage. Record name-only methods separately. |
| Evaluation | Author and AI development reviews only | Two independent qualified human judgments plus adjudication for any gold claim; complete anchor target universes for exact Recall@k. |

## Lock sequence

1. Finish and independently review the generic development-only SQL inventory. Keep parse failures and unsupported constructs in the denominator. The synthetic fixture establishes parser boundaries, not external validity.
2. Add real development compiled provenance or explicitly revise the planned claim to source-only analysis. Do not infer compiled semantics from raw SQL paths.
3. Freeze the adapter, `I1` packet schema, pair enumeration, method versions, thresholds/prompts, compute budget and complete dated manifest. Record hashes in an append-only development revision; retain earlier freezes.
4. Only then apply the precommitted metadata eligibility and hashed selection. Open only selected pinned repositories and log every code-screen failure. Do not choose projects based on positive matches or parser success.
5. Blind two human annotators to method outputs. Adjudicate scope-specific labels and conditional prerequisites before estimating decision safety, recall or maintenance benefit. If complete target universes are unaffordable, report judged-pool retrieval and coverage instead of exact Recall@k.

Any development adapter report should say which steps it actually satisfies. Passing the synthetic inventory alone leaves steps 2 and 3 open and leaves the held-out source gate closed.

## Independent phase-1 finding (2026-09-28 UTC)

`generic_sql_inventory.py` and its report now give a reproducible source-only inventory for 12 synthetic `CREATE VIEW` statements: 24 emitted projections and 276 pairs. Six projections have recognized aggregate operators and four are supported by the deliberately narrow parser. The separate negative fixture distinguishes `SUM` from `MEDIAN`, identical `COUNT(*)` syntax over different tables, and `SUM(x)` from `SUM(COALESCE(x, 0))`. These are syntactic differences; the NULL policy remains unknown. The independent review in `generic_adapter_review_contract.md` checked the final code hash and passed the narrow inventory boundary.

The review also exposed two gates that the current report does **not** satisfy. First, the 24 projections include entity keys; an eligible numeric-metric universe has not been generically established. Second, an unparseable projection gets a placeholder but its true arity is unknown. A regex fallback could invent a type name as an alias inside a templated `CAST`; this unsafe fallback was removed and the reports regenerated. The complete-pair count applies only to emitted IDs. These limitations must be resolved or charged to coverage before any held-out candidate denominator is asserted. The report has no compiled provenance and is not a full `I1` comparison packet. The held-out source gate remains closed.

The next diagnostic (`generic_same_input_baselines.py`) uses a 12-output, 66-pair **fixture-only** `.value` subset of that inventory. Its two syntax-context methods share one packet digest and abstain on all semantic decisions. This is a reproducible common-input harness, but it does not repair the eligibility/parser limits above or compare a runnable proposed method and a context-matched LLM. Treat its one same-source and five different-source syntax signals as review observations, not gold-confirmed relationship predictions.
