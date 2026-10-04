#!/usr/bin/env python3
"""Label-free, development-only common-input metric comparison diagnostic.

Reads the existing eligibility, compiled-model, and final expression-trace
reports. An explicit --no-expression-trace fallback is available but is not
the committed report. A trace cannot certify semantic equivalence.
The I0 name scores follow generic_same_input_baselines.py, with Soundex added.
No repository files, gold labels, SQL rows, or held-out projects are read.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
ELIGIBILITY = ROOT / "generic_metric_eligibility_manifest_report.json"
PROVENANCE = ROOT / "generic_compiled_provenance_report.json"
EXPRESSION_TRACE = ROOT / "generic_metric_expression_trace_report.json"
JSON_OUT = ROOT / "generic_i1_same_input_report.json"
MD_OUT = ROOT / "generic_i1_same_input_report.md"
VERSION = "generic_i1_same_input_v1"
PREREQUISITES = ("source", "grain", "time", "filter", "null_policy", "snapshot",
                 "population", "unit", "join_cardinality", "transformation")
I0_FIELDS = ("id", "name")
I1_METHODS = ("normalized_ast_source", "constraint_aware", "source_guided_conditional")
I0_METHODS = ("raw_exact", "normalized_name_exact", "jaro_winkler",
              "token_jaccard", "soundex")
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
WORD = re.compile(r"[a-z0-9]+")
HEX_SHA = re.compile(r"[0-9a-f]{64}\Z")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def tokens(value: str) -> list[str]:
    return WORD.findall(CAMEL.sub(" ", value).casefold())


def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    radius = max(0, max(len(a), len(b)) // 2 - 1)
    am, bm = [False] * len(a), [False] * len(b)
    matches = 0
    for i, letter in enumerate(a):
        for j in range(max(0, i - radius), min(len(b), i + radius + 1)):
            if not bm[j] and b[j] == letter:
                am[i] = bm[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    aa = [letter for letter, used in zip(a, am) if used]
    bb = [letter for letter, used in zip(b, bm) if used]
    swaps = sum(x != y for x, y in zip(aa, bb)) / 2
    return (matches / len(a) + matches / len(b)
            + (matches - swaps) / matches) / 3


def jaro_winkler(a: str, b: str) -> float:
    base = jaro(a, b)
    if base < 0.7:
        return base
    prefix = 0
    for x, y in zip(a[:4], b[:4]):
        if x != y:
            break
        prefix += 1
    return base + .1 * prefix * (1 - base)


def soundex(name: str) -> str:
    """American Soundex, first letter retained; H/W do not break adjacency."""
    letters = re.sub(r"[^A-Z]", "", name.upper())
    if not letters:
        return ""
    groups = {letter: number for number, chars in enumerate(
        ("", "BFPV", "CGJKQSXZ", "DT", "L", "MN", "R"))
        for letter in chars}
    result = letters[0]
    previous = groups.get(letters[0], 0)
    for letter in letters[1:]:
        if letter in "HW":
            continue
        number = groups.get(letter, 0)
        if number and number != previous:
            result += str(number)
        previous = number
    return (result + "000")[:4]


def score_names(a: str, b: str) -> dict:
    na, nb = " ".join(tokens(a)), " ".join(tokens(b))
    ta, tb = set(tokens(a)), set(tokens(b))
    return {
        "raw_exact": int(a == b),
        "normalized_name_exact": int(na == nb),
        "jaro_winkler": round(jaro_winkler(na, nb), 6),
        "token_jaccard": round(len(ta & tb) / len(ta | tb), 6) if ta | tb else 0.0,
        "soundex": int(soundex(a) != "" and soundex(a) == soundex(b)),
    }


def expected_pairs(ids: list[str]) -> list[list[str]]:
    return [list(pair) for pair in itertools.combinations(sorted(ids), 2)]


def checked_inputs(eligibility: dict, provenance: dict) -> tuple[list[dict], list[list[str]], list[list[str]], dict]:
    """Validate complete emitted frames and same-repository model evidence."""
    require(eligibility.get("schema_version") == 1 and
            eligibility.get("scope") == "development_only_declared_dbt_metric_output_inventory",
            "Unexpected eligibility schema or scope")
    candidates = eligibility.get("candidates")
    require(isinstance(candidates, list) and len(candidates) == 32,
            "Expected the complete 32-declaration development frame")
    require(all(isinstance(c, dict) and isinstance(c.get("id"), str) and
                isinstance(c.get("name"), str) and
                c.get("kind") in ("metric", "measure") and
                c.get("eligibility") in ("eligible", "unknown") for c in candidates),
            "Malformed candidate or missing/unknown eligibility")
    ids = [c["id"] for c in candidates]
    require(len(set(ids)) == 32 and ids == sorted(ids), "Candidate IDs must be unique and sorted")
    require(sum(c["kind"] == "metric" for c in candidates) == 19 and
            sum(c["kind"] == "measure" for c in candidates) == 13,
            "Expected 19 metrics and 13 measures")
    frames = eligibility.get("frames", {})
    primary = frames.get("primary_exposed_metrics", {})
    secondary = frames.get("secondary_all_declared_scalars", {})
    primary_ids = sorted(c["id"] for c in candidates if c["kind"] == "metric")
    all_pairs, primary_pairs = expected_pairs(ids), expected_pairs(primary_ids)
    index = {c["id"]: c for c in candidates}
    for frame, frame_ids, pairs in ((primary, primary_ids, primary_pairs),
                                   (secondary, ids, all_pairs)):
        require(frame.get("candidate_ids") == frame_ids, "Incomplete or reordered frame IDs")
        rows = frame.get("pairs")
        require(isinstance(rows, list) and len(rows) == len(pairs) and
                [[p.get("left_id"), p.get("right_id")] for p in rows if isinstance(p, dict)] == pairs,
                "Missing, duplicated, or reordered pair in input frame")
        for pair, item in zip(pairs, rows):
            l, r = (index[identifier]["eligibility"] for identifier in pair)
            require(item.get("left_status") == l and item.get("right_status") == r and
                    item.get("eligibility") == ("eligible" if l == r == "eligible" else "unknown"),
                    "Input pair eligibility disagrees with candidate status")
    coverage = eligibility.get("coverage", {})
    require(coverage.get("candidate_scalar_definitions") == 32 and
            coverage.get("declared_metrics") == 19 and coverage.get("declared_measures") == 13 and
            coverage.get("all_declared_scalar_pairs") == 496 and
            coverage.get("primary_metric_pairs") == 171 and
            coverage.get("eligible") == sum(c["eligibility"] == "eligible" for c in candidates) and
            coverage.get("unknown") == sum(c["eligibility"] == "unknown" for c in candidates),
            "Eligibility coverage counters disagree with complete frames")
    manifest_sha = eligibility.get("provenance", {}).get("manifest", {}).get("sha256")
    repo_commit = eligibility.get("provenance", {}).get("repo_commit")
    project = eligibility.get("provenance", {}).get("project")
    require(isinstance(manifest_sha, str) and bool(HEX_SHA.fullmatch(manifest_sha)) and
            isinstance(repo_commit, str) and len(repo_commit) == 40 and
            isinstance(project, str), "Eligibility provenance is incomplete")
    require(provenance.get("schema") == "generic_compiled_model_provenance_v1" and
            provenance.get("scope") == "development_only", "Unexpected model provenance scope")
    cases = [case for case in provenance.get("cases", [])
             if case.get("expected_project") == project and case.get("expected_commit") == repo_commit]
    require(len(cases) == 1, "No unique same-project, same-commit compiled provenance case")
    case = cases[0]
    require(case.get("manifest_file", {}).get("sha256") == manifest_sha and
            case.get("checked_out_commit_matches_pin") is True and
            case.get("manifest_metadata", {}).get("project_name") == project,
            "Manifest SHA or model provenance identity differs")
    nodes = case.get("nodes", [])
    node_index = {n.get("node_id"): n for n in nodes}
    require(len(node_index) == len(nodes) and all(isinstance(nid, str) for nid in node_index),
            "Duplicate or malformed compiled model nodes")
    return candidates, all_pairs, primary_pairs, {"case": case, "nodes": node_index,
                                                   "manifest_sha256": manifest_sha}


def checked_trace(trace: dict | None, manifest_sha: str, eligibility_sha: str,
                  provenance_sha: str, ids: list[str], context: dict) -> dict[str, dict]:
    if trace is None:
        return {}
    expected = {"schema_version", "source_manifest_sha256",
                "source_eligibility_sha256", "model_provenance_sha256", "records"}
    require(isinstance(trace, dict) and expected.issubset(trace) and
            trace["schema_version"] == 1 and
            trace.get("scope") == "pinned_public_development_only" and
            trace["source_manifest_sha256"] == manifest_sha and
            trace["source_eligibility_sha256"] == eligibility_sha and
            trace["model_provenance_sha256"] == provenance_sha,
            "Expression trace hash, schema, or development scope disagree with inputs")
    require(isinstance(trace.get("source"), dict) and
            trace["source"].get("repo_commit") == context["case"]["expected_commit"] and
            trace["source"].get("manifest_path") == context["case"]["manifest_path"] and
            trace["source"].get("manifest_build_commit_attested") is False,
            "Expression trace repository pin or manifest source differs")
    records = trace["records"]
    require(isinstance(records, list) and len(records) == len(ids) and
            all(isinstance(r, dict) and isinstance(r.get("id"), str) and
                isinstance(r.get("compiled_metric_expression_status"), str) and
                bool(r["compiled_metric_expression_status"]) and
                "model_candidate" in r for r in records),
            "Expression trace records must have IDs, status, and model_candidate")
    mapping = {r["id"]: r for r in records}
    require(len(mapping) == len(records) and set(mapping) == set(ids),
            "Expression trace ID set differs from all 32 declarations")
    if "coverage" in trace:
        counts = trace["coverage"]
        require(isinstance(counts, dict) and counts.get("declarations") == len(ids) and
                counts.get("metrics") == 19 and counts.get("measures") == 13 and
                counts.get("compiled_metric_expressions_verified") == sum(
                    r["compiled_metric_expression_status"] == "verified" for r in records),
                "Expression trace coverage counters disagree with ID set")
    return mapping


def packet_declaration(candidate: dict, trace: dict | None, context: dict) -> dict:
    source = candidate.get("source") or {}
    require(isinstance(source, dict) and isinstance(source.get("path"), str) and
            isinstance(source.get("sha256"), str) and bool(HEX_SHA.fullmatch(source["sha256"])) and
            isinstance(source.get("git_blob"), str), "Missing candidate source evidence")
    if trace:
        require(trace.get("id") == candidate["id"] and trace.get("kind") == candidate["kind"] and
                trace.get("name") == candidate["name"] and
                trace.get("numeric_eligibility") == candidate["eligibility"],
                "Trace record identity or eligibility differs from input")
    model_candidate = trace.get("model_candidate") if trace else None
    # A model candidate is evidence only when explicitly traced to one exact
    # known node. No filename/name matching is performed in this script.
    require(model_candidate is None or isinstance(model_candidate, dict),
            "Trace model_candidate must be an object or null")
    model_id = model_candidate.get("id") if model_candidate else None
    require(model_id is None or (isinstance(model_id, str) and model_id in context["nodes"]),
            "Trace model_candidate does not identify one known model node")
    model = context["nodes"].get(model_id) if model_id else None
    if model_candidate:
        for key, expected_value in {
            "manifest_compiled_code_sha256": model["manifest_compiled_code_sha256"],
            "compiled_file_sha256": model["compiled_file"]["sha256"],
            "manifest_raw_code_sha256": model["manifest_raw_code_sha256"],
            "source_sha256": model["pinned_source"]["sha256"],
            "source_path": model["source_path"],
            "compiled_path": model["compiled_path"],
            "model_provenance_status": model["status"],
            "build_commit_attested": context["case"]["build_event"]["commit_attested_by_build"],
        }.items():
            require(model_candidate.get(key) == expected_value,
                    f"Trace model_candidate {key} differs from compiled provenance")
        require(model_candidate.get("manifest_source_checksum") == model["manifest_source_checksum"],
                "Trace model_candidate source checksum differs from compiled provenance")
    trace_status = trace["compiled_metric_expression_status"] if trace else "not_supplied"
    require(trace_status in ("not_supplied", "needs_review", "verified", "unverified"),
            "Unsupported expression trace status")
    model_ok = bool(model and model.get("status") == "model_artifact_checks_pass" and
                    model.get("compiled_file_vs_manifest_compiled_code") == "exact" and
                    model.get("manifest_source_checksum", {}).get("versus_manifest_raw_code") == "exact")
    source_ok = source.get("source_mapping_verified") is True
    # A verified string in a trace is a claim, not a substitute for the
    # independent model/source checks and an explicitly verified YAML mapping.
    effective = "verified" if trace_status == "verified" and model_ok and source_ok else "needs_review"
    raw_expression = trace.get("compiled_metric_expression") if trace else None
    normalized_ast = trace.get("normalized_ast") if trace else None
    if raw_expression is not None:
        require(isinstance(raw_expression, str), "Trace expression must be text")
    if normalized_ast is not None:
        require(isinstance(normalized_ast, (dict, list, str)), "Trace AST must be JSON AST/text")
    if trace:
        require(trace.get("declared_metric_expression") is None or
                isinstance(trace["declared_metric_expression"], str),
                "Malformed declared metric expression")
        require(trace.get("declared_metric_filter") is None or
                isinstance(trace["declared_metric_filter"], (str, dict)),
                "Malformed declared metric filter")
    links = trace.get("measure_links", []) if trace else []
    require(isinstance(links, list) and all(isinstance(link, dict) and
            isinstance(link.get("measure_id"), str) and
            isinstance(link.get("measure_expr"), str) and
            isinstance(link.get("binding_status"), str) for link in links),
            "Malformed declared measure expression links")
    require(len({link["measure_id"] for link in links}) == len(links) and
            all(link["binding_status"] == "exact_manifest_resource_and_measure" for link in links),
            "Duplicate or non-exact declared measure expression link")
    for link in links:
        measure = context["candidate_index"].get(link["measure_id"])
        require(measure is not None and measure["kind"] == "measure" and
                link.get("measure_agg") == measure.get("aggregate") and
                link.get("measure_name") == measure["name"] and
                link.get("semantic_model_id") == measure["source"]["manifest_resource_id"],
                "Trace declared measure link differs from eligible resource-qualified measure")
    linked_expressions = [{"measure_id": link["measure_id"],
                           "declared_measure_expression": link["measure_expr"],
                           "declared_measure_aggregate": link.get("measure_agg"),
                           "expression_defaulted_to_name": link.get("measure_expr_defaulted_to_name"),
                           "binding_status": link["binding_status"],
                           "semantic_model_id": link.get("semantic_model_id"),
                           "model_id": link.get("model_id")}
                          for link in links]
    deps = candidate.get("declared_dependencies") or {}
    require(isinstance(deps, dict), "Malformed candidate dependencies")
    type_params = deps.get("type_params") if isinstance(deps.get("type_params"), dict) else {}
    missing = list(PREREQUISITES)
    stops = []
    if candidate["eligibility"] == "unknown":
        stops.append("numeric_eligibility_unknown")
    if not source_ok:
        stops.append("declaration_source_mapping_unverified")
    if context["case"].get("status") == "needs_review":
        stops.append("compiled_model_source_checksums_need_review")
    if trace_status != "verified":
        stops.append("compiled_metric_expression_unverified")
    if not model_ok:
        stops.append("model_artifact_or_binding_unverified")
    stops += [f"{field}_unknown" for field in missing if field != "source"]
    return {
        "id": candidate["id"], "name": candidate["name"], "kind": candidate["kind"],
        "eligibility": candidate["eligibility"], "eligibility_reasons": candidate.get("reasons", []),
        "metric_type": candidate.get("metric_type"), "declared_data_type": candidate.get("declared_data_type"),
        "aggregate": candidate.get("aggregate"),
        "declared_expression": trace.get("declared_metric_expression") if trace else type_params.get("expr"),
        "declared_expression_evidence": "trace_source_declaration_unverified" if trace else "eligibility_declaration_unverified",
        "declared_metric_filter": trace.get("declared_metric_filter") if trace else None,
        "linked_declared_measure_expressions": linked_expressions,
        "unique_declared_measure_expression": (linked_expressions[0]["declared_measure_expression"]
                                                 if len(linked_expressions) == 1 else None),
        "declared_dependencies": {
            "nodes": candidate.get("depends_on_nodes", []),
            "supporting_measure_refs": candidate.get("supporting_measure_refs", []),
            "type_params": type_params,
        },
        "source": {key: source.get(key) for key in ("path", "sha256", "git_blob",
                                                    "manifest_resource_id", "source_mapping_verified")},
        "artifact": {"manifest_sha256": context["manifest_sha256"],
                     "model_node_id": model_id,
                     "compiled_code_sha256": model.get("manifest_compiled_code_sha256") if model else None,
                     "pinned_source_sha256": model.get("pinned_source", {}).get("sha256") if model else None,
                     "compiled_file_sha256": model.get("compiled_file", {}).get("sha256") if model else None,
                     "model_status": model.get("status") if model else "unmapped",
                     "build_commit_attested": context["case"].get("build_event", {}).get("commit_attested_by_build", False)},
        "expression_trace": {"status_reported": trace_status, "status_effective": effective,
                             "compiled_metric_expression": raw_expression,
                             "normalized_ast": normalized_ast,
                             "field_owner_statuses": sorted({row["field_owner_status"]
                                 for row in trace.get("field_traces", []) if isinstance(row, dict)
                                 and isinstance(row.get("field_owner_status"), str)}) if trace else [],
                             "stop_reasons_reported": trace.get("stop_reasons", []) if trace else []},
        "semantic_prerequisites": {field: "unknown" for field in PREREQUISITES},
        "stop_reasons": sorted(set(stops)),
    }


def semantic_stop(left: dict, right: dict) -> tuple[list[str], str]:
    missing = sorted(field for field in PREREQUISITES if
                     left["semantic_prerequisites"][field] == "unknown" or
                     right["semantic_prerequisites"][field] == "unknown")
    if left["eligibility"] != "eligible" or right["eligibility"] != "eligible":
        return missing, "numeric_eligibility_unknown"
    if (left["expression_trace"]["status_effective"] != "verified" or
            right["expression_trace"]["status_effective"] != "verified"):
        return missing, "expression_or_model_provenance_unverified"
    if missing:
        return missing, "semantic_prerequisites_missing"
    return missing, "no_formal_equivalence_proof"


def compare_i1(method: str, packet_bytes: bytes, pair_ids: list[list[str]]) -> list[dict]:
    """Each method independently decodes the *same exact* canonical I1 bytes."""
    packet = json.loads(packet_bytes)
    require(packet["pair_ids"] == pair_ids, "Method did not receive the common pair set")
    lookup = {c["id"]: c for c in packet["declarations"]}
    output = []
    for left_id, right_id in pair_ids:
        left, right = lookup[left_id], lookup[right_id]
        missing, reason = semantic_stop(left, right)
        if method == "normalized_ast_source":
            la, ra = left["expression_trace"], right["expression_trace"]
            if (la["status_effective"] == ra["status_effective"] == "verified" and
                    la["normalized_ast"] is not None and ra["normalized_ast"] is not None and
                    left["artifact"]["model_node_id"] and right["artifact"]["model_node_id"]):
                equal = (la["normalized_ast"] == ra["normalized_ast"] and
                         left["artifact"]["model_node_id"] == right["artifact"]["model_node_id"])
                signal = "same_normalized_ast_and_model" if equal else "different_ast_or_model"
            else:
                signal = "abstain_unverified_ast_or_source"
        elif method == "constraint_aware":
            same_ref = bool(set(left["declared_dependencies"]["supporting_measure_refs"]) &
                            set(right["declared_dependencies"]["supporting_measure_refs"]))
            signal = "shared_declared_measure_review_candidate" if same_ref else "abstain_no_shared_measure_evidence"
        elif method == "source_guided_conditional":
            same_ref = bool(set(left["declared_dependencies"]["supporting_measure_refs"]) &
                            set(right["declared_dependencies"]["supporting_measure_refs"]))
            same_file = left["source"]["path"] == right["source"]["path"] and bool(left["source"]["path"])
            signal = ("shared_declared_measure_review_candidate" if same_ref else
                      "same_declaration_file_review_candidate" if same_file else "abstain_no_shared_context")
        else:
            raise ValueError(f"Unknown I1 method {method}")
        output.append({"left_id": left_id, "right_id": right_id,
                       "syntax_or_review_signal": signal, "semantic_decision": "abstain",
                       "semantic_abstention_reason": reason, "missing_semantic_prerequisites": missing})
    return output


def generate(eligibility_bytes: bytes, provenance_bytes: bytes,
             trace_bytes: bytes | None = None) -> dict:
    eligibility = json.loads(eligibility_bytes)
    provenance = json.loads(provenance_bytes)
    candidates, pair_ids, primary_pairs, context = checked_inputs(eligibility, provenance)
    context["candidate_index"] = {c["id"]: c for c in candidates}
    trace = json.loads(trace_bytes) if trace_bytes is not None else None
    traces = checked_trace(trace, context["manifest_sha256"], digest(eligibility_bytes),
                           digest(provenance_bytes), [c["id"] for c in candidates], context)
    declarations = [packet_declaration(c, traces.get(c["id"]), context) for c in candidates]
    index = {c["id"]: c for c in declarations}
    i1_packet = {"schema_version": 1, "declarations": declarations, "pair_ids": pair_ids}
    i0_packet = {"schema_version": 1,
                 "declarations": [{key: c[key] for key in I0_FIELDS} for c in candidates],
                 "pair_ids": pair_ids}
    i1_bytes, i0_bytes = canonical_bytes(i1_packet), canonical_bytes(i0_packet)
    pair_sha = digest(canonical_bytes(pair_ids))
    primary_sha = digest(canonical_bytes(primary_pairs))
    i1_outputs = {m: compare_i1(m, i1_bytes, pair_ids) for m in I1_METHODS}
    i0_lookup = {c["id"]: c["name"] for c in i0_packet["declarations"]}
    rows = []
    for n, (left_id, right_id) in enumerate(pair_ids):
        methods = {m: i1_outputs[m][n] for m in I1_METHODS}
        require(all((row["left_id"], row["right_id"]) == (left_id, right_id)
                    for row in methods.values()), "I1 pair identity drift")
        rows.append({"left_id": left_id, "right_id": right_id,
                     "i0_name_scores": score_names(i0_lookup[left_id], i0_lookup[right_id]),
                     "i1": {m: {k: v for k, v in result.items() if k not in ("left_id", "right_id")}
                            for m, result in methods.items()}})
    require(len(rows) == 496 and all(len(i1_outputs[m]) == 496 for m in I1_METHODS),
            "Output pair coverage incomplete")
    input_meta = {"source_manifest_sha256": context["manifest_sha256"],
                  "source_eligibility_sha256": digest(eligibility_bytes),
                  "model_provenance_sha256": digest(provenance_bytes),
                  "expression_trace_sha256": digest(trace_bytes) if trace_bytes is not None else None,
                  "expression_trace_supplied": trace_bytes is not None}
    method_inputs = {
        m: {"version": f"{m}_v1", "input_level": "I1", "packet_sha256": digest(i1_bytes),
            "packet_bytes": len(i1_bytes), "pair_ids_sha256": pair_sha, "pair_count": 496,
            "evidence_fields_used": fields}
        for m, fields in {
            "normalized_ast_source": ["expression_trace.status_effective", "expression_trace.normalized_ast", "artifact.model_node_id"],
            "constraint_aware": ["declared_dependencies.supporting_measure_refs", "eligibility", "expression_trace.status_effective", "semantic_prerequisites"],
            "source_guided_conditional": ["declared_dependencies.supporting_measure_refs", "source.path", "eligibility", "expression_trace.status_effective", "semantic_prerequisites"],
        }.items()}
    method_inputs.update({m: {"version": f"{m}_v1", "input_level": "I0_name_only",
                              "packet_sha256": digest(i0_bytes), "packet_bytes": len(i0_bytes),
                              "pair_ids_sha256": pair_sha, "pair_count": 496,
                              "evidence_fields_used": list(I0_FIELDS)} for m in I0_METHODS})
    return {
        "schema_version": 1, "algorithm_version": VERSION,
        "scope": "public_development_only_label_free_manifest_same_input",
        "input": input_meta,
        "primary_exposed_metric_frame": {
            "candidate_ids": [c["id"] for c in candidates if c["kind"] == "metric"],
            "pair_ids": primary_pairs, "pair_ids_sha256": primary_sha},
        "pair_universe": {
            "all_declaration_ids": 32, "metrics": 19, "measures": 13,
            "all_unordered_pairs": 496, "all_pair_ids_sha256": pair_sha,
            "primary_exposed_metric_ids": 19, "primary_exposed_metric_pairs": 171,
            "primary_pair_ids_sha256": primary_sha,
            "true_unemitted_declaration_arity_known": False,
            "held_out": False},
        "i1_packet": i1_packet, "i1_packet_sha256": digest(i1_bytes),
        "i0_name_only_packet": i0_packet, "i0_name_only_packet_sha256": digest(i0_bytes),
        "method_inputs": method_inputs,
        "coverage": {"eligibility": dict(sorted(Counter(c["eligibility"] for c in declarations).items())),
                     "all_pair_numeric_eligibility": dict(sorted(Counter(
                         "eligible" if all(index[identifier]["eligibility"] == "eligible" for identifier in pair)
                         else "unknown" for pair in pair_ids).items())),
                     "trace_expression_status_reported": dict(sorted(Counter(
                         c["expression_trace"]["status_reported"] for c in declarations).items())),
                     "unique_model_candidates": sum(c["artifact"]["model_node_id"] is not None for c in declarations),
                     "declarations_with_declared_expression": sum(c["declared_expression"] is not None for c in declarations),
                     "declarations_with_declared_filter": sum(c["declared_metric_filter"] is not None for c in declarations),
                     "declarations_with_unique_linked_measure_expression": sum(
                         c["unique_declared_measure_expression"] is not None for c in declarations),
                     "unknown_prerequisites_by_field": {field: sum(c["semantic_prerequisites"][field] == "unknown"
                         for c in declarations) for field in PREREQUISITES},
                     "i1_syntax_or_review_signals": {m: dict(sorted(Counter(
                         r["syntax_or_review_signal"] for r in output).items()))
                         for m, output in i1_outputs.items()},
                     "i1_semantic_abstentions_per_method": {m: 496 for m in I1_METHODS},
                     "i1_semantic_decisions_per_method": {m: 0 for m in I1_METHODS},
                     "i0_scored_pairs_per_method": {m: 496 for m in I0_METHODS}},
        "rows": rows,
        "limitations": [
            "All pair counts are complete over the 32 emitted manifest declarations, not a known full project metric universe.",
            "A measure dependency is a review signal, not a label; 146 same-file review candidates are weak co-location signals, may be noisy, and imply neither a transformation nor conditional equivalence.",
            "Manifest build time is a separate event; the compiled-model provenance report marks Jaffle source checksums needs_review.",
            "The final expression trace supplies source-declared expressions, filters and model candidates; it verifies zero compiled metric expressions. Declared expressions are not compiled queries.",
            "This comparator does not parse compiled SQL with SQLGlot or establish complete AST/SQLGlot coverage from manifest declarations.",
            "Native grain, time, filter, NULL, snapshot, population, unit, join cardinality, and transformation semantics are unknown in these inputs.",
            "No human gold, row outcome, AI review label, candidate recall, classification F1, review-effort outcome, or method superiority is measured.",
        ],
    }


def markdown(report: dict) -> str:
    u, c = report["pair_universe"], report["coverage"]
    lines = ["# I1 same-input packet (public development only)", "",
             f"Algorithm: `{VERSION}`. No optional expression trace was supplied." if not report["input"]["expression_trace_supplied"] else
             f"Algorithm: `{VERSION}`. Integrated final expression trace SHA256: `{report['input']['expression_trace_sha256']}`.",
             f"Input eligibility SHA256: `{report['input']['source_eligibility_sha256']}`. Model provenance SHA256: `{report['input']['model_provenance_sha256']}`. Manifest SHA256: `{report['input']['source_manifest_sha256']}`.",
             f"All {u['all_declaration_ids']} emitted declarations ({u['metrics']} metrics, {u['measures']} measures): {u['all_unordered_pairs']} pairs, SHA256 `{u['all_pair_ids_sha256']}`. The {u['primary_exposed_metric_ids']} exposed metrics have {u['primary_exposed_metric_pairs']} separate pairs, SHA256 `{u['primary_pair_ids_sha256']}`.",
             f"Shared I1 canonical packet SHA256: `{report['i1_packet_sha256']}`; I0 name-only packet SHA256: `{report['i0_name_only_packet_sha256']}`.",
             f"Numeric eligibility: {c['eligibility'].get('eligible', 0)} eligible, {c['eligibility'].get('unknown', 0)} unknown; pair statuses {c['all_pair_numeric_eligibility']}. Unknown records remain in all pairs.",
             f"Trace status: {c['trace_expression_status_reported']}; {c['unique_model_candidates']} unique model candidates, {c['declarations_with_unique_linked_measure_expression']} unique linked declared measure expressions, {c['declarations_with_declared_expression']} declared metric expressions, {c['declarations_with_declared_filter']} declared metric filters. Compiled metric expressions reported verified: {c['trace_expression_status_reported'].get('verified', 0)}.",
             f"Unknown native semantic prerequisites by field (out of 32 declarations): {c['unknown_prerequisites_by_field']}.",
             "", "## Shared inputs and outputs", "",
             "| Method | Evidence | Pairs | Semantic decisions | Signal summary |",
             "| --- | --- | ---: | ---: | --- |"]
    for method in I0_METHODS:
        lines.append(f"| {method} v1 | names only | 496 | 0 | name score |")
    for method in I1_METHODS:
        counts = c["i1_syntax_or_review_signals"][method]
        summary = ", ".join(f"{key}: {count}" for key, count in counts.items())
        lines.append(f"| {method} v1 | same I1 packet | 496 | 0 | {summary} |")
    lines += ["", "All three I1 methods receive identical canonical bytes and pair IDs. The five I0 methods receive the same pair IDs with only qualified IDs and names. An exact shared measure reference creates a review signal only. The 146 same-declaration-file review candidates are weak co-location signals and may be noisy: they are NOT transformation suggestions or conditional equivalence. There is no comparison win. Constraint-aware checks list missing semantic prerequisites; source-guided conditional first uses exact measure references, then the declaration file. No thresholds are tuned.",
              "", "The normalized AST/source method needs a verified compiled metric expression, owner and normalized AST. The trace contains source-declared expressions and filters, not compiled metric queries or normalized SQL ASTs. This implementation does not perform SQLGlot extraction and cannot claim complete SQLGlot or AST coverage from manifest declarations. It abstains on all 496 pairs.",
              "", "Soundex uses the English letter groups BFPV=1, CGJKQSXZ=2, DT=3, L=4, MN=5, R=6; the first letter is kept, H/W do not reset adjacency, and the code is four characters. Other I0 scores use the local same-input baseline formulas: raw name equality, camel/punctuation normalized equality, Jaro-Winkler (0.1 prefix weight after Jaro >= 0.7), and token-set Jaccard. The full resource ID identifies a pair but is excluded from the score.",
              "", "Every I1 semantic decision abstains: the supplied reports do not establish compiled metric-expression lineage or verified source mapping, and native grain, time, filter, NULL behavior, snapshot, population, unit, join cardinality, and transformation prerequisites remain unknown. Source-declared expressions, filters, and measure links are preserved as unverified declarations. A trace claiming `verified` cannot override a source checksum mismatch. The 13 Jaffle compiled model sources remain under review even though compiled files match manifest code.",
              "", "Pair completeness is only over emitted IDs; malformed declarations could hide an unknown number of other IDs. There is no human gold, accuracy, review-effort or superiority estimate. No held-out source was opened.",
              "", "## Reproduction", "",
              "Run `python3 -B metric_matching_pilot/generic_i1_same_input.py --check` to verify this final trace-integrated report byte for byte without writing. `--expression-trace PATH` explicitly selects an alternate trace with matching hash references and 32-ID set. `--no-expression-trace` is an unreported diagnostic fallback and does not match this report.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expression-trace", type=Path, default=EXPRESSION_TRACE,
                        help="versioned expression-trace JSON (defaults to final development trace)")
    parser.add_argument("--no-expression-trace", dest="expression_trace", action="store_const", const=None,
                        help="unreported fallback that omits expression trace")
    parser.add_argument("--check", action="store_true", help="byte-check both reports without writing")
    args = parser.parse_args()
    trace_bytes = args.expression_trace.read_bytes() if args.expression_trace else None
    report = generate(ELIGIBILITY.read_bytes(), PROVENANCE.read_bytes(), trace_bytes)
    rendered = {JSON_OUT: (json.dumps(report, indent=2, ensure_ascii=False,
                                      allow_nan=False) + "\n").encode("utf-8"),
                MD_OUT: markdown(report).encode("utf-8")}
    if args.check:
        for path, expected in rendered.items():
            if not path.is_file() or path.read_bytes() != expected:
                raise SystemExit(f"FAIL: missing or stale {path.name}; --check wrote nothing")
        print("PASS: input identity, full pair sets, common packet and reports agree; --check wrote nothing")
    else:
        for path, data in rendered.items():
            path.write_bytes(data)
        print(f"Wrote {JSON_OUT.name} and {MD_OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
