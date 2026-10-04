# Jaffle Shop gross-profit dependency: bounded development observation

Public source: `dbt-labs/jaffle-shop@7be2c5838dbdeca8e915d4e46db70e910753d7f6` (the already inspected Jaffle Shop submodule checkout). Executed with DuckDB `1.5.6` using four pinned public seeds in an **in-memory** catalog. The selected staging and mart columns in the script follow the pinned model joins, grouped supply costs, order summary, day truncation, and `DECIMAL(16,2)` cents conversion. The three ungrouped queries below are pinned MetricFlow SQL from the prior same-commit parse; they execute here on the reconstructed tables. The daily and per-order queries are explicitly scoped SQL, not native MetricFlow compilations at those grains.

## Result and scope

The YAML declares `order_gross_profit` as `revenue - cost`, with `cost` an alias for input metric `order_cost`. `revenue` sums `order_items.product_price`; `order_cost` sums `orders.order_cost`, itself the per-order sum of item supply costs. Both semantic models default to `ordered_at` at day grain. This is a **definition dependency**, while the observations below concern only these pinned public rows and query scopes.

| Ungrouped compiled metric | Dollars |
| --- | ---: |
| `revenue` | 637444.00 |
| `order_cost` | 131788.38 |
| `order_gross_profit` | 505655.62 |
| Independent item `SUM(product_price - supply_cost)` | 505655.62 |

| Scoped comparison with independent item expression | Groups | Non-NULL derived groups | NULL-aware differences |
| --- | ---: | ---: | ---: |
| `ordered_at` day, `2024-09-01 00:00:00`–`2025-08-31 00:00:00` | 365 | 365 | 0 |
| `order_id` on all orders | 61948 | 61465 | 0 (0 among non-NULL values) |

Counts: 61,948 raw orders, 90,900 raw items, 10 products, 65 supplies; reconstructed 61,948 order rows and 90,900 item rows. 365 union dates (2024-09-01 00:00:00 through 2025-08-31 00:00:00); 0 dates without a revenue group, 0 without a cost group, 0 dates with NULL derived profit. 483 orders have no item group. Duplicate order IDs: 0; duplicate item IDs: 0; items without order time, product price, supply cost: 0, 0, 0. The per-order derived expression is NULL on 483 orders; an explicit `COALESCE` on *both* measures makes those 483 differences zero (0 nonzero after fill). The ungrouped totals omit NULL order costs under `SUM` and have represented item rows, so their values reconcile.

**Concrete missing-group case:** `e0b8f516-92e5-45aa-93eb-ed2971d4441e` on `2024-09-02 00:00:00`: item revenue `NULL` (no group), order cost `NULL`, derived difference `NULL`, explicit zero-filled difference `0.00`. No numeric counterexample was found among comparable non-NULL scalar, day, or order results. An order-grain claim that every order has a numeric gross profit is false without a stated zero-fill rule. NULL-aware equality treats each missing group differently from a numeric zero; two NULL diagnostics on the same absent order do not constitute an observed numeric match.

## Executed queries

Pinned ungrouped MetricFlow SQL (hashes below):

**revenue**

```sql
SELECT
  SUM(product_price) AS revenue
FROM "dev"."main"."order_items" order_item_src_10000
```

**order_cost**

```sql
SELECT
  SUM(order_cost) AS order_cost
FROM "dev"."main"."orders" orders_src_10000
```

**order_gross_profit**

```sql
SELECT
  revenue - cost AS order_gross_profit
FROM (
  SELECT
    MAX(subq_5.revenue) AS revenue
    , MAX(subq_11.cost) AS cost
  FROM (
    SELECT
      SUM(product_price) AS revenue
    FROM "dev"."main"."order_items" order_item_src_10000
  ) subq_5
  CROSS JOIN (
    SELECT
      SUM(order_cost) AS cost
    FROM "dev"."main"."orders" orders_src_10000
  ) subq_11
) subq_12
```

The following daily query aligns each metric to its own model's `ordered_at` day and compares with an independently computed item expression:

```sql
WITH revenue_by_day AS (
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
ORDER BY 1
```

The following order diagnostic joins by `order_id`; `zero_filled_profit` is an **extra hypothetical policy**, not a property of the declared derived metric:

