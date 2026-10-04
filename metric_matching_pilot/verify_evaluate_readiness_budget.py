#!/usr/bin/env python3
"""Toy, source-free controls for the pre-source readiness budget planner."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("evaluate_readiness_budget.py")
ALPHA = "example/alpha@" + "a" * 40
BETA = "example/beta@" + "b" * 40


def manifest(projects=None, **budget_changes):
    budget = {
        "total_reviewer_person_hours": "2",
        "annotation_minutes_per_pair_per_annotator": "6",
        "adjudication_fraction": "0.2",
        "adjudication_minutes_per_case": "9",
        "audit_fraction": "0.2",
        "audit_minutes_per_case": "4",
        "coordination_reserve_minutes": "10",
        "target_anchors_per_project": 2,
    }
    budget.update(budget_changes)
    return {
        "schema_version": 1,
        "manifest_kind": "metadata_only_pre_source",
        "candidate_snapshot_id": "toy-2026-09-29",
        "projects": projects if projects is not None else [
            {"project_key": ALPHA, "planned_eligible_metric_count": 4}
        ],
        "budget": budget,
    }


def invoke(payload):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "candidate_manifest.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(path)],
                              capture_output=True, text=True, env=env, check=False)


def accepted(payload):
    result = invoke(payload)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class BudgetPlannerControls(unittest.TestCase):
    def test_complete_universe_deduplicates_symmetric_pairs_and_reserves(self):
        out = accepted(manifest())
        project = out["project_plans"][0]
        totals = out["totals"]
        self.assertEqual(project["selected_anchor_count"], 2)
        self.assertEqual(project["anchor_candidate_incidences"], 6)
        self.assertEqual(project["distinct_complete_anchor_pairs"], 5)
        self.assertEqual(project["symmetric_pair_deduplications"], 1)
        self.assertEqual(totals["annotation_person_minutes"], "60")
        self.assertEqual(totals["annotation_person_hours"], "1.0000")
        self.assertEqual(totals["adjudication_reserved_cases"], 1)
        self.assertEqual(totals["adjudication_reserve_person_minutes"], "9")
        self.assertEqual(totals["audit_reserve_person_minutes"], "4")
        self.assertEqual(totals["coordination_reserve_person_minutes"], "10")
        self.assertEqual(totals["planned_total_person_minutes"], "83")
        self.assertEqual(totals["planned_total_person_hours"], "1.3833")
        self.assertEqual(out["decision"]["designation"], "complete_anchor_budget_plan")
        self.assertFalse(out["decision"]["exact_recall_ready"])

    def test_hash_order_and_selection_ignore_manifest_project_order(self):
        projects = [
            {"project_key": ALPHA, "planned_eligible_metric_count": 5},
            {"project_key": BETA, "planned_eligible_metric_count": 3},
        ]
        settings = dict(total_reviewer_person_hours="20", adjudication_fraction="0",
                        audit_fraction="0", target_anchors_per_project=3)
        first = accepted(manifest(projects, **settings))
        reverse = accepted(manifest(list(reversed(projects)), **settings))
        self.assertEqual(first, reverse)
        project_hashes = [p["project_order_sha256"] for p in first["project_plans"]]
        self.assertEqual(project_hashes, sorted(project_hashes))
        for project in first["project_plans"]:
            key = project["project_key"]
            ordered = project["anchor_slot_hash_order"]
            self.assertEqual([item["sha256"] for item in ordered],
                             sorted(item["sha256"] for item in ordered))
            self.assertEqual(project["selected_anchor_slots"],
                             [item["slot"] for item in ordered[:3]])
            for item in ordered:
                slot_number = int(item["slot"].removeprefix("slot_"))
                expected = hashlib.sha256(f"{key}\nslot:{slot_number:06d}".encode()).hexdigest()
                self.assertEqual(item["sha256"], expected)

    def test_lower_anchor_fallback_fits_fixed_person_hours(self):
        out = accepted(manifest(
            [{"project_key": ALPHA, "planned_eligible_metric_count": 10}],
            total_reviewer_person_hours="2",
            annotation_minutes_per_pair_per_annotator="5",
            adjudication_fraction="0", audit_fraction="0",
            target_anchors_per_project=3,
        ))
        self.assertEqual(out["project_plans"][0]["selected_anchor_count"], 1)
        self.assertEqual(out["totals"]["distinct_complete_anchor_pairs"], 9)
        self.assertEqual(out["totals"]["planned_total_person_minutes"], "100")
        self.assertTrue(out["decision"]["lower_anchor_fallback_applied"])
        self.assertIsNone(out["decision"]["judged_pool_distinct_pair_capacity_if_no_anchors"])

    def test_unaffordable_complete_universe_designates_judged_pool(self):
        out = accepted(manifest(
            [{"project_key": ALPHA, "planned_eligible_metric_count": 30}],
            total_reviewer_person_hours="1",
            annotation_minutes_per_pair_per_annotator="5",
            adjudication_fraction="0", audit_fraction="0",
        ))
        self.assertEqual(out["totals"]["selected_anchor_count"], 0)
        self.assertEqual(out["decision"]["designation"], "judged_pool_only")
        self.assertEqual(out["decision"]["judged_pool_distinct_pair_capacity_if_no_anchors"], 5)
        self.assertEqual(out["totals"]["planned_total_person_minutes"], "0")
        self.assertFalse(out["decision"]["exact_recall_ready"])

    def test_pool_capacity_covers_reserve_rounding_across_projects(self):
        out = accepted(manifest(
            [{"project_key": ALPHA, "planned_eligible_metric_count": 100},
             {"project_key": BETA, "planned_eligible_metric_count": 100}],
            total_reviewer_person_hours="0.5",
            annotation_minutes_per_pair_per_annotator="1",
            adjudication_fraction="0.1", adjudication_minutes_per_case="20",
            audit_fraction="0", coordination_reserve_minutes="0",
        ))
        self.assertEqual(out["decision"]["designation"], "judged_pool_only")
        # Two pairs in separate projects require two reserved adjudications: 44 min.
        self.assertEqual(out["decision"]["judged_pool_distinct_pair_capacity_if_no_anchors"], 1)

    def test_rare_positive_and_unresolved_toy_outcomes_cannot_be_input_or_gold(self):
        # Hypothetical later outcomes are intentionally kept outside the planner input.
        later_outcomes = {"rare_positive": 1, "needs_review": 1, "other": 4}
        out = accepted(manifest(
            [{"project_key": ALPHA, "planned_eligible_metric_count": 4}],
            total_reviewer_person_hours="10", target_anchors_per_project=4,
        ))
        self.assertEqual(sum(later_outcomes.values()), 6)  # complete unordered toy universe
        self.assertEqual(out["totals"]["distinct_complete_anchor_pairs"], 6)
        self.assertFalse(out["decision"]["gold_established"])
        self.assertFalse(out["decision"]["exact_recall_ready"])
        self.assertIn("needs_review", out["unresolved_policy"]["conditional_gold"])
        attempted = manifest()
        attempted["projects"][0]["labels"] = later_outcomes
        self.assertEqual(invoke(attempted).returncode, 2)

    def test_reserve_cases_round_up_per_project(self):
        out = accepted(manifest(
            [{"project_key": ALPHA, "planned_eligible_metric_count": 2},
             {"project_key": BETA, "planned_eligible_metric_count": 2}],
            total_reviewer_person_hours="5", target_anchors_per_project=1,
            adjudication_fraction="0.1", audit_fraction="0.1",
        ))
        self.assertEqual(out["totals"]["distinct_complete_anchor_pairs"], 2)
        self.assertEqual(out["totals"]["adjudication_reserved_cases"], 2)
        self.assertEqual(out["totals"]["audit_reserved_cases"], 2)

    def test_rejects_missing_ambiguous_and_nonmetadata_input(self):
        cases = []
        missing = manifest()
        del missing["budget"]["audit_fraction"]
        cases.append(missing)
        wrong_type = manifest()
        wrong_type["projects"][0]["planned_eligible_metric_count"] = True
        cases.append(wrong_type)
        unsafe = manifest()
        unsafe["projects"][0]["source_path"] = "models/secret.sql"
        cases.append(unsafe)
        invalid_fraction = manifest(adjudication_fraction="1.1")
        cases.append(invalid_fraction)
        numeric_hours = manifest(total_reviewer_person_hours=2.0)
        cases.append(numeric_hours)
        same_repo = manifest([
            {"project_key": ALPHA, "planned_eligible_metric_count": 2},
            {"project_key": "example/alpha@" + "c" * 40,
             "planned_eligible_metric_count": 2},
        ])
        cases.append(same_repo)
        dot_repo = manifest([{"project_key": "example/..@" + "a" * 40,
                              "planned_eligible_metric_count": 2}])
        cases.append(dot_repo)
        for case in cases:
            with self.subTest(case=case):
                rejected = invoke(case)
                self.assertEqual(rejected.returncode, 2)
                self.assertEqual(rejected.stdout, "")
        duplicate = '{"schema_version":1,"schema_version":1}'
        self.assertIn("duplicate JSON key", invoke(duplicate).stderr)
        self.assertEqual(invoke('{"budget":NaN}').returncode, 2)

    def test_deeply_nested_json_is_rejected_without_traceback(self):
        result = invoke("[" * 20000 + "0" + "]" * 20000)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid manifest:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
