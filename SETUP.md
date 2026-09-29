# Setup: installing the tools and building the practice project

This takes about **30–45 minutes** the first time, most of it waiting for downloads. You do it once per project. Follow the steps in order.

At several points the guide gives a ✅ **Check** of what you should see. If your screen doesn't match a check, **stop** and email the coordinator (see the README's "Help" section).

Commands are shown for **macOS / Linux** (Terminal) and **Windows** (PowerShell). Type or paste one line at a time and press Enter. Lines starting with `#` are comments, so don't type them.

> The coordinator tested these steps on Linux. The macOS steps are the same as Linux. The Windows steps follow the official tools' documentation but weren't tested by the coordinator. If one fails, email the exact error.

---

## Step 1: Install Git

- **macOS:** open Terminal and run `git --version`. If macOS offers to install "command line developer tools", accept, wait for it to finish, then run `git --version` again.
- **Windows:** download and run the installer from <https://git-scm.com/download/win>. The default options are fine. Afterwards, open a **new** PowerShell window.
- **Linux:** `sudo apt install git` (Ubuntu/Debian) or your distribution's equivalent.

✅ **Check:** `git --version` prints something like `git version 2.4x.x`.

## Step 2: Install Python 3.12

dbt needs a specific Python version. Please use **3.12**.

- **macOS / Windows:** download "Python 3.12.x" from <https://www.python.org/downloads/> and run the installer.
  - **Windows:** on the first installer screen, **tick "Add python.exe to PATH"**.
- **Linux:** `sudo apt install python3.12 python3.12-venv`, or your distribution's equivalent.

✅ **Check:** open a **new** terminal window, then run:

```bash
# macOS / Linux
python3.12 --version
```
```powershell
# Windows
py -3.12 --version
```

It prints `Python 3.12.x`.

## Step 3: Make a work folder

```bash
# macOS / Linux
mkdir -p ~/metric-review && cd ~/metric-review
```
```powershell
# Windows
mkdir $HOME\metric-review; cd $HOME\metric-review
```

Every later step assumes you start in this folder.

## Step 4: Download the practice project at the exact version

The practice packet uses the public **Jaffle Shop** project at one fixed commit. The commit ID pins the files so that everyone sees exactly the same bytes.

```bash
git clone https://github.com/dbt-labs/jaffle-shop.git
cd jaffle-shop
git checkout 7be2c5838dbdeca8e915d4e46db70e910753d7f6
git log -1 --format=%H
```

These commands are the same on every system.

- Git may print a note about a "detached HEAD". That's expected and fine.
- ✅ **Check:** the last command prints exactly `7be2c5838dbdeca8e915d4e46db70e910753d7f6`.

**Stay inside the `jaffle-shop` folder for all remaining steps.**

## Step 5: Create an isolated Python environment and install dbt

This keeps the tools separate from anything else on your computer. The version numbers are fixed so that every reviewer gets identical results.

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

- The install takes a few minutes. A message saying a newer `pip` is available is harmless.
- After activation, your prompt starts with `(.venv)`.
- **Every time you open a new terminal later**, go back into the folder and re-activate before running anything:

  ```bash
  # macOS / Linux
  cd ~/metric-review/jaffle-shop && source .venv/bin/activate
  ```
  ```powershell
  # Windows
  cd $HOME\metric-review\jaffle-shop; .venv\Scripts\Activate.ps1
  ```

✅ **Check:** `dbt --version` shows `installed: 1.12.5`, and lists `duckdb: 1.11.0` under Plugins.

## Step 6: Tell dbt to use a local database file

dbt needs a *profile* saying where the data lives. You'll use **DuckDB**, a small database stored in a single file inside this folder. It needs no account or password.

In your text editor, create a new file called **`profiles.yml`** directly inside the `jaffle-shop` folder, next to `dbt_project.yml`. Paste exactly this into it:

```yaml
default:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: jaffle.duckdb
      threads: 1
```

Some details matter here:
- **Spaces, not tabs.** Keep the indentation exactly as shown.
- **Windows (Notepad):** choose "Save as type: All files" so it isn't saved as `profiles.yml.txt`.
- **Location:** the file must be in the project folder. The query tool in Step 9 won't find it in `~/.dbt/`.
- **Git:** this file is ignored by Git. That's expected.

## Step 7: Install the project's packages and load the sample data

```bash
dbt deps
dbt seed --full-refresh --vars "{load_source_data: true}"
```

These commands are the same on every system.

- `dbt deps` downloads helper packages. It may say "Update your versions in packages.yml". That is fine, so change nothing.
- `dbt deps` also rewrites `package-lock.yml` (`git status` then shows it as modified). This is expected, so don't undo it.
- `dbt seed` loads six CSV files of sample shop data into `jaffle.duckdb`.

