Hi — welcome, and thank you for helping with this study. You need **no background**: everything is explained in the repository you'll clone below. This message just tells you the exact order of steps, so nothing gets missed. There are three phases. **Phase 1 needs no installation and comes first.**

**Your role code is "Reviewer B".** Use it in every file you send us. Please never write your real name in any file you send.

## What you need

- A computer with internet, **Git**, and **Python 3.12** (Phases 2–3 only; Phase 1 needs neither beyond a browser). SETUP.md pins the Python version exactly.
- A plain-text or Markdown editor.
- Email, for sending worksheets back.
- Total effort: Phase 1 about **45 minutes**; Phase 2 about **1–2 hours**; Phase 3 will arrive later and will state its own time budget.

## Phase 1 — Practice round (do this FIRST; ~45 min; no install)

1. Clone the repository, branch `heldout-setup`:
   `git clone -b heldout-setup https://github.com/jangoansuhas/metric-matching.git`
   *(If you don't use Git yet: every file is also readable in your browser at https://github.com/jangoansuhas/metric-matching/tree/heldout-setup — but a clone is better for Phase 2.)*
2. Read `README.md` (5 minutes). It explains what the study is and the five rules that matter most.
3. Read `practice/README.md`, then do exactly what it says with `practice/CAL_ORIGINAL_PACKET.md`. The key points, all also stated there:
   - **Compare the single overall number** for each metric: no grouping, no date filter.
   - **Work from the source files only.** You do not need to build the project or run any query for this round. The packet's pinned GitHub links are all you need; its `git show` command is an optional alternative if you already use Git. If you do run a query anyway, write down exactly what you ran.
   - **Use the worksheet table inside the packet itself** (not `templates/REVIEWER_WORKSHEET.md`). Make a private copy of the packet, fill in its "Independent reviewer worksheet" section, and email it to the coordinator (just reply to the email that pointed you here).
   - Skip the packet's "Coordinator timing and lock log" section — that's for us.
4. **Do not open `SETUP.md` before you have emailed your practice worksheet.** Its example queries show values for some practice metrics, and we need your practice judgments to be source-only.
5. Email the worksheet. You'll get a short confirmation that it's locked. That ends Phase 1.

**Please do Phase 1 within about two days of receiving this.**

## Phase 2 — Setup (after we confirm your practice worksheet is locked)

1. Follow `SETUP.md` top to bottom: it installs pinned tool versions (`dbt-core 1.12.5`, `dbt-duckdb 1.11.0`, `dbt-metricflow 0.15.0`) in a virtual environment and builds the small practice project.
2. Then follow the three per-project sheets in `setup/`, one for each study project. Each is standalone and ends with a checklist of what "done" looks like.
   - One project uses a **fixed data snapshot** in `setup/data/`: the sheet has you verify its checksums. Don't run that project's data generators.
   - One project targets Snowflake: its sheet uses two helper scripts in `setup/tools/`. These are the only allowed changes anywhere; what a metric *means* is always read from the pinned, unchanged files.
3. If anything fails, email the coordinator (just reply to the email that pointed you here) with the exact command and the last ~20 lines of output. Don't improvise fixes and don't edit project files.
4. Note: the sheets' Linux/macOS commands are tested; Windows PowerShell equivalents are given but untested — if you're on Windows and something differs, tell us and we'll help.

## Phase 3 — Labelling round (packets arrive later)

- The real packets are **not in the repository yet**; we'll add them as new folders and email you when they're ready. Until then, there's nothing to do after Phase 2.
- When a packet arrives: read `REVIEWER_GUIDE.md` once (it's short), then work pair by pair.
- Each packet may be accompanied by dated, hashed written clarifications (rulings and rubric amendments). Those are part of the rulebook: read them before labelling. For each pair the packet gives the two metric declarations, links to the exact lines, and one **"Compare at"** scope. You record: the relationship label (one of six, or blank), your evidence status (`sufficient` or `needs_review`), the exact files/lines/queries you relied on, and roughly how many minutes it took.
- You may run read-only queries against your Phase-2 build to check your reading — the guide lists the allowed commands. Equal values never prove interchangeability on their own; the guide explains how to use query results.
- "I can't tell" is a valid, useful answer: leave the label blank, mark `needs_review`, and name the missing fact.
- When finished, copy `templates/REVIEWER_WORKSHEET.md`, fill it in, and email it. **Target: all your worksheets locked by October 9.**

## The five rules (from the repository README — they apply throughout)

1. **No AI tools at any point** — no ChatGPT, Claude, Copilot, Gemini, Cursor, or AI answer boxes in search results.
2. **Work alone.** No discussing any specific pair with anyone until your worksheet is sent. Questions about the *rules* are welcome — send them in writing, and the answer goes to every reviewer.
3. **Don't commit or push to the repository.** It's read-only for you; worksheets go by email.
4. **Use only the pinned sources:** the project files at the exact commit in the packet, your Phase-2 local build, and the official dbt docs at docs.getdbt.com.
5. **Don't change a worksheet after sending it.** Spot a mistake? Send a separate, dated note.

Questions at any point: the coordinator (just reply to the email that pointed you here). Thanks again — your time is the scarce resource here, and the materials are built so that none of it is wasted.
