# Aggressive AST equivalence on pinned Jaffle I1

## Rule and input boundary

The baseline compares the complete MetricFlow-generated DuckDB SQL AST for two **ungrouped** cards. It alpha-renames bound relation aliases and discards a cosmetic outer output alias, then asserts `direct_equivalent` as **general metric substitutability** from that ungrouped AST identity. The JSON records `evidence_scope=ungrouped_scalar` and `assertion_scope=general_metric_substitution`. It does not check declared cumulative type, time semantics, grouped queries, row results, or numeric eligibility. A different AST is an abstention, not a `non_match`. This deliberately permissive two-card method is independent of `ast_mask_baseline.py`.

Pinned public Jaffle commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`; packet SHA-256 `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`; pair-set SHA-256 `0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`. The packet has 19 declared metrics and **all 171 unordered pairs**. Generated SQL covers 18 ungrouped metrics (153 common-scope pairs); the other metric has only a `metric_time` query (18 incompatible-scope pairs). SQLGlot `30.20.0`, DuckDB dialect. Packet and SQL hashes are checked before comparison. No held-out source or labels are read.

## Full-frame results

| Decision | Count / 171 | Reason |
| --- | ---: | --- |
| `direct_equivalent` | 1 | identical ungrouped AST modulo alias |
| `abstain` | 152 | different ungrouped AST |
| `abstain` | 18 | incompatible generated scopes |

The sole asserted pair is `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue`: `direct_equivalent` / `same_ungrouped_ast_modulo_alias`. The two ungrouped queries select `SUM(product_price)` from `"dev"."main"."order_items"`; only the output aliases differ. The **evidence** is limited to this ungrouped scalar; the deliberately broader assertion is a method prediction, not an all-grain proof.

## Existing month-grouped counterexample

The existing `experiment_cumulative_revenue_report.md` (SHA-256 `1ae15f4734134d4a60e10a59876a75fdbe45a4f4cab048f95902e3bbb64a988f`) records a separate bounded `metric_time__month` compilation and execution for 2024-09-01 through 2025-08-31 on reconstructed public seed relations. Both ungrouped queries returned $637,444.00 there. In October 2024, monthly `revenue` was $19,422.00 while MetricFlow `cumulative_revenue` was $15,670.00 (the running amount through October 1 under that query's `FIRST_VALUE` rule). The direct end-of-October control was $34,640.00. Thus the method's general substitution assertion is **conditionally refuted** for the month scope on that bounded reconstructed input. A claim explicitly limited to the ungrouped scalar is not refuted by a month result. The generated month SQL and execution are outside this baseline's decision inputs. The reconstruction was not a full dbt build, and this observation is **not an adjudicated gold label** or a measured error rate on 171 reference labels.

## Exact pair outputs

The following table includes every pair, including all 18 scope abstentions. IDs are the packet's exact lexical pair IDs.

| Pair ID | Decision | Reason |
| --- | --- | --- |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.count_lifetime_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.cumulative_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.drink_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.drink_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.drink_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.average_order_value||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.cumulative_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.drink_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.drink_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.drink_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.count_lifetime_orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.drink_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.drink_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.drink_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue` | `direct_equivalent` | `same_ungrouped_ast_modulo_alias` |
| `metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.drink_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.drink_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.drink_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.food_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.drink_revenue_pct||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.food_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.food_revenue_pct` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.large_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.food_revenue_pct||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.lifetime_spend_pretax` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.large_orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.median_revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.lifetime_spend_pretax||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.new_customer_orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.median_revenue||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.order_cost` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.new_customer_orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.order_cost||metric.jaffle_shop.order_gross_profit` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_cost||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_cost||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_cost||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_cost||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.order_gross_profit||metric.jaffle_shop.order_total` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_gross_profit||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_gross_profit||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_gross_profit||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.order_total||metric.jaffle_shop.orders` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_total||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.order_total||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.orders||metric.jaffle_shop.revenue` | `abstain` | `different_ungrouped_ast` |
| `metric.jaffle_shop.orders||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |
| `metric.jaffle_shop.revenue||metric.jaffle_shop.revenue_growth_mom` | `abstain` | `incompatible_generated_scope` |

## Reproduce

From this directory, run `/workspace/scratch/e767b9d6f697/metric_matching_dev_build_20260928/venv/bin/python -B aggressive_ast_equivalence_baseline.py` for JSON with all 171 outputs; add `--check` to verify this Markdown byte for byte. `--write-report` writes only this report. With missing or differently versioned SQLGlot, same-scope pairs abstain and report generation fails closed. No other files are written.
