# Setup: AI-Augmented Executive Revenue Intelligence Platform

**Project:** <https://github.com/rohitndev/AI-Augmented-Executive--Revenue-Intelligence-Platform>
**Pinned commit:** `36ea21e4cf795bfe2ea437120109048a601d3daa`
**dbt project folder inside the repository:** `dbt/`

Before this sheet, finish Steps 1–3 of [SETUP.md](../SETUP.md): Git, Python 3.12 and the `metric-review` work folder. The ✅ checks work the same way: if your screen doesn't match one, stop and email the coordinator.

**This project is written for Snowflake, a cloud warehouse.** To run it on your laptop without any account, you use two small helper scripts from **this reviewer repository**, in `setup/tools/`:

1. **`load_revenue_intelligence_duckdb.py`** runs the project's **own** data generator and puts the tables into a local DuckDB file, where the project's Snowflake loader would put them.
2. **`patch_revenue_intelligence_duckdb.py`** changes one Snowflake type name that DuckDB doesn't know. `number(12, 2)` becomes `decimal(12, 2)`, which means exactly the same thing in Snowflake. **This touches 5 lines in 4 files, and nothing else.**

**Reading rule for this project:** your local copy has those 5 lines changed. For what a metric *means*, always use the **pinned, unchanged files**, meaning the GitHub links in your packet. Use your local build only for running queries.

In the commands below, **`<MATERIALS>`** is the folder where you downloaded or cloned this reviewer repository, e.g. `~/metric-review/metric-matching`.

---

## Step 1: Download the project at the exact version

```bash
cd ~/metric-review          # Windows: cd $HOME\metric-review
git clone https://github.com/rohitndev/AI-Augmented-Executive--Revenue-Intelligence-Platform.git revenue-intelligence
cd revenue-intelligence
git checkout 36ea21e4cf795bfe2ea437120109048a601d3daa
git log -1 --format=%H
```

✅ **Check:** the last command prints exactly `36ea21e4cf795bfe2ea437120109048a601d3daa`.

**Stay inside the `revenue-intelligence` folder** unless a step says otherwise.

## Step 2: Create the data environment

```bash
# macOS / Linux
python3.12 -m venv .venv-data
source .venv-data/bin/activate
pip install "pandas==3.0.3" "numpy==2.4.6" "duckdb==1.5.6"
```
```powershell
# Windows
py -3.12 -m venv .venv-data
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv-data\Scripts\Activate.ps1
pip install "pandas==3.0.3" "numpy==2.4.6" "duckdb==1.5.6"
```

The `pandas` and `numpy` versions are the ones in the project's `requirements.txt`. The `duckdb` version matches the one dbt uses.

## Step 3: Load the data and apply the type patch

Run both commands from the `revenue-intelligence` folder:

```bash
python <MATERIALS>/setup/tools/load_revenue_intelligence_duckdb.py dbt/revenue_intelligence.duckdb
python <MATERIALS>/setup/tools/patch_revenue_intelligence_duckdb.py
```

On Windows, use backslashes in the paths: `python <MATERIALS>\setup\tools\load_revenue_intelligence_duckdb.py dbt\revenue_intelligence.duckdb`.

✅ **Check 1:** the first command prints these 5 lines:

```
loaded RAW.CUSTOMERS
loaded RAW.SUBSCRIPTIONS
loaded RAW.INVOICES
loaded RAW.OPPORTUNITIES
defined macro to_date
```

✅ **Check 2:** the second command prints each changed line, then ends with `5 line(s) changed`.

✅ **Check 3:** `git status --short` lists **exactly** these four modified files and nothing else modified:
- `dbt/models/staging/stg_customers.sql`
- `dbt/models/staging/stg_invoices.sql`
- `dbt/models/staging/stg_opportunities.sql`
- `dbt/models/staging/stg_subscriptions.sql`

`git diff` shows the 5 changed lines.

Only run the patch **once**. If you run it again, it prints `0 line(s) changed`, which is harmless.

Then leave the data environment:

```bash
deactivate
```

## Step 4: Create the dbt environment

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```
```powershell
# Windows
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # allows the next line, for this window only
.venv\Scripts\Activate.ps1
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```

✅ **Check:** `dbt --version` shows `installed: 1.12.5`, and lists `duckdb: 1.11.0` under Plugins.

## Step 5: Tell dbt to use the local database file

The project already contains a `dbt/profiles.yml`, but it is for Snowflake. **Don't edit it.** Instead:

1. Create a **separate** folder for your profile:
   - macOS / Linux: `mkdir -p ~/metric-review/profiles-revenue-intelligence`
   - Windows: `mkdir $HOME\metric-review\profiles-revenue-intelligence`
2. In that folder, create **`profiles.yml`** containing exactly:

   ```yaml
   revenue_intelligence:
     target: dev
     outputs:
       dev:
         type: duckdb
         path: revenue_intelligence.duckdb
         threads: 1
   ```

**Every time you open a new terminal**, activate the environment and point dbt at that folder:

```bash
# macOS / Linux
cd ~/metric-review/revenue-intelligence/dbt && source ../.venv/bin/activate
export DBT_PROFILES_DIR=~/metric-review/profiles-revenue-intelligence
```
```powershell
# Windows
cd $HOME\metric-review\revenue-intelligence\dbt; ..\.venv\Scripts\Activate.ps1
$env:DBT_PROFILES_DIR = "$HOME\metric-review\profiles-revenue-intelligence"
```

Run those lines now too.

## Step 6: Build the project

Run from inside `dbt/`, which is where the previous step leaves you:

```bash
dbt deps
dbt build
```

- `dbt deps` installs one helper package (`dbt_utils`).
- ✅ **Check:** the build ends with `Done. PASS=40 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=40`.
- Yellow deprecation lines are normal.

## Step 7: Check the query tools

```bash
mf list metrics
```

✅ **Check:** it says `We've found 10 metrics.`

The query commands from SETUP.md Step 9 work the same way here. Run them from `dbt/`, with `DBT_PROFILES_DIR` set.

## Step 8: Where the source files are

| What | Where |
| --- | --- |
| Metrics | `dbt/models/semantic/metrics.yml` |
| Semantic models | `dbt/models/semantic/semantic_models.yml` |
| Model SQL | `dbt/models/staging/`, `dbt/models/intermediate/` and `dbt/models/marts/` |
| How the data is made | `src/ingestion/sample_data.py`. It is part of the project, so you can read it. |
| Other documentation | The project also has an app layer (`src/semantic/`, `api/`, `docs/`). Its catalog files are project documentation, so you can read them. The metric definitions you label are the dbt ones listed above. |

Remember the reading rule: use the **pinned GitHub files** for meaning. Five lines in your local copy were changed so it can build.

---

## If something goes wrong

| Symptom | Likely cause and fix |
| --- | --- |
| `Type with name number does not exist` | The patch in Step 3 wasn't applied. |
| `Table with name CUSTOMERS does not exist` or similar | The loader in Step 3 wasn't run, or it wrote to a different file. It must be `dbt/revenue_intelligence.duckdb`. |
| `Could not find profile named 'revenue_intelligence'`, or an error mentioning Snowflake or `SNOWFLAKE_ACCOUNT` | `DBT_PROFILES_DIR` isn't set in this terminal (Step 5). |
| `No module named 'src'` | The loader was run from the wrong folder. Run it from `revenue-intelligence`, not from `dbt/`. |
| Anything else | Email the coordinator the step number, the command and the full error text. |

**Don't edit any project file yourself.** The patch script makes the only allowed change.
