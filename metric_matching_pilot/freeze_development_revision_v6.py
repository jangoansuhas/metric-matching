#!/usr/bin/env python3
"""Append-only v6 checkpoint: development trace and common-input diagnostics.

This hash record does not open held-out source, certify metric-expression
provenance, or convert AI review into human gold.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum_v6.json"
PREVIOUS = ROOT / "post_snapshot_development_addendum_v5.json"
FILES = (
    "freeze_development_revision_v6.py",
    "generic_v6_preimplementation_contract.md",
    "generic_metric_expression_trace.py",
    "generic_metric_expression_trace_report.json",
    "generic_metric_expression_trace_report.md",
    "generic_i1_same_input.py",
    "generic_i1_same_input_report.json",
    "generic_i1_same_input_report.md",
    "generic_v6_independent_review_20260928.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    trace = json.loads((ROOT / "generic_metric_expression_trace_report.json").read_text())
    comparison = json.loads((ROOT / "generic_i1_same_input_report.json").read_text())
    coverage = trace["coverage"]
    if (coverage["declarations"], coverage["metrics"], coverage["measures"],
        coverage["compiled_metric_expressions_verified"],
        coverage["compiled_metric_expressions_needs_review"]) != (32, 19, 13, 0, 32):
        raise ValueError("Expression trace coverage or fail-closed status changed")
    if trace["source"]["repo_commit"] != "7be2c5838dbdeca8e915d4e46db70e910753d7f6":
        raise ValueError("Trace development commit changed")
    if any(row["compiled_metric_expression_status"] != "needs_review"
           for row in trace["records"]):
        raise ValueError("Trace promoted an unverified expression")
    pair_frame = comparison["pair_universe"]
    if (pair_frame["all_declaration_ids"], pair_frame["metrics"],
        pair_frame["measures"], pair_frame["all_unordered_pairs"],
        pair_frame["primary_exposed_metric_pairs"]) != (32, 19, 13, 496, 171):
        raise ValueError("Common-input pair frame changed")
    if comparison["input"]["expression_trace_sha256"] != sha(
            ROOT / "generic_metric_expression_trace_report.json"):
        raise ValueError("I1 report is not linked to reviewed expression trace")
    if comparison["input"]["expression_trace_supplied"] is not True:
        raise ValueError("Final packet did not consume the expression trace")
    if comparison["input"]["source_manifest_sha256"] != trace["source_manifest_sha256"]:
        raise ValueError("Trace and packet manifest hashes differ")
    i1 = {k: v for k, v in comparison["method_inputs"].items()
          if v["input_level"] == "I1"}
    if set(i1) != {"normalized_ast_source", "constraint_aware", "source_guided_conditional"}:
        raise ValueError("Missing common-input I1 methods")
    if any(v["packet_sha256"] != comparison["i1_packet_sha256"] or
           v["pair_ids_sha256"] != pair_frame["all_pair_ids_sha256"] or
           v["pair_count"] != 496 for v in i1.values()):
        raise ValueError("I1 methods do not share packet bytes and pair IDs")
    if len(comparison["rows"]) != 496 or any(
            row["i1"][method]["semantic_decision"] != "abstain"
            for row in comparison["rows"] for method in i1):
        raise ValueError("Development comparisons dropped pairs or overclaimed decisions")
    review = (ROOT / "generic_v6_independent_review_20260928.md").read_text()
    for name in FILES:
        if name.startswith("generic_") and name != "generic_v6_independent_review_20260928.md":
            if sha(ROOT / name) not in review:
                raise ValueError(f"Independent review does not sign current {name}")
    return {
        "schema_version": 6,
        "scope": "public_development_only_compiled_metric_trace_and_common_i1_packet",
        "previous_addendum_sha256": sha(PREVIOUS),
        "files_sha256": {name: sha(ROOT / name) for name in FILES},
        "trace_manifest_sha256": trace["source_manifest_sha256"],
        "trace_report_sha256": comparison["input"]["expression_trace_sha256"],
        "all_pair_ids_sha256": pair_frame["all_pair_ids_sha256"],
        "shared_i1_packet_sha256": comparison["i1_packet_sha256"],
        "coverage": {"declared_ids": 32, "all_pairs": 496,
                     "compiled_metric_expressions_verified": 0,
                     "semantic_decisions_per_i1_method": 0},
        "heldout_gate": "blocked_compiled_metric_expression_and_same_revision_build_verification_missing",
        "reason": "Record complete emitted-ID packet plumbing and abstention, not effectiveness, human labels, or method superiority.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = snapshot()
    if args.write:
        if OUT.exists():
            raise ValueError("v6 checkpoint already exists; append a new revision instead")
        current["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(current, indent=2) + "\n")
        print("Recorded v6 development checkpoint; held-out source gate blocked")
    else:
        saved = json.loads(OUT.read_text())
        if not saved.pop("recorded_at_utc", None) or saved != current:
            raise ValueError("v6 checkpoint differs from final reviewed files")
        print("Verified v6 development checkpoint; held-out source gate blocked")


if __name__ == "__main__":
    main()
