# Public metric matching pilot

This is a small, synthetic feasibility fixture for the SANER 2027 paper draft. It uses Python 3's standard library and SQLite for its initial checks. Rows and amounts are constructed, with no raw company records or company code. Some motivating names or rules originated in private discussions: **this working archive is not cleared for public release**. The current manuscript plan is public-only; use independently public definitions and review this fixture's provenance before sharing it externally. No Snowflake account is required for the initial checks. See `public_only_venue_and_data_plan_20260928.md` for the active scope decision.

## Current public study gate (29 September 2026)

The dated `public_source_screen_amendment_20260929.md` permitted outcome-blind source eligibility and adapter-coverage screening before reviewer staffing. The manifest/queue audit, source-screen reports for ranks 1 and 2, and `source_screen_selection_ledger_20260929.json` (SHA-256 `6a1e16cc3ecd8affebea701534cce5119e13d89a5c3e866d6c60987fbec67fc5`) record the first two selected pinned projects under the **original broad SQL-output rule**; 60 queue entries were not opened. A later source-only audit in `semantic_declaration_count_audit_20260929.md` confirms zero declared MetricFlow metrics in either project and provisionally identifies 17 and 3 SQL aggregate outputs under its explicit rule. Those output counts are not a frozen compiled inventory or pair labels. The unchanged MetricFlow adapter parsed rank 1 with no declared targets; on rank 2 it exited before parse on a nested dbt project. No pair comparison, value execution, relationship result, human gold, or accuracy follows.

The disclosed `semantic_metric_cohort_reset_20260929.md` **pauses the SQL/catalog bridge for this paper**. `semantic_metric_frame_precommit_20260929.json` fixed a separate, bounded public Semantic Layer metadata frame before source inspection. The returned source screen records three selected projects at hash ranks 7, 9 and 14, with a total of 20 source-screen-listed metrics. Frozen adapter v1 stopped before parsing the nested projects; a separately versioned external v2 then generated ungrouped SQL for their 5 and 10 metrics, and the earlier root-project run supplied another 5. These are 20 SQL-generation outputs, with no metric-value execution or labels. `semantic_metric_frame_after_screen_20260929.md` verifies the archived metadata and combined technical evidence, records missing source bytes, and reconciles a separately generated post-screen list of all 65 compiler-visible pairs with the earlier, still-gated eight-slot primary sampling rule. The guarded adapter code in this packet is a synthetic-tested candidate, **not** the external v2 used in the empirical coverage runs. The earlier handoff and SQL inventory bridge are historical tasks, not active selection rules. Both frames and their post-screen chronology must be disclosed; the AI reviews are technical critiques, not human reference judgments.

## Run

From this directory:

```sh
python3 pilot.py --check
```

This creates `report.json` and `report.md` and checks the seven hand-labeled scenarios against the rule output. The script exits nonzero if a scenario fails. Python 3.9 or later is sufficient.

Then run:

```sh
python3 extract_signatures.py --check
```

This creates `extracted_signatures.json` from the view SQL itself. The extractor supports only the simple `SELECT` shape in these fixtures: one key projection, one measure projection, one source table, at most one explicit join, conjunction-only filters, and an optional simple `GROUP BY`. It extracts source columns, aggregation, keys, a fixed snapshot date when written in `WHERE`, and join text. It leaves unit, business state, and join cardinality unresolved and returns `needs_review` for unsupported expressions. The extracted signatures are **not yet used** by `pilot.py` to classify pairs.

### Repeat the pinned public corpus test

The optional public test uses `git` and PyYAML (run here with PyYAML 6.0.3). From the directory containing the extracted `metric_matching_pilot` folder:

```sh
git clone https://github.com/dbt-labs/jaffle-shop.git
git -C jaffle-shop checkout 5beb145b00f5465ec759cfcdd9745e858818cf95
python3 metric_matching_pilot/run_public_corpus.py --repo jaffle-shop --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --check
python3 metric_matching_pilot/trace_dbt_lineage.py --repo jaffle-shop --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --check
python3 metric_matching_pilot/build_public_pair_review.py --repo jaffle-shop --check
```

This writes `public_corpus_report.json` and `public_corpus_report.md` inside `metric_matching_pilot`. The pinned source repository is not included in the ZIP. The initial SQL grammar covers 0 of 13 dbt SQL model files because they are model SQL, not `CREATE VIEW` statements. A separate limited YAML pass records 7 partial signatures and 16 `needs_review` results from 23 native metric definitions. It does not compile dbt, execute rows, validate column-level lineage, classify pairs, or measure matching accuracy.

The second command writes `public_lineage_report.json` and `public_lineage_report.md`. It follows **three selected candidate paths** through this revision's source SELECTs, CTEs, refs, and joins. It records the order total's source order field, the item revenue's source product price, and the first-order filter's window expression. The tracer recognizes only a documented subset and abstains on ambiguous stars or unknown expressions. It does not compile adapter-dispatched macros, resolve MetricFlow dimensions by running dbt, prove join cardinality, or apply across all model files; no relationship labels or coverage rate are claimed for this separate probe.

The last command checks ten **first-analyst pair proposals** in `public_pair_proposals.json` against the pinned repository and generates `public_pair_blind_review.md` for an independent second reviewer. Open that blind sheet before the proposals if you intend to review independently. `public_pair_proposals.md` is a readable summary of the first analyst's labels. A user-submitted second label set has since been normalized in `public_second_review.json`; whether its analysis was independent is unverified. There are no adjudicated ground-truth labels or confirmed direct/cross-grain equivalents in this small naturally occurring selection. The ten selected pairs cannot serve as a held-out accuracy benchmark or an estimate of label prevalence.

### Reconcile source rows and compare reviews

Using the same pinned checkout, from the directory containing `metric_matching_pilot`:

```sh
python3 metric_matching_pilot/reconcile_public_seeds.py --repo jaffle-shop --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --check
python3 metric_matching_pilot/compare_public_pair_reviews.py --check
python3 metric_matching_pilot/audit_agreed_public_pairs.py --repo jaffle-shop --check
```

The first command checks the raw CSV seeds against the visible model-level relationships, including tax on `order_total` versus pretax item `revenue`, and the difference between `ordered_at` and `first_ordered_at` for time-indexed totals. It writes `public_seed_reconciliation.json` and `.md`. The second compares the first proposals with the submitted labels stored in `public_second_review.json` and writes `public_pair_review_comparison.json` and `.md`. To normalize the original submitted Markdown again, add `--review-file /path/to/submitted-review.md`; that original file is not included in the ZIP. `public_pair_author_decisions.json` records the author's acceptance of the recommended JS-001, JS-005, JS-007, and JS-010 labels on September 27, 2026. The third command audits the six initially agreed labels against exact pinned YAML/SQL source and writes `public_agreed_pair_audit.json` and `.md`. All four initial disagreements have author decisions, and six agreements have source support, but the set is **not gold-label ground truth**. These commands do not run dbt or MetricFlow and finite sample equality cannot prove semantic equivalence.

### Check an existing public cross-grain candidate

From the directory containing `metric_matching_pilot`, clone the separate demonstration repository and its pinned Jaffle Shop submodule:

