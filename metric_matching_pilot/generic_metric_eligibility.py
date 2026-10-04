#!/usr/bin/env python3
"""Conservative, label-free dbt metric-output eligibility inventory.

Read a pinned Git tree's source YAML, or a supplied local dbt manifest alongside
that tree. A manifest's build revision cannot be established from its JSON alone.
This development adapter does not read model SQL, warehouse rows, or labels.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import re
import shlex
import subprocess

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


HERE = Path(__file__).resolve().parent
DEFAULT_PREFIX = HERE / "generic_metric_eligibility_report"
NUMERIC_AGGS = frozenset(("sum", "count", "count_distinct", "average", "avg", "median"))
NUMERIC_TYPES = frozenset(("int", "integer", "bigint", "smallint", "float", "double",
                           "decimal", "numeric", "number", "real", "double precision"))


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def pinned_blobs(repo: Path, expected: str) -> tuple[str, dict[str, tuple[str, bytes]]]:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", expected):
        raise ValueError("--expected-commit must be a complete 40-character SHA")
    root = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != repo:
        raise ValueError("--repo must be the pinned Git checkout root")
    commit = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if commit != expected.lower():
        raise ValueError(f"Expected {expected}, found {commit}")
    objects = {}
    for item in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, oid = meta.split()
        if kind != b"blob" or mode == b"120000":
            continue
        name = path.decode("utf-8")
        if name in ("dbt_project.yml", "dbt_project.yaml") or name.lower().endswith((".yml", ".yaml")):
            objects[name] = (oid.decode(), git(repo, "cat-file", "blob", oid.decode()))
    return commit, objects


def key_nodes(node: MappingNode, key: str) -> list:
    return [value for label, value in node.value
            if isinstance(label, ScalarNode) and label.value == key]


def node_value(node):
    loader = yaml.SafeLoader("")
    try:
        return loader.construct_object(node, deep=True)
    finally:
        loader.dispose()


def string_field(value, key: str) -> str | None:
    result = value.get(key) if isinstance(value, dict) else None
    return result if isinstance(result, str) else None


def jinja(value) -> bool:
    if isinstance(value, str):
        return bool(re.search(r"\{[{%#]|[%#]}\}", value))
    if isinstance(value, (dict, list)):
        return any(jinja(v) for v in (value.values() if isinstance(value, dict) else value))
    return False


def eligibility(item: dict, aggregate: str | None = None) -> tuple[str, list[str]]:
    """Only declaration-level numeric evidence; never infer value equivalence."""
    if not isinstance(item, dict):
        return "unknown", ["malformed_declaration"]
    if jinja({k: item.get(k) for k in ("name", "type", "agg", "expr", "filter", "type_params")}):
        return "unknown", ["jinja"]
    dtype = item.get("data_type", item.get("dtype"))
    if dtype is not None:
        if not isinstance(dtype, str) or dtype.lower().strip() not in NUMERIC_TYPES:
            return "unknown", ["explicit_type_not_known_numeric"]
    kind = string_field(item, "type")
    agg = aggregate if aggregate is not None else string_field(item, "agg")
    if isinstance(agg, str):
        agg = agg.lower().strip()
    if kind in (None, "simple"):
        if agg in NUMERIC_AGGS:
            return "eligible", ["numeric_aggregate_declaration"]
        return "unknown", ["aggregation_missing" if agg is None else "unresolved_numeric_type"]
    if kind in ("derived", "ratio", "cumulative"):
        # An expression or dependency reference may be unresolved or nonnumeric.
        return "unknown", ["dependency_numeric_type_unverified"]
    return "unknown", ["missing_type" if kind is None else "unsupported_type"]


def record(kind: str, identifier: str, name: str | None, declaration: dict | None,
           source: dict, aggregate: str | None = None, extra_reasons=()) -> dict:
    status, reasons = eligibility(declaration, aggregate)
    # A measure can declare an aggregate without a `type`; a dbt metric
    # without its metric type is malformed even if an `agg` happens to appear.
    if kind == "metric" and isinstance(declaration, dict) and not string_field(declaration, "type"):
        status = "unknown"
        reasons = ["missing_metric_type"]
    reasons.extend(extra_reasons)
    if extra_reasons:
        status = "unknown"
    decl = declaration if isinstance(declaration, dict) else {}
    return {"id": identifier, "kind": kind, "name": name,
            "eligibility": status, "reasons": sorted(set(reasons)),
            "metric_type": string_field(decl, "type"),
            "aggregate": aggregate if aggregate is not None else string_field(decl, "agg"),
            "declared_data_type": decl.get("data_type", decl.get("dtype")),
            "declared_dependencies": {key: decl.get(key) for key in
                                      ("measure", "type_params", "numerator", "denominator",
                                       "input_metric", "input_metrics")
                                      if key in decl},
            "source": source,
            "unresolved_semantics": ["grain", "time", "null_policy", "join_cardinality", "snapshot"],
            "compiled_provenance": None}


def yaml_inventory(objects: dict, roots: list[str]) -> tuple[list[dict], list[dict], dict]:
    metrics, measures = [], []
    census = Counter()
    files = []
    outside = []
    for path, (oid, raw) in sorted(objects.items()):
        if path.startswith("dbt_project.y"):
            continue
        if not any(root == "." or path.startswith(root.rstrip("/") + "/") for root in roots):
            outside.append(path)
            continue
        files.append(path)
        try:
            documents = list(yaml.compose_all(raw.decode("utf-8"), Loader=yaml.SafeLoader))
        except (UnicodeError, yaml.YAMLError):
            # One placeholder represents an unresolved file; its true arity is unknown.
            source = {"path": path, "sha256": sha(raw), "git_blob": oid,
                      "line": None, "yaml_path": None}
            metrics.append(record("unresolved", f"yaml:unresolved:{path}:unresolved", None, None, source,
                                  extra_reasons=["unresolved_source_yaml"]))
            census["unresolved_files_unknown_arity"] += 1
            continue
        for document_index, doc in enumerate(documents):
            if not isinstance(doc, MappingNode):
                census["non_mapping_documents"] += 1
                source = {"path": path, "sha256": sha(raw), "git_blob": oid,
                          "line": doc.start_mark.line + 1 if doc else None,
                          "yaml_path": f"doc[{document_index}]"}
                metrics.append(record("unresolved", f"yaml:unresolved:{path}:doc[{document_index}]",
                                      None, None, source, extra_reasons=["unresolved_document_shape"]))
                continue

            def definitions(owner: MappingNode, prefix: str):
                for kind in ("metrics", "measures"):
                    for container_index, node in enumerate(key_nodes(owner, kind)):
                        target = metrics if kind == "metrics" else measures
                        entries = node.value if isinstance(node, SequenceNode) else [node]
                        if not isinstance(node, SequenceNode):
                            census["unresolved_containers_unknown_arity"] += 1
                        for ordinal, entry in enumerate(entries):
                            mark = f"{prefix}.{kind}[{container_index}][{ordinal}]"
                            try:
                                decl = node_value(entry)
                            except (ValueError, yaml.YAMLError, RecursionError):
                                decl = None
                            name = string_field(decl, "name")
                            source = {"path": path, "sha256": sha(raw), "git_blob": oid,
                                      "line": entry.start_mark.line + 1, "yaml_path": mark}
                            issues = [] if isinstance(node, SequenceNode) else ["unresolved_container_shape"]
                            if not isinstance(decl, dict):
                                issues.append("malformed_declaration")
                            if name is None or jinja(name):
                                issues.append("unresolved_name")
                            unit_kind = "metric" if kind == "metrics" else "measure"
                            target.append(record(unit_kind, f"yaml:{unit_kind}:{path}:{mark}",
                                                 name, decl, source,
                                                 extra_reasons=issues))

            definitions(doc, f"doc[{document_index}]")
            for collection in ("models", "semantic_models"):
                for group_index, group in enumerate(key_nodes(doc, collection)):
                    if not isinstance(group, SequenceNode):
                        census[f"unresolved_{collection}_container"] += 1
                        # Unknown nested declaration count: retain a candidate placeholder.
                        source = {"path": path, "sha256": sha(raw), "git_blob": oid,
                                  "line": group.start_mark.line + 1,
                                  "yaml_path": f"doc[{document_index}].{collection}[{group_index}]"}
                        metrics.append(record("unresolved", f"yaml:unresolved:{path}:{source['yaml_path']}",
                                              None, None, source, extra_reasons=["unresolved_container_shape"]))
                        continue
                    for owner_index, owner in enumerate(group.value):
                        if not isinstance(owner, MappingNode):
                            census["malformed_owners"] += 1
                            source = {"path": path, "sha256": sha(raw), "git_blob": oid,
                                      "line": owner.start_mark.line + 1,
                                      "yaml_path": f"doc[{document_index}].{collection}[{group_index}][{owner_index}]"}
                            metrics.append(record("unresolved", f"yaml:unresolved:{path}:{source['yaml_path']}",
                                                  None, None, source, extra_reasons=["malformed_owner_unknown_arity"]))
                            continue
                        prefix = f"doc[{document_index}].{collection}[{group_index}][{owner_index}]"
                        definitions(owner, prefix)
                        for column_key in ("columns", "dimensions", "entities"):
                            for section in key_nodes(owner, column_key):
                                if not isinstance(section, SequenceNode):
                                    census[f"unresolved_{column_key}_census"] += 1
                                    continue
                                for column in section.value:
                                    if column_key != "columns":
                                        census[column_key] += 1
                                    elif isinstance(column, MappingNode):
                                        if key_nodes(column, "entity"):
                                            census["entity_columns"] += 1
                                        elif key_nodes(column, "dimension"):
                                            census["dimension_columns"] += 1
                                        else:
                                            census["ordinary_columns"] += 1
                                    else:
                                        census["malformed_columns"] += 1
    return metrics, measures, {"yaml_files_scanned": files,
                               "yaml_files_outside_model_paths": outside,
                               "non_candidate_census": dict(sorted(census.items()))}


def manifest_inventory(raw: bytes, blobs: dict) -> tuple[list[dict], list[dict], dict, str | None]:
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("metadata"), dict):
        raise ValueError("Manifest requires metadata and resource maps")
    metrics, measures = [], []
    census = Counter()
    for kind, container in (("metric", manifest.get("metrics")),
                            ("semantic_model", manifest.get("semantic_models"))):
        if not isinstance(container, dict):
            raise ValueError(f"Manifest {kind} container missing or unsupported")
        for resource_id, entry in sorted(container.items()):
            if not isinstance(entry, dict):
                entry = {}
            source_path = entry.get("original_file_path")
            tracked = blobs.get(source_path) if isinstance(source_path, str) else None
            source = {"path": source_path, "sha256": sha(tracked[1]) if tracked else None,
                      "git_blob": tracked[0] if tracked else None, "line": None,
                      "manifest_resource_id": resource_id, "source_mapping_verified": False}
            if kind == "metric":
                name = string_field(entry, "name")
                issues = []
                agg = None
                if not name:
                    issues.append("unresolved_name")
                params = entry.get("type_params")
                ref = params.get("measure") if isinstance(params, dict) else None
                if isinstance(ref, dict):
                    ref = ref.get("name")
                metrics.append(record("metric", f"manifest:metric:{resource_id}", name, entry, source,
                                      aggregate=agg, extra_reasons=issues))
                metrics[-1]["supporting_measure_name"] = ref if isinstance(ref, str) else None
            else:
                for excluded in ("entities", "dimensions"):
                    section = entry.get(excluded)
                    if isinstance(section, list):
                        census[excluded] += len(section)
                    elif section is not None:
                        census[f"unresolved_{excluded}"] += 1
                section = entry.get("measures")
                if not isinstance(section, list):
                    if section is not None:
                        census["unresolved_measure_container"] += 1
                        measures.append(record("measure", f"manifest:measure:{resource_id}:unresolved",
                                               None, None, source, extra_reasons=["unresolved_container_shape"]))
                    continue
                for index, measure in enumerate(section):
                    name = string_field(measure, "name")
                    issues = [] if isinstance(measure, dict) and name else ["malformed_declaration"]
                    item = record("measure", f"manifest:measure:{resource_id}:measures[{index}]", name,
                                  measure, {**source, "manifest_measure_index": index},
                                  extra_reasons=issues)
                    measures.append(item)
    by_name = defaultdict(list)
    for measure in measures:
        if measure["name"]:
            by_name[measure["name"]].append(measure)
    for metric in metrics:
        ref = metric.pop("supporting_measure_name")
        declared_depends = manifest["metrics"].get(metric["source"]["manifest_resource_id"], {}).get("depends_on", {})
        nodes = declared_depends.get("nodes") if isinstance(declared_depends, dict) else None
        nodes = nodes if isinstance(nodes, list) else []
        name_candidates = by_name.get(ref, []) if ref else []
        # A global name match is only a hint. The exact semantic-model node
        # must occur in this metric's declared dependency list.
        candidates = [m for m in name_candidates if
                      m["source"]["manifest_resource_id"] in nodes]
        metric["measure_name_only_candidates"] = [m["id"] for m in name_candidates]
        metric["supporting_measure_refs"] = [m["id"] for m in candidates]
        metric["depends_on_nodes"] = nodes
        if metric["metric_type"] == "simple" and len(candidates) == 1:
            # Eligibility from the linked declaration; do not count the measure
            # as a second scalar metric output.
            linked = candidates[0]
            metric["aggregate"] = linked["aggregate"]
            if linked["eligibility"] == "eligible" and metric["eligibility"] == "unknown" \
                    and metric["reasons"] == ["aggregation_missing"]:
                metric["eligibility"] = "eligible"
                metric["reasons"] = ["numeric_aggregate_declaration", "unique_manifest_measure_reference"]
            elif linked["eligibility"] != "eligible":
                metric["reasons"] = sorted(set(metric["reasons"] + ["measure_numeric_type_unverified"]))
        elif metric["metric_type"] == "simple":
            metric["eligibility"] = "unknown"
            metric["reasons"] = sorted(set(metric["reasons"] +
                                           ["ambiguous_measure_binding" if len(candidates) > 1 else
                                            "name_only_measure_candidate" if name_candidates else
                                            "unresolved_measure_binding"]))
    return metrics, measures, {"manifest_resource_counts": {
        "metrics": len(manifest["metrics"]), "semantic_models": len(manifest["semantic_models"])},
        "non_candidate_census": dict(sorted(census.items()))}, manifest["metadata"].get("project_name")


def build(repo: Path, expected: str, source: str, manifest_path: Path | None) -> dict:
    commit, blobs = pinned_blobs(repo, expected)
    project_path = next((p for p in ("dbt_project.yml", "dbt_project.yaml") if p in blobs), None)
    if project_path is None:
        raise ValueError("Pinned tree lacks dbt_project.yml/yaml")
    project = yaml.safe_load(blobs[project_path][1])
    if not isinstance(project, dict) or not isinstance(project.get("name"), str):
        raise ValueError("Pinned dbt_project has no project name")
    model_paths = project.get("model-paths", ["models"])
    if not isinstance(model_paths, list) or not model_paths or any(
            not isinstance(x, str) or x.startswith("/") or ".." in x.split("/") or "{{" in x
            for x in model_paths):
        raise ValueError("Unresolvable model-paths")
    root_names = [Path(x).as_posix() for x in model_paths]
    provenance = {"project": project["name"], "repo_commit": commit, "mode": source,
                  "project_yaml": {"path": project_path, "sha256": sha(blobs[project_path][1])},
                  "parser": {"name": "PyYAML", "version": yaml.__version__}}
    if source == "yaml":
        if manifest_path is not None:
            raise ValueError("--manifest only valid with --source manifest")
        metrics, measures, meta = yaml_inventory(blobs, root_names)
        provenance["inputs"] = {p: sha(blobs[p][1]) for p in meta["yaml_files_scanned"]}
    else:
        if manifest_path is None:
            raise ValueError("--source manifest requires --manifest")
        manifest_file = manifest_path.resolve()
        target = (repo / "target").resolve()
        if target not in manifest_file.parents:
            raise ValueError("Manifest path must resolve inside the selected repository's target directory")
        if not manifest_file.is_file():
            raise ValueError("Selected repository target has no supplied manifest file")
        raw = manifest_file.read_bytes()
        metrics, measures, meta, manifest_project = manifest_inventory(raw, blobs)
        if manifest_project != project["name"]:
            raise ValueError("Manifest project name does not match the pinned dbt_project")
        provenance["manifest"] = {"path": manifest_file.relative_to(repo).as_posix(),
                                  "sha256": sha(raw), "project_name": manifest_project,
                                  "build_commit_verified": False}
    metrics.sort(key=lambda x: x["id"])
    measures.sort(key=lambda x: x["id"])
    candidates = sorted(metrics + measures, key=lambda x: x["id"])
    ids = [m["id"] for m in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate resource-qualified candidate ID")
    def enumerate_pairs(items: list[dict]) -> list[dict]:
        return [{"left_id": left["id"], "right_id": right["id"],
              "eligibility": "eligible" if left["eligibility"] == right["eligibility"] == "eligible"
              else "unknown", "left_status": left["eligibility"], "right_status": right["eligibility"]}
             for left, right in itertools.combinations(items, 2)]
    primary_pairs = enumerate_pairs(metrics)
    all_pairs = enumerate_pairs(candidates)
    counts = {"candidate_scalar_definitions": len(candidates),
        "declared_metrics": sum(m["kind"] == "metric" for m in metrics),
        "unresolved_scope_placeholders": sum(m["kind"] == "unresolved" for m in candidates),
        "declared_measures": len(measures), "eligible": sum(
        m["eligibility"] == "eligible" for m in candidates), "unknown": sum(
        m["eligibility"] == "unknown" for m in candidates),
        "eligibility_by_kind": {kind: dict(sorted(Counter(m["eligibility"] for m in candidates
                                                            if m["kind"] == kind).items()))
                                for kind in ("metric", "measure", "unresolved")},
        "primary_metric_pairs": len(primary_pairs), "all_declared_scalar_pairs": len(all_pairs),
        "primary_pair_status": dict(sorted(Counter(p["eligibility"] for p in primary_pairs).items())),
        "all_pair_status": dict(sorted(Counter(p["eligibility"] for p in all_pairs).items())),
        "unknown_reasons": dict(sorted(Counter(reason for m in candidates if m["eligibility"] == "unknown"
                                                for reason in m["reasons"]).items()))}
    return {"schema_version": 1, "scope": "development_only_declared_dbt_metric_output_inventory",
            "provenance": provenance, "coverage": counts, "source_census": meta,
            "candidates": candidates,
            "frames": {"primary_exposed_metrics": {"candidate_ids": [m["id"] for m in metrics], "pairs": primary_pairs},
                       "secondary_all_declared_scalars": {"candidate_ids": ids, "pairs": all_pairs}},
            "limits": ["Pair completeness applies only to emitted IDs (including unresolved placeholders) in each frame; invalid YAML/container shapes can hide an unknown number of declarations.",
                       "Declared metrics and measures are distinct scalar definitions with resource-qualified IDs. A metric's measure reference is a dependency, not an equivalence label; same names do not collapse units.",
                       "Dimensions, entity keys and ordinary SQL projections are not declared metric outputs.",
                       "A numeric aggregation is declaration-level type evidence, not verified runtime value or equivalence.",
                       "Derived, ratio, cumulative and unsupported numeric results remain unknown without resolved dependency types.",
                       "YAML source and manifest resources are different inventories; separate revisions/build transformations can change counts.",
                       "A manifest hash and a pinned checkout do not establish that the manifest was built from that commit; compiled provenance and source mapping remain unverified.",
                       "No labels, row outcomes, candidate correctness or method superiority are measured."]}


def negative_control() -> dict:
    fixture = HERE / "generic_metric_eligibility_negative.yml"
    raw = fixture.read_bytes()
    node = yaml.compose(raw.decode(), Loader=yaml.SafeLoader)
    assert isinstance(node, MappingNode)
    columns = key_nodes(key_nodes(node, "models")[0].value[0], "columns")[0]
    assert isinstance(columns, SequenceNode)
    excluded = [node_value(c) for c in columns.value]
    assert any(c.get("name") == "entity_key" and c.get("entity") for c in excluded)
    assert any(c.get("name") == "value" and not c.get("entity") for c in excluded)
    entries = key_nodes(key_nodes(node, "models")[0].value[0], "metrics")[0]
    assert isinstance(entries, SequenceNode)
    statuses = {node_value(n)["name"]: eligibility(node_value(n))[0] for n in entries.value}
    assert statuses == {"declared_total": "eligible", "templated_value": "unknown"}
    metrics, measures, _ = yaml_inventory({"models/fixture.yml": ("synthetic", raw)}, ["models"])
    ids = sorted([x["id"] for x in metrics + measures])
    assert len(metrics) == 2 and len(measures) == 1 and len(ids) == len(set(ids))
    assert metrics[0]["name"] == measures[0]["name"] and metrics[0]["id"] != measures[0]["id"]
    sem_id = "semantic_model.synthetic.source"
    metric_id = "metric.synthetic.output"
    base = {"metadata": {"project_name": "synthetic"},
            "metrics": {metric_id: {"name": "declared_total", "type": "simple",
                        "type_params": {"measure": {"name": "declared_total"}},
                        "depends_on": {"nodes": []}}},
            "semantic_models": {sem_id: {"name": "source", "original_file_path": "models/fixture.yml",
                                "measures": [{"name": "declared_total", "agg": "sum"}]}}}
    blobs = {"models/fixture.yml": ("synthetic", raw)}
    unbound, _, _, _ = manifest_inventory(json.dumps(base).encode(), blobs)
    assert len(unbound) == 1 and unbound[0]["eligibility"] == "unknown"
    assert unbound[0]["supporting_measure_refs"] == []
    assert len(unbound[0]["measure_name_only_candidates"]) == 1
    base["metrics"][metric_id]["depends_on"]["nodes"] = [sem_id]
    bound, _, _, _ = manifest_inventory(json.dumps(base).encode(), blobs)
    assert len(bound) == 1 and bound[0]["eligibility"] == "eligible"
    assert len(bound[0]["supporting_measure_refs"]) == 1
    untyped = record("metric", "yaml:metric:synthetic:untyped", "untyped_total",
                     {"name": "untyped_total", "agg": "sum"}, {"path": "synthetic"})
    assert untyped["eligibility"] == "unknown" and "missing_metric_type" in untyped["reasons"]
    malformed_raw = (b"models:\n  - name: fixture\n    metrics: malformed_container\n"
                     b"    measures:\n      - name: minimum\n        agg: min\n")
    malformed_metrics, malformed_measures, malformed_meta = yaml_inventory(
        {"models/malformed.yml": ("synthetic", malformed_raw)}, ["models"])
    assert len(malformed_metrics) == len(malformed_measures) == 1
    assert malformed_metrics[0]["eligibility"] == malformed_measures[0]["eligibility"] == "unknown"
    assert malformed_meta["non_candidate_census"]["unresolved_containers_unknown_arity"] == 1
    return {"path": fixture.name, "sha256": sha(raw),
            "excluded_column_names": [c.get("name") for c in excluded],
            "declared_metric_statuses": statuses, "resource_qualified_candidate_ids": ids,
            "name_only_manifest_binding": "unknown", "exact_dependency_manifest_binding": "eligible",
            "missing_metric_type": "unknown", "malformed_container_arity": "unknown",
            "interpretation": "Numeric entity_key and arbitrary value columns are excluded; templated, untyped and malformed metric declarations remain unknown; same-named metric and measure remain distinct; only an exact dependency permits measure-derived eligibility."}


def markdown(report: dict) -> str:
    p, c, s = report["provenance"], report["coverage"], report["source_census"]
    lines = ["# Generic dbt metric-output eligibility (development only)", "",
             f"Source: `{p['mode']}` for `{p['project']}@{p['repo_commit']}`; PyYAML {p['parser']['version']}.",
             "Manifest build commit is unverified." if p["mode"] == "manifest" else "Reads pinned Git YAML blobs, not checkout edits.",
             "", "| Category | Count |", "| --- | ---: |",
             f"| Declared scalar candidates (metrics + measures) | {c['candidate_scalar_definitions']} |",
             f"| Metric declarations | {c['declared_metrics']} |",
             f"| Measure declarations | {c['declared_measures']} |",
             f"| Unresolved-scope placeholders | {c['unresolved_scope_placeholders']} |",
             f"| Eligible by declared numeric aggregation | {c['eligible']} |",
             f"| Unknown numeric status | {c['unknown']} |",
             f"| Primary exposed-metric pairs | {c['primary_metric_pairs']} |",
             f"| Secondary all-declared-scalar pairs | {c['all_declared_scalar_pairs']} |", ""]
    if "manifest_resource_counts" in s:
        lines.append(f"Manifest resources: {s['manifest_resource_counts']['metrics']} metrics, {s['manifest_resource_counts']['semantic_models']} semantic models. Measures are listed within those models.")
        lines.append(f"Manifest input: `{p['manifest']['path']}` (SHA256 `{p['manifest']['sha256']}`); build commit unattested, source mapping unverified.")
    else:
        lines.append(f"Pinned model-path YAML files scanned: {len(s['yaml_files_scanned'])}.")
    lines.append(f"Pinned project file: `{p['project_yaml']['path']}` (SHA256 `{p['project_yaml']['sha256']}`).")
    lines.extend(["", "| Non-candidate / unknown category | Count |", "| --- | ---: |"])
    lines.extend(f"| {key} | {value} |" for key, value in s["non_candidate_census"].items())
    lines.extend(["", "| Unknown reason | Count |", "| --- | ---: |"])
    lines.extend(f"| {key} | {value} |" for key, value in c["unknown_reasons"].items())
    lines.extend(["", "## Reconciliation and limits", "",
                  "Primary pairs use exposed metric declarations. Secondary pairs also include each declared measure under its own resource-qualified ID. A metric-to-measure reference is a dependency, not a duplicate ID or an equivalence label. Source YAML and built manifests can represent different revisions and transformations; compare paths, revisions and build provenance before interpreting count differences.",
                  ""])
    lines.extend(f"- {line}" for line in report["limits"])
    control = report["negative_control"]
    lines.extend(["", f"Control `{control['path']}` SHA256 `{control['sha256']}`: " + control["interpretation"],
                  "", "## Reproduce", "",
                  "```bash",
                  report["reproduce_command"],
                  "```", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--source", choices=("yaml", "manifest"), required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_PREFIX)
    parser.add_argument("--check", action="store_true", help="Byte compare generated reports; never write")
    args = parser.parse_args()
    result = build(args.repo.resolve(), args.expected_commit, args.source, args.manifest)
    result["negative_control"] = negative_control()
    def display(path: Path) -> str:
        absolute = path.resolve()
        try:
            return absolute.relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return absolute.as_posix()
    invocation = ["python3", "-B", display(Path(__file__)), "--repo", display(args.repo),
                  "--expected-commit", args.expected_commit, "--source", args.source]
    if args.manifest is not None:
        invocation += ["--manifest", display(args.manifest)]
    invocation += ["--output-prefix", display(args.output_prefix), "--check"]
    result["reproduce_command"] = " ".join(shlex.quote(x) for x in invocation)
    rendered = {".json": json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                ".md": markdown(result)}
    for suffix, content in rendered.items():
        path = Path(str(args.output_prefix) + suffix)
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode():
                raise ValueError(f"Missing or stale report: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"{args.source}: {result['coverage']['candidate_scalar_definitions']} candidates, "
          f"{result['coverage']['primary_metric_pairs']} primary / "
          f"{result['coverage']['all_declared_scalar_pairs']} secondary pairs; "
          f"{'checked' if args.check else 'written'}")


if __name__ == "__main__":
    main()
