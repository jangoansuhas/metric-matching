#!/usr/bin/env python3
"""Development-only, source-YAML metric inventory for a pinned dbt Git tree.

This adapter recognizes top-level metrics and metrics nested directly under models
or semantic_models. It does not compile dbt, inspect SQL/rows, or resolve metric
dependencies. Every recognized definition gets a card, including unsupported ones.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


BARE_FIELD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
UNKNOWN_KEYS = ("join_cardinality", "null_policy", "missing_groups", "time_zone",
                "units", "snapshot", "grouping_set_expansion")
DEPENDENCY_KEYS = ("numerator", "denominator", "input_metric", "input_metrics", "type_params")
METRIC_CONTAINERS = ("models", "semantic_models")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def pinned_tree(repo: Path, expected_commit: str) -> tuple[str, list[tuple[str, str]]]:
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", expected_commit):
        raise ValueError("--expected-commit must be a full Git commit ID")
    if Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() != repo:
        raise ValueError("--repo must be the Git checkout root")
    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if head != expected_commit.lower():
        raise ValueError(f"Wrong repository revision: expected {expected_commit}, got {head}")
    files = []
    for entry in git(repo, "ls-tree", "-r", "-z", "--full-tree", head).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = path.decode("utf-8")
        if name.lower().endswith((".yml", ".yaml")) and kind == b"blob" and mode != b"120000":
            files.append((name, oid.decode("ascii")))
    return head, sorted(files)


def node_key(node: MappingNode, key: str):
    return next((value for label, value in node.value
                 if isinstance(label, ScalarNode) and label.value == key), None)


def entries(node: MappingNode, key: str, path: str) -> list[tuple[int, object]]:
    """Identify native definition lists, retaining their exact source nodes."""
    marked = node_key(node, key)
    if marked is not None and not isinstance(marked, SequenceNode):
        raise ValueError(f"Expected a sequence at {path}.{key}")
    if marked is None:
        return []
    return list(enumerate(marked.value))


def construct(node):
    """Safely load just a model/metric metadata node, never unit-test fixtures."""
    loader = yaml.SafeLoader("")
    try:
        return loader.construct_object(node, deep=True)
    finally:
        loader.dispose()


def model_metadata(node: MappingNode, path: str) -> dict:
    model = {}
    for key in ("name", "agg_time_dimension"):
        value = node_key(node, key)
        if value is not None:
            model[key] = construct(value)
    columns = node_key(node, "columns")
    if columns is not None:
        if not isinstance(columns, SequenceNode):
            raise ValueError(f"Expected a sequence at {path}.columns")
        model["columns"] = []
        for column in columns.value:
            if not isinstance(column, MappingNode):
                continue
            item = {}
            for key in ("name", "entity"):
                value = node_key(column, key)
                if value is not None:
                    item[key] = construct(value)
            model["columns"].append(item)
    return model


def last_content_line(node) -> int:
    return max((leaf.end_mark.line + (leaf.end_mark.column > 0)
                for leaf in content_leaves(node)),
               default=node.start_mark.line + 1)


def content_leaves(node):
    if isinstance(node, MappingNode):
        for key, value in node.value:
            yield from content_leaves(key)
            yield from content_leaves(value)
    elif isinstance(node, SequenceNode):
        for child in node.value:
            yield from content_leaves(child)
    else:
        yield node


def json_value(value):
    """Retain declared dependencies without evaluating YAML expressions or templates."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_value(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def card(metric, model, path: str, document: int, yaml_path: str, node) -> dict:
    malformed = not isinstance(metric, dict)
    metric = metric if not malformed else {}
    model = model if isinstance(model, dict) else None
    name = metric.get("name") if isinstance(metric.get("name"), str) else None
    typ = metric.get("type") if isinstance(metric.get("type"), str) else None
    expr = metric.get("expr")
    expression = str(expr) if isinstance(expr, (str, int, float)) and not isinstance(expr, bool) else None
    raw_filter = metric.get("filter")
    columns = model.get("columns", []) if model else []
    columns = columns if isinstance(columns, list) else []
    known_columns = {c["name"] for c in columns if isinstance(c, dict) and isinstance(c.get("name"), str)}
    primary = sorted({c["name"] for c in columns if isinstance(c, dict)
                      and isinstance(c.get("name"), str) and isinstance(c.get("entity"), dict)
                      and c["entity"].get("type") == "primary"})
    time_key = model.get("agg_time_dimension") if model else None
    if not isinstance(time_key, str):
        time_key = None
    flags = {"source_yaml_only", "compiled_sql_unavailable", "grain_not_verified",
             "period_not_resolved", "field_lineage_not_traced"}
    if model is None:
        flags.add("source_relation_not_resolved")
    else:
        flags.add("source_ref_declared_only")
    if time_key:
        flags.add("declared_time_key_not_period")
    if raw_filter is not None:
        flags.add("filter_not_resolved")
        if not isinstance(raw_filter, str):
            flags.add("unsupported_filter_shape")

    fields = []
    if malformed:
        syntax = "malformed_definition"
        flags.add("malformed_metric_definition")
    elif typ == "simple":
        if "expr" not in metric:
            syntax = "simple_implicit_expression"
            flags.add("implicit_expression_not_resolved")
        elif isinstance(expr, str) and BARE_FIELD.fullmatch(expr):
            syntax = "simple_bare_field"
            fields = [expr]
            if model and expr not in known_columns:
                flags.add("field_absent_from_model_yaml_columns")
        elif isinstance(expr, (int, float)) and not isinstance(expr, bool):
            syntax = "simple_numeric_constant"
        else:
            syntax = "simple_unsupported_expression"
            flags.add("expression_requires_parser")
        if not metric.get("agg"):
            flags.add("aggregation_missing")
    else:
        syntax = "non_simple_unresolved"
        flags.add("metric_dependencies_not_resolved")
        if typ not in ("derived", "ratio", "cumulative"):
            flags.add("unsupported_metric_type")
        # Keep derived source text separately from an unresolved output value.
        expression = None

    return {
        "id": f"{path}#doc[{document}].{yaml_path}",
        "metric_name": name, "grain": None,
        "source_ref": model.get("name") if model and isinstance(model.get("name"), str) else None,
        "value_expr": expression, "where_expr": None,
        "period_expr": None, "segment_expr": None, "group_by": None,
        "time_key": time_key, "value_input_fields": fields, "filter_input_fields": [],
        "source_location": {"path": path, "start_line": node.start_mark.line + 1,
                            "end_line": last_content_line(node), "document": document,
                            "yaml_path": yaml_path},
        "compiled_location": None, "review_flags": sorted(flags),
        "unknown_semantics": {key: None for key in UNKNOWN_KEYS},
        "metric_type": typ, "aggregation": json_value(metric.get("agg")),
        "syntactic_status": syntax, "declared_primary_columns": primary,
        "declared_expression": json_value(expr) if "expr" in metric else None,
        "declared_filter": json_value(raw_filter) if "filter" in metric else None,
        "declared_dependencies": {key: json_value(metric[key]) for key in DEPENDENCY_KEYS if key in metric},
    }


