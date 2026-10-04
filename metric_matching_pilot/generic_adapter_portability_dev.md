# Frozen generic adapter portability check on GTM development project

**Scope (2026-09-29 UTC).** This is a bounded technical check on the already inspected `public_corpus/gtm-funnel-analytics` checkout. No new held-out repository was inspected, no adapter or project source was edited, and no pair labels or accuracy estimates are made.

## Inputs and isolated run

| Item | Recorded value |
| --- | --- |
| Frozen adapter | `metric_provenance_verification/inputs/run_adapter.py`, SHA-256 `7b90ef37dfb1cce9c0a15f211ef89fb56106a0f1eb8817ed0ae405ad05ce09fe` before and after the run |
| Project commit | `a71232c123a5fb78da9b52d4246950ee48591c00`; checkout clean before and after; origin `https://github.com/jross21/gtm-funnel-analytics.git` |
| Isolation | Fresh `/tmp/gtm_adapter_portability_venv` and `/tmp/gtm_adapter_portability_run_20260929`; adapter exported the pinned commit by `git archive` (tar SHA-256 `e8bba40deac8a8851a61fef6399617b04dafc9534d7db1b6d19a581e9647179f`), generated a local DuckDB profile, and ran dbt with its scrubbed environment. The export had no `target/`. |
| Runtime | Python 3.12.14; `dbt-core` 1.11.6, `dbt-duckdb` 1.10.1, DuckDB 1.4.4, `dbt-metricflow` 0.15.0, MetricFlow 0.213.0 |
| Invocation | `/tmp/gtm_adapter_portability_venv/bin/python -B metric_provenance_verification/inputs/run_adapter.py --repo /workspace/scratch/e767b9d6f697/public_corpus/gtm-funnel-analytics --commit a71232c123a5fb78da9b52d4246950ee48591c00 --out /tmp/gtm_adapter_portability_run_20260929 --venv /tmp/gtm_adapter_portability_venv` |

The frozen script completed its failure-reporting path with process exit **0**, but `run_metadata.json` records `failure_stage: "dbt parse"` and `parse_exit: 2`. Its success as a process must not be read as a successful extraction. The run's `SHA256SUMS` entries verified.

## Actual frozen-adapter coverage and failures

| Stage / denominator | Observed result |
| --- | --- |
| Project-specific governed catalog | **9** definitions in the pinned root `metrics_catalog.yml`: `mql_volume`, `pipeline_created`, `win_rate`, `avg_sales_cycle_days`, `sla_compliance`, `speed_to_lead_median_min`, `mql_to_sal_rate`, `sal_to_sql_rate`, `sql_to_opp_rate`. These are catalog entries implemented in `models/marts/metrics/fct_metric_values.sql`, not dbt Semantic Layer metric declarations. |
| `dbt deps` | Exit **2**. Its registry lookup for `https://hub.getdbt.com/api/v1/index.json` failed with `NameResolutionError` / temporary DNS failure. The pinned archive requires one `dbt_utils` package and contained no installed `dbt_packages`; zero were installed. The copied lock's SHA-256 stayed `7b2ac03716100a9af5917667fdab99650eb2040fd903943837dc266f22576582`. |
| `dbt parse --no-partial-parse` | Exit **2**: `dbt found 1 package(s) specified in packages.yml, but only 0 package(s) installed in dbt_packages`. No fresh `manifest.json` or `semantic_manifest.json` was emitted by this adapter run. |
| Metric extraction and compilation | `provenance.json` is `[]`; `provenance.csv` has only its header: **0 rows for 9 catalog definitions**. The adapter did not enter its metric loop, did not call `mf query --explain`, and generated **0 metric SQL files**. The nine definitions were *not assessed* for provenance or compilation by this failed run. |
| Ancillary environment record | `python -m pip freeze` exited **1** because the fresh `uv` venv has no `pip` module. This did not cause the dependency or parse failures. |

Run evidence: `/tmp/gtm_adapter_portability_run_20260929/logs/01_dbt_deps.{exit,stdout}`, `logs/02_dbt_parse.{exit,stdout}`, `run_metadata.json` (SHA-256 `4c762190970d71386ac9b5c9643c7d60ed1b1ce43d2e575bb79e2e177c3ae036`), and `provenance.json` (SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`). These `/tmp` paths are local run evidence, not durable report attachments.

## Separate diagnostic of the format boundary

To distinguish the immediate package-fetch failure from project compatibility, I made a **separate** pinned Git archive at `/tmp/gtm_adapter_portability_diag_20260929/project`, copied the development checkout's pre-existing local `dbt_packages/dbt_utils` directory into that diagnostic copy, and ran `dbt parse --no-partial-parse` with the same venv and a local DuckDB profile. This manual dependency supply is **not an unmodified adapter run** and makes no claim about the exact registry package bytes.

The diagnostic parse exited **0** and wrote a `manifest.json` (SHA-256 `adcbff8917ab077c67f3b2b26b4391467e73d23d51ce7001b497e85581b1baca`) and a `semantic_manifest.json` (SHA-256 `90ac128fee2016eab7c89e7409f56d3f13773758a445e0c9c0523d228529cdc5`). Both contain **0 metrics and 0 semantic models**; the semantic manifest also has **0 time spines**. A direct `mf query --metrics mql_volume --explain` in this diagnostic copy exited **1** before generating SQL: `At least one time spine must be configured to use the semantic layer, but none were found.` The adapter itself would iterate over `semantic_manifest.json["metrics"]`, so even after a successful dependency install and parse it would emit zero rows for this project as currently defined.

## Assessment

The script **runs unmodified as a failure-reporting process** against this second development project, but **cannot provide metric provenance or compiled metric SQL for GTM as-is**. The immediate local blocker is the unavailable dbt package registry, which prevents its clean-archive parse. Independently, GTM's nine governed metrics live in a custom root catalog and SQL model, while the frozen adapter only extracts dbt Semantic Layer metrics and invokes MetricFlow for those entries. Supplying dependencies alone therefore does not bridge the nine catalog definitions; it also does not supply a MetricFlow time spine. A project-side Semantic Layer migration or a different extraction contract would be required for substantive coverage. This check reports technical coverage and failure modes only; it establishes no matching accuracy, equivalence, or cross-project method performance.
