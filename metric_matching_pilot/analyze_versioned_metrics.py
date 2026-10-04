#!/usr/bin/env python3
"""Compare two Git revisions of a small, documented Rill metrics-view subset.

This is a source analyzer, not a SQL compiler or a metric-value verifier. It
links unchanged measure IDs automatically, reports expression changes, and
traces explicit dashboard references. Unsupported semantics remain unresolved.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )
    if done.returncode:
        raise ValueError(f"Git command failed: {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.rstrip("\n")


def checked_project(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.is_absolute() or not path or any(p in ("..", ".") for p in pure.parts):
        raise ValueError("--project must be a relative path without dot segments")
    return str(pure)


def files_at(repo: Path, commit: str, prefix: str, suffix: str) -> list[str]:
    return [path for path in git(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix).splitlines()
            if path.endswith(suffix)]


def source(repo: Path, commit: str, path: str) -> str:
    return git(repo, "show", f"{commit}:{path}")


def mapping(node: MappingNode) -> dict[str, yaml.nodes.Node]:
    if not isinstance(node, MappingNode):
        raise ValueError("Expected a YAML mapping")
    return {k.value: v for k, v in node.value if isinstance(k, ScalarNode)}


def scalar(node: yaml.nodes.Node | None) -> str | None:
    return node.value if isinstance(node, ScalarNode) else None


def where(commit: str, path: str, node: yaml.nodes.Node) -> dict:
    return {"commit": commit, "path": path, "line": node.start_mark.line + 1}


def model_lineage(repo: Path, commit: str, project: str, model: str | None) -> dict:
    if not model or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", model):
        return {"status": "needs_review", "reason": "Missing or unsupported model name"}
    sql_path = f"{project}/models/{model}.sql"
    if sql_path not in files_at(repo, commit, f"{project}/models", ".sql"):
        return {"status": "needs_review", "reason": "Model SQL missing in selected revision"}
    sql = source(repo, commit, sql_path)
    source_names = {PurePosixPath(p).stem for p in files_at(repo, commit, f"{project}/sources", ".yaml")}
    tokens = re.findall(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z_0-9]*)", sql, re.I)
    referenced = sorted(set(tokens) & source_names)
    refs = []
    for name in referenced:
        match = re.search(r"\b(?:from|join)\s+" + re.escape(name) + r"\b", sql, re.I)
        assert match is not None
        refs.append({"source": name, "location": {"commit": commit, "path": sql_path,
                                                   "line": sql[:match.start()].count("\n") + 1}})
    if not refs:
        return {"status": "needs_review", "reason": "No resolvable declared source"}
    return {"status": "model_level_only", "model": model, "model_path": sql_path,
            "declared_sources": refs,
            "clock_relative_time_detected": bool(re.search(r"\bCURRENT_TIMESTAMP\b", sql, re.I)),
            "field_lineage": "needs_review: model has SQL CTEs/star projections; no column mapping or join-cardinality proof"}


def measures_at(repo: Path, commit: str, project: str) -> dict[tuple[str, str], dict]:
    result = {}
    for path in files_at(repo, commit, f"{project}/metrics", ".yaml"):
        content = source(repo, commit, path)
        root = yaml.compose(content)
        if not isinstance(root, MappingNode):
            raise ValueError(f"Unsupported metrics view YAML: {path}")
        fields = mapping(root)
        if scalar(fields.get("type")) != "metrics_view":
            continue
        entries = fields.get("measures")
        if not isinstance(entries, SequenceNode):
            raise ValueError(f"Unsupported measures field: {path}")
        view = PurePosixPath(path).stem
        model = scalar(fields.get("model"))
        lineage = model_lineage(repo, commit, project, model)
        for entry in entries.value:
            if not isinstance(entry, MappingNode):
                raise ValueError(f"Unsupported measure entry: {path}")
            item = mapping(entry)
            name, expr = scalar(item.get("name")), scalar(item.get("expression"))
            if not name or expr is None or not re.fullmatch(r"[A-Za-z_0-9]+", name):
                raise ValueError(f"Missing/unsupported name or expression: {path}:{entry.start_mark.line+1}")
            key = (view, name)
            if key in result:
                raise ValueError(f"Duplicate measure key: {key}")
            result[key] = {
                "view": view, "measure": name, "expression": expr.strip(),
                "model": model,
                "time_column": scalar(fields.get("timeseries")),
                "smallest_time_grain": scalar(fields.get("smallest_time_grain")),
                "format_preset": scalar(item.get("format_preset")),
                "location": where(commit, path, item["expression"]),
                "lineage": lineage,
                "unresolved": ["business_population", "unit_beyond_format_hint",
                               "join_cardinality", "field_level_lineage", "observed_values"],
            }
    return result


def compact(expression: str) -> str:
    return re.sub(r"\s+", "", expression).lower()


def expression_class(before: dict, after: dict) -> dict:
    scope_fields = ("model", "time_column", "smallest_time_grain")
    if any(before[field] != after[field] for field in scope_fields):
        return {"kind": "needs_review", "reason": "Model or declared time/grain changed"}
    old, new = compact(before["expression"]), compact(after["expression"])
    if old == new:
        return {"kind": "expression_unchanged"}
    guarded = re.fullmatch(r"(.+)/nullif\((sum\([a-z_][a-z_0-9]*\)),0\)", new)
    if guarded and old == guarded.group(1) + "/" + guarded.group(2):
        return {"kind": "zero_denominator_guard_added",
                "denominator": guarded.group(2),
                "input_domain": f"{guarded.group(2)} = 0 after grouping",
                "nonzero_domain": "Expressions algebraically identical if other inputs and numeric semantics agree",
                "zero_domain": "New expression returns NULL; old division-by-zero result is engine-specific",
                "observed_row_impact": "needs_review: source data and native runtime not executed"}
    return {"kind": "needs_review", "reason": "Expression changed outside the supported pattern"}


def dashboard_refs(repo: Path, commit: str, project: str, view: str, measure: str) -> list[dict]:
    found = []
    for path in files_at(repo, commit, f"{project}/dashboards", ".yaml"):
        root = yaml.compose(source(repo, commit, path))
        if not root:
            continue

        def walk(node: yaml.nodes.Node, inherited_view: str | None, parent_key: str = "") -> None:
            if isinstance(node, MappingNode):
                attrs = mapping(node)
                local_view = scalar(attrs.get("metrics_view")) or inherited_view
                for key, value in node.value:
                    walk(value, local_view, scalar(key) or "")
            elif isinstance(node, SequenceNode):
                for value in node.value:
                    walk(value, inherited_view, parent_key)
            elif isinstance(node, ScalarNode) and inherited_view == view:
                if node.value == measure and parent_key not in ("metrics_view", "display_name"):
                    found.append({"kind": "explicit_declaration", "location": where(commit, path, node)})
                elif node.value == "*" and parent_key == "measures":
                    found.append({"kind": "wildcard_potential", "location": where(commit, path, node)})

        walk(root, None)
    return sorted(found, key=lambda ref: (ref["location"]["path"], ref["location"]["line"], ref["kind"]))


def base_url(repo: Path) -> str | None:
    value = subprocess.run(["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
                           text=True, capture_output=True, check=False).stdout.strip()
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([\w.\-]+/[\w.\-]+?)(?:\.git)?/?", value)
    return f"https://github.com/{match.group(1)}" if match else None


def anchor(ref: dict, remote: str | None) -> str:
    commit, path, line = ref["commit"], ref["path"], ref["line"]
    label = f"{path}:{line}"
    if remote:
        return f"[{label}]({remote}/blob/{commit}/{quote(path)}#L{line})"
    return f"`{commit}:{label}`"


def analyze(repo: Path, project: str, before_ref: str, after_ref: str) -> dict:
    before = git(repo, "rev-parse", "--verify", f"{before_ref}^{{commit}}")
    after = git(repo, "rev-parse", "--verify", f"{after_ref}^{{commit}}")
    if git(repo, "rev-parse", f"{after}^") != before:
        raise ValueError("This pilot only compares adjacent parent and child commits")
    old, new = measures_at(repo, before, project), measures_at(repo, after, project)
    common = sorted(old.keys() & new.keys())
    changes = []
    for key in common:
        left, right = old[key], new[key]
        decision = expression_class(left, right)
        if decision["kind"] == "expression_unchanged":
            continue
        changes.append({"view": key[0], "measure": key[1], "before": left, "after": right,
                        "decision": decision,
                        "declared_dashboard_consumers": dashboard_refs(repo, after, project, *key)})
    return {
        "project": project, "before_commit": before, "after_commit": after,
        "method": "Rill metrics-view YAML scalar expression subset; exact (view,measure) ID linking across adjacent commits",
        "candidate_generation": {"old_count": len(old), "new_count": len(new),
                                 "linked_exact_id": len(common),
                                 "removed_or_unlinked": sorted([list(k) for k in old.keys() - new.keys()]),
                                 "added_or_unlinked": sorted([list(k) for k in new.keys() - old.keys()]),
                                 "rename_detection": "unsupported",
                                 "cross_view_equivalence_retrieval": "unsupported"},
        "changes": changes,
        "limits": ["No metric values or remote parquet queried", "No native Rill runtime executed",
                   "Dashboard declarations show potential consumers, not actual use or affected users",
                   "Model-level source recognition does not prove field lineage, population, or join cardinality",
                   "No evaluation on unseen repositories and no matching accuracy measurement"],
    }


def markdown(report: dict, remote: str | None) -> str:
    cand = report["candidate_generation"]
    rows = [
        "# Automated adjacent-commit metric analysis — development case", "",
        f"Project `{report['project']}`; parent `{report['before_commit']}`; child `{report['after_commit']}`.",
        "", "## Automated candidate linking and changes", "",
        f"The analyzer read {cand['old_count']} prior and {cand['new_count']} later measures; "
        f"linked {cand['linked_exact_id']} by the declared `(metrics_view, measure)` ID without pair IDs; "
        f"found {len(report['changes'])} changed expressions. Added/removed or renamed measures remain unresolved.",
        "", "| Measure | Before | After | Source-level classification |", "| --- | --- | --- | --- |",
    ]
    for change in report["changes"]:
        before, after = change["before"], change["after"]
        rows.append(f"| `{change['view']}.{change['measure']}` | "
                    f"{anchor(before['location'], remote)} | {anchor(after['location'], remote)} | "
                    f"`{change['decision']['kind']}` |")
    rows += ["", "## Changed-input condition and declared consumers", ""]
    for change in report["changes"]:
        decision = change["decision"]
        rows.append(f"### `{change['view']}.{change['measure']}`")
        rows.append("")
        rows.append(f"Before: `{change['before']['expression']}`. After: `{change['after']['expression']}`.")
        rows.append("")
        if decision["kind"] == "zero_denominator_guard_added":
            rows.append(f"The only supported expression change is guarding `{decision['denominator']}` "
                        "with `NULLIF(..., 0)`. For a zero grouped denominator, the new expression yields "
                        "NULL; the old division-by-zero outcome depends on the engine. With a nonzero "
                        "denominator, the expressions agree under the same inputs and numeric semantics. "
                        "Observed Rill row impact: **unknown**.")
        else:
            rows.append(f"Classification is unresolved: {decision.get('reason', 'unsupported change')}.")
        rows += ["", "Declared dashboard references in the child revision:", ""]
        refs = change["declared_dashboard_consumers"]
        if refs:
            rows += [f"- {item['kind']}: {anchor(item['location'], remote)}" for item in refs]
        else:
            rows.append("- No explicit declaration found in the scanned dashboards.")
        lineage = change["after"]["lineage"]
        if lineage.get("declared_sources"):
            rows += ["", "Model-level source path (field-level lineage unresolved):"]
            rows += [f"- `{lineage['model']}` reads `{item['source']}` at "
                     f"{anchor(item['location'], remote)}" for item in lineage["declared_sources"]]
        rows.append("")
    rows += ["## Boundaries", "", "- " + "\n- ".join(report["limits"]), "",
             "This is a reproducible development case and a narrow automated source analysis. "
             "It is not a measured matcher, a proof of metric equivalence, or an industrial result.", ""]
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--project", default="rill-openrtb-prog-ads")
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check", action="store_true", help="Check the pinned historical case")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        raise ValueError("--repo must be a local Git checkout")
    report = analyze(repo, checked_project(args.project), args.before, args.after)
    if args.check:
        observed = {(c["view"], c["measure"], c["decision"]["kind"]) for c in report["changes"]}
        expected = {("bids_metrics", "ctr", "zero_denominator_guard_added"),
                    ("bids_metrics", "ecpm", "zero_denominator_guard_added")}
        if observed != expected:
            raise AssertionError(f"Historical change differs from expected: {observed}")
        for change in report["changes"]:
            if not any(ref["kind"] == "explicit_declaration" for ref in change["declared_dashboard_consumers"]):
                raise AssertionError(f"Missing declared consumer for {change['measure']}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "versioned_metrics_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output_dir / "versioned_metrics_report.md").write_text(markdown(report, base_url(repo)))
    print(f"Linked {report['candidate_generation']['linked_exact_id']} measures; "
          f"found {len(report['changes'])} expression changes; outputs in {args.output_dir}")


if __name__ == "__main__":
    main()
