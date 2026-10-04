# Development-only name retrieval baselines

Algorithm: `development_name_baselines_v1` in `run_development_baselines.py` (Python standard library only).
Scores use **metric names only** for all four methods. The ranking excludes the query metric; it never reads labels or source signatures. No relationship classification is performed.

Normalization splits underscores, punctuation, and camel case, then casefolds ASCII alphanumeric tokens. Exact compares the ordered normalized text. Jaccard uses unique token sets. Jaro–Winkler uses the normalized text, standard Jaro matching and a four-character prefix boost of 0.1 when Jaro ≥ 0.7. American Soundex concatenates tokens, ignores digits, and compares four-character codes. Scores are rounded to six decimals before ranking; a score of 0 is unranked. A rank range shows all candidates tied at that positive score; the top-three list in JSON breaks ties by candidate ID for display.

## Public Jaffle Shop: 10 selected pairs against 23 extracted metrics

Source: `public_corpus_report.json` and `public_pair_proposals.json`, pinned at `5beb145b00f5465ec759cfcdd9745e858818cf95`. Each query has 22 other candidates. The extraction reports 7 partial signatures and 16 needing review, so this inventory supplies names rather than complete verified source cards. These selected pairs were reviewed, but the full inventory was not judged for each query.

| Case: query → selected target | Exact score / rank | Token Jaccard | Jaro–Winkler | Soundex |
| --- | ---: | ---: | ---: | ---: |
| `JS-001`: `orders.order_total` → `order_items.revenue` | 0.000 / unranked | 0.000 / unranked | 0.489 / 13 | 0.000 / unranked |
| `JS-002`: `orders.orders` → `orders.new_customer_orders` | 0.000 / unranked | 0.333 / 4–5 | 0.459 / 19 | 0.000 / unranked |
| `JS-003`: `orders.orders` → `orders.large_orders` | 0.000 / unranked | 0.500 / 1–3 | 0.583 / 5–6 | 0.000 / unranked |
| `JS-004`: `order_items.revenue` → `order_items.food_revenue` | 0.000 / unranked | 0.500 / 1–4 | 0.861 / 2 | 0.000 / unranked |
| `JS-005`: `order_items.food_revenue` → `order_items.drink_revenue` | 0.000 / unranked | 0.333 / 3–6 | 0.777 / 4 | 0.000 / unranked |
| `JS-006`: `order_items.revenue` → `order_items.median_revenue` | 0.000 / unranked | 0.500 / 1–4 | 0.536 / 11 | 0.000 / unranked |
| `JS-007`: `customers.customers` → `orders.orders` | 0.000 / unranked | 0.000 / unranked | 0.444 / 12 | 0.000 / unranked |
| `JS-008`: `customers.lifetime_spend` → `customers.lifetime_spend_pretax` | 0.000 / unranked | 0.667 / 1 | 0.933 / 1 | 1.000 / 1 |
| `JS-009`: `customers.customers` → `locations.average_tax_rate` | 0.000 / unranked | 0.000 / unranked | 0.340 / 19 | 0.000 / unranked |
| `JS-010`: `orders.order_total` → `customers.lifetime_spend` | 0.000 / unranked | 0.000 / unranked | 0.385 / 21 | 0.000 / unranked |

## Constructed SQLite fixture: 7 selected pairs against 12 hand-authored cards

Source: `cards.json` and `pairs.json`; card IDs distinguish versioned definitions with identical names. Each query has 11 other cards. This is a separate synthetic diagnostic.

| Case: query card → selected target card | Exact score / rank | Token Jaccard | Jaro–Winkler | Soundex |
| --- | ---: | ---: | ---: | ---: |
| `P1_alias`: `booking_alias_a` (`opportunity_booking_arr_usd`) → `booking_alias_b` (`total_opportunity_booking_arr_usd`) | 0.000 / unranked | 0.800 / 1 | 0.797 / 2 | 0.000 / unranked |
| `P2_rollup`: `account_arr` (`account_net_revenue`) → `opportunity_arr_rollup` (`crm_revenue_net`) | 0.000 / unranked | 0.500 / 2 | 0.709 / 2 | 0.000 / unranked |
| `P3_live_vs_booking`: `product_live` (`product_arr_usd`) → `product_booked` (`product_booking_arr_usd`) | 0.000 / unranked | 0.750 / 1 | 0.910 / 1 | 1.000 / 1 |
| `P4_filter_change`: `pipeline_v0` (`pipeline_arr`) → `pipeline_v1` (`pipeline_arr`) | 1.000 / 1 | 1.000 / 1 | 1.000 / 1 | 1.000 / 1 |
| `P5_fanout`: `account_arr` (`account_net_revenue`) → `opportunity_arr_fanout` (`crm_revenue_net_bad_mapping`) | 0.000 / unranked | 0.333 / 3 | 0.609 / 3 | 0.000 / unranked |
| `P6_missing_time`: `account_arr` (`account_net_revenue`) → `account_arr_unknown_time` (`account_net_revenue_undocumented`) | 0.000 / unranked | 0.750 / 1 | 0.919 / 1 | 1.000 / 1 |
| `P7_equal_counts`: `customer_count` (`number_of_customers`) → `product_count` (`num_of_products`) | 0.000 / unranked | 0.200 / 1 | 0.823 / 1 | 1.000 / 1 |

## Conditional positive without an inventory

`POS-001`: `orders.subtotal` → `order_items.revenue` from `public_positive_candidate.json` (semantic commit `8686fe3ea0fd4ceffa08e523a422331bd228ac32`, dbt submodule `7be2c5838dbdeca8e915d4e46db70e910753d7f6`). exact=0.000, token_jaccard=0.000, jaro_winkler=0.000, soundex=0.000. **No rank:** the supplied candidate file is a pair case study, not a complete metric inventory.

The pinned sample has 0 differing aligned daily totals across 365 dates; 483 zero-item orders require an outer join and COALESCE at order grain. This is conditional sample evidence, not an unconditional cross-engine or future-data equivalence label.

## Reading the probes

- `JS-008` is a hard negative for **unconditional equivalence**: the first analyst and user-submitted labels both call tax-inclusive `lifetime_spend` versus `lifetime_spend_pretax` *related*, despite similar names. Review independence is unverified; this does not make it a `non_match` relationship.
- Constructed `P4_filter_change` has the exact same metric name in v0 and v1, yet the hand-authored stage filters differ; the fixture records candidate definition drift.
- `POS-001` is the conditional positive above. Its names can be lexically dissimilar even when aligned sample totals reconcile under stated conditions.

All ten selected public pairs and all seven constructed pairs appear above; examples illustrate failure modes and were not used to choose features, weights, cutoffs, or performance figures. Labels remain source context and never enter ranking. No accuracy, precision, Recall@k, or claim of baseline effectiveness is estimated from these selected cases. The full per-query top-three positive candidates, tie ranges, source hashes, and source statuses are in `development_baselines_report.json`.

Reproduce: `python3 metric_matching_pilot/run_development_baselines.py` from the workspace root; verify committed outputs without rewriting them with `python3 metric_matching_pilot/run_development_baselines.py --check`.
