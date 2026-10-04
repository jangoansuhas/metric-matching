# Compiled dbt MODEL provenance audit (development only)

Source is anchored to a pinned Git blob. Compiled file equality is checked against manifest `compiled_code` as exact bytes; whitespace-only agreement is reported separately. Source alignment distinguishes exact bytes, one trailing LF, other strip-only agreement, and differences. A dbt manifest checksum can hash normalized `raw_code`; it is checked against both raw_code and the pinned blob without assuming it is a hash of source file bytes. Manifest generation is a distinct build event without an attested commit. A MODEL artifact pass does **not** establish metric-expression lineage or semantic equivalence.

| Repository | Commit matches | Project / dbt | Models | Pinned blobs | Compiled exact | Raw exact / +LF / strip | Checksum = blob / raw | Mapping review | Node review |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `public_corpus/gtm-funnel-analytics` | True | `arcline` / `1.11.6` | 33 | 33 | 33 | 0 / 33 / 0 | 0 / 33 | 0 | 0 |
| `public_corpus/jaffle-shop-sidemantic/jaffle-shop` | True | `jaffle_shop` / `1.12.5` | 13 | 13 | 13 | 0 / 13 / 0 | 0 / 0 | 13 | 13 |

## Review reasons

### `public_corpus/gtm-funnel-analytics`

Pinned commit: `a71232c123a5fb78da9b52d4246950ee48591c00`; manifest SHA-256: `16c739b2ff2348c0047b564b08a0dac43bcfe4ee25cd3d2a761b912fc646fe95`. Manifest generated at `2026-09-27T18:14:32.653406Z` (a separate, unauthenticated build event).

- No node-level check failures.

### `public_corpus/jaffle-shop-sidemantic/jaffle-shop`

Pinned commit: `7be2c5838dbdeca8e915d4e46db70e910753d7f6`; manifest SHA-256: `1467a9a6a71de14f196adbab89927083adcc2b9f680f7e9b6256a0720b40fb24`. Manifest generated at `2026-09-27T17:51:14.701525Z` (a separate, unauthenticated build event).

- `manifest_source_checksum_different_vs_raw_code`: 13 model(s).

No newly selected or held-out repository source was read. See the JSON report for every MODEL node, its paths, artifact hashes, comparison status and review reasons.
