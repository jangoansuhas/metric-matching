#!/usr/bin/env python3
"""Extract a bounded set of long-format dbt metric branches from pinned source SQL.

This recognizes one WITH CTE containing top-level SELECT ... UNION ALL SELECT
branches with five ordered projections and a single CTE in each FROM. It records
SQL expressions verbatim; it does not execute dbt, expand Jinja or GROUPING SETS,
trace columns, or decide whether two values/definitions are equivalent.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "public_corpus" / "gtm-funnel-analytics"
COMMIT = "a71232c123a5fb78da9b52d4246950ee48591c00"
MODEL = "models/marts/metrics/fct_metric_values.sql"
COLUMNS = ("metric_name", "grain", "period_start", "segment", "value")
LEX = re.compile(
    r"(?P<space>\s+)|(?P<comment>--[^\n]*|/\*.*?\*/)|"
    r"(?P<jinja>\{\{.*?\}\}|\{%.*?%\})|"
    r"(?P<string>'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\")|"
    r"(?P<word>[A-Za-z_][A-Za-z_0-9]*)|(?P<number>\d+(?:\.\d+)?)|"
    r"(?P<symbol>.)",
    re.S,
)
REF = re.compile(r"\{\{\s*ref\(\s*(['\"])([A-Za-z_][A-Za-z_0-9]*)\1\s*\)\s*}}")
SET = re.compile(r"\{%\s*set\s+([A-Za-z_][A-Za-z_0-9]*)\s*=.*?%\}", re.S)
SIMPLE_COLUMN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)?")
SIMPLE_JINJA_VAR = re.compile(r"\{\{\s*(\w+)\s*}}")


class Unsupported(ValueError):
    """Syntax outside the extractor's deliberately narrow grammar."""


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


class Source:
    def __init__(self, sql: str):
        self.sql = sql
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", sql)]
        self.tokens = self.lex(sql)

    @staticmethod
    def lex(sql: str) -> list[Token]:
        out = []
        end = 0
        for match in LEX.finditer(sql):
            if match.start() != end:
                raise Unsupported("Lexer skipped source text")
            end = match.end()
            kind = match.lastgroup
            if kind == "symbol" and match.group() in "{}'\"":
                raise Unsupported("Malformed Jinja block or quoted string")
            if kind not in ("comment", "space"):
                out.append(Token(kind, match.group(), match.start(), end))
        if end != len(sql):
            raise Unsupported("Lexer did not reach the end of source")
        return out

    def raw(self, tokens: list[Token]) -> str:
        return self.sql[tokens[0].start:tokens[-1].end].strip() if tokens else ""

    def location(self, tokens: list[Token]) -> dict | None:
        if not tokens:
            return None
        return {"path": MODEL, "start_line": self.line(tokens[0].start),
                "end_line": self.line(tokens[-1].end - 1)}

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.line_starts, offset)


def word(token: Token, value: str) -> bool:
    return token.kind == "word" and token.value.lower() == value


def match_close(tokens: list[Token], start: int) -> int:
    if tokens[start].value != "(":
        raise Unsupported("Expected opening parenthesis")
    depth = 0
    for pos in range(start, len(tokens)):
        if tokens[pos].value == "(":
            depth += 1
        elif tokens[pos].value == ")":
            depth -= 1
            if depth == 0:
                return pos
    raise Unsupported("Unbalanced parentheses")


def split_top(tokens: list[Token], separator: str) -> list[list[Token]]:
    parts, start, depth = [], 0, 0
    for pos, token in enumerate(tokens):
        if token.value == "(":
            depth += 1
        elif token.value == ")":
            depth -= 1
            if depth < 0:
                raise Unsupported("Unbalanced parentheses")
        elif token.value == separator and depth == 0:
            parts.append(tokens[start:pos])
            start = pos + 1
    if depth:
        raise Unsupported("Unbalanced parentheses")
    parts.append(tokens[start:])
    if any(not part for part in parts):
        raise Unsupported("Empty comma-separated expression")
    return parts


