#!/usr/bin/env python3
"""Bounded, evidence-only field provenance for the pinned GTM compiled metric model.

The source branch extractor supplies source locations. This script checks the dbt
manifest against the compiled files, links branches by unique literal identities,
and walks a small SELECT/CTE/UNION subset. An unresolved owner, join, star, macro,
or depth limit is retained as a review stop, never guessed from a dbt dependency.
No SQL is run and no metric equivalence or numerical correctness is inferred.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import extract_dbt_metric_branches as pilot


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "public_corpus" / "gtm-funnel-analytics"
MANIFEST = "target/manifest.json"
JSON_REPORT = ROOT / "compiled_metric_fields_report.json"
MD_REPORT = ROOT / "compiled_metric_fields_report.md"
MAX_MODEL_HOPS = 6
MAX_CTE_HOPS = 10
MAX_NODES = 48  # per root field; a bound on expanding derived expressions
IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
LITERAL = re.compile(r"'((?:''|[^'])*)'\Z", re.S)
KEYWORDS = set("""as and or not is null true false case when then else end in between like
    ilike distinct filter where within group order by asc desc over partition rows range
    current row unbounded preceding following cast try_cast date timestamp double float
    decimal integer int bigint boolean varchar string interval extract from select union all
    on join left right inner full cross outer having qualify limit grouping sets
    month day minute year epoch with recursive""".split())
JOIN_WORDS = {"left", "right", "inner", "full", "cross", "outer", "join"}


class Stop(ValueError):
    """A deliberately unsupported provenance edge."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def loc(source: pilot.Source, tokens: list[pilot.Token], path: str) -> dict | None:
    place = source.location(tokens)
    return {**place, "path": path} if place else None


def raw(source: pilot.Source, tokens: list[pilot.Token]) -> str:
    return source.raw(tokens)


def clauses(tokens: list[pilot.Token]) -> dict[str, list[pilot.Token]]:
    """Top-level SELECT clauses. JOIN is confined to FROM and parsed separately."""
    if not tokens or not pilot.word(tokens[0], "select"):
        raise Stop("unsupported_query_not_select")
    boundaries, depth = [], 0
    for i in range(1, len(tokens)):
        t = tokens[i]
        if t.value == "(":
            depth += 1
        elif t.value == ")":
            depth -= 1
        elif depth == 0 and t.kind == "word":
            key = t.value.lower()
            if key in {"from", "where", "having", "limit", "qualify"}:
                boundaries.append((i, key, 1))
            elif key in {"group", "order"} and i + 1 < len(tokens) and pilot.word(tokens[i + 1], "by"):
                boundaries.append((i, key + " by", 2))
        if depth < 0:
            raise Stop("unbalanced_query")
    if depth or not boundaries or boundaries[0][1] != "from":
        raise Stop("unsupported_query_clauses")
    names = [b[1] for b in boundaries]
    if len(names) != len(set(names)) or names != [k for k in
            ("from", "where", "group by", "having", "order by", "limit", "qualify") if k in names]:
        raise Stop("unsupported_query_clauses")
    result = {"select": tokens[1:boundaries[0][0]]}
    for i, (at, key, width) in enumerate(boundaries):
        result[key] = tokens[at + width:boundaries[i + 1][0] if i + 1 < len(boundaries) else len(tokens)]
        if not result[key]:
            raise Stop("empty_clause")
    if set(result) - {"select", "from", "where", "group by"}:
        raise Stop("unsupported_query_clause")
    return result


def outputs(source: pilot.Source, tokens: list[pilot.Token]) -> tuple[list[dict], list[str]]:
    result, stars = [], []
    for part in pilot.split_top(tokens, ","):
        expr = part
        alias = None
        if len(part) >= 3 and pilot.word(part[-2], "as") and part[-1].kind == "word":
            alias, expr = part[-1].value.lower(), part[:-2]
        elif len(part) == 1 and part[0].kind == "word":
            alias = part[0].value.lower()
        elif (len(part) == 3 and part[0].kind == "word" and part[1].value == "."
              and part[2].kind == "word"):
            alias = part[2].value.lower()
        value = raw(source, expr)
        if value == "*" or re.fullmatch(r"[A-Za-z_]\w*\.\*", value):
            stars.append(value)
        result.append({"name": alias, "expression": value, "tokens": expr, "location_tokens": part})
    return result, stars


