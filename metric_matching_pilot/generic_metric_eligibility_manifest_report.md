# Generic dbt metric-output eligibility (development only)

Source: `manifest` for `jaffle_shop@7be2c5838dbdeca8e915d4e46db70e910753d7f6`; PyYAML 6.0.3.
Manifest build commit is unverified.

| Category | Count |
| --- | ---: |
| Declared scalar candidates (metrics + measures) | 32 |
| Metric declarations | 19 |
| Measure declarations | 13 |
| Unresolved-scope placeholders | 0 |
| Eligible by declared numeric aggregation | 22 |
| Unknown numeric status | 10 |
| Primary exposed-metric pairs | 171 |
| Secondary all-declared-scalar pairs | 496 |

Manifest resources: 19 metrics, 6 semantic models. Measures are listed within those models.
Manifest input: `target/manifest.json` (SHA256 `1467a9a6a71de14f196adbab89927083adcc2b9f680f7e9b6256a0720b40fb24`); build commit unattested, source mapping unverified.
Pinned project file: `dbt_project.yml` (SHA256 `f71f84b9198be0d30263b350ac278694fd485aa1c5393359a650da5a8b121122`).

| Non-candidate / unknown category | Count |
| --- | ---: |
| dimensions | 25 |
| entities | 10 |

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
python3 -B metric_matching_pilot/generic_metric_eligibility.py --repo public_corpus/jaffle-shop-sidemantic/jaffle-shop --expected-commit 7be2c5838dbdeca8e915d4e46db70e910753d7f6 --source manifest --manifest public_corpus/jaffle-shop-sidemantic/jaffle-shop/target/manifest.json --output-prefix metric_matching_pilot/generic_metric_eligibility_manifest_report --check
```