def ctes(source: Source) -> tuple[dict[str, dict], list[Token], dict[str, dict]]:
    tokens, pos = source.tokens, 0
    definitions = {}
    while pos < len(tokens) and tokens[pos].kind == "jinja" and tokens[pos].value.startswith("{%"):
        matched = SET.fullmatch(tokens[pos].value)
        if not matched or matched[1] in definitions:
            raise Unsupported("Only unique top-level Jinja set declarations are supported")
        definitions[matched[1]] = {"expression": tokens[pos].value,
                                   "location": source.location([tokens[pos]])}
        pos += 1
    if pos >= len(tokens) or not word(tokens[pos], "with"):
        raise Unsupported("Expected top-level WITH after Jinja set declarations")
    pos += 1
    result = {}
    while pos + 2 < len(tokens):
        if tokens[pos].kind != "word" or not word(tokens[pos + 1], "as") or tokens[pos + 2].value != "(":
            raise Unsupported("Expected named CTE AS (...)")
        name = tokens[pos].value.lower()
        if name in result:
            raise Unsupported("Duplicate CTE name")
        end = match_close(tokens, pos + 2)
        result[name] = {"body": tokens[pos + 3:end],
                        "location": source.location(tokens[pos:end + 1])}
        pos = end + 1
        if pos < len(tokens) and tokens[pos].value == ",":
            pos += 1
            continue
        return result, tokens[pos:], definitions
    raise Unsupported("Incomplete CTE list")


def union_parts(tokens: list[Token]) -> list[list[Token]]:
    parts, start, depth, pos = [], 0, 0, 0
    while pos < len(tokens):
        token = tokens[pos]
        if token.value == "(":
            depth += 1
        elif token.value == ")":
            depth -= 1
            if depth < 0:
                raise Unsupported("Unbalanced UNION body")
        elif depth == 0 and word(token, "union"):
            if pos + 1 >= len(tokens) or not word(tokens[pos + 1], "all"):
                raise Unsupported("Only UNION ALL is supported")
            if not tokens[start:pos]:
                raise Unsupported("Empty UNION branch")
            parts.append(tokens[start:pos])
            pos += 2
            start = pos
            continue
        pos += 1
    if depth or not tokens[start:]:
        raise Unsupported("Unbalanced or empty final UNION branch")
    parts.append(tokens[start:])
    return parts


def select_clauses(tokens: list[Token]) -> dict[str, list[Token]]:
    if not tokens or not word(tokens[0], "select"):
        raise Unsupported("Branch must start with SELECT")
    boundaries = []
    depth = 0
    pos = 1
    while pos < len(tokens):
        token = tokens[pos]
        if token.value == "(":
            depth += 1
        elif token.value == ")":
            depth -= 1
            if depth < 0:
                raise Unsupported("Unbalanced SELECT")
        elif depth == 0 and token.kind == "word":
            key, width = None, 1
            if token.value.lower() in ("from", "where", "having", "limit", "qualify"):
                key = token.value.lower()
            elif token.value.lower() in ("group", "order") and pos + 1 < len(tokens) and word(tokens[pos + 1], "by"):
                key, width = token.value.lower() + " by", 2
            elif token.value.lower() in ("join", "union", "intersect", "except"):
                raise Unsupported(f"Unsupported top-level {token.value.upper()}")
            if key:
                boundaries.append((pos, key, width))
                pos += width
                continue
        pos += 1
    if depth:
        raise Unsupported("Unbalanced SELECT")
    keys = [key for _, key, _ in boundaries]
    if not keys or keys[0] != "from" or len(set(keys)) != len(keys):
        raise Unsupported("Expected one top-level FROM")
    if keys != [key for key in ("from", "where", "group by", "having", "order by", "limit", "qualify") if key in keys]:
        raise Unsupported("Unexpected SQL clause order")
    result = {"select": tokens[1:boundaries[0][0]]}
    for idx, (at, key, width) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(tokens)
        result[key] = tokens[at + width:end]
        if not result[key]:
            raise Unsupported(f"Empty {key.upper()} clause")
    return result


def projection(source: Source, tokens: list[Token]) -> tuple[str, str | None]:
    alias = None
    if len(tokens) >= 3 and word(tokens[-2], "as") and tokens[-1].kind == "word":
        alias = tokens[-1].value.lower()
        tokens = tokens[:-2]
    return source.raw(tokens), alias


def ref_sources(source: Source, cte_map: dict[str, dict]) -> dict[str, dict]:
    result = {}
    for name, info in cte_map.items():
        if name == "unioned":
            continue
        try:
            clauses = select_clauses(info["body"])
            select = clauses["select"]
            from_tokens = clauses["from"]
            if (len(select) == 1 and select[0].value == "*" and len(from_tokens) == 1
                    and len(clauses) == 2 and from_tokens[0].kind == "jinja"):
                match = REF.fullmatch(from_tokens[0].value)
                if match:
                    result[name] = {"ref": match[2], "ref_location": source.location(from_tokens),
                                    "cte_location": info["location"], "resolution": "simple_select_star_ref"}
                    continue
        except Unsupported:
            pass
        result[name] = {"ref": None, "ref_location": None,
                        "cte_location": info["location"], "resolution": "unsupported_cte_source"}
    return result


