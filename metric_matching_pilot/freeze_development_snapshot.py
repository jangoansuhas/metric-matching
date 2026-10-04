#!/usr/bin/env python3
"""Record or verify the fixed development implementation before new test code.

This hashes local development artifacts; it does not select test repositories,
judge labels, or claim the GTM-specific adapter is deployable on a new project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "development_snapshot_freeze.json"
FILES = (
    "freeze_development_snapshot.py",
    "heldout_sampling_protocol.md",
    "evaluation_contract.md",
    "annotation_schema.json",
    "conditional_method_contract.md",
    "extract_dbt_metric_branches.py",
    "trace_compiled_metric_fields.py",
    "build_conditional_evidence.py",
    "conditional_evidence_packet.json",
    "normalized_sql_lineage_baseline.py",
    "normalized_sql_lineage_report.json",
    "constraint_aware_baseline.py",
    "constraint_aware_report.json",
    "conditional_decision_method.py",
    "conditional_decision_report.json",
    "compare_conditional_development.py",
    "conditional_development_comparison.json",
)
METHOD_REPORTS = (
    "normalized_sql_lineage_report.json",
    "constraint_aware_report.json",
    "conditional_decision_report.json",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def snapshot() -> dict:
    packet_raw = (ROOT / "conditional_evidence_packet.json").read_bytes()
    packet = json.loads(packet_raw)
    ids = [card["id"] for card in packet["cards"]]
    pairs = {(p["left_id"], p["right_id"]) for p in packet["pairs"]}
    if len(ids) != len(set(ids)) or len(ids) != 11 or len(pairs) != 55:
        raise ValueError("Development packet is no longer the 11-card/55-pair universe")
    reports = {}
    for name in METHOD_REPORTS:
        report = json.loads((ROOT / name).read_bytes())
        r_pairs = {(r["left_id"], r["right_id"]) for r in report["results"]}
        if report["input_sha256"] != sha(packet_raw) or r_pairs != pairs or len(report["results"]) != 55:
            raise ValueError(f"Incomplete or changed same-input report: {name}")
        reports[report["method"]] = {
            "file": name,
            "counts": report["counts"],
            "needs_review": sum(r["evidence_status"] == "needs_review" for r in report["results"]),
        }
    if len(reports) != 3 or any(v["needs_review"] != 55 for v in reports.values()):
        raise ValueError("Unexpected method inventory or status")
    comparison = json.loads((ROOT / "conditional_development_comparison.json").read_bytes())
    if comparison["common_universe"] != {
        "packet_sha256": sha(packet_raw), "cards": 11, "pairs": 55
    } or set(comparison["methods"]) != set(reports):
        raise ValueError("Development comparison no longer uses these three reports")
    return {
        "schema_version": 1,
        "scope": "development_implementation_snapshot_not_heldout_registration_or_accuracy",
        "packet_sha256": sha(packet_raw),
        "cards": 11, "unordered_pairs": 55,
        "files_sha256": {name: sha((ROOT / name).read_bytes()) for name in FILES},
        "methods": reports,
        "input_budgets": {
            "full_context": "identical I1 packet bytes for all three classifiers; every one of 55 pairs",
            "name_only": "earlier I0 rankers are separate limited-input diagnostics",
            "rows": "GTM/Jaffle observations checked only after method outputs; no row access in classifier",
            "llm": "not run in this same-input comparison; no prompt or API budget frozen",
        },
        "fixed_decision_rules": {
            "relationship_output": "direct/conditional/scope/related candidate or abstain, never unconditional equivalence",
            "evidence_output": "needs_review for all 55 development results",
            "conditional_rollup": "source-linked additive month to window candidate only when grouping loses the month key one-to-one; unresolved time, row membership, NULL/zero, grouping levels, rounding, units and snapshot remain conditions",
            "thresholds": "none; deterministic source/shape gates for these classifiers",
        },
        "holdout_readiness": {
            "status": "blocked_pending_selection_manifest_and_generic_adapter",
            "why": "The packet builder and classifiers currently require 11 GTM-specific cards and 55 pairs; no generic new-project extraction/classification path or held-out search frame is frozen.",
            "rule": "Any code/decision revision after this snapshot needs a dated new freeze, reason and development-only verification before opening held-out source; once opened, preserve the original snapshot and report protocol deviations.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="record one dated local development snapshot")
    action.add_argument("--check", action="store_true", help="verify saved snapshot without writing")
    args = parser.parse_args()
    fresh = snapshot()
    if args.write:
        if OUT.exists():
            raise ValueError("Snapshot exists; archive it before recording a dated revision")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Recorded development snapshot at {fresh['recorded_at_utc']}")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        timestamp = saved.pop("recorded_at_utc", None)
        if not timestamp or saved != fresh:
            raise ValueError("Saved development snapshot differs from current implementation")
        print("Development snapshot hashes and same-input reports verified; held-out gate remains blocked")


if __name__ == "__main__":
    main()
