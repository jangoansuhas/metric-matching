#!/usr/bin/env python3
"""Finite food_revenue/revenue check on pinned public Jaffle Shop seeds.

Run with the existing local DuckDB venv, for example:
  metric_matching_dev_build_20260928/venv/bin/python -B \
    metric_matching_pilot/experiment_food_revenue.py

Only an in-memory DuckDB connection is used. The only file written is the
adjacent experiment_food_revenue_report.md.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / "public_corpus/jaffle-shop-sidemantic/jaffle-shop"
BUILD = ROOT / "build_verification/order_cost_build_7be2c58/compiled/jaffle_shop/models"
PROVENANCE = ROOT / "metric_provenance_verification"
REPORT = Path(__file__).with_name("experiment_food_revenue_report.md")
COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"

# Relative to ROOT; fail closed if a seed, declaration, model, or generated
# statement differs from the previously inspected public development inputs.
EXPECTED_SHA256 = {
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml": "81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.sql": "7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_order_items.sql": "102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_orders.sql": "9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_products.sql": "062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_supplies.sql": "1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/macros/cents_to_dollars.sql": "5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_items.csv": "bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_orders.csv": "e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_products.csv": "01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d",
    "public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_supplies.csv": "309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1",
    "build_verification/order_cost_build_7be2c58/compiled/jaffle_shop/models/marts/order_items.sql": "508b47c1522cb633c05bf896a9f6ab3247ef3689e9f36d52883aaa68f1339b29",
    "build_verification/order_cost_build_7be2c58/compiled/jaffle_shop/models/staging/stg_supplies.sql": "0fa0d78a4aacc5c32cbd710ca163f4a58019fd93744fb21928941735f2ae59c3",
    "metric_provenance_verification/manifests/manifest.json": "8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42",
    "metric_provenance_verification/manifests/semantic_manifest.json": "bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51",
    "metric_provenance_verification/generated_sql/revenue.sql": "eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134",
    "metric_provenance_verification/generated_sql/food_revenue.sql": "682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110",
}

# Only columns used by the compiled mart and its metric expressions are
# projected here. These are literal DuckDB translations of the pinned staging
# source and cents_to_dollars macro, whose bytes are checked above.
STAGING_SQL = (
    """CREATE TABLE "jaffle_dev"."main"."stg_order_items" AS
SELECT id AS order_item_id, order_id, sku AS product_id
FROM "jaffle_dev"."raw"."raw_items"
""",
    """CREATE TABLE "jaffle_dev"."main"."stg_orders" AS
SELECT id AS order_id, date_trunc('day', ordered_at) AS ordered_at
FROM "jaffle_dev"."raw"."raw_orders"
""",
    """CREATE TABLE "jaffle_dev"."main"."stg_products" AS
SELECT sku AS product_id, name AS product_name,
       (price / 100)::numeric(16, 2) AS product_price,
       coalesce(type = 'jaffle', false) AS is_food_item,
       coalesce(type = 'beverage', false) AS is_drink_item
