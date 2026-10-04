# Same-input baseline diagnostic (development only)

Frozen input: `generic_sql_inventory_report.json` SHA256 `fdb68bd980cb425e39140056b3360952d3ccb77b1545523a07e47fad256abfc7`.
Algorithm: `generic_same_input_baselines_v1`. Raw inventory: 24 outputs / 276 pairs. Eligible fixture scalars: 12 `.value` outputs / 66 pairs.
Pair-set SHA256: `4eff0ecb816a0268adef5e285531362b3f6787c86865bdc7765753127a9100fb`. I1 packet SHA256: `6e575c9fd3b8d3021eb6a3adaff1a677a91ad0c8fc47107a41879e5d2219bff9`.

## Same-input coverage

| Method | Input pair IDs | Output | Semantic decisions |
| --- | ---: | --- | ---: |
| raw_exact | 66 | Score on every eligible pair | 0 |
| normalized_name_exact | 66 | Score on every eligible pair | 0 |
| jaro_winkler | 66 | Score on every eligible pair | 0 |
| token_jaccard | 66 | Score on every eligible pair | 0 |
| normalized_ast_source | 66 | 1 same syntax, 5 different syntax, 60 unsupported | 0 |
| constraint_aware | 66 | 1 same syntax, 5 different syntax, 60 unsupported | 0 |

All methods use the exact same 66 eligible pair IDs. Both I1 baselines use the identical packet hash and fields. All 66 I1 semantic decisions abstain because required semantics are unknown or outputs are unsupported.

## Interpretation

This is a same-input development diagnostic on a synthetic CREATE VIEW fixture. I0 scores use view/metric names; full output IDs serve only as pair identities. Raw exact match is a sanity reference and scores zero for distinct views here. Scores have no calibrated threshold and there is no human gold; the table cannot establish Recall@k, F1, or superiority. A different SQL source expression does not prove a semantic contradiction, and a matching source signature does not prove equivalence.

The raw 24/276 inventory is complete only over emitted output IDs; 12 entity_key projections are not metric scalars. For this fixture alone, eligibility is exactly the 12 `.value` scalar projections, including unsupported ones, giving 66 pairs. This alias rule is not a generic held-out rule. An unparseable view receives one abstaining placeholder although its true projection arity is unknown. Therefore this is not a full metric universe or held-out readiness evidence.

## Method definitions

- **raw_exact:** Case-sensitive equality of view/metric names; sanity reference only because distinct fixture views have unique names.
- **normalized_name_exact:** Equality after camel/punctuation splitting and ASCII casefold of view/metric names; binary score.
- **jaro_winkler:** Jaro-Winkler over normalized view/metric names; prefix scaling 0.1 when Jaro >= 0.7; rounded to six decimals.
- **token_jaccard:** Set Jaccard over normalized view/metric name tokens; rounded to six decimals.
- **normalized_ast_source:** Compare AST aggregate operator/argument and source table/WHERE/GROUP BY fields from the same inventory packet; syntax signal only.
- **constraint_aware:** Same syntax packet plus grain, time, NULL, join cardinality and snapshot requirements; abstain if missing. No domain constraints supplied.

## Reproduction

Run `python generic_same_input_baselines.py --check`. It reads the frozen JSON and checks both report files byte-for-byte without writing. The frozen input digest and algorithm version are in the JSON report.
