#!/usr/bin/env python3
"""Conservative, pinned-source links for the portable jaffle metric packet.

This is a development addendum, not a dbt compiler or an evaluation adapter.
Only Git objects at the packet-pinned commit and the existing packet are read.
No portable runner, frozen decision, or held-out source is imported or inspected.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

import yaml
from yaml.nodes import MappingNode, SequenceNode


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REF = re.compile(r"\{\{\s*ref\(\s*(['\"])([A-Za-z_][A-Za-z_0-9]*)\1\s*\)\s*\}\}", re.S)
SOURCE = re.compile(
    r"\{\{\s*source\(\s*(['\"])([A-Za-z_][A-Za-z_0-9]*)\1\s*,\s*"
    r"(['\"])([A-Za-z_][A-Za-z_0-9]*)\3\s*\)\s*\}\}", re.S
)
JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
JINJA_OPEN = re.compile(r"\{[{%#]")


def git(project: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(project), *args], stderr=subprocess.PIPE)


def at_commit(project: Path, commit: str, path: str) -> bytes:
    return git(project, "show", f"{commit}:{path}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mapping_value(node: MappingNode, key: str):
    if not isinstance(node, MappingNode):
        raise ValueError(f"Expected YAML mapping while looking for {key!r}")
    for k, v in node.value:
        if k.value == key:
            return v
    raise ValueError(f"Missing YAML key {key!r}")


def metric_definitions(path: str, data: bytes) -> tuple[list[dict], list[dict]]:
    documents = list(yaml.safe_load_all(data))
    nodes = list(yaml.compose_all(data))
    if len(documents) != len(nodes):
        raise ValueError(f"YAML document/node count differs: {path}")
    metrics = []
    models = []
    for doc_idx, (doc, node) in enumerate(zip(documents, nodes)):
        if not doc:
            continue
        if not isinstance(doc, dict):
            raise ValueError(f"YAML root is not a mapping: {path} doc {doc_idx}")
        for model_idx, model in enumerate(doc.get("models", [])):
            name = model["name"]
            models.append({"name": name, "yaml_path": path})
            model_node = mapping_value(node, "models").value[model_idx]
            if not isinstance(model_node, MappingNode):
                raise ValueError(f"Model YAML is not a mapping: {path}")
            model_metrics = model.get("metrics", [])
            if model_metrics:
                metric_nodes = mapping_value(model_node, "metrics")
                if not isinstance(metric_nodes, SequenceNode):
                    raise ValueError(f"Model metrics are not a sequence: {path}")
                for i, (metric, metric_node) in enumerate(zip(model_metrics, metric_nodes.value)):
                    key = f"models[{model_idx}].metrics[{i}]"
                    metrics.append(metric_record(path, doc_idx, key, metric, metric_node, name))
                if len(model_metrics) != len(metric_nodes.value):
                    raise ValueError(f"Model metric count differs: {path}")
        if doc.get("models") and len(doc["models"]) != len(mapping_value(node, "models").value):
            raise ValueError(f"Model count differs: {path}")
        root_metrics = doc.get("metrics", [])
        if root_metrics:
            metric_nodes = mapping_value(node, "metrics")
            if not isinstance(metric_nodes, SequenceNode):
                raise ValueError(f"Root metrics are not a sequence: {path}")
            for i, (metric, metric_node) in enumerate(zip(root_metrics, metric_nodes.value)):
                metrics.append(metric_record(path, doc_idx, f"metrics[{i}]", metric, metric_node, None))
            if len(root_metrics) != len(metric_nodes.value):
                raise ValueError(f"Root metric count differs: {path}")
    lines = data.decode("utf-8").splitlines()
    for item in metrics:
        loc = item["yaml_location"]
        while loc["end_line"] >= loc["start_line"] and (
            not lines[loc["end_line"] - 1].strip()
            or lines[loc["end_line"] - 1].lstrip().startswith("#")
        ):
            loc["end_line"] -= 1
    return metrics, models


def metric_record(path: str, doc: int, key: str, metric: dict, node, model_name: str | None) -> dict:
    if not isinstance(metric, dict) or not isinstance(node, MappingNode):
        raise ValueError(f"Metric YAML is not a mapping: {path} {key}")
    return {
        "id": f"{path}#doc[{doc}].{key}",
        "name": metric["name"],
        "yaml_path": path,
        "yaml_location": {
            "path": path,
            "start_line": node.start_mark.line + 1,
            "end_line": node.end_mark.line,
            "document": doc,
            "yaml_path": key,
        },
        "model_name": model_name,
        "metric": metric,
    }


def dependencies(metric: dict) -> list[dict]:
    kind = metric.get("type")
    if kind == "ratio":
        return [{"role": role, "name": metric[role]} for role in ("numerator", "denominator")]
    if kind == "derived":
        return [{"role": "input_metric", **item} for item in metric["input_metrics"]]
    if kind == "cumulative":
        return [{"role": "input_metric", "name": metric["input_metric"]}]
    return []


def packet_dependencies(metric: dict) -> dict:
    return {key: metric[key] for key in ("numerator", "denominator", "input_metrics", "input_metric") if key in metric}


def scan_sql(path: str, data: bytes, model_paths_by_name: dict[str, list[str]]) -> dict:
    source = data.decode("utf-8")
    edges, sources, unsupported = [], [], []
    covered = [False] * len(source)
    for match in JINJA.finditer(source):
        for i in range(match.start(), match.end()):
            covered[i] = True
        raw = match.group()
        line = source.count("\n", 0, match.start()) + 1
        ref = REF.fullmatch(raw)
        src = SOURCE.fullmatch(raw)
        if ref:
            name = ref.group(2)
            targets = model_paths_by_name.get(name, [])
            edges.append({"line": line, "ref": name, "sql_path": targets[0] if len(targets) == 1 else None,
                          "status": "unique_model_path" if len(targets) == 1 else "unresolved_or_ambiguous"})
        elif src:
            sources.append({"line": line, "source_name": src.group(2), "table_name": src.group(4),
                            "status": "declaration_only_physical_relation_unresolved"})
        else:
            unsupported.append({"line": line, "snippet": raw.strip(), "reason": "unsupported_jinja"})
    for match in JINJA_OPEN.finditer(source):
        if not covered[match.start()]:
            unsupported.append({"line": source.count("\n", 0, match.start()) + 1,
                                "snippet": source[match.start():match.start() + 80].splitlines()[0],
                                "reason": "unclosed_or_unsupported_jinja"})
    return {
        "path": path,
        "sha256": digest(data),
        "line_span": [1, len(source.splitlines())],
        "kind": "pinned_uncompiled_source_sql",
        "literal_ref_edges": edges,
        "source_calls": sources,
        "unsupported_jinja": unsupported,
    }


def analyze(project: Path, packet_path: Path) -> dict:
    packet_bytes = packet_path.read_bytes()
    packet = json.loads(packet_bytes)
    if packet.get("schema_version") != 1 or len(packet.get("cards", [])) != 23:
        raise ValueError("Expected the existing schema-1 packet with exactly 23 metric cards")
    commit = git(project, "rev-parse", "HEAD").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or commit != packet["provenance"]["commit"]:
        raise ValueError(f"Pinned commit mismatch: project HEAD {commit}, packet {packet['provenance']['commit']}")
    project_bytes = at_commit(project, commit, "dbt_project.yml")
    project_config = yaml.safe_load(project_bytes)
    if project_config["name"] != packet["provenance"]["project"]:
        raise ValueError("Packet/project dbt project names differ")
    model_roots = project_config.get("model-paths", ["models"])
    if not isinstance(model_roots, list) or not all(isinstance(x, str) for x in model_roots):
        raise ValueError("Unsupported model-paths configuration")
    if model_roots != packet["provenance"]["model_paths"]:
        raise ValueError("Packet/model-paths differ")
    tree_paths = git(project, "ls-tree", "-r", "--name-only", commit, "--", *model_roots).decode().splitlines()
    yaml_paths = sorted(p for p in tree_paths if p.endswith((".yml", ".yaml")))
    sql_paths = sorted(p for p in tree_paths if p.endswith(".sql"))
    expected_hashes = packet["provenance"]["input_sha256"]
    if set(expected_hashes) != {"dbt_project.yml", *yaml_paths}:
        raise ValueError("Packet YAML inventory does not equal pinned Git model-path inventory")
    inputs = {"dbt_project.yml": project_bytes}
    inputs.update({p: at_commit(project, commit, p) for p in yaml_paths})
    for path, data in inputs.items():
        if digest(data) != expected_hashes[path]:
            raise ValueError(f"Pinned input hash differs from packet: {path}")

    definitions, models = [], []
    for path in yaml_paths:
        found_metrics, found_models = metric_definitions(path, inputs[path])
        definitions.extend(found_metrics)
        models.extend(found_models)
    defs_by_id = {d["id"]: d for d in definitions}
    packet_by_id = {c["id"]: c for c in packet["cards"]}
    if len(defs_by_id) != len(definitions) or len(packet_by_id) != len(packet["cards"]):
        raise ValueError("Duplicate metric IDs")
    if set(defs_by_id) != set(packet_by_id):
        raise ValueError("Packet metric IDs do not equal pinned YAML inventory")
    for id_, definition in defs_by_id.items():
        card, m = packet_by_id[id_], definition["metric"]
        checks = {
            "metric_name": m["name"],
            "metric_type": m.get("type"),
            "aggregation": m.get("agg"),
            "declared_expression": m.get("expr"),
            "declared_filter": m.get("filter"),
            "declared_dependencies": packet_dependencies(m),
            "source_ref": definition["model_name"],
            "source_location": definition["yaml_location"],
        }
        for key, expected in checks.items():
            if card.get(key) != expected:
                raise ValueError(f"Packet/YAML mismatch for {id_} {key}: {card.get(key)!r} != {expected!r}")

    model_defs = defaultdict(list)
    for model in models:
        model_defs[model["name"]].append(model)
    sql_by_name = defaultdict(list)
    for path in sql_paths:
        sql_by_name[PurePosixPath(path).stem].append(path)
    names = defaultdict(list)
    for definition in definitions:
        names[definition["name"]].append(definition)

    def direct_path(definition: dict) -> str | None:
        name = definition["model_name"]
        if not name or len(model_defs[name]) != 1:
            return None
        candidates = sql_by_name[name]
        if len(candidates) != 1:
            return None
        path = candidates[0]
        if PurePosixPath(path).parent != PurePosixPath(definition["yaml_path"]).parent:
            return None
        return path

    def source_paths(definition: dict, visiting: frozenset[str] = frozenset()) -> list[str]:
        if definition["id"] in visiting:
            return []
        if definition["metric"].get("type") == "simple":
            path = direct_path(definition)
            return [path] if path else []
        result = []
        for dep in dependencies(definition["metric"]):
            targets = names[dep["name"]]
            if len(targets) != 1:
                return []
            child = source_paths(targets[0], visiting | {definition["id"]})
            if not child:
                return []
            result.extend(child)
        return list(dict.fromkeys(result))

    rows = []
    for card in packet["cards"]:
        d = defs_by_id[card["id"]]
        m = d["metric"]
        paths = source_paths(d)
        dep_links = []
        for dep in dependencies(m):
            candidates = names[dep["name"]]
            target = candidates[0] if len(candidates) == 1 else None
            dep_links.append({**dep, "target_card_id": target["id"] if target else None,
                              "source_sql_paths": source_paths(target) if target else [],
                              "resolution": "unique_yaml_metric" if target else "unresolved_or_ambiguous"})
        filter_value = m.get("filter")
        if filter_value and JINJA_OPEN.search(filter_value):
            filter_status = "rejected_unsupported_jinja"
        elif filter_value:
            filter_status = "declared_only_uncompiled"
        else:
            filter_status = "none_declared"
        expr = m.get("expr")
        expr_has_jinja = isinstance(expr, str) and bool(JINJA_OPEN.search(expr))
        if m.get("type") != "simple":
            coverage = "dependency_sources_only" if paths else "unlinked"
            expr_status = "rejected_unsupported_jinja" if expr_has_jinja else "non_simple_shape_not_inferred"
            blockers = ["Dependency links do not establish the metric SQL shape or result semantics."]
            if m.get("type") == "ratio":
                blockers.append("No division, zero-denominator, or NULL behavior inferred from numerator/denominator names.")
            elif m.get("type") == "cumulative":
                blockers.append("No accumulation window, time period, or ordering inferred from input_metric.")
            if any("offset_window" in dep for dep in dep_links):
                blockers.append("offset_window is YAML only; period alignment is unresolved.")
        elif not paths:
            coverage = "unlinked"
            expr_status = "rejected_unsupported_jinja" if expr_has_jinja else (
                "explicit_yaml_only" if expr is not None else "omitted_no_shape_inference"
            )
            blockers = ["No unique adjacent, Git-tracked SQL model path for YAML model name."]
        elif filter_status == "rejected_unsupported_jinja":
            coverage = "direct_source_sql_filter_jinja_blocked"
            expr_status = "rejected_unsupported_jinja" if expr_has_jinja else (
                "explicit_yaml_only" if expr is not None else "omitted_no_shape_inference"
            )
            blockers = ["Unsupported YAML Jinja filter; it is not evaluated or replaced with a column."]
        elif expr_has_jinja:
            coverage = "direct_source_sql_expr_jinja_blocked"
            expr_status = "rejected_unsupported_jinja"
            blockers = ["Unsupported YAML Jinja expression; no rendered expression is inferred."]
        elif expr is None:
            coverage = "direct_source_sql_implicit_expr"
            expr_status = "omitted_no_shape_inference"
            blockers = ["YAML omits expr; aggregation input and metric SQL shape are not inferred."]
        else:
            coverage = "direct_source_sql_explicit_expr"
            expr_status = "explicit_yaml_only"
            blockers = ["Declared YAML expr is not compiled or verified against model output fields."]
        if not paths and m.get("type") != "simple":
            blockers.append("At least one dependency is missing, ambiguous, cyclic, or lacks source SQL.")
        if filter_status == "declared_only_uncompiled":
            blockers.append("YAML filter is uncompiled and unresolved.")
        if expr_has_jinja and "Unsupported YAML Jinja expression; no rendered expression is inferred." not in blockers:
            blockers.append("Unsupported YAML Jinja expression; no rendered expression is inferred.")
        row = {
            "id": card["id"],
            "metric_name": card["metric_name"],
            "metric_type": m.get("type"),
            "coverage": coverage,
            "yaml_evidence": {**d["yaml_location"], "sha256": expected_hashes[d["yaml_path"]]},
            "anchor_rule": "nested_yaml_model_name_unique_adjacent_sql" if m.get("type") == "simple"
                           else "unique_yaml_metric_dependencies_to_nested_model_sql",
            "direct_source_sql_path": direct_path(d) if m.get("type") == "simple" else None,
            "linked_source_sql_paths": paths,
            "dependency_links": dep_links,
            "declared_aggregation": m.get("agg"),
            "declared_expression": expr,
            "expression_status": expr_status,
            "declared_filter": filter_value,
            "filter_status": filter_status,
            "compiled_sql": None,
            "compiled_evidence_verified": False,
            "blockers": blockers + ["No commit-verified compiled SQL; output fields and semantic behavior are unverified."],
            "not_claimed": ["output_grain", "period", "join_cardinality", "null_policy",
                            "filter_resolution", "output_field_lineage", "metric_query_sql"],
        }
        rows.append(row)

    sql_data = {p: at_commit(project, commit, p) for p in sql_paths}
    catalog = {}
    pending = sorted({p for row in rows for p in row["linked_source_sql_paths"]})
    while pending:
        path = pending.pop(0)
        if path in catalog:
            continue
        entry = scan_sql(path, sql_data[path], sql_by_name)
        catalog[path] = entry
        pending.extend(edge["sql_path"] for edge in entry["literal_ref_edges"] if edge["sql_path"])
        pending = sorted(set(pending))
    catalog = dict(sorted(catalog.items()))
    counts = Counter(row["coverage"] for row in rows)
    manifest = project / project_config.get("target-path", "target") / "manifest.json"
    dbt_cli = shutil.which("dbt")
    dbt_module = importlib.util.find_spec("dbt") is not None
    return {
        "schema_version": 1,
        "scope": "exploratory_development_addendum_only",
        "provenance": {
            "project": project_config["name"], "commit": commit,
            "packet_path": str(packet_path.relative_to(ROOT)), "packet_sha256": digest(packet_bytes),
            "source_selection": "All blobs read by immutable commit ID; project/YAML hashes verified against packet inventory; raw SQL hashes recorded independently in this report",
            "input_sha256": expected_hashes,
            "model_paths": model_roots,
            "heldout_sources_inspected": False,
        },
        "counts": {
            "yaml_metrics": len(rows), "source_sql_direct_links": sum(r["direct_source_sql_path"] is not None for r in rows),
            "source_sql_dependency_only_links": counts["dependency_sources_only"],
            "unlinked": counts["unlinked"], "verified_compiled_sources": 0,
            "by_coverage": dict(sorted(counts.items())),
        },
        "offline_tooling": {
            "dbt_cli_available": bool(dbt_cli), "dbt_core_importable": dbt_module,
            "dbt_packages_directory_present": (project / "dbt_packages").is_dir(),
            "manifest_present": manifest.is_file(),
            "compile_attempted": False,
            "compiled_artifact_policy": "An unaccompanied target artifact cannot establish a pinned commit; none is accepted.",
            "blockers": [
                "dbt CLI and dbt-core are unavailable in the current Python environment."
                if not (dbt_cli or dbt_module) else "Offline compilation was not established by this source-only adapter.",
                "Pinned project packages are not installed locally."
                if not (project / "dbt_packages").is_dir() else "Installed package provenance is not verified.",
                "No local manifest.json exists."
                if not manifest.is_file() else "Local manifest.json has no commit attestation and is not accepted.",
            ],
        },
        "interpretation": [
            "A direct link identifies a pinned raw model SQL file via the model-path and same-directory YAML model name; it is not compiled SQL.",
            "A dependency link identifies uniquely named YAML metric inputs and their raw model SQL files; it does not assign the parent metric a source relation.",
            "Only literal single-argument ref(...) and literal source(...) calls are inventoried as graph edges; source(...) is not a physical relation resolution.",
            "Other Jinja, including Dimension(...) filters and SQL macros, is rejected as unresolved; a ref edge is not a rendered query.",
            "A declared expr remains YAML evidence. Missing expr never implies a column or aggregate expression; ratio, derived, and cumulative shape is not materialized.",
            "Descriptions, entity keys, tests, saved queries, and the packet's pairs are not proof of grain, period, JOIN cardinality, NULL behavior, or filter semantics.",
        ],
        "sql_source_catalog": catalog,
        "cards": rows,
        "generated_decisions": [],
        "review_and_freeze_required_for_any_decisions": True,
    }


def markdown(report: dict) -> str:
    c = report["counts"]
    lines = [
        "# Pinned raw-source development trace (Jaffle Shop)",
        "",
        f"Pinned commit: `{report['provenance']['commit']}`. Exploratory development addendum only.",
        "",
        "No verified compiled source is available. These are file and dependency links to pinned, raw SQL, with zero generated decisions. Any decision requires separate review and freeze.",
        "",
        "## Coverage",
        "",
        "| Coverage | Cards | Meaning |",
        "| --- | ---: | --- |",
    ]
    meanings = {
        "direct_source_sql_explicit_expr": "Adjacent model SQL; explicit YAML expression only.",
        "direct_source_sql_implicit_expr": "Adjacent model SQL; YAML expression omitted, shape rejected.",
        "direct_source_sql_filter_jinja_blocked": "Adjacent model SQL; Dimension Jinja filter unresolved.",
        "direct_source_sql_expr_jinja_blocked": "Adjacent model SQL; expression Jinja unresolved.",
        "dependency_sources_only": "Unique YAML dependencies reach SQL; parent query shape unresolved.",
        "unlinked": "No safe unique source link.",
    }
    for key, meaning in meanings.items():
        lines.append(f"| `{key}` | {c['by_coverage'].get(key, 0)} | {meaning} |")
    lines += [
        "",
        f"**Totals:** {c['yaml_metrics']} cards; {c['source_sql_direct_links']} direct source SQL links; "
        f"{c['source_sql_dependency_only_links']} dependency-only links; {c['verified_compiled_sources']} verified compiled sources.",
        "",
        "## Per-card evidence",
        "",
        "Each YAML location and SQL file is read by the immutable pinned commit ID. Project/YAML hashes match the packet inventory; SQL hashes are recorded separately in this report. A direct link names a raw SQL file, not a proven metric expression or compiled field lineage.",
        "",
        "| Metric (YAML line) | Coverage | Raw SQL path or dependency paths | Explicit blocker |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["cards"]:
        loc = row["yaml_evidence"]
        paths = ", ".join(f"`{p}`" for p in row["linked_source_sql_paths"]) or "none"
        blocker = row["blockers"][0].replace("|", "\\|")
        lines.append(f"| `{row['metric_name']}` (`{loc['path']}:{loc['start_line']}-{loc['end_line']}`) "
                     f"| `{row['coverage']}` | {paths} | {blocker} |")
    t = report["offline_tooling"]
    lines += [
        "", "## Compilation and limits", "",
        f"`dbt` CLI available: {str(t['dbt_cli_available']).lower()}; dbt-core importable: "
        f"{str(t['dbt_core_importable']).lower()}; local packages: "
        f"{str(t['dbt_packages_directory_present']).lower()}; manifest: "
        f"{str(t['manifest_present']).lower()}. Compilation was not attempted.",
        "",
    ]
    for blocker in t["blockers"]:
        lines.append(f"- {blocker}")
    lines += ["", "A literal `ref` scan supports only an uncompiled dependency graph. SQL macros and YAML `Dimension(...)` Jinja are unresolved. YAML expressions are declarations; omitted expressions do not imply a column, and non-simple dependencies do not imply arithmetic or period semantics. No output grain, period, JOIN cardinality, NULL behavior, filter resolution, output field lineage, or compiled metric SQL is claimed.",
              "", "## Exact commands", "", "From `/workspace/scratch/e767b9d6f697`:", "",
              "```sh", "git -C public_corpus/jaffle-shop rev-parse HEAD", "command -v dbt || true",
              "python -c \"import importlib.util; print(importlib.util.find_spec('dbt'))\"",
              "python metric_matching_pilot/trace_portable_development_evidence.py",
              "python metric_matching_pilot/trace_portable_development_evidence.py --check", "```", "",
              "`--check` reads pinned inputs and existing reports, compares exact bytes, and writes nothing.",
              "", "Generated decisions: **0**. Separate review and freeze are required before using any links as decisions.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "public_corpus/jaffle-shop")
    parser.add_argument("--packet", type=Path, default=HERE / "portable_jaffle_packet.json")
    parser.add_argument("--json", type=Path, default=HERE / "trace_portable_development_evidence.json")
    parser.add_argument("--md", type=Path, default=HERE / "trace_portable_development_evidence.md")
    parser.add_argument("--check", action="store_true", help="Read-only recomputation and exact comparison with reports")
    args = parser.parse_args()
    try:
        report = analyze(args.project.resolve(), args.packet.resolve())
        expected = {
            args.json: json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            args.md: markdown(report),
        }
        if args.check:
            mismatches = [str(path) for path, content in expected.items()
                          if not path.is_file() or path.read_bytes() != content.encode("utf-8")]
            if mismatches:
                print("Missing or stale reports: " + ", ".join(mismatches), file=sys.stderr)
                return 1
            print("Read-only check OK: pinned inputs and both reports match exactly.")
        else:
            for path, content in expected.items():
                path.write_text(content, encoding="utf-8")
            print(f"Wrote {len(report['cards'])} cards; direct SQL: {report['counts']['source_sql_direct_links']}; "
                  f"dependency only: {report['counts']['source_sql_dependency_only_links']}; "
                  "verified compiled: 0; decisions: 0.")
        return 0
    except (ValueError, KeyError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
        print(f"Evidence trace rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
