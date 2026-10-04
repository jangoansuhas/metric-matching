# Prospective public evaluation sampling protocol (development draft)

Written September 27, 2026 **before any further public test repositories or metric pairs are selected**. This is an internal, versioned plan, not an externally registered study. Earlier inspected Jaffle, Sidemantic, GTM, and Rill projects, their forks, shared seeds, and related commit families are development material and are excluded from the held-out evaluation. Any later protocol change must be dated with a reason before opening the affected sample.

## Unit and project selection

- The unit is either (a) a pair of declared metric *scalar outputs* with explicit row grain, time, population, and transformation scope, or (b) one metric definition in two adjacent repository versions with source-linked downstream dependencies. A field alias is not automatically an equivalent whole row; a change event is evaluated separately from a pair relationship.
- Before opening any held-out code, save a sampling-frame manifest with the exact GitHub search query strings, search date, complete result order/pages used, eligibility decisions, and pinned commit IDs. The proposed query families are repository results for `dbt metric`, `dbt semantic model`, and `rill metrics`, restricted to publicly readable Git projects. This family and eligibility rule were fixed here, but the actual result snapshot and repository list **have not yet been frozen**. Admit a project only if it has accessible versioned SQL/dbt models, declared measures/metrics or reproducible aggregate queries, and enough public source or local data to inspect compared definitions. Do not require a positive match to admit it. Record rejected repositories and reasons.
- From eligible repositories, select four unrelated projects by lexicographic SHA-256 of `owner/repo@commit` as recorded in the frozen manifest. Record every candidate and exclusion. If fewer than four qualify, report the smaller sample and avoid broad generalization. Do not change the sample because it has few positive cases.
- For each project, enumerate definitions and parent-to-child changes over the 12 months preceding its pinned commit (limit to the 100 most recent commits in that window) **before inspecting labels**. Sample up to 25 candidate pairs and 10 definition changes per project by fixed hash order from (i) lexical top candidates, (ii) shared lineage/source candidates, and (iii) randomly selected distinct definition pairs. Deduplicate, preserve sampling stratum and inclusion probability where known, and include unchanged as well as changed commit events. Do not enrich the test set by cherry-picking appealing examples after outcomes are known; collect discovered rare positives in a separately marked case-study supplement.

## Annotation and adjudication

- Give two human annotators the same pinned source snapshot and documented evidence fields while concealing each other's labels and all system predictions. Record exactly which scalar, group, and period each decision concerns; source-line locations; transformation and preconditions (join cardinality, absent rows/NULL, filters, units, population, snapshot); label; confidence; and decisive missing evidence.
- Use relationship labels `direct_equivalent`, `cross_grain_equivalent` **under a stated transformation**, `temporal_or_scope_variant`, `related`, `conflicting_definition`, or `non_match`. Store `needs_review` as an *evidence status* with missing-field reason, not as a seventh kind of business relationship. For version changes separately record `behavior_preserving`, `behavior_changing`, or `needs_review`, with the affected input domain and observed-row evidence if present.
- Label `temporal_or_scope_variant` when an identified conceptual measure changes its time rule, state, population, or filter; label `related` when measures share a domain or lineage but cannot be substituted and no single specified variant relationship is supported. A cross-grain label requires a verified mapping and explicit treatment of zero-item/missing groups. Adjudicate disagreements through a third domain-aware human reviewer with the evidence, preserving both originals and reasons. If human labels cannot be obtained, call the set a source-audited development sample, not gold.

## Evaluation design and stopping rules

- Freeze project split before threshold tuning; all related commit families and dataset derivatives stay in one split. Exclude the four inspected projects from held-out metrics and model development. Publish class counts and unsupported counts even if they are too small for per-class estimates. Report uncertainty by project; a few dozen pairs do not establish stable performance over six relationship classes.
- Separate candidate generation (Recall@k and retrieval cost), classification on a fixed candidate set (per-class errors, especially false equivalence), and end-to-end decisions (precision/recall when defensible, coverage/abstention, review effort, runtime and cost). **Recall@k requires a completely judged candidate universe for each evaluated anchor metric** (or a clearly stated judged-pool estimate); 25 sampled pairs per project cannot establish recall over all possible matches. Analyze unconditional labels separately from conditionally reconciled pairs. A finite reconciliation is supporting evidence, not a universal proof.
- Compare exact/name/token/Soundex/Jaro-Winkler/Jaccard retrieval where appropriate, normalized SQL and lineage, a constraint-based implementation, and a context-matched LLM if access and budget allow. Show each method's inputs. Full-context and name-only runs answer different questions and must be reported separately; tune prompts and thresholds on development projects only.
- Do not turn an absence of positives into an artificial positive-only benchmark. If source-verified natural positive pairs or industrial decisions are too scarce, report a scoped failure-mode study with transparent negatives/uncertainty instead of an accuracy or superiority claim. Stop the selection at the predefined project and pair budgets and disclose unavailable projects, failed builds, and changes to this plan.

## Next executable slice

Implement one automated pipeline on a *development* commit pair: read two versioned source trees, extract a documented SQL/dbt subset, link candidate definitions without hand-supplied pair IDs, produce a source-linked change explanation and affected model dependencies, and emit explicit `needs_review` for unsupported SQL or missing join/time evidence. Run the frozen selection protocol only after that pipeline and its baselines are fixed. An industrial evaluation is a separate permissioned activity and needs actual owner decisions; no company code or Snowflake setup is required for the public slice.

## September 29, 2026 status addendum (no selection yet)

The September 27 statement that the search snapshot had not yet been frozen
was true when written. A subsequent dated, metadata-only capture now contains
65 ranked result occurrences and 62 pinned distinct repositories; the
read-only `verify_heldout_search_frame.py` check passed on September 29 for
`heldout_search_capture/attempt-20260928T020324Z-1c3dd1fe`. This is a search
frame, not an eligible-project table or a selection of four projects. No new
held-out repository source was inspected for this addendum. The public-only
Industrial study still requires a dated eligibility/sampling decision record,
reviewer budget, same-input comparator configuration, and source/evidence
acceptance rules before opening any new held-out source. The prospective
adjacent-commit task is outside the primary within-revision relationship
study unless separately staffed and evaluated.
