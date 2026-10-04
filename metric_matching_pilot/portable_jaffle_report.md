# Portable dbt YAML metric inventory — development only

Pinned `jaffle_shop@5beb145b00f5465ec759cfcdd9745e858818cf95`. Source YAML only; no compilation or rows.

| Inventory | Count |
| --- | ---: |
| YAML files scanned | 14 |
| YAML files with definitions | 4 |
| Metric cards | 23 |
| Unordered pairs | 253 |
| Syntactically supported simple declarations | 9 |
| Definitions excluded | 0 |

| Metric type | Count |
| --- | ---: |
| `cumulative` | 1 |
| `derived` | 3 |
| `ratio` | 2 |
| `simple` | 17 |

| Syntactic status | Count |
| --- | ---: |
| `non_simple_unresolved` | 6 |
| `simple_bare_field` | 4 |
| `simple_implicit_expression` | 6 |
| `simple_numeric_constant` | 5 |
| `simple_unsupported_expression` | 2 |

| Review diagnostic | Count |
| --- | ---: |
| Bare fields absent from model YAML columns | 3 |
| Raw filters unresolved | 4 |
| Metric dependencies unresolved | 6 |

## Exclusions and limits

10 scanned model-path YAML files had no native metric definitions; 7 other tracked YAML files were outside dbt's configured model paths. Saved-query references, measures, tests and source rows are excluded as definitions; zero native metric definitions were dropped.

- Recognized definitions under configured model-paths: top-level metrics and metrics directly on models/semantic_models; malformed sequences fail explicitly.
- Source expressions are verbatim declarations; raw filters are in declared_filter while where_expr stays null. Neither is compiled or resolved SQL.
- Bare fields are syntactic names only; primary columns and aggregate time dimensions are declarations, not verified output grain or period.
- Every card requires semantic review; there are no relationship labels, gold pairs or row observations.

The packet has no gold labels or row observations. Null grain, period, units, grouping and join properties remain unresolved; the card list and all pairs require review.
