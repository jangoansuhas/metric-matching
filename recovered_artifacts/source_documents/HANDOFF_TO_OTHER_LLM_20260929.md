# Handoff: declared-metric screen, reviewer materials, adapter v2 and pair draw (2026-09-29)

**From:** Claude, the AI assistant working in the author's dev container.
**To:** the verifying LLM, which also maintains the outline. This note replaces `HANDOFF_RETURN_20260929.md`.
**Status:** everything here is technical evidence for you to verify. None of it is a human judgment, and it contains no relationship labels, method predictions or metric values.

---

## 1. Artifacts in this folder

| File | SHA-256 | Contents |
| --- | --- | --- |
| `semantic_metric_frame_precommit_20260929.json` | `911ccb677943d4fe6e561e4d4d24d437842e25b3fbb265af89e6d98dde5b1623` | Your precommit, checked unchanged |
| `semantic_metric_frame_screen_20260929.zip` (156 files) | `2c5be6c5a452f7ac62d0ff2388d0cca6149339abb5e51d466b175f0f6d01517c` | Stage 1 and 2 raw responses, queue, ledger, scripts, `report.md`, adapter v1 runs |
| `adapter_v2_pairdraw_20260929.zip` (189 files) | `65a38470bac9a9b70f64f88bf386fe72abf7b1b0a6cec8f82f4f8ce531b492d9` | Adapter v2, the v1→v2 diff, regression runs, held-out runs, pair-draw precommit, draw script, pair list |
| `reviewer_materials_406e4cd.zip` | `a85db6e5916cee6e449e6a246db02abde1f4fd00f0559c05512ce1dfbbc6df39` | The reviewer repository, a private GitHub repo at commit `406e4cd` |
| `labeling_protocol_20260929.zip` | `7d06bf84fb2382b1dbd5e1776f64351d1745a98fbc70c283f44656ad62f0eb7e` | Coordinator guide 01, plus drafts 02 and 03, which the reviewer repo supersedes |

Each ZIP includes its own `SHA256SUMS`. Start with `report.md` in the screen ZIP and `README.md` in the adapter ZIP.

---

## 2. What was done

### 2.1 Declared-metric frame screen (your handoff, Stages 1–2)

- **Stage 1.** 3 queries gave 260 items. After removing duplicates, 238 were unique; 85 passed the filter; the first 20 were pinned. For query 2, 101 results lay outside page 1, as the precommit allows.
- **Stage 2.** Screening ran in rank order and stopped at rank 14, where the third eligible project appeared. Selected:

  | Rank | Repository @ commit | Dbt project location | Metrics | Warehouse |
  | --- | --- | --- | --- | --- |
  | 7 | `orbiane/homelab-data-platform@5e8e25d7f79cb407402d7dd107a7694311bb9e9b` | nested, in `dbt_project/` | 5 | synthetic |
  | 9 | `rohitndev/AI-Augmented-Executive--Revenue-Intelligence-Platform@36ea21e4cf795bfe2ea437120109048a601d3daa` | nested, in `dbt/` | 10 | synthetic; targets Snowflake |
  | 14 | `KushPatel29/supply-chain-analytics-dbt@04ba76437cf0ba8b0b90c1709b6559e3fa7ba2cb` | repository root | 5 | the repo's own seed CSVs |

- All three are MIT-licensed. None shows Jaffle, Sidemantic, GTM or Rill ancestry.
- The 62-row queue and the frozen adapter v1 (`7b90ef37dfb1cce9c0a15f211ef89fb56106a0f1eb8817ed0ae405ad05ce09fe`) were not changed.

### 2.2 Adapter v2 (author delegated the decision)

- **What changed.** `run_adapter_v2.py` is v1 plus two things: an optional `--project-subdir`, and `--repo`/`--out` converted to absolute paths. `v1_to_v2.diff` is the complete diff.
- **Regression.** v2 was run without a subdirectory:
  - **Jaffle `7be2c58`:** the 19 SQL files are byte-identical to v1. `provenance.json` differs only in a log path and timestamp inside one error message.
  - **Rank 14:** `provenance.json` and the SQL are identical to v1.
- **Held-out coverage:** all 20 metrics compile ungrouped.

  | Rank | Metrics compiled | Semantic models | Metric types |
  | --- | --- | --- | --- |
  | 7 | 5/5 | 3 | simple, ratio |
  | 9 | 10/10 | 2 | simple, ratio, derived |
  | 14 | 5/5 | 1 (`orders`) | — |

- **No values were computed.** The DuckDB inventory after explain is `[]`.

### 2.3 Pair draw (author delegated the decision)

1. `pair_draw_precommit_20260929.json` (SHA-256 `2f5215fa129ceec35b04355d0ca956f61d4398cbce612e0b2655b10de59777d3`) was written, hashed and made read-only **before** the list was generated.
2. The rule it fixes:
   - Pairs are unordered, and both metrics come from the same project.
   - Pairs are ordered by `sha256('saner27-pairdraw-v1|<repo>@<commit>|<a>|<b>')`.
   - They are coded P-01 to P-65 and split into batches of 13.
   - The target is all 65 pairs. The minimum is batches 1–2, and a partial run is reported as the completed hash-randomised prefix.
   - Each pair is compared at two scopes: ungrouped, and `metric_time__month`.
   - Results are reported per project, macro-averaged, and pooled.
3. Result: `pair_list_20260929.csv` (SHA-256 `ddda90de…d1fb`). Rank 9 contributes 45 pairs, and ranks 7 and 14 contribute 10 each. Every batch contains pairs from at least two projects.

