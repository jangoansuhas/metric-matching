#!/usr/bin/env python3
"""Bounded, public-seed experiment for Jaffle Shop cumulative_revenue vs revenue.

Only the companion Markdown report is written in the workspace. The project,
profile, warehouse, MetricFlow CSVs, and logs live in a TemporaryDirectory.
The input manifests are the already verified parse artifacts of commit 7be2c58;
this program compiles fresh time-grain SQL with MetricFlow but does not run dbt.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "metric_matching_dev_build_20260928/source"
PROV = ROOT / "metric_provenance_verification"
SEEDS = SOURCE / "seeds/jaffle-data"
REPORT = Path(__file__).with_name("experiment_cumulative_revenue_report.md")
PYTHON_ENV = ROOT / "metric_matching_dev_build_20260928/venv/bin"
COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
FIRST = "2024-09-01"
LAST = "2025-08-31"

# Fixed expectations for the previously archived public commit. Checking these
# before opening any CSV or compiling SQL prevents a modified local copy from
# silently inheriting the commit claim in the report.
EXPECTED_SOURCE_HASHES = {
    "dbt_project.yml": "f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122",
    "models/marts/order_items.yml": "81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97",
    "models/marts/order_items.sql": "7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639",
    "models/marts/metricflow_time_spine.sql": "1e8de1247e68fe0f70de20000d0ae5d7ebb60b1e3c56202d233ea96cb8429ecf",
    "models/staging/stg_order_items.sql": "102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04",
    "models/staging/stg_orders.sql": "9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327",
    "models/staging/stg_products.sql": "062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6",
    "models/staging/stg_supplies.sql": "1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4",
    "macros/cents_to_dollars.sql": "5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb",
}
EXPECTED_SEED_HASHES = {
    "raw_orders": "e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b",
    "raw_items": "bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca",
    "raw_products": "01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d",
    "raw_supplies": "309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1",
}

# The relevant columns/joins from stg_order_items, stg_orders, stg_products,
# stg_supplies and marts/order_items.sql. This is DIRECT SQL RECONSTRUCTION,
# not a dbt-built relation. The grouped measure uses only date and price.
MODEL_SQL = """CREATE TABLE order_items AS
WITH order_supplies_summary AS (
  SELECT sku AS product_id, SUM((cost / 100)::NUMERIC(16,2)) AS supply_cost
  FROM read_csv_auto(?) GROUP BY sku
)
SELECT i.id AS order_item_id, i.order_id, i.sku AS product_id,
       DATE_TRUNC('day', o.ordered_at) AS ordered_at,
       p.name AS product_name,
       (p.price / 100)::NUMERIC(16,2) AS product_price,
       COALESCE(p.type = 'jaffle', FALSE) AS is_food_item,
       COALESCE(p.type = 'beverage', FALSE) AS is_drink_item,
       s.supply_cost
FROM read_csv_auto(?) i
LEFT JOIN read_csv_auto(?) o ON i.order_id = o.id
LEFT JOIN read_csv_auto(?) p ON i.sku = p.sku
LEFT JOIN order_supplies_summary s ON i.sku = s.product_id"""

# Exact daily slice needed by the two bounded MetricFlow queries. This is a
# reconstructed time spine, not the dbt_date-built project time spine.
SPINE_SQL = """CREATE TABLE metricflow_time_spine AS
SELECT CAST(date_day AS DATE) AS date_day
FROM generate_series(DATE '2024-09-01', DATE '2025-08-31', INTERVAL 1 DAY)
  AS days(date_day)"""

CONTROL_SQL = """WITH months AS (
  SELECT DATE_TRUNC('month', ordered_at) AS month,
         COUNT(*) AS item_count, SUM(product_price) AS revenue
  FROM order_items GROUP BY 1
)
SELECT m.month, m.item_count, m.revenue,
       (SELECT SUM(product_price) FROM order_items o
        WHERE o.ordered_at <= m.month) AS first_day_running,
       (SELECT SUM(product_price) FROM order_items o
        WHERE o.ordered_at < m.month + INTERVAL 1 month) AS month_end_running,
       (SELECT SUM(product_price) FROM order_items o
        WHERE o.ordered_at = m.month) AS first_day_revenue,
       (SELECT COUNT(*) FROM order_items o
        WHERE o.ordered_at = m.month) AS first_day_item_count
