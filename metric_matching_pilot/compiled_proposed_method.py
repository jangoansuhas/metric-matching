"""Source-linked conditional review hypotheses on the common I1 metric cards.

This method consumes only two cards from the frozen packet. It uses SQLGlot's
DuckDB AST through the same parsing utilities as the AST baseline, but never
reads a baseline result, label, row reconciliation, or a repository. A review
hypothesis and ordinal score are distinct from a semantic taxonomy decision.
"""

from __future__ import annotations

import hashlib
from typing import Any

import compiled_ast_lineage_baseline as ast
from compiled_numeric_eligibility import classify


VERSION = "compiled_conditional_review_v1"


def _result(signal: str, reason: str, evidence: list, *, score: float | None = None,
            hypothesis: str | None = None, obligations: dict | None = None) -> dict:
    return {"signal": signal, "decision": "abstain", "candidate_score": score,
            "candidate_hypothesis": hypothesis, "obligations": obligations or {},
            "evidence": evidence, "reason": reason}


def _digest_ok(card: dict) -> bool:
    sql = card.get("compiled_sql")
    models = card.get("source_models")
    if (not isinstance(sql, str) or not sql.strip() or
            hashlib.sha256(sql.encode("utf-8")).hexdigest() != card.get("compiled_sql_sha256") or
            card.get("source_status") != "metricflow_sql_generated_not_executed" or
            not isinstance(models, list) or not models):
        return False
    return all(isinstance(model, dict) and isinstance(model.get("raw_sql"), str)
               and isinstance(model.get("node"), str)
               and hashlib.sha256(model["raw_sql"].encode("utf-8")).hexdigest()
                   == model.get("raw_sql_sha256") for model in models)


def _dependency(derived: dict, input_card: dict) -> bool:
    """Require the manifest edge and exact declaration input reference."""
    if (derived.get("type") not in {"derived", "ratio"} or
            input_card.get("metric_id") not in derived.get("manifest_depends_on", [])):
        return False
    name = input_card.get("metric_name")
    if derived["type"] == "derived":
        refs = derived.get("input_metrics")
        return isinstance(refs, list) and any(
            isinstance(ref, dict) and ref.get("name") == name for ref in refs)
    return name in (derived.get("numerator"), derived.get("denominator"))


def _location(card: dict) -> dict:
    return {"metric_id": card["metric_id"],
            "declaration_file": card.get("declared_file"),
            "text_located_span": card.get("declared_span_text_located"),
            "source_model_files": sorted({m.get("source_file") for m in card["source_models"]
                                          if isinstance(m, dict) and isinstance(m.get("source_file"), str)}),
            "generated_sql_sha256": card["compiled_sql_sha256"]}


def _obligations(a: dict, b: dict, *, same_ast: bool, same_measure: bool,
                 filters_a: list[str], filters_b: list[str]) -> dict:
    eligibility = [classify(a), classify(b)]
    observed_filter = ("same_declaration_and_compiled_predicate" if
                       a.get("metric_filter") == b.get("metric_filter") and filters_a == filters_b
                       else "different_or_unresolved_predicate")
    return {
        "declaration_numeric_eligibility": {"state": "declaration_only" if all(
            e["status"] == "eligible_declaration_only" for e in eligibility) else "unknown",
            "per_metric": [e["status"] for e in eligibility]},
        "generated_query_integrity": {"state": "observed_hash_match"},
        "declared_metric_to_measure_owner": {"state": "observed_unique_owner"},
        "identical_generated_scope_ast": {"state": "observed" if same_ast else "different_syntax"},
        "same_declared_measure_owner": {"state": "observed" if same_measure else "different_or_unresolved"},
        "compiled_filter_alignment": {"state": observed_filter,
                                      "left_where": filters_a, "right_where": filters_b},
        # No scalar AST, same-source table, or manifest dependency fills these.
        "runtime_numeric_type": {"state": "unknown"},
        "metric_expression_field_lineage": {"state": "unknown"},
        "grain_and_rollup": {"state": "unknown"},
        "time_grain_and_window": {"state": "unknown"},
        "population_and_filter_meaning": {"state": "unknown"},
        "join_cardinality": {"state": "unknown"},
        "missing_group_rule": {"state": "unknown"},
        "null_policy": {"state": "unknown"},
        "units": {"state": "unknown"},
        "snapshot_state": {"state": "unknown"},
    }


