# Isolated Jaffle metric build attempt — 2026-09-28

Scope: already inspected public development checkout only. No held-out repositories inspected. This is a build/provenance report, not an annotation or interpretation of CAL-03.

## Source and isolation

- Source Git HEAD: `7be2c5838dbdeca8e915d4e46db70e910753d7f6`.
- Clean source created by `git archive HEAD | tar -x -C <isolated>/source`; original checkout, its existing `target/`, and its pre-existing modified `package-lock.yml` were not written.
- Original tracked `package-lock.yml` hash from HEAD and isolated copy: `a1d44d11c893f4d68e722ef8479bd3c4d2f632202f1ef7bd4ade6a14986b50db`. Original checkout's modified lock is `67ecfc0a7ebdcc03b8e2f38c86d7b283e72c5d58fb9a7de9b4f30aa2a3a01eef` (pre-existing at start).
- Pinned lock: dbt_utils 1.1.1, dbt_date 0.10.0, dbt-audit-helper Git revision `b8f3a3348ce0ff8afc3aa4b9ade2123b00772473`. Note the same Git revision's tracked `packages.yml` asks for dbt_utils 1.3.3, dbt_date 0.17.1, and dbt-audit-helper `main`. This mismatch may cause dbt to regenerate the lock on a successful `dbt deps`; it did not do so in this timed attempt.
- Additional source hashes: `packages.yml` `43c2cc277fee0dd4bb0958c711593509b4b30171e8dc04074184ab93d62b2cce`; `dbt_project.yml` `f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122`; `models/marts/order_items.yml` `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97`; `models/marts/orders.yml` `223dc461510c54b38681167b85cea019b3919c4a1de8bfac6673d60465ea0391`.

## Isolated runtime and commands

- Python 3.12.14; created `venv` in this report directory.
- `timeout 75s uv pip install --python venv/bin/python 'dbt-core==1.12.5' dbt-duckdb metricflow` succeeded. Resolved: dbt-core 1.12.5, dbt-duckdb 1.11.0, metricflow 0.213.0, duckdb 1.5.6, sqlglot 30.20.0. Full resolver record: `install.log` (SHA-256 `58c446c30979c109ed3c23d1feeb5d0ea258092a65d8dab25a659a006cc91bf8`). These are *environment* versions, not pinned by the repository lock.
- In isolated `source/`: `timeout 30s ../venv/bin/dbt deps --project-dir . --profiles-dir .` exited 124 (timeout). `deps.log` contains only `Running with dbt=1.12.5`; no package was installed. Lock hash unchanged. Log SHA-256 `28a7409e37b7d551be5c7ca74b1a417a0dbbb47a4d791f1b5dcb1669363d62fa`. Root cause of timeout not established; cannot claim certificate or network failure specifically.
- `../venv/bin/dbt parse --project-dir . --profiles-dir . --no-partial-parse` initially exited 2 because clean Git archive has no local `profiles.yml` (`parse.log`, SHA-256 `f3f66305bae07419d21dfb9d2fabde868ce625cd6edc014694e1907549f7ceaa`).
- Copied the development checkout's local DuckDB-only `profiles.yml` into the isolated copy; SHA-256 `c8f849439789c5031dc714c177c82e1224d70df6e733893f98175033a3cc0e41`. Then `timeout 12s ../venv/bin/dbt parse --project-dir . --profiles-dir . --no-partial-parse` exited 2: dbt expected 3 packages, found 0; `parse_with_profile.log` SHA-256 `84ea64938b9c2bb2a8d415819b0ce0fb8d6a859a8b3b99f45c9bdc0b5f28905f`.
- `metricflow` 0.213.0 installed **no `mf` console entry point**. `venv/bin/mf` does not exist, and `venv/bin/dbt sl --help` reports `No such command 'sl'`. Consequently `mf query --metrics order_cost --explain` was not run. `/usr/bin/mf` on the system is not a MetricFlow CLI.

## Outcome

- No fresh `manifest.json`, `semantic_manifest.json`, or compiled metric SQL was produced; artifact hashes and SQL are therefore **unavailable**. Existing target artifacts in the original checkout remain unattested to this pinned source and were not used as fresh build evidence.
- Warehouse credential requirement: **undetermined**, because dependency installation and parsing failed before a metric query could be attempted. The copied development profile is a local DuckDB profile, not a remote warehouse credential.
- Next bounded technical action: make pinned dbt package dependencies available in an isolated environment, resolve tracked `packages.yml` versus lock inconsistency explicitly, then run clean `dbt parse` and install the CLI distribution that actually exposes `mf` before trying an explain/compile. Keep all new evidence away from practice adjudicators until their blind responses are locked.

## Follow-up addendum — 2026-09-28 14:31 UTC

The [dbt-labs MetricFlow README](https://github.com/dbt-labs/metricflow/blob/main/README.md) documents `dbt-metricflow` as the CLI bundle and `mf` as its command. This corrects the earlier assumption that installing the Python `metricflow` library alone should provide `mf`.

- From the **same isolated venv**, `uv pip install --python venv/bin/python 'dbt-core==1.12.5' 'dbt-duckdb==1.11.0' 'metricflow==0.213.0' dbt-metricflow` succeeded. Resolved versions: dbt-core 1.12.5, dbt-duckdb 1.11.0, metricflow 0.213.0, **dbt-metricflow 0.15.0**. The new `mf` console entry point is `dbt_metricflow.cli.main:cli`. Resolver output: [cli_install_pinned.log](./cli_install_pinned.log), SHA-256 `917211f65038b4432737d6d4b540e597fabaa8cb2d932001ed07935cce422f0b`.
- `venv/bin/mf --help` exited 0, showing `query`, `list`, `validate-configs`, `health-checks`, and `tutorial`; [mf_help.log](./mf_help.log), SHA-256 `8c0b534f4fa638cfd48b526be303cfb05f62795060398b24da24957fc7f7f23c`. `venv/bin/mf --version` exited 0 with `mf, version 0.15.0`; [mf_version.log](./mf_version.log), SHA-256 `032e004f226c83db6b890eaaa57aa2158dec20ba096f06ccb27d28ded923adaf`.
- From the isolated Git archive's dbt project root, `timeout 18s ../venv/bin/mf query --metrics order_cost --explain` exited 1 **before compilation**: `Unable to load the semantic manifest` at `source/target/semantic_manifest.json`. [mf_explain.log](./mf_explain.log), SHA-256 `8e7377229132a1add0424cb6b80b6ff300a7d1ea3535a0dd7895d744c7e3428a`. The preceding `dbt parse` failed because three dbt dependencies were absent; no fresh semantic manifest or generated SQL exists. Warehouse credentials were **not reached or tested**.
- The original public checkout remains at `7be2c5838dbdeca8e915d4e46db70e910753d7f6` with only its pre-existing `package-lock.yml` modification; its lock hash remained `67ecfc0a7ebdcc03b8e2f38c86d7b283e72c5d58fb9a7de9b4f30aa2a3a01eef`. The isolated pinned lock remained `a1d44d11c893f4d68e722ef8479bd3c4d2f632202f1ef7bd4ade6a14986b50db`.

The next build task is now specifically to install the dbt packages for the pinned source and successfully generate a fresh semantic manifest in isolation; the CLI bundle is available. This addendum makes no relationship-label decision.
