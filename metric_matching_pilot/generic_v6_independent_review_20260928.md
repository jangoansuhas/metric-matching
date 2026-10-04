# Independent v6 review — public development only (2026-09-28 UTC)

**Disposition: bounded development pass; held-out source gate remains blocked.** I reviewed the final trace and common-input outputs against `generic_v6_preimplementation_contract.md` and the v5 inputs. This is an independent AI technical review, not human annotation or gold. No newly selected held-out repository source was opened. The v1–v5 freezes were not edited; the v5 read-only checkpoint still passes.

## Final-byte SHA-256 ledger for the v6 freeze

All paths below are relative to `metric_matching_pilot/`. The seven hashes were computed after the final trace-integrated `--check` runs and refer to the files reviewed here.

| File | SHA-256 |
| --- | --- |
| `generic_v6_preimplementation_contract.md` | `7dd985de6afbce77ff0201e4b8cee0ca0f8e9601a90145a18bcbba5360a30f19` |
| `generic_metric_expression_trace.py` | `0f480b24a8e067ffb69ebe4734a643dd3164c57d63db576ebb8a881e7de22925` |
| `generic_metric_expression_trace_report.json` | `0c727e08f3bd4f02bab3b475771c8299aef16145bc85432c94e5e250d0861d5c` |
| `generic_metric_expression_trace_report.md` | `4cf4951fa2d2d81d9e84cd812d83d59e3830bf2077857668f5e09b611e9fb19a` |
| `generic_i1_same_input.py` | `356e685f6fe49a211ab4c8ca1ce1485c141e7a4011bd371e3182a8d9f504b07c` |
| `generic_i1_same_input_report.json` | `b0cef40239ebe06706339b397fa2887105cd92614d2ca2e9b303adc838989318` |
| `generic_i1_same_input_report.md` | `bb8e7cc794807bf1042530aa08c63bcfedd0540d000e2a8b126dbe5c452a2b65` |

The manifest file SHA-256 is `1467a9a6a71de14f196adbab89927083adcc2b9f680f7e9b6256a0720b40fb24`; the checked-out Jaffle/Sidemantic Git HEAD is `7be2c5838dbdeca8e915d4e46db70e910753d7f6`. Both agree with the trace and I1 input metadata. The local manifest's build event does **not** attest that commit.

## Read-only regeneration and independent probes

From the workspace root, these commands exited 0 without changing the worker reports:

```bash
python3 -B metric_matching_pilot/freeze_development_revision_v5.py --check
python3 -B metric_matching_pilot/generic_metric_expression_trace.py --check
python3 -B metric_matching_pilot/generic_metric_expression_trace.py --self-test
python3 -B metric_matching_pilot/generic_i1_same_input.py --check
python3 -B metric_matching_pilot/generic_i1_same_input.py --expression-trace metric_matching_pilot/generic_metric_expression_trace_report.json --check
```

Independent, in-memory assertions (no saved test fixture) recomputed the canonical packet and pair hashes; checked every row against each I1 method's output; compared all 32 packet declarations with the 32 trace record IDs, model candidates, and measure links; and checked all method versions, evidence-field lists and pair counts. I removed one trace record, changed the trace commit, and changed its manifest digest in separate controls: all three were rejected. A forged `verified` trace status stayed `needs_review` under the existing model/source checks. A duplicate measure name within an explicit semantic model was rejected as ambiguous; a joined `SELECT *` was flagged for both star expansion and field-owner ambiguity; changing a model's compiled SQL in memory produced `compiled_file_hash_mismatch`. All unknown semantic fields stayed unknown, and unknown numeric eligibility remained in the 496-pair frame.

## Coverage and same-input result