def between_time_keys(tokens: list[Token]) -> list[str]:
    """Recognize only `column BETWEEN <Jinja> AND <Jinja>` token sequences."""
    keys = []
    for pos in range(1, len(tokens) - 3):
        if (word(tokens[pos], "between") and tokens[pos + 1].kind == "jinja"
                and word(tokens[pos + 2], "and") and tokens[pos + 3].kind == "jinja"):
            key = tokens[pos - 1].value
            if tokens[pos - 1].kind == "word":
                if pos >= 3 and tokens[pos - 2].value == "." and tokens[pos - 3].kind == "word":
                    key = tokens[pos - 3].value + "." + key
                if SIMPLE_COLUMN.fullmatch(key):
                    keys.append(key)
    return list(dict.fromkeys(keys))


def branch(source: Source, tokens: list[Token], ordinal: int,
           sources: dict[str, dict], definitions: dict[str, dict]) -> dict:
    base = {"ordinal": ordinal, "location": source.location(tokens)}
    try:
        clauses = select_clauses(tokens)
        if set(clauses) - {"select", "from", "where", "group by"}:
            raise Unsupported("HAVING/ORDER BY/LIMIT/QUALIFY is outside the branch subset")
        fields = [projection(source, part) for part in split_top(clauses["select"], ",")]
        if len(fields) != len(COLUMNS):
            raise Unsupported(f"Expected {len(COLUMNS)} ordered metric projections, got {len(fields)}")
        expected_aliases = {i: name for i, name in enumerate(COLUMNS)}
        if any(alias is not None and alias != expected_aliases[i] for i, (_, alias) in enumerate(fields)):
            raise Unsupported("Unexpected projection alias for metric output position")
        from_tokens = clauses["from"]
        if len(from_tokens) != 1 or from_tokens[0].kind != "word":
            raise Unsupported("Only FROM one unaliased CTE is supported")
        cte_name = from_tokens[0].value.lower()
        if cte_name not in sources:
            raise Unsupported("FROM does not resolve to a preceding CTE")
        expressions = dict(zip(COLUMNS, (expr for expr, _ in fields)))
        literal = re.compile(r"'((?:''|[^'])*)'\Z", re.S)
        metric_match = literal.fullmatch(expressions["metric_name"])
        grain_match = literal.fullmatch(expressions["grain"])
        grain_literal = grain_match[1].replace("''", "'") if grain_match else None
        grain = grain_literal if grain_literal in ("month", "window") else "unknown"
        where = source.raw(clauses.get("where", [])) or None
        grouping = source.raw(clauses.get("group by", [])) or None
        group_tokens = clauses.get("group by", [])
        grouping_sets = any(word(t, "grouping") and i + 1 < len(group_tokens)
                            and word(group_tokens[i + 1], "sets") for i, t in enumerate(group_tokens))
        jinja = list(dict.fromkeys(t.value for key in ("select", "where", "group by")
                                    for t in clauses.get(key, []) if t.kind == "jinja"))
        set_vars = [m[1] for expr in jinja if (m := SIMPLE_JINJA_VAR.fullmatch(expr))]
        macro_calls = [expr for expr in jinja if expr.startswith("{{")
                       and not SIMPLE_JINJA_VAR.fullmatch(expr)]
        time_filter_keys = between_time_keys(clauses.get("where", []))
        period = expressions["period_start"]
        period_key = period if SIMPLE_COLUMN.fullmatch(period) else None
        flags = ["field_lineage_not_traced"]
        if grouping_sets:
            flags.append("grouping_sets_not_expanded")
        if jinja:
            flags.append("jinja_not_expanded")
        if macro_calls:
            flags.append("dbt_macro_not_expanded")
        if grain == "unknown":
            flags.append("unknown_grain")
        if not metric_match:
            flags.append("unknown_metric_name")
        if sources[cte_name]["ref"] is None:
            flags.append("cte_source_unresolved")
        return {**base, "parse_status": "extracted", "review_status": "needs_review",
                "metric_name": metric_match[1].replace("''", "'") if metric_match else None,
                "grain": grain, "expressions": expressions,
                "period_time_key": period_key, "time_filter_keys": time_filter_keys,
                "where": where, "group_by": grouping, "grouping_sets": grouping_sets,
                "source_cte": cte_name, "source_ref": sources[cte_name]["ref"],
                "source_cte_location": sources[cte_name]["cte_location"],
                "source_ref_location": sources[cte_name]["ref_location"],
                "clause_locations": {key: source.location(part) for key, part in clauses.items()},
                "jinja_expressions": jinja,
                "macro_calls_unexpanded": macro_calls,
                "jinja_set_definitions": {name: definitions[name] for name in set_vars if name in definitions},
                "review_flags": flags,
                "field_lineage": "not_traced"}
    except Unsupported as exc:
        return {**base, "parse_status": "unsupported", "review_status": "needs_review",
                "reason": str(exc), "raw_sql": source.raw(tokens), "grain": "unknown",
                "field_lineage": "not_traced"}


