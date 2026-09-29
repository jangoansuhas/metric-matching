# Practice packet: CAL (3 pairs)

**Packet ID:** `CAL-practice-v1`
**Project:** Jaffle Shop, <https://github.com/dbt-labs/jaffle-shop>
**Pinned commit:** `7be2c5838dbdeca8e915d4e46db70e910753d7f6`
**Setup:** [SETUP.md](../SETUP.md), Steps 1–10, which use this exact project and commit.

This is a **practice round**. It isn't scored. Work exactly as the [REVIEWER_GUIDE.md](../REVIEWER_GUIDE.md) describes, and note anything confusing in the Notes section of your worksheet.

**Compare at (all three pairs):**
- the **overall total** (no grouping);
- **by month** (`--group-by metric_time__month`).

If a metric can't be queried or compared at one of these scopes, say so in your worksheet. Don't choose a different scope instead.

Each link below opens the exact declaration lines at the pinned commit. From there, trace each metric back to its measure, semantic model and SQL yourself (REVIEWER_GUIDE §3).

| Pair | Metric 1 (file and lines) | Metric 2 (file and lines) |
| --- | --- | --- |
| CAL-01 | `revenue`: [models/marts/order_items.yml L90–95](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L90-L95) | `food_revenue`: [models/marts/order_items.yml L108–113](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L108-L113) |
| CAL-02 | `lifetime_spend_pretax`: [models/marts/customers.yml L73–78](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.yml#L73-L78) | `order_total`: [models/marts/orders.yml L124–129](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L124-L129) |
| CAL-03 | `order_total`: [models/marts/orders.yml L124–129](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L124-L129) | `order_cost`: [models/marts/order_items.yml L96–101](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L96-L101) |

Below is a starting query for any pair. It is only a starting point, and not every pair needs it.

```bash
mf query --metrics <metric1>,<metric2>
mf query --metrics <metric1>,<metric2> --group-by metric_time__month --order metric_time__month
```

When you're done, fill in [templates/REVIEWER_WORKSHEET.md](../templates/REVIEWER_WORKSHEET.md) with the Packet ID `CAL-practice-v1`, and email it to the coordinator.
