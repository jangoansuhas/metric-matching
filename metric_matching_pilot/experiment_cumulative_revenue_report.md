# Jaffle Shop: `cumulative_revenue` and `revenue` (bounded development experiment)

## Source and method

- Public source: `dbt-labs/jaffle-shop` commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. The existing provenance run archived this commit (tar SHA-256 `7af864659e9b579296bba0766181ec7dc155c00fc05aba267bda28a1b9f3e88e`). This script checks its `run_metadata.json` and **asserts** fixed expected hashes for every source file used in the reconstruction and all four seed CSVs before building or compiling. These expected values pin the previously archived local copy; this run does not independently call Git HEAD, `git archive`, or `dbt parse`.
- `models/marts/order_items.yml` SHA-256 `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97`: lines 71–74 declare measure `revenue`, aggregation `sum`, expression `product_price`; lines 90–95 declare simple metric `revenue` over that measure; lines 162–167 declare cumulative metric `cumulative_revenue` over the **same** measure with no window or grain-to-date parameter. The `order_item` semantic model uses `ordered_at` as its aggregation time dimension. The checked semantic manifest agrees.
- Parsed `manifest.json` SHA-256 `8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42`; `semantic_manifest.json` SHA-256 `bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51`. These are the prior clean, same-commit parse artifacts, loaded into a temporary project for **new** MetricFlow compilation. `dbt_project.yml` SHA-256 `f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122`.
- Runtime: local `dbt-metricflow 0.15.0` / `metricflow 0.213.0` and DuckDB `1.5.6`. Query bounds (inclusive): `2024-09-01` through `2025-08-31`; `--group-by metric_time__month`. No external warehouse, held-out input, worksheet, relationship label, or human gold was used.

Pinned source hashes (all asserted before execution):

| Pinned source file | Expected and verified SHA-256 |
|---|---|
| `dbt_project.yml` | `f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122` |
| `models/marts/order_items.yml` | `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97` |
| `models/marts/order_items.sql` | `7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639` |
| `models/marts/metricflow_time_spine.sql` | `1e8de1247e68fe0f70de20000d0ae5d7ebb60b1e3c56202d233ea96cb8429ecf` |
| `models/staging/stg_order_items.sql` | `102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04` |
| `models/staging/stg_orders.sql` | `9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327` |
| `models/staging/stg_products.sql` | `062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6` |
| `models/staging/stg_supplies.sql` | `1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4` |
| `macros/cents_to_dollars.sql` | `5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb` |


### Public seed inputs

All four CSV hashes below are compared against fixed expected values before any seed is read:

| CSV | Rows | SHA-256 |
|---|---:|---|
| `raw_orders.csv` | 61,948 | `e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b` |
| `raw_items.csv` | 90,900 | `bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca` |
| `raw_products.csv` | 10 | `01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d` |
| `raw_supplies.csv` | 65 | `309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1` |

The temporary `order_items` has 90,900 unique item rows, no missing date or price, and a sum of $637,444.00. The daily spine slice contains 365 days. Both are **direct SQL reconstructions**, not a `dbt seed`/`dbt run` build. The original `metricflow_time_spine.sql` calls `dbt_date.get_base_dates(n_dateparts=365*10, datepart='day')`; its materialized contents were not used here. The explicit slice covers every date selected by the bounded compiled SQL.

Reconstruction SQL (`?` parameters in order: `raw_supplies`, `raw_items`, `raw_orders`, `raw_products`):

```sql
CREATE TABLE order_items AS
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
LEFT JOIN order_supplies_summary s ON i.sku = s.product_id
```

Time spine slice:

```sql
CREATE TABLE metricflow_time_spine AS
SELECT CAST(date_day AS DATE) AS date_day
FROM generate_series(DATE '2024-09-01', DATE '2025-08-31', INTERVAL 1 DAY)
  AS days(date_day)
```

## Generated and executed SQL

`mf query --metrics <name> --explain` compiled both scalar queries. The regenerated SQL equals the previously archived `generated_sql/{revenue,cumulative_revenue}.sql` byte for byte. Ignoring only the output alias, both are `SUM(product_price)` over `"dev"."main"."order_items"`. Each executed to **$637,444.00**, verified via MetricFlow CLI CSV and the direct model sum.

```sql
SELECT
  SUM(product_price) AS revenue
FROM "dev"."main"."order_items" order_item_src_10000
```

```sql
SELECT
  SUM(product_price) AS cumulative_revenue
FROM "dev"."main"."order_items" order_item_src_10000
```

For the time-grain queries, the program issued `mf query --metrics <name> --group-by metric_time__month --start-time 2024-09-01 --end-time 2025-08-31 --explain`, then the same calls without `--explain` and with `--csv` into the temporary directory. It also executed each extracted SQL statement directly in DuckDB. The CLI CSV and direct execution agree by month, and the results agree with a separate seed-model control query.

| SQL (MetricFlow) | SHA-256, UTF-8 with terminal newline |
|---|---|
| `revenue` ungrouped | `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134` |
| `cumulative_revenue` ungrouped | `a157e77b8a38a9d368574a4063ac2831eae81557cb7ccf4dc70fe823725fe798` |
| `revenue` bounded month | `a72932f3a655389be5352cf5355eb20b652e9c00c8f0d524dc4ab57f6a9d6d21` |
| `cumulative_revenue` bounded month | `b914f6be26330147517fa25d1977e82ff63ef4577392a4279b8180cbd24dc3f3` |

