#!/usr/bin/env python3
"""Bounded, reproducible Jaffle Shop gross-profit development observation.

Requires DuckDB. Builds the relevant pinned dbt model expressions from the four
public seeds in an in-memory catalog and executes the pinned ungrouped MetricFlow
SQL. Daily/order SQL below is an explicit scoped comparison, not a MetricFlow
compilation or a general identity proof. Writes only the companion Markdown file.
"""

import argparse
import hashlib
import subprocess
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
SOURCE_HASHES = {
    "seeds/jaffle-data/raw_orders.csv": "e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b",
    "seeds/jaffle-data/raw_items.csv": "bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca",
    "seeds/jaffle-data/raw_products.csv": "01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d",
    "seeds/jaffle-data/raw_supplies.csv": "309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1",
    "models/marts/order_items.yml": "81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97",
    "models/marts/orders.yml": "223dc461510c54b38681167b85cea019b3919c4a1de8bfac6673d60465ea0391",
    "models/marts/order_items.sql": "7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639",
    "models/marts/orders.sql": "a1196f297da67c4a55c1e1011202f4fa7cf29c9ad3a0282970de4f947cc2ef1b",
    "models/staging/stg_orders.sql": "9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327",
    "models/staging/stg_order_items.sql": "102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04",
    "models/staging/stg_products.sql": "062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6",
    "models/staging/stg_supplies.sql": "1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4",
    "macros/cents_to_dollars.sql": "5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb",
}
SQL_HASHES = {
    "revenue": "eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134",
    "order_cost": "c0f6c4ca283c57bbafe985506aa28b54b8f4dec0074e67063654c54212d217ab",
    "order_gross_profit": "d2828571bfb4cc45577230d06339f13beb2a0451eaefe1d29fe9bac9418e6b2c",
}

# Equivalent selected columns and joins from the pinned staging/mart SQL.
# Monetary conversion uses the pinned DuckDB default cents_to_dollars macro.
BUILD_SQL = (
    """CREATE TABLE dev.main.stg_orders AS
       SELECT id AS order_id,
              date_trunc('day', CAST(ordered_at AS TIMESTAMP)) AS ordered_at,
              CAST(CAST(subtotal AS BIGINT) / 100 AS DECIMAL(16,2)) AS subtotal
       FROM dev.main.raw_orders""",
    """CREATE TABLE dev.main.stg_order_items AS
       SELECT id AS order_item_id, order_id, sku AS product_id
       FROM dev.main.raw_items""",
    """CREATE TABLE dev.main.stg_products AS
       SELECT sku AS product_id,
              CAST(CAST(price AS BIGINT) / 100 AS DECIMAL(16,2)) AS product_price
       FROM dev.main.raw_products""",
    """CREATE TABLE dev.main.stg_supplies AS
       SELECT sku AS product_id,
              CAST(CAST(cost AS BIGINT) / 100 AS DECIMAL(16,2)) AS supply_cost
       FROM dev.main.raw_supplies""",
    """CREATE TABLE dev.main.order_items AS
       WITH order_supplies_summary AS (
           SELECT product_id, SUM(supply_cost) AS supply_cost
           FROM dev.main.stg_supplies GROUP BY product_id
       )
       SELECT i.order_item_id, i.order_id, i.product_id, o.ordered_at,
              p.product_price, s.supply_cost
       FROM dev.main.stg_order_items i
       LEFT JOIN dev.main.stg_orders o ON i.order_id = o.order_id
       LEFT JOIN dev.main.stg_products p ON i.product_id = p.product_id
       LEFT JOIN order_supplies_summary s ON i.product_id = s.product_id""",
    """CREATE TABLE dev.main.orders AS
       WITH order_items_summary AS (
           SELECT order_id, SUM(supply_cost) AS order_cost,
                  SUM(product_price) AS order_items_subtotal
           FROM dev.main.order_items GROUP BY order_id
       )
       SELECT o.order_id, o.ordered_at, o.subtotal,
              s.order_cost, s.order_items_subtotal
       FROM dev.main.stg_orders o
       LEFT JOIN order_items_summary s ON o.order_id = s.order_id""",
)

