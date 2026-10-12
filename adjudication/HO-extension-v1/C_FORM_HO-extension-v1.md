# Adjudicator C fill-in form: `HO-extension-v1`

This form replaces typing into the decision-record table. Fill it in **by hand** (no AI tools, and switch off AI autocomplete) on your own laptop, then email it. A fixed script (no AI) will copy your answers into the scored table; your form is the official record.

**How to fill it in:** write after the colon on each `- ...:` line. Don't delete lines or change the `## P-xx` headings.

Allowed values:
- **Final label:** `direct_equivalent`, `cross_grain_equivalent`, `temporal_or_scope_variant`, `conflicting_definition`, `related`, `non_match`, `blank`, or `unresolved`. Write exactly one, with no extra words; put any uncertainty in Final evidence and the rationale.
- **Final evidence:** `sufficient` or `needs_review`.
- **Root cause:** `rubric_wording`, `missed_evidence`, `scope`, `value_interpretation`, `judgment`, or `other`.
- **Decision (agreements):** `accept` or `override`. If `override`, also fill Final label, Final evidence and Rationale for that pair.
- **Decisive files (agreements):** write `as cited` to use both reviewers' cited lines shown above it, or write your own.

## Header

- Adjudicator code: Adjudicator C
- Packet SHA-256: `7ce6f34f02d5b1fa8af9baada95a58b8a7e4763edd0a1b3023eef571e1d58ee3`
- Reviewer 1 worksheet SHA-256: `4a8a20e5733fb40668df5077a8aa1fce1b3bc90e4d8b20e4d5edf8bee0e8bf4e`
- Reviewer 2 worksheet SHA-256: `e7d1f00fb3d3a89f47cc91aa514be71e222dfb204e8a129df550b3ea89fc3cef`
- Hashes checked against the coordinator's values (yes / no):
- Date and time zone:
- Active minutes:

# Part 1: the 11 disagreements

Review each pair yourself at its Compare-at scope. You may pick either reviewer's label or a third label the evidence clearly supports.

## P-12: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-13: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-14: disagreement (Compare at: metric_time__month)

Reviewer 1: non_match / needs_review  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-17: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / needs_review  
Reviewer 2: temporal_or_scope_variant / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-34: disagreement (Compare at: metric_time__month)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-45: disagreement (Compare at: metric_time__month)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-46: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-55: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / needs_review  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-58: disagreement (Compare at: metric_time__month)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-60: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / needs_review  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

## P-64: disagreement (Compare at: ungrouped total)

Reviewer 1: non_match / sufficient  
Reviewer 2: related / sufficient

- Final label:
- Final evidence:
- Root cause:
- Decisive files, lines and queries:
- Rationale (1–3 sentences):

# Part 2: the 32 agreements

Skim the cited lines. Override only for a clear factual error, and explain it.