```sh
git clone https://github.com/sidequery/jaffle-shop-sidemantic.git
git -C jaffle-shop-sidemantic checkout 8686fe3ea0fd4ceffa08e523a422331bd228ac32
git -C jaffle-shop-sidemantic submodule update --init
python3 metric_matching_pilot/verify_public_positive_candidate.py --repo jaffle-shop-sidemantic --check
```

`public_positive_candidate.{json,md}` records a **conditional** cross-grain candidate between `orders.subtotal` (MetricFlow measure, order grain) and `order_items.revenue` (Cube measure, item grain). Both definitions already exist in the public repository. The source check verifies pinned revisions and raw rows: among 61,948 orders, **483 have no items**, producing an absent/NULL item sum versus a zero order subtotal. A left join and `COALESCE(item_sum, 0)` remove all observed order-grain differences; all-time and aligned daily totals agree across 365 dates. Align Cube's explicit `ordered_at` time dimension with MetricFlow's default `ordered_at`. This curated demonstration shares the Jaffle Shop dataset with the earlier ten cases, so it is a **development candidate**, not independent held-out evidence or industrial validation. The source repos themselves are not bundled in the ZIP.

To reproduce the materialized dbt build and NULL-aware check, run these from the same parent directory after cloning (requires Python 3.11/3.12 and `uv`):

```sh
cp metric_matching_pilot/duckdb_profile_example.yml jaffle-shop-sidemantic/jaffle-shop/profiles.yml
cp metric_matching_pilot/public_positive_dbt_package_lock.yml jaffle-shop-sidemantic/jaffle-shop/package-lock.yml
(cd jaffle-shop-sidemantic && uv run setup.py)
uv run --with duckdb --with pyyaml python metric_matching_pilot/check_built_positive_candidate.py --repo jaffle-shop-sidemantic --check
```

The pinned build reported `PASS=49 WARN=0 ERROR=0 NO-OP=3 TOTAL=52`. Its declared `order_items_subtotal = subtotal` test passed with zero failures, **despite 483 NULL-versus-zero order discrepancies** in materialized tables: the compiled `WHERE NOT(order_items_subtotal = subtotal)` predicate filters them out. The companion `public_positive_built_check.{json,md}` records these results. The build alone does not execute a semantic-layer measure or establish a gold label.

Execute both imported semantic definitions through the public project's unified Sidemantic engine against the same dbt-built database:

```sh
uv run --with 'sidemantic[lookml,malloy]==0.8.2' --with polars --with pyarrow python metric_matching_pilot/check_semantic_positive_candidate.py --repo jaffle-shop-sidemantic --check
```

The two measures agree on all **365** aligned `ordered_at` dates and sum to **$637,444.00** each; see `public_positive_semantic_check.{json,md}` for the generated SQL and comparison. The repository demonstrates the 0.8.2 importer. An attempted run with 0.12.0 could not parse its OSI product model. Sidemantic translates MetricFlow and Cube YAML into **one** engine; this does not execute the two native runtimes and does not remove the 483 order-grain NULL differences.

### Audit unrelated positive controls and a real metric change

From the directory containing `metric_matching_pilot`, check out the unrelated GTM example and a sparse copy of Rill's example repository at their recorded revisions:

```sh
git clone https://github.com/jross21/gtm-funnel-analytics.git
git -C gtm-funnel-analytics checkout a71232c123a5fb78da9b52d4246950ee48591c00
git clone --filter=blob:none --no-checkout https://github.com/rilldata/rill-examples.git
git -C rill-examples sparse-checkout init --cone
git -C rill-examples sparse-checkout set rill-openrtb-prog-ads
git -C rill-examples checkout c35c312174431273726a1d6cfc030717babe5a88
```

Build the checked-in synthetic GTM seeds with the versions in its `requirements.txt`. The example profile removes a redundant ICU extension download; it leaves model SQL unchanged. Use one dbt thread and a fresh database so DuckDB's database can be reopened in this environment:

```sh
(cd gtm-funnel-analytics && uv run --with 'dbt-core==1.11.6' --with 'dbt-duckdb==1.10.1' --with 'duckdb==1.4.4' dbt deps --profiles-dir profiles)
(cd gtm-funnel-analytics && DBT_DUCKDB_PATH=arcline_singlethread.duckdb uv run --with 'dbt-core==1.11.6' --with 'dbt-duckdb==1.10.1' --with 'duckdb==1.4.4' dbt build --profiles-dir ../metric_matching_pilot/gtm_profile --target dev --threads 1 --quiet)
uv run --with 'duckdb==1.4.4' --with pyyaml python metric_matching_pilot/audit_unrelated_public.py --gtm-repo gtm-funnel-analytics --rill-repo rill-examples --check
```

`unrelated_public_audit.{json,md}` records four `pipeline_created` segment rollups with zero month-to-window differences, an exact downstream canonical alias, and a real Rill historical commit changing CTR and eCPM zero-denominator behavior. The GTM data and reconciliation are **synthetic and intentionally designed**; Rill's remote parquet was not queried. The constructed division values in the report illustrate SQL behavior and are not Rill source-data results. Neither repo is a held-out benchmark.

### Read the separate AI reviews and prospective sampling plan

`independent_review_protocol.md` describes five development cases given to a separate AI agent with no first labels or earlier audit documents. `first_labels_for_second_review.json` records the prior conclusions saved before its reply. `blind_second_agent_review.md` retains the source-only response, and `second_agent_comparison.md` explains why four prior conclusions are compatible **under specified conditions** and the fifth has no first label. This was not human annotation, gold ground truth, or a measured accuracy result. The agent recomputed raw-seed values; a separate read-only check confirmed its GTM total in the built model.

The same agent then inspected the manuscript and audits for `paper_readiness_review.md`. That second critique was **not blind** to the paper. It found five major gaps: industrial outcome evidence, automated end-to-end method, representative human-adjudicated labels, demonstrated novelty, and fair baseline evaluation. `heldout_sampling_protocol.md` fixes a prospective plan before inspecting further public test cases; it does not assert that the evaluation has been run. A narrow real two-commit source analysis now follows.

### Run the automated adjacent-commit source slice

With the pinned `rill-examples` checkout already cloned as above, from its parent directory run:

```sh
python3 metric_matching_pilot/analyze_versioned_metrics.py \
  --repo rill-examples \
  --before 3516d3d144979d23ceded2a1a72efcbddd452800 \
  --after 10a9bce8f0181623d8c596fbed7df37244666cc4 \
  --check
```

Requires Git and PyYAML (run here with PyYAML 6.0.3). The script reads **both Git revisions**, not checked-out working files, enumerates the Rill metrics-view YAML measures, and pairs them by stable `(view, measure)` IDs. It extracts expression and model/time declarations with source line numbers, recognizes only a literal addition of `NULLIF(sum(column), 0)` to a trailing denominator, links a declared model to known sources at **model level**, and finds exact measure references in dashboard YAML. On this historical development case it links **16/16 stable IDs** and reports **two** changed expressions, both with declared dashboard references. The report is `versioned_metrics_report.{json,md}`.

