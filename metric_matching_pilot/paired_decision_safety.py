#!/usr/bin/env python3
"""Descriptive safety accounting for two methods on identical I1 pair frames.

Examples:
  python3 -B paired_decision_safety.py
  python3 -B paired_decision_safety.py --report same_input_a.json \
      --report same_input_b.json --reference locked_adjudication.json

Each report has the generic_i1_same_input_report.json shape: a canonical
``i1_packet``, matching method_inputs, and rows with two I1 semantic_decisions.
The project key is the report's source_manifest_sha256, not a user-supplied
partition of one project. An optional report ``project_identity`` object with
``repository`` (owner/repo) and ``commit`` (40-character SHA) is required for
every sufficient reference and to count distinct repositories for the
two-project testability gate; distinct manifests alone do not establish
distinct projects. Only pairs *both* methods
decide enter the paired safety comparison. Syntax/review signals and I0 name
scores are never labels.

Optional reference JSON shape (the metadata is asserted by its provider; this
script cannot authenticate reviewer identities or validate cited source bytes):
{
  "schema_version": 1,
  "scope": "independently_adjudicated_source_linked",
  "entries": [{
    "project_key": "<source_manifest_sha256>",
    "left_id": "<first packet ID>", "right_id": "<second packet ID>",
    "evidence_status": "sufficient", "label": "direct_equivalent",
    "repo_commit": "<40-character commit SHA>",
    "reviewer_codes": ["reviewer_a", "reviewer_b"],
    "adjudicator_code": "adjudicator_c", "blinded_to_methods": true,
    "source_links": [
      {"side": "left", "path": "models/a.yml", "line_start": 1,
       "line_end": 4, "repo_commit": "<same commit SHA>"},
      {"side": "right", "path": "models/b.yml", "line_start": 2,
       "line_end": 5, "repo_commit": "<same commit SHA>"}
    ]
  }]
}

For cross_grain_equivalent, the reference and prediction additionally need a
matching, nonempty ``transformation_id`` to count as supported. A missing or
different transformation is unsupported_unknown, not a verified contradiction.
An entry with evidence_status needs_review requires missing_evidence and may
carry a tentative known relationship label or null. Neither is sufficient
evidence, even when the tentative label agrees with a method prediction.
No reference is loaded unless --reference is explicitly supplied. Output is
JSON to stdout; no input or report file is modified.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "generic_i1_same_input_report.json"
LABELS = frozenset({"direct_equivalent", "cross_grain_equivalent",
                    "temporal_or_scope_variant", "conflicting_definition",
                    "related", "non_match"})
EQUIVALENCE = frozenset({"direct_equivalent", "cross_grain_equivalent"})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
MIN_ASSERTIONS_PER_METHOD = 20
MIN_PROJECTS = 2


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def pair_key(left: str, right: str) -> tuple[str, str]:
    require(isinstance(left, str) and isinstance(right, str) and
            left < right, "Pair IDs must be distinct and in canonical order")
    return left, right


def prepare_reports(reports: list[dict], methods: tuple[str, str]) -> tuple[dict, dict, list[dict]]:
    require(reports, "At least one same-I1 report is required")
    require(methods[0] != methods[1], "Select two distinct I1 methods")
    project_rows: dict[str, set[tuple[str, str]]] = {}
    project_identities = {}
    flattened = []
    for report in reports:
        require(isinstance(report, dict) and report.get("schema_version") == 1,
                "Unexpected same-I1 report schema")
        project = report.get("input", {}).get("source_manifest_sha256")
        require(isinstance(project, str) and SHA256.fullmatch(project) is not None,
                "Report lacks a source-manifest SHA256 project identity")
        require(project not in project_rows, "Duplicate project identity; cannot split one project")
        identity = report.get("project_identity")
        if identity is not None:
            require(isinstance(identity, dict) and
                    isinstance(identity.get("repository"), str) and
                    REPOSITORY.fullmatch(identity["repository"]) is not None and
                    isinstance(identity.get("commit"), str) and
                    COMMIT.fullmatch(identity["commit"]) is not None,
                    "project_identity needs repository owner/name and pinned commit")
            project_identities[project] = identity
        packet = report.get("i1_packet")
        require(isinstance(packet, dict) and isinstance(packet.get("pair_ids"), list) and
                isinstance(packet.get("declarations"), list) and
                report.get("i1_packet_sha256") == digest(packet),
                "I1 packet missing or its canonical hash does not match")
        pairs = packet["pair_ids"]
        pair_hash = digest(pairs)
        require(report.get("pair_universe", {}).get("all_pair_ids_sha256") == pair_hash and
                report.get("pair_universe", {}).get("all_unordered_pairs") == len(pairs),
                "Pair universe identity or count does not match packet")
        declaration_ids = [d.get("id") for d in packet["declarations"] if isinstance(d, dict)]
        require(len(set(declaration_ids)) == len(packet["declarations"]) and
                all(isinstance(i, str) for i in declaration_ids),
                "Invalid or duplicate declarations")
        ids = set(declaration_ids)
        checked_pairs = []
        for pair in pairs:
            require(isinstance(pair, list) and len(pair) == 2, "Malformed packet pair")
            key = pair_key(*pair)
            require(set(key) <= ids, "Pair references an unknown declaration")
            checked_pairs.append(key)
        require(len(set(checked_pairs)) == len(checked_pairs), "Duplicate pair in packet")
        project_rows[project] = set(checked_pairs)
        rows = report.get("rows")
        require(isinstance(rows, list) and len(rows) == len(pairs),
                "Report row count differs from complete I1 pair frame")
        method_inputs = report.get("method_inputs", {})
        for method in methods:
            meta = method_inputs.get(method, {})
            require(meta.get("input_level") == "I1" and
                    meta.get("packet_sha256") == report["i1_packet_sha256"] and
                    meta.get("pair_ids_sha256") == pair_hash and
                    meta.get("pair_count") == len(pairs) and
                    isinstance(meta.get("version"), str) and meta["version"],
                    f"Method {method} did not use the same complete I1 packet")
        for expected, row in zip(checked_pairs, rows):
            require(isinstance(row, dict) and
                    pair_key(row.get("left_id"), row.get("right_id")) == expected,
                    "Report row identity or order differs from packet")
            i1 = row.get("i1", {})
            decisions = {}
            for method in methods:
                decision = i1.get(method, {})
                require(isinstance(decision, dict) and
                        decision.get("semantic_decision") in (LABELS | {"abstain"}),
                        f"Method {method} has missing or unrecognized semantic decision")
                decisions[method] = decision
            flattened.append({"project_key": project, "pair": expected,
                              "decisions": decisions})
        reported_decisions = report.get("coverage", {}).get("i1_semantic_decisions_per_method", {})
        for method in methods:
            require(reported_decisions.get(method) == sum(
                row["decisions"][method]["semantic_decision"] != "abstain"
                for row in flattened if row["project_key"] == project),
                f"Method {method} coverage counter disagrees with rows")
    return project_rows, project_identities, flattened


def prepare_reference(reference: dict | None, project_rows: dict,
                      project_identities: dict) -> dict:
    if reference is None:
        return {}
    require(isinstance(reference, dict) and reference.get("schema_version") == 1 and
            reference.get("scope") == "independently_adjudicated_source_linked" and
            isinstance(reference.get("entries"), list),
            "Reference requires independent adjudication provenance and schema version 1")
    checked = {}
    for entry in reference["entries"]:
        require(isinstance(entry, dict), "Malformed reference entry")
        project = entry.get("project_key")
        key = pair_key(entry.get("left_id"), entry.get("right_id"))
        require(project in project_rows and key in project_rows[project],
                "Reference pair does not occur in supplied project I1 frame")
        identity = (project, key)
        require(identity not in checked, "Duplicate reference pair")
        status = entry.get("evidence_status")
        require(status in ("sufficient", "needs_review"), "Unknown reference evidence status")
        if status == "needs_review":
            tentative = entry.get("label")
            require((tentative is None or
                     (isinstance(tentative, str) and tentative in LABELS)) and
                    isinstance(entry.get("missing_evidence"), str) and entry["missing_evidence"].strip(),
                    "Unresolved reference needs missing_evidence and null or known tentative label")
        else:
            require(entry.get("label") in LABELS, "Sufficient reference needs a known relationship")
            commit = entry.get("repo_commit")
            require(isinstance(commit, str) and COMMIT.fullmatch(commit) is not None,
                    "Adjudicated reference requires a pinned source commit")
            require(project in project_identities,
                    "Sufficient reference requires pinned project_identity in the report")
            require(commit == project_identities[project]["commit"],
                    "Reference commit disagrees with report repository identity")
            codes = entry.get("reviewer_codes")
            adjudicator = entry.get("adjudicator_code")
            require(isinstance(codes, list) and len(codes) == 2 and
                    all(isinstance(code, str) and code.strip() for code in codes) and
                    len(set(codes)) == 2 and
                    isinstance(adjudicator, str) and adjudicator.strip() and
                    adjudicator not in codes and entry.get("blinded_to_methods") is True,
                    "Reference needs two distinct blind reviewers and distinct adjudicator")
            links = entry.get("source_links")
            require(isinstance(links, list) and
                    {"left", "right"} <= {link.get("side") for link in links
                                          if isinstance(link, dict)},
                    "Sufficient reference needs citations for both definitions")
            for link in links:
                require(isinstance(link, dict) and link.get("side") in {"left", "right"} and
                        isinstance(link.get("path"), str) and link["path"].strip() and
                        type(link.get("line_start")) is int and
                        type(link.get("line_end")) is int and
                        1 <= link["line_start"] <= link["line_end"] and
                        link.get("repo_commit") == commit,
                        "Source citation needs a path, exact lines, and pinned commit")
            if entry["label"] == "cross_grain_equivalent":
                require(isinstance(entry.get("transformation_id"), str) and
                        entry["transformation_id"].strip(),
                        "Cross-grain reference requires a specified transformation")
        checked[identity] = entry
    return checked


def equivalence_outcome(prediction: dict, reference: dict | None) -> str:
    """Contradiction requires sufficient source-linked independently adjudicated evidence."""
    if reference is None or reference["evidence_status"] != "sufficient":
        return "unsupported_unknown_reference"
    claimed = prediction["semantic_decision"]
    truth = reference["label"]
    if claimed != truth:
        return "unsafe_contradicted_by_reference"
    if claimed == "cross_grain_equivalent":
        if (not isinstance(prediction.get("transformation_id"), str) or
                not prediction["transformation_id"].strip() or
                prediction["transformation_id"] != reference["transformation_id"]):
            return "unsupported_unknown_transformation"
    return "supported_by_reference"


def evaluate(reports: list[dict], reference: dict | None = None,
             methods: tuple[str, str] = ("source_guided_conditional", "constraint_aware")) -> dict:
    project_rows, project_identities, rows = prepare_reports(reports, methods)
    gold = prepare_reference(reference, project_rows, project_identities)
    paired = [row for row in rows if all(
        row["decisions"][method]["semantic_decision"] != "abstain" for method in methods)]
    counts = {}
    for method in methods:
        decided = sum(row["decisions"][method]["semantic_decision"] != "abstain"
                      for row in rows)
        outcomes = Counter()
        projects = set()
        for row in paired:
            prediction = row["decisions"][method]
            if prediction["semantic_decision"] in EQUIVALENCE:
                outcome = equivalence_outcome(prediction,
                    gold.get((row["project_key"], row["pair"])))
                outcomes[outcome] += 1
                if (outcome in ("supported_by_reference", "unsafe_contradicted_by_reference") and
                        row["project_key"] in project_identities):
                    projects.add(project_identities[row["project_key"]]["repository"])
        verified = outcomes["supported_by_reference"] + outcomes["unsafe_contradicted_by_reference"]
        equivalence_count = sum(outcomes.values())
        unknown_count = (outcomes["unsupported_unknown_reference"] +
                         outcomes["unsupported_unknown_transformation"])
        counts[method] = {
            "decided_pairs": decided, "coverage_denominator_pairs": len(rows),
            "coverage": decided / len(rows) if rows else None,
            "equivalence_assertions_on_paired_decisions": equivalence_count,
            "supported_assertions": outcomes["supported_by_reference"],
            "unsafe_assertions": outcomes["unsafe_contradicted_by_reference"],
            "unsupported_unknown_reference": outcomes["unsupported_unknown_reference"],
            "unsupported_unknown_transformation": outcomes["unsupported_unknown_transformation"],
            "primary_common_decided_pair_denominator": len(paired),
            "observed_unsafe_per_common_decided_pair": outcomes["unsafe_contradicted_by_reference"] / len(paired)
                if paired else None,
            "unsafe_per_equivalence_assertion": outcomes["unsafe_contradicted_by_reference"] / equivalence_count
                if equivalence_count else None,
            "rate_interpretation": ("undefined_no_common_decisions" if not paired else
                                    "observed_lower_bound_unknown_reference" if unknown_count else
                                    "complete_within_supplied_paired_frame"),
            "adjudicated_assertion_denominator": verified,
            "projects_with_adjudicated_equivalence_assertions": len(projects),
        }
    reasons = []
    if not any(entry["evidence_status"] == "sufficient" for entry in gold.values()):
        reasons.append("no_source_linked_independently_adjudicated_reference")
    for method in methods:
        item = counts[method]
        if item["adjudicated_assertion_denominator"] < MIN_ASSERTIONS_PER_METHOD:
            reasons.append(f"{method}:fewer_than_20_adjudicated_equivalence_assertions")
        if item["projects_with_adjudicated_equivalence_assertions"] < MIN_PROJECTS:
            reasons.append(f"{method}:fewer_than_two_projects_with_adjudicated_assertions")
    return {
        "schema_version": 1, "analysis": "descriptive_same_I1_paired_decision_safety",
        "methods": list(methods), "projects": len(project_rows),
        "project_keys": sorted(project_rows),
        "distinct_declared_repositories": len({p["repository"] for p in project_identities.values()}),
        "pair_frame_denominator": len(rows),
        "paired_decided_pairs": len(paired),
        "paired_coverage": len(paired) / len(rows) if rows else None,
        "source_linked_adjudicated_reference_pairs": sum(
            entry["evidence_status"] == "sufficient" for entry in gold.values()),
        "methods_summary": counts,
        "hypothesis_test_status": "untestable" if reasons else "eligible_for_separate_predeclared_analysis",
        "untestable_reasons": reasons,
        "rules": {
            "minimum_adjudicated_equivalence_assertions_per_method": MIN_ASSERTIONS_PER_METHOD,
            "minimum_projects_with_adjudicated_assertions_per_method": MIN_PROJECTS,
            "paired_comparison_frame": "intersection_of_pairs_both_methods_decide",
            "unsafe_definition": "direct/cross-grain assertion contradicted by a sufficient, source-linked, independently adjudicated reference",
            "primary_rate_denominator": "all common decided pairs, identical for both methods",
            "secondary_rate_denominator": "all equivalence assertions issued by that method on common decided pairs; undefined when zero",
            "unknown_reference_policy": "unknown assertions remain in denominators; observed unsafe rates are lower bounds until their reference evidence is resolved",
        },
        "limitations": [
            "No pair ranking, selective-risk curve, significance test, or superiority claim is produced.",
            "Reference metadata is checked structurally but reviewer independence and cited source content cannot be authenticated by this evaluator.",
            "Unknown reference or unverified transformation never counts as safe or unsafe.",
            "Pair completeness and project independence beyond declared repository identities are not established here.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path, action="append",
                        help="Combined same-I1 JSON report; repeat for distinct projects")
    parser.add_argument("--reference", type=Path,
                        help="Optional independent, source-linked, third-person-adjudicated JSON")
    parser.add_argument("--method-a", default="source_guided_conditional")
    parser.add_argument("--method-b", default="constraint_aware")
    args = parser.parse_args()
    reports = [json.loads(path.read_text(encoding="utf-8"))
               for path in (args.report or [DEFAULT_REPORT])]
    reference = (json.loads(args.reference.read_text(encoding="utf-8"))
                 if args.reference else None)
    result = evaluate(reports, reference, (args.method_a, args.method_b))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
