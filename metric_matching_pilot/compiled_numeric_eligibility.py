#!/usr/bin/env python3
"""Declaration-level numeric eligibility for a frozen compiled-metric packet.

This wraps the existing generic dbt declaration rule. A positive here is a
numeric *declaration candidate*, not runtime numeric certification, a metric
relationship, or an executed value. No names, labels, rows, or other reports
are read to decide eligibility.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

from compiled_jaffle_packet import canonical, sha256
from generic_metric_eligibility import eligibility, jinja


HERE = Path(__file__).resolve().parent
EXPECTED_PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"
VERSION = "compiled_numeric_declaration_gate_v2"


def _unknown(*reasons: str) -> dict:
    return {"status": "unknown", "reasons": sorted(set(reasons)),
            "runtime_numeric_certification": "unknown"}


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest_matches(value: object, expected: object) -> bool:
    if not _nonempty(value) or not isinstance(expected, str):
        return False
    try:
        return sha256(value.encode("utf-8")) == expected
    except UnicodeError:
        return False


def _filter_shape(value: object) -> bool:
    """The supported MetricFlow filter shape; other shapes need review."""
    if value is None:
        return True
    if not isinstance(value, dict) or set(value) != {"where_filters"}:
        return False
    filters = value["where_filters"]
    return (isinstance(filters, list) and bool(filters) and all(
        isinstance(part, dict) and set(part) == {"where_sql_template"} and
        _nonempty(part["where_sql_template"]) for part in filters))


def _explicit_type_reasons(*declarations: dict) -> list[str]:
    # The generic rule reads one type field. Check every explicit type at every
    # layer so a numeric metric type cannot hide a conflicting measure type.
    for declaration in declarations:
        for key in ("data_type", "dtype"):
            if key in declaration:
                value = declaration[key]
                if not _nonempty(value):
                    return ["explicit_type_not_known_numeric"]
                status, reasons = eligibility(
                    {"type": "simple", "agg": "sum", "data_type": value})
                if status != "eligible":
                    return reasons
    return []


def _span(value: object) -> bool:
    return (isinstance(value, list) and len(value) == 2 and
            all(type(n) is int and n > 0 for n in value) and value[0] <= value[1])


def classify(card: dict) -> dict:
    """Assess a packet card, without treating a self-declared hash as certification.

    The frozen packet hash in build() authenticates the extraction. An isolated
    card can only show internal consistency. Its dependency identifies a
    semantic-model resource, but the card does not independently prove that
    the named measure occurs in that model's source YAML.
    """
    if not isinstance(card, dict):
        return _unknown("malformed_card")
    metric_id = card.get("metric_id")
    if not _nonempty(metric_id):
        return _unknown("malformed_metric_id")
    parts = metric_id.split(".")
    if len(parts) != 3 or parts[0] != "metric" or not all(parts[1:]):
        return _unknown("malformed_metric_id")
    if (card.get("numeric_eligibility_status") != "not_certified_by_compiled_bundle" or
            card.get("runtime_numeric_certification") not in (None, "unknown")):
        return _unknown("numeric_certification_claim_unverified")
    if (not _digest_matches(card.get("compiled_sql"), card.get("compiled_sql_sha256")) or
            card.get("source_status") != "metricflow_sql_generated_not_executed" or
            card.get("sql_scope") not in ("ungrouped", "metric_time")):
        return _unknown("compiled_query_provenance_unverified")
    models = card.get("source_models")
    if (not isinstance(models, list) or not models or any(
            not isinstance(m, dict) or
            not _digest_matches(m.get("raw_sql"), m.get("raw_sql_sha256")) or
            not _nonempty(m.get("node")) or not _nonempty(m.get("source_file"))
            for m in models)):
        return _unknown("source_model_digest_unverified")
    model_nodes = {m["node"] for m in models}
    if len(model_nodes) != len(models):
        return _unknown("source_model_mapping_ambiguous")
    metric_type = card.get("type")
    measures = card.get("input_measures")
    if not isinstance(measures, list) or not measures:
        return _unknown("input_measure_missing")
    if metric_type != "simple":
        # Derived, ratio and cumulative calculations can be numerically
        # intended, but their types and denominators are unresolved here.
        if not isinstance(metric_type, str):
            return _unknown("missing_metric_type" if metric_type is None else "unsupported_type")
        item = {"type": metric_type, "expr": card.get("type_params_expr"),
                "filter": card.get("metric_filter")}
        _, reasons = eligibility(item)
        return _unknown(*reasons)
    if len(measures) != 1:
        return _unknown("simple_metric_measure_arity_unverified")
    measure = measures[0]
    if not isinstance(measure, dict) or not _nonempty(measure.get("measure")):
        return _unknown("malformed_measure")
    owners = measure.get("owners")
    if (not isinstance(owners, list) or len(owners) != 1 or
            type(measure.get("owner_count")) is not int or
            measure["owner_count"] != 1 or not isinstance(owners[0], dict)):
        return _unknown("measure_owner_ambiguous")
    owner = owners[0]
    nodes = owner.get("model_node")
    if (not isinstance(nodes, list) or len(nodes) != 1 or
            not _nonempty(nodes[0]) or nodes[0] not in model_nodes or
            not _nonempty(owner.get("semantic_model")) or
            "." in owner["semantic_model"] or
            jinja(owner["semantic_model"]) or jinja(measure["measure"]) or
            not _nonempty(owner.get("semantic_model_file")) or
            not _nonempty(owner.get("node_relation")) or
            not _span(owner.get("measure_span")) or
            not _span(owner.get("semantic_model_span")) or
            not (owner["semantic_model_span"][0] <= owner["measure_span"][0] <=
                 owner["measure_span"][1] <= owner["semantic_model_span"][1])):
        return _unknown("measure_source_mapping_unverified")
    # This is a resource-qualified manifest edge, not a match on a measure or
    # model name. Cross-package owners need a full owner resource ID in a
    # future schema; this packet only gives the short semantic-model name.
    semantic_node = f"semantic_model.{parts[1]}.{owner['semantic_model']}"
    if card.get("manifest_depends_on") != [semantic_node]:
        return _unknown("measure_manifest_dependency_unverified")
    if (card.get("input_metrics") != [] or card.get("numerator") is not None or
            card.get("denominator") is not None or
            card.get("cumulative_type_params") is not None):
        return _unknown("simple_metric_dependencies_unverified")
    if ("type_params_expr" not in card or "metric_filter" not in card or
            "filter" not in measure or "fill_nulls_with" not in measure or
            "expr" not in owner or "non_additive_dimension" not in owner):
        return _unknown("declaration_fields_missing")
    expr = card.get("type_params_expr")
    if expr is not None:
        if not isinstance(expr, str):
            return _unknown("malformed_metric_expression")
        return _unknown("jinja" if jinja(expr) else "simple_metric_expression_unverified")
    if (measure.get("fill_nulls_with") is not None or
            measure.get("join_to_timespine") is not False or
            owner.get("non_additive_dimension") is not None):
        return _unknown("measure_semantics_unverified")
    if not _filter_shape(card.get("metric_filter")) or not _filter_shape(measure.get("filter")):
        return _unknown("filter_schema_unverified")
    if jinja(measure.get("filter")):
        return _unknown("jinja")
    types = _explicit_type_reasons(card, measure, owner)
    if types:
        return _unknown(*types)
    if owner["expr"] is not None and not _nonempty(owner["expr"]):
        return _unknown("malformed_measure_expression")
    if jinja(owner.get("expr")):
        return _unknown("jinja_measure_expression")
    item = {"type": metric_type, "agg": owner.get("agg"),
            "expr": card.get("type_params_expr"), "filter": card.get("metric_filter")}
    for key in ("data_type", "dtype"):
        if key in card:
            item[key] = card[key]
    status, reasons = eligibility(item, aggregate=owner.get("agg"))
    return {"status": "eligible_declaration_only" if status == "eligible" else "unknown",
            "reasons": sorted(set(reasons)),
            "runtime_numeric_certification": "unknown"}


def build(packet_path: Path) -> dict:
    raw = packet_path.read_bytes()
    if sha256(raw) != EXPECTED_PACKET_SHA256:
        raise ValueError("numeric eligibility requires the frozen label-free v2 packet")
    packet = json.loads(raw)
    cards = packet["cards"]
    pairs = packet["pairs"]
    if (packet.get("packet_version") != "compiled_jaffle_i1_packet_v2" or
            not isinstance(cards, list) or len(cards) != 19 or
            not isinstance(pairs, list) or len(pairs) != 171 or
            packet.get("metric_count") != 19 or packet.get("pair_count") != 171):
        raise ValueError("incomplete development frame")
    ids = [card.get("metric_id") if isinstance(card, dict) else None for card in cards]
    if (any(not _nonempty(uid) for uid in ids) or len(set(ids)) != len(ids)):
        raise ValueError("missing or duplicate metric ID")
    expected_pairs = [(a, b) for a, b in itertools.combinations(sorted(ids), 2)]
    if ([pair.get("a") if isinstance(pair, dict) else None for pair in pairs] !=
            [a for a, _ in expected_pairs] or
            [pair.get("b") if isinstance(pair, dict) else None for pair in pairs] !=
            [b for _, b in expected_pairs] or
            any(pair.get("pair_id") != f"{a}||{b}" for pair, (a, b) in
                zip(pairs, expected_pairs)) or
            sha256(canonical([pair["pair_id"] for pair in pairs])) != packet.get("pair_set_sha256")):
        raise ValueError("incomplete or inconsistent pair frame")
    assessments = {card["metric_id"]: classify(card) for card in cards}
    if len(assessments) != len(cards):
        raise ValueError("duplicate metric ID")
    pair_counts = Counter(
        "both_eligible_declaration_only" if all(
            assessments[pair[key]]["status"] == "eligible_declaration_only" for key in ("a", "b"))
        else "at_least_one_unknown" for pair in pairs)
    return {
        "version": VERSION, "development_only": True,
        "packet_sha256": sha256(raw), "pair_set_sha256": packet["pair_set_sha256"],
        "rule_sha256": {name: sha256((HERE / name).read_bytes()) for name in
                        ("compiled_numeric_eligibility.py", "generic_metric_eligibility.py")},
        "metric_count": len(cards), "pair_count": len(packet["pairs"]),
        "status_counts": dict(sorted(Counter(a["status"] for a in assessments.values()).items())),
        "pair_status_counts": dict(sorted(pair_counts.items())),
        "assessments": assessments,
        "limits": ["Declaration-level numeric intent only; runtime type is unverified.",
                   "The frozen packet authenticates extraction; a card alone cannot verify its named measure in the source YAML.",
                   "Unknown declarations and every pair remain in the frame.",
                   "No relationship labels or human reference decisions were used."],
    }


def markdown(report: dict) -> str:
    lines = ["# Compiled Jaffle numeric declaration eligibility (development only)", "",
             f"Frozen packet SHA-256: `{report['packet_sha256']}`. Rules and source hashes are in JSON.",
             f"{report['metric_count']} exposed declarations; {report['pair_count']} unordered pairs retained.", "",
             "| Declaration state | Metrics |", "| --- | ---: |"]
    lines += [f"| `{name}` | {count} |" for name, count in report["status_counts"].items()]
    lines += ["", "| Pair state | Pairs |", "| --- | ---: |"]
    lines += [f"| `{name}` | {count} |" for name, count in report["pair_status_counts"].items()]
    lines += ["", "`eligible_declaration_only` means a simple metric has one measure entry,"
              " a unique owner with an exact semantic-model manifest dependency, a declared"
              " numeric aggregate, and no unresolved template in the relevant declaration."
              " The frozen packet authenticates extraction, but a card alone does not independently"
              " verify that measure's name in the source YAML. It is **not** `certified_numeric`."
              " Derived, ratio, cumulative and"
              " templated declarations remain unknown. The generated SQL was not executed;"
              " no semantic pair label, accuracy, or candidate Recall@k follows.", ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, default=HERE / "compiled_jaffle_i1_packet.json")
    p.add_argument("--json", type=Path, default=HERE / "compiled_numeric_eligibility_report.json")
    p.add_argument("--markdown", type=Path, default=HERE / "compiled_numeric_eligibility_report.md")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    report = build(a.packet)
    data, md = canonical(report), markdown(report).encode("utf-8")
    if a.check:
        if a.json.read_bytes() != data or a.markdown.read_bytes() != md:
            raise SystemExit("numeric eligibility report differs from frozen output")
        print("numeric eligibility OK", hashlib.sha256(data).hexdigest())
    else:
        a.json.write_bytes(data)
        a.markdown.write_bytes(md)
        print("wrote numeric eligibility", hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