- The emitted declaration universe is **32 distinct IDs: 19 exposed metrics and 13 measures**, including 10 declarations with unknown numeric eligibility. It has exactly **496** unordered pairs. The 19-metric primary subset has exactly **171** pairs. True arity outside successfully emitted declarations is unknown.
- The I1 packet SHA-256 is `e7aa1991367e28245c49d89492cd9529a02c6917c41da3838053c179fa0d2ec0`. The 496-pair ID SHA-256 is `67cb4648a0a8f866869208db451d7384f86a9bb38e65126de08e4da0114812b2`; the 171-pair primary SHA-256 is `8232e9567af68c998560e4c49ba0567dabc93655a95ed866a7d4d8b704aab373`. All three I1 methods use those identical I1 packet bytes and the 496-pair set: `normalized_ast_source_v1`, `constraint_aware_v1`, and `source_guided_conditional_v1`. Their declared evidence fields and versions are recorded in `method_inputs`.
- The I0 packet SHA-256 is `99ad1b1b8f7ea182d1537b0bdfb23a14a924cde4ab7b668bc2d5d09de67fda96`. Its declarations contain **only** `id` and `name`; raw exact, normalized exact, Jaro–Winkler, token Jaccard, and Soundex each score the same 496 pair IDs, with explicit `_v1` versions. I0 scores appear in the **output rows**, not as I1 method input or truth labels.
- The final I1 packet incorporates the trace report: all 32 record identities and measure links agree, and 31 declarations have a unique compiled-*model* candidate. The remaining declaration has multiple model candidates. The trace verifies **0** compiled metric expressions; all **32** remain `needs_review`. All three I1 methods abstain on semantic decisions for every pair. The constraint comparator emits 11 shared-declared-measure review signals, and the conditional method additionally emits 146 same-declaration-file signals. These are syntactic candidate signals, not correctness or advantage estimates. The normalized AST comparator abstains on all 496 pairs because verified scalar AST evidence is absent.
- The canonical input packets contain no author/AI review labels, human gold, method scores, or private employer examples. The report's method scores/signals are outputs only. No accuracy, candidate Recall@k, F1, review-effort saving, or method superiority is measured.

## Provenance and remaining stops

- The 13 Jaffle compiled **model** files match manifest `compiled_code`, but all 13 source mappings in the v5 provenance report remain `needs_review` because their manifest source checksums agree with neither pinned source blobs nor manifest `raw_code`. The final trace keeps the mismatch, joined `SELECT *`, CTE and field-owner boundaries from becoming a verified scalar expression. A manifest metric-to-measure dependency is a declared reference, not an equivalence label or compiled metric query.
- The trace records a second, independent build uncertainty: pinned `package-lock.yml` SHA-256 `a1d44d11c893f4d68e722ef8479bd3c4d2f632202f1ef7bd4ade6a14986b50db` differs from local SHA-256 `67ecfc0a7ebdcc03b8e2f38c86d7b283e72c5d58fb9a7de9b4f30aa2a3a01eef`. The pinned lock lists different dbt package versions/revisions from the modified working file. The build commit is unattested. **Neither observation identifies the cause of the checksum mismatch.**
- The v6 implementation is pinned to one development checkout and known declaration counts. It demonstrates a reproducible same-input scaffold and conservative abstention, but no verified positive scalar trace and no effective normalized AST comparison on public metrics. A general adapter and substantive context-matched baselines are still needed before reading held-out source. The I1 script has no dedicated `--self-test`; independent in-memory tamper and pair-universe probes above partly cover that gap.

## Separate public calibration packet check

I read `metric_matching_public_calibration_packet.md` at the workspace root, without editing it. It contains three blank reviewer cards/worksheets, rubric **names** but no assigned relationship labels, model predictions, similarity scores, private company definitions, or filled answers. All 21 linked line ranges exist in immutable Git blobs at commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`; the named YAML top-level metrics are at the cited lines. CAL-03 clearly identifies the cross-file `order_cost` metric/measure reference and says no verified **compiled** binding is supplied. For coordinator clarity, specify that the manifest does provide a declared dependency to `semantic_model.jaffle_shop.orders`; the remaining ambiguity is compiled scalar/value semantics, not the absence of any manifest-level link. This practice packet is separate from v6 method inputs and is **not** held-out gold or an evaluation result.

**Gate:** signed off only for the bounded development reports at the hashes above. Do not open newly selected held-out repository source on the strength of this checkpoint; first fix a generic expression adapter and run context-matched methods with independently reviewed, label-free packet inputs. Human annotations and adjudication remain future work.