Bounded **revenue** SQL, emitted by MetricFlow:

```sql
SELECT
  DATE_TRUNC('month', ordered_at) AS metric_time__month
  , SUM(product_price) AS revenue
FROM "dev"."main"."order_items" order_item_src_10000
WHERE DATE_TRUNC('day', ordered_at) BETWEEN '2024-09-01' AND '2025-08-31'
GROUP BY
  DATE_TRUNC('month', ordered_at)
```

Bounded **cumulative_revenue** SQL, emitted by MetricFlow:

```sql
SELECT
  metric_time__month
  , cumulative_revenue
FROM (
  SELECT
    metric_time__month
    , FIRST_VALUE(cumulative_revenue) OVER (
      PARTITION BY metric_time__month
      ORDER BY metric_time__day
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS cumulative_revenue
  FROM (
    SELECT
      subq_7.metric_time__day AS metric_time__day
      , subq_7.metric_time__month AS metric_time__month
      , SUM(subq_6.__revenue) AS cumulative_revenue
    FROM (
      SELECT
        date_day AS metric_time__day
        , DATE_TRUNC('month', date_day) AS metric_time__month
      FROM "dev"."main"."metricflow_time_spine" subq_8
      WHERE date_day BETWEEN '2024-09-01' AND '2025-08-31'
    ) subq_7
    INNER JOIN (
      SELECT
        DATE_TRUNC('day', ordered_at) AS metric_time__day
        , product_price AS __revenue
      FROM "dev"."main"."order_items" order_item_src_10000
      WHERE DATE_TRUNC('day', ordered_at) BETWEEN '2000-01-01' AND '2025-08-31'
    ) subq_6
    ON
      (subq_6.metric_time__day <= subq_7.metric_time__day)
    WHERE subq_7.metric_time__day BETWEEN '2024-09-01' AND '2025-08-31'
    GROUP BY
      subq_7.metric_time__day
      , subq_7.metric_time__month
  ) subq_15
) subq_16
GROUP BY
  metric_time__month
  , cumulative_revenue
```

## Results (12 months per query)

| Month | Item rows | Month-start items | Revenue | MetricFlow cumulative | Direct end-of-month control |
|---|---:|---:|---:|---:|---:|
| 2024-09 | 2,190 | 73 | $15,218.00 | $470.00 | $15,218.00 |
| 2024-10 | 2,698 | 57 | $19,422.00 | $15,670.00 | $34,640.00 |
| 2024-11 | 3,404 | 113 | $24,135.00 | $35,436.00 | $58,775.00 |
| 2024-12 | 4,471 | 195 | $32,166.00 | $60,183.00 | $90,941.00 |
| 2025-01 | 5,275 | 113 | $37,824.00 | $91,887.00 | $128,765.00 |
| 2025-02 | 5,192 | 216 | $37,023.00 | $130,285.00 | $165,788.00 |
| 2025-03 | 9,065 | 187 | $64,006.00 | $167,048.00 | $229,794.00 |
| 2025-04 | 10,143 | 246 | $72,599.00 | $231,871.00 | $302,393.00 |
| 2025-05 | 11,631 | 415 | $81,715.00 | $305,228.00 | $384,108.00 |
| 2025-06 | 11,889 | 485 | $82,613.00 | $387,436.00 | $466,721.00 |
| 2025-07 | 11,740 | 281 | $80,994.00 | $469,060.00 | $547,715.00 |
| 2025-08 | 13,202 | 418 | $89,729.00 | $550,386.00 | $637,444.00 |

Every one of the 12 month-start dates has item rows in the reconstructed model (minimum 57; the table gives each count). The explicit assertion makes the first-calendar-day reading below valid for this bounded seed run.

Independent control query over the reconstructed item relation (the month-end column is a direct reference value, not a MetricFlow metric):

```sql
WITH months AS (
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
FROM months m ORDER BY m.month
```

The `MetricFlow cumulative` column takes `FIRST_VALUE` by day within each month after summing all item prices on or before that day. For this bounded daily spine it is **the running total through the first calendar day of each month**, including that day's items. It is neither that month's revenue nor the month-end cumulative sum.

Concrete counterexample, October 2024: September revenue is $15,218.00; October 1 adds $452.00, giving the MetricFlow October cumulative value **$15,670.00**. October's own revenue is **$19,422.00**. The direct end-of-October running total is **$34,640.00**. Scalar equality ($637,444.00 for both metrics) therefore does not imply equality at month grain.

## Interpretation boundary and reproduction

The SQL marked MetricFlow above was genuinely compiled from the prior pinned manifest and executed both by `mf query` and directly. The `order_items` and time-spine relations were reconstructed from public CSVs and a bounded date series; a fresh dbt dependency installation, seed load, model build, and original ten-year time-spine materialization were **not tested**. The observed month values are conditional on those reconstructions and this inclusive date window. They are a within-project counterexample to treating ungrouped SQL identity as all-grain identity; they establish no matching gold label, model superiority, or cross-project result.

Reproduce from the workspace root with `metric_matching_dev_build_20260928/venv/bin/python metric_matching_pilot/experiment_cumulative_revenue.py`. The script asserts the fixed source, seed, and manifest hashes, checks all month-start item counts, compiles four MetricFlow statements, executes four MetricFlow queries, directly executes the two month statements, checks the control totals, and rewrites only this report in the workspace. Script SHA-256 `0c3078abb8138f795489fc7a7e2fc7ee179f679615e13495c1d35bbbc6174ab9`. The temporary project and database are removed on exit.