# Same SUM inputs and default ordered_at day on each semantic model. The full
# outer join exposes missing days, and the line-item expression independently
# checks the resulting arithmetic on represented item days.
DAILY_SQL = """WITH revenue_by_day AS (
    SELECT ordered_at AS day, SUM(product_price) AS revenue
    FROM dev.main.order_items GROUP BY 1
), cost_by_day AS (
    SELECT ordered_at AS day, SUM(order_cost) AS cost
    FROM dev.main.orders GROUP BY 1
), direct_by_day AS (
    SELECT ordered_at AS day, SUM(product_price - supply_cost) AS direct_profit
    FROM dev.main.order_items GROUP BY 1
)
SELECT COALESCE(r.day, c.day) AS day, r.revenue, c.cost,
       r.revenue - c.cost AS derived_profit, d.direct_profit,
       r.day IS NULL AS missing_revenue_group,
       c.day IS NULL AS missing_cost_group
FROM revenue_by_day r FULL OUTER JOIN cost_by_day c ON r.day = c.day
LEFT JOIN direct_by_day d ON d.day = COALESCE(r.day, c.day)
ORDER BY 1"""

# Per-order mapping is a diagnostic using the order_id relation. Absent item
# groups have no SUM value; zero fill is shown as an explicit alternate policy.
ORDER_SQL = """WITH revenue_by_order AS (
    SELECT order_id, SUM(product_price) AS revenue,
           SUM(product_price - supply_cost) AS direct_profit
    FROM dev.main.order_items GROUP BY 1
)
SELECT o.order_id, o.ordered_at AS day, r.revenue, o.order_cost AS cost,
       r.revenue - o.order_cost AS derived_profit, r.direct_profit,
       COALESCE(r.revenue, 0) - COALESCE(o.order_cost, 0) AS zero_filled_profit,
       r.order_id IS NULL AS missing_item_group
FROM dev.main.orders o LEFT JOIN revenue_by_order r ON o.order_id = r.order_id
ORDER BY o.ordered_at, o.order_id"""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_pins(repo):
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if head != COMMIT:
        raise ValueError(f"Expected {COMMIT}; found {head}")
    for relative, expected in SOURCE_HASHES.items():
        local = sha256(repo / relative)
        committed = hashlib.sha256(subprocess.check_output(
            ["git", "-C", str(repo), "show", f"HEAD:{relative}"])).hexdigest()
        if local != expected or committed != expected:
            raise ValueError(f"Source or seed pin failed: {relative}: {local} / {committed}")
    sql_dir = ROOT / "metric_provenance_verification" / "generated_sql"
    for name, expected in SQL_HASHES.items():
        if sha256(sql_dir / f"{name}.sql") != expected:
            raise ValueError(f"Compiled SQL pin failed: {name}")
    return sql_dir


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def build(conn, repo):
    conn.execute("ATTACH ':memory:' AS dev")
    for name in ("orders", "items", "products", "supplies"):
        path = repo / "seeds" / "jaffle-data" / f"raw_{name}.csv"
        conn.execute(f"CREATE TABLE dev.main.raw_{name} AS SELECT * FROM "
                     f"read_csv({sql_literal(path)}, header=true, all_varchar=true)")
    for statement in BUILD_SQL:
        conn.execute(statement)


def scalar(conn, query):
    return conn.execute(query).fetchone()[0]


