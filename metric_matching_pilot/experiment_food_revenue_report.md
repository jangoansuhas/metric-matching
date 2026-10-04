# `food_revenue` vs `revenue`: finite public seed experiment

Repository: `dbt-labs/jaffle-shop` at `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. Executed locally with DuckDB `1.5.6` in one `:memory:` connection; both attached catalogs are also `:memory:`. No existing database was opened or modified. This is a development observation, not a human gold label or a method comparison.

## Source and query scope

Both simple metrics resolve in the verified semantic manifest to the same `order_item` model (`order_items`, one row per order item), `sum` aggregation, and default time dimension `ordered_at`. The declared `revenue` expression is `product_price`; `food_revenue` is `case when is_food_item then product_price else 0 end`. In staging, `product_price` is `(price / 100)::numeric(16, 2)` and `is_food_item` is `coalesce(type = 'jaffle', false)`. The compiled `order_items` model left-joins orders, products, and per-product supply totals. The experiment loads four CSV seeds, projects the required staging columns using the source expressions, executes the pinned compiled supply and order-item models, and exposes the result under the `dev` catalog to execute the two archived MetricFlow total queries **unchanged**. The grouped queries below are constructed from the same declared expressions; they are experiment SQL, not archived MetricFlow-generated grouped SQL.

Input rows: raw items **90,900**, raw orders **61,948**, raw products **10**, raw supplies **65**; resulting `order_items` **90,900** rows and **90,900** distinct item IDs. Missing product prices **0**; negative prices **0**; zero prices **0**; food item rows **20,081**; masked (non-food or null-flag) rows **70,819**; missing `ordered_at` **0**. The mart row count equals the raw item count; the query did not fan out item rows on these seeds.

The raw order IDs are unique (**61,948**). **483** raw orders have no item row, so they do not appear in the `order_id` grouping; the other **61,465** orders do.

## Observed values

All monetary values are dollars (`DECIMAL` aggregation); equality checks used DuckDB decimal values without a floating-point tolerance.

| Scope | Groups | Equal | Different | NULL result | Sum revenue | Sum food revenue |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Total (one scalar) | 1 | 0 | 1 | 0 | 637,444.00 | 240,877.00 |
| `ordered_at` day | 365 | 0 | 365 | 0 | 637,444.00 | 240,877.00 |
| `order_id` | 61,465 | 1,131 | 60,334 | 0 | 637,444.00 | 240,877.00 |

Total difference (`revenue - food_revenue`): **396,567.00**. Group sums reconcile exactly to both independently executed generated totals.

| Example | Group key | Revenue | Food revenue | Difference | Item rows | Food / masked rows | Masked price sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Different day | `2024-09-01` | 470.00 | 86.00 | 384.00 | 73 | 7 / 66 | 384.00 |
| Equal day | none observed | — | — | — | — | — | — |
| Different order | `0004b076-5866-45a9-afdf-24d1cb9c702a` | 5.00 | 0.00 | 5.00 | 1 | 0 / 1 | 5.00 |
| Equal order | `003ec4ff-163a-4bee-8e03-f826a0a5fedd` | 22.00 | 22.00 | 0.00 | 2 | 2 / 0 | 0.00 |

The examples are the first keys in ascending SQL order for each category. An equal group demonstrates only equality at that grouping on these rows. A different group gives a direct counterexample to substituting the two metric values in that scope.

## SQL executed

The archived MetricFlow-generated **total** statements were executed byte-for-byte (file hashes below):

`revenue`:

```sql
SELECT
  SUM(product_price) AS revenue
FROM "dev"."main"."order_items" order_item_src_10000
```

`food_revenue`:

```sql
SELECT
  SUM(case when is_food_item then product_price else 0 end) AS food_revenue
FROM "dev"."main"."order_items" order_item_src_10000
```

Shared `ordered_at` day grouping (constructed from the verified measure expressions):

```sql
SELECT CAST(ordered_at AS DATE) AS metric_time__day,
       SUM(product_price) AS revenue,
       SUM(case when is_food_item then product_price else 0 end) AS food_revenue,
       COUNT(*) AS item_rows,
       COUNT(*) FILTER (WHERE is_food_item IS TRUE) AS food_rows,
       COUNT(*) FILTER (WHERE is_food_item IS NOT TRUE) AS nonfood_rows,
       SUM(CASE WHEN is_food_item IS NOT TRUE THEN product_price ELSE 0 END) AS masked_revenue
FROM "jaffle_dev"."main"."order_items"
GROUP BY 1
ORDER BY 1
```

Shared order grouping (same expressions, key from `order_items`):

```sql
SELECT order_id AS order_id,
       SUM(product_price) AS revenue,
       SUM(case when is_food_item then product_price else 0 end) AS food_revenue,
       COUNT(*) AS item_rows,
       COUNT(*) FILTER (WHERE is_food_item IS TRUE) AS food_rows,
       COUNT(*) FILTER (WHERE is_food_item IS NOT TRUE) AS nonfood_rows,
       SUM(CASE WHEN is_food_item IS NOT TRUE THEN product_price ELSE 0 END) AS masked_revenue
FROM "jaffle_dev"."main"."order_items"
GROUP BY 1
ORDER BY 1
```

The exact staging projection SQL and `CREATE TABLE ... AS` loading procedure are in `experiment_food_revenue.py`; the compiled supply and order-item SQL are read and executed verbatim from the hashed files below. A `dev.main.order_items` in-memory view supplies the archived total statements' original relation name.

## Input SHA-256 (exact bytes)

| Input relative to workspace root | SHA-256 |
| --- | --- |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.yml` | `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/marts/order_items.sql` | `7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_order_items.sql` | `102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_orders.sql` | `9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_products.sql` | `062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/models/staging/stg_supplies.sql` | `1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/macros/cents_to_dollars.sql` | `5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_items.csv` | `bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_orders.csv` | `e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_products.csv` | `01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d` |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop/seeds/jaffle-data/raw_supplies.csv` | `309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1` |
| `build_verification/order_cost_build_7be2c58/compiled/jaffle_shop/models/marts/order_items.sql` | `508b47c1522cb633c05bf896a9f6ab3247ef3689e9f36d52883aaa68f1339b29` |
| `build_verification/order_cost_build_7be2c58/compiled/jaffle_shop/models/staging/stg_supplies.sql` | `0fa0d78a4aacc5c32cbd710ca163f4a58019fd93744fb21928941735f2ae59c3` |
| `metric_provenance_verification/manifests/manifest.json` | `8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42` |
| `metric_provenance_verification/manifests/semantic_manifest.json` | `bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51` |
| `metric_provenance_verification/generated_sql/revenue.sql` | `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134` |
| `metric_provenance_verification/generated_sql/food_revenue.sql` | `682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110` |

## Interpretation and limits

**Source-supported relation:** on the same order-item rows, `food_revenue` replaces each non-food (or unknown-flag) price with zero before summing; `revenue` sums all prices. It is a food-scoped component of the unfiltered revenue expression. The source expressions alone do not guarantee a strict inequality at every grouping: a group may have only food rows, zero non-food prices, or negative prices. NULL and empty-input behavior also matters in other data. The positive-price, non-null observations and counts above belong to these local seeds only.

**Empirical result:** these seeds give the displayed total and group counts; the different groups refute value equivalence for those scopes here. The source path explains the observed difference, while the finite sample does not establish values for other datasets, filters, time windows, or future commits. No held-out source or practice worksheet was read for this run, no human gold label was assigned, and no method superiority follows from this experiment.
