"""Conservative AST/declared-lineage baseline for Jaffle development cards.

``compare(card_a, card_b)`` consumes only two cards from the common, label-free
I1 packet. It does not load that packet, source files, outcomes, or prior
decisions. Its syntax signal is a SQLGlot AST comparison; its taxonomy decision
is a separate source-supported hypothesis, never a row-equivalence proof.

Fixed, untuned source-only ranking rule for compatible, parsed pairs, in
descending priority (first matching rule wins): 1.0 = same normalized AST,
same uniquely owned measure set and physical sources; 0.8 = same AST and
physical sources without established matching ownership; 0.6 = shared
uniquely owned measure and same physical sources; 0.4 = explicit direct
derived-metric input dependency with checked owners/sources; 0.2 = same
nonempty physical source set; 0.0 = none of these. ``candidate_score`` is
None for malformed/unsupported input, unavailable parsing or mismatched SQL
scopes. The score ranks review candidates, not probability or taxonomy.
For ranking, sort descending by score and break every tie by ascending
lexical pair ID: ``min(metric_id_a, metric_id_b) + '||' + max(...)`` using
Python's Unicode string ordering. Null-score pairs are unranked. No label,
selected pair, outcome, threshold tuning, or metric-name similarity is used.

Taxonomy decisions require an upstream certified numeric eligibility, a
scope-matched verified source status, separate structured expression and
field-owner traces bound to the SQL hash, and structured independent evidence
for grain, units, snapshot, join cardinality, missing groups, NULL handling,
population, time rule and time zone. Each prerequisite record has a verified
value matching the card and a non-SQL independent review/check artifact with
its digest, locator and verifier. No scalar card field or bare status string
is itself evidence. The current compiled Jaffle packet supplies none of these
independent records, so it can produce ranking signals but no taxonomy class.
External attestation authenticity must be checked by the provider of these
records; this two-card comparator checks only their schema and binding.

Reproduce with Python and ``python -m pip install sqlglot==30.20.0``. A missing
or different parser version returns ``unsupported_parser`` and abstains.
Dialect: DuckDB (the development MetricFlow SQL target).
"""

from __future__ import annotations

import hashlib
from typing import Any

SQLGLOT_PIN = "30.20.0"
DIALECT = "duckdb"
TAXONOMY = frozenset({
    "direct_equivalent", "cross_grain_equivalent", "temporal_or_scope_variant",
    "related", "conflicting_definition", "non_match", "abstain",
})
SCOPES = frozenset({"ungrouped", "metric_time"})
UNKNOWN_FIELDS = (
    "grain", "join_cardinality", "missing_group_rule", "null_policy",
    "snapshot_state", "units",
)
SEMANTIC_FIELDS = UNKNOWN_FIELDS + ("population", "time_rule", "time_zone")
INDEPENDENT_EVIDENCE_KINDS = frozenset({"independent_review", "executed_constraint_check"})

try:
    import sqlglot
    from sqlglot import exp
    from sqlglot.optimizer.scope import traverse_scope
except ImportError:
    sqlglot = None
    exp = None
    traverse_scope = None


def _result(signal: str, syntax: str, reason: str, evidence: list[str],
            decision: str = "abstain", *, score: float | None = None) -> dict[str, Any]:
    assert decision in TAXONOMY
    assert score is None or 0.0 <= score <= 1.0
    return {"signal": signal, "syntax_decision": syntax, "decision": decision,
            "candidate_score": score,
            "evidence": evidence, "reason": reason}


def _card_value(card: dict, key: str) -> Any:
    """Accept the packet's flat fields or a harness-supplied provenance object."""
    nested = card.get("provenance")
    if isinstance(nested, dict) and key in nested:
        if key in card and card[key] != nested[key]:
            raise ValueError(f"conflicting {key} in card/provenance")
        return nested[key]
    return card.get(key)