def observe(conn, sql_dir):
    values = {name: scalar(conn, (sql_dir / f"{name}.sql").read_text())
              for name in SQL_HASHES}
    direct = scalar(conn, "SELECT SUM(product_price - supply_cost) FROM dev.main.order_items")
    if values["order_gross_profit"] != values["revenue"] - values["order_cost"]:
        raise AssertionError("Ungrouped compiler expression differed from its inputs")
    counts = {name: scalar(conn, f"SELECT COUNT(*) FROM dev.main.{name}")
              for name in ("raw_orders", "raw_items", "raw_products", "raw_supplies", "orders", "order_items")}
    integrity = conn.execute("""SELECT
        (SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM dev.main.orders),
        (SELECT COUNT(*)-COUNT(DISTINCT order_item_id) FROM dev.main.order_items),
        (SELECT COUNT(*) FROM dev.main.order_items WHERE ordered_at IS NULL),
        (SELECT COUNT(*) FROM dev.main.order_items WHERE product_price IS NULL),
        (SELECT COUNT(*) FROM dev.main.order_items WHERE supply_cost IS NULL),
        (SELECT COUNT(*) FROM dev.main.orders WHERE order_cost IS NULL)
    """).fetchone()
    if any(integrity[:5]) or counts["raw_orders"] != counts["orders"] or counts["raw_items"] != counts["order_items"]:
        raise AssertionError(f"Unexpected source mapping, key, or price/cost null: {counts}, {integrity}")
    daily = conn.execute(DAILY_SQL).fetchall()
    orders = conn.execute(ORDER_SQL).fetchall()
    daily_diff = [row for row in daily if row[3] != row[4]]
    order_diff = [row for row in orders if row[4] != row[5]]
    absent = [row for row in orders if row[7]]
    present = [row for row in orders if not row[7]]
    if len(orders) != counts["orders"] or len(absent) != integrity[5]:
        raise AssertionError("Order coverage/null reconciliation failed")
    return values, direct, counts, integrity, daily, daily_diff, orders, order_diff, absent, present


def fenced(sql):
    return "```sql\n" + sql.strip() + "\n```"