def extract_document(node, path: str, document: int) -> list[dict]:
    if not isinstance(node, MappingNode):
        return []  # A non-properties YAML document has no native metric definition.
    cards = []
    for index, marked in entries(node, "metrics", path):
        cards.append(card(construct(marked), None, path, document, f"metrics[{index}]", marked))
    for container in METRIC_CONTAINERS:
        for index, marked_model in entries(node, container, path):
            if not isinstance(marked_model, MappingNode):
                continue
            model = model_metadata(marked_model, path)
            for ordinal, marked in entries(marked_model, "metrics", path):
                cards.append(card(construct(marked), model, path, document,
                                  f"{container}[{index}].metrics[{ordinal}]", marked))
    return cards


def build(repo: Path, expected_commit: str) -> tuple[dict, dict]:
    commit, yaml_files = pinned_tree(repo, expected_commit)
    file_oids = dict(yaml_files)
    project_path = next((p for p in ("dbt_project.yml", "dbt_project.yaml") if p in file_oids), None)
    if project_path is None:
        raise ValueError("Pinned tree has no dbt_project.yml or dbt_project.yaml")
    project_file = git(repo, "cat-file", "blob", file_oids[project_path])
    project = yaml.safe_load(project_file)
    if not isinstance(project, dict):
        raise ValueError("dbt_project YAML must be a mapping")
    model_paths = project.get("model-paths", ["models"])
    if (not isinstance(model_paths, list) or not model_paths
            or any(not isinstance(p, str) or not p or p.startswith("/")
                   or ".." in p.split("/") or "{{" in p for p in model_paths)):
        raise ValueError("Cannot resolve dbt model-paths from pinned project YAML")
    roots = [Path(p).as_posix() for p in model_paths]
    in_scope = lambda name: name != project_path and any(
        root == "." or name.startswith(root + "/") for root in roots)
    selected = [(path, oid) for path, oid in yaml_files if in_scope(path)]
    excluded_paths = [path for path, _ in yaml_files if not in_scope(path) and path != project_path]
    blobs = {path: git(repo, "cat-file", "blob", oid) for path, oid in selected}

    cards = []
    empty_files = []
    for path, raw in blobs.items():
        try:
            source = raw.decode("utf-8")
            marked = list(yaml.compose_all(source, Loader=yaml.SafeLoader))
            found = [item for index, node in enumerate(marked)
                     for item in extract_document(node, path, index)]
        except (UnicodeError, yaml.YAMLError, ValueError) as exc:
            raise ValueError(f"Cannot inventory pinned YAML {path}: {exc}") from exc
        cards.extend(found)
        if not found:
            empty_files.append(path)

    cards.sort(key=lambda c: c["id"])
    ids = [item["id"] for item in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source-location metric IDs")
    pairs = [{"left_id": left, "right_id": right}
             for left, right in itertools.combinations(ids, 2)]
    packet = {
        "schema_version": 1,
        "provenance": {
            "project": project.get("name"), "commit": commit,
            "input_sha256": {path: hashlib.sha256(raw).hexdigest()
                             for path, raw in sorted({project_path: project_file, **blobs}.items())},
            "evidence_scope": "Development; pinned source model/metric YAML only; no compilation, rows or labels",
            "yaml_inventory": "Git-tracked .yml/.yaml regular files under pinned dbt model-paths",
            "model_paths": model_paths,
        },
        "cards": cards, "pairs": pairs,
    }
    kinds = Counter(item["metric_type"] or "missing" for item in cards)
    syntax = Counter(item["syntactic_status"] for item in cards)
    flags = Counter(flag for item in cards for flag in item["review_flags"])
    report = {
        "schema_version": 1, "project": project.get("name"), "commit": commit,
        "counts": {"yaml_files_scanned": len(blobs),
                   "yaml_files_with_metrics": len(blobs) - len(empty_files),
                   "metric_cards": len(cards), "unordered_pairs": len(pairs),
                   "metric_types": dict(sorted(kinds.items())),
                   "syntactic_status": dict(sorted(syntax.items())),
                   "syntactically_supported_simple": sum(
                       c["syntactic_status"] in ("simple_bare_field", "simple_numeric_constant")
                       and "aggregation_missing" not in c["review_flags"] for c in cards),
                   "review_flags": dict(sorted(flags.items())),
                   "definitions_excluded": 0},
        "exclusions": {
            "yaml_files_without_metric_definitions": empty_files,
            "yaml_files_outside_model_paths": excluded_paths,
            "non_definition_sections": "Saved-query metric references, measures, tests and source rows are not metric definitions",
            "unread_inputs": "SQL, compiled manifests/artifacts, dependencies outside the pinned Git tree, and warehouse row data; YAML unit-test rows are not constructed",
        },
        "limits": [
            "Recognized definitions under configured model-paths: top-level metrics and metrics directly on models/semantic_models; malformed sequences fail explicitly.",
            "Source expressions are verbatim declarations; raw filters are in declared_filter while where_expr stays null. Neither is compiled or resolved SQL.",
            "Bare fields are syntactic names only; primary columns and aggregate time dimensions are declarations, not verified output grain or period.",
            "Every card requires semantic review; there are no relationship labels, gold pairs or row observations.",
        ],
    }
    return packet, report


def markdown(report: dict) -> str:
    counts = report["counts"]
    lines = ["# Portable dbt YAML metric inventory — development only", "",
             f"Pinned `{report['project']}@{report['commit']}`. Source YAML only; no compilation or rows.", "",
             "| Inventory | Count |", "| --- | ---: |",
             f"| YAML files scanned | {counts['yaml_files_scanned']} |",
             f"| YAML files with definitions | {counts['yaml_files_with_metrics']} |",
             f"| Metric cards | {counts['metric_cards']} |",
             f"| Unordered pairs | {counts['unordered_pairs']} |",
             f"| Syntactically supported simple declarations | {counts['syntactically_supported_simple']} |",
             f"| Definitions excluded | {counts['definitions_excluded']} |", "",
             "| Metric type | Count |", "| --- | ---: |"]
    lines.extend(f"| `{key}` | {count} |" for key, count in counts["metric_types"].items())
    lines.extend(["", "| Syntactic status | Count |", "| --- | ---: |"])
    lines.extend(f"| `{key}` | {count} |" for key, count in counts["syntactic_status"].items())
    lines.extend(["", "| Review diagnostic | Count |", "| --- | ---: |",
                  f"| Bare fields absent from model YAML columns | {counts['review_flags'].get('field_absent_from_model_yaml_columns', 0)} |",
                  f"| Raw filters unresolved | {counts['review_flags'].get('filter_not_resolved', 0)} |",
                  f"| Metric dependencies unresolved | {counts['review_flags'].get('metric_dependencies_not_resolved', 0)} |"])
    lines.extend(["", "## Exclusions and limits", "",
                  f"{len(report['exclusions']['yaml_files_without_metric_definitions'])} scanned model-path YAML files had no native metric definitions; {len(report['exclusions']['yaml_files_outside_model_paths'])} other tracked YAML files were outside dbt's configured model paths. Saved-query references, measures, tests and source rows are excluded as definitions; zero native metric definitions were dropped.", ""])
    lines.extend(f"- {limit}" for limit in report["limits"])
    lines.extend(["", "The packet has no gold labels or row observations. Null grain, period, units, grouping and join properties remain unresolved; the card list and all pairs require review.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output-prefix", type=Path, required=True,
                        help="Path prefix for packet.json, report.json and report.md")
    parser.add_argument("--check", action="store_true", help="Compare outputs without writing")
    args = parser.parse_args()
    packet, report = build(args.repo.resolve(), args.expected_commit)
    outputs = {"packet.json": json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
               "report.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
               "report.md": markdown(report)}
    for suffix, content in outputs.items():
        path = Path(str(args.output_prefix) + suffix)
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"Missing or stale output: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"Pinned {report['project']}@{report['commit']}: "
          f"{len(packet['cards'])} cards, {len(packet['pairs'])} pairs; "
          f"{'verified' if args.check else 'wrote development packet/report'}")


if __name__ == "__main__":
    main()
