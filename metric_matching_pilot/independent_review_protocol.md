# Blind second review protocol — development cases

Date: September 27, 2026. This sheet was prepared before the separate reviewer returned labels. It describes the review questions without the first analyst's decisions or observed reconciliation values.

## Evidence and independence

- Reviewer sees only the specified pinned public Git checkouts and their source, history, and available sample rows. The first analyst's outline, proposed labels, audits, and summaries remain hidden during labeling.
- For each relationship, record an unconditional label if supported, a conditional relationship if the transformation is explicit, or `needs_review` with the decisive missing evidence. Do not infer equivalence from matching names or one aggregate total.
- Check grain, eligible population, SQL computation, source lineage, filters, time grouping, currency/unit, missing groups, NULL handling, and join cardinality. Separate source-level support from executed-row evidence.
- Labels: `direct_equivalent`, `cross_grain_equivalent`, `temporal_or_scope_variant`, `related`, `conflicting_definition`, `non_match`, `needs_review`. For a before/after definition change use `behavior_preserving`, `behavior_changing`, or `needs_review` and specify the affected input domain.
- Record confidence, source file and line references, a concrete reason, and limitations. The reviewer may run read-only queries on the public DuckDB files but should not alter repositories.

## Public checkouts

| Project | Pinned revision | Review inputs |
| --- | --- | --- |
| `jross21/gtm-funnel-analytics` | `a71232c123a5fb78da9b52d4246950ee48591c00` | `metrics_catalog.yml`, `models/marts/metrics/fct_metric_values.sql`, `models/marts/reconciliation/rpt_metric_reconciliation.sql`, built DuckDB |
| `sidequery/jaffle-shop-sidemantic` | `8686fe3ea0fd4ceffa08e523a422331bd228ac32` with dbt submodule `7be2c5838dbdeca8e915d4e46db70e910753d7f6` | MetricFlow and Cube YAML, dbt model SQL, seed rows, built DuckDB |
| `rilldata/rill-examples` | `c35c312174431273726a1d6cfc030717babe5a88` | `rill-openrtb-prog-ads/metrics/{auction,bids}_metrics.yaml`, source-model SQL and parquet references; Rill historical parent `3516d3d144979d23ceded2a1a72efcbddd452800` to change `10a9bce8f0181623d8c596fbed7df37244666cc4` |

## Cases to label without prior decisions

| ID | Compared definitions or versions | Question |
| --- | --- | --- |
| BR-01 | GTM `fct_metric_values.pipeline_created`: monthly records versus analysis-window record, same segment | Does a documented month-to-window rollup reconcile? Which groups and dates must align? |
| BR-02 | GTM `fct_metric_values.pipeline_created`, `grain='window'`, `segment='All'` versus `rpt_metric_reconciliation` `pipeline_created`, `variant_key='canonical'` | Which reported value field, if any, is a direct alias? |
| BR-03 | Jaffle MetricFlow `orders.subtotal` versus Cube `order_items.revenue` | Does item-to-order or aligned-day comparison need explicit transformations? What happens to orders without items? |
| BR-04 | Rill `ctr` and `ecpm` in the historical parent versus committed change | Is the behavior preserved on all inputs? Which inputs, if any, differ? Is the effect on actual Rill rows measured? |
| BR-05 | Rill `avg_bid_floor` in auction versus bids metric views | Do identical names and similar SQL imply the same measured population and output? What source mapping or data would resolve this? |

## Record fields for every case

`ID; label or behavior class; exact transformation/affected input domain; source evidence; executed evidence (if any); missing evidence; confidence; reviewer rationale.`

This is a development review. A separate AI reviewer can detect disagreements and errors but does not supply independent human ground truth. Preserve its response unchanged, compare with earlier judgments only after labeling, and ask a domain-aware human to adjudicate contested cases before building a benchmark. Keep a future held-out repository and commit sample separate from all cases selected after inspecting their results.
