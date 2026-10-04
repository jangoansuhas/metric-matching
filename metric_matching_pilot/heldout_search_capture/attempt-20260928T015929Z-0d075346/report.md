# Held-out search capture report

- Attempt: `attempt-20260928T015929Z-0d075346`
- Status: **abandoned_for_persistence_revision**
- Started UTC: 2026-09-28T01:59:29.504921Z
- Updated UTC: 2026-09-28T02:02:36.810675Z
- Precommit SHA-256: `c96e4074a507789a8d24f332ee55a07b31acb4c6c0a09e66e42c438de7852fc1`
- Development snapshot SHA-256: `176d3b5c275b78f04f36411616fa6d1a055b6454659e5a422ea525c6b8ccad76`
- Captured search pages: 3/3
- Terminal HEAD records: 5/62
- HEAD HTTP attempts: 5
- Interrupted raw ref artifacts: 0

Failure or pause: Three pages and five refs captured, then atomic raw-file staging was added. Start a new full three-page attempt under one script revision; these bytes are retained for audit only.

| Query | HTTP | Items / total | Incomplete | Body SHA-256 |
| --- | ---: | ---: | --- | --- |
| `dbt metric` | 200 | 30 / 387 | False | `cfd856edb662070816109b40a1b53c557bcc7e3725e9714ebfc6cca5dded5918` |
| `dbt semantic model` | 200 | 30 / 78 | False | `b235ca4ec8d99d81afa72011ca5d3018012fc42becc36aa87e30f5dff1bb3850` |
| `rill metrics` | 200 | 5 / 5 | False | `6756f4b832292606639d792acf81ed84bdd31661523cc34af314ac76bd87edca` |

**This is an incomplete attempt, not a frozen manifest.**

The search ranks and HEAD refs were observed at separate times; this is not an atomic GitHub snapshot.
Repository source remains unopened by this capture.