def field_refs(tokens: list[pilot.Token], source: pilot.Source, path: str) -> tuple[list[dict], bool]:
    """Find lexical column uses, excluding function names, types, literals and SQL words.

    It is intentionally NOT a general SQL parser: a subquery, Jinja or an unknown
    token shape stops the edge instead of producing a field-level assertion.
    """
    refs, seen, count_star = [], set(), False
    for i, t in enumerate(tokens):
        if t.kind == "jinja" or pilot.word(t, "select"):
            raise Stop("macro_or_subquery_in_expression")
        if (t.value == "*" and i >= 2 and tokens[i - 1].value == "("
                and pilot.word(tokens[i - 2], "count")):
            count_star = True
        if t.kind != "word":
            continue
        name = t.value.lower()
        prev = tokens[i - 1].value.lower() if i else ""
        following = tokens[i + 1].value if i + 1 < len(tokens) else ""
        if name in KEYWORDS or following in {"(", "."} or prev in {"::", "as"}:
            continue
        qualifier, start = None, i
        if prev == "." and i >= 2 and tokens[i - 2].kind == "word":
            qualifier, start = tokens[i - 2].value.lower(), i - 2
        key = (qualifier, name)
        if key not in seen:
            seen.add(key)
            refs.append({"qualifier": qualifier, "field": name,
                         "location": loc(source, tokens[start:i + 1], path)})
    return refs, count_star


def from_sources(tokens: list[pilot.Token], source: pilot.Source, path: str) -> tuple[dict, list[dict]]:
    """Only named CTEs or three-part compiled relations with optional aliases/ON."""
    pos, sources, joins = 0, {}, []

    def relation(at: int) -> tuple[dict, int]:
        start = at
        parts = []
        while at < len(tokens) and tokens[at].kind in {"word", "string"}:
            t = tokens[at]
            if t.kind == "string" and not t.value.startswith('"'):
                break
            parts.append(t.value.strip('"').lower())
            at += 1
            if at < len(tokens) and tokens[at].value == ".":
                at += 1
                continue
            break
        if len(parts) not in (1, 3) or not all(IDENT.fullmatch(p) for p in parts):
            raise Stop("unsupported_from_relation")
        relation_name = ".".join(parts)
        alias = parts[-1]
        if at < len(tokens) and pilot.word(tokens[at], "as"):
            at += 1
            if at >= len(tokens) or tokens[at].kind != "word":
                raise Stop("unsupported_from_alias")
            alias = tokens[at].value.lower()
            at += 1
        elif at < len(tokens) and tokens[at].kind == "word" and tokens[at].value.lower() not in JOIN_WORDS | {"on"}:
            alias = tokens[at].value.lower()
            at += 1
        return {"name": relation_name, "alias": alias, "location": loc(source, tokens[start:at], path)}, at

    first, pos = relation(pos)
    sources[first["alias"]] = first
    while pos < len(tokens):
        if tokens[pos].value == ",":
            raise Stop("comma_join_ambiguous")
        join_start = pos
        while pos < len(tokens) and tokens[pos].kind == "word" and tokens[pos].value.lower() in JOIN_WORDS - {"join"}:
            pos += 1
        if pos >= len(tokens) or not pilot.word(tokens[pos], "join"):
            raise Stop("unsupported_join_syntax")
        pos += 1
        item, pos = relation(pos)
        if item["alias"] in sources:
            raise Stop("duplicate_from_alias")
        sources[item["alias"]] = item
        if pos >= len(tokens) or not pilot.word(tokens[pos], "on"):
            raise Stop("join_without_on")
        pos += 1
        pred_start, depth = pos, 0
        while pos < len(tokens):
            if tokens[pos].value == "(":
                depth += 1
            elif tokens[pos].value == ")":
                depth -= 1
            if depth == 0 and tokens[pos].kind == "word" and tokens[pos].value.lower() in JOIN_WORDS:
                break
            pos += 1
        if pos == pred_start or depth:
            raise Stop("unsupported_join_predicate")
        joins.append({"expression": raw(source, tokens[pred_start:pos]),
                      "location": loc(source, tokens[join_start:pos], path)})
    return sources, joins


def normalized_relation(name: str) -> str:
    return name.replace('"', "").lower()


