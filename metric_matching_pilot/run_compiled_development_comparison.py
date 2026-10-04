#!/usr/bin/env python3
"""Run fixed baselines and proposed review method on the label-free Jaffle packet.

This development diagnostic produces syntax/constraint signals and abstentions;
it does not read annotations or estimate accuracy, Recall@k, or method safety.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

from compiled_jaffle_packet import canonical, sha256
from generic_same_input_baselines import name_scores
from run_development_baselines import soundex


VERSION = "compiled_jaffle_same_input_comparison_v2"
EXPECTED_PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"
EXPECTED_PAIR_SET_SHA256 = "0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0"
ALLOWED_DECISIONS = {"direct_equivalent", "cross_grain_equivalent", "temporal_or_scope_variant",
                     "conflicting_definition", "related", "non_match", "abstain"}


def _validate(method: str, result: dict) -> dict:
    if not isinstance(result, dict) or result.get("decision") not in ALLOWED_DECISIONS:
        raise ValueError(f"{method}: malformed decision output: {result!r}")
    # This frozen packet contains no authenticated semantic prerequisites.
    # A future decision driver needs a separate evidence-authentication gate.
    if result["decision"] != "abstain":
        raise ValueError(f"{method}: semantic decision is unsupported on the frozen development packet")
    if not isinstance(result.get("signal"), str) or not isinstance(result.get("reason"), str):
        raise ValueError(f"{method}: signal and reason are required strings")
    if not isinstance(result.get("evidence"), list):
        raise ValueError(f"{method}: evidence must be a list")
    score = result.get("candidate_score")
    if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float))
                              or not math.isfinite(score) or not 0 <= score <= 1):
        raise ValueError(f"{method}: candidate_score must be null or finite in [0, 1]")
    return result


def generate(packet_path: Path) -> dict:
    # All I1 methods receive the same two cards for every compatible pair;
    # the common scope policy hard-gates mixed-scope pairs for all methods.
    import compiled_ast_lineage_baseline as ast_module
    from compiled_ast_lineage_baseline import compare as ast_compare
    from compiled_constraint_baseline import compare as constraint_compare
    from compiled_proposed_method import compare as proposed_compare
    from compiled_numeric_eligibility import classify as classify_numeric

    if ast_module.sqlglot is None or ast_module.sqlglot.__version__ != ast_module.SQLGLOT_PIN:
        raise RuntimeError(f"full I1 comparison requires sqlglot=={ast_module.SQLGLOT_PIN}")

    packet_bytes = packet_path.read_bytes()
    if sha256(packet_bytes) != EXPECTED_PACKET_SHA256:
        raise ValueError("I1 packet bytes differ from the frozen label-free input")
    packet = json.loads(packet_bytes)
    if packet.get("packet_version") != "compiled_jaffle_i1_packet_v2":
        raise ValueError("unknown or unfrozen I1 packet version")
    if packet.get("pair_set_sha256") != EXPECTED_PAIR_SET_SHA256:
        raise ValueError("pair-set hash differs from frozen frame")
    cards = {card["metric_id"]: card for card in packet["cards"]}
    if len(cards) != 19 or len(packet["pairs"]) != 171:
        raise ValueError("incomplete development frame")
    eligibility_by_metric = {metric_id: classify_numeric(card) for metric_id, card in cards.items()}
    rows = []
    for pair in packet["pairs"]:
        a, b = cards[pair["a"]], cards[pair["b"]]
        if a["metric_id"] + "||" + b["metric_id"] != pair["pair_id"]:
            raise ValueError("unstable pair identity")
        i0 = name_scores(a["metric_name"], b["metric_name"])
        i0["soundex"] = int(soundex(a["metric_name"]) == soundex(b["metric_name"]))
        if not pair["scope_compatible"]:
            abstain = {"signal": "incompatible_generated_scope", "decision": "abstain",
                       "candidate_score": None, "candidate_hypothesis": None, "obligations": {}, "evidence": [],
                       "reason": "one metric has only a metric_time query while the other has only an ungrouped query"}
            ast, constraint, proposed = dict(abstain), dict(abstain), dict(abstain)
        else:
            ast = ast_compare(a, b)
            constraint = constraint_compare(a, b)
            proposed = proposed_compare(a, b)
        rows.append({"pair_id": pair["pair_id"], "a": pair["a"], "b": pair["b"],
                     "target_scope": pair["target_scope"], "scope_compatible": pair["scope_compatible"],
                     "name_only_i0": i0,
                     "ast_lineage_i1": _validate("ast_lineage_i1", ast),
                     "constraint_aware_i1": _validate("constraint_aware_i1", constraint),
                     "proposed_i1": _validate("proposed_i1", proposed)})
    counts = {}
    for key in ("ast_lineage_i1", "constraint_aware_i1", "proposed_i1"):
        counts[key] = {"decision": dict(sorted(collections.Counter(row[key]["decision"] for row in rows).items())),
                       "signal": dict(sorted(collections.Counter(row[key]["signal"] for row in rows).items()))}
    comparable = [row for row in rows if row["scope_compatible"]]
    rank_inputs = {
        "i0_raw_exact": lambda r: r["name_only_i0"]["raw_exact"],
        "i0_normalized_name_exact": lambda r: r["name_only_i0"]["normalized_name_exact"],
        "i0_jaro_winkler": lambda r: r["name_only_i0"]["jaro_winkler"],
        "i0_token_jaccard": lambda r: r["name_only_i0"]["token_jaccard"],
        "i0_soundex": lambda r: r["name_only_i0"]["soundex"],
        "i1_ast_lineage": lambda r: r["ast_lineage_i1"].get("candidate_score"),
        "i1_constraint_aware": lambda r: r["constraint_aware_i1"].get("candidate_score"),
        "i1_proposed": lambda r: r["proposed_i1"].get("candidate_score"),
    }
    # Restrict the exploratory rank frame to common ungrouped query scope;
    # stable pair IDs break ties. No judged positives, so no Recall@k is computed.
    candidate_ranking = {}
    candidate_by_anchor = {}
    for name, get_score in rank_inputs.items():
        scored = [(get_score(row), row["pair_id"]) for row in comparable]
        candidate_ranking[name] = {
            "scored_pairs": sum(score is not None for score, _ in scored),
            "positive_score_pairs": sum(score is not None and score > 0 for score, _ in scored),
            "ranked_pair_ids": [pair_id for score, pair_id in sorted(
                (item for item in scored if item[0] is not None),
                key=lambda item: (-item[0], item[1]))],
        }
        anchors = sorted({metric for row in comparable for metric in (row["a"], row["b"])})
        candidate_by_anchor[name] = {
            anchor: [partner for score, partner in sorted(
                ((get_score(row), row["b"] if row["a"] == anchor else row["a"])
                 for row in comparable if anchor in (row["a"], row["b"])
                 and get_score(row) is not None),
                key=lambda item: (-item[0], item[1]))]
            for anchor in anchors
        }
    here = Path(__file__).resolve().parent
    method_files = ("compiled_jaffle_packet.py", "compiled_ast_lineage_baseline.py",
                    "compiled_constraint_baseline.py", "generic_same_input_baselines.py",
                    "compiled_numeric_eligibility.py", "generic_metric_eligibility.py",
                    "compiled_proposed_method.py", "run_development_baselines.py",
                    "compiled_development_baselines_contract.md",
                    "compiled_proposed_development_contract.md",
                    "run_compiled_development_comparison.py")
    method_sha256 = {name: sha256((here / name).read_bytes()) for name in method_files}
    return {"version": VERSION, "development_only": True, "human_gold_used": False,
            "packet_sha256": sha256(packet_bytes), "pair_set_sha256": packet["pair_set_sha256"],
            "method_sha256": method_sha256,
            "parser": {"name": "sqlglot", "version": ast_module.sqlglot.__version__,
                       "dialect": ast_module.DIALECT},
            "metric_count": 19, "pair_count": 171,
            "numeric_eligibility_by_metric": eligibility_by_metric,
            "numeric_eligibility_counts": dict(sorted(collections.Counter(
                item["status"] for item in eligibility_by_metric.values()).items())),
            "comparable_pair_count": len(comparable),
            "candidate_ranking_comparable_only": candidate_ranking,
            "candidate_ranking_by_anchor_comparable_only": candidate_by_anchor,
            "common_decided_pairs": sum(row["ast_lineage_i1"]["decision"] != "abstain" and
                                        row["constraint_aware_i1"]["decision"] != "abstain" and
                                        row["proposed_i1"]["decision"] != "abstain" for row in rows),
            "proposed_review_hypotheses": sum(bool(row["proposed_i1"].get("candidate_hypothesis"))
                                               for row in rows),
            "counts": counts, "rows": rows}


def markdown(report: dict) -> str:
    out = ["# Compiled Jaffle same-input comparison (development only)", "",
           f"Frozen I1 packet SHA-256: `{report['packet_sha256']}`. Pair-set SHA-256: `{report['pair_set_sha256']}`.",
           "Method file hashes are recorded in the JSON report.",
           f"The full frame contains {report['pair_count']} pairs over {report['metric_count']} declared metrics."
           " Three I1 methods run on the 153 same-scope pairs. The common harness retains 18"
           " incompatible-scope pairs and records an abstention for each method.", "",
           "Declaration-only numeric eligibility: " + ", ".join(
               f"{k}: {v}" for k, v in report["numeric_eligibility_counts"].items()) +
           ". No runtime numeric certification follows.", "",
           "| I1 method | Semantic decisions | Abstentions | Syntax/other signals |", "| --- | ---: | ---: | --- |"]
    for name in ("ast_lineage_i1", "constraint_aware_i1", "proposed_i1"):
        counts = report["counts"][name]
        decided = report["pair_count"] - counts["decision"].get("abstain", 0)
        signals = ", ".join(f"{key}: {value}" for key, value in counts["signal"].items())
        out.append(f"| `{name}` | {decided} | {counts['decision'].get('abstain', 0)} | {signals} |")
    out += ["", f"Common decided pairs: **{report['common_decided_pairs']}**.", "",
            f"Proposed source-linked review prompts: **{report['proposed_review_hypotheses']}**;"
            " these are questions or test recipes, not semantic decisions."
            " The weaker same-model scores add no prompt.", "",
            "Candidate-score coverage on the 153 common ungrouped-scope pairs (global ties use lexical pair ID; per-anchor ties use candidate ID):",
            "", "| Method | Scored pairs | Positive scores |", "| --- | ---: | ---: |"]
    for name, row in report["candidate_ranking_comparable_only"].items():
        out.append(f"| `{name}` | {row['scored_pairs']} / {report['comparable_pair_count']} |"
                   f" {row['positive_score_pairs']} |")
    if all(report["candidate_ranking_comparable_only"][name]["positive_score_pairs"] == 0
           for name in ("i0_raw_exact", "i0_normalized_name_exact")):
        out += ["", "Both exact-name rankers score zero on every comparable pair; their"
                " recorded order is entirely the lexical tie break."]
    out += ["",
            "I0 name scores (exact, normalized exact, Jaro–Winkler, token Jaccard, Soundex) are recorded"
            " on the same pair IDs as retrieval signals, not semantic decisions. All I1 methods receive"
            " identical label-free cards on the same-scope pairs. The JSON also records per-anchor rankings for the"
            " 18 ungrouped declarations. A shared absent metric filter is only declaration-level agreement;"
            " base population stays unknown and gives no cross-measure score credit."
            " No human labels or held-out sources enter this report."
            " Syntax agreement, an abstention, and a compiler-generated query are not evidence of classification"
            " accuracy, candidate Recall@k, or improved maintenance outcomes. The compiled SQL is DuckDB-only"
            " and was not executed.", ""]
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    p.add_argument("--packet", type=Path, default=here / "compiled_jaffle_i1_packet.json")
    p.add_argument("--json", type=Path, default=here / "compiled_development_baselines_report.json")
    p.add_argument("--markdown", type=Path, default=here / "compiled_development_baselines_report.md")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    report = generate(a.packet)
    data = canonical(report)
    md = markdown(report).encode("utf-8")
    if a.check:
        if a.json.read_bytes() != data or a.markdown.read_bytes() != md:
            raise SystemExit("compiled development baseline reports differ from frozen outputs")
        print("baseline report OK", hashlib.sha256(data).hexdigest())
    else:
        a.json.write_bytes(data)
        a.markdown.write_bytes(md)
        print("wrote compiled development baseline report", hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