def extract(sql: str) -> dict:
    source = Source(sql)
    cte_map, final, definitions = ctes(source)
    if "unioned" not in cte_map or not cte_map["unioned"]["body"]:
        raise Unsupported("No nonempty unioned CTE")
    # If the outer query changes shape, positions in the union no longer establish
    # the emitted long-format columns; stop rather than silently reinterpret them.
    outer = select_clauses(final)
    if (set(outer) != {"select", "from"} or source.raw(outer["from"]).lower() != "unioned"
            or [source.raw(p).lower() for p in split_top(outer["select"], ",")] != list(COLUMNS)):
        raise Unsupported("Outer SELECT must project the five unioned columns unchanged")
    parts = union_parts(cte_map["unioned"]["body"])
    sources = ref_sources(source, cte_map)
    branches = [branch(source, part, idx, sources, definitions) for idx, part in enumerate(parts, 1)]
    return {"source": {"project": "jross21/gtm-funnel-analytics", "commit": COMMIT,
                       "path": MODEL, "method": "git show of pinned source SQL; no compiled SQL used"},
            "scope": "One unioned CTE in fct_metric_values.sql; single-CTE FROM and five positional outputs",
            "counts": {"union_all_branches": len(parts),
                       "extracted": sum(b["parse_status"] == "extracted" for b in branches),
                       "unsupported": sum(b["parse_status"] == "unsupported" for b in branches),
                       "unknown_grain": sum(b["grain"] == "unknown" for b in branches),
                       "known_grains": dict(sorted(Counter(b["grain"] for b in branches).items())),
                       "grouping_sets_unexpanded": sum(b.get("grouping_sets", False) for b in branches),
                       "jinja_unexpanded": sum(bool(b.get("jinja_expressions")) for b in branches),
                       "dbt_macro_unexpanded": sum(bool(b.get("macro_calls_unexpanded")) for b in branches),
                       "field_lineage_not_traced": len(branches)},
            "jinja_declarations": definitions,
            "boundaries": ["Expressions and WHERE clauses are copied, not evaluated or normalized for matching.",
                           "GROUPING SETS are marked, not expanded into per-segment/All rows.",
                           "Jinja sets, refs and dbt macros are not compiled; source CTE refs are identified syntactically.",
                           "Period key and BETWEEN time keys use narrow syntactic recognition; upstream time filters are not traced.",
                           "Column/field lineage, aggregation semantics, row cardinality and runtime data are not inferred.",
                           "Identical text or reconciled totals are not evidence of semantic equivalence."],
            "branches": branches}


def cell(value: str | None) -> str:
    return "`" + re.sub(r"\s+", " ", value).replace("|", "\\|") + "`" if value else "—"