class Tracer:
    def __init__(self, repo: Path, manifest: dict):
        self.repo, self.manifest = repo, manifest
        self.nodes = manifest["nodes"]
        self.by_relation = {normalized_relation(n["relation_name"]): key for key, n in self.nodes.items()
                            if n.get("relation_name")}
        self.parsed = {}
        self.artifacts = {}

    def model(self, model_id: str) -> dict:
        if model_id in self.parsed:
            return self.parsed[model_id]
        node = self.nodes.get(model_id)
        if not node or node.get("resource_type") != "model" or not node.get("compiled_path"):
            raise Stop("model_compiled_sql_unavailable")
        path = node["compiled_path"]
        if Path(path).is_absolute() or ".." in Path(path).parts or not path.startswith("target/compiled/"):
            raise Stop("compiled_path_outside_target")
        content = (self.repo / path).read_bytes()
        sql = content.decode("utf-8")
        if sql.strip() != node.get("compiled_code", "").strip():
            raise Stop("manifest_compiled_code_mismatch")
        self.artifacts[model_id] = {"path": path, "sha256": digest(content),
                                    "manifest_compiled_code_matches_file_after_strip": True}
        source = pilot.Source(sql)
        if source.tokens and pilot.word(source.tokens[0], "with"):
            ctes, final, _ = pilot.ctes(source)
        else:
            ctes, final = {}, source.tokens
        parsed = {"source": source, "path": path, "ctes": ctes, "final": final}
        self.parsed[model_id] = parsed
        return parsed

    def target(self, model_id: str, relation: dict, ctes: dict) -> tuple[str, str]:
        name = relation["name"]
        if name in ctes:
            return "cte", name
        target = self.by_relation.get(name)
        if not target or target not in self.nodes[model_id].get("depends_on", {}).get("nodes", []):
            raise Stop("relation_not_declared_manifest_dependency")
        return self.nodes[target]["resource_type"], target

    def walk(self, model_id: str, field: str, *, stage: str | None = None) -> dict:
        budget = {"nodes": 0}
        return self._walk(model_id, "final", field, stage, 0, 0, set(), budget)

    def _walk(self, model_id: str, scope: str, field: str, stage: str | None,
              models: int, ctes: int, seen: set, budget: dict) -> dict:
        budget["nodes"] += 1
        if budget["nodes"] > MAX_NODES or models > MAX_MODEL_HOPS or ctes > MAX_CTE_HOPS:
            return {"field": field, "status": "needs_review", "stop": "trace_bound_reached"}
        key = (model_id, scope, field, stage)
        if key in seen:
            return {"field": field, "status": "needs_review", "stop": "cycle"}
        seen = seen | {key}
        try:
            parsed = self.model(model_id)
            source, path = parsed["source"], parsed["path"]
            tokens = parsed["final"] if scope == "final" else parsed["ctes"][scope]["body"]
            parts = pilot.union_parts(tokens)
            if len(parts) > 1:
                if not stage:
                    raise Stop("union_field_without_discriminator")
                candidates = []
                for part in parts:
                    q = clauses(part)
                    projections, _ = outputs(source, q["select"])
                    stage_positions = [i for i, p in enumerate(projections) if p["name"] == "stage"]
                    if len(stage_positions) != 1:
                        raise Stop("union_stage_ambiguous")
                    match = LITERAL.fullmatch(projections[stage_positions[0]]["expression"])
                    if match and match[1].replace("''", "'") == stage:
                        candidates.append(part)
                if len(candidates) != 1:
                    raise Stop("union_stage_ambiguous")
                tokens = candidates[0]
            q = clauses(tokens)
            projections, stars = outputs(source, q["select"])
            sources, joins = from_sources(q["from"], source, path)
            matches = [p for p in projections if p["name"] == field]
            if len(matches) > 1:
                raise Stop("duplicate_field_declaration")
            if matches:
                selected = matches[0]
                if stars:
                    raise Stop("explicit_field_with_star_ambiguous")
                expr = selected["expression"]
                expr_tokens = selected["tokens"]
                declaration = loc(source, selected["location_tokens"], path)
                refs, _ = field_refs(expr_tokens, source, path)
            else:
                if len(stars) != 1 or len(sources) != 1 or joins:
                    raise Stop("ambiguous_or_missing_star_field")
                star = stars[0]
                if star != "*" and star.split(".")[0] not in sources:
                    raise Stop("unresolved_qualified_star")
                expr = star
                expr_tokens = []
                declaration = loc(source, next(p["location_tokens"] for p in projections
                                               if p["expression"] == star), path)
                refs = [{"field": field, "qualifier": None, "location": declaration}]
            result = {"model": model_id, "scope": scope, "field": field,
                      "expression": expr, "location": declaration, "inputs": []}
            if joins:
                result["join"] = joins
                result["review_flags"] = ["join_cardinality_unchecked"]
            if q.get("where"):
                result["row_filter"] = {"expression": raw(source, q["where"]),
                                        "location": loc(source, q["where"], path)}
            if q.get("group by"):
                result["group_by"] = {"expression": raw(source, q["group by"]),
                                      "location": loc(source, q["group by"], path)}
                if re.search(r"\bgrouping\s+sets\b", result["group_by"]["expression"], re.I):
                    result.setdefault("review_flags", []).append("grouping_sets_not_expanded")
            if ("date_diff(" in expr.lower() and
                    self.nodes[model_id].get("depends_on", {}).get("macros")):
                result.setdefault("review_flags", []).append("compiled_macro_expression_requires_review")
            for ref in refs:
                alias = ref["qualifier"]
                if alias is None:
                    if len(sources) != 1:
                        child = {"field": ref["field"], "status": "needs_review",
                                 "stop": "unqualified_field_in_join"}
                        result["inputs"].append({"use": ref, "trace": child})
                        continue
                    alias = next(iter(sources))
                if alias not in sources:
                    child = {"field": ref["field"], "status": "needs_review",
                             "stop": "unresolved_qualifier"}
                else:
                    try:
                        kind, target = self.target(model_id, sources[alias], parsed["ctes"])
                        if kind == "cte":
                            child = self._walk(model_id, target, ref["field"], stage,
                                               models, ctes + 1, seen, budget)
                        elif kind == "model":
                            child = self._walk(target, "final", ref["field"], None,
                                               models + 1, ctes, seen, budget)
                        elif kind == "seed":
                            seed = self.nodes[target]
                            seed_path = self.repo / seed["original_file_path"]
                            with seed_path.open(newline="", encoding="utf-8-sig") as f:
                                header = next(csv.reader(f))
                            if ref["field"] not in [h.lower() for h in header]:
                                raise Stop("seed_header_field_missing")
                            child = {"status": "seed_header_field", "field": ref["field"],
                                     "seed": target, "location": {"path": seed["original_file_path"],
                                                                     "start_line": 1, "end_line": 1}}
                        else:
                            raise Stop("unsupported_dependency_resource")
                    except (Stop, pilot.Unsupported, OSError, UnicodeError, StopIteration) as exc:
                        child = {"field": ref["field"], "status": "needs_review", "stop": str(exc)}
                result["inputs"].append({"use": ref, "relation": sources[alias], "trace": child})
            result["status"] = "needs_review" if (result.get("review_flags") or
                        any(has_review(x["trace"]) for x in result["inputs"])) else "traced"
            return result
        except (Stop, pilot.Unsupported, KeyError, OSError, UnicodeError) as exc:
            return {"model": model_id, "scope": scope, "field": field,
                    "status": "needs_review", "stop": str(exc)}

    def immediate_filter(self, model_id: str) -> dict | None:
        """Record the immediate model's row predicate and trace its named fields."""
        try:
            parsed = self.model(model_id)
            q = clauses(parsed["final"])
            if not q.get("where"):
                return None
            source, path = parsed["source"], parsed["path"]
            refs, _ = field_refs(q["where"], source, path)
            sources, joins = from_sources(q["from"], source, path)
            result = {"expression": raw(source, q["where"]),
                      "location": loc(source, q["where"], path), "fields": []}
            if joins:
                result["review_flags"] = ["join_cardinality_unchecked"]
            for ref in refs:
                alias = ref["qualifier"] or (next(iter(sources)) if len(sources) == 1 else None)
                if alias is None or alias not in sources:
                    child = {"field": ref["field"], "status": "needs_review", "stop": "unqualified_field_in_join"}
                else:
                    kind, target = self.target(model_id, sources[alias], parsed["ctes"])
                    child = self._walk(model_id if kind == "cte" else target,
                                       target if kind == "cte" else "final", ref["field"],
                                       None, 0 if kind == "cte" else 1, 1 if kind == "cte" else 0,
                                       set(), {"nodes": 0}) if kind in {"cte", "model"} else {
                                           "field": ref["field"], "status": "needs_review",
                                           "stop": "direct_seed_filter_not_traced"}
                result["fields"].append({"use": ref, "trace": child})
            return result
        except (Stop, pilot.Unsupported, OSError, KeyError) as exc:
            return {"status": "needs_review", "stop": str(exc)}