This adapter **does not** detect renamed/cross-view matches, parse arbitrary SQL/dbt definitions, resolve column lineage or join cardinality, check a Rill runtime or its remote parquet, or prove any observed customer impact. The two dashboard files establish declared *potential* consumers. A source-level behavior condition is not a benchmark result. The paper outline's Section 23 states which measurements are needed before writing a conclusion.

### Check a dbt SQL formatting-heavy commit

With the previously cloned GTM checkout as `gtm-funnel-analytics`, run from the same parent directory:

```sh
python3 metric_matching_pilot/analyze_dbt_sql_versions.py \
  --repo gtm-funnel-analytics \
  --before f387f822ab65f94bb2d04691ed0288ec3cdb17a2 \
  --after a4c122762b910a6a1c847e3d1a4999a5162db00a \
  --check
```

This standard-library-only script reads the two Git revisions' `models/**/*.sql`, links model files by path, and compares lexical SQL tokens after removing comments and whitespace outside strings/Jinja blocks. It finds simple `ref('model')` edges to model SQL or public seed files, then lists **potential** downstream model paths. In this development commit, 30 prior and 33 later model files yield **7 token-identical edits, 4 changed-token edits marked `needs_review`, and 3 new models**. The `fct_opportunities` formatting edit has declared dependency paths to both `fct_metric_values` and `rpt_metric_reconciliation`. The output is `dbt_version_report.{json,md}`.

The script does not compile dbt, resolve macros/column lineage, extract individual KPI branches from the `UNION ALL` metric table, prove equivalent results, or discover renamed metric pairs. A token-identical source stream is only a source observation; even a declared dependency is not evidence that metric values changed. The paper outline's Section 24 collects these interim case-study findings and limits.

### Check metric branches, name-only baselines, and evaluation rules

With the pinned GTM checkout at `a71232c123a5fb78da9b52d4246950ee48591c00`, run:

```sh
python3 metric_matching_pilot/extract_dbt_metric_branches.py --repo gtm-funnel-analytics --self-check
python3 metric_matching_pilot/run_development_baselines.py --check
```

The first script reads the pinned `fct_metric_values.sql` Git object and extracts 11 syntactic metric branches, including source line ranges, name/grain, period, value, filter, grouping, and CTE→`ref()` relation. `dbt_metric_branches_report.{json,md}` documents eight unexpanded `GROUPING SETS`, ten unexpanded Jinja branches, one dbt macro, and 11 missing field-lineage paths. Every branch has `needs_review`. An independent read-only check matched the 11 `(metric_name, grain)` IDs to the distinct IDs in the built GTM model. This checks this selected project's branch inventory, not semantic correctness or equivalence.

The second script reproduces `development_baselines_report.{json,md}` for exact-normalized names, token Jaccard, Jaro–Winkler, and Soundex. Its ten selected public Jaffle pairs are ranked in a 23-name inventory; seven constructed pairs are ranked in a separate 12-card inventory; one conditional pair has scores but no rank because its inventory is incomplete. The rankers see names only. These diagnostic selections are not a held-out, completely judged candidate universe. There are no accuracy or Recall@k estimates here.

`evaluation_contract.md` audits the prospective protocol and specifies how to freeze a complete search-result frame, annotate scoped scalar and conditional relationships, reserve fully judged anchor universes, and compare methods at matched inputs and reviewer budget. `annotation_schema.json` is a prospective record schema for two human judgments and finalization; its JSON and 47 local references were checked, but a full Draft 2020-12 validation has not yet run and no annotation records exist. The contract did not inspect new held-out project code. Keep the earlier protocol and record any changes before sampling.

### Trace compiled fields, rank candidates, and inspect a version edge

With the previously built pinned GTM checkout and its local `target/manifest.json` and `target/compiled` artifacts, run from the parent directory:

```sh
python3 metric_matching_pilot/trace_compiled_metric_fields.py --repo gtm-funnel-analytics --check
python3 metric_matching_pilot/rank_source_aware_candidates.py --check
python3 metric_matching_pilot/analyze_versioned_dbt_branches.py --repo gtm-funnel-analytics --check
```

`compiled_metric_fields_report.{json,md}` aligns 11 source and compiled branches, traces scalar and branch-filter field uses into immediate model declarations and some supported seed-header paths, and preserves review flags for ambiguous UNION lineage, grouping sets, macros, joins, and row cardinality. Artifact hashes document the local build; this does not prove metric equivalence. The generated compiled files and source repository are not bundled in the ZIP, so reproduce the pinned dbt build above for the first command.

`source_aware_candidates_report.{json,md}` scores every one of the 55 unordered pairs among those 11 branches. Four name-only methods and a fixed seven-feature syntactic source score rank the **same ten candidates per query**. All equivalence decisions abstain; without fully judged anchor universes, a rank is not a Recall@k or accuracy result. Equal weights and literal-text features are development heuristics, not a learned or validated matcher.

`versioned_dbt_branches_report.{json,md}` links 11 metric branches across the pinned adjacent GTM commits `f387f822ab65f94bb2d04691ed0288ec3cdb17a2` → `a4c122762b910a6a1c847e3d1a4999a5162db00a`. The metric SQL Git blob is identical; a nontrivia upstream alias edit on declared `ref()` paths triggers seven **potential source-review alerts**, while four branches abstain. These are model-path signals, not field-level impact, observed value changes, or a useful-alert rate. The earlier Rill changed-denominator event is a separate development case. `next_step_integration_contract.md` records how to interpret these three probes before evaluation.

### Compare conditional source decisions on the same public development pairs

To verify the saved reports against the **same local GTM compiled artifacts** and Jaffle checkout, run from this pilot's parent directory (substitute your checkout paths as needed):

```sh
python3 metric_matching_pilot/build_conditional_evidence.py --repo public_corpus/gtm-funnel-analytics --check
python3 metric_matching_pilot/normalized_sql_lineage_baseline.py --check
python3 metric_matching_pilot/constraint_aware_baseline.py --check
python3 metric_matching_pilot/conditional_decision_method.py --check
uv run --offline --with 'duckdb==1.4.4' --with 'pyyaml==6.0.3' python -B metric_matching_pilot/compare_conditional_development.py --check
```

These exact `--check` results use the pinned manifest/compiled SQL and built DuckDB database from the reported local GTM build; the public repositories and build artifacts are outside this ZIP. A **fresh** clone/build can produce different manifest bytes even if its metric SQL is unchanged. First regenerate `dbt_metric_branches_report`, `compiled_metric_fields_report`, the conditional packet, the three method reports and comparison without `--check`, using `--repo` for the new GTM checkout and `--database`/`--jaffle-repo` for the comparison. Then use `--check` against those newly generated files. Compare branch expressions and counts to the saved report; do not assume that a different build has the same packet hash.

For the fresh checkouts named in the earlier instructions, after building GTM and initializing the Jaffle submodule:

```sh
python3 metric_matching_pilot/extract_dbt_metric_branches.py --repo gtm-funnel-analytics
python3 metric_matching_pilot/trace_compiled_metric_fields.py --repo gtm-funnel-analytics
python3 metric_matching_pilot/build_conditional_evidence.py --repo gtm-funnel-analytics
python3 metric_matching_pilot/normalized_sql_lineage_baseline.py
python3 metric_matching_pilot/constraint_aware_baseline.py
python3 metric_matching_pilot/conditional_decision_method.py
uv run --with 'duckdb==1.4.4' --with 'pyyaml==6.0.3' python -B metric_matching_pilot/compare_conditional_development.py --database gtm-funnel-analytics/arcline_singlethread.duckdb --jaffle-repo jaffle-shop-sidemantic
```

