#!/usr/bin/env python3
"""Compare GTM long-format metric branches in two pinned, adjacent Git objects.

Only literal (metric_name, grain) IDs are linked. SQL tokens, source-level ref()
edges and changed line spans are evidence, never a test of runtime equivalence.
No dbt compilation, SQL execution, field lineage or held-out corpus is involved.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from urllib.parse import quote

# Import the existing analyzers without creating bytecode beside shared files.
sys.dont_write_bytecode = True
import analyze_dbt_sql_versions as versions  # noqa: E402
import extract_dbt_metric_branches as branches  # noqa: E402


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "public_corpus" / "gtm-funnel-analytics"
BEFORE = "f387f822ab65f94bb2d04691ed0288ec3cdb17a2"
AFTER = "a4c122762b910a6a1c847e3d1a4999a5162db00a"
MODEL = branches.MODEL
BASE_URL = "https://github.com/jross21/gtm-funnel-analytics"
JSON_PATH = ROOT / "versioned_dbt_branches_report.json"
MD_PATH = ROOT / "versioned_dbt_branches_report.md"
EXPOSURES = "models/exposures.yml"
BARE_REF = re.compile(r"\bref\(\s*(['\"])([A-Za-z_]\w*)\1\s*\)")


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise ValueError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def git_text(repo: Path, *args: str) -> str:
    return git_bytes(repo, *args).decode("utf-8")


def location(commit: str, path: str, start: int, end: int | None = None) -> dict:
    return {"commit": commit, "path": path, "start_line": start, "end_line": start if end is None else end}


def full_location(commit: str, path: str, sql: str) -> dict:
    return location(commit, path, 1, max(1, len(sql.splitlines())))


def exact_edit_spans(before: str, after: str, old: str, new: str, path: str) -> list[dict]:
    """Line spans in both Git blobs, including empty sides for insert/delete."""
    result = []
    for op, a, b, c, d in difflib.SequenceMatcher(
        None, old.splitlines(), new.splitlines(), autojunk=False
    ).get_opcodes():
        if op != "equal":
            result.append({"operation": op,
                           "before": location(before, path, a + 1, b) if a < b else None,
                           "after": location(after, path, c + 1, d) if c < d else None})
    return result


def source_comparison(before: str, after: str, path: str,
                      old: str | None, new: str | None) -> dict:
    if old is None:
        status = "added_source"
    elif new is None:
        status = "removed_source"
    elif old == new:
        status = "identical_source"
    elif path.endswith(".csv"):
        status = "seed_data_source_edit"
    elif nontrivia(old) == nontrivia(new):
        status = "trivia_only_source_edit"
    else:
        status = "nontrivia_source_edit"
    return {"model_path": path, "status": status,
            "before_location": full_location(before, path, old) if old is not None else None,
            "after_location": full_location(after, path, new) if new is not None else None,
            "edit_spans": exact_edit_spans(before, after, old, new, path)
            if path.endswith(".sql") and old is not None and new is not None and old != new else []}


def nontrivia(sql: str | None) -> list[tuple[str, str]] | None:
    return [(kind, value) for kind, value, _ in versions.tokens(sql)] if sql is not None else None


def bounded_time_predicates(where: str | None) -> list[list[tuple[str, str]]]:
    """Only column BETWEEN <Jinja> AND <Jinja>; other time SQL stays unclassified."""
    if not where:
        return []
    tokens = branches.Source(where).tokens
    found = []
    for pos in range(1, len(tokens) - 3):
        if (branches.word(tokens[pos], "between") and tokens[pos + 1].kind == "jinja"
                and branches.word(tokens[pos + 2], "and") and tokens[pos + 3].kind == "jinja"
                and tokens[pos - 1].kind == "word"):
            start = pos - 3 if (pos >= 3 and tokens[pos - 2].value == "."
                                     and tokens[pos - 3].kind == "word") else pos - 1
            found.append([(t.kind, t.value) for t in tokens[start:pos + 4]])
    return found


def read_models(repo: Path, commit: str) -> dict[str, dict]:
    result = {}
    for path in versions.sql_paths(repo, commit):
        sql = git_text(repo, "show", f"{commit}:{path}")
        refs, unresolved = versions.refs(sql)
        result[path] = {"name": Path(path).stem, "sql": sql, "refs": refs,
                        "unsupported_refs": unresolved}
    return result


def read_seeds(repo: Path, commit: str) -> dict[str, str]:
    paths = versions.git(repo, "ls-tree", "-r", "--name-only", commit, "--", "seeds").splitlines()
    return {path: git_text(repo, "show", f"{commit}:{path}")
            for path in paths if path.startswith("seeds/") and path.endswith(".csv")}


def source_branches(commit: str, sql: str) -> dict:
    snapshot = {"commit": commit, "path": MODEL,
                "sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                "location": full_location(commit, MODEL, sql)}
    try:
        extracted = branches.extract(sql)
        source = branches.Source(sql)
        ctes, _, _ = branches.ctes(source)
        parts = branches.union_parts(ctes["unioned"]["body"])
        assert len(parts) == len(extracted["branches"])
    except branches.Unsupported as exc:
        snapshot.update({"extraction_status": "unsupported_model_shape", "reason": str(exc),
                         "branches": [], "counts": None})
        return snapshot
    snapshot.update({"extraction_status": "bounded_extraction", "counts": extracted["counts"],
                     "branches": extracted["branches"]})
    for entry, tokens in zip(snapshot["branches"], parts):
        entry["raw_sql"] = source.raw(tokens)
        # The older extractor has a different pinned constant; always overwrite it.
        for key in ("location", "source_cte_location", "source_ref_location"):
            if entry.get(key):
                entry[key] = {"commit": commit, **entry[key]}
        for key, loc in entry.get("clause_locations", {}).items():
            if loc:
                entry["clause_locations"][key] = {"commit": commit, **loc}
        for definition in entry.get("jinja_set_definitions", {}).values():
            if definition.get("location"):
                definition["location"] = {"commit": commit, **definition["location"]}
    return snapshot


def branch_index(snapshot: dict) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    groups = defaultdict(list)
    unresolved = []
    for entry in snapshot["branches"]:
        if (entry["parse_status"] != "extracted" or not entry.get("metric_name")
                or entry.get("grain") == "unknown"):
            unresolved.append({"ordinal": entry["ordinal"], "location": entry["location"],
                               "reason": entry.get("reason", "Unknown literal metric name/grain")})
        else:
            groups[(entry["metric_name"], entry["grain"])].append(entry)
    for key, entries in groups.items():
        if len(entries) != 1:
            unresolved.extend({"ordinal": entry["ordinal"], "location": entry["location"],
                               "reason": f"Duplicate explicit ID {key!r}"} for entry in entries)
    return {key: entries[0] for key, entries in groups.items() if len(entries) == 1}, unresolved


def direct_change(old: dict, new: dict) -> dict:
    """Compare declared facets; token equality is only a lexical observation."""
    facets = []
    old_expr, new_expr = old["expressions"], new["expressions"]
    for name, facet in (("value", "value"), ("period_start", "time"),
                        ("segment", "grouping")):
        if nontrivia(old_expr[name]) != nontrivia(new_expr[name]):
            facets.append(facet)
    for name, facet in (("where", "filter"), ("group_by", "grouping")):
        if nontrivia(old[name]) != nontrivia(new[name]):
            facets.append(facet)
            if name == "where" and (old["time_filter_keys"] != new["time_filter_keys"]
                                     or bounded_time_predicates(old["where"]) !=
                                     bounded_time_predicates(new["where"])):
                facets.append("time")
    if (old["source_cte"], old["source_ref"]) != (new["source_cte"], new["source_ref"]):
        facets.append("source")
    declarations = set(old["jinja_set_definitions"]) | set(new["jinja_set_definitions"])
    for name in declarations:
        left = old["jinja_set_definitions"].get(name, {}).get("expression")
        right = new["jinja_set_definitions"].get(name, {}).get("expression")
        if nontrivia(left) == nontrivia(right):
            continue
        marker = re.compile(r"\{\{\s*" + re.escape(name) + r"\s*}}")
        for field, facet in (("value", "value"), ("period_start", "time"),
                             ("segment", "grouping")):
            if marker.search(old_expr[field]) or marker.search(new_expr[field]):
                facets.append(facet)
        for field, facet in (("where", "filter"), ("group_by", "grouping")):
            if marker.search(old[field] or "") or marker.search(new[field] or ""):
                facets.append(facet)
                if field == "where":
                    facets.append("time")
    if old["raw_sql"] == new["raw_sql"]:
        edit = "identical_branch_source"
    elif nontrivia(old["raw_sql"]) == nontrivia(new["raw_sql"]):
        edit = "trivia_only_branch_edit"
    else:
        edit = "nontrivia_branch_edit"
    if edit == "nontrivia_branch_edit" and not facets:
        facets.append("unclassified_direct_edit")
    return {"branch_source_edit": edit, "changed_facets": sorted(set(facets)),
            "interpretation": "Source-text comparison only; no runtime equivalence claim"}


def upstream(start: str | None, models: dict[str, dict], seeds: dict[str, str], commit: str,
             branch_loc: dict | None) -> tuple[list[dict], list[dict]]:
    names = defaultdict(list)
    for path, info in models.items():
        names[info["name"]].append(path)
    seed_names = defaultdict(list)
    for path in seeds:
        seed_names[Path(path).stem].append(path)
    if not start or len(names[start]) != 1:
        return [], [{"reference": start, "from_location": branch_loc,
                     "reason": "Missing, ambiguous or unsupported branch source ref"}]
    path = names[start][0]
    found = [{"model_path": path, "depth": 0, "via_model_path": MODEL,
              "via_ref_location": branch_loc}]
    unresolved = []
    seen = {path}
    queue = deque([(path, 0)])
    while queue:
        current, depth = queue.popleft()
        for ref in models[current]["refs"]:
            loc = location(commit, current, ref["line"])
            targets = names[ref["model"]]
            if len(targets) == 0 and len(seed_names[ref["model"]]) == 1:
                found.append({"model_path": seed_names[ref["model"]][0], "kind": "seed_ref",
                              "depth": depth + 1, "via_model_path": current,
                              "via_ref_location": loc})
            elif len(targets) != 1 or seed_names[ref["model"]]:
                unresolved.append({"reference": ref["model"], "from_location": loc,
                                   "reason": "Missing or ambiguous model ref"})
            elif targets[0] not in seen:
                target = targets[0]
                seen.add(target)
                found.append({"model_path": target, "depth": depth + 1,
                              "via_model_path": current,
                              "via_ref_location": loc})
                queue.append((target, depth + 1))
        unresolved.extend({"reference": ref["expression"],
                           "from_location": location(commit, current, ref["line"]),
                           "reason": "Unsupported ref syntax"}
                          for ref in models[current]["unsupported_refs"])
    return found, unresolved


def ref_path(walk: list[dict], target: str) -> list[dict]:
    """Reconstruct the shortest declared-ref chain from the metric SQL to target."""
    nodes = {item["model_path"]: item for item in walk}
    chain = []
    current = target
    seen = set()
    while current != MODEL:
        if current not in nodes or current in seen:
            raise ValueError(f"Broken or cyclic ref path to {target}")
        seen.add(current)
        item = nodes[current]
        chain.append({"from_model_path": item["via_model_path"], "to_source_path": current,
                      "ref_location": item["via_ref_location"]})
        current = item["via_model_path"]
    return list(reversed(chain))


def potential_consumers(repo: Path, commit: str, models: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Model ref paths plus direct test refs and narrow exposure depends_on refs."""
    seed_names = {Path(p).stem for p in versions.git(repo, "ls-tree", "-r", "--name-only",
                                                      commit, "--", "seeds").splitlines()
                  if p.startswith("seeds/") and p.endswith(".csv")}
    reverse, unresolved, _ = versions.dependents(models, seed_names)
    found = [{"kind": "model_ref", "model_path": item["model_path"], "depth": item["depth"],
              "via_model_path": item["edge_from"],
              "ref_location": location(commit, item["model_path"], item["source_line"])}
             for item in versions.transitive_dependents(MODEL, reverse)]
    issues = [{"reason": x["reason"], "evidence": x} for x in unresolved]
    for path in versions.git(repo, "ls-tree", "-r", "--name-only", commit, "--", "tests").splitlines():
        if not path.startswith("tests/") or not path.endswith(".sql"):
            continue
        sql = git_text(repo, "show", f"{commit}:{path}")
        refs, unknown = versions.refs(sql)
        found.extend({"kind": "test_ref", "model_path": path, "depth": 1,
                      "ref_location": location(commit, path, ref["line"])}
                     for ref in refs if ref["model"] == Path(MODEL).stem)
        issues.extend({"reason": "Unsupported test ref syntax", "evidence": {
            "location": location(commit, path, ref["line"]), "expression": ref["expression"]}}
                      for ref in unknown)
    paths = versions.git(repo, "ls-tree", "-r", "--name-only", commit, "--", EXPOSURES).splitlines()
    if EXPOSURES in paths:
        name = None
        for line_number, line in enumerate(git_text(repo, "show", f"{commit}:{EXPOSURES}").splitlines(), 1):
            matched_name = re.match(r"\s*- name:\s*([A-Za-z_]\w*)\s*$", line)
            if matched_name:
                name = matched_name[1]
            if "depends_on:" in line and not line.lstrip().startswith("#"):
                for match in BARE_REF.finditer(line.split("#", 1)[0]):
                    if match[2] == Path(MODEL).stem:
                        found.append({"kind": "exposure_ref", "name": name, "model_path": EXPOSURES,
                                      "depth": 1, "ref_location": location(commit, EXPOSURES, line_number)})
    return found, issues


