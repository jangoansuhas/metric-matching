# Pinned Jaffle Shop: MetricFlow grouped revenue scope probe

## Scope and provenance

Public `dbt-labs/jaffle-shop` checkout at `7be2c5838dbdeca8e915d4e46db70e910753d7f6`; previous same-commit archive SHA-256 `7af864659e9b579296bba0766181ec7dc155c00fc05aba267bda28a1b9f3e88e`. The checkout HEAD, every local source/seed byte stream, its committed Git blob, both existing parse manifests, and three archived scalar SQL files were checked against fixed hashes **before** loading rows. Previous `run_metadata.json` supplies the commit/archive identity; it was not regenerated. The manifest binds all three simple `sum` metrics to `order_item` / `order_items`, default `ordered_at` time, with expressions `product_price`, `case when is_food_item then product_price else 0 end`, and `case when is_drink_item then product_price else 0 end`.

The program reconstructed the selected model columns from pinned public CSVs in a disposable `/tmp` DuckDB file (`dev.main.order_items`). It computed `stg_products` flags with `COALESCE` first, then left-joined the staged products into the mart, preserving NULL flags on an absent product; it also used the source order join, day truncation, and cents conversion to `NUMERIC(16,2)`. The compiled mart's supply summary is one row per product and its columns are not used by these metrics; this is a **selected-column SQL reconstruction**, not a dbt build. It loaded the prior same-commit `manifest.json` and `semantic_manifest.json` into a disposable project and called `mf query --metrics <name> --group-by metric_time__day --explain` and the corresponding `--csv` execution for **each** metric, with no time bounds or metric filters. All query files, profile, and database were external to this workspace and removed after execution. Runtime: `dbt-metricflow 0.15.0` / `metricflow 0.213.0`, DuckDB `1.5.6`.

## Seed observations and aligned day comparison

Raw rows: items **90,900**, orders **61,948**, products **10**. Reconstructed item rows **90,900**; duplicate item IDs **0**, duplicate product SKUs **0**, missing order mappings **0**, missing product mappings/NULL prices **0/0**, NULL order times **0**. Food flagged rows **20,081**, drink flagged rows **70,819**, both flags **0**. These public seeds have complete, exclusive food/drink classification and non-NULL prices; that property is empirical.

All three CLI results and direct executions of their freshly generated SQL have **365 distinct, identical day keys** (`2024-09-01` through `2025-08-31`), covering every calendar day in that span. No duplicate key, NULL day key, or NULL metric value occurred in the seed output. The raw-seed control groups **365 days** and **90,900 item rows**. It computes integer cents by product type from independent raw joins and converts only the resulting sums to dollars. Every day and each metric matches this control with exact decimal values. On all 365 observed days, revenue equals food plus drink revenue; the three sums also match their separately archived ungrouped MetricFlow SQL on this reconstructed table.

| Fresh MetricFlow SQL | SHA-256 (UTF-8, terminal newline) | Day groups | NULL values | Sum of groups ($) |
| --- | --- | ---: | ---: | ---: |
| `revenue` day | `5e4e6b4485853ddf7a1d0ffbd9f9d480bae0ee6336f172b5fc6f72fdb19723c4` | 365 | 0 | 637,444.00 |
| `food_revenue` day | `8446f5e5ff32c2f3367519c6874fe360bd35264acafa30a50132066bf068604a` | 365 | 0 | 240,877.00 |
| `drink_revenue` day | `55823a9a95b8f71a7977a30885a4cabbecf1b6158ed83e1fa9f6696bafd99da8` | 365 | 0 | 396,567.00 |

| Day example | Item rows | Revenue ($) | Food ($) | Drink ($) |
| --- | ---: | ---: | ---: | ---: |
| `2024-09-01` | 73 | 470.00 | 86.00 | 384.00 |
| `2025-03-02` | 203 | 1,402.00 | 462.00 | 940.00 |
| `2025-07-16` | 342 | 2,910.00 | 1,802.00 | 1,108.00 |

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
SELECT CAST(DATE_TRUNC('day', CAST(o.ordered_at AS TIMESTAMP)) AS DATE) AS day,
       COUNT(*) AS item_rows,
       SUM(CAST(p.price AS BIGINT)) AS revenue_cents,
       SUM(CASE WHEN p.type = 'jaffle' THEN CAST(p.price AS BIGINT) ELSE 0 END) AS food_cents,
       SUM(CASE WHEN p.type = 'beverage' THEN CAST(p.price AS BIGINT) ELSE 0 END) AS drink_cents
