# Public seed reconciliation for disputed pair labels

Pinned repository: `dbt-labs/jaffle-shop@5beb145b00f5465ec759cfcdd9745e858818cf95`. Values below are integer cents from raw CSV seeds, grouped according to the visible source model expressions; dbt and MetricFlow were not run.

| Check | Observed |
| --- | ---: |
| Order rows | 61,948 |
| Orders with nonzero tax | 61,465 |
| JS-001 sum of item prices / order subtotals (cents) | 63,744,400 / 63,744,400 |
| JS-001 sum of order totals / taxes (cents) | 67,142,537 / 3,398,137 |
| JS-010 all-time order totals / customer lifetime sums (cents) | 67,142,537 / 67,142,537 |
| JS-010 dates with different daily totals | 365 of 365 |

For example, on 2024-09-01, order-day total is 49,815 cents while the value allocated to customers' first-order date is 7,830,698 cents. All item sums match order subtotals and all orders satisfy subtotal + tax = order_total in these seed rows. No product, order, or customer mappings were missing. These finite checks do not prove universal equivalence or exact behavior after dbt compilation.
