#!/usr/bin/env python3
"""Compile and execute three day-grouped Jaffle Shop metrics on pinned public seeds.

Writes only probe_grouped_scope_report.md in the workspace. The profile, project,
CSV query outputs, and DuckDB database are created under /tmp and removed on exit.
This reuses the previously archived same-commit manifests; it does not run dbt.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import date
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "public_corpus/jaffle-shop-sidemantic/jaffle-shop"
PROV = ROOT / "metric_provenance_verification"
REPORT = Path(__file__).with_name("probe_grouped_scope_report.md")
VENV_BIN = ROOT / "metric_matching_dev_build_20260928/venv/bin"
COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
ARCHIVE_SHA = "7af864659e9b579296bba0766181ec7dc155c00fc05aba267bda28a1b9f3e88e"
METRICS = ("revenue", "food_revenue", "drink_revenue")

SOURCE_HASHES = {
    "dbt_project.yml": "f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122",
    "models/marts/order_items.yml": "81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97",
    "models/marts/order_items.sql": "7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639",
    "models/staging/stg_order_items.sql": "102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04",
    "models/staging/stg_orders.sql": "9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327",
    "models/staging/stg_products.sql": "062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6",
    "macros/cents_to_dollars.sql": "5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb",
    "seeds/jaffle-data/raw_items.csv": "bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca",
    "seeds/jaffle-data/raw_orders.csv": "e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b",
    "seeds/jaffle-data/raw_products.csv": "01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d",
}
PROV_HASHES = {
    "manifests/manifest.json": "8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42",
    "manifests/semantic_manifest.json": "bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51",
    "generated_sql/revenue.sql": "eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134",
    "generated_sql/food_revenue.sql": "682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110",
    "generated_sql/drink_revenue.sql": "3e1d04e6f6a6ac412fdab159503b76feb0ae180b59f8a63900c293e0bf09d613",
}

# Selected pinned staging/mart columns. Compute flags inside stg_products,
# BEFORE the mart's left join: an absent product has NULL mart flags, although
# a present product with NULL type has FALSE staging flags. The mart's supply
# subquery is grouped to one row per product and contributes no column used by
# these three measures. This is a reconstruction, not a fresh dbt model build.
STG_PRODUCTS_SQL = """CREATE TABLE stg_products AS
SELECT sku AS product_id,
       (CAST(price AS BIGINT) / 100)::NUMERIC(16,2) AS product_price,
       COALESCE(type = 'jaffle', FALSE) AS is_food_item,
       COALESCE(type = 'beverage', FALSE) AS is_drink_item
FROM raw_products"""

MODEL_SQL = """CREATE TABLE order_items AS
SELECT i.id AS order_item_id, i.order_id, i.sku AS product_id,
       DATE_TRUNC('day', CAST(o.ordered_at AS TIMESTAMP)) AS ordered_at,
       p.product_price, p.is_food_item, p.is_drink_item
FROM raw_items i
LEFT JOIN raw_orders o ON i.order_id = o.id
LEFT JOIN stg_products p ON i.sku = p.product_id"""

# Independent raw-cent control: it does not aggregate the reconstructed mart.
# The CASE/ELSE 0 matches the three manifest measure expressions, including
# NULL product and flag behavior. Conversion happens after integer summation.
CONTROL_SQL = """SELECT CAST(DATE_TRUNC('day', CAST(o.ordered_at AS TIMESTAMP)) AS DATE) AS day,
       COUNT(*) AS item_rows,
       SUM(CAST(p.price AS BIGINT)) AS revenue_cents,
       SUM(CASE WHEN p.type = 'jaffle' THEN CAST(p.price AS BIGINT) ELSE 0 END) AS food_cents,
       SUM(CASE WHEN p.type = 'beverage' THEN CAST(p.price AS BIGINT) ELSE 0 END) AS drink_cents
FROM raw_items i
LEFT JOIN raw_orders o ON i.order_id = o.id
LEFT JOIN raw_products p ON i.sku = p.sku
GROUP BY 1 ORDER BY 1"""

# Use the very same compiled day SQL on isolated counterfactual inputs after
# the public-seed results have been captured. These rows are not seed evidence.
MISSING_PRODUCT_SQL = """INSERT INTO order_items
    (order_item_id, order_id, product_id, ordered_at, product_price, is_food_item, is_drink_item)