def assess_branch(direct: dict, whole_model_edit: str, relevant: list[dict],
                  unresolved_by_commit: dict[str, list[dict]]) -> dict:
    """Classify source evidence while explicitly accounting for incomplete refs."""
    unclassified_model_edit = whole_model_edit == "nontrivia_source_edit" and not direct["changed_facets"]
    detected_change = bool(direct["changed_facets"]) or unclassified_model_edit or any(
        edit["status"] in ("nontrivia_source_edit", "seed_data_source_edit",
                           "added_source", "removed_source") for edit in relevant)
    incomplete = any(unresolved_by_commit.values())
    if detected_change:
        assessment = "potential_metric_change"
        basis = "Direct facet/model edit or changed upstream source on a declared ref path; row effect unknown."
        if incomplete:
            basis += " Incomplete upstream refs in at least one commit; additional changes cannot be ruled out."
    else:
        assessment = "abstention"
        if incomplete:
            basis = ("No change detected on inspected source paths, but missing, ambiguous or unsupported "
                     "upstream refs in at least one commit force abstention; absence of metric change "
                     "cannot be inferred.")
        else:
            basis = ("No direct or nontrivia upstream source edit detected on supported resolved ref paths; "
                     "runtime behavior remains unverified.")
    return {"assessment": assessment, "assessment_qualifier": (
                "incomplete_upstream" if incomplete else "supported_upstream_refs_resolved"),
            "upstream_incomplete": incomplete, "unclassified_model_sql_edit": unclassified_model_edit,
            "assessment_basis": basis}