FROM "jaffle_dev"."raw"."raw_products"
""",
)


def checked_inputs() -> None:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if commit != COMMIT:
        raise RuntimeError(f"unexpected checkout {commit}, expected {COMMIT}")
    for relative, expected in EXPECTED_SHA256.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"input hash mismatch: {relative}: {actual} != {expected}")


def declarations() -> dict[str, str]:
    semantic = json.loads((PROVENANCE / "manifests/semantic_manifest.json").read_text())
    manifest = json.loads((PROVENANCE / "manifests/manifest.json").read_text())
    owner = next(model for model in semantic["semantic_models"] if model["name"] == "order_item")
    assert owner["node_relation"]["alias"] == "order_items"
    assert owner["defaults"]["agg_time_dimension"] == "ordered_at"
    measures = {m["name"]: m for m in owner["measures"]}
    expected = {
        "revenue": "product_price",
        "food_revenue": "case when is_food_item then product_price else 0 end",
    }
    for name, expr in expected.items():
        metric = next(m for m in semantic["metrics"] if m["name"] == name)
        assert metric["type"] == "simple"
        assert metric["type_params"]["measure"]["name"] == name
        assert metric["type_params"]["measure"]["filter"] is None
        assert measures[name]["agg"] == "sum" and measures[name]["expr"] == expr
        assert manifest["metrics"][f"metric.jaffle_shop.{name}"]["depends_on"]["nodes"] == [
            "semantic_model.jaffle_shop.order_item"
        ]
    return expected


def build_in_memory(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    con.execute("ATTACH ':memory:' AS jaffle_dev")
    con.execute("ATTACH ':memory:' AS dev")
    con.execute('CREATE SCHEMA "jaffle_dev"."raw"')
    counts = {}
    for name in ("raw_items", "raw_orders", "raw_products", "raw_supplies"):
        path = REPO / "seeds/jaffle-data" / f"{name}.csv"
        con.execute(
            f'CREATE TABLE "jaffle_dev"."raw"."{name}" AS SELECT * FROM read_csv_auto(?)',
            [str(path)],
        )
        counts[name] = con.execute(f'SELECT COUNT(*) FROM "jaffle_dev"."raw"."{name}"').fetchone()[0]
    for sql in STAGING_SQL:
        con.execute(sql)
    con.execute(
        'CREATE TABLE "jaffle_dev"."main"."stg_supplies" AS '\
        + (BUILD / "staging/stg_supplies.sql").read_text()
    )
    con.execute(
        'CREATE TABLE "jaffle_dev"."main"."order_items" AS '\
        + (BUILD / "marts/order_items.sql").read_text()
    )
    # The archived MetricFlow statements use "dev". The view lets us execute
    # their original SQL byte-for-byte without writing an on-disk database.
    con.execute(
        'CREATE VIEW "dev"."main"."order_items" AS '
        'SELECT * FROM "jaffle_dev"."main"."order_items"'
    )
    counts["order_items"] = con.execute(
        'SELECT COUNT(*) FROM "jaffle_dev"."main"."order_items"'
    ).fetchone()[0]
    return counts


def grouped_sql(group: str, expr: dict[str, str]) -> str:
    key = {"day": "CAST(ordered_at AS DATE)", "order_id": "order_id"}[group]
    alias = {"day": "metric_time__day", "order_id": "order_id"}[group]
    return f"""SELECT {key} AS {alias},
       SUM({expr['revenue']}) AS revenue,
       SUM({expr['food_revenue']}) AS food_revenue,
       COUNT(*) AS item_rows,
       COUNT(*) FILTER (WHERE is_food_item IS TRUE) AS food_rows,
       COUNT(*) FILTER (WHERE is_food_item IS NOT TRUE) AS nonfood_rows,
       SUM(CASE WHEN is_food_item IS NOT TRUE THEN product_price ELSE 0 END) AS masked_revenue
