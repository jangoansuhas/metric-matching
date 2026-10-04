#!/usr/bin/env python3
"""In-memory synthetic controls and read-only development-report smoke check.

These constructed references are test data only, not human gold or results.
Run: python3 -B metric_matching_pilot/paired_decision_safety_checks.py
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from paired_decision_safety import DEFAULT_REPORT, digest, evaluate


A = "source_guided_conditional"
B = "constraint_aware"
COMMIT = "a" * 40


def report_for(name: str, pairs: list[tuple[str, str]],
               predictions: list[tuple[dict, dict]]) -> dict:
    project = digest({"constructed_project": name})
    packet = {"schema_version": 1,
              "declarations": [{"id": identifier} for identifier in
                               sorted({identifier for pair in pairs for identifier in pair})],
              "pair_ids": [list(pair) for pair in pairs]}
    packet_hash, pair_hash = digest(packet), digest(packet["pair_ids"])
    rows = [{"left_id": left, "right_id": right, "i1": {A: pa, B: pb}}
            for (left, right), (pa, pb) in zip(pairs, predictions)]
    return {"schema_version": 1, "input": {"source_manifest_sha256": project},
            "project_identity": {"repository": f"example/{name}", "commit": COMMIT},
            "i1_packet": packet, "i1_packet_sha256": packet_hash,
            "pair_universe": {"all_pair_ids_sha256": pair_hash,
                              "all_unordered_pairs": len(pairs)},
            "method_inputs": {method: {"version": method + "_test", "input_level": "I1",
                                       "packet_sha256": packet_hash, "pair_ids_sha256": pair_hash,
                                       "pair_count": len(pairs)} for method in (A, B)},
            "coverage": {"i1_semantic_decisions_per_method": {
                method: sum(row["i1"][method]["semantic_decision"] != "abstain" for row in rows)
                for method in (A, B)}},
            "rows": rows}


def predicted(label: str, transformation_id: str | None = None) -> dict:
    result = {"semantic_decision": label}
    if transformation_id is not None:
        result["transformation_id"] = transformation_id
    return result


def adjudicated(project: str, pair: tuple[str, str], label: str,
                transformation_id: str | None = None) -> dict:
    left, right = pair
    entry = {"project_key": project, "left_id": left, "right_id": right,
             "evidence_status": "sufficient", "label": label,
             "repo_commit": COMMIT, "reviewer_codes": ["r1", "r2"],
             "adjudicator_code": "r3", "blinded_to_methods": True,
             "source_links": [
                 {"side": side, "path": f"models/{identifier}.yml", "line_start": 4,
                  "line_end": 7, "repo_commit": COMMIT}
                 for side, identifier in (("left", left), ("right", right))]}
    if transformation_id is not None:
        entry["transformation_id"] = transformation_id
    return entry


def must_fail(work: callable, message: str) -> None:
    try:
        work()
    except ValueError:
        return
    raise AssertionError(message)


def check_constructed() -> None:
    pairs = [("a", "b"), ("a", "c"), ("a", "d"),
             ("b", "c"), ("b", "d"), ("c", "d")]
    predictions = [
        (predicted("direct_equivalent"), predicted("direct_equivalent")),
        (predicted("direct_equivalent"), predicted("related")),
        (predicted("non_match"), predicted("non_match")),
        (predicted("direct_equivalent"), predicted("abstain")),
        (predicted("cross_grain_equivalent", "rollup_1"),
         predicted("cross_grain_equivalent", "rollup_2")),
        (predicted("direct_equivalent"), predicted("non_match")),
    ]
    report = report_for("constructed-one", pairs, predictions)
    project = report["input"]["source_manifest_sha256"]
    entries = [adjudicated(project, pairs[0], "non_match"),
               adjudicated(project, pairs[1], "direct_equivalent"),
               adjudicated(project, pairs[4], "cross_grain_equivalent", "rollup_1"),
               {"project_key": project, "left_id": "c", "right_id": "d",
                "evidence_status": "needs_review", "label": None,
                "missing_evidence": "Unresolved constructed source"}]
    ref = {"schema_version": 1, "scope": "independently_adjudicated_source_linked",
           "entries": entries}
    result = evaluate([report], ref)
    assert result["pair_frame_denominator"] == 6
    assert result["paired_decided_pairs"] == 5
    assert result["hypothesis_test_status"] == "untestable"
    source, baseline = result["methods_summary"][A], result["methods_summary"][B]
    assert (source["decided_pairs"], baseline["decided_pairs"]) == (6, 5)
    assert source["equivalence_assertions_on_paired_decisions"] == 4
    assert source["unsafe_assertions"] == 1 and source["supported_assertions"] == 2
    assert source["unsupported_unknown_reference"] == 1
    assert source["primary_common_decided_pair_denominator"] == 5
    assert source["observed_unsafe_per_common_decided_pair"] == 1 / 5
    assert source["unsafe_per_equivalence_assertion"] == 1 / 4
    assert baseline["equivalence_assertions_on_paired_decisions"] == 2
    assert baseline["unsafe_assertions"] == 1
    assert baseline["unsupported_unknown_transformation"] == 1
    assert baseline["observed_unsafe_per_common_decided_pair"] == 1 / 5
    assert baseline["unsafe_per_equivalence_assertion"] == 1 / 2
    assert source["rate_interpretation"] == baseline["rate_interpretation"] == \
        "observed_lower_bound_unknown_reference"
    assert source["adjudicated_assertion_denominator"] == 3
    assert baseline["adjudicated_assertion_denominator"] == 1

    tentative = deepcopy(ref)
    tentative["entries"][-1]["label"] = "direct_equivalent"
    tentative_result = evaluate([report], tentative)
    tentative_source = tentative_result["methods_summary"][A]
    assert tentative_result["source_linked_adjudicated_reference_pairs"] == 3
    assert tentative_source["supported_assertions"] == 2
    assert tentative_source["unsafe_assertions"] == 1
    assert tentative_source["unsupported_unknown_reference"] == 1
    assert tentative_result["hypothesis_test_status"] == "untestable"
    incomplete = deepcopy(tentative)
    del incomplete["entries"][-1]["missing_evidence"]
    must_fail(lambda: evaluate([report], incomplete), "tentative label without missing evidence accepted")
    incomplete = deepcopy(tentative)
    incomplete["entries"][-1]["label"] = "invented_label"
    must_fail(lambda: evaluate([report], incomplete), "unknown tentative label accepted")

    incomplete = deepcopy(ref)
    incomplete["entries"][0]["source_links"] = incomplete["entries"][0]["source_links"][:1]
    must_fail(lambda: evaluate([report], incomplete), "one-sided source citation accepted")
    incomplete = deepcopy(ref)
    incomplete["entries"][0]["adjudicator_code"] = "r1"
    must_fail(lambda: evaluate([report], incomplete), "reviewer self-adjudication accepted")
    incomplete = deepcopy(report)
    del incomplete["project_identity"]
    must_fail(lambda: evaluate([incomplete], ref), "sufficient gold without pinned project identity accepted")
    incomplete = deepcopy(report)
    incomplete["project_identity"]["commit"] = "b" * 40
    must_fail(lambda: evaluate([incomplete], ref), "reference commit from another project accepted")
    incomplete = deepcopy(report)
    incomplete["method_inputs"][B]["packet_sha256"] = "0" * 64
    must_fail(lambda: evaluate([incomplete]), "different I1 input accepted")
    incomplete = deepcopy(report)
    incomplete["rows"][0]["i1"][A]["semantic_decision"] = "unsupported_gold_label"
    must_fail(lambda: evaluate([incomplete]), "unknown method decision accepted")
    must_fail(lambda: evaluate([report, deepcopy(report)]), "same project counted twice")

    no_gold = evaluate([report])
    assert no_gold["source_linked_adjudicated_reference_pairs"] == 0
    assert no_gold["hypothesis_test_status"] == "untestable"
    assert no_gold["methods_summary"][A]["unsafe_assertions"] == 0
    assert no_gold["methods_summary"][A]["unsupported_unknown_reference"] == 4

    empty_eq = report_for("constructed-none", [("x", "y")],
                          [(predicted("non_match"), predicted("related"))])
    no_assertions = evaluate([empty_eq])
    for item in no_assertions["methods_summary"].values():
        assert item["observed_unsafe_per_common_decided_pair"] == 0
        assert item["unsafe_per_equivalence_assertion"] is None

    # Threshold control: two constructed projects, 10 independently described
    # pairs per project. This exercises the gate without creating real gold.
    counted_reports, counted_entries = [], []
    for name in ("constructed-two-a", "constructed-two-b"):
        ten = [(f"a{i}", f"b{i}") for i in range(10)]
        target = report_for(name, ten, [(predicted("direct_equivalent"),
                                         predicted("direct_equivalent")) for _ in ten])
        counted_reports.append(target)
        counted_entries.extend(adjudicated(target["input"]["source_manifest_sha256"],
                                            pair, "direct_equivalent") for pair in ten)
    counted_ref = {"schema_version": 1,
                   "scope": "independently_adjudicated_source_linked",
                   "entries": counted_entries}
    assert evaluate(counted_reports, counted_ref)["hypothesis_test_status"] == \
        "eligible_for_separate_predeclared_analysis"
    same_repository = deepcopy(counted_reports)
    same_repository[1]["project_identity"]["repository"] = \
        same_repository[0]["project_identity"]["repository"]
    assert evaluate(same_repository, counted_ref)["hypothesis_test_status"] == "untestable"
    one_project = report_for("constructed-threshold", [(f"a{i}", f"b{i}") for i in range(20)],
                             [(predicted("direct_equivalent"), predicted("direct_equivalent"))
                              for _ in range(20)])
    one_ref = {"schema_version": 1, "scope": "independently_adjudicated_source_linked",
               "entries": [adjudicated(one_project["input"]["source_manifest_sha256"],
                                        pair, "direct_equivalent")
                           for pair in one_project["i1_packet"]["pair_ids"]]}
    assert evaluate([one_project], one_ref)["hypothesis_test_status"] == "untestable"
    print("PASS: constructed paired denominators, unknowns, contradictions, same-I1 identity and thresholds")


def check_development_report() -> None:
    report = json.loads(Path(DEFAULT_REPORT).read_text(encoding="utf-8"))
    result = evaluate([report])
    assert result["pair_frame_denominator"] == 496
    assert result["paired_decided_pairs"] == 0
    assert result["hypothesis_test_status"] == "untestable"
    for method in (A, B):
        item = result["methods_summary"][method]
        assert item["decided_pairs"] == 0 and item["unsafe_assertions"] == 0
        assert item["observed_unsafe_per_common_decided_pair"] is None
        assert item["unsafe_per_equivalence_assertion"] is None
    print("PASS: existing development I1 outputs, 496 pairs, zero common decisions, untestable")


if __name__ == "__main__":
    check_constructed()
    check_development_report()
