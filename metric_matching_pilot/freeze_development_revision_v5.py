#!/usr/bin/env python3
"""Append-only checkpoint for reviewed, development-only dbt adapter probes.

This records eligibility and compiled-MODEL provenance evidence without
certifying metric-expression lineage, same-input evaluation, or held-out access.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "post_snapshot_development_addendum_v5.json"
PREVIOUS = ROOT / "post_snapshot_development_addendum_v4.json"
FILES = (
    "freeze_development_revision_v5.py",
    "generic_adapter_bridge_contract_20260928.md",
    "generic_metric_eligibility.py",
    "generic_metric_eligibility_negative.yml",
    "generic_metric_eligibility_report.json",
    "generic_metric_eligibility_report.md",
    "generic_metric_eligibility_manifest_report.json",
    "generic_metric_eligibility_manifest_report.md",
    "generic_compiled_provenance.py",
    "generic_compiled_provenance_report.json",
    "generic_compiled_provenance_report.md",
    "generic_adapter_parallel_review_20260928.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot() -> dict:
    source = json.loads((ROOT / "generic_metric_eligibility_report.json").read_text())
    manifest = json.loads((ROOT / "generic_metric_eligibility_manifest_report.json").read_text())
    compiled = json.loads((ROOT / "generic_compiled_provenance_report.json").read_text())
    source_counts, manifest_counts = source["coverage"], manifest["coverage"]
    if (source_counts["declared_metrics"], source_counts["declared_measures"],
        source_counts["primary_metric_pairs"], source_counts["all_declared_scalar_pairs"]) != (23, 0, 253, 253):
        raise ValueError("Source YAML development frame changed")
    if (manifest_counts["declared_metrics"], manifest_counts["declared_measures"],
        manifest_counts["primary_metric_pairs"], manifest_counts["all_declared_scalar_pairs"]) != (19, 13, 171, 496):
        raise ValueError("Manifest development frame changed")
    if (source["provenance"]["repo_commit"] != "5beb145b00f5465ec759cfcdd9745e858818cf95"
            or manifest["provenance"]["repo_commit"] != "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
            or manifest["provenance"]["manifest"]["build_commit_verified"] is not False):
        raise ValueError("Eligibility provenance changed")
    if any(card["compiled_provenance"] is not None for card in source["candidates"] + manifest["candidates"]):
        raise ValueError("An unverified metric was promoted to compiled provenance")
    cases = compiled["cases"]
    if len(cases) != 2:
        raise ValueError("Expected two already inspected development projects")
    by_project = {case["expected_project"]: case for case in cases}
    if set(by_project) != {"arcline", "jaffle_shop"}:
        raise ValueError("Development project list changed")
    gtm = by_project["arcline"]["coverage"]
    jaffle = by_project["jaffle_shop"]["coverage"]
    if (gtm["models_enumerated"], gtm["model_artifact_checks_pass"],
        gtm["compiled_files_exact_manifest_code"]) != (33, 33, 33):
        raise ValueError("GTM model artifact checks changed")
    if (jaffle["models_enumerated"], jaffle["needs_review"],
        jaffle["compiled_files_exact_manifest_code"],
        jaffle["manifest_source_checksums_equal_raw_code"]) != (13, 13, 13, 0):
        raise ValueError("Jaffle model artifact checks changed")
    if compiled["metric_expression_lineage"] != "metric_expression_unverified":
        raise ValueError("Unexpected promotion of metric expression lineage")
    review = (ROOT / "generic_adapter_parallel_review_20260928.md").read_text()
    for name in FILES:
        if name.startswith("generic_") and name not in (
                "generic_adapter_parallel_review_20260928.md",
                "generic_adapter_bridge_contract_20260928.md"):
            if sha(ROOT / name) not in review:
                raise ValueError(f"Independent review does not sign current {name}")
    return {
        "schema_version": 5,
        "scope": "development_only_dbt_declaration_eligibility_and_compiled_model_artifacts",
        "previous_addendum_sha256": sha(PREVIOUS),
        "files_sha256": {name: sha(ROOT / name) for name in FILES},
        "eligibility_source_commit": source["provenance"]["repo_commit"],
        "eligibility_manifest_commit": manifest["provenance"]["repo_commit"],
        "eligibility_frames": {
            "source_yaml": {"metrics": 23, "measures": 0, "all_pairs": 253},
            "separate_manifest": {"metrics": 19, "measures": 13,
                                  "metric_pairs": 171, "all_scalar_pairs": 496},
        },
        "compiled_model_artifacts": {
            "gtm_pass": 33, "jaffle_review": 13,
            "compiled_files_exact_manifest_code": 46,
            "metric_expression_lineage": "unverified",
        },
        "heldout_gate": "blocked_no_verified_metric_expression_mapping_or_full_same_input_i1_methods",
        "reason": "Record bounded adapter coverage and independent AI review without inventing human labels, matching accuracy, or a method advantage.",
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
            raise ValueError("Revision v5 already exists; do not overwrite")
        fresh["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        OUT.write_text(json.dumps(fresh, indent=2) + "\n", encoding="utf-8")
        print("Recorded development v5; held-out source gate remains blocked")
    else:
        saved = json.loads(OUT.read_text(encoding="utf-8"))
        if not saved.pop("recorded_at_utc", None) or saved != fresh:
            raise ValueError("Development v5 differs from current files")
        print("Development v5 hashes verified; held-out source gate remains blocked")


if __name__ == "__main__":
    main()
