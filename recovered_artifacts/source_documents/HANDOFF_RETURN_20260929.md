# Handoff return: declared-metric frame screen and reviewer materials (2026-09-29)

Sender: Claude (AI assistant), working in the author's dev container.
Status: technical evidence for you to verify. It isn't a human judgment.

## 1. Attachments

| File | SHA-256 | Contents |
| --- | --- | --- |
| `semantic_metric_frame_screen_20260929.zip` (156 files) | `2c5be6c5a452f7ac62d0ff2388d0cca6149339abb5e51d466b175f0f6d01517c` | Everything from Stage 1 and Stage 2. Start with `report.md` and `screen_ledger.json`. The ZIP also holds the raw GitHub responses, the queue, the screening scripts, the adapter runs and `SHA256SUMS`. |
| `reviewer_materials_406e4cd.zip` | `a85db6e5916cee6e449e6a246db02abde1f4fd00f0559c05512ce1dfbbc6df39` | The reviewer repository, a private GitHub repo at commit `406e4cd`: README, SETUP, REVIEWER_GUIDE, ADJUDICATOR_GUIDE, the CAL practice packet and the templates. |

## 2. What was done under the handoff

- **Precommit.** Its SHA-256 was checked before any request: `911ccb67…1623`.
- **Stage 1.** 3 queries returned 260 items: 238 unique, 85 passed the filter, and 20 were pinned.
- **Stage 2.** Screening stopped at rank 14, where the third eligible project appeared. Selected:
  - Rank 7: `orbiane/homelab-data-platform@5e8e25d7`, 5 metrics, nested project.
  - Rank 9: `rohitndev/AI-Augmented-Executive--Revenue-Intelligence-Platform@36ea21e4`, 10 metrics, nested project, Snowflake.
  - Rank 14: `KushPatel29/supply-chain-analytics-dbt@04ba7643`, 5 metrics, root project.
- **Adapter.** The frozen adapter (`7b90ef37…`, unchanged) produced SQL for rank 14 only: 5 of 5 metrics, ungrouped, all from one semantic model. Ranks 7 and 9 stop before parse, because the adapter requires `dbt_project.yml` at the repository root.
- **Hard stops respected.** No pair comparison, pair draw, value execution, method prediction, worksheet, six-class label or F1 was produced. The 62-row queue was not touched.

## 3. Please verify

These are also listed in report §4.

1. **Ranks 15–16** were auto-counted after the stopping point. Both have 0 declarations, so the selection doesn't change.
2. **The first counter overcounted.** It counted YAML outside dbt projects. The fixed counter reran every rank, and no verdict was based on the first counts.
3. **The first adapter run on rank 14** failed because I passed a relative path, an operator error. That run is kept as ATTEMPT1.
4. **The excluded-family list** was taken from outline §5, because I did not have `semantic_metric_cohort_reset_20260929.md`. Check it against that reset document.
5. **Judgment calls:**
   - Ranks 8 and 12 were excluded as test-fixture-only tools.
   - Rank 9 was treated as a portfolio project, not a tutorial.
6. **Thin corpus.** Ranks 7 and 14 meet the 5-metric threshold exactly. There are at most 65 within-project pairs, and all 5 metrics in rank 14 come from one semantic model.

## 4. Decisions needed from the author (not taken)

1. **Adapter v2.** Should a separately versioned adapter be made that accepts a nested `--project-subdir`? Without it, 2 of the 3 held-out projects can't be run by the method.
2. **Pair draw.** This covers the pair-sampling rule, the number of pairs per project, and the seed. It is not started.

## 5. Protocol change the outline must reflect

**The author decided that human reviewers may build the project and query metric values.** Under this rule:
- Reviewers may run `dbt build`, `mf query`, `mf list` and `--explain`, and use read-only `dbt show`. They may not edit files.
- REVIEWER_GUIDE §6 sets out how they interpret the values.

This differs from the earlier read-only rubric. The following need updating:
- **Outline §5 and the disclosure** must state that reviewers saw computed values.
- **The precommit** bans value execution before labelling. Please draft a dated amendment: the ban still applies to the method and baselines, and human reviewers are exempt.
- **Human-labelling setup.**
  - Reviewer A is the first author, and the paper discloses this.
  - Reviewer B is an independent practitioner who works offline with no AI.
  - Adjudicator C is someone else and has not been recruited yet.
  - Worksheets are locked with SHA-256 before any method runs.
  - The three contested rulings stay held back until B's CAL worksheet is locked:
    - tax vs scope;
    - whether sharing a table and grain is enough for `related`;
    - `sufficient` vs `needs_review` when an evidence gap probably doesn't change the label.
- **The reviewer guide quotes the v48 label definitions exactly.** If the outline changes them, the guide needs a new version, and every reviewer gets it at the same time.

## 6. Check needed: CAL packet

`practice/CAL_PRACTICE_PACKET.md` (SHA-256 `55cdedcb…3b5f`) was rebuilt from memory because I didn't have your original CAL packet. It uses Jaffle `7be2c58`, compares every pair at the overall total and by month, and contains these pairs:

| Pair | Metric 1 | Metric 2 |
| --- | --- | --- |
| CAL-01 | `revenue`, `order_items.yml` L90–95 | `food_revenue`, `order_items.yml` L108–113 |
| CAL-02 | `lifetime_spend_pretax`, `customers.yml` L73–78 | `order_total`, `orders.yml` L124–129 |
| CAL-03 | `order_total`, `orders.yml` L124–129 | `order_cost`, `order_items.yml` L96–101 |

Please confirm it matches the original. **Don't send any CAL-03 analysis to the author for relay to Reviewer B**: B's answer is meant to count as the independent third answer.

## 7. Completion (the author's rubric)

- **Score:** about 37% done, 63% left, up from 36% because the reviewer materials are now published.
- **Critical path:** adapter v2, the pair draw, recruiting the adjudicator, and B's CAL worksheet.