## P-15: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L56–64 (ltv_to_cac), L22–26 (total_mrr); customers model  
Reviewer 2 cited: metrics.yml L56–64 (ltv_to_cac), L22–26 (total_mrr); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-18: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L74–78 (lifetime_revenue), L34–38 (total_cac_spend); customers model in semantic_models.yml. Checked ltv_to_cac at L56–64 — it simplifies to lifetime_revenue / total_cac_spend  
Reviewer 2 cited: metrics.yml L74–78 (lifetime_revenue), L34–38 (total_cac_spend); see customers model in semantic_models.yml, different columns of dim_customers

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-19: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L22–26 (total_mrr); customers model  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L22–26 (total_mrr); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-20: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L40–46 (cac), L48–54 (ltv); customers model. ltv_to_cac at L56–64 defined as ltv / nullif(cac, 0)  
Reviewer 2 cited: metrics.yml L40–46 (cac), L48–54 (ltv); both in customers model, same denominator (customer_count), different numerators (cac_cost vs lifetime_revenue)

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-24: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L12–20 (arr), L56–64 (ltv_to_cac); customers model  
Reviewer 2 cited: metrics.yml L12–20 (arr), L56–64 (ltv_to_cac); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-26: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L66–72 (avg_revenue_per_customer), L56–64 (ltv_to_cac); looked at both in semantic_models.yml  
Reviewer 2 cited: metrics.yml L66–72 (avg_revenue_per_customer), L56–64 (ltv_to_cac); looked at both in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-27: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L74–78 (lifetime_revenue), L48–54 (ltv); customers model — ltv numerator = lifetime_revenue, denominator = customer_count  
Reviewer 2 cited: metrics.yml L74–78 (lifetime_revenue), L48–54 (ltv); customers model shows ltv numerator = lifetime_revenue, denominator = customer_count

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-28: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L12–20 (arr), L28–32 (customer_count); customers model  
Reviewer 2 cited: metrics.yml L12–20 (arr), L28–32 (customer_count); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-32: agreed related / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L66–72 (avg_revenue_per_customer), L6–10 (total_revenue); ARPC uses total_revenue as numerator  
Reviewer 2 cited: metrics.yml L66–72 (avg_revenue_per_customer), L6–10 (total_revenue); ARPC def shows total_revenue as numerator, customer_count as denominator

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-33: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L40–46 (cac), L22–26 (total_mrr); customers model  
Reviewer 2 cited: metrics.yml L40–46 (cac), L22–26 (total_mrr); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-36: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L34–38 (total_cac_spend), L6–10 (total_revenue); different semantic models  
Reviewer 2 cited: metrics.yml L34–38 (total_cac_spend), L6–10 (total_revenue); total_cac_spend in customers model, total_revenue in revenue model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-37: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L12–20 (arr), L40–46 (cac); customers model  
Reviewer 2 cited: metrics.yml L12–20 (arr), L40–46 (cac); customers model in semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-40: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L48–54 (ltv); ltv def in customers model has customer_count as denominator  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L48–54 (ltv); ltv definition in customers model has customer_count as the denominator

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-41: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L40–46 (cac), L28–32 (customer_count); cac denominator = customer_count  
Reviewer 2 cited: metrics.yml L40–46 (cac), L28–32 (customer_count); cac def shows denominator = customer_count

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-42: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L74–78 (lifetime_revenue), L56–64 (ltv_to_cac); did the algebra: customer_count cancels and you get ltv_to_cac = lifetime_revenue / total_cac_spend  
Reviewer 2 cited: metrics.yml L74–78 (lifetime_revenue), L56–64 (ltv_to_cac); worked out the algebra: ltv_to_cac = (lifetime_revenue/count) / (cac_spend/count) simplifies to lifetime_revenue / total_cac_spend

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-43: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L66–72 (avg_revenue_per_customer), L34–38 (total_cac_spend); see semantic_models.yml  
Reviewer 2 cited: metrics.yml L66–72 (avg_revenue_per_customer), L34–38 (total_cac_spend); see semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-44: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L56–64 (ltv_to_cac); worked through the algebra  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L56–64 (ltv_to_cac); worked through ltv_to_cac's algebra

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-48: agreed related / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L66–72 (avg_revenue_per_customer), L28–32 (customer_count); ARPC = total_revenue / customer_count  
Reviewer 2 cited: metrics.yml L66–72 (avg_revenue_per_customer), L28–32 (customer_count); ARPC = total_revenue / customer_count by definition

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-49: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L56–64 (ltv_to_cac), L34–38 (total_cac_spend); simplified form: ltv_to_cac = lifetime_revenue / total_cac_spend  
Reviewer 2 cited: metrics.yml L56–64 (ltv_to_cac), L34–38 (total_cac_spend); simplified ltv_to_cac = lifetime_revenue / total_cac_spend

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-50: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L74–78 (lifetime_revenue); both in customers model. ltv at L48–54 uses both  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L74–78 (lifetime_revenue); both in customers model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-53: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L12–20 (arr), L34–38 (total_cac_spend); both in customers model, different columns  
Reviewer 2 cited: metrics.yml L12–20 (arr), L34–38 (total_cac_spend); both in customers model, different columns (total_mrr vs cac_cost)

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-54: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L56–64 (ltv_to_cac), L6–10 (total_revenue); ltv_to_cac uses lifetime_revenue not total_revenue  
Reviewer 2 cited: metrics.yml L56–64 (ltv_to_cac), L6–10 (total_revenue); ltv_to_cac from customers model, total_revenue from revenue model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-61: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L34–38 (total_cac_spend); cac at L40–46 uses both as numerator/denominator  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L34–38 (total_cac_spend); both in customers model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-62: agreed related / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: metrics.yml L28–32 (customer_count), L6–10 (total_revenue); ARPC at L66–72 uses both  
Reviewer 2 cited: metrics.yml L28–32 (customer_count), L6–10 (total_revenue); customer_count in customers model, total_revenue in revenue model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-63: agreed temporal_or_scope_variant / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L12–20 (arr: `expr: mrr * 12`, mrr = total_mrr), L22–26 (total_mrr); total_mrr measure in customers model  
Reviewer 2 cited: metrics.yml L12–20 (arr def: `expr: mrr * 12`, mrr aliases total_mrr), L22–26 (total_mrr); total_mrr measure in customers model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-65: agreed related / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: metrics.yml L48–54 (ltv), L56–64 (ltv_to_cac: ltv / nullif(cac, 0))  
Reviewer 2 cited: metrics.yml L48–54 (ltv), L56–64 (ltv_to_cac); ltv_to_cac def is ltv / nullif(cac, 0)

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-38: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: semantic_models.yml L53–57 (order_count_total), L43–47 (total_gross_margin); both under orders model in same file  
Reviewer 2 cited: semantic_models.yml L53–57 (order_count_total: SUM of 1), L43–47 (total_gross_margin: SUM of gross_margin); both under orders semantic model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-59: agreed non_match / sufficient (Compare at: metric_time__month)

