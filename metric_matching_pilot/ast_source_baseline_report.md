# I1 SQL AST source baseline — GTM development packet

Method: `sqlglot_ast_source_i1_v1`. Same packet bytes: SHA-256 `7fffd7366e333f907c70938544b92c07a0fb22c29845b7aaf20c7d319c1d5aed`. The packet has 11 cards and all 55 unordered pairs; outcomes are source candidates or abstentions.

## Dependency and parser coverage

Exact dependency: `sqlglot==30.20.0`; DuckDB parser. Installed version: `30.20.0`. Install with `python -m pip install 'sqlglot==30.20.0'`. A missing or different version makes all 55 outputs abstentions.

| Packet expression field | Non-null | AST parsed | Unsupported | Absent |
| --- | ---: | ---: | ---: | ---: |
| `value_expr` | 11 | 11 | 0 | 0 |
| `where_expr` | 9 | 9 | 0 | 2 |
| `period_expr` | 11 | 11 | 0 | 0 |
| `segment_expr` | 11 | 11 | 0 | 0 |
| `group_by` | 8 | 8 | 0 | 3 |
| `time_key` | 3 | 3 | 0 | 8 |

Parser unsupported occurrences: **0**. Absent optional fields are tracked separately and are not parser failures.

Parsed value shapes: `avg` 1, `count` 2, `field` 3, `percentile` 2, `ratio` 1, `sum` 2.
The percentile, AVG, and ratio shapes parse but do not qualify for additive rollup. A field projection alone is also not an additive aggregate.

## Same-input comparison with the existing constraint baseline

| Decision | SQL AST I1 | Constraint-aware I1 |
| --- | ---: | ---: |
| `direct_candidate` | 0 | 0 |
| `conditional_candidate` | 2 | 2 |
| `scope_variant_candidate` | 0 | 0 |
| `related_candidate` | 3 | 3 |
| `abstain` | 50 | 50 |

Decision agreement: 55/55. Decision disagreements: 0.

There is no demonstrated incremental candidate gain over the constraint baseline.

## Decision scope and limits

The parser reads compiled value, filter, period, segment, grouping, and optional time-key expressions from the same packet used by the other I1 methods. It retains the original expression and source/compiled locations in every pair's evidence. AST comparison keeps string and numeric literal tokens in order, plus NULL and inequality/date-bound operators. SQLGlot interprets DuckDB casts (`::`), `IS NOT NULL`, and grouping parentheses; the method does not commute predicates, change stage literals or dates, or prove SQL equivalence.

A cross-grain candidate requires identical source, value AST, filter AST, segment AST, input fields, a month period key, a constant date window label, and grouping sets that reduce after removing that key. Only `COUNT(*)` and a simple `SUM(column)` core are treated as additive. Literal `BETWEEN` bounds are evidence of syntax, not coverage. A rounded `SUM` requires aggregation of unrounded cores followed by one final rounding; a `DOUBLE` cast leaves numeric equality open.

Visible stage equalities with different case-sensitive string literals may be related candidates, with a contradicted filter prerequisite. Neither stage populations nor upstream field lineage are established by the packet. Unknown join cardinality, NULL policy, missing groups and zero fill, time zone, units, snapshot, grouping expansion, period coverage, and source membership remain explicit conditions. Source candidates are not verified equivalences, accuracy results, or built-row reconciliations.

## Reproduction

From the workspace root: `python metric_matching_pilot/ast_source_baseline.py` writes only the two sidecar reports. `python metric_matching_pilot/ast_source_baseline.py --check` reads the packet and existing reports, validates exact output bytes, and writes nothing.
