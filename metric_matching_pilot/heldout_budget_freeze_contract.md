# Pre-source anchor budget freeze contract (development planning aid)

Date: 2026-09-29. This companion to `heldout_sampling_protocol.md` and `evaluation_contract.md` estimates human effort **before** opening a new evaluation source. It does not amend either protocol, freeze an actual search frame, decide repository eligibility, select independent projects, identify real metrics, or establish human gold. Run it on a supplied metadata-only candidate manifest outside this repository. Keep its input and JSON output with a dated digest as a planning record; resolve the policy items below and freeze the actual frame and metric IDs before heldout work.

## Input boundary

`python evaluate_readiness_budget.py /tmp/candidate_manifest.json` prints one JSON plan to standard output and exits with status 2 on invalid input. The only file it opens is that explicitly supplied JSON manifest; it refuses paths within this repository, including symlinks resolving into it. It does not traverse projects, open source or labels, access Git or a network, or write results. The JSON must have exactly these fields (decimal quantities are **strings**, not JSON numbers):

```json
{
  "schema_version": 1,
  "manifest_kind": "metadata_only_pre_source",
  "candidate_snapshot_id": "development-example-1",
  "projects": [
    {
      "project_key": "example/alpha@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "planned_eligible_metric_count": 8
    }
  ],
  "budget": {
    "total_reviewer_person_hours": "12",
    "annotation_minutes_per_pair_per_annotator": "6",
    "adjudication_fraction": "0.20",
    "adjudication_minutes_per_case": "9",
    "audit_fraction": "0.10",
    "audit_minutes_per_case": "5",
    "coordination_reserve_minutes": "45",
    "target_anchors_per_project": 3
  }
}
```

`project_key` is a lowercase `owner/repo@40-hex-commit` metadata identifier. Each repository may appear once. The count is a *planned* cardinality of eligible scalar definitions at that version, not a source-screen result; zero and one are allowed but cannot yield a pair anchor. It does not enumerate real IDs. Supply 1–50 candidates, counts 0–10,000 each and at most 100,000 combined, and a target of 1–100 anchors per project. The budget is aggregate **person hours**, not elapsed calendar hours. Minute assumptions and fractions use plain nonnegative decimal strings with at most four fractional places; annotation time and total hours must be positive, fractions must be at most one, and case time must be positive when its fraction is positive. Coordination is a fixed reserve charged once if any anchors are planned. The adjudication fraction is an assumed share of distinct pairs needing a third reviewer; the audit fraction is an assumed share audited after agreement. Both are assumptions, not outcome estimates from heldout labels.

All keys are required; unknown keys, duplicate JSON keys, duplicate repositories, noncanonical IDs, wrong types, nonfinite numbers, and malformed JSON are rejected. In particular, source paths, SQL, labels, positive counts, prediction fields, and eligibility verdicts cannot be attached to this schema. The external manifest path and 1 MB cap make accidental repository reading less likely; the operator remains responsible for supplying only metadata.

## Deterministic budget rule

For each project with planned count `n`, the planner makes ordinal placeholders `slot_000001` through `slot_NNNNNN`. These placeholders are **not metric IDs**. Project traversal sorts lowercase hexadecimal SHA-256 of UTF-8 `project_key` lexicographically, with the key as a tie break. Within a project, slots sort by lowercase hexadecimal SHA-256 of UTF-8 `project_key + "\nslot:" + six_digit_ordinal`, with slot text as a tie break. The complete placeholder hash order and the selected prefix appear in output. Reordering input projects cannot change the plan. After actual eligible IDs are known, freeze a separately specified hash order over those IDs before viewing labels or system results; ordinal slots must not be relabeled into purported selected metrics.

The planner attempts the first anchor in each project in project order, then the second in each, up to the requested target and at most `n` anchors. Each tentative addition is retained only if the recomputed total fits the fixed budget. This is a deterministic lower-anchor fallback; it is a transparent allocation rule, not a global optimization or a way to choose eligible projects. A count below two receives no anchor. A project whose next complete anchor costs too much may be skipped while a smaller project's anchor fits.

For `a` selected anchors among `n` planned metrics, anchor-candidate incidences are `a(n−1)` and distinct unordered pairs are `a(n−1) − a(a−1)/2`. Each distinct pair receives **two independent annotations** once, even if it belongs to two anchor universes. Annotation person minutes are `2 × distinct_pairs × minutes_per_pair_per_annotator`. Reserve cases are `ceil(fraction × distinct_pairs)` **per project** for adjudication and audit, multiplied by their respective minutes per case. Add the fixed coordination reserve. Budget comparison uses full decimal minutes; displayed hours are rounded to four places. This counts all other planned eligible definitions per anchor, including anticipated extraction failures, and never treats sampled lexical pairs as a complete universe.

If no complete anchor fits, the designation is `judged_pool_only`. Its reported distinct-pair capacity is a conservative count under the same two-annotator and reserve assumptions, bounded by all planned unordered pairs. Because pair allocation across projects is unknown, it reserves up to `min(pairs, ceil(fraction × pairs) + min(pairs, pair-capable projects) − 1)` cases for each nonzero fraction, an upper bound on per-project ceiling sums. It does not pick pairs, create a recall denominator, or promise that a partial pool can be scored. A zero capacity means even a single pair is unaffordable. A later pool sampling rule must be frozen independently; only **judged-pool recall** may eventually be named for that pool. If some complete anchors fit below target, the selected lower quota is shown and no leftover pair pool is silently added.

## Decisions still required before any evaluation claim

Every output includes five `unresolved_policy` fields: `unknown_eligibility_handling`, `source_screen`, `project_independence`, `reviewer_availability`, and `conditional_gold`. In particular:

- Freeze the search frame, source-screen rules, exclusions and replacements, pinned revisions, related-project decisions, actual eligible scalar IDs, extraction failures, and actual anchor order under the existing protocols. The manifest's planned counts confer no eligibility or independence.
- Obtain two qualified, independent human annotators, a third adjudicator and audit capacity. Rebudget if actual counts, pair times, or availability differ; retain the earlier plan and date the change before seeing affected outcomes.
- Preserve native and conditional target judgments separately. An unresolved `needs_review` pair or decisive conditional prerequisite cannot be counted as a negative or a resolved positive. Rare natural positives and zero-positive anchors remain as found; no label-based top-up is allowed.
- Exact Recall@k remains **unestablished** for every output. It requires actual complete, sufficiently resolved anchor-candidate universes for the particular target, frozen ranking rules and denominators, and the evaluation contract's human process. A budgeted complete universe is only a prospective workload calculation.

Run `python -B verify_evaluate_readiness_budget.py` for toy controls covering pair deduplication, two-person hours, reserve rounding, lexical hash selection, lower-anchor fallback, an unaffordable universe, hypothetical rare positives and unresolved judgments, and input rejection. These controls use invented counts and never supply outcomes to the planner.