### 2.4 Human-labelling materials

- **Reviewer repository:** private, at `406e4cd`. Its files:
  - `README`;
  - `SETUP`: 10 steps for Jaffle at `7be2c58`, tested on Linux; the Windows steps are untested;
  - `REVIEWER_GUIDE`, which quotes the v48 label definitions exactly;
  - `ADJUDICATOR_GUIDE`;
  - `practice/CAL_PRACTICE_PACKET.md`;
  - the two templates.
- **Roles:**
  - **Reviewer A** is the first author, and the paper discloses this.
  - **Reviewer B** is an independent practitioner who works offline, uses no AI, and returns work by email.
  - **Adjudicator C** will be someone who is neither A nor B. They have **not yet been recruited**.
- **Locking:** each worksheet is locked with a SHA-256 before any method runs on its pairs. A sensitivity check rescores the results with B's labels alone as gold.

---

## 3. Protocol change the outline must reflect

**The author decided that human reviewers may build the project and query metric values.**
- **Allowed:** `dbt build`, `mf query`, `mf list`, `--explain`, and read-only `dbt show`.
- **Not allowed:** editing files.
- REVIEWER_GUIDE §6 gives the rules for interpreting values.

Please:
1. **Update outline §5 and the disclosure.** Reviewers saw computed values, and the paper must say so.
2. **Draft a dated amendment to the frame precommit.** Its ban on value execution before labelling still covers the method and baselines. It no longer covers human reviewers. It also doesn't cover the author testing a reviewer setup sheet, if that test is limited to `dbt build` plus `mf list metrics`. Please rule on that last point.
3. **Add adapter v2 to the method section.** Name it as a separately versioned tool, include the regression evidence, and make clear that v1 stays frozen.
4. **Add the pair-draw rule to the evaluation design**, including the per-project/macro-averaged reporting.

---

## 4. Please verify

1. The judgment calls in the screen:
   - ranks 8 and 12 excluded as test-fixture-only tools;
   - rank 9 treated as a portfolio project, not a tutorial.
2. The list of excluded families. I took it from outline §5 because I didn't have `semantic_metric_cohort_reset_20260929.md`.
3. The deviations disclosed in `report.md` §4:
   - ranks 15–16 were auto-counted after the stop point;
   - the counter overcounted before it was fixed;
   - the first adapter run failed on a relative path.
4. The **CAL practice packet** (SHA-256 `55cdedcb…3b5f`). I rebuilt it from memory, not from your original. Please confirm it matches:

   | Pair | Metric 1 | Metric 2 |
   | --- | --- | --- |
   | CAL-01 | `revenue`, `order_items.yml` L90–95 | `food_revenue`, `order_items.yml` L108–113 |
   | CAL-02 | `lifetime_spend_pretax`, `customers.yml` L73–78 | `order_total`, `orders.yml` L124–129 |
   | CAL-03 | `order_total`, `orders.yml` L124–129 | `order_cost`, `order_items.yml` L96–101 |

   All three use Jaffle at `7be2c58` and are compared ungrouped and by month.
5. That the adapter v2 diff introduces no behaviour change beyond the two stated changes.
6. That the pair list regenerates exactly with `draw_pairs.py`. The inputs are the three `semantic_manifest.json` files: two in `runs/` and one in `regression/regress_rank14/`.

---

## 5. Hard constraints for you

- **P-01 to P-65:** don't produce relationship labels, similarity judgments, method predictions or baseline outputs until the author tells you both A's and B's worksheets for that batch are locked.
- **CAL-03:** send the author no analysis that could reach Reviewer B. B's answer counts as the independent third answer.
- **Rulings:** don't release the three held-back rulings until B's CAL worksheet is locked. They are:
  - tax vs scope;
  - whether sharing a table and grain is enough for `related`;
  - `sufficient` vs `needs_review` when an evidence gap probably doesn't change the label.
- **Worksheets:** you shouldn't receive or read reviewer worksheets before they are locked.

---

## 6. Known risks and open items

- **Thin corpus.** There are 65 pairs, and 69% come from rank 9. Ranks 7 and 14 meet the five-metric threshold exactly. All 5 metrics in rank 14 come from one semantic model, so its pairs may be less varied.
- **Rank 9 targets Snowflake.** A local DuckDB build for reviewers is untested. If it fails, reviewers can use the pinned YAML/SQL and `--explain` only for that project, which is different from the other projects. Please propose how the paper handles that.
- **Setup sheets for each project** (ranks 7, 9 and 14) are not written yet. Reviewers need them before they get packets.
- **Adjudicator C** is not recruited. **Reviewer B's CAL worksheet** is not yet received.
- **Coordinator guide 01** has a note saying the reviewer repo supersedes guides 02 and 03, and that values are allowed. Its body still describes the older read-only rules.

---

## 7. Completion (the author's fixed rubric)

| # | Workstream | Weight | Progress |
| --- | --- | --- | --- |
| 1 | Scope/claim | 10 | 75% |
| 2 | Dev infrastructure | 10 | 90% |
| 3 | Held-out corpus | 15 | 65% |
| 4 | Method/baselines | 15 | 50% |
| 5 | Human labels | 20 | 18% |
| 6 | Evaluation | 10 | 0% |
| 7 | Prose | 15 | 25% |
| 8 | Submission package | 5 | 20% |

**Total: about 42% done, 58% left.** The critical path, in order:
1. setup sheets for each project;
2. B's CAL worksheet;
3. recruiting C;
4. labelling batch 1;
5. running the method and baselines on locked batches;
6. evaluation.
