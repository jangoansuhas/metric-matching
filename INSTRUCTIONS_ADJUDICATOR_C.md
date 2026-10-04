# Instructions for Adjudicator C — start here

Hi — welcome, and thank you. Your job: two reviewers, A and B, will each independently label the same pairs of dbt metrics. You produce the **final label** for each pair, focussing on the ones they disagree on. Your decisions become the study's reference answers. You need no background beyond being able to read dbt YAML and SQL; everything is explained in the repository below.

**Your role code is "Adjudicator C".** Use it in every file you send us. Please never write your real name in any file you send.

## Before you start — eligibility (confirm to the coordinator by email)

1. You are not Reviewer A or Reviewer B, and you haven't helped write the paper or build its method.
2. You have not seen any automated or AI output about these pairs — no tool predictions, no chatbot analyses.
3. You can read dbt YAML and SQL.

If any of these isn't true, tell the coordinator and stop.

## What you need

- A computer with internet, **Git**, and **Python 3.12** (SETUP.md pins it exactly).
- Total effort: about **2–4 hours** spread over the steps below. Most pairs will be agreements you can accept quickly; the disagreements are where your time goes.

## Phase 1 — Read and set up (can be done now; ~1–2 hours)

1. Clone the repository, branch `heldout-setup` (the same branch the reviewers use):
   `git clone -b heldout-setup https://github.com/jangoansuhas/metric-matching.git`
2. Read `README.md` (the study in one paragraph and the five rules).
3. Follow `SETUP.md` top to bottom: pinned tool versions (`dbt-core 1.12.5`, `dbt-duckdb 1.11.0`, `dbt-metricflow 0.15.0`) and the practice-project build, then the three per-project sheets in `setup/`. If anything fails, email the coordinator the exact command and the last ~20 lines of output — don't improvise fixes.
4. Read `REVIEWER_GUIDE.md` once — you apply exactly the same definitions and rules the reviewers used. Then read `ADJUDICATOR_GUIDE.md` — your full procedure.

## Phase 2 — Wait for the adjudication materials

The reviewers are still labelling. When both worksheets are locked, the coordinator emails you:

- the packet ID and its SHA-256;
- the two locked worksheets, under neutral codes ("Reviewer 1" and "Reviewer 2") with their SHA-256 values — you will **not** be told which reviewer is which; one of them is the paper's first author, and that must not influence you in either direction;
- the written Q&A log of rulings.

Verify each file's SHA-256 (`shasum -a 256 <file>` on macOS/Linux, `Get-FileHash <file>` on Windows) against the values in the email. If anything doesn't match, stop and report it.

## Phase 3 — Adjudicate (~1–2 hours; deadline: email your record by October 12)

Work through `ADJUDICATOR_GUIDE.md` §4's case table, pair by pair:

- **Full agreement:** accept it; skim the cited lines. Override only for a clear factual error, and explain.
- **Same label, different evidence status:** decide whether a decisive fact really is missing.
- **Different labels:** review the pair yourself at the packet's stated scope, read both reasonings, and pick A's label, B's label, or a third label the evidence clearly supports. Explain the decisive evidence.
- **Blank labels:** decide whether the evidence supports a label; if it doesn't, leave it blank with `needs_review`.
- **Truly can't decide:** mark `unresolved` and explain. Honest `unresolved` is a fine outcome.
- For each disagreement, also give a **root cause** (`rubric_wording`, `missed_evidence`, `scope`, `value_interpretation`, `judgment`, `other`).

Then: copy `templates/ADJUDICATOR_DECISION_RECORD.md` outside the repository, fill it in, and **email it to the coordinator**. Don't commit anything to the repository, and don't change the record after sending — corrections go in a separate, dated note.

## Ground rules (from the repository guides — they apply throughout)

1. **No AI tools at any point.**
2. **Same sources as the reviewers:** the pinned files, your own Phase-1 build, `docs.getdbt.com`, the two locked worksheets, the Q&A log.
3. **Same rulebook:** `REVIEWER_GUIDE` §4–§6 plus the written rulings. Don't invent new categories.
4. **Treat both reviewers equally** — judge only the evidence.
5. **Questions go to both reviewers in writing**, never a live discussion with one. Keep the replies.
6. **Don't commit to the repository.** Everything goes by email.

Questions at any point: reply to the email that pointed you here. Thanks — your independent judgment is what makes the study's answers credible.