SELECT 'missing-only', 'probe-order', 'ABSENT-SKU', DATE '2025-09-01',
       p.product_price, p.is_food_item, p.is_drink_item
FROM (VALUES ('ABSENT-SKU')) AS i(sku)
LEFT JOIN stg_products p ON i.sku = p.product_id"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sql_sha(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def checked_inputs() -> dict:
    meta = json.loads((PROV / "run_metadata.json").read_text())
    if (meta["commit"], meta["archive_tar_sha256"]) != (COMMIT, ARCHIVE_SHA):
        raise AssertionError("Prior provenance commit/archive differs")
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    if head != COMMIT:
        raise AssertionError(f"Unexpected checkout: {head}")
    for relative, expected in SOURCE_HASHES.items():
        path = REPO / relative
        committed = subprocess.check_output(["git", "-C", str(REPO), "show", f"HEAD:{relative}"])
        if sha(path) != expected or hashlib.sha256(committed).hexdigest() != expected:
            raise AssertionError(f"Public source/seed pin failed: {relative}")
    for relative, expected in PROV_HASHES.items():
        if sha(PROV / relative) != expected:
            raise AssertionError(f"Same-commit provenance pin failed: {relative}")
    semantic = json.loads((PROV / "manifests/semantic_manifest.json").read_text())
    manifest = json.loads((PROV / "manifests/manifest.json").read_text())
    model = next(s for s in semantic["semantic_models"] if s["name"] == "order_item")
    if model["node_relation"]["alias"] != "order_items" or model["defaults"]["agg_time_dimension"] != "ordered_at":
        raise AssertionError("Semantic model binding/time changed")
    measure_by_name = {m["name"]: m for m in model["measures"]}
    expressions = {
        "revenue": "product_price",
        "food_revenue": "case when is_food_item then product_price else 0 end",
        "drink_revenue": "case when is_drink_item then product_price else 0 end",
    }
    for name, expr in expressions.items():
        metric = next(m for m in semantic["metrics"] if m["name"] == name)
        if (metric["type"] != "simple" or metric["type_params"]["measure"]["name"] != name
                or metric["type_params"]["measure"]["filter"] is not None
                or measure_by_name[name]["agg"] != "sum" or measure_by_name[name]["expr"] != expr
                or manifest["metrics"][f"metric.jaffle_shop.{name}"]["depends_on"]["nodes"]
                != ["semantic_model.jaffle_shop.order_item"]):
            raise AssertionError(f"Metric declaration/binding changed: {name}")
    return meta


def run_mf(args: list[str], project: Path, env: dict[str, str]) -> str:
    result = subprocess.run(["mf", "query", *args], cwd=project, env=env,
                            capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"mf query {args!r}: {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def generated_sql(metric: str, project: Path, env: dict[str, str]) -> str:
    out = run_mf(["--metrics", metric, "--group-by", "metric_time__day", "--explain"], project, env)
    marker = "\nSELECT\n"
    if out.count(marker) != 1:
        raise AssertionError(f"Cannot isolate one MetricFlow SQL statement: {out}")
    return "SELECT\n" + out.split(marker, 1)[1].rstrip() + "\n"


def day_key(value: object) -> str | None:
    return None if value is None or value == "" else str(value)[:10]


def dollars(value: object) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value)).quantize(Decimal("0.01"))