FROM months m ORDER BY m.month"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def assert_hash(path: Path, expected: str) -> None:
    actual = sha(path)
    if actual != expected:
        raise AssertionError(f"Input changed: {path}: {actual} != {expected}")


def money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def run_mf(cmd: list[str], project: Path, env: dict[str, str]) -> str:
    result = subprocess.run(cmd, cwd=project, env=env, capture_output=True,
                            text=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"{cmd!r} exited {result.returncode}:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def explain(metric: str, grouped: bool, project: Path, env: dict[str, str]) -> str:
    cmd = ["mf", "query", "--metrics", metric]
    if grouped:
        cmd += ["--group-by", "metric_time__month", "--start-time", FIRST,
                "--end-time", LAST]
    stdout = run_mf(cmd + ["--explain"], project, env)
    # The CLI prints a status display followed by exactly one SQL statement.
    marker = "\nSELECT\n"
    if stdout.count(marker) != 1:
        raise AssertionError(f"Could not isolate generated SQL: {stdout}")
    return "SELECT\n" + stdout.split(marker, 1)[1].rstrip() + "\n"


def mf_csv(metric: str, grouped: bool, project: Path,
           env: dict[str, str], output: Path) -> list[dict[str, str]]:
    cmd = ["mf", "query", "--metrics", metric]
    if grouped:
        cmd += ["--group-by", "metric_time__month", "--start-time", FIRST,
                "--end-time", LAST]
    run_mf(cmd + ["--csv", str(output)], project, env)
    with output.open(newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    metadata = json.loads((PROV / "run_metadata.json").read_text())
    assert metadata["commit"] == COMMIT
    assert metadata["archive_tar_sha256"] == "7af864659e9b579296bba0766181ec7dc155c00fc05aba267bda28a1b9f3e88e"
    for name, expected in EXPECTED_SOURCE_HASHES.items():
        assert_hash(SOURCE / name, expected)
    for name, expected in EXPECTED_SEED_HASHES.items():
        assert_hash(SEEDS / f"{name}.csv", expected)
    assert_hash(PROV / "manifests/manifest.json", "8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42")
    assert_hash(PROV / "manifests/semantic_manifest.json", "bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51")
    semantic = json.loads((PROV / "manifests/semantic_manifest.json").read_text())
    metrics = {x["name"]: x for x in semantic["metrics"]}
    assert metrics["revenue"]["type"] == "simple"
    assert metrics["cumulative_revenue"]["type"] == "cumulative"
    assert all(metrics[x]["type_params"]["measure"]["name"] == "revenue"
               for x in ("revenue", "cumulative_revenue"))
    assert any(s["name"] == "order_item" and
               any(m["name"] == "revenue" and m["agg"] == "sum" and
                   m["expr"] == "product_price" for m in s["measures"])
               for s in semantic["semantic_models"])

    seed_names = tuple(EXPECTED_SEED_HASHES)
    seed_hashes = {name: sha(SEEDS / f"{name}.csv") for name in seed_names}
    seed_counts: dict[str, int] = {}

    with tempfile.TemporaryDirectory(prefix="jaffle_cumulative_", dir="/tmp") as tmp:
        temp = Path(tmp)
        project = temp / "project"
        profile = temp / "profiles"
        (project / "target").mkdir(parents=True)
        profile.mkdir()
        shutil.copyfile(SOURCE / "dbt_project.yml", project / "dbt_project.yml")
        for name in ("manifest.json", "semantic_manifest.json"):
            shutil.copyfile(PROV / "manifests" / name, project / "target" / name)
        db = temp / "dev.duckdb"  # makes DuckDB catalog "dev"
        (profile / "profiles.yml").write_text(
            "default:\n  target: dev\n  outputs:\n    dev:\n"
            f"      type: duckdb\n      path: {db}\n      schema: main\n      threads: 1\n")
        env = {"HOME": str(temp), "PATH": f"{PYTHON_ENV}:/usr/bin:/bin",
               "LANG": "C.UTF-8", "DBT_PROFILES_DIR": str(profile),
               "DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DO_NOT_TRACK": "1"}

        con = duckdb.connect(str(db))
        for name in seed_names:
            seed_counts[name] = con.execute("SELECT COUNT(*) FROM read_csv_auto(?)",
                                            [str(SEEDS / f"{name}.csv")]).fetchone()[0]
        con.execute(MODEL_SQL, [str(SEEDS / f"{name}.csv") for name in
                                ("raw_supplies", "raw_items", "raw_orders", "raw_products")])
        con.execute(SPINE_SQL)
        row_count, unique_count, null_count, total = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT order_item_id), "
            "COUNT(*) FILTER (WHERE ordered_at IS NULL OR product_price IS NULL), "
            "SUM(product_price) FROM order_items").fetchone()
        spine_count = con.execute("SELECT COUNT(*) FROM metricflow_time_spine").fetchone()[0]
        assert (row_count, unique_count, null_count, spine_count) == (90900, 90900, 0, 365)
        assert money(total) == Decimal("637444.00")
        control = con.execute(CONTROL_SQL).fetchall()
        assert len(control) == 12 and sum(row[1] for row in control) == row_count
        assert [str(row[0])[:7] for row in control] == [
            "2024-09", "2024-10", "2024-11", "2024-12", "2025-01", "2025-02",
            "2025-03", "2025-04", "2025-05", "2025-06", "2025-07", "2025-08"]
        assert all(row[6] > 0 for row in control), "A month start has no order items"
        con.close()  # MetricFlow opens the same DuckDB file in another process.

        sql: dict[tuple[str, bool], str] = {}
        mf_rows: dict[tuple[str, bool], list[dict[str, str]]] = {}
        for grouped in (False, True):
            for metric in ("revenue", "cumulative_revenue"):
                sql[metric, grouped] = explain(metric, grouped, project, env)
                mf_rows[metric, grouped] = mf_csv(
                    metric, grouped, project, env,
                    temp / (metric + ("_month" if grouped else "_scalar") + ".csv"))

        # The two scalar queries have the same operation after alias removal.
        assert sql["revenue", False].replace(" AS revenue\n", " AS value\n") == \
               sql["cumulative_revenue", False].replace(" AS cumulative_revenue\n", " AS value\n")
        for metric in ("revenue", "cumulative_revenue"):
            archived = (PROV / "generated_sql" / f"{metric}.sql").read_text()
            assert sql[metric, False] == archived, (repr(sql[metric, False]), repr(archived))
            assert len(mf_rows[metric, False]) == 1
            assert money(mf_rows[metric, False][0][metric]) == money(total)

        # Execute each fresh MetricFlow-compiled statement independently in DuckDB,
        # then compare against the actual mf CLI output and a separate direct control.
        con = duckdb.connect(str(db), read_only=True)
        actual: dict[str, dict[str, Decimal]] = {}
        for metric in ("revenue", "cumulative_revenue"):
            fetched = con.execute(sql[metric, True]).fetchall()
            actual[metric] = {str(row[0])[:10]: money(row[1]) for row in fetched}
            cli = {row["metric_time__month"][:10]: money(row[metric])
                   for row in mf_rows[metric, True]}
            assert len(fetched) == len(cli) == len(actual[metric]) == 12
            assert cli == actual[metric], (metric, cli, actual[metric])
        for month, count, revenue, first_day, month_end, first_day_revenue, first_day_count in control:
            key = str(month)[:10]
            assert actual["revenue"][key] == money(revenue)
            assert actual["cumulative_revenue"][key] == money(first_day)
        con.close()

    def dollars(value: object) -> str:
        return f"${money(value):,.2f}"

    table = "| Month | Item rows | Month-start items | Revenue | MetricFlow cumulative | Direct end-of-month control |\n|---|---:|---:|---:|---:|---:|\n"
    for month, count, revenue, first_day, month_end, _, first_day_count in control:
        table += (f"| {str(month)[:7]} | {count:,} | {first_day_count:,} | {dollars(revenue)} | "
                  f"{dollars(actual['cumulative_revenue'][str(month)[:10]])} | "
                  f"{dollars(month_end)} |\n")
    october = next(row for row in control if str(row[0])[:7] == "2024-10")
    september = next(row for row in control if str(row[0])[:7] == "2024-09")
    assert money(september[2]) + money(october[5]) == money(october[3])
    assert money(september[2]) + money(october[2]) == money(october[4])
    assert money(october[2]) != money(october[3]) != money(october[4])

    seed_table = "| CSV | Rows | SHA-256 |\n|---|---:|---|\n"
    for name in seed_names:
        seed_table += f"| `{name}.csv` | {seed_counts[name]:,} | `{seed_hashes[name]}` |\n"
    source_table = "| Pinned source file | Expected and verified SHA-256 |\n|---|---|\n"
    for name, expected in EXPECTED_SOURCE_HASHES.items():
        source_table += f"| `{name}` | `{expected}` |\n"
    hash_table = "| SQL (MetricFlow) | SHA-256, UTF-8 with terminal newline |\n|---|---|\n"
    for grouped in (False, True):
        for metric in ("revenue", "cumulative_revenue"):
            label = "bounded month" if grouped else "ungrouped"
            hash_table += f"| `{metric}` {label} | `{sql_hash(sql[metric, grouped])}` |\n"

    report = f"""# Jaffle Shop: `cumulative_revenue` and `revenue` (bounded development experiment)

## Source and method

- Public source: `dbt-labs/jaffle-shop` commit `{COMMIT}`. The existing provenance run archived this commit (tar SHA-256 `{metadata['archive_tar_sha256']}`). This script checks its `run_metadata.json` and **asserts** fixed expected hashes for every source file used in the reconstruction and all four seed CSVs before building or compiling. These expected values pin the previously archived local copy; this run does not independently call Git HEAD, `git archive`, or `dbt parse`.
- `models/marts/order_items.yml` SHA-256 `{sha(SOURCE / 'models/marts/order_items.yml')}`: lines 71–74 declare measure `revenue`, aggregation `sum`, expression `product_price`; lines 90–95 declare simple metric `revenue` over that measure; lines 162–167 declare cumulative metric `cumulative_revenue` over the **same** measure with no window or grain-to-date parameter. The `order_item` semantic model uses `ordered_at` as its aggregation time dimension. The checked semantic manifest agrees.
- Parsed `manifest.json` SHA-256 `{sha(PROV / 'manifests/manifest.json')}`; `semantic_manifest.json` SHA-256 `{sha(PROV / 'manifests/semantic_manifest.json')}`. These are the prior clean, same-commit parse artifacts, loaded into a temporary project for **new** MetricFlow compilation. `dbt_project.yml` SHA-256 `{sha(SOURCE / 'dbt_project.yml')}`.
- Runtime: local `dbt-metricflow 0.15.0` / `metricflow 0.213.0` and DuckDB `{duckdb.__version__}`. Query bounds (inclusive): `{FIRST}` through `{LAST}`; `--group-by metric_time__month`. No external warehouse, held-out input, worksheet, relationship label, or human gold was used.

Pinned source hashes (all asserted before execution):

{source_table}

### Public seed inputs

All four CSV hashes below are compared against fixed expected values before any seed is read:

{seed_table}
The temporary `order_items` has {row_count:,} unique item rows, no missing date or price, and a sum of {dollars(total)}. The daily spine slice contains {spine_count} days. Both are **direct SQL reconstructions**, not a `dbt seed`/`dbt run` build. The original `metricflow_time_spine.sql` calls `dbt_date.get_base_dates(n_dateparts=365*10, datepart='day')`; its materialized contents were not used here. The explicit slice covers every date selected by the bounded compiled SQL.

Reconstruction SQL (`?` parameters in order: `raw_supplies`, `raw_items`, `raw_orders`, `raw_products`):

```sql
{MODEL_SQL}
```

Time spine slice:

```sql
{SPINE_SQL}
```

## Generated and executed SQL

`mf query --metrics <name> --explain` compiled both scalar queries. The regenerated SQL equals the previously archived `generated_sql/{{revenue,cumulative_revenue}}.sql` byte for byte. Ignoring only the output alias, both are `SUM(product_price)` over `"dev"."main"."order_items"`. Each executed to **{dollars(total)}**, verified via MetricFlow CLI CSV and the direct model sum.

```sql
{sql['revenue', False].strip()}
```

```sql
{sql['cumulative_revenue', False].strip()}
```

For the time-grain queries, the program issued `mf query --metrics <name> --group-by metric_time__month --start-time {FIRST} --end-time {LAST} --explain`, then the same calls without `--explain` and with `--csv` into the temporary directory. It also executed each extracted SQL statement directly in DuckDB. The CLI CSV and direct execution agree by month, and the results agree with a separate seed-model control query.

{hash_table}
Bounded **revenue** SQL, emitted by MetricFlow:

```sql
{sql['revenue', True].strip()}
```

Bounded **cumulative_revenue** SQL, emitted by MetricFlow:

```sql
{sql['cumulative_revenue', True].strip()}
```

## Results (12 months per query)

{table}
Every one of the 12 month-start dates has item rows in the reconstructed model (minimum {min(row[6] for row in control)}; the table gives each count). The explicit assertion makes the first-calendar-day reading below valid for this bounded seed run.

Independent control query over the reconstructed item relation (the month-end column is a direct reference value, not a MetricFlow metric):

```sql
{CONTROL_SQL}
```

The `MetricFlow cumulative` column takes `FIRST_VALUE` by day within each month after summing all item prices on or before that day. For this bounded daily spine it is **the running total through the first calendar day of each month**, including that day's items. It is neither that month's revenue nor the month-end cumulative sum.

Concrete counterexample, October 2024: September revenue is {dollars(september[2])}; October 1 adds {dollars(october[5])}, giving the MetricFlow October cumulative value **{dollars(october[3])}**. October's own revenue is **{dollars(october[2])}**. The direct end-of-October running total is **{dollars(october[4])}**. Scalar equality ({dollars(total)} for both metrics) therefore does not imply equality at month grain.

## Interpretation boundary and reproduction

The SQL marked MetricFlow above was genuinely compiled from the prior pinned manifest and executed both by `mf query` and directly. The `order_items` and time-spine relations were reconstructed from public CSVs and a bounded date series; a fresh dbt dependency installation, seed load, model build, and original ten-year time-spine materialization were **not tested**. The observed month values are conditional on those reconstructions and this inclusive date window. They are a within-project counterexample to treating ungrouped SQL identity as all-grain identity; they establish no matching gold label, model superiority, or cross-project result.

Reproduce from the workspace root with `metric_matching_dev_build_20260928/venv/bin/python metric_matching_pilot/experiment_cumulative_revenue.py`. The script asserts the fixed source, seed, and manifest hashes, checks all month-start item counts, compiles four MetricFlow statements, executes four MetricFlow queries, directly executes the two month statements, checks the control totals, and rewrites only this report in the workspace. Script SHA-256 `{sha(Path(__file__))}`. The temporary project and database are removed on exit.
"""
    REPORT.write_text(report)
    print(f"Wrote {REPORT}; scalar {dollars(total)}, {len(control)} months, "
          f"October {dollars(october[2])} vs {dollars(october[3])}")


if __name__ == "__main__":
    main()