```sql
WITH revenue_by_order AS (
    SELECT order_id, SUM(product_price) AS revenue,
           SUM(product_price - supply_cost) AS direct_profit
    FROM dev.main.order_items GROUP BY 1
)
SELECT o.order_id, o.ordered_at AS day, r.revenue, o.order_cost AS cost,
       r.revenue - o.order_cost AS derived_profit, r.direct_profit,
       COALESCE(r.revenue, 0) - COALESCE(o.order_cost, 0) AS zero_filled_profit,
       r.order_id IS NULL AS missing_item_group
FROM dev.main.orders o LEFT JOIN revenue_by_order r ON o.order_id = r.order_id
ORDER BY o.ordered_at, o.order_id
```

Reconstruction SQL is in `experiment_gross_profit.py` (`BUILD_SQL`); it creates `dev.main.order_items` and `dev.main.orders` in memory. Run from this workspace with:

```bash
metric_matching_dev_build_20260928/venv/bin/python metric_matching_pilot/experiment_gross_profit.py
```

## Exact pins (SHA-256)

Git HEAD and each local source byte stream were checked against the expected hash and Git `HEAD:path`; no dependency was read from an unpinned checkout. Source and seed hashes:

| Commit-relative path | SHA-256 |
| --- | --- |
| `seeds/jaffle-data/raw_orders.csv` | `e8ee89233d417fd695d016588649c008d930110d50027480bb95b443ec0dc76b` |
| `seeds/jaffle-data/raw_items.csv` | `bc18d101291697036d97e9fd0e6deb43fef6d1b5ce2282167462a882513980ca` |
| `seeds/jaffle-data/raw_products.csv` | `01825b18e182090b6770cee6aaf7bd52d5781a0c74bb1ff2872aac4b47809f0d` |
| `seeds/jaffle-data/raw_supplies.csv` | `309a2d1cfd330da2b493b411d2fe5e0aef1b463ed0281760691793f8b423bde1` |
| `models/marts/order_items.yml` | `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97` |
| `models/marts/orders.yml` | `223dc461510c54b38681167b85cea019b3919c4a1de8bfac6673d60465ea0391` |
| `models/marts/order_items.sql` | `7f39a62b3fcf4ed61a50f9717938e327d35ee6ecb7545bc2870ceec8a10ed639` |
| `models/marts/orders.sql` | `a1196f297da67c4a55c1e1011202f4fa7cf29c9ad3a0282970de4f947cc2ef1b` |
| `models/staging/stg_orders.sql` | `9b1b41c48e4463f736d9304a898da2d979b29b9377f1576951f959ff5cc7c327` |
| `models/staging/stg_order_items.sql` | `102a386f0423d233aae94e6312cc028470aacc120df5692532296a2d8ed61b04` |
| `models/staging/stg_products.sql` | `062c753f5014b17e4df4266503cf6f48f191b95aa86f3ddeada063ed844d5cd6` |
| `models/staging/stg_supplies.sql` | `1835f7e81a9116987eedf053b3630e26cff26dbcac38f6a5895c51f181bec5a4` |
| `macros/cents_to_dollars.sql` | `5ebc8923ad19fa427e9def74a3ad8fc6f186168ed82950280f04003cde7b0ffb` |

Prior same-commit compiled query files under `metric_provenance_verification/generated_sql/`:

| File | SHA-256 |
| --- | --- |
| `revenue.sql` | `eb46efbc7803b9a958a96c4576ab01095dc3a20ee47291985515e1504ed62134` |
| `order_cost.sql` | `c0f6c4ca283c57bbafe985506aa28b54b8f4dec0074e67063654c54212d217ab` |
| `order_gross_profit.sql` | `d2828571bfb4cc45577230d06339f13beb2a0451eaefe1d29fe9bac9418e6b2c` |

**Limit:** One finite, curated public sample on DuckDB. Model SQL is reconstructed for relevant columns, while the ungrouped metric queries are executed verbatim. The daily and order comparisons are manual scoped analogues and cannot establish a general identity across filters, future rows, missing groups, other times, or other engines. This is neither a reference label nor a method result. No held-out source or worksheet was accessed.