def raw_controls(con: duckdb.DuckDBPyConnection) -> tuple[dict, list]:
    counts = {name: con.execute(f"SELECT COUNT(*) FROM raw_{name}").fetchone()[0]
              for name in ("items", "orders", "products")}
    counts["order_items"] = con.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    checks = con.execute("""SELECT
      COUNT(*) - COUNT(DISTINCT order_item_id),
      COUNT(*) FILTER (WHERE ordered_at IS NULL),
      COUNT(*) FILTER (WHERE product_price IS NULL),
      COUNT(*) FILTER (WHERE is_food_item),
      COUNT(*) FILTER (WHERE is_drink_item),
      COUNT(*) FILTER (WHERE is_food_item AND is_drink_item)
    FROM order_items""").fetchone()
    missing_product = con.execute("""SELECT COUNT(*) FROM raw_items i
        LEFT JOIN raw_products p ON i.sku = p.sku WHERE p.sku IS NULL""").fetchone()[0]
    missing_order = con.execute("""SELECT COUNT(*) FROM raw_items i
        LEFT JOIN raw_orders o ON i.order_id = o.id WHERE o.id IS NULL""").fetchone()[0]
    duplicate_products = con.execute("SELECT COUNT(*) - COUNT(DISTINCT sku) FROM raw_products").fetchone()[0]
    counts.update(zip(("duplicate_items", "null_time", "null_price", "food_items",
                       "drink_items", "both_flags"), checks))
    counts.update(missing_product=missing_product, missing_order=missing_order,
                  duplicate_products=duplicate_products)
    if (counts["order_items"] != counts["items"] or counts["duplicate_items"]
            or counts["duplicate_products"] or counts["missing_product"] != counts["null_price"]):
        raise AssertionError(f"Unexpected join cardinality or NULL mapping: {counts}")
    direct = con.execute(CONTROL_SQL).fetchall()
    return counts, direct


def edge_cases(con: duckdb.DuckDBPyConnection, sql: dict[str, str]) -> dict:
    # A transaction prevents any fixture from surviving in the temporary DB.
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM order_items")
        empty = {name: con.execute(sql[name]).fetchall() for name in METRICS}
        scalar_empty = {name: con.execute((PROV / "generated_sql" / f"{name}.sql").read_text()).fetchone()[0]
                        for name in METRICS}
        assert all(rows == [] for rows in empty.values()) and all(v is None for v in scalar_empty.values())

        con.execute(MISSING_PRODUCT_SQL)
        missing_row = con.execute("""SELECT product_id, product_price, is_food_item, is_drink_item
                                     FROM order_items""").fetchone()
        assert missing_row == ("ABSENT-SKU", None, None, None), missing_row
        only_missing = {name: con.execute(sql[name]).fetchall() for name in METRICS}
        only_values = {name: rows[0][1] for name, rows in only_missing.items()}
        assert all(len(rows) == 1 and day_key(rows[0][0]) == "2025-09-01"
                   for rows in only_missing.values()), only_missing
        assert only_values == {"revenue": None, "food_revenue": Decimal(0),
                               "drink_revenue": Decimal(0)}, only_values

        # Known food and beverage on the same date demonstrate a nonempty mixed
        # group with an unmatched product. This is isolated from the seed run.
        con.execute("""INSERT INTO order_items
          (order_item_id, order_id, product_id, ordered_at, product_price, is_food_item, is_drink_item)
          SELECT p.product_id, 'probe-order', p.product_id, DATE '2025-09-01',
                 p.product_price, p.is_food_item, p.is_drink_item
          FROM stg_products p WHERE p.product_id IN ('JAF-001', 'BEV-001')""")
        mixed = {name: con.execute(sql[name]).fetchall() for name in METRICS}
        mixed_values = {name: dollars(rows[0][1]) for name, rows in mixed.items()}
        assert all(len(rows) == 1 for rows in mixed.values()), mixed
        assert mixed_values == {"revenue": Decimal("17.00"),
                                "food_revenue": Decimal("11.00"),
                                "drink_revenue": Decimal("6.00")}, mixed_values
        con.execute("""INSERT INTO order_items
          (order_item_id, order_id, product_id, ordered_at, product_price, is_food_item, is_drink_item)
          VALUES ('null-time', 'probe-order', 'JAF-001', NULL, 11.00, TRUE, FALSE)""")
        null_time = {name: con.execute(sql[name]).fetchall() for name in METRICS}
        null_values = {name: dollars(next(v for k, v in rows if k is None))
                       for name, rows in null_time.items()}
        assert all(len(rows) == 2 for rows in null_time.values()), null_time
        assert null_values == {"revenue": Decimal("11.00"),
                               "food_revenue": Decimal("11.00"),
                               "drink_revenue": Decimal("0.00")}, null_values
        return {"empty_groups": {name: len(rows) for name, rows in empty.items()},
                "empty_scalars": scalar_empty, "missing_only": only_values,
                "missing_row": missing_row, "mixed": mixed_values,
                "null_time": null_values}
    finally:
        con.execute("ROLLBACK")