def compare(card_a: dict, card_b: dict) -> dict:
    """Return an ordinal review priority and named proof obligations, no label."""
    if not isinstance(card_a, dict) or not isinstance(card_b, dict):
        return _result("unsupported_input", "Both inputs must be metric cards.", [])
    a, b = card_a, card_b
    ids = (a.get("metric_id"), b.get("metric_id"))
    if not all(isinstance(x, str) and x for x in ids) or ids[0] == ids[1]:
        return _result("unsupported_input", "Expected distinct metric IDs.", [])
    if a.get("sql_scope") != b.get("sql_scope"):
        return _result("incompatible_generated_scope", "No common generated SQL scope.",
                       [{"metric_ids": list(ids)}])
    if a.get("sql_scope") not in {"ungrouped", "metric_time"} or not _digest_ok(a) or not _digest_ok(b):
        return _result("compiled_provenance_needs_review", "Compiled query/source digest or scope is unverified.",
                       [{"metric_ids": list(ids)}])
    if ast.sqlglot is None or ast.sqlglot.__version__ != ast.SQLGLOT_PIN:
        return _result("unsupported_parser", f"Requires SQLGlot {ast.SQLGLOT_PIN}.",
                       [{"metric_ids": list(ids)}])
    try:
        trees = [ast._parse(c["compiled_sql"]) for c in (a, b)]
        scalars = [ast._outer(t, c["sql_scope"]) for t, c in zip(trees, (a, b))]
        features = [ast._features(t, s[0]) for t, s in zip(trees, scalars)]
        normalized = [ast._normal_ast(t) for t in trees]
        parsed = [ast._card(c) for c in (a, b)]
        measure_keys = [ast._measure_keys(c) for c in parsed]
    except (ValueError, KeyError, TypeError, ast.sqlglot.errors.SqlglotError) as exc:
        return _result("unsupported_sql_or_card", f"Parser/binding failed: {type(exc).__name__}: {str(exc)[:120]}",
                       [{"metric_ids": list(ids)}])
    if (not all(ok for _, ok in measure_keys) or
            not all(ast._owner_sources_match(c, f) for c, f in zip(parsed, features))):
        return _result("owner_lineage_needs_review", "A unique owner-to-compiled-source link is unavailable.",
                       [_location(a), _location(b)])
    keys_a, keys_b = measure_keys[0][0], measure_keys[1][0]
    same_measure = bool(keys_a) and keys_a == keys_b
    shared_measure = bool(keys_a & keys_b)
    same_ast = normalized[0] == normalized[1]
    declared_dependency = _dependency(a, b) or _dependency(b, a)
    declared_filter_difference = a.get("metric_filter") != b.get("metric_filter")
    compiled_filter_difference = features[0]["filters"] != features[1]["filters"]
    same_sources = (bool(features[0]["sources"]) and
                    features[0]["sources"] == features[1]["sources"])
    model_nodes = [{m["node"] for m in c["source_models"]} for c in (a, b)]
    source_model_same = bool(model_nodes[0]) and model_nodes[0] == model_nodes[1]
    obligations = _obligations(a, b, same_ast=same_ast, same_measure=same_measure,
                               filters_a=features[0]["filters"], filters_b=features[1]["filters"])
    evidence: list[Any] = [_location(a), _location(b),
        {"observed_metric_types": [a.get("type"), b.get("type")],
         "declared_measure_names": [sorted(k[0] for k in keys_a), sorted(k[0] for k in keys_b)],
         "manifest_depends_on": [a.get("manifest_depends_on"), b.get("manifest_depends_on")],
         "compiled_sources": [features[0]["sources"], features[1]["sources"]],
         "compiled_filters": [features[0]["filters"], features[1]["filters"]],
         "normalized_ast_sha256": [hashlib.sha256(n.sql(dialect=ast.DIALECT).encode()).hexdigest()
                                   for n in normalized]}]

    if (a["sql_scope"] == "ungrouped" and same_ast and same_measure and same_sources
            and {a.get("type"), b.get("type")} == {"simple", "cumulative"}):
        return _result("time_semantics_review",
                       "Same ungrouped AST cannot establish the cumulative time window.", evidence,
                       score=1.0,
                       hypothesis="Generate aligned time-grain queries and inspect cumulative-window, missing-group, and NULL rules before classifying this pair.",
                       obligations=obligations)
    if declared_dependency:
        return _result("declared_input_review",
                       "One declaration references the other as an exact metric input; the transformation is not proven equivalent.",
                       evidence, score=0.8,
                       hypothesis="Trace the declared input through the generated scalar expression and test its transformation at aligned grain and snapshot.",
                       obligations=obligations)
    if same_measure and declared_filter_difference and compiled_filter_difference:
        return _result("filter_scope_review",
                       "Same declared measure owner has different declared and generated query filters; compiled field lineage and population inclusion are unproved.",
                       evidence, score=0.6,
                       hypothesis="Resolve both filter predicates against source rows, then reconcile the same measure at a common grain, time scope, and snapshot.",
                       obligations=obligations)
    if same_ast and same_measure and same_sources:
        return _result("same_ast_review",
                       "Matching syntax and declared measure ownership are review evidence, not semantic equivalence.",
                       evidence, score=0.5,
                       hypothesis="Verify population, time, grain, NULL, units, and snapshot before an equivalence decision.",
                       obligations=obligations)
    if shared_measure:
        return _result("shared_measure_review",
                       "An input measure is shared by declaration while the scalar AST differs; compiled field lineage remains unknown.", evidence,
                       score=0.4,
                       hypothesis="Trace the distinct transformations and filters before assigning a relationship.",
                       obligations=obligations)
    if source_model_same:
        return _result("same_model_review",
                       "Model co-location is a weak review signal and gives no semantic class.", evidence,
                       score=0.2,
                       obligations=obligations)
    return _result("insufficient_relation_evidence",
                   "No supported relationship rule fired from these source artifacts.", evidence,
                   score=0.0, obligations=obligations)