def analyze(repo: Path) -> dict:
    if git_text(repo, "rev-parse", f"{AFTER}^").strip() != BEFORE:
        raise ValueError("Pinned commits must be adjacent parent and child")
    models = {commit: read_models(repo, commit) for commit in (BEFORE, AFTER)}
    seeds = {commit: read_seeds(repo, commit) for commit in (BEFORE, AFTER)}
    snapshots = {commit: source_branches(commit, models[commit][MODEL]["sql"])
                 for commit in (BEFORE, AFTER)}
    source_edits = {path: source_comparison(BEFORE, AFTER, path,
                    models[BEFORE][path]["sql"] if path in models[BEFORE] else seeds[BEFORE].get(path),
                    models[AFTER][path]["sql"] if path in models[AFTER] else seeds[AFTER].get(path))
                    for path in sorted(models[BEFORE].keys() | models[AFTER].keys() |
                                       seeds[BEFORE].keys() | seeds[AFTER].keys())}
    indexed = {commit: branch_index(snapshots[commit]) for commit in (BEFORE, AFTER)}
    old, old_issues = indexed[BEFORE]
    new, new_issues = indexed[AFTER]
    consumers = {}
    consumer_issues = {}
    for commit in (BEFORE, AFTER):
        consumers[commit], consumer_issues[commit] = potential_consumers(repo, commit, models[commit])
    pairs = []
    for metric_name, grain in sorted(old.keys() & new.keys()):
        left, right = old[(metric_name, grain)], new[(metric_name, grain)]
        direct = direct_change(left, right)
        paths = {}
        unresolved = {}
        for commit, entry in ((BEFORE, left), (AFTER, right)):
            paths[commit], unresolved[commit] = upstream(entry["source_ref"], models[commit],
                                                       seeds[commit], commit, entry["source_ref_location"])
        upstream_names = {x["model_path"] for version_paths in paths.values() for x in version_paths}
        relevant = [source_edits[p] for p in sorted(upstream_names)
                    if source_edits[p]["status"] != "identical_source"]
        whole_model_edit = source_edits[MODEL]["status"]
        decision = assess_branch(direct, whole_model_edit, relevant, unresolved)
        change_paths = [{"changed_source_path": e["model_path"],
                         "source_edit": e["status"],
                         "after_ref_chain": ref_path(paths[AFTER], e["model_path"])}
                        for e in relevant if e["status"] in (
                            "nontrivia_source_edit", "seed_data_source_edit", "added_source")
                        and e["model_path"] in {p["model_path"] for p in paths[AFTER]}]
        pairs.append({"id": {"metric_name": metric_name, "grain": grain},
                      "before_ordinal": left["ordinal"], "after_ordinal": right["ordinal"],
                      "before_location": left["location"], "after_location": right["location"],
                      "before_source_ref": left["source_ref"], "after_source_ref": right["source_ref"],
                      "direct_change": direct, "whole_model_source_edit": whole_model_edit,
                      "upstream_paths_by_commit": paths, "upstream_source_edits": relevant,
                      "potential_change_ref_paths": change_paths,
                      "unresolved_upstream_refs_by_commit": unresolved,
                      "potential_downstream_consumers_by_commit": consumers,
                      **decision})
    unmatched = {}
    for commit, one, other, problems in ((BEFORE, old, new, old_issues),
                                         (AFTER, new, old, new_issues)):
        unmatched[commit] = {"unique_ids_without_counterpart": [
            {"metric_name": key[0], "grain": key[1], "location": one[key]["location"]}
            for key in sorted(one.keys() - other.keys())], "unresolved_or_ambiguous": problems}
    seed_summary = {commit: {"occurrences_across_branch_walks": sum(
        item.get("kind") == "seed_ref" for pair in pairs
        for item in pair["upstream_paths_by_commit"][commit]),
                             "unique_seed_paths": sorted({item["model_path"] for pair in pairs
                                                          for item in pair["upstream_paths_by_commit"][commit]
                                                          if item.get("kind") == "seed_ref"})}
                    for commit in (BEFORE, AFTER)}
    return {"scope": "Pinned adjacent GTM Git objects; one long-format metric model; declared ref paths",
            "before_commit": BEFORE, "after_commit": AFTER, "model_path": MODEL,
            "model_sql_file_counts": {BEFORE: len(models[BEFORE]), AFTER: len(models[AFTER])},
            "source_comparison": source_edits[MODEL],
            "negative_control": {"observation": "fct_metric_values.sql has no source diff",
                                 "exact_git_blob_identity": git_bytes(repo, "rev-parse", f"{BEFORE}:{MODEL}") ==
                                 git_bytes(repo, "rev-parse", f"{AFTER}:{MODEL}"),
                                 "interpretation": "Source identity, not runtime equivalence"},
            "by_source": [snapshots[BEFORE], snapshots[AFTER]], "linked_branches": pairs,
            "unmatched_branches_by_commit": unmatched,
            "resolved_seed_refs_by_commit": seed_summary,
            "potential_model_consumers_by_commit": consumers,
            "unresolved_consumer_refs_by_commit": consumer_issues,
            "relevant_upstream_source_edits": [source_edits[path] for path in sorted({
                edit["model_path"] for pair in pairs for edit in pair["upstream_source_edits"]})],
            "counts": {"branches_before": len(snapshots[BEFORE]["branches"]),
                       "branches_after": len(snapshots[AFTER]["branches"]),
                       "stable_explicit_id_links": len(pairs),
                       "potential_metric_change": sum(p["assessment"] == "potential_metric_change" for p in pairs),
                       "abstention": sum(p["assessment"] == "abstention" for p in pairs),
                       "incomplete_upstream_pairs": sum(p["upstream_incomplete"] for p in pairs)},
            "assessment_policy": {
                "no_detected_change_with_unresolved_refs":
                    "abstention with incomplete_upstream qualifier; missing/ambiguous/unsupported refs "
                    "cannot establish absence of change",
                "detected_change_with_unresolved_refs":
                    "potential_metric_change with incomplete_upstream qualifier; unresolved refs may "
                    "hide additional changes",
                "detected_change_with_resolved_refs": "potential_metric_change, never observed row impact",
                "no_detected_change_with_resolved_refs": "abstention, never runtime equivalence"},
            "assessment_denominator": "Unique explicit ID links in this one supported metric model (11), "
                                      "each checked against two source snapshots and their declared ref paths; "
                                      "not an exhaustive classification of row or dashboard impact",
            "limits": ["Source comparison ignores only comments and whitespace outside strings/Jinja; "
                       "token equality does not prove behavior or metric equivalence.",
                       "Nontrivia upstream tokens may be harmless SQL refactors; seed CSV refs are terminal "
                       "and compared by source identity. Every declared ref path is relation-level, "
                       "with no field-level lineage.",
                       "dbt/Jinja macros, vars, GROUPING SETS and runtime data are not expanded or executed.",
                       "Only literal unique (metric_name, grain) IDs in the supported UNION ALL model are linked; "
                       "unrecognized and duplicate IDs remain unresolved.",
                       "Model and test ref() syntax is narrow; exposure refs use inline depends_on declarations. "
                       "These are potential consumers of the whole model, not proof of branch-specific use.",
                       "Missing, ambiguous or unsupported upstream refs force an incomplete-upstream qualifier; "
                       "source comparison cannot rule out changes beyond a broken declared path.",
                       "No observed row impact, tested semantic equivalence, dashboard usage, or held-out evaluation. "
                       "The earlier Rill real-change control is separate."]}


