#!/usr/bin/env python3
"""Append-only record of post-snapshot development adapters and comparators.

This checkpoint is development evidence, not a held-out source selection or a
pre-registration. Never overwrite an existing addendum or original snapshot.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum.json"
FILES = (
    "freeze_post_snapshot_addendum.py",
    "extract_portable_dbt_yaml.py",
    "portable_jaffle_packet.json",
    "portable_jaffle_report.json",
    "portable_jaffle_report.md",
    "run_portable_development_methods.py",
    "verify_portable_boundary.py",
    "portable_jaffle_decisions.json",
    "portable_jaffle_decisions.md",
    "ast_source_baseline.py",
    "ast_source_baseline_report.json",
    "ast_source_baseline_report.md",
    "human_annotation_kit.md",
    "heldout_search_precommit.json",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    previous = ROOT / "development_snapshot_freeze.json"
    if not previous.exists():
        raise ValueError("Original development snapshot missing")
    packet = ROOT / "portable_jaffle_packet.json"
    report = json.loads((ROOT / "portable_jaffle_decisions.json").read_text(encoding="utf-8"))
    ast = json.loads((ROOT / "ast_source_baseline_report.json").read_text(encoding="utf-8"))
    if (report["input_sha256"] != digest(packet) or report["cards"] != 23
            or report["pairs"] != 253 or
            any(method["counts"] != {"abstain": 253}
                for method in report["methods"].values())):
        raise ValueError("Portable development report has unexpected input or decisions")
    return {
        "schema_version": 1,
        "scope": "post_snapshot_development_addendum_no_heldout_claim",
        "previous_snapshot_sha256": digest(previous),
        "files_sha256": {name: digest(ROOT / name) for name in FILES},
        "portable_project": "pinned_jaffle_shop_development_source_yaml_only",
        "portable_cards": 23,
        "portable_pairs": 253,
        "ast_input_sha256": ast["input_sha256"],
        "checks": [
            "freeze_development_snapshot.py --check",
            "verify_portable_boundary.py",
            "extract_portable_dbt_yaml.py --check on pinned Jaffle Shop",
            "run_portable_development_methods.py --check",
            "ast_source_baseline.py --check with sqlglot==30.20.0",
        ],
        "holdout_status": "blocked_until_complete_dated_search_frame_and_fixed_generic_compiled_source_adapter",
        "reason": "Separate portable YAML inventory and AST comparator were built after the original GTM-specific snapshot; retain both revisions and development-only outcomes.",
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
            raise ValueError("Addendum exists; never overwrite an archived checkpoint")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
        print("Recorded append-only development addendum; held-out gate remains blocked")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        timestamp = saved.pop("recorded_at_utc", None)
        if not timestamp or fresh != saved:
            raise ValueError("Post-snapshot development addendum differs from current files")
        print("Append-only development addendum hashes verified; held-out gate remains blocked")


if __name__ == "__main__":
    main()