✅ **Check:** the seed output ends with `Done. PASS=6 WARN=0 ERROR=0`.

## Step 8: Build the project

```bash
dbt build
```

This creates the project's tables and runs its data tests. It takes about a minute.

- Several yellow **deprecation** lines are normal. So is a warning mentioning `cumulative_revenue` and "OSI document".
- ✅ **Check:** the output ends with `Done. PASS=43 WARN=0 ERROR=0 SKIP=0 NO-OP=3`, with `TOTAL=46`.

## Step 9: Try the query tools

You now have three ways to look at metrics. Try each once so you know they work.

**a) List all metrics and their dimensions**

```bash
mf list metrics
mf list dimensions --metrics revenue
```

✅ **Check:** the first command says `We've found 19 metrics.`

**b) Get metric values**

```bash
# the overall total (no grouping)
mf query --metrics revenue

# by month
mf query --metrics revenue --group-by metric_time__month --order metric_time__month

# two metrics side by side, same grouping
mf query --metrics revenue,order_total --group-by metric_time__month --order metric_time__month
```

✅ **Check:** each prints a small table of numbers.

Some notes on these queries:
- **Grain.** `metric_time__month` means "group by the metric's own time dimension, at month grain". You can also use `metric_time__day` and `metric_time__year`.
- **Other dimensions.** To group by something else, use a name from `mf list dimensions`, e.g. `--group-by order_id__location__location_name`.
- **Months with no rows.** Some months may show an empty value where the metric has no rows.

**c) See the SQL a metric really runs**

```bash
mf query --metrics revenue --explain
mf query --metrics revenue --group-by metric_time__month --explain
```

This prints the generated SQL instead of values. It is often the quickest way to see a metric's filters and aggregation.

**d) (Optional) Your own SQL against the built tables**

```bash
dbt show --inline "select count(*) as n_orders from {{ ref('orders') }}"
```

✅ **Check:** it prints `61948`.

- **Windows PowerShell quoting:** if this quoting fails, use `dbt show --inline 'select count(*) as n_orders from {{ ref(\"orders\") }}'`, or skip this optional step.

## Step 10: Open the source files

You'll read the YAML and SQL files a lot. Any text editor works, e.g. [VS Code](https://code.visualstudio.com) (turn off its AI features, per the rules) or Notepad++. Open the `jaffle-shop` folder in the editor.

- **Metric declarations:** under `models/marts/*.yml`, in the `metrics:` sections.
- **Measures and semantic models:** in the same YAML files, under `semantic_models:`.
- **SQL:** each model's SQL is in `models/marts/<name>.sql` and `models/staging/<name>.sql`.

The packet also gives GitHub links to the exact lines at the pinned commit. They open in the browser and need no login.

---

## If something goes wrong

| Symptom | Likely cause and fix |
| --- | --- |
| `command not found: dbt` or `mf` | The environment isn't active. Re-run the activate line from Step 5. |
| `Could not find profile named 'default'` | `profiles.yml` is missing, misnamed (`.txt`), or not in the `jaffle-shop` folder (Step 6). |
| `python3.12: command not found` | Python 3.12 isn't installed or not on PATH (Step 2). Open a new terminal after installing. |
| Build shows `ERROR=` above 0 | Email the coordinator the last 30 lines of output. Don't change any project file. |
| Anything else | Stop and email the coordinator the step number, the command and the full error text. |

**Don't edit any project file** (`.yml`, `.sql`, `.csv`). The only file you create is `profiles.yml`. If you think you changed something by accident, run `git status` and tell the coordinator what it shows.

## Later projects

Each held-out packet names its project. **Set it up with its sheet in `setup/`.** Each sheet repeats Steps 4–9 with that project's own clone URL, commit, profile and check values. You only need Steps 1–3 of this page first.

| Project | Setup sheet | What is different |
| --- | --- | --- |
| homelab-data-platform | [setup/SETUP_homelab-data-platform.md](setup/SETUP_homelab-data-platform.md) | You generate the data with the project's own scripts first. You **must** set `PYTHONHASHSEED=0`. |
| revenue-intelligence | [setup/SETUP_revenue-intelligence.md](setup/SETUP_revenue-intelligence.md) | Written for Snowflake. Two helper scripts from `setup/tools/` load its own data into DuckDB and change 5 type names. |
| supply-chain-analytics-dbt | [setup/SETUP_supply-chain-analytics.md](setup/SETUP_supply-chain-analytics.md) | Ships its own data and local profile. It needs the fewest steps. |

These sheets were tested on Linux. The Windows commands haven't been tested yet: if one fails, email the coordinator.
