# Held-out search metadata capture run report

**Date:** 2026-09-28 UTC. The only GitHub requests were anonymous repository search, Git-ref metadata, and a rate-limit check. No repository source, README, SQL/YAML, or metric definition was opened.

## Attempt history

| Attempt | Disposition | Captured fixed pages | Terminal HEADs | Manifest |
| --- | --- | ---: | ---: | --- |
| `attempt-20260928T015233Z-9167c2e2` | `integrity_failed`; preserved unchanged after failure marking | 3/3 | 29/62 | None |
| `attempt-20260928T015929Z-0d075346` | `abandoned_for_persistence_revision`; preserved | 3/3 | 5/62 | None |
| `attempt-20260928T020324Z-1c3dd1fe` | **`finalized`** under the hashed revised script | **3/3** | **62/62** | `manifest.json` |

The first failure was an observed persistence-integrity mismatch: `refs/repo_1376352072_01.headers.bin` was 56 bytes when checked, with SHA-256 `1a2d2ae6d3df5252e458622a26569141aa465786b69503352e2b2b71c1ec9e9b`, while its saved response record required `6c893ca1d718c732eedd6d441850dc8dc56a8a3c7bfd8cce496360d47f15628f`. The remaining 56-byte header contained only an HTTP/1.1 status and `Date`, not the saved GitHub request ID. The surviving artifacts do not establish which process or network event changed it. The original implementation wrote curl output directly to final paths, had no per-attempt writer lock, and could reuse a stem after an interrupted header-only request because it counted only body files. These were concrete persistence hazards; no digest was edited to make the failed attempt pass.

The script now holds an exclusive attempt lock; stages each curl body/header in unique `inflight/` paths; publishes completed raw files with atomic renames; avoids stems occupied by either a body or header; records interrupted artifacts; and rejects saved-digest mismatches. It hashes the script, precommit, and development snapshot and refuses to resume with changed inputs. The second attempt was stopped before this last persistence revision so that the final run used one script hash throughout. Neither earlier attempt supplied a page or HEAD record to the final attempt.

## Final bounded frame

- Acquisition interval: **2026-09-28T02:03:24.268265Z** to **2026-09-28T02:12:18.566284Z**. This is an observation window, not one atomic GitHub timestamp.
- Fixed requests: the three precommitted `sort=updated&order=desc&per_page=30&page=1` repository queries, in order. All three HTTP 200 pages had `incomplete_results=false`: **30 + 30 + 5 = 65 ordered occurrences**, with duplicates retained at their original query ranks.
- **62 distinct repositories; 62 metadata-only default-branch refs with commit SHAs; zero unavailable refs.** The response log contains 63 recorded ref transport attempts, including one timed-out attempt later retried. Three partial `inflight/` header artifacts from interrupted calls are separately recorded in the manifest and were never treated as HEAD results. A fourth, empty staging header found after finalization is disclosed in the final attempt's `postfinal_artifact_audit.md`; it is not a ref response and the manifest was not changed.
- Independent verification rehashed every saved page/ref body and header, checked every rank, verified the 62 terminal ref records, and matched the script/precommit hashes and `manifest.sha256`.
- Final manifest SHA-256: `6404c6aa719456abb4b28a82198c695f09ded48bbb442347fa0b7fdedc7db10f`.
- The exact capture script used in this finalized attempt is archived as `attempt-20260928T020324Z-1c3dd1fe/capture_script_snapshot.py`, SHA-256 `fed5d2a9cc49144a94ef703b69185ddaf8359b7a2190d0d7044ba8dfc8e888c2`. The current working script has been restored byte-for-byte to that finalized version; the later improvement is archived separately as a future candidate.

## Capture-script provenance correction

The finalized manifest's `capture_script_sha256` refers to the script **as executed for that attempt**. The current `../capture_heldout_search_frame.py` has been restored byte-for-byte from `../development_revision_history/capture_script_finalized_v1.py`; both and the attempt's `capture_script_snapshot.py` have SHA-256 `fed5d2a9cc49144a94ef703b69185ddaf8359b7a2190d0d7044ba8dfc8e888c2`. A post-final improvement that inventories staging files immediately before finalization and archives the script at new-attempt creation is preserved separately at `../development_revision_history/capture_script_future_candidate_v2.py`, SHA-256 `2663fd9b06721bdcd192b479551d8b35604c09457888402152586597e58acec1`. The manifest and its hash were **not** rewritten.

This freezes the **bounded search metadata frame and observed HEAD SHAs only**. It does not establish repository eligibility, independence, positive matches, human gold labels, or an atomic as-of view. The precommit's separate generic-adapter/development-check gate still applies before opening new held-out source.