def link(loc: dict | None, label: str | None = None) -> str:
    if loc is None:
        return "—"
    path, commit = loc["path"], loc["commit"]
    start, end = loc["start_line"], loc["end_line"]
    caption = label or f"{path}:{start}" + (f"–{end}" if end != start else "")
    anchor = f"#L{start}" + (f"-L{end}" if end != start else "")
    return f"[{caption}]({BASE_URL}/blob/{commit}/{quote(path)}{anchor})"


def markdown(report: dict) -> str:
    counts = report["counts"]
    lines = ["# Versioned GTM dbt metric branches", "",
             f"Parent `{BEFORE}` → child `{AFTER}`. "
             f"Exact Git blob identity for `{MODEL}`: **{report['negative_control']['exact_git_blob_identity']}**. "
             "This is a negative control for direct metric SQL edits, not runtime equivalence.", "",
             f"{counts['branches_before']} and {counts['branches_after']} individual UNION ALL branches; "
             f"{counts['stable_explicit_id_links']} unique literal `(metric_name, grain)` links; "
             f"{counts['potential_metric_change']} potential changes through declared sources and "
             f"{counts['abstention']} abstentions. No observed row impact is claimed.", "",
             f"Denominator: {report['assessment_denominator']}.", "",
             "## Assessment rule", "",
             "If a branch has missing, ambiguous or unsupported upstream `ref()` edges in either commit, "
             "its upstream evidence is marked `incomplete_upstream`. With no detected source change, "
             "it is an explicit `abstention`; with a detected direct or reachable source change, "
             "it remains `potential_metric_change` with that incomplete-upstream qualifier. "
             "An unresolved path never establishes the absence of change. "
             f"Here, {counts['incomplete_upstream_pairs']} of {counts['stable_explicit_id_links']} "
             "linked branches have incomplete upstream refs.", "",
             "## Individual source branches and links", "",
             "Every direct branch source is identical at these commits. The upstream column lists "
             "source edits on a declared `ref()` path, including trivia-only edits; "
             "`nontrivia` does not establish a changed result.", "",
             "| Explicit ID | Parent branch | Child branch | Direct facets | Upstream source edits | Assessment |",
             "| --- | --- | --- | --- | --- | --- |"]
    for pair in report["linked_branches"]:
        edits = pair["upstream_source_edits"]
        details = "; ".join(f"{link((e['edit_spans'][0]['after'] or e['after_location']) if e['edit_spans'] else e['after_location'], Path(e['model_path']).stem)} "
                            f"({e['status']})" for e in edits) or "none detected on inspected paths"
        name, grain = pair["id"].values()
        lines.append(f"| `{name}` / `{grain}` | {link(pair['before_location'], 'source')} | "
                     f"{link(pair['after_location'], 'source')} | "
                     f"{', '.join(pair['direct_change']['changed_facets']) or 'none'}; "
                     f"`{pair['direct_change']['branch_source_edit']}` | {details} | "
                     f"`{pair['assessment']}`"
                     f"{' (`incomplete_upstream`)' if pair['upstream_incomplete'] else ''} |")
    lines += ["", "## Source edits and locations", "",
              "The only nontrivia source edit on a linked branch's upstream path is the "
              "explicit alias `AS` in `int_leads__unified.sql`. Its effect on compiled SQL and rows "
              "was not checked. Token-preserving edits are recorded as trivia observations only.", ""]
    for edit in report["relevant_upstream_source_edits"]:
        spans = "; ".join(f"{link(s['before'], 'parent')} → {link(s['after'], 'child')}"
                          for s in edit["edit_spans"])
        lines.append(f"- `{edit['status']}` `{edit['model_path']}`: {spans or 'whole file location in JSON'}.")
    lines += ["", "The changed-token alias line is `from contacts c` → `from contacts as c`. "
              "The following distinct child-revision `ref()` chains lead to that source; "
              "each link points to the referring expression, and all members of a group "
              "share only a model-level potential path:", ""]
    groups = defaultdict(list)
    for pair in report["linked_branches"]:
        for path in pair["potential_change_ref_paths"]:
            signature = tuple((edge["from_model_path"], edge["to_source_path"],
                               edge["ref_location"]["start_line"]) for edge in path["after_ref_chain"])
            groups[signature].append(pair["id"])
    for signature, ids in sorted(groups.items()):
        chain = " → ".join(f"{link(location(AFTER, source, line), Path(source).stem)} "
                            f"`ref('{Path(target).stem}')`" for source, target, line in signature)
        names = ", ".join(f"`{item['metric_name']}/{item['grain']}`" for item in ids)
        lines.append(f"- {names}: {chain}.")
    lines += ["", "## Potential downstream `ref()` consumers", "",
              "These references are to the whole metric model; they do not establish use of any "
              "particular branch. The JSON attaches this inventory to every linked branch at both commits.", ""]
    for commit in (BEFORE, AFTER):
        lines.append(f"**`{commit}`**")
        lines.append("")
        for item in report["potential_model_consumers_by_commit"][commit]:
            description = item.get("name", item["model_path"])
            lines.append(f"- `{item['kind']}` {description}: {link(item['ref_location'])} "
                         f"(depth {item['depth']}).")
        if not report["potential_model_consumers_by_commit"][commit]:
            lines.append("- No supported `ref()` consumer found.")
        lines.append("")
    lines += ["## Unresolved evidence and limits", ""]
    for commit in (BEFORE, AFTER):
        pending = report["unmatched_branches_by_commit"][commit]
        unresolved_refs = sum(len(p["unresolved_upstream_refs_by_commit"][commit])
                              for p in report["linked_branches"])
        lines.append(f"- `{commit}`: {len(pending['unique_ids_without_counterpart'])} unmatched unique IDs, "
                     f"{len(pending['unresolved_or_ambiguous'])} unsupported/ambiguous branches, "
                     f"{unresolved_refs} unresolved upstream refs on linked paths, "
                     f"{len(report['unresolved_consumer_refs_by_commit'][commit])} unresolved consumer refs. "
                     "Details and raw unsupported SQL remain in JSON.")
        seed_info = report["resolved_seed_refs_by_commit"][commit]
        lines.append(f"- `{commit}`: {seed_info['occurrences_across_branch_walks']} resolved seed-ref "
                     f"occurrences across {counts['stable_explicit_id_links']} branch walks, "
                     f"pointing to {len(seed_info['unique_seed_paths'])} unique CSV seed paths. "
                     "Shared dependencies are counted once per branch walk, and seed files are "
                     "terminal source comparisons, not unresolved models.")
    lines.extend(f"- {sentence}" for sentence in report["limits"])
    lines.append("")
    return "\n".join(lines)