`conditional_method_contract.md` fixes the same-input development protocol. The packet builder checks the pinned source and compiled model, then writes `conditional_evidence_packet.{json,md}` with 11 metric branches and all 55 unordered pairs. It has no selected labels or row reconciliation values. Each method reads the same packet bytes and reports one candidate decision or abstention per pair with explicit evidence status and unresolved prerequisites. The comparator verifies the packet hash and all pair IDs before making separate, read-only observations on the built GTM rows and pinned Jaffle raw rows. `conditional_development_comparison.{json,md}` records exact counts and examples; `conditional_method_review.md` records the independent AI integration review.

Both the constraint-aware comparator and the proposed method surface the same two month-to-window **conditional candidates**. The normalized SQL/lineage baseline identifies their scope difference without proposing the transform. This is a selected synthetic development corpus, and the candidate decisions are not human-adjudicated labels. The two full-context methods have no demonstrated effectiveness or novelty difference. The separate Jaffle zero-item example illustrates a NULL-versus-zero condition and is not scored among the 55 GTM pairs. An observed finite row reconciliation does not verify all future data, source lineage, grouping-set semantics, or deployment behavior.

### Freeze development rules and probe portability

`development_snapshot_freeze.json` hashes the three current same-input methods, their shared GTM packet/reports, the development comparison and evaluation contracts. The command below checks that snapshot without editing it:

```sh
python3 metric_matching_pilot/freeze_development_snapshot.py --check
```

The snapshot is **not a held-out preregistration**. The original input builder still requires the pinned GTM model and exactly 11 cards. On the already inspected pinned Jaffle Shop checkout, a separate source-YAML adapter inventories every native metric without fabricating compiled SQL, output grain, period grouping, filters, units or join behavior:

```sh
uv run --offline --with 'pyyaml==6.0.3' python -B metric_matching_pilot/extract_portable_dbt_yaml.py --repo public_corpus/jaffle-shop --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --output-prefix metric_matching_pilot/portable_jaffle_ --check
python3 -B metric_matching_pilot/run_portable_development_methods.py --packet metric_matching_pilot/portable_jaffle_packet.json --output metric_matching_pilot/portable_jaffle_decisions.json --check
python3 -B metric_matching_pilot/verify_portable_boundary.py
python3 -B metric_matching_pilot/freeze_development_revision_v2.py --check
python3 -B metric_matching_pilot/trace_portable_development_evidence.py --check
python3 -B metric_matching_pilot/freeze_development_revision_v3.py --check
```

This finds 23 YAML metric cards and all 253 unordered pairs. Nine simple declarations have field or numeric-constant syntax, but none supplies independently verified output grain and period grouping. All three methods abstain on all 253 pairs; this measures a **source-evidence coverage limit**, not accuracy, recall or superiority. `run_portable_development_methods.py` reproduces all 55 original GTM pair records exactly when given the original packet. Its strict schema and independent raw-filter/source-flag guard reject nested outcome fields and prevent unresolved YAML filters from being read as unfiltered. `verify_portable_boundary.py` checks both failure paths with controlled development cards. `post_snapshot_development_addendum.json` pins the first post-snapshot revision; its superseded files are preserved byte for byte under `development_revision_history/post_snapshot_v1/`. The append-only `post_snapshot_development_addendum_v2.json` pins the revised boundary checks and cross-references the metadata search frame. `post_snapshot_development_addendum_v3.json` pins the source-only tracer after replacing mutable `HEAD` reads with immutable commit IDs. These checkpoints do not open held-out evaluation. `human_annotation_kit.md` is a blank two-human/third-review workflow, not collected labels. `heldout_search_precommit.json` fixes metadata-only GitHub repository queries and page bounds before any new repository source is opened; `heldout_search_surface_audit.md` documents the search endpoint and its limits. The finalized metadata frame in `heldout_search_capture/attempt-20260928T020324Z-1c3dd1fe/` records 65 ranked occurrences, 62 pinned distinct repositories, raw responses and a manifest hash. Run `python3 -B metric_matching_pilot/verify_heldout_search_frame.py metric_matching_pilot/heldout_search_capture/attempt-20260928T020324Z-1c3dd1fe` for a read-only check. Earlier failed/abandoned attempts remain archived. No held-out source was opened; evaluation remains blocked on the generic compiled-source adapter and protocol freeze.

An additional pinned SQL AST baseline uses SQLGlot 30.20.0 on the **same** GTM packet:

```sh
uv run --with 'sqlglot==30.20.0' python -B metric_matching_pilot/ast_source_baseline.py --check
```

Its parser recognizes all 53 populated expression-field occurrences and records absent fields separately. The AST method yields 2 conditional candidates, 3 related candidates and 50 abstentions, exactly the same 55 pair decisions as the constraint-aware baseline. This is a development comparison of source candidates, not a semantic proof or measured matching accuracy. `gemini_feedback_triage.md` verifies which external review suggestions improve the study and distinguishes the Registered Report's plan-first path from a SANER proceedings paper.

## What the original fixture pilot does

- Runs the SQL views in `sql/metric_views.sql` against the rows in `sql/fixture.sql`.
- Compares **manually written** metric cards in `cards.json`. It does not extract these signatures from SQL or dbt yet.
- Evaluates seven specified pairs in `pairs.json`: direct alias, account rollup, live versus frozen product ARR, a changed pipeline filter, a duplicate hierarchy mapping, an account metric with missing snapshot metadata, and equal-valued customer and product counts as a negative control.
- Checks row values, and for rollups checks that each eligible opportunity has exactly one hierarchy mapping. A valid sample plus manually asserted metadata yields only a **provisional** cross-grain decision.
- Reports one downstream dependency chain for the constructed filter change.

The v0 and v1 pipeline views are simulated versions, not real commits. The cards and mapping instructions are supplied by hand; the fixture classifier cannot independently confirm that they faithfully describe SQL. In particular, the opportunity stage and account exclusion rules used in the rollup have not been proven equivalent across historical data. The separate source extractors and candidate probes above have **not** been connected to this classifier. The fixture classifier does not implement candidate retrieval, general SQL parsing, dbt lineage extraction, query-equivalence proof, an LLM, Snowflake execution, or a representative benchmark. Passing these constructed scenarios is **not** evidence of industrial accuracy or paper readiness. Equal values on a finite fixture never prove semantic equivalence.

## Files

