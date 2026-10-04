# Automated adjacent-commit metric analysis — development case

Project `rill-openrtb-prog-ads`; parent `3516d3d144979d23ceded2a1a72efcbddd452800`; child `10a9bce8f0181623d8c596fbed7df37244666cc4`.

## Automated candidate linking and changes

The analyzer read 16 prior and 16 later measures; linked 16 by the declared `(metrics_view, measure)` ID without pair IDs; found 2 changed expressions. Added/removed or renamed measures remain unresolved.

| Measure | Before | After | Source-level classification |
| --- | --- | --- | --- |
| `bids_metrics.ctr` | [rill-openrtb-prog-ads/metrics/bids_metrics.yaml:39](https://github.com/rilldata/rill-examples/blob/3516d3d144979d23ceded2a1a72efcbddd452800/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L39) | [rill-openrtb-prog-ads/metrics/bids_metrics.yaml:39](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L39) | `zero_denominator_guard_added` |
| `bids_metrics.ecpm` | [rill-openrtb-prog-ads/metrics/bids_metrics.yaml:64](https://github.com/rilldata/rill-examples/blob/3516d3d144979d23ceded2a1a72efcbddd452800/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L64) | [rill-openrtb-prog-ads/metrics/bids_metrics.yaml:64](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/metrics/bids_metrics.yaml#L64) | `zero_denominator_guard_added` |

## Changed-input condition and declared consumers

### `bids_metrics.ctr`

Before: `sum(click_reg_cnt)*1.0/sum(imp_cnt)`. After: `sum(click_reg_cnt)*1.0/nullif(sum(imp_cnt),0)`.

The only supported expression change is guarding `sum(imp_cnt)` with `NULLIF(..., 0)`. For a zero grouped denominator, the new expression yields NULL; the old division-by-zero outcome depends on the engine. With a nonzero denominator, the expressions agree under the same inputs and numeric semantics. Observed Rill row impact: **unknown**.

Declared dashboard references in the child revision:

- wildcard_potential: [rill-openrtb-prog-ads/dashboards/bids_explore.yaml:10](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/bids_explore.yaml#L10)
- explicit_declaration: [rill-openrtb-prog-ads/dashboards/bids_explore.yaml:34](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/bids_explore.yaml#L34)
- explicit_declaration: [rill-openrtb-prog-ads/dashboards/executive_overview.yaml:111](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/executive_overview.yaml#L111)

Model-level source path (field-level lineage unresolved):
- `bids_data_model` reads `bids_data_raw` at [rill-openrtb-prog-ads/models/bids_data_model.sql:5](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/models/bids_data_model.sql#L5)

### `bids_metrics.ecpm`

Before: `sum(media_spend_usd)*1.0/1000/sum(imp_cnt)`. After: `sum(media_spend_usd)*1.0/1000/nullif(sum(imp_cnt),0)`.

The only supported expression change is guarding `sum(imp_cnt)` with `NULLIF(..., 0)`. For a zero grouped denominator, the new expression yields NULL; the old division-by-zero outcome depends on the engine. With a nonzero denominator, the expressions agree under the same inputs and numeric semantics. Observed Rill row impact: **unknown**.

Declared dashboard references in the child revision:

- wildcard_potential: [rill-openrtb-prog-ads/dashboards/bids_explore.yaml:10](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/bids_explore.yaml#L10)
- explicit_declaration: [rill-openrtb-prog-ads/dashboards/bids_explore.yaml:39](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/bids_explore.yaml#L39)
- explicit_declaration: [rill-openrtb-prog-ads/dashboards/executive_overview.yaml:112](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/dashboards/executive_overview.yaml#L112)

Model-level source path (field-level lineage unresolved):
- `bids_data_model` reads `bids_data_raw` at [rill-openrtb-prog-ads/models/bids_data_model.sql:5](https://github.com/rilldata/rill-examples/blob/10a9bce8f0181623d8c596fbed7df37244666cc4/rill-openrtb-prog-ads/models/bids_data_model.sql#L5)

## Boundaries

- No metric values or remote parquet queried
- No native Rill runtime executed
- Dashboard declarations show potential consumers, not actual use or affected users
- Model-level source recognition does not prove field lineage, population, or join cardinality
- No evaluation on unseen repositories and no matching accuracy measurement

This is a reproducible development case and a narrow automated source analysis. It is not a measured matcher, a proof of metric equivalence, or an industrial result.