FROM raw_items i
LEFT JOIN raw_orders o ON i.order_id = o.id
LEFT JOIN raw_products p ON i.sku = p.sku
GROUP BY 1 ORDER BY 1
```

Staged product relation, then selected-column reconstructed mart:

```sql
CREATE TABLE stg_products AS
SELECT sku AS product_id,
       (CAST(price AS BIGINT) / 100)::NUMERIC(16,2) AS product_price,
       COALESCE(type = 'jaffle', FALSE) AS is_food_item,
       COALESCE(type = 'beverage', FALSE) AS is_drink_item
FROM raw_products
```

```sql
CREATE TABLE order_items AS
SELECT i.id AS order_item_id, i.order_id, i.sku AS product_id,
       DATE_TRUNC('day', CAST(o.ordered_at AS TIMESTAMP)) AS ordered_at,
       p.product_price, p.is_food_item, p.is_drink_item
FROM raw_items i
LEFT JOIN raw_orders o ON i.order_id = o.id
LEFT JOIN stg_products p ON i.sku = p.product_id
```

**`revenue` day SQL** (SHA-256 `5e4e6b4485853ddf7a1d0ffbd9f9d480bae0ee6336f172b5fc6f72fdb19723c4`):

```sql
SELECT
  DATE_TRUNC('day', ordered_at) AS metric_time__day
  , SUM(product_price) AS revenue
FROM "dev"."main"."order_items" order_item_src_10000
GROUP BY
  DATE_TRUNC('day', ordered_at)
```

**`food_revenue` day SQL** (SHA-256 `8446f5e5ff32c2f3367519c6874fe360bd35264acafa30a50132066bf068604a`):

```sql
SELECT
  metric_time__day
  , SUM(__food_revenue) AS food_revenue
FROM (
  SELECT
    DATE_TRUNC('day', ordered_at) AS metric_time__day
    , case when is_food_item then product_price else 0 end AS __food_revenue
  FROM "dev"."main"."order_items" order_item_src_10000
) subq_3
GROUP BY
  metric_time__day
```

**`drink_revenue` day SQL** (SHA-256 `55823a9a95b8f71a7977a30885a4cabbecf1b6158ed83e1fa9f6696bafd99da8`):

```sql
SELECT
  metric_time__day
  , SUM(__drink_revenue) AS drink_revenue
FROM (
  SELECT
    DATE_TRUNC('day', ordered_at) AS metric_time__day
    , case when is_drink_item then product_price else 0 end AS __drink_revenue
  FROM "dev"."main"."order_items" order_item_src_10000
) subq_3
GROUP BY
  metric_time__day
```

The three existing **ungrouped** SQL files, used to reconcile sums and check empty scalar behavior, have the hashes below. The day SQL above was freshly generated and executed; it is not an archived grouped query.

| Prior provenance input (relative to `metric_provenance_verification`) | SHA-256 |
| --- | --- |
| `manifests/manifest.json` | `8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42` |
| `manifests/semantic_manifest.json` | `bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51` |
| `generated_sql/revenue.sql` | `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134` |
| `generated_sql/food_revenue.sql` | `682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110` |
| `generated_sql/drink_revenue.sql` | `3e1d04e6f6a6ac412fdab159503b76feb0ae180b59f8a63900c293e0bf09d613` |

| Pinned source or seed (relative to the public checkout) | SHA-256 |
| --- | --- |
| `dbt_project.yml` | `f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122` |
| `models/marts/order_items.yml` | `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97` |
| `models/marts/order_items.sql` | `7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639` |
| `models/staging/stg_order_items.sql` | `102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04` |
| `models/staging/stg_orders.sql` | `9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327` |
| `models/staging/stg_products.sql` | `062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6` |
| `macros/cents_to_dollars.sql` | `5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb` |
| `seeds/jaffle-data/raw_items.csv` | `bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca` |
| `seeds/jaffle-data/raw_orders.csv` | `e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b` |
| `seeds/jaffle-data/raw_products.csv` | `01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d` |

## Interpretation and reproduction

This is a finite development observation under one pinned dataset, reconstruction, manifest, and day grouping. The declared CASE expressions explain why both components partition these rows when product types are exclusively `jaffle` or `beverage`, but they do not guarantee that partition on other products, missing prices, NULL flags, filters, or other data. No universal equivalence, human gold relationship, held-out repository, worksheet, or method performance is claimed.

Run from the workspace root with `metric_matching_dev_build_20260928/venv/bin/python -B metric_matching_pilot/probe_grouped_scope.py`. It checks pins and binding, compiles and runs three CLI queries, checks direct SQL and raw-cent control, runs the isolated NULL/empty fixtures, and writes only this report. Script SHA-256 `de91507dbd8094e4d52165dce695e79a38477a9d62f549b11b448a31b375f9aa`.
