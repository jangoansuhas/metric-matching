# Prospective amendment: source inventory before reviewer staffing

**Recorded 2026-09-29T20:09:11Z, before opening any new held-out repository source.** This is an internal protocol amendment, not an external preregistration. The previous `public_pair_selection_freeze.md` and `public_study_presolve_policy_20260929.md` required committed human reviewer capacity before source inspection. That order has blocked the project-level metric and compilation denominators reviewers asked for. The amended order below permits an outcome-blind **eligibility and extraction screen** now and keeps human annotation gated on staffing. The original texts and hashes remain in the archive for audit; this amendment changes only the timing of the reviewer-capacity gate.

## Immutable inputs and selection

- Use the dated 65-occurrence/62-distinct-repository search manifest SHA-256 `6404c6aa719456abb4b28a82198c695f09ded48bbb442347fa0b7fdedc7db10f` and the complete hash-sorted queue SHA-256 `3ffb00fa94642fb27574c156ba0e8412bd493483fda5902602d48ea69119b472`. Do not update HEADs or reorder the queue.
- Screen a contiguous prefix in queue order at the recorded commit. Apply the same family/independence, public access, versioned SQL/dbt, and at-least-two-inspectable numeric scalar output criteria in the original freeze. Stop at the first two independent eligible projects. Record every screened row and every rejection, quarantine, access failure, source count and evidence; leave the unscreened tail unopened. A project is not rejected for few positive pairs, unsupported syntax or a failed build.
- Generic adapter identity remains the already fixed `metric_provenance_verification/inputs/run_adapter.py` SHA-256 `7b90ef37dfb1cce9c0a15f211ef89fb56106a0f1eb8817ed0ae405ad05ce09fe`. No tuning on screened repository results. Run it on the selected pinned projects when technically possible; report exceptions and the complete definition denominator, rather than replacing a project because compilation fails.

## Information boundary

The screener may inspect repository metadata, license/README, dbt/project configuration, declared metric/measure YAML, and enough versioned SQL to determine declaration existence, numeric/aggregate status, source location, and independent project/dataset provenance. It may run a pinned adapter/parse/SQL-generation attempt for **coverage only** after project selection. Record failure classes and tool versions. Do **not** compare two metric definitions, inspect pair labels, run relationship methods, execute metric values, choose a positive-looking case, draw the pair sample, or view human worksheets in this phase. The source inventory and extraction report are still held-out corpus-flow observations; they are not method accuracy or gold.

## Reviewer gate retained

Freeze and hash each selected project's full numeric output inventory and all within-project unordered pair IDs, including unsupported definitions, before method execution. Hold the fixed lexical/lineage/hash-random pair draw, classifier evaluation, and human labeling until two qualified independent reviewers and a distinct adjudicator commit the 24-person-hour core and receive identical prediction-free packets. The existing up-to-eight-pairs-per-project ceiling and no-exact-Recall@k rule remain. If staffing does not materialize, publish only the eligibility/extraction coverage and bounded development findings; do not call the unjudged corpus an accuracy evaluation or substitute AI review for human gold.

This amendment is prospective relative to the affected source screen. It is a practical sequencing change, not an outcome-based project replacement. Any subsequent deviation must be dated before inspecting the affected outputs.
