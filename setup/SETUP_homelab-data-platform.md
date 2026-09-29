# Setup: homelab-data-platform

**Project:** <https://github.com/orbiane/homelab-data-platform>
**Pinned commit:** `5e8e25d7f79cb407402d7dd107a7694311bb9e9b`
**dbt project folder inside the repository:** `dbt_project/`

Before this sheet, finish Steps 1–3 of [SETUP.md](../SETUP.md): Git, Python 3.12 and the `metric-review` work folder. You don't need to repeat the Jaffle Shop steps. The ✅ checks work the same way: if your screen doesn't match one, stop and email the coordinator.

This project has no sample data in the repository. Instead, it includes small Python scripts that **generate** the data. You'll run them once, in Step 3, before building.

---

## Step 1: Download the project at the exact version

```bash
cd ~/metric-review          # Windows: cd $HOME\metric-review
git clone https://github.com/orbiane/homelab-data-platform.git
cd homelab-data-platform
git checkout 5e8e25d7f79cb407402d7dd107a7694311bb9e9b
git log -1 --format=%H
```

✅ **Check:** the last command prints exactly `5e8e25d7f79cb407402d7dd107a7694311bb9e9b`.

**Stay inside the `homelab-data-platform` folder** unless a step says otherwise.

## Step 2: Create the data-generation environment

This is a separate environment used only to make the data.

```bash
# macOS / Linux
python3.12 -m venv .venv-data
source .venv-data/bin/activate
pip install "faker==40.13.0" "pandas==3.0.2" "numpy==2.4.4"
```
```powershell
# Windows
py -3.12 -m venv .venv-data
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv-data\Scripts\Activate.ps1
pip install "faker==40.13.0" "pandas==3.0.2" "numpy==2.4.4"
```

The project's own README uses `uv`. These are the same versions its `uv.lock` pins, installed with `pip`.

## Step 3: Generate the data

**Run the four scripts in this order**, because the later ones read the first one's output. The `PYTHONHASHSEED=0` line matters: without it, one of the scripts produces different numbers on every run, and two reviewers would see different values.

```bash
# macOS / Linux
cd data_generation
mkdir -p output
export PYTHONHASHSEED=0
python -m generators.account_master
python -m generators.subscription
python -m generators.message_event
python -m generators.revenue_monthly
```
```powershell
# Windows
cd data_generation
mkdir output -Force
$env:PYTHONHASHSEED = "0"
python -m generators.account_master
python -m generators.subscription
python -m generators.message_event
python -m generators.revenue_monthly
```

Each script prints a line starting `Generated … records`. Some also print short summaries of the data; ignore them.

✅ **Check:** compute the SHA-256 of two of the files:

```bash
# macOS / Linux
shasum -a 256 output/account_master.csv output/revenue_monthly.csv
```
```powershell
# Windows
Get-FileHash output\account_master.csv, output\revenue_monthly.csv -Algorithm SHA256
```

They must be:

| File | SHA-256 |
| --- | --- |
| `account_master.csv` | `8e67691cc583795300c8b72dc24b59c61fc3d85402071118f4da0906e678679e` |
| `revenue_monthly.csv` | `75152f3997390ae9105c05771bbc7c0155f006fecb5e8644157ed796e9ba35be` |

If `revenue_monthly.csv` differs, `PYTHONHASHSEED` wasn't set in that terminal. Set it, rerun the four scripts, and check again.

The other two files, `subscription_log.csv` and `message_event.csv`, have a **different SHA-256 on every run**, because they contain randomly generated event IDs. That is expected.

Then go back to the project folder and leave this environment:

```bash
cd ..
deactivate
```

## Step 4: Create the dbt environment

This is the same as SETUP.md Step 5, but inside this project's folder:

```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```
```powershell
# Windows
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install "dbt-core==1.12.5" "dbt-duckdb==1.11.0" "dbt-metricflow==0.15.0"
```

The project's README names older dbt versions. The study uses the same pinned versions for every project.

✅ **Check:** `dbt --version` shows `installed: 1.12.5`, and lists `duckdb: 1.11.0` under Plugins.

**Every time you open a new terminal later**, run:
- macOS / Linux: `cd ~/metric-review/homelab-data-platform/dbt_project && source ../.venv/bin/activate`
- Windows: `cd $HOME\metric-review\homelab-data-platform\dbt_project; ..\.venv\Scripts\Activate.ps1`

## Step 5: Tell dbt to use a local database file

Create a new file called **`profiles.yml`** inside the **`dbt_project`** folder, next to that folder's `dbt_project.yml`. Paste exactly this:

```yaml
dbt_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: warehouse.duckdb
      threads: 1
```

Use spaces, not tabs. On Windows, make sure Notepad doesn't save it as `profiles.yml.txt`.

## Step 6: Build the project

**Run dbt from inside `dbt_project`.** The project finds the generated files by a path relative to that folder.

```bash
cd dbt_project
dbt build
```

This project has no packages, so there is no `dbt deps` step.

- ✅ **Check:** the output ends with `Done. PASS=13 WARN=3 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=16`.
- The **3 warnings** come from the project's own data-quality tests, which the project was written to trigger. They're expected.

## Step 7: Check the query tools

Stay in `dbt_project`:

```bash
mf list metrics
```

✅ **Check:** it says `We've found 5 metrics.`

The query commands from SETUP.md Step 9 (`mf query`, `--explain` and `dbt show`) work the same way here. Run them from `dbt_project`.

## Step 8: Where the source files are

| What | Where |
| --- | --- |
| Metrics and semantic models | `dbt_project/models/mart/` (`_metrics.yml` and `_semantic_models.yml`) |
| Model SQL | `dbt_project/models/mart/*.sql` and `dbt_project/models/staging/*.sql` |
| Sources | `dbt_project/models/staging/_sources.yml` |
| The author's design notes | `docs/decisions/`. These are part of the project's own documentation, so you can use them. |
| How the data is made | `data_generation/generators/`. Also part of the project, so you can read it. |

---

## If something goes wrong

| Symptom | Likely cause and fix |
| --- | --- |
| `No files found that match the pattern` or `…output/….csv` | Step 3 was skipped, or dbt was run from the wrong folder. Run it from `dbt_project` (Step 6). |
| `Could not find profile named 'dbt_project'` | `profiles.yml` is missing, misnamed, or not in `dbt_project/` (Step 5). |
| `revenue_monthly.csv` hash doesn't match | `PYTHONHASHSEED` wasn't set (Step 3). |
| Anything else | Email the coordinator the step number, the command and the full error text. |

**Don't edit any project file.** You create only the `output/` CSVs, `profiles.yml` and the two environments.
