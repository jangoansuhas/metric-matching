#!/usr/bin/env python3
"""Append-only checkpoint for development-only generic SQL diagnostics.

This records source and baseline reports after independent review. It does not
certify a compiled adapter, complete metric universe, or held-out readiness.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum_v4.json"
PREVIOUS = ROOT / "post_snapshot_development_addendum_v3.json"
FILES = (
    "freeze_development_revision_v4.py",
    "generic_sql_inventory.py",
    "generic_sql_fixture_negative.sql",
    "generic_sql_inventory_report.json",
    "generic_sql_inventory_report.md",
    "generic_adapter_review_contract.md",
    "generic_adapter_integration_gate.md",
    "generic_same_input_baselines.py",
    "generic_same_input_baselines_report.json",
    "generic_same_input_baselines_report.md",
    "generic_same_input_baselines_review.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    inventory = json.loads((ROOT / "generic_sql_inventory_report.json").read_text())
    baseline = json.loads((ROOT / "generic_same_input_baselines_report.json").read_text())
    coverage = inventory["coverage"]
    if (coverage["views"] != 12 or coverage["outputs"] != 24
            or coverage["unordered_pairs"] != 276):
        raise ValueError("Development inventory counts changed")
    if (baseline["input"]["sha256"] != sha(ROOT / "generic_sql_inventory_report.json")):
        raise ValueError("Baseline input hash does not match inventory")
    pair_frame = baseline["pair_universe"]
    if (pair_frame.get("eligible_scalar_ids") != 12
            or pair_frame.get("unordered_pairs") != 66
            or not pair_frame.get("all_methods_same_pair_set")):
        raise ValueError("Development same-input metric pair frame is incomplete")
    return {
        "schema_version": 4,
        "scope": "generic_SQL_source_inventory_and_same_input_diagnostics_development_only",
        "previous_addendum_sha256": sha(PREVIOUS),
        "files_sha256": {name: sha(ROOT / name) for name in FILES},
        "inventory_input_sha256": inventory["input"]["sha256"],
        "baseline_pair_set_sha256": pair_frame["pair_set_sha256"],
        "coverage": {
            "raw_views": coverage["views"],
            "emitted_outputs": coverage["outputs"],
            "raw_pairs": coverage["unordered_pairs"],
            "development_metric_ids": pair_frame["eligible_scalar_ids"],
            "development_metric_pairs": pair_frame["unordered_pairs"],
        },
        "heldout_gate": "blocked_generic_compiled_provenance_and_complete_metric_eligibility_missing",
        "reason": "Record independently reviewed synthetic SQL inventory and same-input baseline diagnostic without implying gold or method superiority.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = snapshot()
    if args.write:
        if OUT.exists():
            raise ValueError("Revision v4 already exists; do not overwrite")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
        print("Recorded generic development v4; held-out source gate remains blocked")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        if not saved.pop("recorded_at_utc", None) or saved != fresh:
            raise ValueError("Generic development v4 differs from current files")
        print("Generic development v4 hashes verified; held-out gate remains blocked")


if __name__ == "__main__":
    main()
