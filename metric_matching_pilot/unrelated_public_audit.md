# Independent public-project audit: positive controls and real metric change

**GTM source.** [jross21/gtm-funnel-analytics](https://github.com/jross21/gtm-funnel-analytics/tree/a71232c123a5fb78da9b52d4246950ee48591c00) is an unrelated but synthetic, deliberately reconciled Salesforce/HubSpot example. With dbt-core 1.11.6, dbt-duckdb 1.10.1, DuckDB 1.4.4 and one dbt thread, the local build recorded 44 successful nodes, 111 passing tests and 8 no-op exposures. The model tables reopened and were queried in DuckDB. An alternate local profile omits a redundant ICU download; the source metric SQL is unchanged.

| `pipeline_created` segment | Month rows | Sum of monthly values ($) | Window value ($) | Difference ($) |
| --- | ---: | ---: | ---: | ---: |
| All | 7 | 6884381.39 | 6884381.39 | 0.0 |
| Enterprise | 6 | 2566701.9 | 2566701.9 | 0.0 |
| Mid-Market | 7 | 2717736.87 | 2717736.87 | 0.0 |
| SMB | 7 | 1599942.62 | 1599942.62 | 0.0 |

The separate reconciliation table's `canonical` row republishes the `All` window metric: source 6884381.39, reported variant 6884381.39, reported canonical 6884381.39, delta 0.0. Four intentionally naive pipeline variants have nonzero deltas. The month and window branches use the same filters; the month-to-window relationship is a **designed cross-grain reconciliation**, while the report row is a **direct lineage alias**, not a separately computed duplicate.

Pinned GTM evidence: [catalog](https://github.com/jross21/gtm-funnel-analytics/blob/a71232c123a5fb78da9b52d4246950ee48591c00/metrics_catalog.yml#L38); [monthly](https://github.com/jross21/gtm-funnel-analytics/blob/a71232c123a5fb78da9b52d4246950ee48591c00/models/marts/metrics/fct_metric_values.sql#L41); [window](https://github.com/jross21/gtm-funnel-analytics/blob/a71232c123a5fb78da9b52d4246950ee48591c00/models/marts/metrics/fct_metric_values.sql#L48); [alias](https://github.com/jross21/gtm-funnel-analytics/blob/a71232c123a5fb78da9b52d4246950ee48591c00/models/marts/reconciliation/rpt_metric_reconciliation.sql#L57).

**Rill history.** [rilldata/rill-examples](https://github.com/rilldata/rill-examples/commit/10a9bce8f0181623d8c596fbed7df37244666cc4) has a real historical change from `3516d3d144979d23ceded2a1a72efcbddd452800` to `10a9bce8f0181623d8c596fbed7df37244666cc4` in `rill-openrtb-prog-ads/metrics/bids_metrics.yaml`. Both `ctr` and `ecpm` gained `NULLIF(sum(imp_cnt),0)` in their denominators:

| Measure | Earlier expression | Later expression |
| --- | --- | --- |
| `ctr` | [`sum(click_reg_cnt)*1.0/sum(imp_cnt)`](https://github.com/rilldata/rill-examples/blob/3516d3d144979d23ceded2a1a72efcbddd452800/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L39) | [`sum(click_reg_cnt)*1.0/nullif(sum(imp_cnt),0)`](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L39) |
| `ecpm` | [`sum(media_spend_usd)*1.0/1000/sum(imp_cnt)`](https://github.com/rilldata/rill-examples/blob/3516d3d144979d23ceded2a1a72efcbddd452800/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L64) | [`sum(media_spend_usd)*1.0/1000/nullif(sum(imp_cnt),0)`](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L64) |

A constructed DuckDB 1.4.4 division check returned `0.75` for `3/4` both ways, `inf` versus NULL for `1/0`, and `nan` versus NULL for `0/0`. Thus the change preserves ordinary nonzero-denominator values but alters zero-denominator behavior in that SQL engine. We did not load Rill's remote parquet or run the Rill service; actual source-row frequency and impact are unknown.

**Paper status.** These two independent public projects add a cross-grain positive control, a direct alias control, and a real versioned edge-case change to the development set. They are synthetic/examples, selected after inspection, and not held-out or independently adjudicated. Do not claim matching accuracy, prevalence, enterprise scale, or demonstrated superiority from them.