| File | Purpose |
| --- | --- |
| `sql/fixture.sql` | Invented source rows, including a quote update and a duplicated hierarchy mapping. |
| `sql/metric_views.sql` | Executable metric definitions, with one deliberately unsafe rollup. |
| `cards.json` | Hand-authored metric signatures. |
| `pairs.json` | Hand-selected candidate pairs and explicit rollup mapping instructions. |
| `expected.json` | Labels and crucial sample checks, kept separate from the classifier. |
| `pilot.py` | Rule checks, SQLite execution, report generation, and scenario verification. |
| `extract_signatures.py` and `extracted_signatures.json` | A limited SQL extractor and its partial output. |
| `run_public_corpus.py`, `public_corpus_report.json`, `public_corpus_report.md` | Pinned public dbt metric-YAML extraction test and observed boundary. |
| `trace_dbt_lineage.py`, `public_lineage_report.json`, `public_lineage_report.md` | Candidate CTE/ref/source lineage and filter evidence for three selected public metrics. |
| `public_pair_proposals.json`, `public_pair_proposals.md`, `public_pair_blind_review.md`, `build_public_pair_review.py` | First-analyst source-backed labels, validation, and blank independent-review sheet. |
| `reconcile_public_seeds.py`, `public_seed_reconciliation.json`, `public_seed_reconciliation.md` | Reproducible raw-seed checks for disputed tax and time-grain relationships. |
| `public_second_review.json`, `public_pair_resolution_recommendations.json`, `public_pair_author_decisions.json`, `compare_public_pair_reviews.py`, `public_pair_review_comparison.json`, `public_pair_review_comparison.md` | Submitted labels, analyst recommendations, four author-accepted decisions, and disagreement report. Original submitted review is separate. |
| `audit_agreed_public_pairs.py`, `public_agreed_pair_audit.json`, `public_agreed_pair_audit.md` | Source audit of the six initially agreed labels with explicit execution limits. |
| `verify_public_positive_candidate.py`, `public_positive_candidate.json`, `public_positive_candidate.md` | Pinned conditional cross-grain candidate with NULL-aware raw-seed reconciliation. |
| `check_built_positive_candidate.py`, `public_positive_built_check.json`, `public_positive_built_check.md`, `duckdb_profile_example.yml`, `public_positive_dbt_package_lock.yml` | Reproducible materialized dbt check and the passing equality test's NULL gap. |
| `check_semantic_positive_candidate.py`, `public_positive_semantic_check.json`, `public_positive_semantic_check.md` | Execute both declared measures in Sidemantic 0.8.2 and compare every aligned daily result. |
| `audit_unrelated_public.py`, `unrelated_public_audit.json`, `unrelated_public_audit.md`, `gtm_profile/profiles.yml` | Audit independent public development controls and a real before/after metric change; reproduce GTM's single-threaded dbt build. |
| `independent_review_protocol.md`, `first_labels_for_second_review.json`, `blind_second_agent_review.md`, `second_agent_comparison.md` | Source-blind separate AI review of five selected development cases, frozen earlier conclusions, and conditional comparison. |
| `paper_readiness_review.md`, `heldout_sampling_protocol.md` | Separate AI manuscript critique and prospective selection/evaluation rules for later public testing. |
| `analyze_versioned_metrics.py`, `versioned_metrics_report.json`, `versioned_metrics_report.md` | Automated Rill adjacent-commit metric-ID linking, narrow denominator-guard classification, and source-linked dashboard declarations. |
| `analyze_dbt_sql_versions.py`, `dbt_version_report.json`, `dbt_version_report.md` | Bounded dbt SQL source comparison, simple model/seed `ref()` graph, and conservative unresolved-source reporting. |
| `extract_dbt_metric_branches.py`, `dbt_metric_branches_report.json`, `dbt_metric_branches_report.md` | Bounded extraction of individual GTM metric branches from a pinned source file; unexpanded syntax and field lineage remain unresolved. |
| `run_development_baselines.py`, `development_baselines_report.json`, `development_baselines_report.md` | Name-only candidate ranking diagnostics on selected public and constructed cases, without gold-label effectiveness estimates. |
| `evaluation_contract.md`, `annotation_schema.json` | Prospective sampling, human annotation, fair comparison, and record-shape specification; not a completed evaluation. |
| `trace_compiled_metric_fields.py`, `compiled_metric_fields_report.json`, `compiled_metric_fields_report.md` | Bounded compiled field provenance on pinned GTM artifacts, with explicit review stops. |
| `rank_source_aware_candidates.py`, `source_aware_candidates_report.json`, `source_aware_candidates_report.md` | Exhaustive development ranking of 55 GTM branch pairs using name and syntactic-source features; no effectiveness estimate. |
| `analyze_versioned_dbt_branches.py`, `versioned_dbt_branches_report.json`, `versioned_dbt_branches_report.md` | Individual metric-branch source links and potential model-path alerts across a pinned adjacent GTM commit pair. |
| `next_step_integration_contract.md`, `combined_agent_review.md` | Interpretation rules and separate AI synthesis/review of the three parallel probes; neither is human gold. |
| `conditional_method_contract.md`, `build_conditional_evidence.py`, `conditional_evidence_packet.json`, `conditional_evidence_packet.md` | Fixed development protocol and label-free, pinned 11-card/55-pair source/compiled packet. |
| `normalized_sql_lineage_baseline.py`, `normalized_sql_lineage_report.json`, `normalized_sql_lineage_report.md` | Literal-preserving SQL/lineage comparison on the full same-input universe. |
| `constraint_aware_baseline.py`, `constraint_aware_report.json`, `constraint_aware_report.md` | Source and grain/filter/time constrained comparison with explicit unknown prerequisites. |
| `conditional_decision_method.py`, `conditional_decision_report.json`, `conditional_decision_report.md` | Proposed source-linked conditional month-to-window explanation or abstention for every pair. |
| `compare_conditional_development.py`, `conditional_development_comparison.json`, `conditional_development_comparison.md`, `conditional_method_review.md` | Common-input comparison, isolated public row checks, and separate AI review; no human gold. |
| `freeze_development_snapshot.py`, `development_snapshot_freeze.json` | Hash-checked GTM development method/evaluation snapshot; not held-out results. |
| `extract_portable_dbt_yaml.py`, `portable_jaffle_packet.json`, `portable_jaffle_report.{json,md}` | Pinned YAML inventory with missing semantic fields explicit for all 23 Jaffle development definitions. |
| `run_portable_development_methods.py`, `portable_jaffle_decisions.{json,md}` | Full 253-pair portability probe and abstention/coverage report; no gold labels. |
| `verify_portable_boundary.py`, `freeze_post_snapshot_addendum.py`, `post_snapshot_development_addendum.json`, `freeze_development_revision_v2.py`, `post_snapshot_development_addendum_v2.json`, `development_revision_history/post_snapshot_v1/` | Exact replay and filter/label/aggregation guards; byte-preserved v1 and v2 development hash records. |
| `trace_portable_development_evidence.py`, `trace_portable_development_evidence.{json,md}` | Pinned development source-SQL and dependency links only; zero compiled sources or decisions. |
| `freeze_development_revision_v3.py`, `post_snapshot_development_addendum_v3.json`, `trace_portable_development_review.md` | Source-only trace revision hash and independent provenance review; no new held-out source or decisions. |
| `human_annotation_kit.md`, `heldout_search_precommit.json`, `heldout_search_surface_audit.md` | Blinded prospective human review template and predeclared metadata-only repository search; no held-out code inspected. |
| `capture_heldout_search_frame.py`, `verify_heldout_search_frame.py`, `heldout_search_capture/` | Dated metadata-only search attempts, complete raw-response frame, pinned refs and independent integrity check; no held-out source or labels. |
| `ast_source_baseline.py`, `ast_source_baseline_report.{json,md}`, `gemini_feedback_triage.md` | Pinned SQLGlot AST development comparator and source-backed review triage; no demonstrated method advantage. |
| `registered_report_stage1_sketch.md` | Prospective exploratory Stage 1 route, six-page plan, human-work budget examples and non-exact-recall fallback; not a submitted or accepted report. |
| `prior_work_novelty_matrix.md` | Primary-paper audit of Valentine, ConStruM, GEqO and CGM, with a falsifiable maintenance-decision hypothesis; no novelty claim yet. |