FROM "jaffle_dev"."main"."order_items"
GROUP BY 1
ORDER BY 1"""


def money(value: Decimal | None) -> str:
    return "NULL" if value is None else f"{value:,.2f}"


def group_summary(rows: list[tuple]) -> dict:
    equal = [r for r in rows if r[1] is not None and r[2] is not None and r[1] == r[2]]
    different = [r for r in rows if r[1] is not None and r[2] is not None and r[1] != r[2]]
    null = [r for r in rows if r[1] is None or r[2] is None]
    return {
        "groups": len(rows), "equal": len(equal), "different": len(different), "null": len(null),
        "equal_example": equal[0] if equal else None,
        "different_example": different[0] if different else None,
        "sum_revenue": sum((r[1] for r in rows if r[1] is not None), Decimal(0)),
        "sum_food": sum((r[2] for r in rows if r[2] is not None), Decimal(0)),
    }


def example_row(label: str, row: tuple | None) -> str:
    if row is None:
        return f"| {label} | none observed | — | — | — | — | — | — |"
    key, revenue, food, items, food_items, nonfood_items, masked = row
    return (
        f"| {label} | `{key}` | {money(revenue)} | {money(food)} | "
        f"{money(revenue - food)} | {items:,} | {food_items:,} / {nonfood_items:,} | {money(masked)} |"
    )


def main() -> None:
    checked_inputs()
    expr = declarations()
    total_sql = {
        name: (PROVENANCE / "generated_sql" / f"{name}.sql").read_text()
        for name in ("revenue", "food_revenue")
    }
    con = duckdb.connect(":memory:")
    try:
        counts = build_in_memory(con)
        totals = {name: con.execute(sql).fetchone()[0] for name, sql in total_sql.items()}
        sql_by_group = {name: grouped_sql(name, expr) for name in ("day", "order_id")}
        groups = {name: group_summary(con.execute(sql).fetchall()) for name, sql in sql_by_group.items()}
        profile = con.execute('''SELECT
            COUNT(DISTINCT order_item_id),
            COUNT(*) FILTER (WHERE product_price IS NULL),
            COUNT(*) FILTER (WHERE product_price < 0),
            COUNT(*) FILTER (WHERE product_price = 0),
            COUNT(*) FILTER (WHERE is_food_item IS TRUE),
            COUNT(*) FILTER (WHERE is_food_item IS NOT TRUE),
            COUNT(*) FILTER (WHERE ordered_at IS NULL)
          FROM "jaffle_dev"."main"."order_items"''').fetchone()
        order_coverage = con.execute('''SELECT
            COUNT(DISTINCT id),
            COUNT(*) FILTER (WHERE NOT EXISTS (
                SELECT 1 FROM "jaffle_dev"."raw"."raw_items" i WHERE i.order_id = o.id
            ))
          FROM "jaffle_dev"."raw"."raw_orders" o''').fetchone()
        assert counts["order_items"] == counts["raw_items"] == profile[0]
        assert order_coverage[0] == counts["raw_orders"]
        assert order_coverage[1] + groups["order_id"]["groups"] == counts["raw_orders"]
        assert profile[1] == profile[6] == 0
        assert all(g["null"] == 0 for g in groups.values())
        for g in groups.values():
            assert g["sum_revenue"] == totals["revenue"]
            assert g["sum_food"] == totals["food_revenue"]
        assert totals["revenue"] - totals["food_revenue"] == sum(
            (r[6] for r in con.execute(sql_by_group["day"]).fetchall()), Decimal(0)
        )
    finally:
        con.close()

    source_rows = "\n".join(
        f"| `{path}` | `{digest}` |" for path, digest in EXPECTED_SHA256.items()
    )
    def statement(sql: str) -> str:
        return "```sql\n" + sql.strip() + "\n```"

    report = f"""# `food_revenue` vs `revenue`: finite public seed experiment

Repository: `dbt-labs/jaffle-shop` at `{COMMIT}`. Executed locally with DuckDB `{duckdb.__version__}` in one `:memory:` connection; both attached catalogs are also `:memory:`. No existing database was opened or modified. This is a development observation, not a human gold label or a method comparison.

## Source and query scope

Both simple metrics resolve in the verified semantic manifest to the same `order_item` model (`order_items`, one row per order item), `sum` aggregation, and default time dimension `ordered_at`. The declared `revenue` expression is `product_price`; `food_revenue` is `case when is_food_item then product_price else 0 end`. In staging, `product_price` is `(price / 100)::numeric(16, 2)` and `is_food_item` is `coalesce(type = 'jaffle', false)`. The compiled `order_items` model left-joins orders, products, and per-product supply totals. The experiment loads four CSV seeds, projects the required staging columns using the source expressions, executes the pinned compiled supply and order-item models, and exposes the result under the `dev` catalog to execute the two archived MetricFlow total queries **unchanged**. The grouped queries below are constructed from the same declared expressions; they are experiment SQL, not archived MetricFlow-generated grouped SQL.

Input rows: raw items **{counts['raw_items']:,}**, raw orders **{counts['raw_orders']:,}**, raw products **{counts['raw_products']:,}**, raw supplies **{counts['raw_supplies']:,}**; resulting `order_items` **{counts['order_items']:,}** rows and **{profile[0]:,}** distinct item IDs. Missing product prices **{profile[1]:,}**; negative prices **{profile[2]:,}**; zero prices **{profile[3]:,}**; food item rows **{profile[4]:,}**; masked (non-food or null-flag) rows **{profile[5]:,}**; missing `ordered_at` **{profile[6]:,}**. The mart row count equals the raw item count; the query did not fan out item rows on these seeds.

