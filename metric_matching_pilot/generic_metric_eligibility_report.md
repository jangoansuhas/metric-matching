# Generic dbt metric-output eligibility (development only)

Source: `yaml` for `jaffle_shop@5beb145b00f5465ec759cfcdd9745e858818cf95`; PyYAML 6.0.3.
Reads pinned Git YAML blobs, not checkout edits.

| Category | Count |
| --- | ---: |
| Declared scalar candidates (metrics + measures) | 23 |
| Metric declarations | 23 |
| Measure declarations | 0 |
| Unresolved-scope placeholders | 0 |
| Eligible by declared numeric aggregation | 13 |
| Unknown numeric status | 10 |
| Primary exposed-metric pairs | 253 |
| Secondary all-declared-scalar pairs | 253 |

Pinned model-path YAML files scanned: 14.
Pinned project file: `dbt_project.yml` (SHA256 `4ef498cd66a1f7badfde6d3d366ed908db07f598b9b63657ee89f7407c47f01c`).

| Non-candidate / unknown category | Count |
| --- | ---: |
| dimension_columns | 25 |
| entity_columns | 10 |
| ordinary_columns | 13 |

| Unknown reason | Count |
| --- | ---: |
| dependency_numeric_type_unverified | 6 |
| jinja | 4 |

## Reconciliation and limits

Primary pairs use exposed metric declarations. Secondary pairs also include each declared measure under its own resource-qualified ID. A metric-to-measure reference is a dependency, not a duplicate ID or an equivalence label. Source YAML and built manifests can represent different revisions and transformations; compare paths, revisions and build provenance before interpreting count differences.

- Pair completeness applies only to emitted IDs (including unresolved placeholders) in each frame; invalid YAML/container shapes can hide an unknown number of declarations.
- Declared metrics and measures are distinct scalar definitions with resource-qualified IDs. A metric's measure reference is a dependency, not an equivalence label; same names do not collapse units.
- Dimensions, entity keys and ordinary SQL projections are not declared metric outputs.
- A numeric aggregation is declaration-level type evidence, not verified runtime value or equivalence.
- Derived, ratio, cumulative and unsupported numeric results remain unknown without resolved dependency types.
- YAML source and manifest resources are different inventories; separate revisions/build transformations can change counts.
- A manifest hash and a pinned checkout do not establish that the manifest was built from that commit; compiled provenance and source mapping remain unverified.
- No labels, row outcomes, candidate correctness or method superiority are measured.

Control `generic_metric_eligibility_negative.yml` SHA256 `320809e34a2e877224da69ac3a98840188738faa4114619453a51238cf3b49a1`: Numeric entity_key and arbitrary value columns are excluded; templated, untyped and malformed metric declarations remain unknown; same-named metric and measure remain distinct; only an exact dependency permits measure-derived eligibility.

## Reproduce

```bash
python3 -B metric_matching_pilot/generic_metric_eligibility.py --repo public_corpus/jaffle-shop --expected-commit 5beb145b00f5465ec759cfcdd9745e858818cf95 --source yaml --output-prefix metric_matching_pilot/generic_metric_eligibility_report --check
```
