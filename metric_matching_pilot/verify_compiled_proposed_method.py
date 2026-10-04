#!/usr/bin/env python3
"""Independent adversarial checks for the compiled proposed method.

Development packet only: no reports, reference decisions, worksheets, source
repositories, or held-out artifacts are inputs. Run with SQLGlot 30.20.0, e.g.
``python -B metric_matching_pilot/verify_compiled_proposed_method.py``.
The optional runner check activates when a proposed-method runner is present.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import compiled_ast_lineage_baseline as ast
from compiled_proposed_method import compare


HERE = Path(__file__).resolve().parent
PACKET = HERE / "compiled_jaffle_i1_packet.json"
PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"
PAIR_SET_SHA256 = "0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0"
UNKNOWN_PROOFS = (
    "runtime_numeric_type", "metric_expression_field_lineage", "grain_and_rollup",
    "time_grain_and_window", "population_and_filter_meaning", "join_cardinality",
    "missing_group_rule", "null_policy", "units", "snapshot_state",
)
SCORES = {
    "time_semantics_review": 1.0,
    "declared_input_review": 0.8,
    "filter_scope_review": 0.6,
    "same_ast_review": 0.5,
    "shared_measure_review": 0.4,
    "same_model_review": 0.2,
    "insufficient_relation_evidence": 0.0,
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def frozen_packet() -> dict:
    raw = PACKET.read_bytes()
    if digest(raw) != PACKET_SHA256:
        raise AssertionError("v2 packet bytes differ from the contract")
    return json.loads(raw)


class ProposedMethodBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if ast.sqlglot is None or ast.sqlglot.__version__ != "30.20.0":
            raise RuntimeError("verifier requires SQLGlot 30.20.0 in DuckDB dialect")
        cls.packet = frozen_packet()
        cls.by_id = {c["metric_id"]: c for c in cls.packet["cards"]}
        cls.by_name = {c["metric_name"]: c for c in cls.packet["cards"]}

    def named(self, a: str, b: str) -> dict:
        return compare(self.by_name[a], self.by_name[b])

    def safe(self, result: dict, *, signal: str | None = None,
             score: float | None = None) -> None:
        self.assertEqual(result["decision"], "abstain", result)
        fields = {"decision", "signal", "candidate_score", "candidate_hypothesis",
                  "obligations", "evidence", "reason"}
        self.assertEqual(set(result), fields)
        self.assertIsInstance(result["reason"], str)
        self.assertIsInstance(result["evidence"], list)
        if signal is not None:
            self.assertEqual(result["signal"], signal, result)
            self.assertEqual(result.get("candidate_score"), score, result)
        if result.get("candidate_score") is not None:
            self.assertIn(result["signal"], SCORES)
            self.assertEqual(result["candidate_score"], SCORES[result["signal"]])
            self.assertTrue(math.isfinite(result["candidate_score"]))
            for proof in UNKNOWN_PROOFS:
                self.assertEqual(result["obligations"][proof]["state"], "unknown",
                                 (result["signal"], proof))

    def test_complete_frozen_frame_and_full_decision_denominator(self) -> None:
        p = self.packet
        self.assertEqual(p["packet_version"], "compiled_jaffle_i1_packet_v2")
        self.assertEqual((p["metric_count"], len(p["cards"]), len(self.by_id)),
                         (19, 19, 19))
        self.assertEqual((p["pair_count"], len(p["pairs"])), (171, 171))
        ids = sorted(self.by_id)
        expected = [a + "||" + b for a, b in itertools.combinations(ids, 2)]
        observed = [pair["pair_id"] for pair in p["pairs"]]
        self.assertEqual(observed, expected)
        pair_bytes = (json.dumps(expected, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":")) + "\n").encode()
        self.assertEqual(p["pair_set_sha256"], digest(pair_bytes))
        self.assertEqual(p["pair_set_sha256"], PAIR_SET_SHA256)
        scopes = [c["sql_scope"] for c in p["cards"]]
        self.assertEqual((scopes.count("ungrouped"), scopes.count("metric_time")), (18, 1))

        compatible = 0
        mixed = 0
        for pair in p["pairs"]:
            with self.subTest(pair=pair["pair_id"]):
                a, b = self.by_id[pair["a"]], self.by_id[pair["b"]]
                self.assertEqual(pair["a"] + "||" + pair["b"], pair["pair_id"])
                self.assertEqual(pair["scope_compatible"], a["sql_scope"] == b["sql_scope"])
                self.assertEqual(pair["target_scope"],
                                 a["sql_scope"] if pair["scope_compatible"] else None)
                result = compare(a, b)
                self.safe(result)
                if pair["scope_compatible"]:
                    compatible += 1
                    self.assertIsNotNone(result["candidate_score"])
                else:
                    mixed += 1
                    self.safe(result, signal="incompatible_generated_scope", score=None)
                    self.assertIsNone(result["candidate_score"])
        self.assertEqual((compatible, mixed), (153, 18))

    def test_temporal_same_sql_only_prioritizes_review(self) -> None:
        result = self.named("cumulative_revenue", "revenue")
        self.safe(result, signal="time_semantics_review", score=1.0)
        self.assertEqual(result["obligations"]["identical_generated_scope_ast"]["state"], "observed")
        self.assertEqual(result["obligations"]["same_declared_measure_owner"]["state"], "observed")
        self.assertEqual(result["obligations"]["declaration_numeric_eligibility"]["state"],
                         "unknown")
        self.assertIn("cumulative", result["candidate_hypothesis"])
        self.assertEqual(self.by_name["cumulative_revenue"]["sql_scope"], "ungrouped")

        # Even two simple declarations with identical generated SQL and owner
        # evidence cannot turn matching syntax into an equivalence label.
        duplicate = copy.deepcopy(self.by_name["revenue"])
        duplicate["metric_id"] = "metric.synthetic.other_revenue"
        duplicate["metric_name"] = duplicate["name"] = "other_revenue"
        same_sql = compare(self.by_name["revenue"], duplicate)
        self.safe(same_sql, signal="same_ast_review", score=0.5)

    def test_filtered_same_measure_is_unproved_population_relation(self) -> None:
        result = self.named("drink_orders", "food_orders")
        self.safe(result, signal="filter_scope_review", score=0.6)
        self.assertEqual(result["obligations"]["same_declared_measure_owner"]["state"], "observed")
        filters = result["obligations"]["compiled_filter_alignment"]
        self.assertNotEqual(filters["left_where"], filters["right_where"])
        self.assertIn("population", result["reason"])

        # Different YAML filters alone cannot establish a compiled filter
        # contrast when the generated predicates are identical.
        synthetic = copy.deepcopy(self.by_name["food_orders"])
        same_query = self.by_name["drink_orders"]
        synthetic["compiled_sql"] = same_query["compiled_sql"]
        synthetic["compiled_sql_sha256"] = same_query["compiled_sql_sha256"]
        no_compiled_difference = compare(same_query, synthetic)
        self.safe(no_compiled_difference, signal="same_ast_review", score=0.5)

    def test_derived_and_ratio_edges_require_both_declaration_and_manifest(self) -> None:
        for derived, source in (
            ("order_gross_profit", "revenue"),
            ("average_order_value", "count_lifetime_orders"),
            ("drink_revenue_pct", "revenue"),
        ):
            with self.subTest(derived=derived, source=source):
                original = self.by_name[derived]
                input_card = self.by_name[source]
                self.assertIn(input_card["metric_id"], original["manifest_depends_on"])
                result = compare(original, input_card)
                self.safe(result, signal="declared_input_review", score=0.8)
                self.assertIn("not proven equivalent", result["reason"])
                no_edge = copy.deepcopy(original)
                no_edge["manifest_depends_on"].remove(input_card["metric_id"])
                diminished = compare(no_edge, input_card)
                self.safe(diminished)
                self.assertNotEqual(diminished["signal"], "declared_input_review")

                no_ref = copy.deepcopy(original)
                if no_ref["type"] == "ratio":
                    for field in ("numerator", "denominator"):
                        if no_ref[field] == input_card["metric_name"]:
                            no_ref[field] = "unrelated_metric"
                else:
                    no_ref["input_metrics"] = [ref for ref in no_ref["input_metrics"]
                                               if ref["name"] != input_card["metric_name"]]
                diminished = compare(no_ref, input_card)
                self.safe(diminished)
                self.assertNotEqual(diminished["signal"], "declared_input_review")

    def test_syntax_failure_abstains_even_with_a_recomputed_sql_digest(self) -> None:
        base = self.by_name["revenue"]
        peer = self.by_name["cumulative_revenue"]
        for sql in ("SELECT FROM", "SELECT 1; SELECT 2", "SELECT * FROM orders"):
            with self.subTest(sql=sql):
                bad = copy.deepcopy(base)
                bad["compiled_sql"] = sql
                bad["compiled_sql_sha256"] = digest(sql.encode())
                self.safe(compare(bad, peer), signal="unsupported_sql_or_card", score=None)
        with patch.object(ast, "sqlglot", None):
            self.safe(compare(base, peer), signal="unsupported_parser", score=None)

    def test_hash_and_owner_failures_have_no_review_score(self) -> None:
        base = self.by_name["revenue"]
        peer = self.by_name["cumulative_revenue"]
        mutations = (
            ("SQL byte changed", lambda c: c.__setitem__("compiled_sql", c["compiled_sql"] + " -- edit"),
             "compiled_provenance_needs_review"),
            ("source byte changed", lambda c: c["source_models"][0].__setitem__(
                "raw_sql", c["source_models"][0]["raw_sql"] + " -- edit"),
             "compiled_provenance_needs_review"),
            ("source digest changed", lambda c: c["source_models"][0].__setitem__(
                "raw_sql_sha256", "0" * 64), "compiled_provenance_needs_review"),
            ("ambiguous owner", lambda c: c["input_measures"][0].__setitem__(
                "owner_count", 2), "owner_lineage_needs_review"),
            ("missing owner", lambda c: c["input_measures"][0].__setitem__(
                "owners", []), "owner_lineage_needs_review"),
            ("foreign model", lambda c: c["input_measures"][0]["owners"][0].__setitem__(
                "model_node", ["model.foreign"]), "owner_lineage_needs_review"),
            ("foreign physical source", lambda c: c["input_measures"][0]["owners"][0].__setitem__(
                "node_relation", '"dev"."main"."other"'), "owner_lineage_needs_review"),
        )
        for name, mutate, expected in mutations:
            with self.subTest(mutation=name):
                bad = copy.deepcopy(base)
                mutate(bad)
                self.safe(compare(bad, peer), signal=expected, score=None)

    def test_promoted_eligibility_and_self_asserted_semantics_never_label(self) -> None:
        a = copy.deepcopy(self.by_name["orders"])
        b = copy.deepcopy(self.by_name["new_customer_orders"])
        for card in (a, b):
            card["numeric_eligibility_status"] = "certified_numeric"
            card.update({"grain": "order", "units": "count", "join_cardinality": "one_to_one",
                         "missing_group_rule": "zero", "null_policy": "zero",
                         "snapshot_state": "same", "population": "same", "time_rule": "same"})
            card["compiled_metric_expression_provenance"] = {"status": "verified"}
            card["field_owner_provenance"] = {"status": "verified"}
            card["gold_label"] = "direct_equivalent"
        result = compare(a, b)
        self.safe(result, signal="filter_scope_review", score=0.6)
        self.assertEqual(result["obligations"]["runtime_numeric_type"]["state"], "unknown")

    def test_global_and_per_anchor_ranking_and_optional_runner(self) -> None:
        # An independent oracle: sort direct method scores, never a saved report.
        rows = []
        for pair in self.packet["pairs"]:
            a, b = self.by_id[pair["a"]], self.by_id[pair["b"]]
            result = compare(a, b)
            rows.append((pair, result))
        scored = [(r["candidate_score"], pair["pair_id"]) for pair, r in rows
                  if pair["scope_compatible"]]
        global_ids = [pid for score, pid in sorted(scored, key=lambda item: (-item[0], item[1]))]
        self.assertEqual(len(global_ids), 153)
        anchors = sorted(c["metric_id"] for c in self.packet["cards"]
                         if c["sql_scope"] == "ungrouped")
        self.assertEqual(len(anchors), 18)
        by_anchor = {}
        for anchor in anchors:
            candidates = [(r["candidate_score"], pair["b"] if pair["a"] == anchor else pair["a"])
                          for pair, r in rows if pair["scope_compatible"]
                          and anchor in (pair["a"], pair["b"])]
            by_anchor[anchor] = [partner for score, partner in sorted(
                candidates, key=lambda item: (-item[0], item[1]))]
            self.assertEqual(len(by_anchor[anchor]), 17)
            self.assertEqual(len(set(by_anchor[anchor])), 17)
            self.assertNotIn(anchor, by_anchor[anchor])
        self.assertEqual(global_ids[0], "metric.jaffle_shop.cumulative_revenue||metric.jaffle_shop.revenue")

        runners = sorted(HERE.glob("run_compiled*proposed*.py"))
        integrated = HERE / "run_compiled_development_comparison.py"
        if integrated.exists() and "compiled_proposed_method" in integrated.read_text():
            runners.append(integrated)
        if not runners:
            self.skipTest("proposed-method comparison runner has not been added")
        self.assertEqual(len(runners), 1, runners)
        spec = importlib.util.spec_from_file_location("proposed_comparison_under_test", runners[0])
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.generate(PACKET)
        report_rows = report["rows"]
        self.assertEqual({r["pair_id"] for r in report_rows}, {p["pair_id"] for p in self.packet["pairs"]})
        self.assertEqual(len(report_rows), 171)
        pair_by_id = {p["pair_id"]: p for p in self.packet["pairs"]}
        self.assertEqual(sum(not r["scope_compatible"] for r in report_rows), 18)
        method_keys = [key for key, value in report_rows[0].items()
                       if ("proposed" in key or "conditional" in key)
                       and isinstance(value, dict) and "decision" in value]
        self.assertEqual(len(method_keys), 1, method_keys)
        method_key = method_keys[0]
        for row in report_rows:
            pair = pair_by_id[row["pair_id"]]
            self.assertEqual((row["a"], row["b"], row["scope_compatible"]),
                             (pair["a"], pair["b"], pair["scope_compatible"]))
            observed = row[method_key]
            self.safe(observed)
            expected = compare(self.by_id[row["a"]], self.by_id[row["b"]])
            self.assertEqual((observed["signal"], observed.get("candidate_score")),
                             (expected["signal"], expected["candidate_score"]))
            if not row["scope_compatible"]:
                self.assertIsNone(observed["candidate_score"])
                self.assertIsNone(observed["candidate_hypothesis"])
                self.assertEqual(observed["obligations"], {})
        global_rankings = report["candidate_ranking_comparable_only"]
        anchor_rankings = report["candidate_ranking_by_anchor_comparable_only"]
        rank_keys = [key for key in global_rankings if "proposed" in key or "conditional" in key]
        self.assertEqual(len(rank_keys), 1, rank_keys)
        key = rank_keys[0]
        self.assertEqual(global_rankings[key]["ranked_pair_ids"], global_ids)
        self.assertEqual(global_rankings[key]["scored_pairs"], 153)
        self.assertEqual(global_rankings[key]["positive_score_pairs"],
                         sum(score > 0 for score, _ in scored))
        self.assertEqual(anchor_rankings[key], by_anchor)

        # A two-card method cannot authenticate packet membership on its own;
        # the runner must refuse altered packet bytes, including injected gold.
        with TemporaryDirectory() as tmp:
            tampered = copy.deepcopy(self.packet)
            tampered["cards"][0]["gold_label"] = "direct_equivalent"
            path = Path(tmp) / "tampered_packet.json"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen label-free input"):
                module.generate(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