def has_review(tree: dict) -> bool:
    return tree.get("status") == "needs_review" or bool(tree.get("review_flags")) or any(
        has_review(i["trace"]) for i in tree.get("inputs", []))


def walk_nodes(tree: dict):
    yield tree
    for item in tree.get("inputs", []):
        yield from walk_nodes(item["trace"])


def projection_location(sql: str, ordinal: int, column: int, path: str) -> dict:
    source = pilot.Source(sql)
    ctes, _, _ = pilot.ctes(source)
    branch = pilot.union_parts(ctes["unioned"]["body"])[ordinal - 1]
    q = clauses(branch)
    part = pilot.split_top(q["select"], ",")[column]
    return loc(source, part, path)


def build(repo: Path) -> dict:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != pilot.COMMIT:
        raise Stop(f"checkout HEAD {head} differs from pinned {pilot.COMMIT}")
    source_sql = subprocess.run(["git", "-C", str(repo), "show", f"{pilot.COMMIT}:{pilot.MODEL}"],
                                check=True, capture_output=True).stdout.decode("utf-8")
    working_source = (repo / pilot.MODEL).read_bytes()
    if working_source != source_sql.encode("utf-8"):
        raise Stop("working_source_differs_from_pinned_git_object")
    source_report = json.loads((ROOT / "dbt_metric_branches_report.json").read_text(encoding="utf-8"))
    if source_report["source"]["commit"] != head or source_report["branches"] != pilot.extract(source_sql)["branches"]:
        raise Stop("source_branch_report_does_not_match_pinned_git_object")
    manifest_data = (repo / MANIFEST).read_bytes()
    manifest = json.loads(manifest_data)
    tracer = Tracer(repo, manifest)
    metric_id = "model.arcline.fct_metric_values"
    parsed = tracer.model(metric_id)
    compiled_path = parsed["path"]
    compiled_sql = parsed["source"].sql
    compiled = pilot.extract(compiled_sql)
    source_branches = source_report["branches"]
    compiled_branches = compiled["branches"]
    identities = Counter((b.get("metric_name"), b.get("grain"), b.get("source_cte"))
                         for b in source_branches)
    compiled_identities = Counter((b.get("metric_name"), b.get("grain"), b.get("source_cte"))
                                  for b in compiled_branches)
    compiled_ctes = parsed["ctes"]
    linked = []
    for s in source_branches:
        key = (s.get("metric_name"), s.get("grain"), s.get("source_cte"))
        matches = [c for c in compiled_branches if
                   (c.get("metric_name"), c.get("grain"), c.get("source_cte")) == key]
        b = {"ordinal": s["ordinal"], "metric_name": s.get("metric_name"), "grain": s.get("grain"),
             "source_branch": s["location"], "alignment": "needs_review", "review_status": "needs_review"}
        if (s["parse_status"] != "extracted" or identities[key] != 1 or compiled_identities[key] != 1
                or len(matches) != 1 or matches[0]["parse_status"] != "extracted"):
            b["review_flags"] = ["source_compiled_branch_identity_ambiguous"]
            linked.append(b)
            continue
        c = matches[0]
        if s["ordinal"] != c["ordinal"]:
            b["review_flags"] = ["source_compiled_ordinal_changed"]
            linked.append(b)
            continue
        cte = compiled_ctes[s["source_cte"]]
        q = clauses(cte["body"])
        if len(q) != 2 or raw(parsed["source"], q["select"]) != "*":
            b["review_flags"] = ["compiled_cte_not_simple_star"]
            linked.append(b)
            continue
        sources, joins = from_sources(q["from"], parsed["source"], compiled_path)
        if len(sources) != 1 or joins:
            b["review_flags"] = ["compiled_cte_relation_ambiguous"]
            linked.append(b)
            continue
        rel = next(iter(sources.values()))
        kind, model_id = tracer.target(metric_id, rel, compiled_ctes)
        if kind != "model" or tracer.nodes[model_id]["name"] != s["source_ref"]:
            b["review_flags"] = ["source_ref_compiled_relation_disagree"]
            linked.append(b)
            continue
        b.update({"alignment": "unique_literal_grain_cte_and_ordinal",
                  "compiled_branch": {**c["location"], "path": compiled_path},
                  "source_value": {"expression": s["expressions"]["value"],
                                   "location": projection_location(source_sql, s["ordinal"], 4, pilot.MODEL)},
                  "compiled_value": {"expression": c["expressions"]["value"],
                                     "location": projection_location(compiled_sql, c["ordinal"], 4, compiled_path)},
                  "source_where": {"expression": s["where"], "location": s["clause_locations"].get("where")},
                  "compiled_where": {"expression": c["where"],
                                     "location": {**c["clause_locations"]["where"], "path": compiled_path}
                                     if c["where"] else None},
                  "relation_dependency": {"source_cte": s["source_cte"], "source_ref": s["source_ref"],
                                          "source_ref_location": s["source_ref_location"],
                                          "compiled_cte_location": {**cte["location"], "path": compiled_path},
                                          "compiled_relation": rel["name"], "compiled_relation_location": rel["location"],
                                          "manifest_node": model_id,
                                          "manifest_depends_on_node": model_id in tracer.nodes[metric_id]["depends_on"]["nodes"]},
                  "value_fields": [], "branch_filter_fields": []})
        flags = []
        if s.get("macro_calls_unexpanded"):
            flags.append("source_macro_compiled_expansion_requires_review")
        if s.get("grouping_sets"):
            flags.append("grouping_sets_row_groups_not_expanded")
        stage_source = re.fullmatch(r"\s*stage\s*=\s*'([^']+)'\s*", s["where"] or "", re.I)
        stage_compiled = re.fullmatch(r"\s*stage\s*=\s*'([^']+)'\s*", c["where"] or "", re.I)
        stage = stage_source[1] if (stage_source and stage_compiled and
                                    stage_source[1] == stage_compiled[1]) else None
        if (stage_source or stage_compiled) and stage is None:
            flags.append("stage_filter_source_compiled_disagree")
        for kind_name, clause_key, output_key in (("value", "select", "value_fields"),
                                                   ("where", "where", "branch_filter_fields")):
            if kind_name == "value":
                source = parsed["source"]
                branch = pilot.union_parts(compiled_ctes["unioned"]["body"])[c["ordinal"] - 1]
                expr_tokens = pilot.split_top(clauses(branch)["select"], ",")[4]
                if len(expr_tokens) >= 3 and pilot.word(expr_tokens[-2], "as"):
                    expr_tokens = expr_tokens[:-2]
            else:
                source = parsed["source"]
                branch = pilot.union_parts(compiled_ctes["unioned"]["body"])[c["ordinal"] - 1]
                expr_tokens = clauses(branch).get(clause_key, [])
            try:
                refs, count_star = field_refs(expr_tokens, source, compiled_path)
                if kind_name == "value":
                    b["value_uses_row_count"] = count_star
                for ref in refs:
                    if ref["qualifier"]:
                        flags.append("qualified_branch_field_requires_review")
                    traced = (tracer.walk(model_id, ref["field"], stage=stage)
                              if ref["qualifier"] in (None, s["source_cte"]) else
                              {"field": ref["field"], "status": "needs_review", "stop": "unresolved_branch_qualifier"})
                    b[output_key].append({"use": ref, "immediate_declaration":
                                          traced.get("location") if traced.get("model") == model_id else None,
                                          "trace": traced})
            except Stop as exc:
                flags.append(f"{kind_name}_expression_{exc}")
        b["immediate_upstream_row_filter"] = tracer.immediate_filter(model_id)
        b["review_flags"] = sorted(set(flags))
        linked.append(b)
    all_traces = [entry["trace"] for b in linked for key in ("value_fields", "branch_filter_fields")
                  for entry in b.get(key, [])]
    model_filter_traces = [entry["trace"] for b in linked
                           for entry in (b.get("immediate_upstream_row_filter") or {}).get("fields", [])]
    stops = Counter(n["stop"] for tree in all_traces + model_filter_traces
                    for n in walk_nodes(tree) if n.get("stop"))
    counts = {"source_branches": len(source_branches), "compiled_branches": len(compiled_branches),
              "aligned": sum(b["alignment"] != "needs_review" for b in linked),
              "unresolved_alignment": sum(b["alignment"] == "needs_review" for b in linked),
              "value_row_count_branches": sum(b.get("value_uses_row_count", False) for b in linked),
              "row_count_only_branches": sum(b.get("value_uses_row_count", False) and not b.get("value_fields")
                                             for b in linked),
              "value_field_uses": sum(len(b.get("value_fields", [])) for b in linked),
              "branch_filter_field_uses": sum(len(b.get("branch_filter_fields", [])) for b in linked),
              "immediate_value_field_declarations": sum(bool(e["immediate_declaration"]) for b in linked
                                                        for e in b.get("value_fields", [])),
              "immediate_filter_field_declarations": sum(bool(e["immediate_declaration"]) for b in linked
                                                         for e in b.get("branch_filter_fields", [])),
              "upstream_model_row_filter_field_uses": sum(len((b.get("immediate_upstream_row_filter") or {}).get("fields", []))
                                                          for b in linked),
              "seed_header_terminals": sum(n.get("status") == "seed_header_field"
                                           for tree in all_traces for n in walk_nodes(tree)),
              "field_paths_requiring_review": sum(has_review(tree) for tree in all_traces),
              "review_branches": sum(b["review_status"] == "needs_review" for b in linked),
              "stops_by_reason": dict(sorted(stops.items()))}
    return {"artifact_provenance": {"repo": "jross21/gtm-funnel-analytics", "git_head": head,
                                    "source_git_object": pilot.MODEL, "source_git_object_sha256": digest(source_sql.encode()),
                                    "working_source_matches_git_object": True,
                                    "source_branch_report_sha256": digest((ROOT / "dbt_metric_branches_report.json").read_bytes()),
                                    "manifest": MANIFEST, "manifest_sha256": digest(manifest_data),
                                    "dbt_version": manifest["metadata"]["dbt_version"],
                                    "manifest_generated_at": manifest["metadata"].get("generated_at"),
                                    "manifest_node": metric_id, "compiled_artifacts": tracer.artifacts},
            "scope": {"field_edge": "A parsed projection reference through a named CTE/model; seed endpoint is a CSV header.",
                      "relation_edge": "A source ref, compiled relation, and manifest dependency; not field lineage.",
                      "artifact_check": "manifest compiled_code equals file after strip; no SQL execution or runtime validity test.",
                      "limits": ["Only SELECT projections, named CTEs, one stage-discriminated UNION ALL, named relations and explicit ON joins.",
                                 "Stars pass a field only with one FROM relation and no conflicting projection.",
                                 "Qualified joined fields expose a syntactic input; join cardinality and row semantics remain unverified.",
                                 "Group sets and compiled macro expansions are recorded, not semantically interpreted.",
                                 "Depth/node bounds and unsupported constructs stop with needs_review.",
                                 "No equivalence, numerical accuracy, or complete lineage claim."]},
            "bounds": {"model_hops": MAX_MODEL_HOPS, "cte_hops": MAX_CTE_HOPS, "nodes_per_field": MAX_NODES},
            "counts": counts, "branches": linked}