Reviewer 1 cited: semantic_models.yml L58–64 (otif_rate), L43–47 (total_gross_margin); orders model  
Reviewer 2 cited: semantic_models.yml L58–64 (otif_rate: otif_orders / order_count), L43–47 (total_gross_margin); orders semantic model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-31: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: _metrics.yml L23–29 (ctr), L31–39 (revenue_amount); _semantic_models.yml — message_event model vs revenue model  
Reviewer 2 cited: _metrics.yml L23–29 (ctr: clicked_count / delivered_count), L31–39 (revenue_amount); _semantic_models.yml shows ctr from message_event model, revenue_amount from revenue model

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-47: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: _metrics.yml L9–14 (delivered_count), L31–39 (revenue_amount); separate semantic models in _semantic_models.yml  
Reviewer 2 cited: _metrics.yml L9–14 (delivered_count), L31–39 (revenue_amount); separate models in _semantic_models.yml (message_event vs revenue)

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-52: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: _metrics.yml L31–39 (revenue_amount), L2–7 (subscription_count); separate semantic models  
Reviewer 2 cited: _metrics.yml L31–39 (revenue_amount), L2–7 (subscription_count); revenue model vs subscription model in _semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

## P-57: agreed non_match / sufficient (Compare at: ungrouped total)

Reviewer 1 cited: _metrics.yml L16–21 (clicked_count), L31–39 (revenue_amount); message_event vs revenue model  
Reviewer 2 cited: _metrics.yml L16–21 (clicked_count), L31–39 (revenue_amount); message_event model vs revenue model in _semantic_models.yml

- Decision:
- Decisive files, lines and queries:
- If override: Final label:
- If override: Final evidence:
- If override: Rationale:

# Notes (optional)

- Clarification questions sent to both reviewers (date, question, replies), if any:
- Rubric problems observed, if any:

# Declaration

- Before this package, had I seen the reviewers' original (non-neutral) worksheets, or did I know which reviewer is which? (yes / no, and details):
- Did anyone help me, or did I use any AI tool? (yes / no, and details):
- I am not one of the two reviewers, I applied the shared rubric, and I gave neither reviewer's answer extra weight (yes / no):
- Date:
