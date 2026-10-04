#!/usr/bin/env python3
"""Append-only record of the pinned raw-source development tracer.

This source-link trace produces zero compiled metric decisions. The held-out
source-opening gate remains blocked until a generic compiled/aggregate path is
built and independently reviewed on development projects.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum_v3.json"
FILES = (
    "freeze_development_revision_v3.py",
    "trace_portable_development_evidence.py",
    "trace_portable_development_evidence.json",
    "trace_portable_development_evidence.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    previous = ROOT / "post_snapshot_development_addendum_v2.json"
    report = json.loads((ROOT / "trace_portable_development_evidence.json").read_bytes())
    count = report["counts"]
    if (report["provenance"]["packet_sha256"] != sha(ROOT / "portable_jaffle_packet.json")
            or count["yaml_metrics"] != 23 or count["source_sql_direct_links"] != 17
            or count["source_sql_dependency_only_links"] != 6
            or count["verified_compiled_sources"] != 0 or report["generated_decisions"]):
        raise ValueError("Trace changed or made unverified compiled/decision claims")
    for key in ("source_selection", "commit"):
        if not report["provenance"].get(key):
            raise ValueError("Trace provenance incomplete")
    return {
        "schema_version": 3,
        "scope": "pinned_raw_source_links_development_only_no_heldout_source_or_decisions",
        "previous_addendum_sha256": sha(previous),
        "files_sha256": {name: sha(ROOT / name) for name in FILES},
        "project_commit": report["provenance"]["commit"],
        "packet_sha256": report["provenance"]["packet_sha256"],
        "coverage": {"yaml_cards": 23, "direct_source_sql_files": 17,
                     "dependency_sources_only": 6, "verified_compiled": 0,
                     "generated_decisions": 0},
        "reason": "Trace raw source and YAML dependencies by immutable commit ID after independent review identified mutable HEAD and overbroad provenance wording.",
        "check": "python3 -B metric_matching_pilot/trace_portable_development_evidence.py --check",
        "heldout_gate": "blocked_generic_compiled_metric_and_SQL_aggregate_extraction_missing",
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
            raise ValueError("Revision v3 already exists; do not overwrite")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
        print("Recorded source-only development v3; held-out gate remains blocked")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        if not saved.pop("recorded_at_utc", None) or saved != fresh:
            raise ValueError("Source-only development v3 differs from current files")
        print("Source-only development v3 hashes verified; held-out gate remains blocked")


if __name__ == "__main__":
    main()