def markdown(report: dict) -> str:
    c, p = report["counts"], report["artifact_provenance"]
    lines = ["# Compiled GTM metric field provenance (bounded)", "",
             f"Pinned HEAD `{p['git_head']}`; manifest dbt `{p['dbt_version']}`. "
             f"The manifest's `compiled_code` matches the metric compiled SQL after stripping outer whitespace. "
             "This checks artifact identity, not query execution or field lineage certainty.", "",
             f"SHA-256: manifest `{p['manifest_sha256']}`; source Git object `{p['source_git_object_sha256']}`; "
             f"metric compiled file `{p['compiled_artifacts'][p['manifest_node']]['sha256']}`. "
             "Per-model compiled file hashes are in the JSON.", "",
             f"**Coverage:** {c['aligned']}/{c['source_branches']} unique source/compiled branch identities; "
             f"{c['value_field_uses']} scalar value field uses ({c['immediate_value_field_declarations']} "
             f"immediate declarations), {c['branch_filter_field_uses']} branch WHERE field uses "
             f"({c['immediate_filter_field_declarations']} immediate declarations), "
             f"{c['value_row_count_branches']} values containing `count(*)` "
             f"({c['row_count_only_branches']} without scalar field inputs), "
             f"{c['upstream_model_row_filter_field_uses']} immediate model row-filter field uses. "
             f"Of {c['value_field_uses'] + c['branch_filter_field_uses']} root value/branch-WHERE field-use paths, "
             f"{c['field_paths_requiring_review']} carry a review marker. Separately, "
             f"{c['seed_header_terminals']} seed-header terminal occurrences were reached along those paths. "
             f"{c['review_branches']} branches remain `needs_review`.", "",
             "| # | Metric / grain | Source → compiled lines | Scalar `value` inputs → immediate model | Branch WHERE inputs | Deeper evidence / review |",
             "| --- | --- | --- | --- | --- | --- |"]
    for b in report["branches"]:
        s, t = b["source_branch"], b.get("compiled_branch")
        span = f"{s['path']}:{s['start_line']}–{s['end_line']}"
        if t:
            span += f" → {t['path']}:{t['start_line']}–{t['end_line']}"
        if not t:
            lines.append(f"| {b['ordinal']} | `{b['metric_name']}` / `{b['grain']}` | {span} | — | — | identity needs review |")
            continue
        def fields(key):
            return ", ".join(f"`{e['use']['field']}` → " +
                             (f"{e['immediate_declaration']['path']}:{e['immediate_declaration']['start_line']}"
                              if e["immediate_declaration"] else "needs review") for e in b[key]) or "—"
        visited = [n for e in b["value_fields"] + b["branch_filter_fields"]
                   for n in walk_nodes(e["trace"])]
        visited += [n for e in (b.get("immediate_upstream_row_filter") or {}).get("fields", [])
                    for n in walk_nodes(e["trace"])]
        stops = sorted({n["stop"] for n in visited if n.get("stop")})
        flags = sorted(set(b["review_flags"] + stops +
                           [f for n in visited for f in n.get("review_flags", [])]))
        endpoints = list(dict.fromkeys(f"`{n['field']}` → {n['location']['path']}:1" for n in visited
                                       if n.get("status") == "seed_header_field"))
        derived = list(dict.fromkeys(f"`{n['field']}` → {report['artifact_provenance']['compiled_artifacts'][n['model']]['path']}:"
                                          f"{n['location']['start_line']}" for n in visited
                                          if n.get("model") == "model.arcline.fct_funnel_conversion"
                                          and n.get("scope") == "counts" and n.get("location")))
        items = (derived + endpoints)[:4]
        remaining = len(derived + endpoints) - len(items)
        deeper = ", ".join(items) + (f" (+{remaining} paths in JSON)" if remaining else "")
        row_filter = b.get("immediate_upstream_row_filter") or {}
        if not deeper and row_filter.get("expression"):
            place = row_filter["location"]
            deeper = f"upstream WHERE `{row_filter['expression']}` ({place['path']}:{place['start_line']})"
        note = (deeper or "see JSON trace") + ("; review: " + ", ".join(flags) if flags else "")
        value = fields("value_fields") + ("; `count(*)` row set" if b.get("value_uses_row_count") else "")
        if value.startswith("—;"):
            value = "`count(*)` row set (no scalar field)"
        lines.append(f"| {b['ordinal']} | `{b['metric_name']}` / `{b['grain']}` | {span} | "
                     f"{value} | {fields('branch_filter_fields')} | {note.replace('|', '\\|')} |")
    lines += ["", "## Reading the evidence", "",
              "Each JSON branch has its source and compiled scalar value expressions and WHERE clauses with line locations. "
              "The CTE ref, compiled relation and manifest dependency are **relation-level** evidence. "
              "`value_fields`, `branch_filter_fields`, and the immediate model row filter hold parsed field declarations "
              "and their upstream input trees; a seed terminal means the name occurs in the CSV header.", "",
              "Source/compiled identity uses the unique (literal metric name, literal grain, source CTE) tuple "
              "and matching branch ordinal. It does not equate source and expanded SQL expressions. "
              "A source macro, grouping set, unresolved owner, or joined path remains reviewable even when "
              "the compiled expression exposes column names.", "",
              "**Observed stops:** " + (", ".join(f"`{k}`={v}" for k, v in c["stops_by_reason"].items()) or "none") + ".", "",
              "**Limits.** " + " ".join(report["scope"]["limits"]) + ""]
    return "\n".join(lines)