Next research step: improve the proposed method where it demonstrably adds safe, source-backed decisions beyond the strong constraint baseline, or narrow the paper's claim to a careful benchmark and maintenance study. Freeze the implementation, thresholds, evidence budget, and full search-result sampling frame before opening new held-out projects. Obtain two independent domain-human decisions and adjudication before calling any pair label ground truth. Compare unsafe equivalence, coverage, reviewer effort, and cost on complete held-out anchor universes. Native MetricFlow/Cube runtime checks are needed before claiming portability across them. Preserve `needs_review` when parsing or lineage is incomplete.

### Generic SQL source-inventory development check (September 28 UTC)

`generic_sql_inventory.py` uses pinned SQLGlot 30.20.0 with DuckDB dialect to inventory the already included synthetic `sql/metric_views.sql`. `uv run --offline --with 'sqlglot==30.20.0' python -B metric_matching_pilot/generic_sql_inventory.py --check` regenerates the JSON and Markdown reports byte for byte without writing. The report records 12 views, 24 emitted projections and all 276 unordered pairs **of those projections**; six value projections have recognized aggregates and four meet this deliberately narrow source-parser support. Across the 276 pairs, it emits 270 abstentions, one same-source review candidate and five syntax differences. The separate synthetic negative fixture checks SUM/MEDIAN, COUNT over different tables, COALESCE, joins and Jinja. Its aliasless Jinja case gets an abstaining placeholder, with true output arity unknown. None of these cases is human gold or establishes value equivalence.

`generic_adapter_review_contract.md` independently reviewed the initial source inventory and caught unsafe regex alias recovery in unparseable SQL. The corrected parser emits an abstaining view-level placeholder instead of guessing aliases; its final re-review is recorded there. Generic metric eligibility, the true output count of unparseable statements, compiled SQL provenance and full same-input evaluation remain open. The inventory includes `entity_key` projections, so 24/276 is **not** a validated metric-definition universe. `generic_adapter_integration_gate.md` maps these limitations to the existing evaluation contract. No new held-out repository source was inspected, and the held-out source gate remains closed.

`generic_same_input_baselines.py --check` verifies a separate **development-only** same-pair diagnostic without writes. It freezes the source inventory digest, selects the 12 `.value` projections by an explicit **fixture-only** rule, and gives all four name scores plus the normalized AST/source and constraint-aware syntax comparators the same 66 unordered pair IDs. The two `I1` comparators share an evidence-packet hash. Both emit one same-source syntax signal, five source differences and 60 unsupported pair signals; all 66 semantic decisions abstain because grain, time, NULL, snapshot or other decisive semantics are unknown. The `.value` eligibility rule, true projection arity for unparseable SQL, compiled provenance, and a context-matched proposed/LLM method remain unresolved for a real study. This is a fairness scaffold with zero judged outcomes, not a measured baseline advantage or completed evaluation.

The dated v2 independent reviews in `generic_adapter_review_contract.md` and `generic_same_input_baselines_review.md` check the corrected parser and same-input digests. `freeze_development_revision_v4.py --check` verifies an append-only SHA-256 record of this development revision. Earlier freezes are retained unchanged. This checkpoint explicitly keeps the held-out source gate closed.

### Public dbt declaration and compiled-model development audit (September 28 UTC)

`generic_adapter_bridge_contract_20260928.md` fixes the join and evidence-level rules before combining two independent development adapters. `generic_metric_eligibility.py` reads pinned Git YAML declarations or a selected local dbt manifest. It excludes dimensions, entity keys and arbitrary SQL projections; unsupported, derived, templated and malformed declarations remain visible as unknown. Source YAML at Jaffle commit `5beb145b…` yields 23 metric declarations and 253 pairs. A **different** Jaffle/Sidemantic checkout at `7be2c583…` has a locally built manifest with 19 metric declarations and 13 semantic-model measures: 171 exposed-metric pairs, or 496 pairs when measures are separately included. These frames have different commits and source surfaces; do not pool them or call the pairs judged matches. A manifest's build commit and source-to-declaration mapping are unverified. Reproduce the read-only reports with their `--check` commands in `generic_metric_eligibility_report.md` and `generic_metric_eligibility_manifest_report.md`.

`generic_compiled_provenance.py` audits **model artifacts** in already inspected GTM and Jaffle checkouts. It finds all 46 pinned model source blobs and exact equality between all 46 compiled files and manifest `compiled_code`. GTM's 33 model source mappings pass the bounded checksum/normalization checks. All 13 nested Jaffle model mappings remain `needs_review`: their manifest checksums equal neither the pinned Git blobs nor manifest `raw_code`, even though source differs from `raw_code` by only one trailing newline. The manifest generation event is not authenticated to the checked-out commit. Neither result traces an individual metric to a compiled scalar expression. Reproduce with the command and self-test in `generic_compiled_provenance.py` and the independent `generic_adapter_parallel_review_20260928.md`.

The reviewer verified final hashes, report regeneration, missing/modified compiled-file controls, wrong commit/path rejection, ambiguous measure binding, unknown declaration arity, and non-promotion of a model check to metric-expression provenance. This is an **AI code review**, not human gold. `freeze_development_revision_v5.py --check` verifies the append-only v5 hash checkpoint chained to v4. The next technical gate is a same-commit declaration-to-compiled-*metric-expression* mapping and common label-free I1 packet used by the proposed method and strong AST/lineage and constraint-aware baselines on the same complete pair frame. Do not open newly selected held-out source before that adapter and packet are fixed. The concrete human preparation is two independent qualified annotators plus a separate adjudicator, with a bounded public-definition review budget. This pilot archive is a working artifact and still includes a private-motivation synthetic fixture; it has **not** been cleared as a public release package.

### Trace-integrated same-input development revision (September 28 UTC)

`generic_v6_preimplementation_contract.md` fixes the next bounded development inputs before the implementation. `generic_metric_expression_trace.py` follows all 32 Jaffle/Sidemantic manifest declarations through exact manifest resource dependencies to candidate models and checks source paths, compiled files, expression fields and projection owners. It finds 31 unique compiled-**model** candidates, but verifies **zero** compiled **metric expressions**. All 32 remain `needs_review`: the local manifest build commit is unattested, all 13 Jaffle model-source checksums remain unreconciled, compiled metric queries are unavailable, and CTE/star/join ownership can be unresolved. The modified local `package-lock.yml` differs from the pinned Git blob; this is a separate build-provenance caveat, with no established cause for the checksum mismatch. Reproduce the report with `python3 -B metric_matching_pilot/generic_metric_expression_trace.py --check` and its adversarial controls with `--self-test`.

