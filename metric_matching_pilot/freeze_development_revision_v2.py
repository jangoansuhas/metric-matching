#!/usr/bin/env python3
"""Append-only second revision after independent boundary review.

The first post-snapshot addendum remains immutable; byte-identical superseded
files are preserved under development_revision_history/post_snapshot_v1.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum_v2.json"
CURRENT = (
    "freeze_development_revision_v2.py",
    "run_portable_development_methods.py",
    "verify_portable_boundary.py",
    "portable_jaffle_decisions.json",
    "portable_jaffle_decisions.md",
    "verify_heldout_search_frame.py",
)
HISTORY = ROOT / "development_revision_history" / "post_snapshot_v1"
FRAME = ROOT / "heldout_search_capture" / "attempt-20260928T020324Z-1c3dd1fe"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    prior = ROOT / "post_snapshot_development_addendum.json"
    first = json.loads(prior.read_bytes())
    original = ROOT / "development_snapshot_freeze.json"
    if sha(original) != first["previous_snapshot_sha256"]:
        raise ValueError("Original snapshot changed")
    superseded = (
        "run_portable_development_methods.py", "verify_portable_boundary.py",
        "portable_jaffle_decisions.json", "portable_jaffle_decisions.md",
    )
    for name in superseded:
        if sha(HISTORY / name) != first["files_sha256"][name]:
            raise ValueError(f"First addendum's original bytes not preserved: {name}")
    for name, expected in first["files_sha256"].items():
        path = HISTORY / name if name in superseded else ROOT / name
        if sha(path) != expected:
            raise ValueError(f"First addendum's source changed: {name}")
    frame = json.loads((FRAME / "manifest.json").read_bytes())
    if (frame["status"] != "finalized" or frame["unavailable_ref_count"] != 0
            or frame["precommit_sha256"] != first["files_sha256"]["heldout_search_precommit.json"]):
        raise ValueError("Search manifest is not the complete precommitted frame")
    report = json.loads((ROOT / "portable_jaffle_decisions.json").read_bytes())
    if (report["input_sha256"] != sha(ROOT / "portable_jaffle_packet.json")
            or report["cards"] != 23 or report["pairs"] != 253
            or any(v["counts"] != {"abstain": 253} for v in report["methods"].values())):
        raise ValueError("Revised development report differs from expected abstentions")
    return {
        "schema_version": 2,
        "scope": "development_revision_and_metadata_frame_only_no_heldout_source_or_accuracy",
        "previous_addendum_sha256": sha(prior),
        "original_snapshot_sha256": sha(original),
        "archived_v1_sha256": {name: sha(HISTORY / name) for name in superseded},
        "current_files_sha256": {name: sha(ROOT / name) for name in CURRENT},
        "search_frame_manifest_sha256": sha(FRAME / "manifest.json"),
        "search_frame_report": str(FRAME.relative_to(ROOT) / "report.md"),
        "reason": "Reviewer found SUM/MEDIAN and forged-compiled-location promotion and nested grouping payload; YAML carrier is now always unresolved and compiled paths are bound to provenance.",
        "development_checks": [
            "freeze_development_snapshot.py --check",
            "verify_portable_boundary.py",
            "run_portable_development_methods.py --check on pinned Jaffle packet",
            "ast_source_baseline.py --check with sqlglot==30.20.0",
            "verify_heldout_search_frame.py on finalized metadata attempt",
        ],
        "heldout_gate": "blocked_pending_generic_compiled_source_and_SQL_aggregate_extraction_protocol",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument("--write", action="store_true")
    choices.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = snapshot()
    if args.write:
        if OUT.exists():
            raise ValueError("Second addendum exists; never overwrite a checkpoint")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
        print("Recorded dated v2 development revision and metadata cross-reference")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        timestamp = saved.pop("recorded_at_utc", None)
        if not timestamp or fresh != saved:
            raise ValueError("Second development addendum differs from current files")
        print("Development v2 revision verified; held-out source gate remains blocked")


if __name__ == "__main__":
    main()
