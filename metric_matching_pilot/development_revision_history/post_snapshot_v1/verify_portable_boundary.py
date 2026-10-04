#!/usr/bin/env python3
"""Check portable runner boundary cases without reading outcomes or held-out source."""

import copy
import json
from pathlib import Path

from run_portable_development_methods import (
    METHODS, REQUIRED_SOURCE_EVIDENCE, generate, missing_evidence, one_result,
)


BASE = Path(__file__).resolve().parent


def expect_rejected(packet: dict, reason: str) -> None:
    try:
        generate(json.dumps(packet).encode("utf-8"))
    except ValueError:
        return
    raise AssertionError(f"Packet with {reason} was accepted")


def main() -> None:
    gtm_raw = (BASE / "conditional_evidence_packet.json").read_bytes()
    report = generate(gtm_raw)
    original = {
        "normalized_sql_lineage_baseline": "normalized_sql_lineage_report.json",
        "constraint_aware_full_context_v2": "constraint_aware_report.json",
        "proposed_conditional_explanation": "conditional_decision_report.json",
    }
    for method, filename in original.items():
        expected = json.loads((BASE / filename).read_text(encoding="utf-8"))
        assert report["methods"][method]["results"] == expected["results"], method

    yaml = json.loads((BASE / "portable_jaffle_packet.json").read_text(encoding="utf-8"))
    counts = generate(json.dumps(yaml).encode("utf-8"))
    assert counts["cards"] == 23 and counts["pairs"] == 253
    assert all(m["counts"] == {"abstain": 253}
               for m in counts["methods"].values())

    filtered = copy.deepcopy(next(c for c in yaml["cards"] if c["declared_filter"]))
    plain = copy.deepcopy(next(c for c in yaml["cards"] if not c["declared_filter"]))
    for card in (filtered, plain):
        card["review_flags"] = []  # Verify raw filter gate independently.
        for field in REQUIRED_SOURCE_EVIDENCE:
            card[field] = f"controlled_{field}"
        card["compiled_location"] = {"path": "controlled.sql", "start_line": 1, "end_line": 1}
    assert missing_evidence(plain) == []
    assert missing_evidence(filtered) == ["declared_filter_unresolved"]
    for name, decide in METHODS:
        result = one_result(name, decide, filtered, plain)
        assert result["decision"] == "abstain" and result["evidence_status"] == "needs_review", name

    for field in ("row_values", "label", "reconciliation"):
        bad = copy.deepcopy(yaml)
        bad["cards"][0]["declared_dependencies"][field] = "secret"
        expect_rejected(bad, f"nested {field}")
    bad = copy.deepcopy(yaml)
    bad["provenance"]["outcome"] = "secret"
    expect_rejected(bad, "provenance outcome")
    bad = copy.deepcopy(yaml)
    bad["cards"][0]["source_location"]["row_values"] = "secret"
    expect_rejected(bad, "location outcome")
    bad = copy.deepcopy(yaml)
    bad["pairs"][0]["gold"] = True
    expect_rejected(bad, "pair gold")
    bad = copy.deepcopy(yaml)
    bad["cards"][0]["custom_feature"] = "secret"
    expect_rejected(bad, "unexpected card feature")
    bad = (BASE / "portable_jaffle_packet.json").read_bytes().replace(
        b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1', 1)
    try:
        generate(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate JSON property was accepted")
    print("Portable boundary checks passed: exact 55-pair replay, 253 safe abstentions, "
          "unresolved filter guard, nested-outcome rejection, schema and duplicate keys")


if __name__ == "__main__":
    main()