`generic_i1_same_input.py --check` reproduces the **trace-integrated**, label-free comparison packet. It retains 19 metric IDs and 13 measure IDs, all **496** unordered pairs, and a separate 19-metric/171-pair frame. Normalized AST/source, constraint-aware and source-guided conditional methods receive the *same* canonical I1 packet and pair IDs. Five I0 methods—raw exact, normalized exact, Jaro–Winkler, token Jaccard and Soundex—use names only on the same pair IDs. All three I1 methods abstain on **every semantic decision** because expression and scope evidence is incomplete. Constraint-aware emits 11 shared-declared-measure review signals; the source-guided method also emits 146 weak same-file review signals. Those are co-location or declared-dependency diagnostics, **not** transformation claims or measured advantages. The AST method cannot analyze verified scalar ASTs on this input and abstains on all 496 pairs. Packet and pair-set hashes, method versions, evidence fields and abstention reasons are in `generic_i1_same_input_report.{json,md}`.

`generic_v6_independent_review_20260928.md` records an independent AI technical audit of final hashes, read-only checks, pair completeness and tamper controls. `freeze_development_revision_v6.py --check` verifies the append-only v6 record chained to v5. The dated metadata-only search frame is unchanged; **no newly selected held-out source was opened**. This packet is a development plumbing result with zero independently judged accuracy, recall, reviewer effort or method superiority. A general same-commit source-to-compiled-*metric-query* adapter and substantive context-matched baselines are still required before the held-out gate can open.

A separate **public-only** `metric_matching_public_calibration_packet.md` is intended for the two independent human reviewers and later adjudicator. It has three pinned development pairs, public source links, a short rubric and blank worksheets; it is intentionally outside this working ZIP because the ZIP has not been cleared for distribution. It is a practice exercise, not held-out gold. Give both reviewers identical packet bytes and collect their submissions separately before the adjudicator sees them.

### Paired safety accounting and isolated build attempt (September 28, 2026)

`paired_decision_safety.py` computes descriptive safety counts on the common decided-pair intersection of two methods from the same complete I1 packet. Its primary denominator is the **same number of common decided pairs** for both methods; it separately reports each method's equivalence assertion count, unsafe assertions per assertion, unresolved reference evidence and coverage. It requires two qualified independent human judgments and distinct adjudication with source-linked evidence before counting an assertion as confirmed unsafe or supported; the script checks only the structure of that provenance and cannot verify real-world reviewer identity or cited source bytes. The 20-assertion/two-project threshold is a planning floor for a separate predeclared analysis, **not** a significance test. Use `python3 -B metric_matching_pilot/paired_decision_safety_checks.py` from the parent directory to exercise constructed controls and the existing 496-pair no-gold development report. With zero semantic decisions, the result is **untestable**. Neither the controls nor the pilot output are human gold.

`dev_build_evidence_20260928/technical_build_report.md` and its small logs record an isolated build attempt for the pinned Jaffle development commit. dbt Core 1.12.5 and the `dbt-metricflow` 0.15.0 CLI installed and `mf` launched, but `dbt deps` timed out before installing three project packages. Parsing and metric SQL generation therefore remained blocked; no `order_cost` relationship label, warehouse-credential conclusion or verified compiled metric expression follows. The source checkout was left unchanged. Keep this build evidence and all development labels away from blind practice reviewers. The active paper target is the SANER 2027 **Industrial Track**; any earlier registered-report planning sketch in this working archive is not the selected submission route.

### Fresh compiled-metric development packet and fair baselines (September 29, 2026)

The later, separately saved `metric_provenance_jaffle_7be2c58.zip` development bundle supersedes the isolated attempt above. Its SHA-256 is `322aec391ce98c05a51c79a30abae803378d350e824a2e21f07ea0161f28380e`. It contains a clean-environment, same-commit Jaffle parse and MetricFlow-generated DuckDB SQL for **all 19 declared metrics**; no metric values were run. Eighteen SQL queries are ungrouped, while the offset-window metric `revenue_growth_mom` has a generated query only with `metric_time`. The bundle is stored separately from this working archive. See its `report.md` for dependency resolution, connection, and source-mapping limits.

`compiled_development_baselines_contract.md` fixes the label-free I1 evidence budget and the complete 19-metric/171-pair frame. `compiled_jaffle_i1_packet.json` is the frozen derived input (SHA-256 `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`). The 153 pairs with two ungrouped queries can be compared at that limited scope. The 18 pairs involving the time-grouped-only metric remain in the frame and both I1 methods abstain. Numeric eligibility is explicitly unverified by the compiled bundle for every card. The earlier separate declaration inventory classified nine eligible and ten unknown under its own policy; do not infer 19 certified numeric metrics from generated SQL.

To reproduce the packet from the separately saved provenance ZIP, verify its ZIP hash and `SHA256SUMS`, extract it to a directory named `metric_provenance_verification` beside this pilot directory, and run from their parent directory:

```sh
python3 -B metric_matching_pilot/compiled_jaffle_packet.py --check
```

For the baseline diagnostic, use Python with **SQLGlot 30.20.0** (DuckDB dialect), then run:

```sh
python -B metric_matching_pilot/run_compiled_development_comparison.py --check
python -B metric_matching_pilot/verify_compiled_development_comparison.py
```

On this development frame the I0 name scores use all 171 pair IDs; the initially implemented two I1 comparators receive identical card objects on the 153 common-scope pairs, and a common hard gate records their 18 mixed-scope abstentions. Their source-only candidate scores and semantic decisions remain distinct. `compiled_development_baselines_report.{json,md}` records full-frame signals, abstention counts, method and runner hashes, and global and per-anchor rankings on the 153 common-scope pairs with lexical ties. Both exact-name methods score zero for every comparable pair, so their rankings are entirely tie order. The verifier checks all 19 SQL parser inputs, the full pair frame, scope examples, future eligibility-only promotion, and rejection of an altered input packet. It does not test an independently judged match. Identical ungrouped ASTs for `cumulative_revenue` and `revenue` are a **syntax review signal**, not semantic equivalence or human adjudication. No accuracy, candidate Recall@k, safety improvement, or proposed-method superiority can be estimated from this unlabelled development run. The subsequent section includes the proposed comparator on the same packet.

The source bundle and these method outputs remain away from any still-blind CAL-03 practice reviewer. No new held-out repository source was opened. The next section records the subsequent eligibility and proposed-method development work. Before a held-out study, freeze sampling and annotation budgets, authenticate external evidence records, and fix the evaluation policy. The AST comparator checks the shape of external evidence but does not fetch and verify artifact bytes or reviewer identity. The frozen runner rejects changes to this packet, so that gap does not alter its all-abstain report. This ZIP remains a working archive with a synthetic fixture whose private motivation has **not** been cleared for public release.

### Numeric declaration gate and proposed review method (September 29, 2026)

`compiled_proposed_development_contract.md` records the fixed development-only rule before the three-method report. `compiled_numeric_eligibility.py` applies the existing generic dbt declaration policy to the same fresh compiled packet. A simple metric with one uniquely bound numeric-aggregate measure and no unresolved template can be marked `eligible_declaration_only`; generated SQL does **not** certify a runtime numeric result. The current packet has nine declaration-level candidates and ten unknowns (four with templated filters, six with derived/ratio/cumulative rules); **all 19 declarations and all 171 pairs stay in the frame**. See `compiled_numeric_eligibility_report.{json,md}` for per-metric reasons and 36 both-candidate pairs versus 135 pairs with at least one unknown.

