# Setup: supply-chain-analytics-dbt

**Project:** <https://github.com/KushPatel29/supply-chain-analytics-dbt>
**Pinned commit:** `04ba76437cf0ba8b0b90c1709b6559e3fa7ba2cb`
**dbt project folder:** the repository root

Before this sheet, finish Steps 1–3 of [SETUP.md](../SETUP.md): Git, Python 3.12 and the `metric-review` work folder. The ✅ checks work the same way: if your screen doesn't match one, stop and email the coordinator.

This project ships its own sample data (CSV seeds) and its own local DuckDB profile, so it needs the fewest steps.

---

## Step 1: Download the project at the exact version

```bash
cd ~/metric-review          # Windows: cd $HOME\metric-review
git clone https://github.com/KushPatel29/supply-chain-analytics-dbt.git
cd supply-chain-analytics-dbt
git checkout 04ba76437cf0ba8b0b90c1709b6559e3fa7ba2cb
git log -1 --format=%H
```

✅ **Check:** the last command prints exactly `04ba76437cf0ba8b0b90c1709b6559e3fa7ba2cb`.

**Stay inside the `supply-chain-analytics-dbt` folder for all remaining steps.**

## Step 2: Create the dbt environment

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```
```powershell
# Windows
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```

✅ **Check:** `dbt --version` shows `installed: 1.12.5`, and lists `duckdb: 1.11.0` under Plugins.

**Every time you open a new terminal later**, run:
- macOS / Linux: `cd ~/metric-review/supply-chain-analytics-dbt && source .venv/bin/activate`
- Windows: `cd $HOME\metric-review\supply-chain-analytics-dbt; .venv\Scripts\Activate.ps1`

## Step 3: Profile

The project already contains a `profiles.yml` whose default target is a local DuckDB file, `target/supply_chain.duckdb`. **Use it as it is**, without creating or editing anything. The file also names Databricks and Snowflake targets. Don't use them.

## Step 4: Build the project

```bash
dbt deps
dbt build
```

- `dbt deps` installs `dbt_utils`. This project's `package-lock.yml` is **not** changed by it.
- `dbt build` loads the seed CSVs, builds a snapshot and the models, and runs the tests. It takes about a minute.
- ✅ **Check:** the build ends with `Done. PASS=180 WARN=0 ERROR=0 SKIP=0 NO-OP=1 REUSED=0 TOTAL=181`.

## Step 5: Check the query tools

```bash
mf list metrics
```

✅ **Check:** it says `We've found 5 metrics.`

The query commands from SETUP.md Step 9 work the same way here, run from this folder.

## Step 6: Where the source files are

| What | Where |
| --- | --- |
| Metrics and semantic models | `models/semantic/semantic_models.yml` |
| Model SQL | `models/staging/` and `models/marts/` |
| Sample data | `seeds/*.csv` |
| The project's own documentation | `README.md`, `docs/` and `governance/`. You can use them. |
| Project tests | `tests/*.sql`. The file names describe what the author checks, and they are part of the project, so you can read them. |

The `output/` and `exports/` folders hold files the author generated. They're part of the pinned project, so you can read them.

---

## If something goes wrong

| Symptom | Likely cause and fix |
| --- | --- |
| A browser window opens, or `DATABRICKS`/`SNOWFLAKE` appears in an error | A non-default target was selected. Run the commands exactly as shown, without `--target`. |
| `Could not find profile named 'supply_chain_analytics'` | You're not in the project root folder. |
| Anything else | Email the coordinator the step number, the command and the full error text. |

**Don't edit any project file.**