def _card(card: dict) -> dict[str, Any]:
    if not isinstance(card, dict):
        raise ValueError("card must be an object")
    metric_id = card.get("metric_id") or card.get("metric")
    if not isinstance(metric_id, str) or not metric_id:
        raise ValueError("metric_id must be a nonempty string")
    scope = card.get("sql_scope")
    if scope not in SCOPES:
        raise ValueError("sql_scope must be ungrouped or metric_time")
    sql = card.get("compiled_sql")
    if sql is not None and not isinstance(sql, str):
        raise ValueError("compiled_sql must be a string or None")
    status = _card_value(card, "source_status")
    if not isinstance(status, str) or not status:
        raise ValueError("source_status is missing")
    numeric_status = _card_value(card, "numeric_eligibility_status")
    if numeric_status is not None and not isinstance(numeric_status, str):
        raise ValueError("numeric_eligibility_status is malformed")
    metric_type = card.get("type", card.get("metric_type"))
    if metric_type is not None and not isinstance(metric_type, str):
        raise ValueError("declared metric type is malformed")
    deps = _card_value(card, "manifest_depends_on")
    measures = _card_value(card, "input_measures")
    if (not isinstance(deps, list) or any(not isinstance(d, str) for d in deps)
            or not isinstance(measures, list) or any(not isinstance(m, dict) for m in measures)):
        raise ValueError("manifest_depends_on/input_measures are missing or malformed")
    models = card.get("source_models")
    if models is not None and (not isinstance(models, list) or any(
            not isinstance(model, dict) or not isinstance(model.get("node"), str)
            for model in models)):
        raise ValueError("source_models is malformed")
    name = card.get("name") or card.get("metric_name") or metric_id.rsplit(".", 1)[-1]
    if not isinstance(name, str):
        raise ValueError("metric name is malformed")
    return {"raw": card, "id": metric_id, "name": name, "scope": scope,
            "sql": sql, "status": status, "numeric_status": numeric_status,
            "type": metric_type,
            "deps": frozenset(deps), "measures": measures}


def _parse(sql: str) -> Any:
    statements = sqlglot.parse(sql, read=DIALECT, error_level="RAISE")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("expected exactly one SELECT statement")
    tree = statements[0]
    if any(isinstance(n, (exp.Placeholder, exp.Command)) for n in tree.walk()):
        raise ValueError("unresolved placeholder or command in SQL")
    return tree


def _outer(tree: Any, scope: str) -> tuple[Any, Any]:
    """Select the scalar output, retaining the time key at metric_time scope."""
    projections = tree.expressions
    expected = 1 if scope == "ungrouped" else 2
    if len(projections) != expected or any(isinstance(p, exp.Star) for p in projections):
        raise ValueError(f"{scope} requires {expected} explicit outer projection(s)")
    scalar = projections[-1].unalias()
    time_key = projections[0].unalias() if scope == "metric_time" else None
    if any(isinstance(n, exp.Star) for n in scalar.walk()):
        raise ValueError("unresolved star in scalar projection")
    return scalar, time_key


def _normal_ast(tree: Any) -> Any:
    """Alpha-rename bound relations and discard cosmetic outer output aliases.

    SQLGlot scopes bind table/subquery aliases to references. Unbound qualified
    references are left intact: no schema or join cardinality is invented.
    Nested projection aliases, predicates, joins, aggregation, windows, CTEs,
    grouping and literal values remain in the AST comparison.
    """
    result = tree.copy()
    for node in result.walk():
        node.comments = None
    for scope in traverse_scope(result):
        selected = scope.selected_sources
        mapping = {alias: f"__ast_relation_{i}" for i, alias in enumerate(selected, 1)}
        for column in scope.columns:
            if column.table in mapping:
                column.set("table", exp.to_identifier(mapping[column.table]))
        for alias, (source_node, _) in selected.items():
            binding = source_node.parent if isinstance(source_node.parent, exp.Subquery) else source_node
            if isinstance(binding, (exp.Table, exp.Subquery)):
                binding.set("alias", exp.TableAlias(this=exp.to_identifier(mapping[alias])))
            else:
                raise ValueError("unsupported relation alias binding")
    # Removing a projection alias used in ORDER/GROUP/HAVING/QUALIFY would be
    # unsafe. Leave those statements' output aliases intact.
    if not any(result.args.get(k) for k in ("order", "group", "having", "qualify")):
        result.set("expressions", [p.unalias().copy() for p in result.expressions])
    return result


