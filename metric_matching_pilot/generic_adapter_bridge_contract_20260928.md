# Development adapter bridge contract (September 28, 2026 UTC)

This contract is fixed **before** combining the next two development agents' outputs. Its inputs are the already inspected public Jaffle Shop and GTM projects, their pinned source commits, and locally built development artifacts. No new held-out repository source may be opened as part of this bridge. It is a packet contract, not a completed extraction or evaluation.

## Join key and evidence levels

Join a declared metric/measure to a compiled model only by the same immutable repository commit plus an explicit source-model reference resolved to the model node's `original_file_path` or unique ID. Record a missing, ambiguous, or indirect reference as `needs_review`. A shared name, identical column name, or model-level `depends_on` edge is insufficient to establish a compiled metric expression. A submodule build must also record its own pinned commit and dependency version.

Keep the following evidence levels distinct:

1. **Declared candidate**: stable metric/measure ID, source YAML/SQL path and lines or a reason its location is unknown, declared aggregation/expression and explicit eligibility basis. A dimension, entity key, arbitrary SELECT output or model field is not a numeric metric by default. Unknown numeric type remains visible in coverage rather than silently filtered.
2. **Verified compiled model**: an actual dbt manifest node, its original source path/blob or file digest, manifest path/digest, real compiled SQL path/digest, and whether file bytes match `compiled_code` exactly or only under a reported normalization. Source-to-compiled *model* provenance does not imply metric-to-compiled-*expression* provenance.
3. **Verified compiled metric expression**: unique mapping from the declaration to a compiled scalar expression and its source locations, including dependency/CTE and field ownership. Only claim this level if the adapter really traces that edge; otherwise keep `compiled_metric_expression_status: needs_review` even when the model compiles.
4. **Business-semantic prerequisites**: grain, grouping, time window, population, join cardinality, absent rows/NULL, unit, snapshot and currency. Source syntax or a compiled model does not verify these automatically. Missing decisive fields force conditional review/abstention; no equivalence label follows from an expression match.

## Denominators and comparisons

- Report every scanned file/declaration and unsupported parse, plus why an output was eligible, ineligible or unresolved. A parser failure with unknown projection arity cannot establish a complete metric universe. Show `N(N−1)/2` only for the exact set of **emitted eligible IDs**, naming its coverage limit.
- A label-free `I1` packet carries the same versioned source, compiled provenance where available, missing fields and all candidate IDs to the AST/lineage, constraint-aware and proposed methods. Exact/name-only baselines use a declared `I0` subset. Store packet and pair-set SHA-256 and method versions. Do not insert author labels, AI review, reconciliation outcomes or oracle prerequisites.
- SQL execution on public rows supplies finite observations with engine/version/input digest. No observed equality proves universal equivalence or cross-engine portability. Do not compare method accuracy or reviewer benefit without independently human-adjudicated held-out labels.

## Review gate for the parallel outputs

An independent reviewer should inspect the final code hashes and run `--check` for both reports. Counterexamples must include: entity key or dimension not promoted to metric, unresolved declaration retained in the denominator, manifest `compiled_code` versus tampered/missing compiled file, mismatched/mutable repository commit, and a declared metric whose referenced compiled model is present but whose **metric expression** is not verified. A pass at levels 1 and 2 remains a **partial development pass** until level 3, generic eligibility, and the fair `I1` path are demonstrated. Preserve all v1–v4 freezes and append any new checkpoint only after reviews are complete.

The public-only scope decision in `public_only_venue_and_data_plan_20260928.md` controls manuscript use. Employer-derived examples in the working synthetic fixture are not cleared for public release.
