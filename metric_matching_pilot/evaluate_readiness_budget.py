#!/usr/bin/env python3
"""Development-only, metadata-only budget plan for prospective anchor judgments.

Usage: python evaluate_readiness_budget.py /outside/repository/candidates.json
The sole input file must be a supplied JSON manifest outside this repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path


VERSION = 1
MAX_MANIFEST_BYTES = 1_000_000
MAX_PROJECTS = 50
MAX_METRICS = 10_000
MAX_TOTAL_METRICS = 100_000
MAX_ANCHORS = 100
PROJECT_RE = re.compile(r"[a-z0-9-]+/[a-z0-9._-]+@[0-9a-f]{40}\Z")
SNAPSHOT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,4})?\Z")
TOP_KEYS = {"schema_version", "manifest_kind", "candidate_snapshot_id", "projects", "budget"}
PROJECT_KEYS = {"project_key", "planned_eligible_metric_count"}
BUDGET_KEYS = {
    "total_reviewer_person_hours",
    "annotation_minutes_per_pair_per_annotator",
    "adjudication_fraction",
    "adjudication_minutes_per_case",
    "audit_fraction",
    "audit_minutes_per_case",
    "coordination_reserve_minutes",
    "target_anchors_per_project",
}
ZERO = Decimal(0)
SIXTY = Decimal(60)


class ManifestError(ValueError):
    pass


def exact_keys(obj: object, expected: set[str], where: str) -> dict:
    if not isinstance(obj, dict):
        raise ManifestError(f"{where} must be an object")
    missing, extra = expected - obj.keys(), obj.keys() - expected
    if missing or extra:
        raise ManifestError(f"{where} keys: missing={sorted(missing)}, unexpected={sorted(extra)}")
    return obj


def integer(value: object, where: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ManifestError(f"{where} must be an integer from {minimum} to {maximum}")
    return value


def decimal_string(value: object, where: str, *, positive: bool = False,
                   fraction: bool = False) -> Decimal:
    if not isinstance(value, str) or not DECIMAL_RE.fullmatch(value):
        raise ManifestError(f"{where} must be a nonnegative plain decimal string (up to 4 places)")
    number = Decimal(value)
    if positive and number <= ZERO:
        raise ManifestError(f"{where} must be positive")
    if fraction and number > 1:
        raise ManifestError(f"{where} must be at most 1")
    return number


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ManifestError(f"nonstandard JSON constant: {value}")


def load_manifest(path: str) -> dict:
    supplied = Path(path)
    if supplied.suffix != ".json":
        raise ManifestError("the supplied manifest must have a .json suffix")
    resolved = supplied.resolve(strict=True)
    repository = Path(__file__).resolve().parent
    if resolved == repository or repository in resolved.parents:
        raise ManifestError("the supplied manifest must be outside the repository")
    if not resolved.is_file():
        raise ManifestError("the supplied manifest must be a regular file")
    with resolved.open("rb") as handle:
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ManifestError("manifest exceeds the 1 MB input limit")
    try:
        manifest = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicate_keys,
                              parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ManifestError("manifest is not valid UTF-8 JSON") from exc
    except ManifestError:
        raise
    except ValueError as exc:
        raise ManifestError("manifest contains an invalid numeric literal") from exc
    return validate(manifest)


def validate(manifest: object) -> dict:
    obj = exact_keys(manifest, TOP_KEYS, "manifest")
    if type(obj["schema_version"]) is not int or obj["schema_version"] != VERSION:
        raise ManifestError("schema_version must be 1")
    if obj["manifest_kind"] != "metadata_only_pre_source":
        raise ManifestError("manifest_kind must be metadata_only_pre_source")
    if not isinstance(obj["candidate_snapshot_id"], str) or not SNAPSHOT_RE.fullmatch(
        obj["candidate_snapshot_id"]
    ):
        raise ManifestError("candidate_snapshot_id must be a short metadata identifier")
    projects = obj["projects"]
    if not isinstance(projects, list) or not 1 <= len(projects) <= MAX_PROJECTS:
        raise ManifestError(f"projects must contain 1 to {MAX_PROJECTS} candidates")
    seen_repositories = set()
    for index, project in enumerate(projects):
        project = exact_keys(project, PROJECT_KEYS, f"projects[{index}]")
        key = project["project_key"]
        if not isinstance(key, str) or not PROJECT_RE.fullmatch(key):
            raise ManifestError(f"projects[{index}].project_key must be lowercase owner/repo@40-hex-SHA")
        repository = key.split("@", 1)[0]
        if repository.rsplit("/", 1)[-1] in {".", ".."}:
            raise ManifestError(f"projects[{index}].project_key has an invalid repository name")
        if repository in seen_repositories:
            raise ManifestError(f"repeated repository in candidates: {repository}")
        seen_repositories.add(repository)
        integer(project["planned_eligible_metric_count"],
                f"projects[{index}].planned_eligible_metric_count", 0, MAX_METRICS)
    if sum(p["planned_eligible_metric_count"] for p in projects) > MAX_TOTAL_METRICS:
        raise ManifestError(f"total planned metric count must be at most {MAX_TOTAL_METRICS}")
    budget = exact_keys(obj["budget"], BUDGET_KEYS, "budget")
    integer(budget["target_anchors_per_project"], "target_anchors_per_project", 1, MAX_ANCHORS)
    decimal_string(budget["total_reviewer_person_hours"], "total_reviewer_person_hours",
                   positive=True)
    decimal_string(budget["annotation_minutes_per_pair_per_annotator"],
                   "annotation_minutes_per_pair_per_annotator", positive=True)
    for name in ("adjudication_fraction", "audit_fraction"):
        decimal_string(budget[name], name, fraction=True)
    for name, fraction_name in (("adjudication_minutes_per_case", "adjudication_fraction"),
                                ("audit_minutes_per_case", "audit_fraction")):
        decimal_string(budget[name], name, positive=Decimal(budget[fraction_name]) > ZERO)
    decimal_string(budget["coordination_reserve_minutes"], "coordination_reserve_minutes")
    return obj


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def minute_string(value: Decimal) -> str:
    return format(value, "f")


def hours_string(minutes: Decimal) -> str:
    return format((minutes / SIXTY).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), "f")


def cases(pairs: int, fraction: Decimal) -> int:
    return int((Decimal(pairs) * fraction).to_integral_value(rounding=ROUND_CEILING))


def pair_counts(n: int, anchors: int) -> tuple[int, int]:
    incidences = anchors * (n - 1)
    unique = incidences - anchors * (anchors - 1) // 2
    return incidences, unique


def costs(projects: list[dict], counts: dict[str, int], budget: dict) -> dict:
    minutes = Decimal(budget["annotation_minutes_per_pair_per_annotator"])
    adj_fraction = Decimal(budget["adjudication_fraction"])
    audit_fraction = Decimal(budget["audit_fraction"])
    annotation = ZERO
    adjudication = ZERO
    audit = ZERO
    adj_cases = 0
    audit_cases = 0
    for project in projects:
        key = project["project_key"]
        n = project["planned_eligible_metric_count"]
        _, pairs = pair_counts(n, counts[key])
        annotation += 2 * pairs * minutes
        project_adj = cases(pairs, adj_fraction)
        project_audit = cases(pairs, audit_fraction)
        adj_cases += project_adj
        audit_cases += project_audit
        adjudication += project_adj * Decimal(budget["adjudication_minutes_per_case"])
        audit += project_audit * Decimal(budget["audit_minutes_per_case"])
    coordination = Decimal(budget["coordination_reserve_minutes"]) if any(counts.values()) else ZERO
    return {
        "annotation_person_minutes": annotation,
        "adjudication_reserved_cases": adj_cases,
        "adjudication_reserve_person_minutes": adjudication,
        "audit_reserved_cases": audit_cases,
        "audit_reserve_person_minutes": audit,
        "coordination_reserve_person_minutes": coordination,
        "total_person_minutes": annotation + adjudication + audit + coordination,
    }


def pool_capacity(projects: list[dict], budget: dict, available: Decimal) -> int:
    """Conservative capacity for distinct pairs under any project allocation."""
    upper = sum(p["planned_eligible_metric_count"] *
                (p["planned_eligible_metric_count"] - 1) // 2 for p in projects)
    active_projects = sum(p["planned_eligible_metric_count"] >= 2 for p in projects)

    def reserved_cases(pairs: int, fraction: Decimal) -> int:
        if not pairs or not fraction:
            return 0
        # Sum of per-project ceilings is at most ceil(total) + active_projects - 1;
        # no project can reserve more cases than its own pair count.
        return min(pairs, cases(pairs, fraction) + min(pairs, active_projects) - 1)

    def pool_cost(pairs: int) -> Decimal:
        if not pairs:
            return ZERO
        return (
            Decimal(budget["coordination_reserve_minutes"])
            + 2 * pairs * Decimal(budget["annotation_minutes_per_pair_per_annotator"])
            + reserved_cases(pairs, Decimal(budget["adjudication_fraction"]))
            * Decimal(budget["adjudication_minutes_per_case"])
            + reserved_cases(pairs, Decimal(budget["audit_fraction"]))
            * Decimal(budget["audit_minutes_per_case"])
        )

    low, high = 0, upper + 1
    while low + 1 < high:
        middle = (low + high) // 2
        if pool_cost(middle) <= available:
            low = middle
        else:
            high = middle
    return low


def plan(manifest: dict) -> dict:
    # Validation also applies to callers using this function without the CLI.
    manifest = validate(manifest)
    budget = manifest["budget"]
    projects = sorted(manifest["projects"], key=lambda p: (sha(p["project_key"]), p["project_key"]))
    ordering = {}
    for project in projects:
        key = project["project_key"]
        slots = [(f"slot_{index:06d}", sha(f"{key}\nslot:{index:06d}"))
                 for index in range(1, project["planned_eligible_metric_count"] + 1)]
        ordering[key] = sorted(slots, key=lambda item: (item[1], item[0]))
    counts = {project["project_key"]: 0 for project in projects}
    available = Decimal(budget["total_reviewer_person_hours"]) * SIXTY
    target = budget["target_anchors_per_project"]
    for _round in range(target):
        for project in projects:
            key = project["project_key"]
            n = project["planned_eligible_metric_count"]
            if n < 2 or counts[key] >= min(target, n):
                continue
            proposed = dict(counts)
            proposed[key] += 1
            if costs(projects, proposed, budget)["total_person_minutes"] <= available:
                counts = proposed
    spent = costs(projects, counts, budget)
    project_plans = []
    for project in projects:
        key = project["project_key"]
        n = project["planned_eligible_metric_count"]
        a = counts[key]
        incidences, unique = pair_counts(n, a)
        project_plans.append({
            "project_key": key,
            "project_order_sha256": sha(key),
            "planned_eligible_metric_count": n,
            "planned_pair_task_minimum_met": n >= 2,
            "target_anchor_count": min(target, n) if n >= 2 else 0,
            "selected_anchor_count": a,
            "anchor_slot_hash_order": [
                {"slot": slot, "sha256": digest} for slot, digest in ordering[key]
            ],
            "selected_anchor_slots": [slot for slot, _ in ordering[key][:a]],
            "anchor_candidate_incidences": incidences,
            "distinct_complete_anchor_pairs": unique,
            "symmetric_pair_deduplications": incidences - unique,
            "planned_all_unordered_pairs": n * (n - 1) // 2,
        })
    total_pairs = sum(p["distinct_complete_anchor_pairs"] for p in project_plans)
    selected = sum(counts.values())
    lower = any(p["selected_anchor_count"] < p["target_anchor_count"] for p in project_plans)
    canonical = dict(manifest)
    canonical["projects"] = sorted(manifest["projects"], key=lambda p: p["project_key"])
    digest = sha(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return {
        "schema_version": VERSION,
        "tool": "development_pre_source_readiness_planner",
        "candidate_snapshot_id": manifest["candidate_snapshot_id"],
        "canonical_manifest_sha256": digest,
        "basis": "planned metric counts and ordinal placeholders; no source, labels, or eligibility decisions",
        "ordering_rule": "lexicographic lowercase SHA-256 of UTF-8 project_key; slots by SHA-256 of UTF-8 project_key + newline + slot:NNNNNN; ties by text",
        "budget": {
            "available_person_minutes": minute_string(available),
            "available_person_hours": minute_string(Decimal(budget["total_reviewer_person_hours"])),
            "target_anchors_per_project": target,
            "independent_annotators_per_distinct_pair": 2,
            "reserve_rounding": "ceil(fraction * distinct pairs) separately per project",
        },
        "project_plans": project_plans,
        "totals": {
            "selected_anchor_count": selected,
            "anchor_candidate_incidences": sum(p["anchor_candidate_incidences"] for p in project_plans),
            "distinct_complete_anchor_pairs": total_pairs,
            "annotation_person_minutes": minute_string(spent["annotation_person_minutes"]),
            "annotation_person_hours": hours_string(spent["annotation_person_minutes"]),
            "adjudication_reserved_cases": spent["adjudication_reserved_cases"],
            "adjudication_reserve_person_minutes": minute_string(spent["adjudication_reserve_person_minutes"]),
            "audit_reserved_cases": spent["audit_reserved_cases"],
            "audit_reserve_person_minutes": minute_string(spent["audit_reserve_person_minutes"]),
            "coordination_reserve_person_minutes": minute_string(spent["coordination_reserve_person_minutes"]),
            "planned_total_person_minutes": minute_string(spent["total_person_minutes"]),
            "planned_total_person_hours": hours_string(spent["total_person_minutes"]),
            "unallocated_person_minutes": minute_string(available - spent["total_person_minutes"]),
        },
        "decision": {
            "designation": "complete_anchor_budget_plan" if selected else "judged_pool_only",
            "lower_anchor_fallback_applied": lower,
            "judged_pool_distinct_pair_capacity_if_no_anchors": (
                pool_capacity(projects, budget, available) if not selected else None
            ),
            "judged_pool_capacity_reserve_rule": (
                "conservative upper bound on per-project ceiling cases for any pool allocation"
                if not selected else None
            ),
            "actual_anchor_ids_frozen": False,
            "eligibility_established": False,
            "gold_established": False,
            "exact_recall_ready": False,
            "reporting_limit": "No exact Recall@k claim; a partial pool can only support judged-pool recall after judgments.",
        },
        "unresolved_policy": {
            "unknown_eligibility_handling": "unresolved: screen and record every candidate, exclusion, replacement, and extraction failure before assigning actual metric IDs",
            "source_screen": "unresolved: operationalize eligible scalar definitions and accessible adjacent commits without looking at labels",
            "project_independence": "unresolved: verify forks, mirrors, shared seeds, datasets, and related commit families before selecting projects",
            "reviewer_availability": "unresolved: secure two independent qualified humans, third adjudicator, audit reviewer, and actual time capacity",
            "conditional_gold": "unresolved: separately resolve native and conditional target claims and all decisive prerequisites; needs_review remains unscored",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python evaluate_readiness_budget.py /outside/repository/candidates.json",
              file=sys.stderr)
        return 2
    try:
        result = plan(load_manifest(argv[1]))
    except (ManifestError, OSError) as exc:
        print(f"invalid manifest: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
