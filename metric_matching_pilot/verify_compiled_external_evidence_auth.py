"""Adversarial checks for the local supplemental evidence authenticator.

Run: python -B verify_compiled_external_evidence_auth.py
Only temporary artifacts are written; the compiled packet is read-only.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from compiled_external_evidence_auth import (
    EvidenceRejected, authenticate_semantic_evidence, binding_for,
    review_signing_payload,
)

FROZEN_PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class AuthenticatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "allowlisted"
        self.root.mkdir()
        (self.root / "reviews").mkdir()
        self.artifact = self.root / "reviews" / "claim.txt"
        self.artifact.write_bytes(b"Independent review of grain=order\n")
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.roots = {"review-artifacts": self.root}
        self.reviewers = {"reviewer-1": {
            "public_key_ed25519": self.public,
            "reviewer_type": "human",
            "independent_of_producers": frozenset({"producer-1"}),
        }}
        cards = []
        for metric_id, sql in (("metric.a", "SELECT SUM(a) FROM t"),
                               ("metric.b", "SELECT COUNT(*) FROM t")):
            cards.append({
                "metric_id": metric_id, "name": metric_id, "type": "simple",
                "sql_scope": "ungrouped", "compiled_sql": sql,
                "source_status": "metricflow_sql_generated_not_executed",
                "numeric_eligibility_status": "not_certified_by_compiled_bundle",
                "manifest_depends_on": [], "input_measures": [], "source_models": [],
                "grain": None,
            })
        for card in cards:
            card["compiled_sql_sha256"] = hashlib.sha256(card["compiled_sql"].encode()).hexdigest()
        self.packet = _json({
            "packet_version": "test_i1", "source_commit": "a" * 40,
            "cards": cards,
            "pairs": [{"a": "metric.a", "b": "metric.b",
                       "pair_id": "metric.a||metric.b", "scope_compatible": True,
                       "target_scope": "ungrouped"}],
        })
        self.expected_packet_sha256 = hashlib.sha256(self.packet).hexdigest()
        self.pair_id = "metric.a||metric.b"

    def record(self, *, field: str = "grain", value: object = "order",
               kind: str = "independent_review", locator: str = "reviews/claim.txt",
               artifact_hash: str | None = None, signer: Ed25519PrivateKey | None = None,
               reviewer_id: str = "reviewer-1", reviewer_type: str = "human",
               method: str = "manual_artifact_review", producer: str = "producer-1") -> dict:
        claim = {
            "field": field, "value": value, "kind": kind,
            "artifact": {
                "root_id": "review-artifacts", "locator": locator,
                "sha256": artifact_hash or hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            },
            "binding": binding_for(self.packet, self.pair_id, "metric.a",
                                   expected_packet_sha256=self.expected_packet_sha256),
            "provenance": {
                "producer_id": producer, "reviewer_id": reviewer_id,
                "reviewer_type": reviewer_type, "review_method": method,
                "reviewed_at": "2026-09-29T12:00:00Z",
            },
        }
        claim["provenance"]["signature_ed25519"] = base64.b64encode(
            (signer or self.key).sign(review_signing_payload(claim))
        ).decode("ascii")
        return claim

    def authenticate(self, records: list[dict], **overrides: object) -> dict:
        return authenticate_semantic_evidence(
            overrides.get("packet", self.packet), overrides.get("pair_id", self.pair_id),
            "metric.a", records,
            expected_packet_sha256=overrides.get("expected_packet_sha256",
                                                 self.expected_packet_sha256),
            artifact_roots=overrides.get("roots", self.roots),
            trusted_reviewers=overrides.get("reviewers", self.reviewers),
        )

    def test_human_signed_assertion_has_no_baseline_promotion(self) -> None:
        record = self.record()
        original = copy.deepcopy(record)
        result = self.authenticate([record])
        self.assertEqual(record, original)
        self.assertEqual(result["binding"]["source_commit"], "a" * 40)
        self.assertEqual(set(result), {"schema_version", "binding",
                                       "authenticated_signed_assertions"})
        assertion, = result["authenticated_signed_assertions"]
        self.assertEqual(assertion, original)
        self.assertEqual(assertion["binding"], result["binding"])
        self.assertNotIn("status", assertion)
        self.assertNotIn("baseline_card_additions", result)
        self.assertNotIn("semantic_prerequisite_verifications", result)

    def test_automated_reviewer_is_explicitly_distinct(self) -> None:
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(serialization.Encoding.Raw,
                                               serialization.PublicFormat.Raw)
        reviewers = {"check-runner": {
            "public_key_ed25519": public, "reviewer_type": "automated",
            "independent_of_producers": frozenset({"producer-1"}),
        }}
        claim = self.record(kind="executed_constraint_check", reviewer_id="check-runner",
                            reviewer_type="automated", method="automated_constraint_check",
                            signer=key)
        result = self.authenticate([claim], reviewers=reviewers)
        assertion, = result["authenticated_signed_assertions"]
        self.assertEqual(assertion["provenance"]["reviewer_type"], "automated")
        self.assertEqual(assertion["kind"], "executed_constraint_check")

    def test_locator_missing_escape_and_noncanonical_rejected(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_bytes(self.artifact.read_bytes())
        for locator in ("reviews/missing.txt", "../outside.txt", "/tmp/claim.txt",
                        "reviews/../reviews/claim.txt", "reviews/./claim.txt",
                        "reviews//claim.txt", "reviews\\claim.txt", "%2e%2e/claim.txt"):
            with self.subTest(locator=locator), self.assertRaises(EvidenceRejected):
                self.authenticate([self.record(locator=locator)])

    def test_symlink_leaf_parent_and_root_rejected(self) -> None:
        (self.root / "linked.txt").symlink_to(self.artifact)
        (self.root / "linked-dir").symlink_to(self.root / "reviews", target_is_directory=True)
        for locator in ("linked.txt", "linked-dir/claim.txt"):
            with self.subTest(locator=locator), self.assertRaises(EvidenceRejected):
                self.authenticate([self.record(locator=locator)])
        linked_root = Path(self.temp.name) / "root-link"
        linked_root.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record()], roots={"review-artifacts": linked_root})

    def test_exact_file_bytes_and_hash_mismatch(self) -> None:
        claim = self.record()
        self.artifact.write_bytes(self.artifact.read_bytes() + b"\n")
        with self.assertRaisesRegex(EvidenceRejected, "SHA256 mismatch"):
            self.authenticate([claim])
        wrong = self.record(artifact_hash="0" * 64)
        with self.assertRaises(EvidenceRejected):
            self.authenticate([wrong])

    def test_wrong_sql_card_pair_packet_and_commit_bindings(self) -> None:
        binding_keys = ("compiled_sql_sha256", "card_sha256", "pair_id",
                        "packet_sha256", "source_commit")
        for key in binding_keys:
            claim = self.record()
            claim["binding"][key] = "b" * 64 if key != "pair_id" else "wrong"
            claim["provenance"]["signature_ed25519"] = base64.b64encode(
                self.key.sign(review_signing_payload(claim))).decode()
            with self.subTest(key=key), self.assertRaisesRegex(EvidenceRejected, "binding mismatch"):
                self.authenticate([claim])
        bad_packet = json.loads(self.packet)
        bad_packet["cards"][0]["compiled_sql"] += " WHERE TRUE"
        with self.assertRaisesRegex(EvidenceRejected, "pair card compiled SQL hash mismatch"):
            self.authenticate([self.record()], packet=_json(bad_packet),
                              expected_packet_sha256=hashlib.sha256(_json(bad_packet)).hexdigest())

    def test_second_card_sql_and_pair_structure_are_checked(self) -> None:
        for mutation in ("other_sql_changed", "other_sql_missing", "other_hash_missing",
                         "other_status_missing", "other_lineage_missing", "other_scope_wrong",
                         "duplicate_other", "pair_scope_missing", "pair_extra_key"):
            packet = json.loads(self.packet)
            other = packet["cards"][1]
            pair = packet["pairs"][0]
            if mutation == "other_sql_changed":
                other["compiled_sql"] += " WHERE 1=1"
            elif mutation == "other_sql_missing":
                del other["compiled_sql"]
            elif mutation == "other_hash_missing":
                del other["compiled_sql_sha256"]
            elif mutation == "other_status_missing":
                del other["source_status"]
            elif mutation == "other_lineage_missing":
                del other["input_measures"]
            elif mutation == "other_scope_wrong":
                other["sql_scope"] = "metric_time"
            elif mutation == "duplicate_other":
                packet["cards"].append(copy.deepcopy(other))
            elif mutation == "pair_scope_missing":
                del pair["target_scope"]
            elif mutation == "pair_extra_key":
                pair["unreviewed"] = True
            changed = _json(packet)
            with self.subTest(mutation=mutation), self.assertRaises(EvidenceRejected):
                self.authenticate([self.record()], packet=changed,
                                  expected_packet_sha256=hashlib.sha256(changed).hexdigest())

    def test_semantic_value_shapes_reject_boolean_and_unsupported_structures(self) -> None:
        for field, value in (("grain", False), ("grain", 0), ("grain", {"id": "order"}),
                             ("units", ["currency"]), ("snapshot_state", True),
                             ("population", []), ("time_rule", " unknown "),
                             ("time_zone", ""), ("null_policy", {"policy": False}),
                             ("missing_group_rule", {"policy": "zero", "extra": 1}),
                             ("join_cardinality", {"safe_for_comparison": True,
                                                   "relationship": "one_to_one", "extra": 1}),
                             ("join_cardinality", {"safe_for_comparison": False,
                                                   "relationship": "one_to_one"})):
            with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    EvidenceRejected, "unsupported semantic value shape"):
                self.authenticate([self.record(field=field, value=value)])

    def test_supported_shapes_remain_signed_assertions_only(self) -> None:
        for field, value in (("join_cardinality", {"safe_for_comparison": True,
                                                   "relationship": "one_to_one"}),
                             ("null_policy", {"policy": "preserve_null"}),
                             ("time_zone", "UTC")):
            with self.subTest(field=field):
                assertion, = self.authenticate([self.record(field=field, value=value)])[
                    "authenticated_signed_assertions"]
                self.assertEqual(assertion["value"], value)
                self.assertNotIn("status", assertion)

    def test_tampered_packet_with_internally_rehashed_binding_and_signature_rejected(self) -> None:
        tampered = json.loads(self.packet)
        tampered["source_commit"] = "b" * 40
        tampered_bytes = _json(tampered)
        tampered_hash = hashlib.sha256(tampered_bytes).hexdigest()
        claim = self.record()
        claim["binding"] = binding_for(tampered_bytes, self.pair_id, "metric.a",
                                       expected_packet_sha256=tampered_hash)
        claim["provenance"]["signature_ed25519"] = base64.b64encode(
            self.key.sign(review_signing_payload(claim))).decode("ascii")
        self.assertEqual(claim["binding"]["packet_sha256"], tampered_hash)
        with self.assertRaisesRegex(EvidenceRejected, "packet SHA256 mismatch"):
            self.authenticate([claim], packet=tampered_bytes)
        with self.assertRaisesRegex(EvidenceRejected, "packet SHA256 mismatch"):
            binding_for(tampered_bytes, self.pair_id, "metric.a",
                        expected_packet_sha256=self.expected_packet_sha256)

    def test_missing_or_malformed_trusted_packet_digest_rejected(self) -> None:
        with self.assertRaisesRegex(EvidenceRejected, "expected packet SHA256"):
            self.authenticate([self.record()], expected_packet_sha256="")
        with self.assertRaisesRegex(EvidenceRejected, "packet SHA256 mismatch"):
            self.authenticate([self.record()], expected_packet_sha256="0" * 64)

    def test_self_assertion_unpinned_key_and_tampering_rejected(self) -> None:
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record(reviewer_id="producer-1", producer="producer-1")])
        with self.assertRaisesRegex(EvidenceRejected, "not independently trusted"):
            self.authenticate([self.record(reviewer_id="unregistered")])
        other_key = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(EvidenceRejected, "signature does not authenticate"):
            self.authenticate([self.record(signer=other_key)])
        claim = self.record()
        claim["value"] = "customer"
        with self.assertRaisesRegex(EvidenceRejected, "signature does not authenticate"):
            self.authenticate([claim])

    def test_trusted_registry_must_assert_independence_and_type(self) -> None:
        registry = copy.deepcopy(self.reviewers)
        registry["reviewer-1"]["independent_of_producers"] = frozenset()
        with self.assertRaisesRegex(EvidenceRejected, "independence"):
            self.authenticate([self.record()], reviewers=registry)
        registry = copy.deepcopy(self.reviewers)
        registry["reviewer-1"]["reviewer_type"] = "automated"
        with self.assertRaisesRegex(EvidenceRejected, "type or method"):
            self.authenticate([self.record()], reviewers=registry)
        with self.assertRaisesRegex(EvidenceRejected, "roots and trusted reviewers"):
            self.authenticate([self.record()], roots={})
        with self.assertRaisesRegex(EvidenceRejected, "roots and trusted reviewers"):
            self.authenticate([self.record()], reviewers={})

    def test_all_or_nothing_duplicate_and_substantive_values(self) -> None:
        with self.assertRaisesRegex(EvidenceRejected, "duplicate semantic field"):
            self.authenticate([self.record(), self.record()])
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record(), self.record(locator="reviews/missing")])
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record(value="unknown")])
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record(field="join_cardinality", value={
                "safe_for_comparison": False, "relationship": "many_to_many"})])

    def test_no_commit_requires_absence_and_duplicate_json_keys_fail(self) -> None:
        packet = json.loads(self.packet)
        del packet["source_commit"]
        no_commit = _json(packet)
        self.assertNotIn("source_commit", binding_for(
            no_commit, self.pair_id, "metric.a",
            expected_packet_sha256=hashlib.sha256(no_commit).hexdigest()))
        with self.assertRaises(EvidenceRejected):
            self.authenticate([self.record()], packet=no_commit)
        duplicate_key = self.packet.replace(b'"packet_version":"test_i1"',
                                            b'"packet_version":"test_i1","packet_version":"test_i1"')
        with self.assertRaises(EvidenceRejected):
            binding_for(duplicate_key, self.pair_id, "metric.a",
                        expected_packet_sha256=hashlib.sha256(duplicate_key).hexdigest())

    def test_frozen_packet_shape_read_only(self) -> None:
        packet = (Path(__file__).parent / "compiled_jaffle_i1_packet.json").read_bytes()
        parsed = json.loads(packet)
        pair = next(p for p in parsed["pairs"] if p["scope_compatible"])
        card = next(c for c in parsed["cards"] if c["metric_id"] == pair["a"]
                    and c["sql_scope"] == pair["target_scope"])
        context = binding_for(packet, pair["pair_id"], card["metric_id"],
                              expected_packet_sha256=FROZEN_PACKET_SHA256)
        self.assertEqual(context["source_commit"], parsed["source_commit"])
        self.assertEqual(context["compiled_sql_sha256"], card["compiled_sql_sha256"])
        self.assertEqual(context["packet_sha256"], FROZEN_PACKET_SHA256)


if __name__ == "__main__":
    unittest.main()
