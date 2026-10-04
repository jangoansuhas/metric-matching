#!/usr/bin/env python3
"""In-memory controls for the frozen, declaration-only numeric gate.

Run with metric_matching_dev_build_20260928/venv/bin/python -B. No report,
source checkout, label, held-out input, or practice material is read or written.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from compiled_jaffle_packet import canonical, sha256
from compiled_numeric_eligibility import (EXPECTED_PACKET_SHA256, build, classify)


PACKET = Path(__file__).with_name("compiled_jaffle_i1_packet.json")


class _InMemoryPacket:
    def __init__(self, data: bytes):
        self.data = data

    def read_bytes(self) -> bytes:
        return self.data


class NumericEligibilityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = PACKET.read_bytes()
        assert sha256(raw) == EXPECTED_PACKET_SHA256
        cls.packet = json.loads(raw)
        cls.by_name = {c["metric_name"]: c for c in cls.packet["cards"]}

    def card(self, name: str = "revenue") -> dict:
        return deepcopy(self.by_name[name])

    def assert_unknown(self, card: dict, reason: str) -> None:
        result = classify(card)
        self.assertEqual(result["status"], "unknown")
        self.assertIn(reason, result["reasons"])
        self.assertEqual(result["runtime_numeric_certification"], "unknown")

    def test_frozen_frame_and_declaration_only_status(self) -> None:
        report = build(PACKET)
        self.assertEqual(report["packet_sha256"], EXPECTED_PACKET_SHA256)
        self.assertEqual((report["metric_count"], report["pair_count"]), (19, 171))
        self.assertEqual(report["status_counts"],
                         {"eligible_declaration_only": 9, "unknown": 10})
        self.assertEqual(report["pair_status_counts"],
                         {"both_eligible_declaration_only": 36,
                          "at_least_one_unknown": 135})
        self.assertTrue(all(a["runtime_numeric_certification"] == "unknown" and
                            a["status"] in {"eligible_declaration_only", "unknown"}
                            for a in report["assessments"].values()))
        self.assertEqual(classify(self.card())["status"], "eligible_declaration_only")

    def test_tampered_sql_and_rehashed_packet(self) -> None:
        card = self.card()
        card["compiled_sql"] += " -- changed"
        self.assert_unknown(card, "compiled_query_provenance_unverified")
        # A digest next to arbitrary bytes proves only internal consistency.
        # The frozen packet hash, not classify() alone, authenticates extraction.
        card["compiled_sql_sha256"] = sha256(card["compiled_sql"].encode())
        self.assertEqual(classify(card)["status"], "eligible_declaration_only")
        packet = deepcopy(self.packet)
        next(c for c in packet["cards"] if c["metric_id"] == card["metric_id"]).update(card)
        with self.assertRaisesRegex(ValueError, "frozen label-free v2 packet"):
            build(_InMemoryPacket(canonical(packet)))

    def test_source_sql_digest_and_model_shape(self) -> None:
        card = self.card()
        card["source_models"][0]["raw_sql"] += " -- changed"
        self.assert_unknown(card, "source_model_digest_unverified")
        card = self.card()
        card["source_models"][0]["node"] = []
        self.assert_unknown(card, "source_model_digest_unverified")
        card = self.card()
        card["source_models"].append(deepcopy(card["source_models"][0]))
        self.assert_unknown(card, "source_model_mapping_ambiguous")
        card = self.card()
        card["compiled_sql"] = "\ud800"  # A malformed Unicode string must not raise.
        self.assert_unknown(card, "compiled_query_provenance_unverified")

    def test_exact_resource_dependency_prevents_owner_laundering(self) -> None:
        card = self.card()
        card["manifest_depends_on"] = ["semantic_model.other.order_item"]
        self.assert_unknown(card, "measure_manifest_dependency_unverified")
        card = self.card()
        card["manifest_depends_on"] = ["model.jaffle_shop.order_items"]
        self.assert_unknown(card, "measure_manifest_dependency_unverified")
        card = self.card()
        card["manifest_depends_on"] *= 2
        self.assert_unknown(card, "measure_manifest_dependency_unverified")
        card = self.card()
        card["manifest_depends_on"] = []
        self.assert_unknown(card, "measure_manifest_dependency_unverified")

        # Give the forged owner a real model node as well: only the exact
        # semantic-model dependency can reject this otherwise plausible swap.
        card = self.card()
        unrelated = self.card("orders")
        card["source_models"].extend(deepcopy(unrelated["source_models"]))
        card["input_measures"][0]["owners"] = deepcopy(
            unrelated["input_measures"][0]["owners"])
        self.assert_unknown(card, "measure_manifest_dependency_unverified")

    def test_ambiguous_or_malformed_measure(self) -> None:
        card = self.card()
        card["input_measures"][0]["owner_count"] = 2
        card["input_measures"][0]["owners"] *= 2
        self.assert_unknown(card, "measure_owner_ambiguous")
        card = self.card()
        card["input_measures"][0]["owner_count"] = True  # bool is not an int count
        self.assert_unknown(card, "measure_owner_ambiguous")
        card = self.card()
        card["input_measures"][0]["owners"][0]["model_node"] = [["bad"]]
        self.assert_unknown(card, "measure_source_mapping_unverified")
        for malformed in (None, {}, {"measure": 42}, "revenue"):
            with self.subTest(malformed=malformed):
                card = self.card()
                card["input_measures"] = [malformed]
                self.assert_unknown(card, "malformed_measure")

    def test_template_and_filter_controls(self) -> None:
        card = self.card()
        card["metric_filter"] = {"where_filters": [{"where_sql_template": "{{ var('x') }}"}]}
        self.assert_unknown(card, "jinja")
        card = self.card()
        card["input_measures"][0]["filter"] = {
            "where_filters": [{"where_sql_template": "{% if x %} true {% endif %}"}]}
        self.assert_unknown(card, "jinja")
        card = self.card()
        card["input_measures"][0]["owners"][0]["expr"] = "{{ var('x') }}"
        self.assert_unknown(card, "jinja_measure_expression")
        card = self.card()
        card["metric_filter"] = {"unknown_filter_shape": "x"}
        self.assert_unknown(card, "filter_schema_unverified")
        card = self.card()
        card["input_measures"][0]["filter"] = 42
        self.assert_unknown(card, "filter_schema_unverified")
        card = self.card()
        del card["input_measures"][0]["filter"]
        self.assert_unknown(card, "declaration_fields_missing")

    def test_derived_and_unsupported_simple_transforms(self) -> None:
        self.assert_unknown(self.card("order_gross_profit"),
                            "dependency_numeric_type_unverified")
        self.assert_unknown(self.card("cumulative_revenue"),
                            "dependency_numeric_type_unverified")
        self.assert_unknown(self.card("food_revenue_pct"),
                            "dependency_numeric_type_unverified")
        card = self.card()
        card["type"] = "derived"
        self.assert_unknown(card, "dependency_numeric_type_unverified")
        card = self.card()
        card["type_params_expr"] = "cast(revenue as varchar)"
        self.assert_unknown(card, "simple_metric_expression_unverified")
        card = self.card()
        card["type_params_expr"] = {"unexpected": "expression"}
        self.assert_unknown(card, "malformed_metric_expression")
        card = self.card()
        card["input_metrics"] = [{"name": "something_else"}]
        self.assert_unknown(card, "simple_metric_dependencies_unverified")

    def test_explicit_nonnumeric_types_at_every_layer(self) -> None:
        for layer in ("card", "measure", "owner"):
            for field in ("data_type", "dtype"):
                with self.subTest(layer=layer, field=field):
                    card = self.card()
                    target = (card if layer == "card" else card["input_measures"][0]
                              if layer == "measure" else
                              card["input_measures"][0]["owners"][0])
                    target[field] = "varchar"
                    self.assert_unknown(card, "explicit_type_not_known_numeric")
        card = self.card()
        card["data_type"] = "numeric"
        card["dtype"] = "text"  # A first numeric field cannot mask the second.
        self.assert_unknown(card, "explicit_type_not_known_numeric")
        card = self.card()
        card["data_type"] = "DECIMAL"
        self.assertEqual(classify(card)["status"], "eligible_declaration_only")

    def test_certification_claims_are_not_evidence(self) -> None:
        card = self.card()
        card["numeric_eligibility_status"] = "certified_numeric"
        self.assert_unknown(card, "numeric_certification_claim_unverified")
        card = self.card()
        card["runtime_numeric_certification"] = "certified_numeric"
        self.assert_unknown(card, "numeric_certification_claim_unverified")
        card = self.card()
        card["input_measures"][0]["join_to_timespine"] = True
        self.assert_unknown(card, "measure_semantics_unverified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