def _features(tree: Any, scalar: Any) -> dict[str, Any]:
    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    sources = set()
    for table in tree.find_all(exp.Table):
        if table.name not in cte_names:
            unaliased = table.copy()
            unaliased.set("alias", None)
            sources.add(unaliased.sql(dialect=DIALECT))
    sources = sorted(sources)
    filters = sorted(n.this.sql(dialect=DIALECT) for n in tree.walk()
                     if isinstance(n, (exp.Where, exp.Having, exp.Qualify)))
    joins = [n.sql(dialect=DIALECT) for n in tree.walk() if isinstance(n, exp.Join)]
    aggregates = [n.sql(dialect=DIALECT) for n in tree.walk()
                  if isinstance(n, exp.AggFunc)]
    groups = [n.sql(dialect=DIALECT) for n in tree.walk()
              if isinstance(n, exp.Group)]
    time_ops = [n.sql(dialect=DIALECT) for n in tree.walk()
                if isinstance(n, (exp.DateTrunc, exp.TimestampTrunc, exp.Interval,
                                  exp.Window))]
    return {"sources": sources, "filters": filters, "joins": joins,
            "aggregates": aggregates, "groups": groups, "time_ops": time_ops,
            "top_aggregate": type(scalar).__name__ if isinstance(scalar, exp.AggFunc) else None,
            "scalar": scalar.sql(dialect=DIALECT)}


def _measure_keys(card: dict[str, Any]) -> tuple[set[tuple], bool]:
    """A shared name alone is never a lineage link; require one explicit owner."""
    keys: set[tuple] = set()
    for measure in card["measures"]:
        owners = measure.get("owners")
        if measure.get("owner_count") != 1 or not isinstance(owners, list) or len(owners) != 1:
            return set(), False
        owner = owners[0]
        if not isinstance(owner, dict) or not isinstance(owner.get("model_node"), list):
            return set(), False
        models = owner["model_node"]
        required = (measure.get("measure"), owner.get("semantic_model"),
                    owner.get("node_relation"), owner.get("agg"),
                    owner.get("agg_time_dimension"))
        if any(not isinstance(v, str) or not v for v in (*required, *models)) or not models:
            return set(), False
        if (owner.get("expr") is not None and not isinstance(owner["expr"], str)) or not isinstance(
                measure.get("join_to_timespine"), bool):
            return set(), False
        key = (measure["measure"], owner["semantic_model"],
               tuple(sorted(models)), owner["node_relation"], owner["agg"],
               owner.get("expr"), owner["agg_time_dimension"],
               repr(owner.get("non_additive_dimension")), repr(measure.get("filter")),
               repr(measure.get("fill_nulls_with")), measure.get("join_to_timespine"))
        keys.add(key)
    return keys, bool(keys) and len(keys) == len(card["measures"])


def _unknown(card: dict[str, Any]) -> list[str]:
    return [key for key in UNKNOWN_FIELDS if card["raw"].get(key) is None]


def _display(values: list[str], limit: int = 210) -> str:
    rendered = "; ".join(values) if values else "none"
    return rendered if len(rendered) <= limit else rendered[:limit] + "…"


def _measure_payload(tree: Any, scalar: Any) -> Any:
    """Resolve only a direct aggregate argument or one projected subquery alias.

    No arbitrary expression substitution, algebra, or filter simplification.
    A changed SUM argument cannot be mistaken for a filter-only variant.
    """
    if not isinstance(scalar, exp.AggFunc):
        return None
    argument = scalar.this
    if not isinstance(argument, exp.Column):
        return argument
    from_clause = tree.args.get("from_")
    source = from_clause.this if from_clause is not None else None
    if not isinstance(source, exp.Subquery) or not isinstance(source.this, exp.Select):
        return argument
    matches = [p.unalias() for p in source.this.expressions
               if isinstance(p, exp.Alias) and p.alias == argument.name]
    return matches[0] if len(matches) == 1 else None


