#!/usr/bin/env python3
"""Verify prospective Jaffle LLM inputs without invoking any model or API."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import compiled_llm_context_builder as llm


PACKET = Path(__file__).resolve().with_name("compiled_jaffle_i1_packet.json")
EXPECTED_SCHEMA_SHA256 = "b7f018381ee6af217a531dbfecbfbc1d592ad3fcca89c1f688faed5a54f762ad"
EXPECTED_SYSTEM_SHA256 = "321d5f4e800316f6b34bcbf53d84446834d355479d10c9012d1738ade62d12b2"
EXPECTED_PROMPT_SET_SHA256 = "af5ed03f27fc661b5e79849bd024280b454536a2c67d08c59e0cc022ba42ea5e"


class FrozenContextBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_bytes())
        cls.cards = {c["metric_id"]: c for c in cls.packet["cards"]}
        cls.full = llm.build(PACKET)

    def response(self, row: dict, decision: str = "abstain") -> dict:
        return {
            "pair_id": row["pair_id"], "decision": decision, "reason": "Insufficient proof",
            "evidence_status": "unverified", "evidence": [],
            "prerequisites": {name: {"status": "missing", "evidence_ref": None}
                              for name in llm.PREREQUISITES},
            "scoped_transformation": None,
        }

    def test_exact_frame_cards_scopes_and_no_leakage(self) -> None:
        rows = self.full["rows"]
        ids = sorted(self.cards)
        self.assertEqual(len(rows), 171)
        self.assertEqual([r["pair_id"] for r in rows], [a + "||" + b
                         for a, b in itertools.combinations(ids, 2)])
        self.assertEqual(self.full["counts"], {
            "pairs": 171, "prompt_ready": 153,
            "incompatible_generated_scope": 18,
            "complete_context_exceeds_budget": 0,
        })
        for row, pair in zip(rows, self.packet["pairs"]):
            with self.subTest(pair=row["pair_id"]):
                self.assertEqual(row["pair_id"], pair["pair_id"])
                if not pair["scope_compatible"]:
                    self.assertEqual(row["status"], "abstain")
                    self.assertEqual(row["reason"], "incompatible_generated_scope")
                    self.assertIsNone(row["target_scope"])
                    self.assertIsNone(row["messages"])
                    self.assertIsNone(row["prompt_sha256"])
                    self.assertIsNone(row["message_bytes"])
                    continue
                self.assertEqual(row["status"], "prompt_ready")
                self.assertIsNone(row["reason"])
                self.assertEqual(row["target_scope"], "ungrouped")
                messages = row["messages"]
                self.assertEqual([m["role"] for m in messages], ["system", "user"])
                self.assertEqual(messages[0], {"role": "system", "content": llm.SYSTEM_INSTRUCTION})
                self.assertEqual(set(messages[1]), {"role", "content"})
                user_bytes = messages[1]["content"].encode("utf-8")
                user = json.loads(user_bytes)
                self.assertEqual(set(user), {"pair_id", "target_scope", "a", "b"})
                self.assertEqual(user["pair_id"], pair["pair_id"])
                self.assertEqual(user["target_scope"], "ungrouped")
                # This equality includes SQL, source models, nulls and every
                # nested declaration field, with no annotations or method data.
                self.assertEqual(user["a"], self.cards[pair["a"]])
                self.assertEqual(user["b"], self.cards[pair["b"]])
                self.assertEqual(user_bytes, llm.canonical(user))
                serialized = llm.canonical(messages)
                self.assertEqual(row["message_bytes"], {
                    "system_content_utf8": len(llm.SYSTEM_INSTRUCTION.encode("utf-8")),
                    "user_content_utf8": len(user_bytes),
                    "canonical_messages_utf8": len(serialized),
                })
                self.assertEqual(row["required_message_bytes"], len(serialized))
                self.assertLessEqual(len(serialized), self.full["max_context_bytes"])
                self.assertEqual(row["prompt_sha256"], llm.sha256(serialized))

    def test_schema_packet_and_prompt_hashes(self) -> None:
        self.assertEqual(llm.sha256(PACKET.read_bytes()), llm.PACKET_SHA256)
        self.assertEqual(self.full["packet_sha256"], llm.PACKET_SHA256)
        self.assertEqual(self.full["pair_set_sha256"], llm.PAIR_SET_SHA256)
        schema = llm.OUTPUT_SCHEMA
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertIn("abstain", schema["properties"]["decision"]["enum"])
        self.assertNotIn("needs_review", schema["properties"]["decision"]["enum"])
        self.assertEqual(self.full["output_schema_sha256"], llm.sha256(llm.canonical(schema)))
        self.assertEqual(self.full["output_schema_sha256"], EXPECTED_SCHEMA_SHA256)
        self.assertEqual(self.full["system_instruction_sha256"],
                         llm.sha256(llm.SYSTEM_INSTRUCTION.encode("utf-8")))
        self.assertEqual(self.full["system_instruction_sha256"], EXPECTED_SYSTEM_SHA256)
        self.assertIn(llm.canonical(schema).decode("utf-8"), llm.SYSTEM_INSTRUCTION)
        self.assertIn("Judgments are scoped", llm.SYSTEM_INSTRUCTION)
        self.assertIn("does not prove", llm.SYSTEM_INSTRUCTION)
        ready = [r for r in self.full["rows"] if r["status"] == "prompt_ready"]
        self.assertEqual(self.full["prompt_set_sha256"], llm.sha256(llm.canonical([
            {"pair_id": r["pair_id"], "prompt_sha256": r["prompt_sha256"]} for r in ready
        ])))
        self.assertEqual(self.full["prompt_set_sha256"], EXPECTED_PROMPT_SET_SHA256)

    def test_budget_is_complete_and_inclusive(self) -> None:
        required = {r["pair_id"]: r["required_message_bytes"] for r in self.full["rows"]
                    if r["status"] == "prompt_ready"}
        full_by_id = {r["pair_id"]: r for r in self.full["rows"]}
        self.assertEqual((min(required.values()), max(required.values())), (12710, 16748))
        exact = min(required.values())
        bounded = llm.build(PACKET, max_context_bytes=exact)
        for row in bounded["rows"]:
            if row["pair_id"] not in required:
                self.assertEqual(row["reason"], "incompatible_generated_scope")
            elif required[row["pair_id"]] <= exact:
                self.assertEqual(row["status"], "prompt_ready")
                self.assertEqual(row["messages"], full_by_id[row["pair_id"]]["messages"])
            else:
                self.assertEqual(row["status"], "abstain")
                self.assertEqual(row["reason"], "complete_context_exceeds_budget")
                self.assertIsNone(row["messages"])
                self.assertIsNone(row["prompt_sha256"])
                self.assertIsNone(row["message_bytes"])
                self.assertEqual(row["required_message_bytes"], required[row["pair_id"]])
        tiny = llm.build(PACKET, max_context_bytes=1)
        self.assertEqual(tiny["counts"], {"pairs": 171, "prompt_ready": 0,
                         "incompatible_generated_scope": 18,
                         "complete_context_exceeds_budget": 153})
        with self.assertRaises(ValueError):
            llm.build(PACKET, max_context_bytes=0)
        with self.assertRaises(ValueError):
            llm.build(PACKET, max_context_bytes=True)

    def test_tamper_and_frame_refusal(self) -> None:
        with TemporaryDirectory() as directory:
            bad = Path(directory) / "packet.json"
            tampered = copy.deepcopy(self.packet)
            tampered["cards"][0]["description"] = "injected gold decision"
            bad.write_bytes(llm.canonical(tampered))
            with self.assertRaisesRegex(ValueError, "packet bytes differ"):
                llm.build(bad)
        for mutate in (
            lambda p: p["pairs"].reverse(),
            lambda p: p["pairs"][0].update(scope_compatible=False, target_scope=None),
            lambda p: p["cards"].pop(),
            lambda p: p.update(pair_set_sha256="0" * 64),
        ):
            with self.subTest(mutate=mutate):
                changed = copy.deepcopy(self.packet)
                mutate(changed)
                with self.assertRaises(ValueError):
                    llm._frame(changed)

    def test_only_packet_is_read_and_cli_reruns_identically(self) -> None:
        reads = []
        original = Path.read_bytes

        def read_only_packet(path: Path) -> bytes:
            reads.append(Path(path))
            if Path(path) != PACKET:
                raise AssertionError(f"unexpected side input: {path}")
            return original(path)

        with patch.object(Path, "read_bytes", read_only_packet):
            rebuilt = llm.build(PACKET)
        self.assertEqual(reads, [PACKET])
        self.assertEqual(llm.canonical(rebuilt), llm.canonical(self.full))
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / "one.json", Path(directory) / "two.json"]
            for output in paths:
                subprocess.run([sys.executable, "-B", str(llm.HERE / "compiled_llm_context_builder.py"),
                                "--packet", str(PACKET), "--max-context-bytes", "20480",
                                "--output", str(output)], check=True, capture_output=True)
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(paths[0].read_bytes(), llm.canonical(self.full))

    def test_response_pair_identity_and_strict_shape(self) -> None:
        ready = [r for r in self.full["rows"] if r["status"] == "prompt_ready"]
        row = ready[0]
        valid = self.response(row)
        self.assertEqual(llm.validate_response(row, llm.canonical(valid))["decision"], "abstain")
        wrong = copy.deepcopy(valid)
        wrong["pair_id"] = ready[1]["pair_id"]
        with self.assertRaisesRegex(llm.ResponseError, "pair_id differs"):
            llm.validate_response(row, wrong)
        with self.assertRaisesRegex(llm.ResponseError, "pair_id differs"):
            llm.validate_response(row, llm.canonical(wrong))
        extra = dict(valid, gold_label="direct_equivalent")
        with self.assertRaises(llm.ResponseError):
            llm.validate_response(row, extra)
        with self.assertRaises(llm.ResponseError):
            llm.validate_response(row, '{"pair_id":"x","pair_id":"y"}')
        mixed = next(r for r in self.full["rows"] if r["reason"] == "incompatible_generated_scope")
        with self.assertRaisesRegex(llm.ResponseError, "no prompt"):
            llm.validate_response(mixed, self.response(row))

    def test_unsupported_equivalence_shape_and_unverified_gate(self) -> None:
        row = next(r for r in self.full["rows"] if r["status"] == "prompt_ready")
        user = json.loads(row["messages"][1]["content"])
        direct = self.response(row, "direct_equivalent")
        missing = copy.deepcopy(direct)
        del missing["prerequisites"][llm.PREREQUISITES[0]]
        with self.assertRaisesRegex(llm.ResponseError, "prerequisites"):
            llm.validate_response(row, missing)
        gated = llm.validate_response(row, direct)
        self.assertEqual((gated["claimed_decision"], gated["decision"],
                          gated["evidence_review_status"], gated["reason_code"]),
                         ("direct_equivalent", "abstain", "needs_review",
                          "unverified_prerequisites"))
        self.assertIn("grain_and_rollup", gated["unverified_prerequisites"])

        cross = self.response(row, "cross_grain_equivalent")
        with self.assertRaisesRegex(llm.ResponseError, "scoped_transformation"):
            llm.validate_response(row, cross)
        cross["scoped_transformation"] = {
            "from_metric_id": user["a"]["metric_id"],
            "to_metric_id": user["b"]["metric_id"],
            "from_grain": "order", "to_grain": "customer",
            "rollup_operation": "sum by customer", "target_scope": "ungrouped",
            "status": "unverified", "evidence_ref": None,
        }
        gated = llm.validate_response(row, cross)
        self.assertEqual(gated["decision"], "abstain")
        self.assertEqual(gated["evidence_review_status"], "needs_review")
        self.assertIn("scoped_transformation", gated["unverified_prerequisites"])
        wrong_scope = copy.deepcopy(cross)
        wrong_scope["scoped_transformation"]["target_scope"] = "metric_time"
        with self.assertRaisesRegex(llm.ResponseError, "prompted pair/scope"):
            llm.validate_response(row, wrong_scope)

        # Model-authored 'verified' references cannot authenticate themselves.
        forged = copy.deepcopy(cross)
        forged["evidence_status"] = "verified_independent"
        for record in forged["prerequisites"].values():
            record.update(status="verified", evidence_ref="model-claimed-reference")
        forged["scoped_transformation"].update(status="verified",
                                                evidence_ref="model-claimed-reference")
        gated = llm.validate_response(row, forged)
        self.assertEqual(gated["decision"], "abstain")
        self.assertEqual(gated["evidence_review_status"], "needs_review")
        self.assertEqual(gated["reason_code"], "independent_evidence_not_authenticated")


if __name__ == "__main__":
    unittest.main()
