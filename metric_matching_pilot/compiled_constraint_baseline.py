"""Constraint-aware comparator for label-free compiled metric cards.

``compare`` consumes only its two I1 cards.  It does not read reports, labels,
rows, repositories, or a method's previous output.  A source_status of
``verified`` must mean *metric-expression* provenance; a verified compiled
model is insufficient.  Bare semantic values are treated as declarations in
that provenance, while null/unknown values remain unresolved.  In particular,
textually identical SQL, names, and manifest model dependencies do not prove
that two metric expressions have the same field owner or business meaning.
``generated_compiled`` records a checked MetricFlow SQL artifact whose query
has not been executed or certified as an end-to-end metric expression.

The six decision strings follow annotation_schema.json.  ``signal`` is a
source-review observation, not an equivalence assertion.  All decisions are
conservative source classifications; no query-equivalence theorem is claimed.

The uncalibrated candidate_score is the number of four exact source features
divided by four: uniquely owned input-measure IDs, documented metric type plus
aggregate and expression, declared filter *on the same bound measure*, and
compiled SQL bytes.  An unknown feature contributes zero.  Incompatible scopes or failed artifact hashes get
a null score.  Ranking ties are resolved by the lexical order of the sorted
pair of metric IDs; there is no decision threshold or fitted weight.  It ranks
source-review candidates even when numeric eligibility is not certified.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


DECISIONS = frozenset({
    "direct_equivalent", "cross_grain_equivalent", "temporal_or_scope_variant",
    "related", "conflicting_definition", "non_match", "abstain",
})
_VERIFIED = {"verified", "verified_from_source", "verified_compiled_metric_expression"}
_UNKNOWN = {"", "unknown", "unverified", "needs_review", "unsupported", "not_supplied"}
_METRIC_SCOPES = {"ungrouped", "metric_time", "metric", "metric_query",
                  "compiled_metric_query", "metric_expression"}
_SAFE_JOINS = {"no_join", "none", "one_to_one", "many_to_one", "1:1", "n:1"}


def _pick(card: dict, *names: str) -> tuple[Any, bool]:
    for name in names:
        if name in card:
            return card[name], True
    return None, False


def _semantic(card: dict, *names: str) -> tuple[Any, bool]:
    # The harness's explicit unknown takes precedence over a descriptive
    # declaration copied into a top-level field.
    unknowns = card.get("unknown_semantics")
    if isinstance(unknowns, dict):
        for name in names:
            if name in unknowns:
                return unknowns[name], True
    return _pick(card, *names)


def _known(value: Any) -> tuple[str, Any]:
    """Return evidence state and value, without treating an absent NULL as zero."""
    if isinstance(value, dict) and ("status" in value or "state" in value):
        status = str(value.get("status", value.get("state"))).lower()
        if status in {"not_applicable", "n/a"}:
            return "not_applicable", value.get("reason")
        if status == "contradicted":
            return "contradicted", value.get("value")
        if status not in _VERIFIED:
            return "unknown", None
        value = value.get("value")
    if value is None or isinstance(value, str) and value.strip().lower() in _UNKNOWN:
        return "unknown", None
    return "verified", value


def _key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _same(left: Any, right: Any) -> bool:
    # Edge whitespace in declarations is immaterial; inner SQL syntax, quoted
    # literals, and NULL operators are deliberately never rewritten.
    if isinstance(left, str) and isinstance(right, str):
        return left.strip() == right.strip()
    return _key(left) == _key(right)


def _condition(left: Any, right: Any, *, absent_is_none: bool = False) -> dict:
    ls, lv = _known(left)
    rs, rv = _known(right)
    if absent_is_none:
        # A present filter: null means an explicitly unfiltered declaration.
        ls, lv = ("verified", None) if left is None else (ls, lv)
        rs, rv = ("verified", None) if right is None else (rs, rv)
    if "contradicted" in (ls, rs):
        state = "contradicted"
    elif "unknown" in (ls, rs) or ls != rs:
        state = "unknown"
    elif ls == "not_applicable":
        state = "not_applicable"
    else:
        state = "verified" if _same(lv, rv) else "contradicted"
    return {"state": state, "left": lv if ls == "verified" else ls,
            "right": rv if rs == "verified" else rs}


def _field(a: dict, b: dict, *names: str, semantic: bool = False,
           explicit_null: bool = False) -> dict:
    fetch = _semantic if semantic else _pick
    av, ap = fetch(a, *names)
    bv, bp = fetch(b, *names)
    if not ap or not bp:
        return {"state": "unknown", "left": av if ap else "missing",
                "right": bv if bp else "missing"}
    return _condition(av, bv, absent_is_none=explicit_null)


def _status(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("status", value.get("state"))
    return str(value).lower() if value is not None else "unknown"


def _scope(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("level", value.get("scope", value.get("kind")))
    return str(value).lower() if value is not None else "unknown"


def _measures(card: dict) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    items, present = _pick(card, "input_measures")
    if not present or not isinstance(items, (list, tuple)) or not items:
        return (), (), "unknown"
    owners, _ = _pick(card, "input_measure_owners", "measure_owners", "owners")
    ids: list[str] = []
    names: list[str] = []
    for item in items:
        if isinstance(item, str):
            name, identifier, owner = item, None, None
        elif isinstance(item, dict):
            name = item.get("measure", item.get("name"))
            identifier = item.get("measure_id", item.get("id"))
            owner = item.get("owner", item.get("semantic_model_id", item.get("model_id")))
            if owner is None:
                owner = item.get("owners")
            if "owner_count" in item and item["owner_count"] != 1:
                return (), tuple(sorted(names)), "unknown"
        else:
            return (), (), "unknown"
        if not isinstance(name, str) or not name.strip():
            if not isinstance(identifier, str) or not identifier.strip():
                return (), (), "unknown"
            name = identifier
        names.append(name)
        if owner is None and isinstance(owners, dict):
            owner = owners.get(name)
        elif owner is None and isinstance(owners, str):
            owner = owners
        elif owner is None and isinstance(owners, (list, tuple)) and len(owners) == 1:
            owner = owners[0]
        if isinstance(owner, (list, tuple, set)):
            owner = next(iter(owner)) if len(owner) == 1 else None
        if isinstance(owner, dict):
            nodes = owner.get("model_node")
            if isinstance(nodes, list) and len(nodes) == 1 and isinstance(nodes[0], str):
                node = nodes[0]
            elif isinstance(owner.get("model_id"), str):
                node = owner["model_id"]
            else:
                return (), tuple(sorted(names)), "unknown"
            model = owner.get("semantic_model", owner.get("semantic_model_id"))
            owner = f"{node}/{model}" if isinstance(model, str) and model else None
        # Resource-qualified manifest IDs are unique even without a separate
        # owner.  A name-only match is never a verified measure binding.
        qualified = isinstance(identifier, str) and any(c in identifier for c in (".", ":", "/"))
        if qualified:
            ids.append("id:" + identifier)
        elif isinstance(owner, str) and owner.strip():
            ids.append("owner:" + owner + "/" + name)
        else:
            return (), tuple(sorted(names)), "unknown"
    if len(ids) != len(set(ids)):
        return (), tuple(sorted(names)), "unknown"
    return tuple(sorted(ids)), tuple(sorted(names)), "verified"


def _owner_values(card: dict, field: str) -> Any:
    """Keep per-measure metadata in owner/name order, including nulls."""
    _, _, status = _measures(card)
    items = card.get("input_measures")
    if status != "verified" or not isinstance(items, list):
        return None
    values = []
    for item in items:
        if not isinstance(item, dict):
            return None
        owners = item.get("owners")
        if isinstance(owners, list) and len(owners) == 1 and isinstance(owners[0], dict):
            value = owners[0].get(field)
            owner = owners[0]
            ident = (tuple(owner.get("model_node", [])), owner.get("semantic_model"),
                     item.get("measure", item.get("name")))
        else:
            value = item.get(field)
            ident = (str(item.get("owner")), "", item.get("name"))
        values.append((ident, value))
    return [value for _, value in sorted(values)]


def _measure_option(card: dict, field: str) -> Any:
    items = card.get("input_measures")
    if not isinstance(items, list) or not items or any(not isinstance(i, dict) for i in items):
        return None
    if any(field not in i for i in items):
        return None
    values = []
    for item in items:
        owners = item.get("owners")
        if isinstance(owners, list) and len(owners) == 1 and isinstance(owners[0], dict):
            owner = owners[0]
            identity = (str(owner.get("model_node")), str(owner.get("semantic_model")),
                        str(item.get("measure", item.get("name"))))
        else:
            identity = (str(item.get("owner")), "", str(item.get("name")))
        values.append((identity, item[field]))
    return [value for _, value in sorted(values)]


def _model_nodes(card: dict) -> tuple[str, ...]:
    models = card.get("source_models")
    if not isinstance(models, list):
        return ()
    return tuple(sorted({model["node"] for model in models if isinstance(model, dict)
                         and isinstance(model.get("node"), str)}))


def _model_fingerprint(card: dict) -> Any:
    models = card.get("source_models")
    if not isinstance(models, list) or not models:
        return None
    return sorted((model.get("node"), model.get("raw_sql_sha256"), model.get("source_file"))
                  for model in models if isinstance(model, dict))


def _source_models_ok(card: dict) -> bool:
    models = card.get("source_models")
    if not isinstance(models, list) or not models:
        return False
    nodes = set()
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get("node"), str):
            return False
        raw = model.get("raw_sql")
        claimed = model.get("raw_sql_sha256")
        if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != claimed:
            return False
        nodes.add(model["node"])
    owners = card.get("input_measures")
    if not isinstance(owners, list):
        return False
    owned_nodes = {node for item in owners if isinstance(item, dict)
                   for owner in item.get("owners", []) if isinstance(owner, dict)
                   for node in owner.get("model_node", [])}
    return bool(owned_nodes) and owned_nodes == nodes


def _dependencies(card: dict) -> tuple[str, ...]:
    value = card.get("manifest_depends_on")
    if isinstance(value, dict):
        value = value.get("nodes")
    if not isinstance(value, (list, tuple)) or any(not isinstance(v, str) for v in value):
        return ()
    return tuple(sorted(set(value)))


def _sql(card: dict) -> str | None:
    value = card.get("compiled_sql")
    return value if isinstance(value, str) and value.strip() else None


def _definition(a: dict, b: dict) -> dict:
    typ = _field(a, b, "metric_type", "type")
    av, ap = _pick(a, "agg", "aggregation", "aggregate")
    bv, bp = _pick(b, "agg", "aggregation", "aggregate")
    agg = _condition(av if ap else _owner_values(a, "agg"),
                     bv if bp else _owner_values(b, "agg"))
    av, ap = _pick(a, "expr", "declared_expression", "type_params_expr")
    bv, bp = _pick(b, "expr", "declared_expression", "type_params_expr")
    # A null owner expr means an implicit/default field in this packet; do not
    # turn the matching column/measure name into proven field lineage.
    expr = _condition(av if ap and av is not None else _owner_values(a, "expr"),
                      bv if bp and bv is not None else _owner_values(b, "expr"))
    if ((not ap or av is None) and None in (_owner_values(a, "expr") or []) or
            (not bp or bv is None) and None in (_owner_values(b, "expr") or [])):
        expr["state"] = "unknown"
    transform = _condition(
        [a.get("type_params_expr"), a.get("numerator"), a.get("denominator"),
         a.get("cumulative_type_params"), a.get("input_metrics")],
        [b.get("type_params_expr"), b.get("numerator"), b.get("denominator"),
         b.get("cumulative_type_params"), b.get("input_metrics")])
    measure_filter = _condition(_measure_option(a, "filter"), _measure_option(b, "filter"))
    nonadditive = _condition(_owner_values(a, "non_additive_dimension"),
                             _owner_values(b, "non_additive_dimension"))
    # Null aggregate/expr values are source observations, but insufficient to
    # certify a direct relationship.  The structure can still inform signals.
    states = (typ["state"], agg["state"], expr["state"], transform["state"],
              measure_filter["state"], nonadditive["state"])
    state = ("contradicted" if "contradicted" in states else
             "unknown" if "unknown" in states else "verified")
    return {"state": state, "metric_type": typ, "agg": agg, "expr": expr,
            "metric_transformation": transform, "input_measure_filter": measure_filter,
            "non_additive_dimension": nonadditive}


def _verified(*conditions: dict) -> bool:
    return all(item["state"] in {"verified", "not_applicable"} for item in conditions)


def _numeric_eligibility(a: dict, b: dict) -> dict:
    """A compiled scalar SQL result alone is not a certified numeric metric."""
    statuses = [_status(card.get("numeric_eligibility_status")) for card in (a, b)]
    certified = {"certified_numeric", "verified_numeric"}
    return {"state": "verified" if all(s in certified for s in statuses) else "unknown",
            "left": statuses[0], "right": statuses[1]}


def compare(card_a: dict, card_b: dict) -> dict:
    """Compare two cards; return a review signal and a guarded six-class decision.

    Supported source_status: verified metric expression, or an explicit
    unresolved status.  ``sql_scope`` must identify a compiled metric query;
    a compiled model SQL body is not a metric expression.  The parent harness
    supplies independently documented grain, join cardinality, snapshot/state,
    units, missing-group and NULL rules.  Unknowns block semantic labels.
    """
    if not isinstance(card_a, dict) or not isinstance(card_b, dict):
        raise TypeError("compare expects two metric-card dictionaries")
    a, b = card_a, card_b
    aid = a.get("metric_id", a.get("id"))
    bid = b.get("metric_id", b.get("id"))
    aname = a.get("metric_name", a.get("name"))
    bname = b.get("metric_name", b.get("name"))
    ma, na, mas = _measures(a)
    mb, nb, mbs = _measures(b)
    qa, qb = _sql(a), _sql(b)
    sa, sb = _status(a.get("source_status")), _status(b.get("source_status"))
    sca, scb = _scope(a.get("sql_scope")), _scope(b.get("sql_scope"))
    source_ok = sa in _VERIFIED and sb in _VERIFIED
    eligibility = _numeric_eligibility(a, b)
    digest_ok = all(q is not None and hashlib.sha256(q.encode()).hexdigest() == c.get("compiled_sql_sha256")
                    for q, c in ((qa, a), (qb, b)))
    model_ok = _source_models_ok(a) and _source_models_ok(b)
    query_ok = (digest_ok and model_ok and qa is not None and qb is not None
                and sca == scb and sca in _METRIC_SCOPES)
    generated = sa == sb == "metricflow_sql_generated_not_executed"
    provenance = {"state": ("verified" if source_ok and query_ok else
                             "generated_compiled" if generated and query_ok else "unknown"),
                  "left": {"source_status": sa, "sql_scope": sca,
                           "sql_sha256_matches": qa is not None and
                           hashlib.sha256(qa.encode()).hexdigest() == a.get("compiled_sql_sha256"),
                           "source_models_aligned": _source_models_ok(a)},
                  "right": {"source_status": sb, "sql_scope": scb,
                            "sql_sha256_matches": qb is not None and
                            hashlib.sha256(qb.encode()).hexdigest() == b.get("compiled_sql_sha256"),
                            "source_models_aligned": _source_models_ok(b)}}
    binding = {"state": "verified" if mas == mbs == "verified" and ma == mb else
               "contradicted" if mas == mbs == "verified" else "unknown",
               "left": list(ma or na), "right": list(mb or nb)}
    model_identity = _condition(_model_fingerprint(a), _model_fingerprint(b))
    definition = _definition(a, b)
    filt = _field(a, b, "metric_filter", "filter", "declared_filter", "declared_metric_filter",
                  explicit_null=True)
    # A missing filter in two declarations says only that neither declares a
    # metric-level filter. It cannot establish a common population across two
    # different measures/models or certify the base population even on one.
    base_population = _field(a, b, "base_population", "population_domain", semantic=True)
    # None is an explicit lack of fill_nulls_with; it does not resolve the
    # separate NULL or absent-group policy. False disables a time-spine join.
    fa, fap = _pick(a, "fill_nulls", "fill_nulls_with")
    fb, fbp = _pick(b, "fill_nulls", "fill_nulls_with")
    fill = _condition(fa if fap else _measure_option(a, "fill_nulls_with"),
                      fb if fbp else _measure_option(b, "fill_nulls_with"), absent_is_none=True)
    spa, sap = _pick(a, "join_to_timespine")
    spb, sbp = _pick(b, "join_to_timespine")
    spine = _condition(spa if sap else _measure_option(a, "join_to_timespine"),
                       spb if sbp else _measure_option(b, "join_to_timespine"))
    grain = _field(a, b, "grain", "native_grain", semantic=True)
    ta, tap = _semantic(a, "agg_time_dimension", "time_dimension")
    tb, tbp = _semantic(b, "agg_time_dimension", "time_dimension")
    time_key = _condition(ta if tap else _owner_values(a, "agg_time_dimension"),
                          tb if tbp else _owner_values(b, "agg_time_dimension"))
    timezone = _field(a, b, "time_zone", "timezone", semantic=True)
    join = _field(a, b, "join_cardinality", semantic=True)
    if join["state"] == "verified" and str(join["left"]).lower() not in _SAFE_JOINS:
        join["state"] = "unknown"  # Equal unsafe fanout is not a safe join.
    missing = _field(a, b, "missing_group_policy", "missing_group_rule", "missing_groups",
                     semantic=True)
    null = _field(a, b, "null_policy", semantic=True)
    snapshot = _field(a, b, "snapshot", "snapshot_id", semantic=True)
    state = _field(a, b, "business_state", "state", "snapshot_state", semantic=True)
    units = _field(a, b, "units", "unit", semantic=True)
    if qa is None or qb is None:
        sql_match = {"state": "unknown", "left": qa is not None, "right": qb is not None}
    else:
        sql_match = {"state": "verified" if qa == qb else "contradicted",
                     "left": hashlib.sha256(qa.encode()).hexdigest(),
                     "right": hashlib.sha256(qb.encode()).hexdigest()}
    deps_a, deps_b = _dependencies(a), _dependencies(b)
    deps = {"state": ("verified" if deps_a and deps_b and deps_a == deps_b else
                      "contradicted" if deps_a and deps_b else "unknown"),
            "left": list(deps_a), "right": list(deps_b)}
    prerequisites = {
        "numeric_eligibility": eligibility,
        "source_mapping": provenance, "source_model_identity": model_identity,
        "measure_binding": binding,
        "aggregation_and_additivity": definition,
        "metric_filter_declaration": filt, "base_population": base_population,
        "grain": grain, "time_dimension": time_key, "time_zone": timezone,
        "join_cardinality": join, "missing_group_policy": missing,
        "null_policy": null, "snapshot": snapshot, "business_state": state,
        "units": units, "time_spine": spine, "fill_nulls": fill,
        "compiled_sql_identity": sql_match, "manifest_dependency_alignment": deps,
    }
    common = (eligibility, provenance, model_identity, binding, definition, base_population,
              grain, time_key, timezone, join,
              missing, null, snapshot, state, units, spine, fill)
    context = (model_identity, base_population, grain, time_key, timezone, join, missing, null, snapshot, state,
               units, spine, fill)
    filter_unresolved = any("{{" in str(v) or "{%" in str(v)
                            for v in (filt["left"], filt["right"]))
    same_measure = binding["state"] == "verified"
    different_measure = mas == mbs == "verified" and bool(ma) and bool(mb) and ma != mb
    cross_model = different_measure and _model_nodes(a) != _model_nodes(b)
    same_identity = isinstance(aid, str) and bool(aid) and aid == bid

    decision = "abstain"
    if cross_model:
        signal = "cross_model_source_expression"
        reason = "The uniquely owned input measures differ; shared names or SQL do not map their source fields."
    elif different_measure:
        signal = "different_measures_same_model"
        reason = "Distinct measures in the same source model do not establish the same scalar expression."
    elif same_measure and filt["state"] == "contradicted":
        signal = "documented_filter_variant"
        reason = "The same bound measures have different declared metric filters."
        if not filter_unresolved and _verified(*common) and sql_match["state"] == "contradicted":
            decision = "temporal_or_scope_variant"
    elif same_measure and (grain["state"] == "contradicted" or time_key["state"] == "contradicted"):
        signal = "documented_time_or_grain_variant"
        reason = "The bound measures have different documented grain or time rules; rollup is unproved."
        # Grain changes require a separately verified transformation, which
        # these cards do not provide.  Time-rule changes can classify a
        # variant only when all the other prerequisites are explicit.
        if (grain["state"] == "verified" and time_key["state"] == "contradicted"
                and _verified(eligibility, provenance, model_identity, binding, definition,
                              filt, grain, timezone,
                              join, missing, null, snapshot, state, units, spine, fill)
                and sql_match["state"] == "contradicted"):
            decision = "temporal_or_scope_variant"
    elif same_identity and definition["state"] == "contradicted":
        signal = "identity_definition_conflict"
        reason = "The same metric ID carries differing declared type, aggregate, or expression."
        if _verified(eligibility, provenance, binding, filt, *context) and sql_match["state"] == "contradicted":
            decision = "conflicting_definition"
    elif same_measure and definition["state"] == "contradicted":
        signal = "shared_measure_different_definition"
        reason = "The measures are shared, but the metric transformations differ."
        if _verified(eligibility, provenance, binding, filt, *context):
            decision = "related"
    elif (same_measure and _verified(*common, filt, sql_match)
          and not filter_unresolved):
        signal = "same_compiled_metric_definition"
        decision = "direct_equivalent"
        reason = "Verified metric-level provenance and all supplied semantic rules agree, with byte-identical compiled metric SQL."
    elif same_measure:
        signal = "shared_bound_measure_review_candidate"
        reason = "A shared measure is source context; decisive compiled or semantic prerequisites remain unresolved."
    elif qa is not None and qa == qb:
        signal = "same_sql_unmapped_source"
        reason = "Identical SQL does not establish a uniquely owned metric expression or shared source."
    elif aname and aname == bname:
        signal = "same_name_only"
        reason = "A metric name does not establish a source or semantic relationship."
    elif isinstance(aid, str) and aid in deps_b or isinstance(bid, str) and bid in deps_a:
        signal = "manifest_dependency_review_candidate"
        reason = "A manifest dependency edge is not compiled expression or field-owner lineage."
    else:
        signal = "insufficient_source_evidence"
        reason = "No source-backed metric relationship can be established from these cards."

    if sca != scb:
        signal, decision = "incompatible_generated_scope", "abstain"
        reason = "The generated SQL scopes differ; this pair has no common query scope."
    elif not digest_ok or not model_ok:
        signal, decision = "compiled_provenance_needs_review", "abstain"
        reason = "The compiled SQL digest or owner-to-source-model mapping is not verified."

    if sca != scb or not digest_ok or not model_ok:
        score = None
    else:
        score = sum((
            binding["state"] == "verified",
            _verified(definition["metric_type"], definition["agg"], definition["expr"]),
            binding["state"] == "verified" and filt["state"] == "verified",
            sql_match["state"] == "verified",
        )) / 4
    missing_keys = [key for key, value in prerequisites.items()
                    if value["state"] in {"unknown", "generated_compiled"}
                    and key != "manifest_dependency_alignment"]
    return {
        "signal": signal, "decision": decision, "candidate_score": score,
        "prerequisites": prerequisites,
        "missing_prerequisites": missing_keys, "reason": reason,
        "evidence": [
            {"field": "metric_identity", "left": aid, "right": bid,
             "names": [aname, bname]},
            {"field": "numeric_eligibility_status", "left": eligibility["left"],
             "right": eligibility["right"]},
            {"field": "compiled_sql", "left_sha256": sql_match["left"],
             "right_sha256": sql_match["right"], "exact_bytes": sql_match["state"] == "verified"},
            {"field": "input_measures", "left": list(ma or na), "right": list(mb or nb)},
            {"field": "measure_definitions", "left": {"agg": _owner_values(a, "agg"),
                                                     "expr": _owner_values(a, "expr"),
                                                     "agg_time_dimension": _owner_values(a, "agg_time_dimension")},
             "right": {"agg": _owner_values(b, "agg"),
                       "expr": _owner_values(b, "expr"),
                       "agg_time_dimension": _owner_values(b, "agg_time_dimension")}},
            {"field": "source_models", "left": [m.get("node") for m in a.get("source_models", [])
                                                if isinstance(m, dict)],
             "right": [m.get("node") for m in b.get("source_models", [])
                       if isinstance(m, dict)]},
            {"field": "metric_filter", "left": filt["left"], "right": filt["right"]},
            {"field": "manifest_depends_on", "left": list(deps_a), "right": list(deps_b)},
        ],
    }
