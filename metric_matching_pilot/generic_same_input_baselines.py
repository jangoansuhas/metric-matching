#!/usr/bin/env python3
"""Same-input, development-only diagnostics over eligible .value projections.

Only generic_sql_inventory_report.json is read. This script does not inspect SQL,
repositories, labels, or held-out material. Scores and syntax signals are not
semantic match predictions. --check verifies committed reports without writing.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generic_sql_inventory_report.json"
JSON_OUT = ROOT / "generic_same_input_baselines_report.json"
MD_OUT = ROOT / "generic_same_input_baselines_report.md"
VERSION = "generic_same_input_baselines_v1"
FROZEN_INPUT_SHA256 = "fdb68bd980cb425e39140056b3360952d3ccb77b1545523a07e47fad256abfc7"
SEMANTIC_FIELDS = ("grain", "time", "null_policy", "join_cardinality", "snapshot")
SYNTAX_FIELDS = ("ast_operator", "aggregate_argument", "source_table_refs", "where", "group_by")
PACKET_FIELDS = ("id", "view", "output_alias", "expression_ast", "ast_operator",
                 "aggregate_argument", "aggregate_argument_ast", "source_table_refs",
                 "where", "group_by", "status", "failure_reasons", "unknown_semantics")
METHODS = ("raw_exact", "normalized_name_exact", "jaro_winkler", "token_jaccard",
           "normalized_ast_source", "constraint_aware")
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
WORD = re.compile(r"[a-z0-9]+")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def tokens(value: str) -> list[str]:
    return WORD.findall(CAMEL.sub(" ", value).casefold())


def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    radius = max(0, max(len(a), len(b)) // 2 - 1)
    am = [False] * len(a)
    bm = [False] * len(b)
    matches = 0
    for i, letter in enumerate(a):
        for j in range(max(0, i - radius), min(len(b), i + radius + 1)):
            if not bm[j] and b[j] == letter:
                am[i] = bm[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    aa = [letter for letter, used in zip(a, am) if used]
    bb = [letter for letter, used in zip(b, bm) if used]
    transpositions = sum(x != y for x, y in zip(aa, bb)) / 2
    return (matches / len(a) + matches / len(b)
            + (matches - transpositions) / matches) / 3


def jaro_winkler(a: str, b: str) -> float:
    base = jaro(a, b)
    if base < 0.7:
        return base
    prefix = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        prefix += 1
    return base + 0.1 * prefix * (1 - base)


def name_scores(left_name: str, right_name: str) -> dict:
    """I0 uses metric/view names only; output IDs are pair identifiers."""
    a = " ".join(tokens(left_name))
    b = " ".join(tokens(right_name))
    ta, tb = set(tokens(left_name)), set(tokens(right_name))
    union = ta | tb
    return {
        "raw_exact": int(left_name == right_name),
        "normalized_name_exact": int(a == b),
        "jaro_winkler": round(jaro_winkler(a, b), 6),
        "token_jaccard": round(len(ta & tb) / len(union), 6) if union else 0.0,
    }


def source_signal(left: dict, right: dict) -> dict:
    if left["status"] != "supported_aggregate" or right["status"] != "supported_aggregate":
        return {"syntax_signal": "abstain", "reason": "unsupported_output"}
    differences = [field for field in SYNTAX_FIELDS if left[field] != right[field]]
    return {"syntax_signal": "source_difference" if differences else "same_source_signature",
            "reason": "different_source_fields" if differences else "same_source_fields",
            "differing_fields": differences}


def missing_semantics(left: dict, right: dict) -> list[str]:
    return [field for field in SEMANTIC_FIELDS
            if any(side.get("unknown_semantics", {}).get(field) in (None, "unknown", "")
                   for side in (left, right))]


def checked_inventory() -> tuple[dict, bytes, dict, list[tuple[str, str]], str]:
    raw = SOURCE.read_bytes()
    if sha256(raw) != FROZEN_INPUT_SHA256:
        raise ValueError("Frozen inventory digest changed; explicitly review and version the input before rerunning")
    source = json.loads(raw)
    if source.get("schema_version") != 1 or source.get("scope") != "development_only_generic_create_view_source_inventory":
        raise ValueError("Unexpected inventory schema or scope")
    outputs = source["outputs"]
    index = {o["id"]: o for o in outputs}
    if len(index) != len(outputs) or len(index) != source["coverage"]["outputs"]:
        raise ValueError("Duplicate or missing output IDs")
    if any(not set(PACKET_FIELDS).issubset(o) for o in outputs):
        raise ValueError("Required same-input packet fields missing")
    expected = list(itertools.combinations(sorted(index), 2))
    actual = [(p["left_id"], p["right_id"]) for p in source["pairs"]]
    if (actual != expected or len(actual) != source["coverage"]["unordered_pairs"]):
        raise ValueError("Input pair IDs are not the complete unordered set over emitted IDs")
    # The development fixture emits one entity_key and one value per view. This
    # explicit alias rule is fixture-specific and must not migrate to held-out.
    eligible_ids = sorted(identifier for identifier, item in index.items()
                          if item["output_alias"] == "value")
    if len(source["views"]) != 12 or len(eligible_ids) != 12 or len(index) != 24:
        raise ValueError("Development fixture's eligibility shape changed")
    if {index[i]["view"] for i in eligible_ids} != {v["name"] for v in source["views"]}:
        raise ValueError("Expected one eligible .value output per development view")
    eligible = list(itertools.combinations(eligible_ids, 2))
    if not set(eligible).issubset(actual) or len(eligible) != 66:
        raise ValueError("Eligible pair set missing from raw inventory")
    packet = [{key: index[identifier][key] for key in PACKET_FIELDS} for identifier in eligible_ids]
    return source, raw, index, eligible, sha256(canonical_bytes(packet))


def generate() -> dict:
    source, raw, index, pairs, packet_hash = checked_inventory()
    pair_hash = sha256(canonical_bytes(pairs))
    rows = []
    for left_id, right_id in pairs:
        left, right = index[left_id], index[right_id]
        signal = source_signal(left, right)
        missing = missing_semantics(left, right)
        # The packet has syntax, but cannot prove grain, time, NULL, join, or
        # snapshot alignment. A source difference is not a contradiction.
        ast = {**signal, "semantic_decision": "abstain",
               "abstention_reason": "unsupported_output" if signal["syntax_signal"] == "abstain"
               else "semantic_fields_unknown"}
        constraints = {**signal, "missing_semantic_fields": missing,
                       "semantic_decision": "abstain",
                       "abstention_reason": "unsupported_output" if signal["syntax_signal"] == "abstain"
                       else "semantic_fields_unknown" if missing else "no_equivalence_proof"}
        rows.append({"left_id": left_id, "right_id": right_id,
                     "i0_scores": name_scores(left["view"], right["view"]),
                     "i1_normalized_ast_source": ast,
                     "i1_constraint_aware": constraints})
    if len(rows) != len(pairs):
        raise AssertionError("Pair coverage mismatch")
    syntax_counts = dict(sorted(Counter(r["i1_normalized_ast_source"]["syntax_signal"] for r in rows).items()))
    return {
        "schema_version": 1, "algorithm_version": VERSION,
        "scope": "same_input_development_diagnostic_only",
        "input": {"path": SOURCE.name, "sha256": sha256(raw),
                  "inventory_source_sha256": source["input"]["sha256"],
                  "evidence_packet_sha256": packet_hash},
        "method_inputs": {name: {"inventory_sha256": sha256(raw),
                                 "pair_set_sha256": pair_hash,
                                 **({"evidence_packet_sha256": packet_hash} if name in METHODS[4:] else {})}
                          for name in METHODS},
        "raw_inventory": {"emitted_output_ids": len(index),
                          "unordered_pairs": source["coverage"]["unordered_pairs"],
                          "excluded_nonmetric_entity_key_outputs": 12},
        "pair_universe": {"eligible_scalar_ids": 12, "unordered_pairs": len(pairs),
                          "pair_set_sha256": pair_hash,
                          "all_methods_same_pair_set": True,
                          "true_projection_arity_known": False,
                          "held_out": False,
                          "eligibility_rule": "Development fixture only: output_alias == value; includes supported and unsupported .value projections."},
        "coverage": {"i0_scored_pairs_per_method": {m: len(pairs) for m in METHODS[:4]},
                     "i1_syntax_signals_per_method": {m: syntax_counts for m in METHODS[4:]},
                     "i1_semantic_abstentions_per_method": {m: len(pairs) for m in METHODS[4:]},
                     "i1_semantic_decisions_per_method": {m: 0 for m in METHODS[4:]}},
        "method_definitions": {
            "raw_exact": "Case-sensitive equality of view/metric names; sanity reference only because distinct fixture views have unique names.",
            "normalized_name_exact": "Equality after camel/punctuation splitting and ASCII casefold of view/metric names; binary score.",
            "jaro_winkler": "Jaro-Winkler over normalized view/metric names; prefix scaling 0.1 when Jaro >= 0.7; rounded to six decimals.",
            "token_jaccard": "Set Jaccard over normalized view/metric name tokens; rounded to six decimals.",
            "normalized_ast_source": "Compare AST aggregate operator/argument and source table/WHERE/GROUP BY fields from the same inventory packet; syntax signal only.",
            "constraint_aware": "Same syntax packet plus grain, time, NULL, join cardinality and snapshot requirements; abstain if missing. No domain constraints supplied.",
        },
        "rows": rows,
        "limitations": [
            "The raw inventory has 24 emitted outputs and 276 pairs, including 12 entity_key projections that are not metric scalars. The comparison uses only the 12 .value projections and their 66 pairs.",
            "The .value alias eligibility rule is specific to this development fixture, not a generic rule for held-out repositories.",
            "Even the 24/276 raw inventory covers emitted IDs only, not a known full metric universe.",
            "An aliasless parse failure gets one abstaining placeholder; its true projection arity is unknown.",
            "Unparseable views receive placeholders, not recovered aliases; their true output count is unknown.",
            "The SQL inventory is a synthetic development fixture, not compiled dbt or held-out repository evidence.",
            "I0 scores are uncalibrated retrieval diagnostics, not match predictions or effectiveness metrics.",
            "I0 scores use view/metric names, never the shared .value suffix; raw_exact is a zero-valued sanity reference across unique fixture view names.",
            "I1 source sameness is a review signal, not semantic equivalence; source difference is not a semantic contradiction.",
            "No human gold, candidate Recall@k, classification F1, or method-superiority claim is supported.",
            "No metric-owner adjudication or null/time/grain/join verification was available.",
        ],
    }


def markdown(report: dict) -> str:
    c = report["coverage"]
    u = report["pair_universe"]
    lines = ["# Same-input baseline diagnostic (development only)", "",
             f"Frozen input: `{report['input']['path']}` SHA256 `{report['input']['sha256']}`.",
             f"Algorithm: `{VERSION}`. Raw inventory: {report['raw_inventory']['emitted_output_ids']} outputs / {report['raw_inventory']['unordered_pairs']} pairs. Eligible fixture scalars: {u['eligible_scalar_ids']} `.value` outputs / {u['unordered_pairs']} pairs.",
             f"Pair-set SHA256: `{u['pair_set_sha256']}`. I1 packet SHA256: `{report['input']['evidence_packet_sha256']}`.",
             "", "## Same-input coverage", "",
             "| Method | Input pair IDs | Output | Semantic decisions |", "| --- | ---: | --- | ---: |"]
    for m in METHODS[:4]:
        lines.append(f"| {m} | {c['i0_scored_pairs_per_method'][m]} | Score on every eligible pair | 0 |")
    for m in METHODS[4:]:
        signals = c["i1_syntax_signals_per_method"][m]
        lines.append(f"| {m} | {u['unordered_pairs']} | {signals.get('same_source_signature', 0)} same syntax, {signals.get('source_difference', 0)} different syntax, {signals.get('abstain', 0)} unsupported | {c['i1_semantic_decisions_per_method'][m]} |")
    lines += ["", "All methods use the exact same 66 eligible pair IDs. Both I1 baselines use the identical packet hash and fields. All 66 I1 semantic decisions abstain because required semantics are unknown or outputs are unsupported.",
              "", "## Interpretation", "",
              "This is a same-input development diagnostic on a synthetic CREATE VIEW fixture. I0 scores use view/metric names; full output IDs serve only as pair identities. Raw exact match is a sanity reference and scores zero for distinct views here. Scores have no calibrated threshold and there is no human gold; the table cannot establish Recall@k, F1, or superiority. A different SQL source expression does not prove a semantic contradiction, and a matching source signature does not prove equivalence.",
              "", "The raw 24/276 inventory is complete only over emitted output IDs; 12 entity_key projections are not metric scalars. For this fixture alone, eligibility is exactly the 12 `.value` scalar projections, including unsupported ones, giving 66 pairs. This alias rule is not a generic held-out rule. An unparseable view receives one abstaining placeholder although its true projection arity is unknown. Therefore this is not a full metric universe or held-out readiness evidence.",
              "", "## Method definitions", ""]
    for name, definition in report["method_definitions"].items():
        lines.append(f"- **{name}:** {definition}")
    lines += ["", "## Reproduction", "", "Run `python generic_same_input_baselines.py --check`. It reads the frozen JSON and checks both report files byte-for-byte without writing. The frozen input digest and algorithm version are in the JSON report.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify reports without writing")
    args = parser.parse_args()
    report = generate()
    rendered = {JSON_OUT: (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode(),
                MD_OUT: markdown(report).encode()}
    if args.check:
        for path, expected in rendered.items():
            if not path.exists() or path.read_bytes() != expected:
                raise SystemExit(f"FAIL: stale or missing {path.name}")
        print("PASS: frozen input and both reports agree; --check wrote nothing")
    else:
        for path, value in rendered.items():
            path.write_bytes(value)
        print(f"Wrote {JSON_OUT.name} and {MD_OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