The raw order IDs are unique (**{order_coverage[0]:,}**). **{order_coverage[1]:,}** raw orders have no item row, so they do not appear in the `order_id` grouping; the other **{groups['order_id']['groups']:,}** orders do.

## Observed values

All monetary values are dollars (`DECIMAL` aggregation); equality checks used DuckDB decimal values without a floating-point tolerance.

| Scope | Groups | Equal | Different | NULL result | Sum revenue | Sum food revenue |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Total (one scalar) | 1 | {int(totals['revenue'] == totals['food_revenue'])} | {int(totals['revenue'] != totals['food_revenue'])} | 0 | {money(totals['revenue'])} | {money(totals['food_revenue'])} |
| `ordered_at` day | {groups['day']['groups']:,} | {groups['day']['equal']:,} | {groups['day']['different']:,} | {groups['day']['null']:,} | {money(groups['day']['sum_revenue'])} | {money(groups['day']['sum_food'])} |
| `order_id` | {groups['order_id']['groups']:,} | {groups['order_id']['equal']:,} | {groups['order_id']['different']:,} | {groups['order_id']['null']:,} | {money(groups['order_id']['sum_revenue'])} | {money(groups['order_id']['sum_food'])} |

Total difference (`revenue - food_revenue`): **{money(totals['revenue'] - totals['food_revenue'])}**. Group sums reconcile exactly to both independently executed generated totals.

| Example | Group key | Revenue | Food revenue | Difference | Item rows | Food / masked rows | Masked price sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
{example_row('Different day', groups['day']['different_example'])}
{example_row('Equal day', groups['day']['equal_example'])}
{example_row('Different order', groups['order_id']['different_example'])}
{example_row('Equal order', groups['order_id']['equal_example'])}

The examples are the first keys in ascending SQL order for each category. An equal group demonstrates only equality at that grouping on these rows. A different group gives a direct counterexample to substituting the two metric values in that scope.

## SQL executed

The archived MetricFlow-generated **total** statements were executed byte-for-byte (file hashes below):

`revenue`:

{statement(total_sql['revenue'])}

`food_revenue`:

{statement(total_sql['food_revenue'])}

Shared `ordered_at` day grouping (constructed from the verified measure expressions):

{statement(sql_by_group['day'])}

Shared order grouping (same expressions, key from `order_items`):

{statement(sql_by_group['order_id'])}

The exact staging projection SQL and `CREATE TABLE ... AS` loading procedure are in `experiment_food_revenue.py`; the compiled supply and order-item SQL are read and executed verbatim from the hashed files below. A `dev.main.order_items` in-memory view supplies the archived total statements' original relation name.

## Input SHA-256 (exact bytes)

| Input relative to workspace root | SHA-256 |
| --- | --- |
{source_rows}

## Interpretation and limits

**Source-supported relation:** on the same order-item rows, `food_revenue` replaces each non-food (or unknown-flag) price with zero before summing; `revenue` sums all prices. It is a food-scoped component of the unfiltered revenue expression. The source expressions alone do not guarantee a strict inequality at every grouping: a group may have only food rows, zero non-food prices, or negative prices. NULL and empty-input behavior also matters in other data. The positive-price, non-null observations and counts above belong to these local seeds only.

**Empirical result:** these seeds give the displayed total and group counts; the different groups refute value equivalence for those scopes here. The source path explains the observed difference, while the finite sample does not establish values for other datasets, filters, time windows, or future commits. No held-out source or practice worksheet was read for this run, no human gold label was assigned, and no method superiority follows from this experiment.
"""
    REPORT.write_text(report)
    print(f"wrote {REPORT}")
    print(
        f"total revenue={money(totals['revenue'])}, food_revenue={money(totals['food_revenue'])}; "
        f"day equal/different={groups['day']['equal']}/{groups['day']['different']}; "
        f"order equal/different={groups['order_id']['equal']}/{groups['order_id']['different']}"
    )


if __name__ == "__main__":
    main()