def _owner_sources_match(card: dict, feat: dict) -> bool:
    models = card["raw"].get("source_models")
    if not isinstance(models, list):
        return False
    model_ids = {m.get("node") for m in models if isinstance(m, dict)}
    owners = [m["owners"][0] for m in card["measures"]]
    return (bool(owners) and all(set(o["model_node"]) <= model_ids for o in owners)
            and {o["node_relation"] for o in owners} == set(feat["sources"]))


def _related_dependency(a: dict, b: dict) -> bool:
    """Direct declaration of the other metric as an input to a derived value."""
    def edge(derived: dict, input_card: dict) -> bool:
        if derived["type"] not in {"derived", "ratio"} or input_card["id"] not in derived["deps"]:
            return False
        refs = derived["raw"].get("input_metrics")
        if derived["type"] == "derived":
            return (isinstance(refs, list) and any(isinstance(r, dict) and
                    r.get("name") == input_card["name"] for r in refs))
        # Ratio declarations list numerator/denominator in the packet; a
        # manifest edge alone does not say which input was used in the scalar.
        ratio_refs = (derived["raw"].get("numerator"), derived["raw"].get("denominator"))
        return any(isinstance(r, dict) and r.get("name") == input_card["name"]
                   for r in ratio_refs)
    return edge(a, b) or edge(b, a)


def _candidate_score(a: dict, b: dict, fa: dict, fb: dict, equal: bool,
                     keys_a: set[tuple], keys_b: set[tuple],
                     ok_a: bool, ok_b: bool) -> tuple[float, str]:
    """Apply the documented ordinal evidence ladder, independent of labels."""
    same_sources = bool(fa["sources"]) and fa["sources"] == fb["sources"]
    trusted_owners = (ok_a and ok_b and _owner_sources_match(a, fa)
                      and _owner_sources_match(b, fb))
    if equal and same_sources and trusted_owners and keys_a == keys_b:
        return 1.0, "same_ast_owned_lineage_and_sources"
    if equal and same_sources:
        return 0.8, "same_ast_and_sources_owner_unresolved"
    if same_sources and trusted_owners and bool(keys_a & keys_b):
        return 0.6, "shared_owned_measure_and_sources"
    if trusted_owners and _related_dependency(a, b):
        return 0.4, "explicit_direct_metric_dependency"
    if same_sources:
        return 0.2, "same_physical_sources_only"
    return 0.0, "no_supported_ast_lineage_link"


