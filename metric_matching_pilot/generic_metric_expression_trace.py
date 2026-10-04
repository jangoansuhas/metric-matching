#!/usr/bin/env python3
"""Development-only trace from dbt declarations to possible compiled model fields.

The pinned Jaffle manifest contains declarations and compiled *models*, not
compiled MetricFlow metric queries. Syntactic dependencies and projections are
recorded separately from verified metric-expression provenance. In particular,
this adapter never upgrades a model check to a metric-expression check.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

import sqlglot
from sqlglot import exp


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / "public_corpus/jaffle-shop-sidemantic/jaffle-shop"
PIN = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
MANIFEST = REPO / "target/manifest.json"
ELIGIBILITY = HERE / "generic_metric_eligibility_manifest_report.json"
PROVENANCE = HERE / "generic_compiled_provenance_report.json"
OUTPUT_JSON = HERE / "generic_metric_expression_trace_report.json"
OUTPUT_MD = HERE / "generic_metric_expression_trace_report.md"
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()

    def unique(pairs: list[tuple[str, object]]) -> dict:
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key in {path.name}: {key}")
            out[key] = value
        return out

    value = json.loads(data, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON root: {path.name}")
    return value, digest(data)


def pinned_checkout(expected: str = PIN) -> None:
    if expected != PIN:
        raise ValueError("wrong_commit_pin")
    root = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--show-toplevel"],
                          capture_output=True, check=True, text=True).stdout.strip()
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, check=True, text=True).stdout.strip()
    if Path(root).resolve() != REPO.resolve() or head != PIN:
        raise ValueError("pinned_checkout_mismatch")


def safe_file(path: object) -> Path | None:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        return None
    p = PurePosixPath(path)
    if p.is_absolute() or any(x in ("", ".", "..") for x in path.split("/")):
        return None
    result = REPO / path
    try:
        result.resolve().relative_to(REPO.resolve())
    except ValueError:
        return None
    if result.is_symlink() or not result.is_file():
        return None
    return result


def git_source_sha(path: object) -> str | None:
    """Hash an immutable regular blob, without treating a worktree as the pin."""
    if safe_file(path) is None:
        return None
    tree = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-z", PIN, "--", str(path)],
                          capture_output=True, check=True).stdout
    entries = [entry for entry in tree.split(b"\0") if entry]
    if len(entries) != 1:
        return None
    try:
        metadata, name = entries[0].split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split(" ")
        if name.decode("utf-8") != path or kind != "blob" or mode not in ("100644", "100755"):
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    data = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", oid],
                          capture_output=True, check=True).stdout
    return digest(data)


def dependencies(obj: dict) -> list[str]:
    depends = obj.get("depends_on")
    nodes = depends.get("nodes") if isinstance(depends, dict) else None
    return nodes if isinstance(nodes, list) and all(isinstance(n, str) for n in nodes) else []


def measure_id(semantic_id: str, index: int) -> str:
    return f"manifest:measure:{semantic_id}:measures[{index}]"


def make_link(metric_path: list[str], semantic_id: str, index: int, measure: dict,
              semantic: dict, models: dict, candidate_by_id: dict,
              source_sha_cache: dict) -> tuple[dict, list[str]]:
    reasons = []
    measure_key = measure_id(semantic_id, index)
    candidate = candidate_by_id.get(measure_key)
    path = semantic.get("original_file_path")
    if path not in source_sha_cache:
        source_sha_cache[path] = git_source_sha(path)
    source_sha = source_sha_cache[path]
    source_claim = candidate.get("source", {}) if isinstance(candidate, dict) else {}
    source_ok = (isinstance(source_claim, dict) and source_claim.get("path") == path
                 and source_claim.get("sha256") == source_sha and bool(source_sha))
    if not source_ok:
        reasons.append("measure_source_yaml_unaligned")
    model_ids = dependencies(semantic)
    model_id = model_ids[0] if len(model_ids) == 1 and model_ids[0] in models else None
    if model_id is None:
        reasons.append("semantic_model_to_model_edge_not_unique")
    expr = measure.get("expr")
    if expr is None:
        expr = measure.get("name")  # dbt's omitted expr names a column; still only a declaration.
    if not isinstance(expr, str):
        reasons.append("measure_expr_missing_or_malformed")
        expr = None
    link = {
        "measure_id": measure_key, "measure_name": measure.get("name"),
        "metric_dependency_path": metric_path,
        "semantic_model_id": semantic_id,
        "semantic_model_source": {"path": path, "pinned_sha256": source_sha,
                                  "eligibility_sha256": source_claim.get("sha256"),
                                  "aligned_to_pinned_blob": source_ok},
        "model_id": model_id, "measure_expr": expr, "measure_agg": measure.get("agg"),
        "measure_expr_defaulted_to_name": measure.get("expr") is None,
        "binding_status": "exact_manifest_resource_and_measure" if not reasons else "needs_review",
    }
    return link, reasons


def metric_measure_links(metric_id: str, manifest: dict, candidate_by_id: dict,
                         source_sha_cache: dict, path: tuple[str, ...] = ()
                         ) -> tuple[list[dict], list[str]]:
    metrics = manifest.get("metrics", {})
    semantics = manifest.get("semantic_models", {})
    models = manifest.get("nodes", {})
    if metric_id in path:
        return [], ["cyclic_metric_dependency"]
    metric = metrics.get(metric_id)
    if not isinstance(metric, dict):
        return [], ["metric_dependency_missing"]
    path = (*path, metric_id)
    links, reasons = [], []
    edges = dependencies(metric)
    semantic_edges = [key for key in edges if key.startswith("semantic_model.")]
    metric_edges = [key for key in edges if key.startswith("metric.")]
    if len(edges) != len(semantic_edges) + len(metric_edges):
        reasons.append("unsupported_metric_dependency_edge")
    if semantic_edges:
        typed = metric.get("type_params")
        typed = typed if isinstance(typed, dict) else {}
        ref = typed.get("measure")
        name = ref.get("name") if isinstance(ref, dict) else None
        if not isinstance(name, str) or not name:
            reasons.append("metric_measure_reference_missing")
        if len(semantic_edges) != 1 or metric_edges:
            reasons.append("metric_semantic_model_edge_not_unique")
        for semantic_id in semantic_edges:
            semantic = semantics.get(semantic_id)
            if not isinstance(semantic, dict) or not isinstance(name, str):
                reasons.append("semantic_model_or_measure_missing")
                continue
            measures = semantic.get("measures")
            if not isinstance(measures, list):
                reasons.append("semantic_measures_malformed")
                continue
            hits = [(i, measure) for i, measure in enumerate(measures)
                    if isinstance(measure, dict) and measure.get("name") == name]
            if len(hits) != 1:
                reasons.append("ambiguous_or_missing_measure_name_within_explicit_semantic_model")
                continue
            index, measure = hits[0]
            link, link_reasons = make_link(list(path), semantic_id, index, measure, semantic,
                                           models, candidate_by_id, source_sha_cache)
            links.append(link)
            reasons.extend(link_reasons)
    if metric_edges:
        for edge in metric_edges:
            sublinks, subreasons = metric_measure_links(
                edge, manifest, candidate_by_id, source_sha_cache, path)
            links.extend(sublinks)
            reasons.extend(subreasons)
        typed = metric.get("type_params")
        typed = typed if isinstance(typed, dict) else {}
        refs = typed.get("metrics")
        if not isinstance(refs, list) or not refs:
            refs = [typed.get("numerator"), typed.get("denominator")]
        named = {v.get("name") for v in refs if isinstance(v, dict)
                 and isinstance(v.get("name"), str)}
        edge_names = {metrics.get(edge, {}).get("name") for edge in metric_edges
                      if isinstance(metrics.get(edge), dict)}
        if named and named != edge_names:
            reasons.append("metric_references_do_not_match_explicit_dependency_edges")
    if not edges:
        reasons.append("metric_dependency_missing")
    # Keep repeated paths: a derived expression can use one measure twice at different offsets.
    return links, sorted(set(reasons))


def parse_measure_fields(expr_sql: str | None) -> tuple[list[str], str | None]:
    if not isinstance(expr_sql, str):
        return [], "measure_expr_missing"
    if "{{" in expr_sql or "{%" in expr_sql:
        return [], "measure_expr_macro_unexpanded"
    try:
        expression = sqlglot.parse_one(expr_sql, read="duckdb")
    except (sqlglot.errors.ParseError, ValueError):
        return [], "measure_expr_sql_parse_failed"
    if expression is None or any(isinstance(node, (exp.Star, exp.Subquery, exp.Select))
                                 for node in expression.walk()):
        return [], "measure_expr_unsupported"
    return sorted({col.name.lower() for col in expression.find_all(exp.Column)}), None


def trace_projections(compiled: str | None, fields: list[str]
                      ) -> tuple[list[dict], str, list[str]]:
    """Report syntactic projection candidates, never infer through CTEs or stars."""
    if not isinstance(compiled, str):
        return [], "unresolved", ["compiled_sql_missing"]
    if "{{" in compiled or "{%" in compiled:
        return [], "unresolved", ["unexpanded_macro"]
    try:
        tree = sqlglot.parse_one(compiled, read="duckdb")
    except (sqlglot.errors.ParseError, ValueError):
        return [], "unresolved", ["compiled_sql_parse_failed"]
    if tree is None:
        return [], "unresolved", ["compiled_sql_parse_failed"]
    reasons = []
    for cls, code in ((exp.CTE, "cte_projection_boundary"),
                      (exp.Join, "join_field_owner_ambiguous"),
                      (exp.Star, "unexpanded_select_star"),
                      (exp.Window, "window_projection_boundary"),
                      (exp.Union, "union_projection_boundary")):
        if any(isinstance(node, cls) for node in tree.walk()):
            reasons.append(code)
    found = []
    selections = list(tree.find_all(exp.Select))
    for target in fields:
        for scope, selection in enumerate(selections):
            for projection in selection.expressions:
                if not isinstance(projection, exp.Expression):
                    continue
                alias = projection.alias_or_name
                if not isinstance(alias, str) or alias.lower() != target:
                    continue
                body = projection.this if isinstance(projection, exp.Alias) else projection
                columns = sorted({c.sql(dialect="duckdb") for c in body.find_all(exp.Column)})
                found.append({"field": target, "select_scope_index": scope,
                              "projection_sql": projection.sql(dialect="duckdb"),
                              "projection_column_refs": columns})
    found.sort(key=lambda row: (row["field"], row["select_scope_index"], row["projection_sql"]))
    if not fields:
        reasons.append("literal_measure_has_no_field_owner")
        owner = "literal_only"
    elif any(not any(row["field"] == field for row in found) for field in fields):
        reasons.append("missing_explicit_field_projection")
        owner = "unresolved"
    elif any(sum(row["field"] == field for row in found) > 1 for field in fields):
        reasons.append("multiple_projection_candidates")
        owner = "ambiguous"
    elif reasons:
        owner = "candidate_only_complex_sql"
    else:
        # A simple projection is a field candidate, not compiled metric SQL.
        owner = "candidate_only"
    return found, owner, sorted(set(reasons))


def compiled_hashes_match(actual: bytes | None, compiled_code: str | None,
                          reported_sha: object, manifest_sha: object) -> bool:
    if actual is None or not isinstance(compiled_code, str):
        return False
    expected = digest(compiled_code.encode("utf-8"))
    return bool(SHA_RE.fullmatch(str(reported_sha)) and digest(actual) == expected
                and expected == reported_sha == manifest_sha)


def model_info(model_id: str, manifest: dict, provenance: dict,
               case: dict, case_nodes: dict) -> tuple[dict, str | None, list[str]]:
    reasons = []
    model = manifest.get("nodes", {}).get(model_id)
    node = case_nodes.get(model_id)
    if not isinstance(model, dict) or not isinstance(node, dict):
        return {"id": model_id}, None, ["model_or_provenance_node_missing"]
    compiled_path = node.get("compiled_path")
    file = safe_file(compiled_path)
    code = model.get("compiled_code")
    code_sha = digest(code.encode("utf-8")) if isinstance(code, str) else None
    file_bytes = file.read_bytes() if file is not None else None
    file_sha = digest(file_bytes) if file_bytes is not None else None
    reported_sha = node.get("compiled_file", {}).get("sha256")
    if not compiled_hashes_match(file_bytes, code, reported_sha,
                                 node.get("manifest_compiled_code_sha256")):
        reasons.append("compiled_file_hash_mismatch")
    pinned_source_sha = git_source_sha(node.get("source_path"))
    if not pinned_source_sha or pinned_source_sha != node.get("pinned_source", {}).get("sha256"):
        reasons.append("pinned_model_source_hash_mismatch")
    if node.get("status") != "model_artifact_checks_pass":
        reasons.append("model_source_checksum_or_mapping_needs_review")
    checksum = node.get("manifest_source_checksum", {})
    if not isinstance(checksum, dict) or checksum.get("versus_manifest_raw_code") != "exact":
        reasons.append("manifest_source_checksum_mismatch")
    if case.get("build_event", {}).get("commit_attested_by_build") is not True:
        reasons.append("build_commit_unverified")
    source_path = node.get("source_path")
    if source_path != model.get("original_file_path") or node.get("node_id") != model_id:
        reasons.append("model_source_node_mismatch")
    return {
        "id": model_id, "source_path": source_path, "source_sha256": pinned_source_sha,
        "manifest_raw_code_sha256": node.get("manifest_raw_code_sha256"),
        "manifest_source_checksum": checksum,
        "compiled_path": compiled_path, "compiled_file_sha256": file_sha,
        "manifest_compiled_code_sha256": code_sha,
        "model_provenance_status": node.get("status"),
        "build_commit_attested": case.get("build_event", {}).get("commit_attested_by_build") is True,
    }, code, reasons


def trace_candidate(candidate: dict, manifest: dict, candidate_by_id: dict,
                    provenance: dict, case: dict, case_nodes: dict, cache: dict,
                    source_sha_cache: dict) -> dict:
    cid = candidate["id"]
    kind = candidate["kind"]
    reasons = []
    if kind == "measure":
        semantic_id = candidate.get("source", {}).get("manifest_resource_id")
        idx = candidate.get("source", {}).get("manifest_measure_index")
        semantic = manifest.get("semantic_models", {}).get(semantic_id)
        measures = semantic.get("measures") if isinstance(semantic, dict) else None
        if (not isinstance(idx, int) or not isinstance(measures, list) or idx < 0
                or idx >= len(measures) or not isinstance(measures[idx], dict)
                or measure_id(semantic_id, idx) != cid
                or candidate.get("name") != measures[idx].get("name")):
            links = []
            reasons.append("measure_manifest_identity_mismatch")
        else:
            link, extra = make_link([], semantic_id, idx, measures[idx], semantic,
                                    manifest.get("nodes", {}), candidate_by_id, source_sha_cache)
            links = [link]
            reasons.extend(extra)
        metric = None
    elif kind == "metric":
        key = cid.removeprefix("manifest:metric:")
        metric = manifest.get("metrics", {}).get(key)
        if not isinstance(metric, dict) or candidate.get("name") != metric.get("name"):
            links = []
            reasons.append("metric_manifest_identity_mismatch")
        else:
            links, extra = metric_measure_links(key, manifest, candidate_by_id, source_sha_cache)
            reasons.extend(extra)
    else:
        metric, links = None, []
        reasons.append("unsupported_candidate_kind")
    model_ids = sorted({link["model_id"] for link in links if link["model_id"]})
    model_candidates = []
    for mid in model_ids:
        if mid not in cache:
            cache[mid] = model_info(mid, manifest, provenance, case, case_nodes)
        model_candidates.append(cache[mid][0])
        reasons.extend(cache[mid][2])
    if len(model_ids) > 1:
        reasons.append("multiple_model_candidates")
    if not model_ids:
        reasons.append("model_candidate_unresolved")
    model_candidate = model_candidates[0] if len(model_candidates) == 1 else None
    field_traces = []
    for link in links:
        fields, parse_error = parse_measure_fields(link["measure_expr"])
        mid = link["model_id"]
        code = cache[mid][1] if mid in cache else None
        projections, owner, field_reasons = trace_projections(code, fields)
        if parse_error:
            field_reasons.append(parse_error)
        reasons.extend(field_reasons)
        field_traces.append({"measure_id": link["measure_id"], "model_id": mid,
                             "expression_field_refs": fields, "field_owner_status": owner,
                             "projection_candidates": projections,
                             "stop_reasons": sorted(set(field_reasons))})
    if candidate.get("eligibility") == "unknown":
        reasons.append("numeric_eligibility_unknown")
    if kind == "metric" and metric:
        metric_source = candidate.get("source", {})
        path = metric.get("original_file_path")
        if path not in source_sha_cache:
            source_sha_cache[path] = git_source_sha(path)
        if (metric_source.get("path") != path
                or metric_source.get("sha256") != source_sha_cache[path]
                or not source_sha_cache[path]):
            reasons.append("metric_source_yaml_unaligned")
    if metric and metric.get("filter"):
        reasons.append("metric_filter_requires_compiled_metric_query")
    if metric and metric.get("type") in ("derived", "ratio", "cumulative"):
        reasons.append("metric_transformation_requires_compiled_metric_query")
    # Manifest compiles models but supplies no compiled MetricFlow metric queries.
    # Even a unique model field owner would be insufficient to verify the metric.
    reasons.append("compiled_metric_query_unavailable")
    return {
        "id": cid, "kind": kind, "name": candidate.get("name"),
        "numeric_eligibility": candidate.get("eligibility"),
        "metric_type": candidate.get("metric_type"),
        "metric_manifest_dependencies": dependencies(metric) if metric else [],
        "declared_metric_expression": (metric.get("type_params") or {}).get("expr") if metric else None,
        "declared_metric_filter": metric.get("filter") if metric else None,
        "measure_links": links, "model_candidate": model_candidate,
        "model_candidates": model_candidates, "field_traces": field_traces,
        "compiled_metric_expression_status": "needs_review",
        "stop_reasons": sorted(set(reasons)),
    }


def build(expected: str = PIN) -> dict:
    pinned_checkout(expected)
    manifest, manifest_sha = read_json(MANIFEST)
    eligible, eligible_sha = read_json(ELIGIBILITY)
    provenance, provenance_sha = read_json(PROVENANCE)
    if eligible.get("provenance", {}).get("repo_commit") != PIN:
        raise ValueError("eligibility_commit_mismatch")
    if eligible.get("provenance", {}).get("manifest", {}).get("sha256") != manifest_sha:
        raise ValueError("eligibility_manifest_hash_mismatch")
    cases = [c for c in provenance.get("cases", []) if c.get("expected_commit") == PIN]
    if len(cases) != 1 or cases[0].get("manifest_file", {}).get("sha256") != manifest_sha:
        raise ValueError("provenance_case_or_manifest_mismatch")
    case = cases[0]
    if case.get("checked_out_commit") != PIN or case.get("checked_out_commit_matches_pin") is not True:
        raise ValueError("provenance_commit_mismatch")
    if manifest.get("metadata", {}).get("project_name") != "jaffle_shop":
        raise ValueError("manifest_project_mismatch")
    candidates = eligible.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 32:
        raise ValueError("eligibility_candidate_census_mismatch")
    ids = [c.get("id") for c in candidates if isinstance(c, dict)]
    if len(ids) != 32 or len(set(ids)) != 32 or any(not isinstance(i, str) for i in ids):
        raise ValueError("eligibility_ids_missing_or_duplicated")
    expected_ids = {f"manifest:metric:{k}" for k in manifest.get("metrics", {})}
    expected_ids.update(measure_id(k, i) for k, semantic in manifest.get("semantic_models", {}).items()
                        for i, _ in enumerate(semantic.get("measures", [])))
    if set(ids) != expected_ids:
        raise ValueError("eligibility_manifest_declaration_set_mismatch")
    case_nodes = {n["node_id"]: n for n in case.get("nodes", [])}
    if len(case_nodes) != len(case.get("nodes", [])):
        raise ValueError("duplicate_model_provenance_nodes")
    index = {c["id"]: c for c in candidates}
    model_cache, source_sha_cache = {}, {}
    records = [trace_candidate(index[cid], manifest, index, provenance, case,
                               case_nodes, model_cache, source_sha_cache) for cid in sorted(ids)]
    counts = Counter(record["kind"] for record in records)
    lock_file = safe_file("package-lock.yml")
    lock_working_sha = digest(lock_file.read_bytes()) if lock_file else None
    lock_pinned_sha = git_source_sha("package-lock.yml")
    return {
        "schema_version": 1, "scope": "pinned_public_development_only",
        "source_manifest_sha256": manifest_sha,
        "source_eligibility_sha256": eligible_sha,
        "model_provenance_sha256": provenance_sha,
        "sql_parser": {"name": "sqlglot", "version": sqlglot.__version__, "dialect": "duckdb"},
        "source": {"repo_commit": PIN, "manifest_path": "target/manifest.json",
                   "manifest_build_commit_attested": case.get("build_event", {}).get("commit_attested_by_build") is True,
                   "manifest_generated_at": manifest.get("metadata", {}).get("generated_at"),
                   "package_lock": {"path": "package-lock.yml", "pinned_sha256": lock_pinned_sha,
                                    "working_sha256": lock_working_sha,
                                    "working_differs_from_pin": lock_working_sha != lock_pinned_sha}},
        "coverage": {"declarations": len(records), "metrics": counts["metric"],
                     "measures": counts["measure"],
                     "unknown_numeric_eligibility": sum(r["numeric_eligibility"] == "unknown" for r in records),
                     "with_exact_measure_link": sum(any(link["binding_status"] == "exact_manifest_resource_and_measure"
                                                        for link in r["measure_links"]) for r in records),
                     "with_unique_model_candidate": sum(r["model_candidate"] is not None for r in records),
                     "compiled_metric_expressions_verified": 0,
                     "compiled_metric_expressions_needs_review": len(records)},
        "records": records,
        "limits": [
            "Only pinned public Jaffle development artifacts were read.",
            "An explicit manifest metric-to-measure dependency is not a pair label.",
            "SQL projection candidates do not prove field lineage across CTEs, joins, stars, or model build revisions.",
            "Model compilation does not include compiled MetricFlow metric expressions here.",
            "Unverified build commit and source checksum mismatch stop every public-corpus expression verification.",
            "No business equivalence, human gold, accuracy, or method superiority is established.",
        ],
    }


def render_markdown(report: dict) -> str:
    c = report["coverage"]
    reasons = Counter(reason for row in report["records"] for reason in row["stop_reasons"])
    lock = report["source"]["package_lock"]
    lines = [
        "# Metric expression trace: pinned public development checkout",
        "",
        f"- Repository: Jaffle/Sidemantic `{PIN}`.",
        f"- Manifest SHA-256: `{report['source_manifest_sha256']}`.",
        f"- Eligibility report SHA-256: `{report['source_eligibility_sha256']}`.",
        f"- Model provenance report SHA-256: `{report['model_provenance_sha256']}`.",
        f"- SQL parser: `sqlglot {report['sql_parser']['version']}`, `{report['sql_parser']['dialect']}` dialect.",
        f"- Local package lock differs from pinned package lock: {lock['working_differs_from_pin']} "
        f"(pinned SHA-256 `{lock['pinned_sha256']}`; local SHA-256 `{lock['working_sha256']}`). "
        "This is separate build provenance uncertainty; it does not establish the cause of the model checksum mismatch.",
        f"- Declarations: {c['declarations']} ({c['metrics']} metrics, {c['measures']} measures); "
        f"{c['unknown_numeric_eligibility']} unknown numeric eligibility.",
        f"- Exact manifest measure paths: {c['with_exact_measure_link']}; unique model candidates: "
        f"{c['with_unique_model_candidate']}. These are candidate mappings, not equivalence labels.",
        f"- Compiled metric expressions verified: {c['compiled_metric_expressions_verified']}; "
        f"needs review: {c['compiled_metric_expressions_needs_review']}.",
        "",
        "## Stop reasons by affected declaration",
        "",
        "| Reason | Declarations |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{reason}` | {count} |" for reason, count in sorted(reasons.items()))
    lines += ["", "## Distinct declarations", "", "| ID | Model candidate | Measure paths | Expression status |",
              "| --- | --- | ---: | --- |"]
    for record in report["records"]:
        model = record["model_candidate"]
        lines.append(f"| `{record['id']}` | `{model['id'] if model else 'unresolved/multiple'}` "
                     f"| {len(record['measure_links'])} | `{record['compiled_metric_expression_status']}` |")
    lines += ["", "## Interpretation", "",
              "The source YAML and compiled model hash references are in the JSON report. "
              "The compiled SQL files match their manifest text in the prior model provenance audit, "
              "but Jaffle model source checksums do not reconcile; the manifest build commit is unverified. "
              "The selected compiled models contain CTEs and unexpanded stars, with join ambiguity for some fields. "
              "No compiled metric query is present, so a measure-to-model mapping is never promoted to "
              "a verified metric expression.",
              "", "The 32 IDs remain separate; derived dependencies never collapse measures into metrics. "
              "Nothing here measures matching accuracy or establishes semantic equivalence.",
              "", "Reproduce from the workspace root: "
              "`python3 -B metric_matching_pilot/generic_metric_expression_trace.py --check`.",
              ""]
    return "\n".join(lines)


def self_test() -> None:
    try:
        pinned_checkout("0" * 40)
    except ValueError as e:
        assert str(e) == "wrong_commit_pin"
    else:
        raise AssertionError("wrong commit accepted")
    manifest = {
        "metrics": {"metric.demo.revenue": {
            "name": "revenue", "type": "simple",
            "type_params": {"measure": {"name": "amount"}},
            "depends_on": {"nodes": ["semantic_model.demo.orders"]}}},
        "semantic_models": {"semantic_model.demo.orders": {
            "measures": [{"name": "amount", "expr": "amount", "agg": "sum"},
                         {"name": "amount", "expr": "other", "agg": "sum"}],
            "depends_on": {"nodes": ["model.demo.orders"]}}},
        "nodes": {"model.demo.orders": {}},
    }
    _, reasons = metric_measure_links("metric.demo.revenue", manifest, {}, {})
    assert "ambiguous_or_missing_measure_name_within_explicit_semantic_model" in reasons
    projections, owner, stops = trace_projections(
        "WITH a AS (SELECT * FROM x) SELECT a.*, b.amount FROM a JOIN b ON a.id=b.id",
        ["amount"])
    assert "unexpanded_select_star" in stops and "join_field_owner_ambiguous" in stops
    assert owner != "candidate_only" and projections
    _, owner, stops = trace_projections("SELECT other AS amount FROM x", ["missing"])
    assert owner == "unresolved" and "missing_explicit_field_projection" in stops
    _, owner, stops = trace_projections("SELECT amount FROM x", ["amount"])
    assert owner == "candidate_only" and not stops
    original = b"SELECT amount FROM x"
    hash_value = digest(original)
    assert compiled_hashes_match(original, original.decode(), hash_value, hash_value)
    assert not compiled_hashes_match(original + b" -- tamper", original.decode(),
                                     hash_value, hash_value)
    sample = {"nodes": {"model.demo.orders": {"original_file_path": "a.sql",
                                             "compiled_code": "SELECT amount FROM x"}}}
    case = {"build_event": {"commit_attested_by_build": False}}
    node = {"node_id": "model.demo.orders", "compiled_path": "target/compiled/x.sql",
            "status": "needs_review", "manifest_source_checksum": {"versus_manifest_raw_code": "different"},
            "compiled_file": {"sha256": "f" * 64},
            "manifest_compiled_code_sha256": "f" * 64, "source_path": "a.sql"}
    info, _, stops = model_info("model.demo.orders", sample, {}, case,
                                {"model.demo.orders": node})
    assert info["compiled_file_sha256"] is None and "compiled_file_hash_mismatch" in stops
    assert "manifest_source_checksum_mismatch" in stops and "build_commit_unverified" in stops
    print("self-test passed: wrong commit, ambiguous measure, star/join, missing field owner, "
          "tampered/missing compiled file, source checksum, build attestation")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-commit", default=PIN,
                   help="fixed checkout pin; other commits are rejected")
    p.add_argument("--check", action="store_true", help="compare reports without writing")
    p.add_argument("--self-test", action="store_true", help="in-memory adversarial controls")
    args = p.parse_args()
    if args.self_test:
        self_test()
        return 0
    result = build(args.expected_commit)
    outputs = {
        OUTPUT_JSON: (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"),
        OUTPUT_MD: render_markdown(result).encode("utf-8"),
    }
    if args.check:
        errors = [str(path) for path, expected in outputs.items()
                  if not path.is_file() or path.read_bytes() != expected]
        if errors:
            print("report mismatch: " + ", ".join(errors), file=sys.stderr)
            return 1
        print("read-only check passed: both expression trace reports")
        return 0
    for path, data in outputs.items():
        path.write_bytes(data)
    print(f"wrote {OUTPUT_JSON.name} and {OUTPUT_MD.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"expression trace failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
