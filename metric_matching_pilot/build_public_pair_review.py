#!/usr/bin/env python3
"""Validate source-backed pair proposals and produce a label-blind review sheet."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent


def metric_index(repo):
    found = {}
    for path in (repo / "models").rglob("*.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for model in data.get("models", []):
            keys = [column["name"] for column in model.get("columns", [])
                    if isinstance(column.get("entity"), dict) and column["entity"].get("type") == "primary"]
            for metric in model.get("metrics", []):
                key = (model["name"], metric["name"])
                if key in found:
                    raise ValueError(f"Duplicate metric: {key}")
                found[key] = {"metric": metric, "primary_key": keys[0] if len(keys) == 1 else None,
                              "time_dimension": model.get("agg_time_dimension"),
                              "path": str(path.relative_to(repo))}
    return found


def validate(repo, pack, index):
    commit = repository_commit(repo)
    if commit != pack["commit"]:
        raise ValueError(f"Unexpected repository revision: {commit}")
    ids = set()
    for pair in pack["pairs"]:
        pair_id = pair["id"]
        if pair_id in ids:
            raise ValueError(f"Duplicate pair ID: {pair_id}")
        ids.add(pair_id)
        if pair["proposed_label"] not in pack["labels"]:
            raise ValueError(f"Unknown proposed label in {pair_id}")
        for side in ("left", "right"):
            key = (pair[side]["model"], pair[side]["metric"])
            if key not in index:
                raise ValueError(f"Missing public metric {key}")
            if not any(e["path"] == index[key]["path"] and
                       re.search(r"^\s*- name:\s*" + re.escape(key[1]) + r"\s*$",
                                 "\n".join((repo / e["path"]).read_text(encoding="utf-8").splitlines()[e["start"] - 1:e["end"]]), re.M)
                       for e in pair["evidence"]):
                raise ValueError(f"No metric YAML definition evidence for {pair_id} {side}")
        for e in pair["evidence"]:
            path = repo / e["path"]
            if not path.is_file() or not str(path.resolve()).startswith(str(repo.resolve()) + "/"):
                raise ValueError(f"Invalid evidence path for {pair_id}")
            length = len(path.read_text(encoding="utf-8").splitlines())
            if not 1 <= e["start"] <= e["end"] <= length:
                raise ValueError(f"Invalid line range for {pair_id}: {e}")
    return commit


def field(value):
    if value is None:
        return "unspecified"
    if isinstance(value, str):
        return " ".join(value.split()).replace("|", "\\|")
    return str(value)


def blind_sheet(pack, index):
    commit = pack["commit"]
    lines = ["# Independent public metric-pair review", "",
             f"Repository: [dbt-labs/jaffle-shop at pinned commit](https://github.com/dbt-labs/jaffle-shop/tree/{commit}).",
             "", "Choose one label for each pair **before opening `public_pair_proposals.json`**. These metrics occur naturally in the repository. Review SQL and YAML at the linked lines; do not assume a value match from names. Record why the label holds, or what evidence is missing. This is an unfilled sheet, not a completed independent annotation.", "",
             "Labels: `direct_equivalent` (same quantity/rules), `cross_grain_equivalent` (proved aligned additive transformation), `temporal_or_scope_variant` (same base concept, changed time/population), `related` (shared domain without safe substitution), `conflicting_definition` (same identity/name used for incompatible meanings), `non_match` (different business quantity), `needs_review` (decisive evidence missing).", ""]
    for pair in pack["pairs"]:
        left, right = pair["left"], pair["right"]
        lines += [f"## {pair['id']}: `{left['model']}.{left['metric']}` versus `{right['model']}.{right['metric']}`", "",
                  "| Side | Aggregation | Expression | Filter | Native entity key | Default time dimension |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for side in ("left", "right"):
            node = pair[side]
            entry = index[(node["model"], node["metric"])]
            metric = entry["metric"]
            expr = metric.get("expr", metric["name"])
            lines.append(f"| {side} | `{field(metric.get('agg'))}` | `{field(expr)}` | `{field(metric.get('filter'))}` | `{field(entry['primary_key'])}` | `{field(entry['time_dimension'])}` |")
        refs = [f"[{e['path']}:{e['start']}-{e['end']}](https://github.com/dbt-labs/jaffle-shop/blob/{commit}/{e['path']}#L{e['start']}-L{e['end']})"
                for e in pair["evidence"]]
        lines += ["", "Evidence locations: " + "; ".join(refs) + ".", "",
                  "Reviewer label: ______  Reason / missing evidence: ____________________", ""]
    return "\n".join(lines)


def proposal_summary(pack):
    lines = ["# First-annotator public pair proposals", "",
             f"Pinned revision: `{pack['commit']}`. These ten labels were proposed by one analyst using repository metadata and selected source SQL. No second independent label, adjudication, data reconciliation, or matcher result exists yet.", "",
             "| ID | Pair | Proposed label | Reason / condition |", "| --- | --- | --- | --- |"]
    for p in pack["pairs"]:
        lines.append(f"| {p['id']} | `{p['left']['model']}.{p['left']['metric']}` / `{p['right']['model']}.{p['right']['metric']}` | `{p['proposed_label']}` | {p['reason']} |")
    counts = Counter(p["proposed_label"] for p in pack["pairs"])
    lines += ["", "Distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + ".", "",
              "There are no confirmed equivalent pairs in this naturally occurring sample. Do not use this pack as an accuracy benchmark until an independent reviewer submits blind labels and disagreements are adjudicated. The pair selection is small and intentionally enriched for difficult relationships, so its label distribution is not representative of enterprise metrics.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo = args.repo.resolve()
    pack = json.loads((ROOT / "public_pair_proposals.json").read_text(encoding="utf-8"))
    index = metric_index(repo)
    validate(repo, pack, index)
    blind = blind_sheet(pack, index)
    (ROOT / "public_pair_blind_review.md").write_text(blind, encoding="utf-8")
    (ROOT / "public_pair_proposals.md").write_text(proposal_summary(pack), encoding="utf-8")
    if args.check:
        assert len(pack["pairs"]) == 10
        assert Counter(p["proposed_label"] for p in pack["pairs"]) == {
            "related": 4, "temporal_or_scope_variant": 4, "non_match": 1, "needs_review": 1}
        for p in pack["pairs"]:
            section = blind.split(f"## {p['id']}: ", 1)[1].split("\n## ", 1)[0]
            assert p["proposed_label"] not in section, f"Label leaked for {p['id']}"
            assert p["reason"] not in section, f"Rationale leaked for {p['id']}"
    print("Validated 10 public pairs at pinned commit; wrote blinded review and analyst-proposal summaries"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
