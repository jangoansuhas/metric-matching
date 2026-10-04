# Independent review: portable development evidence trace

**Current disposition: PASS for pinned raw-source tracing.** The three findings in the prior review are resolved. This remains file and dependency evidence; it does not establish compiled SQL, output-field lineage, or metric semantics.

| Check | Result | Independent evidence |
| --- | --- | --- |
| Immutable source selection | **PASS** | `rev-parse HEAD` must be a 40-hex commit equal to the packet commit (`trace_portable_development_evidence.py:184-186`). Subsequent project/YAML and SQL `show` calls use `at_commit(project, commit, path)` (`:41-42`, `:187`, `:203`, `:359`); the model inventory uses the same commit in `ls-tree` (`:196`). No source blob read uses a moving `HEAD` ref. |
| Coverage and dependencies | **PASS** | Independently indexed 23 unique metric IDs and YAML line ranges from 14 model YAML files at commit `5beb145b00f5465ec759cfcdd9745e858818cf95`, exactly matching packet cards and JSON rows. The report has 17 adjacent raw SQL file links (7 explicit expressions, 6 omitted expressions, 4 unresolved Jinja filters), 6 dependency-only links, and 0 unlinked cards. Dependency target IDs resolve uniquely; `order_gross_profit` retains both source file paths. |
| SHA, ref, and line evidence | **PASS** | The packet hash and the packet/report SHA256 inventory match pinned `dbt_project.yml` and all 14 YAML blobs. All 23 YAML locations and all 10 cataloged raw SQL hashes/file spans match immutable-commit blobs. The catalog's 9 literal `ref` lines, 6 literal `source` lines, and 8 unsupported Jinja locations match the source. SQL hashes are recorded in the report; the packet does not attest them. |
| Report wording and limits | **PASS** | JSON `source_selection` (`:1099`) and the Markdown explanation (`:22`) distinguish packet-verified project/YAML hashes from independently recorded SQL hashes. The heading now says “Pinned raw-source development trace”; the Markdown explicitly says a direct link is a raw file link, without a proven metric expression or compiled field lineage. Every card has `compiled_sql: null` and `compiled_evidence_verified: false`; compiled-source and generated-decision totals are zero. Filters, omitted expressions, ratio/period/window behavior, grain, JOIN cardinality, and output-field lineage remain unresolved. |
| `--check` read-only | **PASS** | Recomputed reports match exactly: `python metric_matching_pilot/trace_portable_development_evidence.py --check` exited 0. Hashes and mtimes of the tracer, packet, and both reports were unchanged by the check. |

## Prior findings: resolved

1. **Mutable `HEAD`: closed.** The verified commit ID now addresses all `show` and `ls-tree` reads. The current JSON/Markdown reports pass an independent inventory and hash comparison against that immutable commit.
2. **Overbroad SHA provenance: closed.** `source_selection` (`trace_portable_development_evidence.py:381`) accurately separates packet checks for project/YAML from raw SQL hashes in the report.
3. **Compiled-evidence implication: closed.** The heading (`:425`; Markdown `:1`) and direct-link caveat (`:453`; Markdown `:22`) describe pinned raw source without implying compiled query or field-level proof.

**Scope:** re-reviewed the tracer, packet, regenerated JSON/Markdown reports, and pinned public development source. No held-out repository source was inspected. Only this review file was changed.