`compiled_proposed_method.py` consumes the same two cards as the AST/lineage and constraint-aware baselines on each of 153 ungrouped-scope pairs. Its SQLGlot-based source review ranks candidate investigations and records explicit unknown proof obligations. A shared declared measure owner does **not** establish compiled field lineage. It does **not** accept a syntax match, shared measure, or derived input as semantic equivalence. The common runner retains the 18 mixed-scope pairs as abstentions for all three methods and rejects any semantic decision on this packet. The proposed method produces 25 source-linked review prompts and 25 additional weak same-model ranking signals in this development corpus, while **all 171 semantic decisions abstain** for each method. Prompts are questions or test recipes, not reference labels or validated matches. The `cumulative_revenue`/`revenue` ungrouped AST identity specifically prompts a time-grain check.

With Python using PyYAML 6.0.3 and SQLGlot 30.20.0, from the directory containing this pilot folder:

```sh
python -B metric_matching_pilot/compiled_numeric_eligibility.py --check
python -B metric_matching_pilot/run_compiled_development_comparison.py --check
python -B metric_matching_pilot/verify_compiled_development_comparison.py
python -B metric_matching_pilot/verify_compiled_proposed_method.py
```

The comparison JSON records the frozen packet and pair hashes, method, runner and contract hashes, every pair's signals and abstention, and global/per-anchor candidate ranks over the 153 common-scope pairs. The proposed method reuses parsing utilities from the AST baseline but reads no baseline output. The methods differ in logic while seeing the same input bytes. The prospective numeric rule has been exercised on one repository; it leaves unknown declarations visible instead of treating them as nonnumeric. No newly selected held-out source was inspected. Human reference labels, sampling and reviewer budgets, evidence authentication, and a context-matched evaluation remain open; no Recall@k, accuracy, safety improvement, or novelty advantage has been measured.

### Public study preparation after the three-method development diagnostic

`public_study_presolve_policy_20260929.md` and `public_industrial_readiness_20260929.md` record the public-only Industrial route and remaining pre-source decisions. The dated metadata-only search frame passed its read-only check with 65 ranked occurrences and 62 pinned distinct repositories; these are not selected eligible projects. `heldout_sampling_protocol.md` and `evaluation_contract.md` retain their earlier text and have dated addenda clarifying the later search capture, primary within-revision task, and public-only route. No new held-out source was inspected.

`evaluate_readiness_budget.py` is a metadata-only **planning calculator** for a supplied JSON file outside this directory. `heldout_budget_freeze_contract.md` specifies its exact schema and deterministic anchor-slot and reserve rules. These ordinal slots are not real metric IDs. It cannot establish project eligibility, available qualified reviewers, human gold or exact Recall@k; if a complete anchor cannot fit the planning envelope, it designates a prospective judged-pool-only fallback. Run the toy controls with `python3 -B metric_matching_pilot/verify_evaluate_readiness_budget.py`.

`compiled_external_evidence_auth.py` authenticates a bounded supplemental semantic claim only when the caller supplies the separately trusted packet digest, allowlisted artifact roots and reviewer public-key registry. It checks exact packet/pair/card/SQL binding, the artifact bytes and an Ed25519 signature. The registry's identity and independence, artifact custody, and the semantic truth of a signed claim remain external responsibilities. Its output **does not** certify numeric runtime type, compiled field ownership or the source commit as a Git object; it has not been integrated as a license for non-abstaining labels. Test its adversarial controls with system Python and `cryptography` 46.0.0 as exercised here: `python3 -B metric_matching_pilot/verify_compiled_external_evidence_auth.py` (the separate SQLGlot venv has no `cryptography`).

`compiled_llm_context_builder.py` creates deterministic, complete two-card messages for the same 153 compatible-scope pairs and explicit abstentions for the other 18. `compiled_llm_context_contract.md` records the fixed instruction, scoped response shape and 20,480-byte input construction cap. The cap is **serialized UTF-8 bytes, not provider tokens**; any over-budget message abstains without truncation. Its response validator rejects wrong pair IDs and malformed cross-grain claims, but gates any unsupported semantic assertion to `abstain` with a separate `needs_review` evidence status. It must receive rows from the builder on the pinned packet; a model-written `verified` flag is no independent verification. No model was run, and a provider/version, decoding, response token budget, card-text injection assessment and cost policy remain to be fixed before an LLM baseline study. Check the constructor with `python3 -B metric_matching_pilot/verify_compiled_llm_context_builder.py`.

### Bounded public-study preparation and independent baseline (September 29, 2026)

`scoped_mask_decision.py` is a **development-only** two-case aggregate-mask rule. Its revised documentation guard and `scoped_mask_guard_checks.py` reject nine in-memory adversarial changes, but accept only the exact affirmative food/drink Jaffle wording. It still predicts two scope variants and abstains on 169 of 171 pairs; these are not adjudicated labels. `ast_mask_baseline.py` independently parses a narrow SUM/CASE AST with the same pair-card evidence and makes **the same two outputs and 169 abstentions**. Its upstream flag semantics also remain unresolved. See the two adjacent reports; the development tie establishes no incremental detector result.

`public_pair_selection_freeze.md` and `public_pair_selection_queue.json` record a dated, metadata-only, hash-ordered screening queue of 62 pinned public repositories. None has been source-screened or established eligible. The conditional two-project core samples up to eight within-revision pairs per project and budgets 24 human person-hours including independent judgments, adjudication and audit. It makes no exact Recall@k claim. A four-project, 48-pair expansion requires capacity committed before outcomes. `paper_completion_progress_review_round2.md` is an independent **AI** review recommending this finite empirical gate and stopping the current detector-advance claim. No held-out source or human worksheet was inspected in this round. This archive is a working packet and still contains material not cleared for public release.

### Six reviewer questions: bounded development answers

`reviewer_questions_response.md` gives the evidence status and remaining measurement for each question. `aggressive_ast_equivalence_baseline.py` and its report let an intentionally permissive AST matcher issue its natural **one** broad `direct_equivalent` assertion on `cumulative_revenue`/`revenue` from identical ungrouped SQL; 170 other pairs abstain. The existing bounded month result refutes extending that assertion to month-grain substitution, while a scalar-only assertion survives that check. `counterexample_decision_audit.md` records which food, cumulative and gross-profit observations are actual aligned refutations and which are not. `metricflow_time_semantics_note.md` distinguishes dbt's documented `period_agg: first` default from the first-calendar-day value observed in one reconstructed query. The mask pattern fires 2/171 with and without the exact Jaffle documentation guard; outside-project coverage and human agreement are unknown.

`maintenance_workflow_example.md` is a hypothetical PR-review warning grounded in a pinned public-seed day witness, not observed maintainer behavior. `reviewer_questions_progress_review.md` is an independent **AI** stop/go review and a two-page process-text cut list for a future result-led manuscript. No new held-out source or practice worksheet entered these development checks. The existing archive remains a working packet, not a public release bundle.
