#!/usr/bin/env python3
"""Run frozen source decisions on any complete, label-free card universe.

This is a development-only portability probe. Missing decisive metadata causes
an explicit abstention for all methods. It never reads labels or row outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path

from normalized_sql_lineage_baseline import pair_result as normalized_sql_decide
from constraint_aware_baseline import decide as constraint_decide
from conditional_decision_method import decide as conditional_decide


REQUIRED_CARD_FIELDS = {
    "id", "metric_name", "grain", "source_ref", "value_expr", "where_expr",
    "period_expr", "segment_expr", "group_by", "time_key", "value_input_fields",
    "filter_input_fields", "source_location", "compiled_location", "review_flags",
    "unknown_semantics",
}
REQUIRED_SOURCE_EVIDENCE = (
    "grain", "source_ref", "value_expr", "period_expr"
)
UNKNOWN_FIELDS = {
    "join_cardinality", "null_policy", "missing_groups", "time_zone",
    "units", "snapshot", "grouping_set_expansion",
}
GTM_PROVENANCE = {
    "project", "commit", "source_model", "compiled_model", "dbt_version",
    "input_sha256", "evidence_scope",
}
YAML_PROVENANCE = {
    "project", "commit", "input_sha256", "evidence_scope", "yaml_inventory", "model_paths",
}
YAML_EXTRA_FIELDS = {
    "metric_type", "aggregation", "syntactic_status", "declared_primary_columns",
    "declared_expression", "declared_filter", "declared_dependencies",
}
BLOCKING_SOURCE_FLAGS = {
    "compiled_sql_unavailable", "grain_not_verified", "period_not_resolved",
    "source_relation_not_resolved", "filter_not_resolved", "unsupported_filter_shape",
    "metric_dependencies_not_resolved", "implicit_expression_not_resolved",
    "expression_requires_parser", "aggregation_missing", "malformed_metric_definition",
}
FORBIDDEN_OUTCOME_KEYS = {
    "label", "gold", "prediction", "matched", "row_values", "reconciliation",
    "ground_truth", "is_match", "score", "outcome", "adjudication",
}
METHODS = (
    ("normalized_sql_lineage_baseline", normalized_sql_decide),
    ("constraint_aware_full_context_v2", constraint_decide),
    ("proposed_conditional_explanation", conditional_decide),
)


def unique_object(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_outcome_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_OUTCOME_KEYS:
                raise ValueError(f"Outcome key in decision packet: {key}")
            reject_outcome_keys(child)
    elif isinstance(value, list):
        for child in value:
            reject_outcome_keys(child)


def string_or_none(value: object) -> bool:
    return value is None or isinstance(value, str)


def location(value: object, *, source: bool, yaml_source: bool) -> bool:
    if value is None:
        return not source
    required = {"path", "start_line", "end_line"}
    allowed = required | ({"document", "yaml_path"} if yaml_source and source else set())
    if not isinstance(value, dict) or not required <= value.keys() or set(value) != allowed:
        return False
    if not isinstance(value["path"], str) or not value["path"]:
        return False
    if any(not isinstance(value[k], int) or value[k] < 1 for k in ("start_line", "end_line")):
        return False
    if value["end_line"] < value["start_line"]:
        return False
    return (not yaml_source or not source or
            (isinstance(value["document"], int) and value["document"] >= 0
             and isinstance(value["yaml_path"], str)))


def validate_dependencies(value: object) -> bool:
    if not isinstance(value, dict) or not set(value) <= {
        "numerator", "denominator", "input_metric", "input_metrics", "type_params"
    }:
        return False
    if any(not isinstance(value[k], str) for k in ("numerator", "denominator", "input_metric") if k in value):
        return False
    if "type_params" in value and value["type_params"] not in ({}, None):
        return False  # Requires a versioned schema extension for future declarations.
    if "input_metrics" in value:
        deps = value["input_metrics"]
        if not isinstance(deps, list):
            return False
        for dep in deps:
            if (not isinstance(dep, dict) or not {"name"} <= dep.keys()
                    or not set(dep) <= {"name", "alias", "offset_window"}
                    or any(not isinstance(v, str) for v in dep.values())):
                return False
    return True


def validate(packet: dict) -> tuple[dict[str, dict], list[dict]]:
    if set(packet) != {"schema_version", "provenance", "cards", "pairs"} or packet["schema_version"] != 1:
        raise ValueError("Invalid label-free packet schema")
    reject_outcome_keys(packet)
    provenance = packet["provenance"]
    if not isinstance(provenance, dict) or set(provenance) not in (GTM_PROVENANCE, YAML_PROVENANCE):
        raise ValueError("Unrecognized provenance schema")
    yaml_source = set(provenance) == YAML_PROVENANCE
    if (not all(isinstance(provenance[k], str) and provenance[k] for k in
                ("project", "commit", "evidence_scope"))
            or not re.fullmatch(r"[0-9a-f]{40,64}", provenance["commit"]) 
            or not isinstance(provenance["input_sha256"], dict)
            or not provenance["input_sha256"]
            or any(not isinstance(k, str) or not isinstance(v, str)
                   or not re.fullmatch(r"[0-9a-f]{64}", v)
                   for k, v in provenance["input_sha256"].items())):
        raise ValueError("Malformed provenance or input hashes")
    if yaml_source:
        if (not isinstance(provenance["yaml_inventory"], str)
                or not isinstance(provenance["model_paths"], list)
                or any(not isinstance(p, str) for p in provenance["model_paths"])):
            raise ValueError("Malformed YAML inventory provenance")
    elif any(not isinstance(provenance[k], str) for k in
             ("source_model", "compiled_model", "dbt_version")):
        raise ValueError("Malformed compiled provenance")
    cards = packet["cards"]
    if not isinstance(cards, list) or len(cards) < 2 or len(cards) > 1000:
        raise ValueError("Card universe must have 2–1000 items")
    by_id = {}
    for card in cards:
        allowed = REQUIRED_CARD_FIELDS | (YAML_EXTRA_FIELDS if yaml_source else set())
        if not isinstance(card, dict) or set(card) != allowed:
            raise ValueError("Card is missing required evidence fields")
        if (not isinstance(card["id"], str) or not card["id"] or card["id"] in by_id
                or set(card["unknown_semantics"]) != UNKNOWN_FIELDS
                or not isinstance(card["review_flags"], list)
                or not isinstance(card["value_input_fields"], list)
                or not isinstance(card["filter_input_fields"], list)):
            raise ValueError("Duplicate/invalid card ID or evidence shape")
        if (any(not string_or_none(card[k]) for k in
                ("metric_name", "grain", "source_ref", "value_expr", "where_expr",
                 "period_expr", "segment_expr", "time_key"))
                or not (card["group_by"] is None or isinstance(card["group_by"], (str, list)))
                or any(not isinstance(x, str) for x in card["value_input_fields"] + card["filter_input_fields"]
                       + card["review_flags"])
                or any(value is not None for value in card["unknown_semantics"].values())
                or not location(card["source_location"], source=True, yaml_source=yaml_source)
                or not location(card["compiled_location"], source=False, yaml_source=False)):
            raise ValueError("Invalid card types or unverified semantics in portable packet")
        if yaml_source and (not all(string_or_none(card[k]) for k in
                                    ("metric_type", "aggregation", "syntactic_status", "declared_filter"))
                            or not (string_or_none(card["declared_expression"])
                                    or type(card["declared_expression"]) in (int, float))
                            or not isinstance(card["declared_primary_columns"], list)
                            or any(not isinstance(x, str) for x in card["declared_primary_columns"])
                            or not validate_dependencies(card["declared_dependencies"])):
            raise ValueError("Unrecognized source YAML metadata")
        by_id[card["id"]] = card
    pairs = packet["pairs"]
    expected = set(itertools.combinations(sorted(by_id), 2))
    observed = []
    for pair in pairs:
        if set(pair) != {"left_id", "right_id"}:
            raise ValueError("Pair contains non-ID fields")
        x, y = pair["left_id"], pair["right_id"]
        if x == y or x not in by_id or y not in by_id:
            raise ValueError("Pair refers to invalid ID")
        observed.append(tuple(sorted((x, y))))
    if len(observed) != len(expected) or set(observed) != expected:
        raise ValueError("Pairs must enumerate all unordered card combinations once")
    return by_id, pairs


def missing_evidence(card: dict) -> list[str]:
    fields = [name for name in REQUIRED_SOURCE_EVIDENCE if card[name] is None or card[name] == ""]
    if card["compiled_location"] is None:
        fields.append("compiled_source_unavailable")
    fields += [flag for flag in card["review_flags"] if flag in BLOCKING_SOURCE_FLAGS]
    if card.get("declared_filter") is not None and card["where_expr"] is None:
        fields.append("declared_filter_unresolved")
    return fields


def one_result(method: str, decide, a: dict, b: dict) -> dict:
    missing_a, missing_b = missing_evidence(a), missing_evidence(b)
    if missing_a or missing_b:
        return {
            "left_id": a["id"], "right_id": b["id"], "decision": "abstain",
            "evidence_status": "needs_review",
            "conditions": {"decisive_source_evidence": {
                "status": "unknown", "evidence": {"left_missing": missing_a, "right_missing": missing_b},
                "locations": [a["source_location"], b["source_location"]]}},
            "reasons": ["Missing or unsupported decisive source evidence; no source-backed relationship inferred."],
            "locations": {"left": a["source_location"], "right": b["source_location"]},
        }
    # Give frozen methods the fixed source-card schema only; the YAML carrier
    # and its raw filter declaration are validated above and cannot leak into
    # a method as an accidental feature.
    result = decide({key: a[key] for key in REQUIRED_CARD_FIELDS},
                    {key: b[key] for key in REQUIRED_CARD_FIELDS})
    # A source-only portable card is not a verified semantic relationship.
    result["evidence_status"] = "needs_review"
    return result


def generate(raw: bytes) -> dict:
    packet = json.loads(raw, object_pairs_hook=unique_object)
    by_id, pairs = validate(packet)
    missing_by_card = {ident: missing_evidence(card) for ident, card in by_id.items()
                       if missing_evidence(card)}
    report = {"purpose": "development_portability_probe_not_heldout_accuracy",
              "input_sha256": hashlib.sha256(raw).hexdigest(),
              "cards": len(by_id), "pairs": len(pairs),
              "cards_missing_decisive_evidence": missing_by_card, "methods": {}}
    for name, decide in METHODS:
        results = [one_result(name, decide, by_id[p["left_id"]], by_id[p["right_id"]])
                   for p in pairs]
        report["methods"][name] = {
            "counts": dict(sorted(Counter(r["decision"] for r in results).items())),
            "needs_review": sum(r["evidence_status"] == "needs_review" for r in results),
            "abstentions_due_to_missing_evidence": sum(
                "decisive_source_evidence" in r["conditions"] for r in results),
            "results": results,
        }
    return report


def render_md(report: dict) -> str:
    lines = ["# Portable source decision probe (development only)", "",
             f"Input SHA-256 `{report['input_sha256']}`; "
             f"{report['cards']} source cards and every one of their {report['pairs']} unordered pairs.",
             "No labels, built rows or held-out source are inputs. A candidate is a review hypothesis; "
             "all outcomes require domain-human review.", "",
             "| Method | Candidate decisions | Abstain | Pairs with missing decisive evidence |",
             "| --- | --- | ---: | ---: |"]
    for name, method in report["methods"].items():
        candidates = ", ".join(f"{decision}: {count}" for decision, count in
                               method["counts"].items() if decision != "abstain") or "none"
        lines.append(f"| `{name}` | {candidates} | {method['counts'].get('abstain', 0)} | "
                     f"{method['abstentions_due_to_missing_evidence']} |")
    lines += ["", f"Cards missing one or more required source fields: "
              f"{len(report['cards_missing_decisive_evidence'])}/{report['cards']}.",
              "The complete card/field list and every method decision appear in JSON. "
              "Missing period grouping, grain, source relation or value expression forces an abstention; "
              "unknown NULL, units, time and row-membership semantics remain review conditions.", "",
              "This bridge calls the frozen development decision functions and verifies a complete pair universe. "
              "It does not compile dbt, resolve YAML filters/model lineage, run Snowflake, or establish human gold. "
              "If source fields are absent, candidate coverage is a measurement of this bounded adapter rather than method accuracy.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, help="readable summary; defaults to output basename .md")
    parser.add_argument("--check", action="store_true", help="compare saved report without writing")
    args = parser.parse_args()
    report = generate(args.packet.read_bytes())
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    summary_path = args.summary or args.output.with_suffix(".md")
    summary = render_md(report)
    if args.check:
        if (args.output.read_text(encoding="utf-8") != content
                or summary_path.read_text(encoding="utf-8") != summary):
            raise ValueError("Saved portable report differs from regenerated decisions")
        print("Portable full-pair development report verified")
    else:
        args.output.write_text(content, encoding="utf-8")
        summary_path.write_text(summary, encoding="utf-8")
        print(f"Wrote portable development report to {args.output}")


if __name__ == "__main__":
    main()
