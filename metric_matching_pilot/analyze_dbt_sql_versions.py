#!/usr/bin/env python3
"""Bounded dbt SQL source comparison across adjacent Git commits.

Recognizes identical SQL token streams despite comments/whitespace and follows
simple dbt ref('model') dependencies. Every other SQL change remains unresolved.
This is not compiled dbt, column lineage, or a semantic equivalence checker.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import quote


LEX = re.compile(
    r"(?P<comment>--[^\n]*|/\*.*?\*/)|"
    r"(?P<string>'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")|"
    r"(?P<jinja>\{\{.*?\}\}|\{%.*?%\})|"
    r"(?P<space>\s+)|"
    r"(?P<token>[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?|::|<>|!=|<=|>=|.)",
    re.S,
)
SIMPLE_REF = re.compile(r"\{\{\s*ref\(\s*(['\"])([A-Za-z_][\w]*)\1\s*\)\s*\}\}")


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if done.returncode:
        raise ValueError(f"Git command failed: {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.rstrip("\n")


def sql_paths(repo: Path, commit: str) -> list[str]:
    return [path for path in git(repo, "ls-tree", "-r", "--name-only", commit, "--", "models").splitlines()
            if path.endswith(".sql") and path.startswith("models/")]


def tokens(sql: str) -> list[tuple[str, str, int]]:
    out = []
    offset = 0
    for match in LEX.finditer(sql):
        if match.start() != offset:
            raise ValueError("SQL lexer skipped source text")
        offset = match.end()
        kind = match.lastgroup
        if kind not in ("space", "comment"):
            out.append((kind, match.group(), sql.count("\n", 0, match.start()) + 1))
    if offset != len(sql):
        raise ValueError("SQL lexer stopped before the end of source")
    return out


def refs(sql: str) -> tuple[list[dict], list[dict]]:
    resolved, unresolved = [], []
    for kind, value, line in tokens(sql):
        if kind != "jinja" or "ref(" not in value.replace(" ", ""):
            continue
        match = SIMPLE_REF.fullmatch(value)
        if match:
            resolved.append({"model": match.group(2), "line": line})
        else:
            unresolved.append({"expression": value, "line": line})
    return resolved, unresolved


def read_models(repo: Path, commit: str) -> dict[str, dict]:
    result = {}
    for path in sql_paths(repo, commit):
        sql = git(repo, "show", f"{commit}:{path}")
        dependency_refs, uncertain = refs(sql)
        result[path] = {
            "name": Path(path).stem, "sql": sql,
            "tokens": [(k, v) for k, v, _ in tokens(sql)],
            "refs": dependency_refs, "unsupported_refs": uncertain,
        }
    return result


def dependents(models: dict[str, dict], seed_names: set[str]) -> tuple[dict[str, list[dict]], list[dict], list[dict]]:
    names = defaultdict(list)
    for path, info in models.items():
        names[info["name"]].append(path)
    reverse = defaultdict(list)
    unresolved = []
    seed_refs = []
    for path, info in models.items():
        for ref in info["refs"]:
            candidates = names.get(ref["model"], [])
            if len(candidates) == 1:
                reverse[candidates[0]].append({"path": path, "line": ref["line"]})
            elif not candidates and ref["model"] in seed_names:
                seed_refs.append({"consumer": path, "line": ref["line"], "seed": ref["model"]})
            else:
                unresolved.append({"consumer": path, "line": ref["line"],
                                   "reference": ref["model"],
                                   "reason": "Missing or nonunique model name"})
        unresolved.extend({"consumer": path, **ref, "reason": "Unsupported ref syntax"}
                          for ref in info["unsupported_refs"])
    return reverse, unresolved, seed_refs


def transitive_dependents(start: str, reverse: dict[str, list[dict]]) -> list[dict]:
    result, visited, queue = [], {start}, deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        for ref in sorted(reverse.get(node, []), key=lambda item: (item["path"], item["line"])):
            path = ref["path"]
            if path in visited:
                continue
            visited.add(path)
            result.append({"model_path": path, "depth": depth + 1,
                           "edge_from": node, "source_line": ref["line"]})
            queue.append((path, depth + 1))
    return result


def analyze(repo: Path, earlier: str, later: str) -> dict:
    before = git(repo, "rev-parse", "--verify", f"{earlier}^{{commit}}")
    after = git(repo, "rev-parse", "--verify", f"{later}^{{commit}}")
    if git(repo, "rev-parse", f"{after}^") != before:
        raise ValueError("Only adjacent parent/child commits are supported")
    old, new = read_models(repo, before), read_models(repo, after)
    seed_names = {Path(path).stem for path in git(repo, "ls-tree", "-r", "--name-only", after, "--", "seeds").splitlines()
                  if path.startswith("seeds/") and path.endswith(".csv")}
    reverse, unresolved_refs, seed_refs = dependents(new, seed_names)
    changes = []
    for path in sorted(old.keys() | new.keys()):
        left, right = old.get(path), new.get(path)
        if left is None:
            status = "added_model"
        elif right is None:
            status = "removed_model"
        elif left["sql"] == right["sql"]:
            status = "unchanged_source"
        elif left["tokens"] == right["tokens"]:
            status = "same_nontrivia_token_stream"
        else:
            status = "needs_review_sql_changed"
        if status == "unchanged_source":
            continue
        changes.append({"model_path": path, "status": status,
                        "before_location": {"commit": before, "path": path, "line": 1} if left else None,
                        "after_location": {"commit": after, "path": path, "line": 1} if right else None,
                        "before_refs": left["refs"] if left else [],
                        "after_refs": right["refs"] if right else [],
                        "potential_downstream_models": transitive_dependents(path, reverse) if right else [],
                        "interpretation": (
                            "Same lexical SQL tokens after removing comments/whitespace; compilation and output not checked"
                            if status == "same_nontrivia_token_stream" else
                            "Different token stream or model set; metric behavior undetermined"
                        )})
    return {"before_commit": before, "after_commit": after,
            "model_count_before": len(old), "model_count_after": len(new),
            "source_comparison": "Exact file path matching, then token equality ignoring only comments/whitespace",
            "status_counts": dict(Counter(c["status"] for c in changes)),
            "changes": changes, "unresolved_refs": unresolved_refs,
            "resolved_seed_refs": seed_refs,
            "limits": ["No dbt compilation or macro expansion at the earlier commit",
                       "No field-level lineage or metric branch extraction from UNION ALL SQL",
                       "Same token stream is a low-level source observation, not a proof of equal runtime results",
                       "Downstream refs mark possible dependency, not changed values or users",
                       "Different tokens get needs_review, including harmless alias/parenthesis refactors"]}


def remote_url(repo: Path) -> str | None:
    value = subprocess.run(["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
                           text=True, capture_output=True).stdout.strip()
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([\w.\-]+/[\w.\-]+?)(?:\.git)?/?", value)
    return f"https://github.com/{match.group(1)}" if match else None


def link(loc: dict, remote: str | None) -> str:
    label = f"{loc['path']}:{loc['line']}"
    if remote:
        return f"[{label}]({remote}/blob/{loc['commit']}/{quote(loc['path'])}#L{loc['line']})"
    return f"`{loc['commit']}:{label}`"


def markdown(report: dict, remote: str | None) -> str:
    lines = ["# Bounded dbt SQL adjacent-commit source analysis", "",
             f"Parent `{report['before_commit']}`, child `{report['after_commit']}`; "
             f"{report['model_count_before']} and {report['model_count_after']} model SQL files.", "",
             "## Source-level changes", "",
             "The analyzer linked models by file path, removed comments and whitespace *outside* strings and "
             "Jinja blocks, compared remaining lexical tokens, and built a model-level `ref()` graph. "
             "Only token-identical source is labeled a formatting/comment change; everything else "
             "requiring semantic interpretation stays `needs_review`.", "",
             "| Status | Count |", "| --- | ---: |"]
    for status, count in sorted(report["status_counts"].items()):
        lines.append(f"| `{status}` | {count} |")
    lines += ["", "## Selected trace: `fct_opportunities` and metric descendants", ""]
    case = next((c for c in report["changes"] if c["model_path"].endswith("/fct_opportunities.sql")), None)
    if case:
        lines.append(f"Source {link(case['before_location'], remote)} → "
                     f"{link(case['after_location'], remote)}: `{case['status']}`. "
                     "This records stable SQL tokens across a formatting change, not executed dbt equivalence.")
        lines += ["", "Potential downstream models via declared `ref()` edges:", ""]
        for ref in case["potential_downstream_models"]:
            loc = {"commit": report["after_commit"], "path": ref["model_path"],
                   "line": ref["source_line"]}
            lines.append(f"- Depth {ref['depth']}: {link(loc, remote)}")
        lines.append("")
    lines += ["## Boundaries", "", "- " + "\n- ".join(report["limits"]), "",
              f"Resolved seed `ref()` edges: {len(report['resolved_seed_refs'])}; "
              f"unresolved `ref()` edges: {len(report['unresolved_refs'])}. "
              "The complete model list, paths, statuses, and graph are in the JSON report. "
              "This is a development diagnostic, not a measured metric matcher.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check", action="store_true", help="Check the pinned GTM development commit")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        raise ValueError("--repo must be a local Git checkout")
    report = analyze(repo, args.before, args.after)
    if args.check:
        selected = {Path(c["model_path"]).stem: c for c in report["changes"]}
        if selected["fct_opportunities"]["status"] != "same_nontrivia_token_stream":
            raise AssertionError("Expected SQL-token-preserving development refactor is missing")
        descendants = {Path(c["model_path"]).stem for c in selected["fct_opportunities"]["potential_downstream_models"]}
        if not {"fct_metric_values", "rpt_metric_reconciliation"}.issubset(descendants):
            raise AssertionError("Expected public metric/reconciliation dependency is missing")
        if selected["rpt_metric_reconciliation"]["status"] != "needs_review_sql_changed":
            raise AssertionError("Unsupported alias refactor must abstain")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "dbt_version_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output_dir / "dbt_version_report.md").write_text(markdown(report, remote_url(repo)))
    print(f"Read {report['model_count_before']}/{report['model_count_after']} dbt model files; "
          f"classified {len(report['changes'])} changed/added/removed sources; "
          f"statuses: {report['status_counts']}")


if __name__ == "__main__":
    main()
