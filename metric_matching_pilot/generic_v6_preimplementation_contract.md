# Public development v6 contract (September 28, 2026 UTC)

This contract precedes the v6 implementation slices. Inputs are **only** the
already inspected public Jaffle/Sidemantic checkout at commit
`7be2c5838dbdeca8e915d4e46db70e910753d7f6`, its local
`target/manifest.json`, and the reviewed v5 eligibility and compiled-model
reports. No newly selected held-out repository source may be read. Preserve
the v1–v5 hash checkpoints unchanged.

## Metric expression mapping

Trace each of the 32 resource-qualified manifest declarations separately (19
metrics and 13 semantic-model measures), including all unknown eligibility
records. A metric's measure dependency is **not** a duplicate or equivalence
label. A declaration can have a `model_candidate` if its exact manifest
semantic-model dependency uniquely references a compiled model. Report the
source path, manifest resource IDs, model node, field/expression, and exact
artifact hashes. `compiled_metric_expression_status=verified` requires a
unique expression and field owner through the compiled model, source-to-build
alignment, and no unexpanded star, join, CTE, macro, or ambiguous projection
edge. A model's mere `depends_on` edge, matching column name, or checksum-free
source alignment does **not** suffice. Jaffle's 13 model source mappings are
currently `needs_review` due to a manifest checksum discrepancy; retain that
stop even if compiled files match `compiled_code`. A synthetic or in-memory
positive control may exercise the code path, but is not public-corpus coverage.
No business-semantic equivalence follows from any expression trace.

## One common evidence packet

Build a label-free I1 packet for all 32 declaration IDs and their 496
unordered within-project pairs, including unknown numeric eligibility, source
and artifact hashes, type, measure expression, dependency/model trace status,
grain/time/population/NULL/snapshot/unit unknowns, and stop reasons. Preserve
the exposed-metric 19-ID/171-pair subset separately. Hash the canonical packet
and the pair IDs. Give **exactly those same** I1 bytes and pair IDs to a
normalized AST/source comparator, a constraint-aware comparator, and a
source-guided conditional method; store versions and evidence fields used.
The I0 name-only methods receive an explicitly marked subset of that packet
with the same pair IDs. A method may emit a syntactic/review **candidate** or
abstain; no method may assert semantic equivalence without a complete verified
scope and transformation. Same-input does not imply matched semantic coverage.
No AI/author labels, development reconciliation results, repository-selection
outcomes, or tuned thresholds belong in the packet.

## Gate and review

An independent reviewer reruns final `--check` reports, verifies code and
report hashes, pair-set exhaustiveness, shared I1 hash, identical 496 pair IDs,
method versions, and negative controls: ambiguous measure binding, `SELECT *`
with joined field ownership, tampered compiled SQL, source checksum mismatch,
missing NULL/time/snapshot, and unknown metric type. Report both emitted-ID
coverage and unknowable true arity. If any expression mapping or common-input
method remains partial, retain the held-out source gate as blocked. No human
gold, accuracy estimate, review-effort outcome, or superiority claim is
created by this development work. The existing public-only release restriction
on the pilot ZIP still applies.
