# Flag lineage probe — pinned Jaffle development evidence

Git HEAD: `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. Scope: the `food_revenue`/`revenue` and `drink_revenue`/`revenue` hypotheses in the existing 19-metric, 171-pair packet. These are source-linked conditional scope observations, not pair labels or universal equivalence.

## Checked source chain

| Link | Exact source span | Observation |
| --- | --- | --- |
| Metric and measure | `models/marts/order_items.yml:90-95,108-119,71-82` | `revenue` binds to `sum(product_price)`; `food_revenue` and `drink_revenue` bind to `sum(case when is_food_item/is_drink_item then product_price else 0 end)`, respectively. |
| Mart projections and join | `models/marts/order_items.sql:16-18,43-59,66` | `products.product_price`, `products.is_food_item`, and `products.is_drink_item` come through the `products` CTE, sourced from `stg_products`. The join is `left join products on order_items.product_id = products.product_id`. |
| Product classification | `models/staging/stg_products.sql:3-5,14,18,23,25-30,34` | `sku as product_id`; `type as product_type`; `coalesce(type = 'jaffle', false) as is_food_item`; `coalesce(type = 'beverage', false) as is_drink_item`. The raw table is `source('ecom', 'raw_products')`, declared at `models/staging/__sources.yml:17-18`. |
| Item join key | `models/staging/stg_order_items.sql:3-5,14-16` | `raw_items.sku` becomes the order item's `product_id`. The source is declared at `models/staging/__sources.yml:13-14`. |

The packet cards have unique measure owners on `model.jaffle_shop.order_items`. Their ungrouped generated SQL is exactly `SUM(case when is_food_item then product_price else 0 end) AS food_revenue`, `SUM(case when is_drink_item then product_price else 0 end) AS drink_revenue`, and `SUM(product_price) AS revenue`, each from `"dev"."main"."order_items"`. The generated SQL bytes and hashes match the packet cards. The selected metric-to-measure and model bindings passed in the script before it stopped at the mart projection check.

## DuckDB NULL check

A separate in-memory DuckDB 1.4.3 query used synthetic matched category, matched NULL type, and absent product rows for **each** classifier. It completed successfully with the same results for `jaffle` and `beverage`:

| Raw type / join | Staging flag | Mart flag (`typeof`) | `CASE WHEN flag THEN price ELSE 0 END` with price 500 |
| --- | --- | --- | ---: |
| Matching type, matched product | TRUE | TRUE (`BOOLEAN`) | 500 |
| NULL type, matched product | FALSE | FALSE (`BOOLEAN`) | 0 |
| No matching product row | no staging row | NULL (`BOOLEAN`) | 0 |

Thus the staging `COALESCE` yields a non-NULL Boolean for an existing product, but the mart's `LEFT JOIN` can reintroduce a NULL flag. `CASE WHEN NULL` takes `ELSE 0`. A TRUE flag with NULL price can still yield NULL; aggregate and missing-row behavior has not been established for real data.

## Hashes and test status

The following source-file SHA-256 values were independently equal for worktree bytes and `Git HEAD:<path>`:

| Source path | SHA-256 |
| --- | --- |
| `models/marts/order_items.yml` | `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97` |
| `models/marts/order_items.sql` | `7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639` |
| `models/staging/stg_products.sql` | `062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6` |
| `models/staging/stg_order_items.sql` | `102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04` |
| `models/staging/__sources.yml` | `f7bd8b0cbd4c93cf58887262792efdbe020cf29a327a7f4d0f0795088f673853` |

Packet SHA-256: `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`. Generated SQL SHA-256: food `682e619fc89a74bb67d71ed3aac6797642431e6dff08a3dd822ef32d8911a110`; drink `3e1d04e6f6a6ac412fdab159503b76feb0ae180b59f8a63900c293e0bf09d613`; revenue `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134`.

**Script status: failed, not a passing end-to-end probe.** `python -B metric_matching_pilot/probe_flag_lineage.py` stopped with `Unsupported: projection_not_unique:order_items.product_price` before its own DuckDB step. Its alias-only projection check does not accept the mart's direct `products.product_price` projection. No further implementation or debugging was done. The separate DuckDB query above passed.

The frozen bundle's generated queries use `dev.main.order_items`, while the checkout model compilation uses `jaffle_shop.main.order_items`; a single physical build identity is not attested. Manifest source checksum fields do not reconcile with the Git blobs, and the build commit is not independently attested. This probe did not read real product records or held-out sources/worksheets, establish join cardinality or full aggregation semantics, or produce human gold, universal equivalence, or matching accuracy. Treat the class decision as packet-only evidence with this source corroboration, not as a completed automated lineage result.