def _sha256(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _evidence_record(record: Any, kinds: frozenset[str], forbidden: set[str]) -> bool:
    """Require a located, digested verifier artifact distinct from SQL bytes."""
    return (isinstance(record, dict) and isinstance(record.get("kind"), str)
            and record["kind"] in kinds
            and _sha256(record.get("artifact_sha256"))
            and record["artifact_sha256"] not in forbidden
            and isinstance(record.get("locator"), str) and bool(record["locator"].strip())
            and isinstance(record.get("verified_by"), str)
            and bool(record["verified_by"].strip()))


def _substantive(value: Any) -> bool:
    """Unknown/empty placeholder values cannot be presented as verification."""
    if value is None or value == {} or value == []:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().casefold() not in {
            "unknown", "unverified", "not_certified", "not_applicable", "none",
        }
    return True


def _semantic_blockers(card: dict, tree: Any, scalar: Any, feat: dict) -> list[str]:
    """Do not promote generated SQL or self-asserted semantic fields to proof.

    These are format/binding checks for externally verified records; a card
    cannot certify its own authenticity. The I1 packet has no such records.
    """
    blockers: list[str] = []
    if card["numeric_status"] != "certified_numeric":
        blockers.append("numeric_eligibility_not_certified")
    required_status = ("verified_ungrouped" if card["scope"] == "ungrouped"
                       else "verified_metric_time_only")
    if card["status"] != required_status:
        blockers.append("compiled_metric_source_not_verified_for_scope")
    sql_hash = hashlib.sha256(card["sql"].encode("utf-8")).hexdigest()
    scalar_hash = hashlib.sha256(scalar.sql(dialect=DIALECT).encode("utf-8")).hexdigest()
    if card["raw"].get("compiled_sql_sha256") != sql_hash:
        blockers.append("compiled_sql_hash_unbound")
    expression = card["raw"].get("compiled_metric_expression_provenance")
    expression_ok = (isinstance(expression, dict) and expression.get("status") == "verified"
                     and expression.get("metric_id") == card["id"]
                     and expression.get("compiled_sql_sha256") == sql_hash
                     and expression.get("scalar_ast_sha256") == scalar_hash
                     and _evidence_record(expression.get("evidence"),
                                          frozenset({"compiled_metric_expression_trace"}),
                                          {sql_hash}))
    if not expression_ok:
        blockers.append("compiled_metric_expression_trace_unverified")
    owner = card["raw"].get("field_owner_provenance")
    _, owner_shape_ok = _measure_keys(card)
    owner_nodes = (sorted({node for measure in card["measures"]
                           for source in measure["owners"]
                           for node in source["model_node"]}) if owner_shape_ok else [])
    # Explicit compiled-column -> source-field bindings are distinct from
    # relation-level manifest dependencies. SUM(1) traces the input row.
    observed = sorted({column.sql(dialect=DIALECT) for column in tree.find_all(exp.Column)})
    if not observed:
        observed = ["__input_row__"]
    bindings = owner.get("field_bindings") if isinstance(owner, dict) else None
    bindings_ok = (isinstance(bindings, list) and len(bindings) == len(observed)
                   and all(isinstance(binding, dict)
                           and isinstance(binding.get("compiled_column"), str)
                           and binding.get("owner_model_node") in owner_nodes
                           and isinstance(binding.get("owner_field"), str)
                           and bool(binding["owner_field"].strip())
                           and isinstance(binding.get("trace_location"), str)
                           and bool(binding["trace_location"].strip())
                           for binding in bindings)
                   and sorted(binding["compiled_column"] for binding in bindings) == observed)
    owner_ok = (isinstance(owner, dict) and owner.get("status") == "verified"
                and owner.get("metric_id") == card["id"]
                and owner.get("compiled_sql_sha256") == sql_hash
                and isinstance(owner.get("bound_model_nodes"), list)
                and owner["bound_model_nodes"] == owner_nodes and bool(owner_nodes)
                and bindings_ok
                and owner_shape_ok
                and _owner_sources_match(card, feat)
                and _evidence_record(owner.get("evidence"),
                                     frozenset({"compiled_field_owner_trace"}), {sql_hash}))
    if not owner_ok:
        blockers.append("compiled_field_owner_trace_unverified")
    excluded = {sql_hash}
    if expression_ok:
        excluded.add(expression["evidence"]["artifact_sha256"])
    if owner_ok:
        excluded.add(owner["evidence"]["artifact_sha256"])
    prerequisites = card["raw"].get("semantic_prerequisite_verifications")
    for field in SEMANTIC_FIELDS:
        entry = prerequisites.get(field) if isinstance(prerequisites, dict) else None
        value = card["raw"].get(field)
        verified = (isinstance(entry, dict) and entry.get("status") == "verified"
                    and _substantive(value) and entry.get("value") == value
                    and _evidence_record(entry.get("evidence"),
                                         INDEPENDENT_EVIDENCE_KINDS, excluded))
        if field == "join_cardinality":
            verified = (verified and isinstance(value, dict)
                        and value.get("safe_for_comparison") is True
                        and isinstance(value.get("relationship"), str)
                        and value["relationship"] in {
                            "no_join", "one_to_one", "many_to_one", "preaggregated_one_row",
                        })
        if field in {"missing_group_rule", "null_policy"}:
            verified = verified and isinstance(value, dict) and _substantive(value.get("policy"))
        if not verified:
            blockers.append(f"{field}_independent_verification_missing")
    return blockers


def compare(card_a: dict, card_b: dict) -> dict:
    """Compare two label-free I1 cards; emit syntax and taxonomy separately.

    Same AST/lineage is only a review signal. Equivalence, conflict and
    non-match require business semantics unavailable from compiled SQL alone.
    Cross-scope pairs always abstain, including direct dependency pairs.
    """
    try:
        a, b = _card(card_a), _card(card_b)
    except ValueError as exc:
        return _result("unsupported_input", "unsupported", str(exc), [])
    evidence = [f"metrics: {a['id']} | {b['id']}",
                f"scope: {a['scope']} | {b['scope']}",
                f"source_status: {a['status']} | {b['status']}",
                f"numeric_eligibility_status: {a['numeric_status'] or 'unknown'} | "
                f"{b['numeric_status'] or 'unknown'}",
                f"declared_type: {a['type']} | {b['type']}"]
    if a["id"] == b["id"]:
        return _result("unsupported_input", "unsupported", "pair must contain distinct metric IDs", evidence)
    if sqlglot is None or sqlglot.__version__ != SQLGLOT_PIN:
        found = "unavailable" if sqlglot is None else sqlglot.__version__
        return _result("unsupported_parser", "unsupported",
                       f"Requires sqlglot=={SQLGLOT_PIN} (found {found}); install with "
                       f"python -m pip install sqlglot=={SQLGLOT_PIN} and rerun.", evidence)
    if not a["sql"] or not b["sql"]:
        return _result("missing_compiled_sql", "unsupported",
                       "At least one compiled_sql is absent; no AST comparison is possible.", evidence)
    try:
        trees = [_parse(c["sql"]) for c in (a, b)]
        scalars_and_time = [_outer(t, c["scope"]) for t, c in zip(trees, (a, b))]
        features = [_features(t, st[0]) for t, st in zip(trees, scalars_and_time)]
        normal = [_normal_ast(t) for t in trees]
    except (ValueError, sqlglot.errors.SqlglotError) as exc:
        return _result("unsupported_sql", "unsupported",
                       f"SQL AST unsupported: {type(exc).__name__}: {str(exc)[:180]}", evidence)
    for label, card, feat, (scalar, time_key), norm in zip(
            ("a", "b"), (a, b), features, scalars_and_time, normal):
        digest = hashlib.sha256(norm.sql(dialect=DIALECT).encode()).hexdigest()[:16]
        evidence.extend((f"{label}.ast_sha256_prefix: {digest}",
                         f"{label}.scalar: {feat['scalar'][:210]}",
                         f"{label}.sources: {_display(feat['sources'])}",
                         f"{label}.filters: {_display(feat['filters'])}",
                         f"{label}.joins: {_display(feat['joins'])}",
                         f"{label}.aggregates: {_display(feat['aggregates'])}",
                         f"{label}.grouping: {_display(feat['groups'])}",
                         f"{label}.time_ops: {_display(feat['time_ops'])}"))
        if time_key is not None:
            evidence.append(f"{label}.time_key: {time_key.sql(dialect=DIALECT)[:210]}")
    keys_a, ok_a = _measure_keys(a)
    keys_b, ok_b = _measure_keys(b)
    shared = keys_a & keys_b if ok_a and ok_b else set()
    evidence.extend((f"declared_measure_owner_resolved: {ok_a} | {ok_b}",
                     f"shared_owned_measures: {', '.join(sorted(k[0] for k in shared)) or 'none'}",
                     f"source_model_nodes: "
                     f"{_display(sorted(m['node'] for m in a['raw'].get('source_models') or []))} | "
                     f"{_display(sorted(m['node'] for m in b['raw'].get('source_models') or []))}",
                     f"manifest_depends_on: {', '.join(sorted(a['deps'])) or 'none'} | "
                     f"{', '.join(sorted(b['deps'])) or 'none'}",
                     f"unknown_prerequisites: {', '.join(_unknown(a)) or 'none'} | "
                     f"{', '.join(_unknown(b)) or 'none'}"))
    if a["scope"] != b["scope"]:
        return _result("cross_scope_review", "not_comparable_scope",
                       "Different generated SQL scopes; the I1 packet policy requires abstention.", evidence)
    equal = normal[0] == normal[1]
    syntax = "same_ast" if equal else "different_ast"
    if (equal and ok_a and ok_b and keys_a == keys_b
            and _owner_sources_match(a, features[0])
            and _owner_sources_match(b, features[1])
            and features[0]["sources"] == features[1]["sources"]):
        signal = "same_ast_and_lineage_review"
    elif equal:
        signal = "same_ast_lineage_unresolved_review"
    elif shared:
        signal = "different_ast_shared_lineage_review"
    else:
        signal = "different_ast_or_lineage_review"
    score, score_basis = _candidate_score(a, b, features[0], features[1],
                                          equal, keys_a, keys_b, ok_a, ok_b)
    evidence.append(f"candidate_score_basis: {score_basis}")
    blockers_a = _semantic_blockers(a, trees[0], scalars_and_time[0][0], features[0])
    blockers_b = _semantic_blockers(b, trees[1], scalars_and_time[1][0], features[1])
    if blockers_a or blockers_b:
        evidence.extend((f"a.semantic_blockers: {', '.join(blockers_a) or 'none'}",
                         f"b.semantic_blockers: {', '.join(blockers_b) or 'none'}"))
        return _result(signal, syntax,
                       "Verified compiled expression/field ownership and independently "
                       "verified semantic prerequisites are required; see semantic_blockers.",
                       evidence, score=score)
    # Scope-variant is supported only for a single, uniquely owned measure
    # with the same physical source and aggregate, and an explicit change in
    # an AST WHERE clause. No join, grouping or time operation may intervene.
    fa, fb = features
    payloads = [_measure_payload(t, st[0]) for t, st in zip(trees, scalars_and_time)]
    declared_filters = [c["raw"].get("metric_filter") for c in (a, b)]
    variant = (a["type"] == b["type"] == "simple" and ok_a and ok_b
               and len(keys_a) == len(keys_b) == 1 and keys_a == keys_b
               and fa["sources"] == fb["sources"] and bool(fa["sources"])
               and fa["top_aggregate"] == fb["top_aggregate"]
               and fa["top_aggregate"] is not None
               and payloads[0] is not None and payloads[0] == payloads[1]
               and _owner_sources_match(a, fa) and _owner_sources_match(b, fb)
               and not any(f["joins"] or f["groups"] or f["time_ops"] for f in features)
               and fa["filters"] != fb["filters"]
               and all(bool(c["raw"].get("metric_filter")) == bool(f["filters"])
                       for c, f in zip((a, b), features))
               and declared_filters[0] != declared_filters[1])
    if variant:
        return _result(signal, syntax,
                       "Same uniquely owned measure and aggregate with different declared and "
                       "compiled row filters; source-backed scope-variant hypothesis, not equivalence.",
                       evidence, "temporal_or_scope_variant", score=score)
    if (not equal and ok_a and ok_b and _owner_sources_match(a, fa)
            and _owner_sources_match(b, fb) and _related_dependency(a, b)):
        return _result(signal, syntax,
                       "A declared derived metric directly depends on the other metric and "
                       "their compiled scalar ASTs differ; linked quantities, no equivalence claim.",
                       evidence, "related", score=score)
    missing = sorted(set(_unknown(a) + _unknown(b)))
    reason = ("Compiled AST and declared lineage do not establish a semantic relationship; "
              f"unknown prerequisites: {', '.join(missing) or 'source-row equivalence and transformation validity'}. "
              "Generated SQL is not an execution or a business-semantic proof.")
    return _result(signal, syntax, reason, evidence, score=score)