def report(result, sql_dir, version):
    values, direct, counts, integrity, daily, daily_diff, orders, order_diff, absent, present = result
    missing_day_revenue = sum(row[5] for row in daily)
    missing_day_cost = sum(row[6] for row in daily)
    null_day_profit = sum(row[3] is None for row in daily)
    null_order_profit = sum(row[4] is None for row in orders)
    nonnull_diff = sum(row[4] is not None and row[4] != row[5] for row in orders)
    filled_nonzero = sum(row[6] != 0 for row in absent)
    example = absent[0] if absent else None
    start, end = daily[0][0], daily[-1][0]
    source_lines = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in SOURCE_HASHES.items())
    sql_lines = "\n".join(f"| `{name}.sql` | `{digest}` |" for name, digest in SQL_HASHES.items())
    compiled = "\n\n".join(f"**{name}**\n\n{fenced((sql_dir / f'{name}.sql').read_text())}"
                           for name in ("revenue", "order_cost", "order_gross_profit"))
    example_text = (f"`{example[0]}` on `{example[1]}`: item revenue `NULL` (no group), "
                    f"order cost `NULL`, derived difference `NULL`, explicit zero-filled difference "
                    f"`{example[6]:.2f}`." if example else "None on this sample.")
    return f"""# Jaffle Shop gross-profit dependency: bounded development observation

Public source: `dbt-labs/jaffle-shop@{COMMIT}` (the already inspected Jaffle Shop submodule checkout). Executed with DuckDB `{version}` using four pinned public seeds in an **in-memory** catalog. The selected staging and mart columns in the script follow the pinned model joins, grouped supply costs, order summary, day truncation, and `DECIMAL(16,2)` cents conversion. The three ungrouped queries below are pinned MetricFlow SQL from the prior same-commit parse; they execute here on the reconstructed tables. The daily and per-order queries are explicitly scoped SQL, not native MetricFlow compilations at those grains.

## Result and scope

The YAML declares `order_gross_profit` as `revenue - cost`, with `cost` an alias for input metric `order_cost`. `revenue` sums `order_items.product_price`; `order_cost` sums `orders.order_cost`, itself the per-order sum of item supply costs. Both semantic models default to `ordered_at` at day grain. This is a **definition dependency**, while the observations below concern only these pinned public rows and query scopes.

| Ungrouped compiled metric | Dollars |
| --- | ---: |
| `revenue` | {values['revenue']:.2f} |
| `order_cost` | {values['order_cost']:.2f} |
| `order_gross_profit` | {values['order_gross_profit']:.2f} |
| Independent item `SUM(product_price - supply_cost)` | {direct:.2f} |

| Scoped comparison with independent item expression | Groups | Non-NULL derived groups | NULL-aware differences |
| --- | ---: | ---: | ---: |
| `ordered_at` day, `{start}`–`{end}` | {len(daily)} | {len(daily) - null_day_profit} | {len(daily_diff)} |
| `order_id` on all orders | {len(orders)} | {len(orders) - null_order_profit} | {len(order_diff)} ({nonnull_diff} among non-NULL values) |

Counts: {counts['raw_orders']:,} raw orders, {counts['raw_items']:,} raw items, {counts['raw_products']} products, {counts['raw_supplies']} supplies; reconstructed {counts['orders']:,} order rows and {counts['order_items']:,} item rows. {len(daily)} union dates ({start} through {end}); {missing_day_revenue} dates without a revenue group, {missing_day_cost} without a cost group, {null_day_profit} dates with NULL derived profit. {len(absent)} orders have no item group. Duplicate order IDs: {integrity[0]}; duplicate item IDs: {integrity[1]}; items without order time, product price, supply cost: {integrity[2]}, {integrity[3]}, {integrity[4]}. The per-order derived expression is NULL on {null_order_profit} orders; an explicit `COALESCE` on *both* measures makes those {len(absent)} differences zero ({filled_nonzero} nonzero after fill). The ungrouped totals omit NULL order costs under `SUM` and have represented item rows, so their values reconcile.

**Concrete missing-group case:** {example_text} No numeric counterexample was found among comparable non-NULL scalar, day, or order results. An order-grain claim that every order has a numeric gross profit is false without a stated zero-fill rule. NULL-aware equality treats each missing group differently from a numeric zero; two NULL diagnostics on the same absent order do not constitute an observed numeric match.

## Executed queries

Pinned ungrouped MetricFlow SQL (hashes below):

{compiled}

The following daily query aligns each metric to its own model's `ordered_at` day and compares with an independently computed item expression:

{fenced(DAILY_SQL)}

The following order diagnostic joins by `order_id`; `zero_filled_profit` is an **extra hypothetical policy**, not a property of the declared derived metric:

{fenced(ORDER_SQL)}

Reconstruction SQL is in `experiment_gross_profit.py` (`BUILD_SQL`); it creates `dev.main.order_items` and `dev.main.orders` in memory. Run from this workspace with:

```bash
metric_matching_dev_build_20260928/venv/bin/python metric_matching_pilot/experiment_gross_profit.py
```

## Exact pins (SHA-256)

Git HEAD and each local source byte stream were checked against the expected hash and Git `HEAD:path`; no dependency was read from an unpinned checkout. Source and seed hashes:

| Commit-relative path | SHA-256 |
| --- | --- |
{source_lines}

Prior same-commit compiled query files under `metric_provenance_verification/generated_sql/`:

| File | SHA-256 |
| --- | --- |
{sql_lines}

**Limit:** One finite, curated public sample on DuckDB. Model SQL is reconstructed for relevant columns, while the ungrouped metric queries are executed verbatim. The daily and order comparisons are manual scoped analogues and cannot establish a general identity across filters, future rows, missing groups, other times, or other engines. This is neither a reference label nor a method result. No held-out source or worksheet was accessed.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path,
                        default=ROOT / "public_corpus/jaffle-shop-sidemantic/jaffle-shop")
    args = parser.parse_args()
    repo = args.repo.resolve()
    sql_dir = verify_pins(repo)
    conn = duckdb.connect(":memory:")
    try:
        build(conn, repo)
        result = observe(conn, sql_dir)
    finally:
        conn.close()
    output = Path(__file__).with_name("experiment_gross_profit_report.md")
    output.write_text(report(result, sql_dir, duckdb.__version__), encoding="utf-8")
    print(f"Ungrouped: {result[0]['order_gross_profit']:.2f}; "
          f"daily differences: {len(result[5])}/{len(result[4])}; "
          f"orders without items: {len(result[8])}/{len(result[6])}; report: {output}")


if __name__ == "__main__":
    main()