def markdown(report: dict) -> str:
    counts = report["counts"]
    lines = ["# GTM long-format metric branches (bounded extraction)", "",
             f"Pinned source: [fct_metric_values.sql](https://github.com/jross21/gtm-funnel-analytics/blob/{COMMIT}/{MODEL}). "
             "Read from the Git object at the pinned revision; source locations below use that file's lines.", "",
             f"**Observed:** {counts['union_all_branches']} branches: {counts['extracted']} structurally extracted, "
             f"{counts['unsupported']} unsupported, {counts['unknown_grain']} unknown grain; grains "
             + ", ".join(f"{name}={number}" for name, number in counts["known_grains"].items()) + ". "
             f"{counts['grouping_sets_unexpanded']} branches use unexpanded `GROUPING SETS`; "
             f"{counts['jinja_unexpanded']} contain unexpanded Jinja, including "
             f"{counts['dbt_macro_unexpanded']} with a dbt macro call; field lineage is untraced in all "
             f"{counts['field_lineage_not_traced']}. Every branch needs review for semantic use.", "",
             "| # / source lines | Metric | Grain | Source CTE → ref | Period expression / time keys | Segment expression | Value expression | WHERE | Grouping / status |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for b in report["branches"]:
        loc = b["location"]
        line = f"[L{loc['start_line']}–{loc['end_line']}](https://github.com/jross21/gtm-funnel-analytics/blob/{COMMIT}/{MODEL}#L{loc['start_line']}-L{loc['end_line']})"
        if b["parse_status"] == "unsupported":
            lines.append(f"| {b['ordinal']} / {line} | — | unknown | — | — | — | — | — | unsupported: {b['reason']} |")
            continue
        expr = b["expressions"]
        keys = ", ".join(b["time_filter_keys"]) or "none recognized"
        group = "GROUPING SETS (unexpanded)" if b["grouping_sets"] else "none"
        lines.append(f"| {b['ordinal']} / {line} | {cell(b['metric_name'])} | {cell(b['grain'])} | "
                     f"{cell(b['source_cte'])} → {cell(b['source_ref'])} | "
                     f"{cell(expr['period_start'])}; filter keys: {keys} | "
                     f"{cell(expr['segment'])} | {cell(expr['value'])} | {cell(b['where'])} | {group}; needs review |")
    pipeline = [b for b in report["branches"] if b.get("metric_name") == "pipeline_created"]
    lines += ["", "## Source examples and boundaries", ""]
    if len(pipeline) == 2:
        month, window = pipeline
        lines += [f"- `pipeline_created` month (L{month['location']['start_line']}–{month['location']['end_line']}) "
                  f"uses period key {cell(month['period_time_key'])}, {cell(month['expressions']['value'])}, "
                  f"and {cell(month['where'])}. Its grouping is {cell(month['group_by'])}.",
                  f"- `pipeline_created` window (L{window['location']['start_line']}–{window['location']['end_line']}) "
                  f"uses period expression {cell(window['expressions']['period_start'])}, the same source text for "
                  f"the value expression and WHERE clause, and {cell(window['group_by'])}. "
                  "The `window_start`/`window_end` Jinja declarations depend on dbt vars and have not been expanded. "
                  "The month and window branches are separate aggregations; this report does not assert their totals agree or that they are interchangeable."]
    lines += ["- `win_rate` (L56–61) has an unexpanded `dbt.datediff` macro in its WHERE clause. "
              "The three funnel conversion branches (L89–96) project `conversion_rate` from a CTE referring to "
              "`fct_funnel_conversion`; this syntactic ref does not establish the origin of that field."]
    lines += ["", "**Limits.** " + " ".join(report["boundaries"]), "",
              "Unsupported branches, unknown grains, opaque CTE refs, Jinja and `GROUPING SETS` are retained "
              "as review items in the JSON. Source CTE → `ref` is relation-level syntax, not field lineage. "
              "The extractor does not use pair IDs, rows from the built model, or matching totals to label equivalence.", ""]
    return "\n".join(lines)


def self_check() -> None:
    # Commas and UNION ALL in a quoted value or comment must not create branches.
    toy = """with src as (select * from {{ ref('toy') }}), unioned as (
select 'toy' as metric_name, 'month' as grain, d as period_start, s as segment,
       coalesce(v, 0) as value from src -- union all
union all select 'other', 'custom', d, s, 'union all' from src
) select metric_name, grain, period_start, segment, value from unioned"""
    result = extract(toy)
    assert result["counts"]["union_all_branches"] == 2
    assert result["branches"][0]["expressions"]["value"] == "coalesce(v, 0)"
    assert result["branches"][1]["grain"] == "unknown"
    assert "unknown_grain" in result["branches"][1]["review_flags"]
    bad = toy.replace("'other', 'custom', d, s, 'union all'", "'other', 'window', d, s")
    assert extract(bad)["branches"][1]["parse_status"] == "unsupported"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO, help="local checkout of the pinned public GTM repo")
    parser.add_argument("--self-check", action="store_true", help="run small parser boundary checks first")
    args = parser.parse_args()
    if args.self_check:
        self_check()
    done = subprocess.run(["git", "-C", str(args.repo), "show", f"{COMMIT}:{MODEL}"],
                          capture_output=True, text=True, check=True)
    report = extract(done.stdout)
    (ROOT / "dbt_metric_branches_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "dbt_metric_branches_report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
