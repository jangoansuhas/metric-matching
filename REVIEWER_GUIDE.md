# Reviewer guide: labelling metric pairs

Please read all of this once before starting. You should already have finished [SETUP.md](SETUP.md).

In every file you are **Reviewer B**. Don't write your real name anywhere.

---

## 1. What you decide for each pair

For each **pair** of metrics in a packet, you record three things:

1. **Relationship label:** how the two metrics relate at the stated comparison scope (§4).
2. **Evidence status:** whether what you could see is enough to be sure (§5).
3. **Where the evidence is:**
   - the exact files and line numbers you relied on;
   - any queries you ran and what they showed.

## 2. Ground rules

1. **No AI tools at any point.** That means no ChatGPT, Claude, Copilot, Gemini, Cursor AI, or AI answer boxes in search results.
2. **Work alone.** Don't discuss specific pairs with anyone, including the coordinator, until your worksheet has been sent. Send any rule questions in writing. The answers go to everyone.
3. **Use only these sources:**
   - the pinned project files, via the packet's links or your local clone at the pinned commit;
   - the local database you built in SETUP.md;
   - the official dbt documentation at `docs.getdbt.com`.
4. **Allowed commands:** the commands in SETUP.md, plus any `mf query`, `mf list`, `mf query --explain`, or read-only `dbt show --inline "select …"` against your local build.
   - **Don't edit any project file.** Don't load other data, and don't change the commit.
5. **Don't commit to this repository.** Send your worksheet by email (§8).
6. **Don't change a worksheet after sending it.** Send corrections as a separate, dated note.

## 3. How to review one pair

1. **Find both declarations.** Use the packet's links, or the same file and lines in your clone.
2. **Trace each metric back to what it's built from:**
   - **Measure:** the aggregation (`agg`) and its expression (`expr`), found under `semantic_models:` → `measures:`.
   - **Semantic model:** which model or table it reads, and its grain (one row per order, per customer, per item…).
   - **Filters:** any `filter:` on the metric or measure.
   - **Time behaviour:** cumulative windows, offsets such as "previous month", and which time dimension is used.
   - **The SQL model:** open the model's SQL if you need to see how a column is computed.
3. **Check the stated comparison scope.** Each pair in the packet has a **Compare at** line, such as "overall total and by month". Judge the pair at exactly that scope. Don't hunt for other groupings that would make the answer easier.
4. **Optionally, run queries** to check your reading (§6). Record what you ran.
5. **Choose a label (§4) and an evidence status (§5).** Write down the decisive files, lines and queries.
6. **Record roughly how many minutes the pair took.**

## 4. Relationship labels (pick exactly one, or leave blank)

The wording below is the study's fixed definition. Use it as written.

| Label | Definition | Generic illustration (not from any packet) |
| --- | --- | --- |
| `direct_equivalent` | Same defined output under aligned grain, inputs, time, units, and population, without a grain-changing transform. | `total_sales` and `gross_sales`, both `SUM(amount)` over the same table, same filters, same time dimension |
| `cross_grain_equivalent` | A specified deterministic, valid rollup maps one grain to the other under aligned inputs, time, units, and population, including missing-group and NULL handling. | Account-level `lifetime_bookings`, which sums exactly to invoice-level `bookings` |
| `temporal_or_scope_variant` | Documented shared measure concept with a changed time rule, filter, state, or population. | `sales` vs `sales_eu` (EU rows only); `sales` vs `sales_ytd` |
| `conflicting_definition` | The same or materially similar published name is used for incompatible documented meanings. | Two metrics both called "net revenue", one after refunds and one before |
| `related` | Documented semantic connection, but the defined outputs do not meet a more specific label. | `sales` and `margin = sales - cogs` |
| `non_match` | No supported semantic relationship for the compared outputs. | `shipping_cost` vs `active_users` |
| *(blank)* | You can't choose a label from the evidence. Set the evidence status to `needs_review` and name the missing fact. | |

If two labels seem to fit:

- **Pick the most specific label that fully fits.** `related` is for pairs with a documented connection that don't meet any of the more specific labels.
- **Equal only at some scopes is not `direct_equivalent`.** If the pair is identical at *some* of the stated scopes but not all (e.g. same overall total, different by month), don't use `direct_equivalent`. Say where they diverge.
- **For conditional relationships, spell out the condition.** Where the relationship depends on a transform or a condition, state it in the "Conditions" column and give each prerequisite's status.

## 5. Evidence status (pick one)

| Status | Use it when |
| --- | --- |
| `sufficient` | What you examined settles your label. |
| `needs_review` | A decisive fact is missing. Name it in the "Missing evidence" column. |

## 6. Using query results

Running queries is allowed, but numbers need care:

- **Different numbers at the stated scope are evidence against equivalence at that scope.** This holds only when both metrics are queried the same way: same grouping, same time grain, same period. Record the query and one example of a difference, e.g. "month X: 1,200 vs 1,150".
- **Equal numbers don't prove equivalence.** They show agreement on *this sample data only*. The definitions could still differ on other data, for example rows with NULLs, missing matches or other filters. Still judge from the definitions.
- **Values don't choose between the other labels.** A difference tells you "not equivalent at this scope". Whether the pair is a scope variant, related, or something else still comes from the definitions.
- **Watch for empty groups.** If one metric has no row for a month or group and the other does, note it. How missing rows and NULLs are handled is often the whole story.
- **Record every query that affected your decision.** Copy the exact command. You can paste short results or summarise them.

## 7. Order of work

1. **Practice round:** [practice/CAL_PRACTICE_PACKET.md](practice/CAL_PRACTICE_PACKET.md), 3 pairs. It isn't scored. It exists to find confusing wording in this guide. Afterwards you may discuss the *rules*, but not the pairs, with the coordinator. Clarifications come to everyone in writing.
2. **Main round:** packets with pair codes like `P-01`, added later as new folders. Each has its own setup sheet.

## 8. Sending your worksheet

1. **Make your worksheet:** copy [templates/REVIEWER_WORKSHEET.md](templates/REVIEWER_WORKSHEET.md) to a file outside this repository, e.g. `ReviewerB_CAL.md` in your work folder, and fill it in.
2. **Email it** to the coordinator as an attachment. The email timestamp records when it was finished.
3. **Keep your own copy.** Don't edit it after sending.

Thank you. Your careful, independent judgment is what makes this study credible.