def main() -> None:
    meta = checked_inputs()
    with tempfile.TemporaryDirectory(prefix="jaffle_grouped_", dir="/tmp") as tmp:
        temp = Path(tmp)
        project, profiles = temp / "project", temp / "profiles"
        (project / "target").mkdir(parents=True)
        profiles.mkdir()
        shutil.copyfile(REPO / "dbt_project.yml", project / "dbt_project.yml")
        for name in ("manifest.json", "semantic_manifest.json"):
            shutil.copyfile(PROV / "manifests" / name, project / "target" / name)
        db = temp / "dev.duckdb"
        (profiles / "profiles.yml").write_text(
            "default:\n  target: dev\n  outputs:\n    dev:\n"
            f"      type: duckdb\n      path: {db}\n      schema: main\n      threads: 1\n")
        env = {"HOME": str(temp), "PATH": f"{VENV_BIN}:/usr/bin:/bin", "LANG": "C.UTF-8",
               "DBT_PROFILES_DIR": str(profiles), "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
               "DO_NOT_TRACK": "1"}

        con = duckdb.connect(str(db))  # file name supplies the dev catalog to mf
        for name in ("items", "orders", "products"):
            con.execute(f"CREATE TABLE raw_{name} AS SELECT * FROM read_csv(?, header=true, all_varchar=true)",
                        [str(REPO / "seeds/jaffle-data" / f"raw_{name}.csv")])
        con.execute(STG_PRODUCTS_SQL)
        con.execute(MODEL_SQL)
        counts, direct = raw_controls(con)
        con.close()  # mf opens the file in its own process

        compiled: dict[str, str] = {}
        csv_rows: dict[str, list[dict[str, str]]] = {}
        for name in METRICS:
            compiled[name] = generated_sql(name, project, env)
            output = temp / f"{name}_day.csv"
            run_mf(["--metrics", name, "--group-by", "metric_time__day", "--csv", str(output)],
                   project, env)
            with output.open(newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames != ["metric_time__day", name]:
                    raise AssertionError(f"Unexpected MetricFlow CSV columns: {reader.fieldnames}")
                csv_rows[name] = list(reader)

        con = duckdb.connect(str(db), read_only=True)
        actual: dict[str, dict[str, Decimal | None]] = {}
        for name in METRICS:
            query_rows = con.execute(compiled[name]).fetchall()
            from_sql = {day_key(k): dollars(v) for k, v in query_rows}
            from_cli = {day_key(r["metric_time__day"]): dollars(r[name]) for r in csv_rows[name]}
            if (len(from_sql) != len(query_rows) or len(from_cli) != len(csv_rows[name])
                    or from_sql != from_cli):
                raise AssertionError(f"MetricFlow CLI/direct SQL keys or values differ: {name}")
            actual[name] = from_sql
        control = {day_key(row[0]): row for row in direct}
        if len(control) != len(direct) or any(set(actual[name]) != set(control) for name in METRICS):
            raise AssertionError("MetricFlow grouping differs from direct raw-seed grouping")
        for day, (_, n, revenue, food, drink) in control.items():
            if n <= 0 or (actual["revenue"][day], actual["food_revenue"][day], actual["drink_revenue"][day]) != (
                dollars(None if revenue is None else Decimal(revenue) / 100),
                dollars(Decimal(food) / 100), dollars(Decimal(drink) / 100)):
                raise AssertionError(f"Direct raw-cent expression differs on {day}")
        assert sum(row[1] for row in direct) == counts["items"]
        assert not counts["null_time"] and not counts["null_price"] and not counts["both_flags"]
        assert not counts["missing_order"]
        assert counts["food_items"] + counts["drink_items"] == counts["items"]
        assert all(actual["revenue"][k] == actual["food_revenue"][k] + actual["drink_revenue"][k]
                   for k in control)
        totals = {name: sum(actual[name].values(), Decimal(0)) for name in METRICS}
        scalar = {name: dollars(con.execute((PROV / "generated_sql" / f"{name}.sql").read_text()).fetchone()[0])
                  for name in METRICS}
        assert totals == scalar and totals["revenue"] == totals["food_revenue"] + totals["drink_revenue"]
        con.close()

        # The seed observations have been recorded; mutate only the disposable
        # /tmp database to probe SQL behavior on hypothetical edge inputs.
        con = duckdb.connect(str(db))
        edge = edge_cases(con, compiled)
        con.close()

    days = sorted(control)
    first = days[0]
    if len(days) != (date.fromisoformat(days[-1]) - date.fromisoformat(first)).days + 1:
        raise AssertionError("Unrepresented calendar days between first and last seed day")
    max_food = max(days, key=lambda d: actual["food_revenue"][d])
    middle = days[len(days) // 2]
    def example(day: str) -> str:
        return (f"| `{day}` | {control[day][1]:,} | {actual['revenue'][day]:,.2f} | "
                f"{actual['food_revenue'][day]:,.2f} | {actual['drink_revenue'][day]:,.2f} |")

    source_table = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in SOURCE_HASHES.items())
    prov_table = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in PROV_HASHES.items())
    sql_table = "\n".join(
        f"| `{name}` day | `{sql_sha(compiled[name])}` | {len(csv_rows[name])} | "
        f"{sum(v is None for v in actual[name].values())} | {totals[name]:,.2f} |"
        for name in METRICS)
    sql_blocks = "\n\n".join(f"**`{name}` day SQL** (SHA-256 `{sql_sha(compiled[name])}`):\n\n"
                             f"```sql\n{compiled[name].strip()}\n```" for name in METRICS)
    report = f"""# Pinned Jaffle Shop: MetricFlow grouped revenue scope probe

## Scope and provenance

Public `dbt-labs/jaffle-shop` checkout at `{COMMIT}`; previous same-commit archive SHA-256 `{ARCHIVE_SHA}`. The checkout HEAD, every local source/seed byte stream, its committed Git blob, both existing parse manifests, and three archived scalar SQL files were checked against fixed hashes **before** loading rows. Previous `run_metadata.json` supplies the commit/archive identity; it was not regenerated. The manifest binds all three simple `sum` metrics to `order_item` / `order_items`, default `ordered_at` time, with expressions `product_price`, `case when is_food_item then product_price else 0 end`, and `case when is_drink_item then product_price else 0 end`.

The program reconstructed the selected model columns from pinned public CSVs in a disposable `/tmp` DuckDB file (`dev.main.order_items`). It computed `stg_products` flags with `COALESCE` first, then left-joined the staged products into the mart, preserving NULL flags on an absent product; it also used the source order join, day truncation, and cents conversion to `NUMERIC(16,2)`. The compiled mart's supply summary is one row per product and its columns are not used by these metrics; this is a **selected-column SQL reconstruction**, not a dbt build. It loaded the prior same-commit `manifest.json` and `semantic_manifest.json` into a disposable project and called `mf query --metrics <name> --group-by metric_time__day --explain` and the corresponding `--csv` execution for **each** metric, with no time bounds or metric filters. All query files, profile, and database were external to this workspace and removed after execution. Runtime: `dbt-metricflow {version('dbt-metricflow')}` / `metricflow {version('metricflow')}`, DuckDB `{duckdb.__version__}`.

## Seed observations and aligned day comparison

Raw rows: items **{counts['items']:,}**, orders **{counts['orders']:,}**, products **{counts['products']}**. Reconstructed item rows **{counts['order_items']:,}**; duplicate item IDs **{counts['duplicate_items']}**, duplicate product SKUs **{counts['duplicate_products']}**, missing order mappings **{counts['missing_order']}**, missing product mappings/NULL prices **{counts['missing_product']}/{counts['null_price']}**, NULL order times **{counts['null_time']}**. Food flagged rows **{counts['food_items']:,}**, drink flagged rows **{counts['drink_items']:,}**, both flags **{counts['both_flags']}**. These public seeds have complete, exclusive food/drink classification and non-NULL prices; that property is empirical.

All three CLI results and direct executions of their freshly generated SQL have **{len(days)} distinct, identical day keys** (`{first}` through `{days[-1]}`), covering every calendar day in that span. No duplicate key, NULL day key, or NULL metric value occurred in the seed output. The raw-seed control groups **{len(direct)} days** and **{sum(row[1] for row in direct):,} item rows**. It computes integer cents by product type from independent raw joins and converts only the resulting sums to dollars. Every day and each metric matches this control with exact decimal values. On all {len(days)} observed days, revenue equals food plus drink revenue; the three sums also match their separately archived ungrouped MetricFlow SQL on this reconstructed table.

| Fresh MetricFlow SQL | SHA-256 (UTF-8, terminal newline) | Day groups | NULL values | Sum of groups ($) |
| --- | --- | ---: | ---: | ---: |
{sql_table}

| Day example | Item rows | Revenue ($) | Food ($) | Drink ($) |
| --- | ---: | ---: | ---: | ---: |
{example(first)}
{example(middle)}
{example(max_food)}

Examples are the first day, the middle date, and the day with highest food revenue (lexical tie break). They illustrate the observed grouped scope, not a universal partition claim.

## Empty and missing-product behavior

After recording seed results, the program used a **transaction on the disposable database** to execute the same three compiled day statements on isolated counterfactual rows; it rolled back. These rows are test fixtures, not Jaffle Shop seed observations or human labels.

| Isolated input | Grouped `revenue` | Grouped `food_revenue` | Grouped `drink_revenue` |
| --- | ---: | ---: | ---: |
| Empty item table | no row | no row | no row |
| One item with absent `ABSENT-SKU` on `2025-09-01` | NULL | 0.00 | 0.00 |
| Same group plus `JAF-001` ($11) and `BEV-001` ($6) | 17.00 | 11.00 | 6.00 |
| Separate known food item with NULL `ordered_at` | 11.00 at NULL day key | 11.00 at NULL day key | 0.00 at NULL day key |

The missing SKU has NULL price **and NULL food/drink flags** after the mart's left join to `stg_products`. The measure expressions use `CASE WHEN flag THEN product_price ELSE 0 END`; a NULL flag takes the `ELSE 0` path. The archived scalar SQL on an empty relation returned NULL for each `SUM`, while grouped SQL emitted zero rows: a missing group is not a numeric zero. A present group containing only a missing-price item instead has NULL unfiltered `SUM(product_price)` and two zero CASE sums. With known rows alongside it, SUM skips the NULL price; the known rows contribute $17.00. A separate NULL-time row yields a NULL day group alongside the populated September 1 group in the unbounded compiled SQL. These fixture results distinguish empty group, NULL key, NULL measure, and a real zero. On the actual public seeds, missing products, prices, and times were all zero, so those cases were not observed there.

## SQL and exact input hashes

Direct raw-cent control (the asserted comparison, separate from the mart relation):

```sql
{CONTROL_SQL}
```

Staged product relation, then selected-column reconstructed mart:

```sql
{STG_PRODUCTS_SQL}
```

```sql
{MODEL_SQL}
```

{sql_blocks}

The three existing **ungrouped** SQL files, used to reconcile sums and check empty scalar behavior, have the hashes below. The day SQL above was freshly generated and executed; it is not an archived grouped query.

| Prior provenance input (relative to `metric_provenance_verification`) | SHA-256 |
| --- | --- |
{prov_table}

| Pinned source or seed (relative to the public checkout) | SHA-256 |
| --- | --- |
{source_table}

## Interpretation and reproduction

This is a finite development observation under one pinned dataset, reconstruction, manifest, and day grouping. The declared CASE expressions explain why both components partition these rows when product types are exclusively `jaffle` or `beverage`, but they do not guarantee that partition on other products, missing prices, NULL flags, filters, or other data. No universal equivalence, human gold relationship, held-out repository, worksheet, or method performance is claimed.

Run from the workspace root with `metric_matching_dev_build_20260928/venv/bin/python -B metric_matching_pilot/probe_grouped_scope.py`. It checks pins and binding, compiles and runs three CLI queries, checks direct SQL and raw-cent control, runs the isolated NULL/empty fixtures, and writes only this report. Script SHA-256 `{sha(Path(__file__))}`.
"""
    REPORT.write_text(report)
    print(f"Wrote {REPORT}; {len(days)} day groups, "
          + ", ".join(f"{name}={totals[name]:,.2f}" for name in METRICS))


if __name__ == "__main__":
    main()