def self_check() -> None:
    s = pilot.Source("count(*) filter (where is_won) + date_diff('day', created_date::timestamp, close_date::timestamp)")
    refs, star = field_refs(s.tokens, s, "toy.sql")
    assert star and [r["field"] for r in refs] == ["is_won", "created_date", "close_date"]
    j = pilot.Source("a left join b on a.id = b.id")
    sources, joins = from_sources(j.tokens, j, "toy.sql")
    assert set(sources) == {"a", "b"} and len(joins) == 1
    q = pilot.Source("select * from a left join b on a.id = b.id")
    assert len(from_sources(clauses(q.tokens)["from"], q, "toy.sql")[1]) == 1
    assert has_review({"inputs": [{"trace": {"status": "needs_review", "stop": "ambiguous_star"}}]})
    assert digest(b"x") != digest(b"x ")

    class Tiny(Tracer):
        def __init__(self, sql: str):
            source = pilot.Source(sql)
            ctes, final, _ = pilot.ctes(source)
            self.parsed = {"toy": {"source": source, "path": "toy.sql", "ctes": ctes, "final": final}}
            self.nodes = {"toy": {"depends_on": {"nodes": [], "macros": []}}}

        def model(self, model_id: str) -> dict:
            return self.parsed[model_id]

        def target(self, model_id: str, relation: dict, ctes: dict) -> tuple[str, str]:
            if relation["name"] in ctes:
                return "cte", relation["name"]
            raise Stop("toy_undeclared_relation")

    joined = Tiny("with a as (select 1 as x from src), "
                  "b as (select a.x as v from a left join z on a.x = z.x) "
                  "select v from b")
    jtrace = joined.walk("toy", "v")
    assert jtrace["status"] == "needs_review"
    assert any("join_cardinality_unchecked" in n.get("review_flags", []) for n in walk_nodes(jtrace))
    star = Tiny("with a as (select 1 as x from src), "
                "b as (select * from a left join z on a.x = z.x) select x from b")
    assert any(n.get("stop") == "ambiguous_or_missing_star_field" for n in walk_nodes(star.walk("toy", "x")))
    union = Tiny("with u as (select 'SAL' as stage, 1 as x from src "
                 "union all select 'SQL' as stage, 2 as x from src) select x from u")
    assert union.walk("toy", "x", stage="SAL")["status"] == "traced"
    assert any(n.get("stop") == "union_field_without_discriminator" for n in walk_nodes(union.walk("toy", "x")))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO, help="pinned public GTM checkout")
    parser.add_argument("--check", action="store_true", help="run self-checks and compare both reports without writing")
    parser.add_argument("--self-check", action="store_true", help="run parser boundary checks before generating reports")
    args = parser.parse_args()
    if args.self_check or args.check:
        self_check()
    report = build(args.repo)
    rendered = {JSON_REPORT: json.dumps(report, indent=2) + "\n", MD_REPORT: markdown(report)}
    if args.check:
        for path, data in rendered.items():
            if not path.exists() or path.read_text(encoding="utf-8") != data:
                raise SystemExit(f"report missing or stale: {path}")
        assert report["counts"]["aligned"] == report["counts"]["source_branches"] == 11
        assert report["counts"]["immediate_value_field_declarations"] > 0
        assert report["counts"]["seed_header_terminals"] > 0
        win = next(b for b in report["branches"] if b["metric_name"] == "win_rate")
        assert win["value_uses_row_count"] and [e["use"]["field"] for e in win["value_fields"]] == ["is_won"]
        assert "`is_won`" in rendered[MD_REPORT].split("| 5 |", 1)[1].split("\n", 1)[0]
        assert report["counts"]["row_count_only_branches"] == 2
        print("check passed: pinned artifacts, 11 identities, field paths and reports")
    else:
        for path, data in rendered.items():
            path.write_text(data, encoding="utf-8")
        print(json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
