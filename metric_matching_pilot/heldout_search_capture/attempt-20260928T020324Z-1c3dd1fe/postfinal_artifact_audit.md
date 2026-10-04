# Post-final staging-artifact audit

The finalized `manifest.json` remains unchanged (SHA-256 `6404c6aa719456abb4b28a82198c695f09ded48bbb442347fa0b7fdedc7db10f`). An independent file-inventory check after finalization found one additional, untracked staging file:

- `inflight/repo_348550042_01-3ec1e23c.headers.bin`: **0 bytes**, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, filesystem modification time 2026-09-28T02:12:11.474819Z.

It is an empty temporary header path, not a completed HTTP response or pinned ref. The corresponding repository's final ref response was saved separately, and its body/header digests and commit SHA independently verified. All 62 terminal refs and three page responses remain fully present and hash-valid. The empty staging file does not supply any rank or SHA. This note discloses the diagnostic artifact without rewriting or rehashing the finalized manifest.

The script used for that finalized attempt is preserved as `capture_script_snapshot.py`, SHA-256 `fed5d2a9cc49144a94ef703b69185ddaf8359b7a2190d0d7044ba8dfc8e888c2`, matching the manifest's recorded script hash. The current script was then tightened to inventory staging files immediately before future finalization and to archive its exact bytes when each new attempt starts.