def self_check() -> None:
    """Counterfactual parser, pairing and classification checks independent of Git."""
    toy = ("with src as (select * from {{ ref('upstream') }}), unioned as (\n"
           "select 'toy' as metric_name, 'month' as grain, d as period_start, "
           "s as segment, sum(v) as value from src where flag = 1 group by d, s\n"
           ") select metric_name, grain, period_start, segment, value from unioned")

    def one(sql: str) -> dict:
        parsed = source_branches(BEFORE, sql)
        assert parsed["extraction_status"] == "bounded_extraction"
        return parsed["branches"][0]

    base = one(toy)
    assert branch_index({"branches": [base]})[0].keys() == {("toy", "month")}
    assert direct_change(base, one(toy.replace("sum(v)", "sum(v + 1)")))["changed_facets"] == ["value"]
    assert direct_change(base, one(toy.replace("flag = 1", "flag = 2")))["changed_facets"] == ["filter"]
    timed = toy.replace("flag = 1", "d between {{ start_date }} and {{ end_date }}")
    assert direct_change(one(timed), one(timed.replace("end_date", "revised_end")))[
        "changed_facets"] == ["filter", "time"]
    assert direct_change(base, one(toy.replace("d as period_start", "other_d as period_start")))["changed_facets"] == ["time"]
    assert direct_change(base, one(toy.replace("group by d, s", "group by s, d")))["changed_facets"] == ["grouping"]
    assert direct_change(base, one(toy.replace("ref('upstream')", "ref('other')")))["changed_facets"] == ["source"]
    trivia = one(toy.replace("sum(v) as value", "sum( v ) /* note */ as value"))
    assert direct_change(base, trivia)["branch_source_edit"] == "trivia_only_branch_edit"
    assert not direct_change(base, trivia)["changed_facets"]
    duplicate = branch_index({"branches": [base, base]})
    assert not duplicate[0] and len(duplicate[1]) == 2
    unsupported = one(toy.replace("'month' as grain", "'custom' as grain"))
    assert not branch_index({"branches": [unsupported]})[0]
    templated = "{% set window_start = '2025-01-01' %}\n" + toy.replace(
        "d as period_start", "{{ window_start }} as period_start")
    revised = templated.replace("2025-01-01", "2025-02-01")
    assert direct_change(one(templated), one(revised))["changed_facets"] == ["time"]
    assert source_comparison(BEFORE, AFTER, MODEL, toy, toy + "\n-- note")["status"] == "trivia_only_source_edit"
    assert source_comparison(BEFORE, AFTER, MODEL, toy, toy.replace("sum(v)", "sum(v+1)"))["status"] == "nontrivia_source_edit"
    # Exercise the actual graph walk as well as its classification. Either commit
    # can contain the unresolved edge; it must affect the paired assessment.
    missing_models = {"models/upstream.sql": {"name": "upstream",
                                            "refs": [{"model": "absent", "line": 2}],
                                            "unsupported_refs": []}}
    ambiguous_models = {"models/upstream.sql": {"name": "upstream",
                                              "refs": [{"model": "shared", "line": 3}],
                                              "unsupported_refs": []},
                        "models/a/shared.sql": {"name": "shared", "refs": [], "unsupported_refs": []},
                        "models/b/shared.sql": {"name": "shared", "refs": [], "unsupported_refs": []}}
    for commit, models, expected_reference in ((BEFORE, missing_models, "absent"),
                                               (AFTER, ambiguous_models, "shared")):
        _, issues = upstream("upstream", models, {}, commit, base["source_ref_location"])
        assert len(issues) == 1 and issues[0]["reference"] == expected_reference
        unresolved = {BEFORE: issues if commit == BEFORE else [],
                      AFTER: issues if commit == AFTER else []}
        unchanged = assess_branch(direct_change(base, base), "identical_source", [], unresolved)
        assert unchanged["assessment"] == "abstention"
        assert unchanged["assessment_qualifier"] == "incomplete_upstream"
        assert unchanged["upstream_incomplete"] and "cannot be inferred" in unchanged["assessment_basis"]
        upstream_edit = assess_branch(direct_change(base, base), "identical_source",
                                      [{"status": "nontrivia_source_edit"}], unresolved)
        assert upstream_edit["assessment"] == "potential_metric_change"
        assert upstream_edit["assessment_qualifier"] == "incomplete_upstream"
        assert "additional changes cannot be ruled out" in upstream_edit["assessment_basis"]
        value_edit = assess_branch(direct_change(base, one(toy.replace("sum(v)", "sum(v + 1)"))),
                                   "nontrivia_source_edit", [], unresolved)
        assert value_edit["assessment"] == "potential_metric_change"
        assert value_edit["assessment_qualifier"] == "incomplete_upstream"


