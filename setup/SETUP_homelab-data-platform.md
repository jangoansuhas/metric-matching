# Setup: homelab-data-platform

**Project:** <https://github.com/orbiane/homelab-data-platform>
**Pinned commit:** `5e8e25d7f79cb407402d7dd107a7694311bb9e9b`
**dbt project folder inside the repository:** `dbt_project/`

Before this sheet, finish Steps 1–3 of [SETUP.md](../SETUP.md): Git, Python 3.12 and the `metric-review` work folder. You don't need to repeat the Jaffle Shop steps. The ✅ checks work the same way: if your screen doesn't match one, stop and email the coordinator.

This project has no sample data in its repository. It includes Python scripts that **generate** the data, but they don't produce identical files on every run. So that every reviewer queries exactly the same data, **you'll copy one fixed snapshot of their output** from this reviewer repository instead of running them.

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

## Step 2: Locate the reviewer materials

In the commands below, **`<MATERIALS>`** is the folder where you downloaded or cloned this reviewer repository, e.g. `~/metric-review/metric-matching`. Replace `<MATERIALS>` with that path when you type the commands.

## Step 3: Copy the data snapshot

The snapshot is in this reviewer repository, in [`setup/data/homelab-data-platform/`](data/homelab-data-platform/). Its [NOTICE](data/homelab-data-platform/NOTICE.md) says how it was made. Copy its four CSV files into the project's `data_generation/output/` folder.

```bash
# macOS / Linux
mkdir -p data_generation/output
cp <MATERIALS>/setup/data/homelab-data-platform/*.csv data_generation/output/
cd data_generation/output
shasum -a 256 account_master.csv message_event.csv revenue_monthly.csv subscription_log.csv
cd ../..
```
```powershell
# Windows
mkdir data_generation\output -Force
Copy-Item <MATERIALS>\setup\data\homelab-data-platform\*.csv data_generation\output\
Get-FileHash data_generation\output\*.csv -Algorithm SHA256
```

✅ **Check:** the four hashes must be exactly:

| File | SHA-256 |
| --- | --- |
| `account_master.csv` | `8e67691cc583795300c8b72dc24b59c61fc3d85402071118f4da0906e678679e` |
| `message_event.csv` | `2a9b0283b8de5bd53ae57a88983e24f416a8f7432ad8ffccf726ff3ec84f85cc` |
| `revenue_monthly.csv` | `75152f3997390ae9105c05771bbc7c0155f006fecb5e8644157ed796e9ba35be` |
| `subscription_log.csv` | `00f8b32ae4e5acd102fe8ae17a9c5f047c082b7d27424c281400ed2fc4756261` |

**Don't run the project's generator scripts.** Their output would differ from the snapshot. You may read them (`data_generation/generators/`) to understand how the data was made.

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
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
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
| `No files found that match the pattern` or `…output/….csv` | Step 3 was skipped, the CSVs were copied to the wrong folder, or dbt was run from the wrong folder. Run it from `dbt_project` (Step 6). |
| `Could not find profile named 'dbt_project'` | `profiles.yml` is missing, misnamed, or not in `dbt_project/` (Step 5). |
| A snapshot hash doesn't match | The file was changed or incompletely copied. Copy it again from the reviewer repository (Step 3). |
| Anything else | Email the coordinator the step number, the command and the full error text. |

**Don't edit any project file.** You add only the four snapshot CSVs in `data_generation/output/`, `profiles.yml` and the dbt environment.
