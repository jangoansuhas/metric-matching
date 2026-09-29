# Metric review study: reviewer materials

Welcome, and thank you for helping. This repository has everything you need, and you don't need any background on the study.

## Who you are

You'll have been told your role by the coordinator.

| Role | Code to use in every file | Read these, in this order |
| --- | --- | --- |
| Independent reviewer | **Reviewer B** | 1. this page → 2. [SETUP.md](SETUP.md) → 3. [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) → 4. [practice/CAL_PRACTICE_PACKET.md](practice/CAL_PRACTICE_PACKET.md) |
| Adjudicator | **Adjudicator C** | 1. this page → 2. [SETUP.md](SETUP.md) → 3. [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) (the rules the reviewers follow) → 4. [ADJUDICATOR_GUIDE.md](ADJUDICATOR_GUIDE.md) |

**Never write your real name** in any file you send. Use your code.

## What the study is, in one paragraph

Analytics projects built with **dbt** declare named business numbers called *metrics*, such as `revenue` or `order_count`, in YAML files. Two metrics can sound alike but compute different numbers, or sound different but compute the same one. You'll look at **pairs** of metrics from public open-source dbt projects. For each pair you'll decide how the two relate, using the project's files and, if you want, by running the project on your own computer. There are no trick questions. We want your honest professional judgment, including "I can't tell".

## The five rules that matter most

1. **No AI tools, at any point.** That means no ChatGPT, Claude, Copilot, Gemini, Cursor, or AI answer boxes in search engines. If one pops up, don't read it.
2. **Work alone.** Don't discuss any specific pair with anyone until you've sent in your finished worksheet. Questions about the *rules* are fine: send them in writing to the coordinator, and the answer will go to everyone.
3. **Don't commit or push anything to this repository.** Send your worksheet to the coordinator by **email** (see the guide). This repository is read-only for you.
4. **Use only the pinned sources:**
   - the project files at the exact commit given in the packet;
   - the local database you build by following [SETUP.md](SETUP.md);
   - the official dbt documentation at [docs.getdbt.com](https://docs.getdbt.com).
5. **Don't change a worksheet after sending it.** If you spot a mistake, send a separate, dated note.

## What's in this repository

| Path | What it is |
| --- | --- |
| `SETUP.md` | Step-by-step install: Git, Python, dbt, cloning and building the practice project, and running queries |
| `REVIEWER_GUIDE.md` | How to review a pair, the six relationship labels, evidence status, how to use query results |
| `ADJUDICATOR_GUIDE.md` | For the adjudicator only: how to resolve disagreements |
| `setup/` | One setup sheet per held-out project, plus two helper scripts in `setup/tools/` for one of them |
| `practice/` | The practice packet (3 pairs). Held-out packets will be added later as new folders. |
| `templates/` | Blank worksheet and decision-record templates to copy |

## Getting a copy of this repository

This is a **private** repository, and you've been invited to it.

- **Easiest option, no Git needed yet:** open the repository page on GitHub, click the green **Code** button, then **Download ZIP**, and unzip it anywhere. You can read every file in any text editor or in the browser.
- **With Git (optional):** after accepting the invitation, you can `git clone` it. This needs GitHub login on your computer, for example [GitHub Desktop](https://desktop.github.com). Downloading the ZIP is enough.

You **will** need Git for the public study projects themselves. [SETUP.md](SETUP.md) walks you through it.

## Help

If a step fails or something is unclear, stop and email the coordinator with:
- the step number;
- the exact command you ran;
- the full error text, copied as text rather than as a screenshot if you can.

Don't try to work around it yourself, and don't ask an AI tool.
