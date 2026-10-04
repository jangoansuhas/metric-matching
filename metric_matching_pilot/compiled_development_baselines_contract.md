# Compiled Jaffle development baseline contract

**Status:** Development-only comparison contract, September 29, 2026. The
versioned adapter and packet bytes are fixed for this diagnostic. This is not
a held-out evaluation, human gold, or a published match-quality result.

## Input and pair frame

- Public Jaffle Shop Git commit:
  `7be2c5838dbdeca8e915d4e46db70e910753d7f6`.
- Source bundle: `metric_provenance_jaffle_7be2c58.zip`, SHA-256
  `322aec391ce98c05a51c79a30abae803378d350e824a2e21f07ea0161f28380e`.
  Its `inputs/run_adapter.py` SHA-256 is
  `7b90ef37dfb1cce9c0a15f211ef89fb56106a0f1eb8817ed0ae405ad05ce09fe`.
  The effective `inputs/package-lock.yml.after_deps` SHA-256 is
  `67ecfc0a7ebdcc03b8e2f38c86d7b283e72c5d58fb9a7de9b4f30aa2a3a01eef`;
  the committed lock is different and `audit_helper` floats on `main`.
- Local derived input: `compiled_jaffle_i1_packet.json`, SHA-256
  `78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`.
  It is regenerated from the source bundle with `compiled_jaffle_packet.py`.
- The complete **emitted declared-metric** frame contains 19 IDs and all 171
  unordered pairs. This is not a verified universal numeric-eligibility rule.
  No pairs are selected based on a known or suspected relationship.
  Every card explicitly records numeric eligibility as unverified by this
  compiled bundle; the separate earlier inventory classified nine eligible
  and ten unknown under its own conservative policy.
- SQL for 18 metrics was generated ungrouped. `revenue_growth_mom` has only a
  generated `metric_time` query. The 153 pairs between ungrouped outputs are
  comparable at this limited query scope; the 18 mixed-scope pairs remain in
  the denominator and both I1 methods abstain. No other time-grouped queries
  were generated. SQL generation did not execute metric values.

## Information budget

- **I0:** Metric names and stable pair IDs only. Score exact, normalized exact,
  Jaro–Winkler, token Jaccard and Soundex without a classification threshold.
- **I1:** The exact same two packet cards for the initially implemented methods: public
  YAML declaration metadata from fresh manifests, source-model `raw_code` and
  dependencies, resolved input measures and owners, and MetricFlow-generated
  DuckDB SQL. Field identity and YAML line spans are source-linked, but the
  spans are text-located and source SQL may still contain Jinja/macros.
  Join cardinality, units, population/snapshot policy, missing-group handling,
  and null behavior stay **unknown** unless explicitly supported; a model name,
  same SQL at one scope, or finite sample equality cannot fill them in.
  The AST comparator pins SQLGlot **30.20.0**, DuckDB dialect. The initial I1
  comparators have fixed, source-only candidate-score rules and a lexical
  pair-ID tie break; these scores do not turn abstentions into semantic labels.
- No worksheet, constructed label, adjudication, method prediction, or selected
  positive enters the packet. The initial I1 comparators receive the same two cards
  for each of the 153 common-scope pairs; a shared harness hard-gates the other
  18. The pipeline emits a method result or abstention for all 171 pair IDs.
  Signals and candidate scores stay separate from semantic decisions.
- The frozen runner authenticates these packet bytes, not arbitrary future
  evidence records. The AST comparator checks the structure and claimed digest
  of supplemental provenance, but does not retrieve a locator or authenticate
  its bytes or reviewer. A future evaluation driver must check those records
  against source artifacts and reviewer provenance before any semantic class
  based on them is accepted; otherwise keep the decision at `abstain`.

## Outcomes and limits

Report pair IDs, packet and method hashes (including the comparison runner),
the effective SQLGlot version and DuckDB dialect, compiler/source coverage,
syntax signals, positive-score and score coverage on the 153 common-scope
pairs, semantic decision counts over all 171 pairs, and abstention reasons.
Without independently adjudicated reference labels, do **not** calculate F1,
precision, unsafe-equivalence rate, candidate Recall@k, or a superiority claim.
If a method has no decisions, its safety is untestable rather than zero-error.
Do not use this development packet as human gold; maintain the unchanged blank
practice packet for independent reviewers.

Before inspecting a new held-out repository, fix the numeric-eligibility rule,
fair same-input methods and budgets, sampling protocol, and reviewer capacity.
The dated metadata-only search-result manifest exists; this contract does not
open or select held-out repository source.

**Later development addendum (September 29, 2026):**
`compiled_proposed_development_contract.md` fixes a declaration-level numeric
gate and a proposed source-review method on these unchanged packet bytes.
All three I1 methods now run in the same harness. The numeric gate leaves
runtime type unverified; sampling, reviewer budget, evidence authentication
and reference labels still gate the held-out study.
