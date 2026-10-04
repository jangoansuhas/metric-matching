# MetricFlow cumulative metric at month grain: documented rule and Jaffle observation

**Scope (29 September 2026).** This note checks the already generated, bounded
Jaffle development query against [dbt's cumulative metric documentation for
v1.12](https://docs.getdbt.com/docs/build/cumulative?version=1.12), the
[MetricFlow 0.213.0 release](https://github.com/dbt-labs/metricflow/releases/tag/v0.213.0),
and the installed 0.213.0 compiler source. It does not run another build,
inspect a held-out project or worksheet, or infer user behavior.

## Exact version and local evidence

| Item | Checked evidence |
| --- | --- |
| Runtime | `metricflow 0.213.0`, `dbt-metricflow 0.15.0`, `dbt-core 1.12.5`, DuckDB `1.5.6` in the existing experiment environment. The [official release](https://github.com/dbt-labs/metricflow/releases/tag/v0.213.0) identifies the MetricFlow tag; the local package versions were checked with `importlib.metadata`. |
| Pinned Jaffle definition | `dbt-labs/jaffle-shop` commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`; [local source YAML](../metric_matching_dev_build_20260928/source/models/marts/order_items.yml#L162-L167), SHA-256 `81020ca853159b9e33b3f23cb67ab6bf307ff6a5ea516367201ecca4012bbb97`. `cumulative_revenue` is `type: cumulative` over measure `revenue`; it does **not** specify `period_agg`, `window`, or `grain_to_date`. The measure is `sum(product_price)` and uses `ordered_at` as aggregation time ([lines 44–46 and 70–74](../metric_matching_dev_build_20260928/source/models/marts/order_items.yml#L44-L74)). The pinned semantic manifest, SHA-256 `bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51`, records `cumulative_type_params.period_agg: first`; this value is **materialized in the manifest**, not written in the source YAML. |
| Compiler implementation | Installed [`dataflow_to_subquery.py`, lines 1915–2006](../metric_matching_dev_build_20260928/venv/lib/python3.12/site-packages/metricflow/plan_conversion/to_sql_plan/dataflow_to_subquery.py#L1915-L2006), SHA-256 `16dd2a42d1bcc90dc3696496da04c6512eaaa0eaea9c5955baaddc68b3673d8f`. In `visit_window_reaggregation_node`, lines 1936–1943 choose `PeriodAggregation.FIRST` if a period aggregation is absent, then build an ordered window over the partition. This is the installed package's source for the stated runtime, not a claim about every release. |
| Exact SQL artifact | Existing [experiment report, lines 105–149](experiment_cumulative_revenue_report.md#L105-L149) embeds the output of `mf query --metrics cumulative_revenue --group-by metric_time__month --start-time 2024-09-01 --end-time 2025-08-31 --explain`. SHA-256 of that bounded month SQL (UTF-8, terminal newline): `b914f6be26330147517fa25d1977e82ff63ef4577392a4279b8180cbd24dc3f3`. The companion simple `revenue` bounded month SQL hash is `a72932f3a655389be5352cf5355eb20b652e9c00c8f0d524dc4ab57f6a9d6d21`. The experiment script compiled and executed these queries against reconstructed public seed relations; it did not run a fresh full dbt build. |

## What the docs actually specify

The [official cumulative metric page](https://docs.getdbt.com/docs/build/cumulative?version=1.12)
states that an omitted accumulation period means all-time accumulation. It
separately specifies `period_agg` for reaggregating a cumulative metric at a
coarser requested granularity, with **`first` as its default** and `last` and
`average` as alternatives. Its granularity example shows `FIRST_VALUE` over a
period partition ordered by day. It also distinguishes `grain_to_date: month`,
which *resets* at the beginning of each month, from an all-time cumulative
metric. These documentation sections say they apply to dbt v1.12 and later;
the local experiment used dbt-core 1.12.5. The [official command reference](https://docs.getdbt.com/docs/build/metricflow-commands#time-granularity)
shows `metric_time__month` as the requested monthly grouping syntax. Thus the
choice of the **first period value** is a documented default, not a surprising
undocumented implementation accident. The docs do not promise that every
query produces a row on the first *calendar date* of each month. That last
limit is an inference from the documented first-value rule and the local join.

The generated Jaffle SQL gives the exact operational meaning here:

```sql
FIRST_VALUE(cumulative_revenue) OVER (
  PARTITION BY metric_time__month
  ORDER BY metric_time__day
  ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)
```

The inner query takes days from the bounded daily time spine, joins item rows
with `item_day <= spine_day`, and sums `product_price` per spine day. Its join
is `INNER JOIN`, so `FIRST_VALUE` selects the earliest **surviving daily row**
in each month; the time spine alone does not guarantee a row/value for every
date. The simple `revenue` month query instead performs `DATE_TRUNC('month',
ordered_at)` and `SUM(product_price)` within each monthly group. The full SQL
and bounds are in the [existing report](experiment_cumulative_revenue_report.md#L93-L149).

## Which part was observed

In the bounded reconstruction, all 12 first-of-month dates had item rows
(minimum 57), and the experiment asserted this condition. Therefore the
earliest joined day in every observed month was its calendar first day. The
reported cumulative value is the all-time running sum **through that day,
including its items**. This *first-calendar-day* result is an observation
conditional on that query, daily spine, bounds, join, and data, rather than a
general documented guarantee for every sparse source or grouping. The local
[results and control query](experiment_cumulative_revenue_report.md#L151-L192)
show October 2024 especially clearly:

| October 2024 quantity | Value |
| --- | ---: |
| September total before October | $15,218.00 |
| October 1 item revenue | $452.00 |
| MetricFlow monthly `cumulative_revenue` (through October 1) | **$15,670.00** |
| Simple October `revenue` | $19,422.00 |
| Direct end-of-October cumulative control | $34,640.00 |

Ungrouped queries both returned `$637,444.00` in the same experiment; that
scalar coincidence does not make the monthly series equal. The month-end
number is a direct control over the reconstructed item relation, not a second
MetricFlow metric or a gold label. The original ten-year time spine and a full
`dbt seed`/`dbt run` build were not executed for this bounded check.

## Interpretation boundary

The documented `first` default makes the month-start-style result
**explainable from the definition and SQL**. It does not measure whether
practitioners expected a month-end running total, how often anyone misreads
`metric_time__month`, or how often such a misunderstanding affects decisions.
**Practitioner-misreading frequency is unknown**: no survey, usage telemetry,
user study, or independently judged case set was examined. The Jaffle run is a
single public development example, not evidence of prevalence or method
superiority.
