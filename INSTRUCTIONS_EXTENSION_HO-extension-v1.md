# Extension round `HO-extension-v1` — step-by-step (Reviewer B and Reviewer A)

This round labels the **remaining 43 pairs** of the same three projects you already set up.
**Nothing in the rules changes**: same guide, same three rulings (QA-1 to QA-3), same worksheet
columns, same setup. Budget: about **4 hours** (Reviewer B's previous pace) or less.
**Deadline: worksheet emailed by Tue 13 Oct 2026, end of day your time.**

Commands are for macOS / Linux. Windows equivalents are in each setup sheet in `setup/`.

---

## Step 1 — Update your clone (2 min)

```bash
cd ~/metric-review/metric-matching        # or wherever you cloned the repository
git checkout heldout-setup
git pull --ff-only
```

✅ **Check:** `ls packets/` lists `HO-extension-v1_PACKET.md` and `HO-extension-v1_WORKSHEET.md`.

If `git pull` complains about local changes, run `git stash` first, then repeat `git pull --ff-only`.
(You were asked not to edit repository files; a stash just sets aside anything accidental.)

## Step 2 — Verify the packet (1 min)

```bash
shasum -a 256 packets/HO-extension-v1_PACKET.md packets/HO-extension-v1_WORKSHEET.md
```

✅ **Check:** the two values equal the ones in the coordinator's email. If not, stop and reply.

## Step 3 — Make your private worksheet (1 min)

Copy the worksheet **outside** the repository and rename it with your role code:

```bash
cp packets/HO-extension-v1_WORKSHEET.md ~/ReviewerB_HO-extension-v1.md
```

(Reviewer A: `~/ReviewerA_HO-extension-v1.md`.) Fill in only this copy. Never edit files inside
the repository.

## Step 4 — Re-read the rulebook (15 min)

Read, in this order:

1. `REVIEWER_GUIDE.md` §3 to §6 (how to review a pair, the six labels, evidence status, query results).
2. `RULINGS_QA-1_to_QA-3.md` — rulings QA-1, QA-2, QA-3 (the same text you received by email).

Nothing else applies.

**Important: do not open the `adjudication/` folder at any point in this round.** It holds records of
the finished primary round, including other reviewers' worksheets. Reading them would compromise
your independence on these new pairs. If you opened anything there by accident, tell the
coordinator in your email; that's fine to disclose, just don't rely on it.

## Step 5 — Check your three local builds still work (5 min)

Open one terminal per project and run that project's "every time you open a new terminal" lines
from its setup sheet, then `mf list metrics`:

| Project | Activate (from its setup sheet) | ✅ `mf list metrics` says |
| --- | --- | --- |
| revenue-intelligence | `cd ~/metric-review/revenue-intelligence/dbt && source ../.venv/bin/activate && export DBT_PROFILES_DIR=~/metric-review/profiles-revenue-intelligence` | `We've found 10 metrics.` |
| supply-chain-analytics-dbt | `cd ~/metric-review/supply-chain-analytics-dbt && source .venv/bin/activate` | `We've found 5 metrics.` |
| homelab-data-platform | `cd ~/metric-review/homelab-data-platform/dbt_project && source ../.venv/bin/activate` | `We've found 5 metrics.` |

If a check fails, reply to the coordinator with the exact command and the last ~20 lines of output.
Don't rebuild or change anything on your own.

## Step 6 — Label the 43 pairs (most of the time)

1. In your worksheet header, write your **Reviewer code**, **date and time zone**, and the **Start time**
   when you actually begin labelling (not earlier).
2. Open `packets/HO-extension-v1_PACKET.md`. Work **top to bottom, in the listed order**; don't skip
   ahead. 37 pairs are from revenue-intelligence, then 2 from supply-chain-analytics-dbt, then 4 from
   homelab-data-platform.
3. For each pair, follow `REVIEWER_GUIDE.md` §3 exactly, at the pair's **Compare at** scope:
   - one label from the six, or blank;
   - evidence status `sufficient` or `needs_review`;
   - the exact files and line numbers you relied on;
   - any query you ran, with the exact command and the key result;
   - the missing fact, if you left the label blank;
   - minutes for the pair.
4. Fill the **End time** and **Active minutes** in the header when you finish.

## Step 7 — Send it (2 min)

Email the file `ReviewerB_HO-extension-v1.md` (or `ReviewerA_…`) as an attachment to the coordinator,
subject **`HO-extension-v1 worksheet — Reviewer B`**. You'll get a confirmation with its SHA-256 once it
is locked. After sending, don't change the file; corrections go in a separate, dated note.

---

## The five rules (unchanged)

1. **No AI tools at any point** (no ChatGPT, Claude, Copilot, Gemini, Cursor, AI search answers).
2. **Work alone.** Don't discuss any pair with anyone until your worksheet is sent. Rule questions go
   to the coordinator in writing; the answer goes to every reviewer.
3. **Don't commit or push** to the repository.
4. **Use only the pinned sources:** the files at the packet's commits, your local builds, `docs.getdbt.com`.
5. **Don't change a worksheet after sending it.**