def check(report: dict, repo: Path, expected_json: str, expected_md: str) -> None:
    self_check()
    snapshots = report["by_source"]
    assert report["negative_control"]["exact_git_blob_identity"]
    assert report["source_comparison"]["status"] == "identical_source"
    assert report["counts"] == {"branches_before": 11, "branches_after": 11,
                                "stable_explicit_id_links": 11,
                                "potential_metric_change": 7, "abstention": 4,
                                "incomplete_upstream_pairs": 0}
    assert all(s["extraction_status"] == "bounded_extraction" and
               s["counts"]["unsupported"] == 0 for s in snapshots)
    for pair in report["linked_branches"]:
        assert not pair["direct_change"]["changed_facets"]
        assert pair["direct_change"]["branch_source_edit"] == "identical_branch_source"
        assert pair["before_location"]["commit"] == BEFORE
        assert pair["after_location"]["commit"] == AFTER
        nontrivia_edits = [e for e in pair["upstream_source_edits"]
                           if e["status"] == "nontrivia_source_edit"]
        assert (pair["assessment"] == "potential_metric_change") == bool(nontrivia_edits)
        if nontrivia_edits:
            assert [Path(e["model_path"]).stem for e in nontrivia_edits] == ["int_leads__unified"]
            assert len(pair["potential_change_ref_paths"]) == 1
            chain = pair["potential_change_ref_paths"][0]["after_ref_chain"]
            assert chain[0]["from_model_path"] == MODEL
            assert chain[-1]["to_source_path"] == nontrivia_edits[0]["model_path"]
        for commit in (BEFORE, AFTER):
            assert not pair["unresolved_upstream_refs_by_commit"][commit]
        assert pair["assessment_qualifier"] == "supported_upstream_refs_resolved"
        assert not pair["upstream_incomplete"]
    consumer_kinds = {c["kind"] for c in report["potential_model_consumers_by_commit"][AFTER]}
    assert {"model_ref", "test_ref", "exposure_ref"}.issubset(consumer_kinds)
    assert not any(report["unmatched_branches_by_commit"][c]["unresolved_or_ambiguous"]
                   for c in (BEFORE, AFTER))
    for commit in (BEFORE, AFTER):
        summary = report["resolved_seed_refs_by_commit"][commit]
        assert summary["occurrences_across_branch_walks"] == 97
        assert len(summary["unique_seed_paths"]) == 9
    alias = next(e for e in report["relevant_upstream_source_edits"]
                 if e["model_path"].endswith("/int_leads__unified.sql"))
    assert alias["edit_spans"] == [{"operation": "replace",
                                    "before": location(BEFORE, alias["model_path"], 27),
                                    "after": location(AFTER, alias["model_path"], 27)}]
    assert "from contacts c" in git_text(repo, "show", f"{BEFORE}:{alias['model_path']}").splitlines()[26]
    assert "from contacts as c" in git_text(repo, "show", f"{AFTER}:{alias['model_path']}").splitlines()[26]
    assert git_text(repo, "diff", "--name-only", BEFORE, AFTER, "--", MODEL).strip() == ""
    if JSON_PATH.read_text(encoding="utf-8") != expected_json or MD_PATH.read_text(encoding="utf-8") != expected_md:
        raise AssertionError("Saved reports differ from regenerated pinned-source analysis")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO, help="local checkout with the two pinned GTM commits")
    parser.add_argument("--self-check", action="store_true", help="run synthetic boundary tests only")
    parser.add_argument("--check", action="store_true", help="self-check, pinned assertions and saved report comparison")
    args = parser.parse_args()
    if args.self_check and not args.check:
        self_check()
        print("Synthetic branch checks passed")
        return
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        parser.error("--repo must be a Git checkout")
    report = analyze(repo)
    json_out = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    md_out = markdown(report)
    if args.check:
        check(report, repo, json_out, md_out)
        print("Pinned GTM branch and saved-report checks passed:", report["counts"])
    else:
        JSON_PATH.write_text(json_out, encoding="utf-8")
        MD_PATH.write_text(md_out, encoding="utf-8")
        print("Wrote versioned GTM branch reports:", report["counts"])


if __name__ == "__main__":
    main()
