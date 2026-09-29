# Adjudicator guide: resolving reviewer disagreements

Thank you for agreeing to adjudicate. Two reviewers, **A** and **B**, have each labelled the same metric pairs independently. Your job is to produce the **final label** for each pair, concentrating on the pairs where they disagree.

In every file you are **Adjudicator C**. Don't write your real name anywhere.

Before starting, read the [README](README.md), finish [SETUP.md](SETUP.md), and read the [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md). You apply the same definitions the reviewers used.

---

## 1. Eligibility (confirm before starting)

You must:

- not be Reviewer A or Reviewer B, and not have helped write the paper or build its method;
- not have seen any automated or AI output for these pairs, including method results, tools' predictions and chatbot analyses;
- be able to read dbt YAML and SQL.

If any of these isn't true, tell the coordinator and stop.

## 2. Ground rules

1. **No AI tools at any point.**
2. **Use the same sources and commands as the reviewers:**
   - the pinned files;
   - your own local build from SETUP.md, with the same allowed commands as REVIEWER_GUIDE §2;
   - `docs.getdbt.com`;
   - the two locked worksheets;
   - the written Q&A log of rulings.
3. **Use the same rulebook.** Apply REVIEWER_GUIDE §4–§6, plus any written rulings in the Q&A log. Don't invent new categories.
4. **Treat both reviewers equally.** Reviewer A is the paper's first author. That must give A's answer **no extra weight**. Judge only the evidence.
5. **Questions go to both reviewers.** If you need a reviewer to clarify something, send the same written question to both A and B, and keep their written replies. Don't hold a live discussion with only one of them.
6. **Don't commit to this repository.** Send your decision record by email.

## 3. What you receive (from the coordinator, by email)

- The packet ID and its SHA-256.
- A's and B's **locked** worksheets, with their SHA-256 values.
- The Q&A log.

Check that the files' SHA-256 values match the ones the coordinator sent. If they don't, stop and report it.

To compute a SHA-256:

```bash
# macOS / Linux
shasum -a 256 <file>
```
```powershell
# Windows
Get-FileHash <file> -Algorithm SHA256
```

## 4. Procedure for each pair

| Case | What you do |
| --- | --- |
| **Full agreement** (same label **and** same evidence status) | Accept it. Skim the cited lines. Override only for a clear factual error, e.g. a cited line doesn't say what's claimed, and explain the override. |
| **Same label, different evidence status** | Read the "missing evidence" notes. Decide whether a decisive fact really is missing (`needs_review`) or not (`sufficient`). |
| **Different labels** | Review the pair yourself (REVIEWER_GUIDE §3, at the packet's stated scope), then read both reviewers' reasoning and queries. Pick A's label, B's label, or a third label if the evidence clearly supports it. Explain the decisive evidence. |
| **One or both left the label blank** | Decide whether the evidence supports a label. If it doesn't, leave it blank with `needs_review`. |
| **Truly can't decide** | Mark it **`unresolved`** and explain why. Unresolved pairs are reported separately in the paper. That's an honest outcome, not a failure. |

For each disagreement, also give a **root cause**:

| Root cause | Meaning |
| --- | --- |
| `rubric_wording` | The definitions were ambiguous. |
| `missed_evidence` | One reviewer missed a relevant line or query. |
| `scope` | They compared at different scopes. |
| `value_interpretation` | They read the same query results differently. |
| `judgment` | Both readings are defensible. |
| `other` | Anything else; say what. |

## 5. Your decision record

Copy [templates/ADJUDICATOR_DECISION_RECORD.md](templates/ADJUDICATOR_DECISION_RECORD.md) to a file outside this repository and fill it in.

## 6. When you're done

- Email the decision record to the coordinator and keep a copy. Don't change it after sending. Send any correction as a separate, dated note.
- Your final labels are the study's reference labels. The coordinator will not edit them.

## 7. Practice pairs (if asked)

You may be asked to settle a practice pair (`CAL-…`) with the same procedure. That result is a **calibration outcome** only. It is not scored in the paper.
