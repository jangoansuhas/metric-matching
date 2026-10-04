#!/usr/bin/env python3
"""Trace a documented subset of Jaffle Shop dbt SELECTs, abstaining on unknown syntax."""

import argparse
import json
import re
from pathlib import Path

import yaml

from run_public_corpus import repository_commit


ROOT = Path(__file__).resolve().parent
IDENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
COLUMN = re.compile(r"^(?:(\w+)\.)?(\w+)$")
REF = re.compile(r"^\{\{\s*ref\(['\"](\w+)['\"]\)\s*}}$", re.I)
SOURCE = re.compile(r"^\{\{\s*source\(['\"](\w+)['\"]\s*,\s*['\"](\w+)['\"]\)\s*}}$", re.I)
MACRO = re.compile(r"^\{\{\s*cents_to_dollars\(['\"](\w+)['\"]\)\s*}}$", re.I)


class Unsupported(Exception):
    pass


def clean_sql(sql):
    # This subset contains no '--' inside a quoted string.
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def closing_paren(text, start):
    depth, quote = 0, None
    for i in range(start, len(text)):
        ch = text[i]
        if ch in "'\"":
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
        elif quote is None:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
    raise Unsupported("Unbalanced CTE or expression parentheses")


def split_commas(text):
    fields, start, depth, quote = [], 0, 0, None
    for i, ch in enumerate(text):
        if ch in "'\"":
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
        elif quote is None:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                fields.append(text[start:i].strip())
                start = i + 1
    if quote or depth:
        raise Unsupported("Unbalanced SELECT projection")
    fields.append(text[start:].strip())
    return fields


def parse_ctes(sql):
    text = clean_sql(sql).strip()
    ctes = {}
    if not re.match(r"^with\b", text, re.I):
        return ctes, text
    pos = 4
    while True:
        match = re.match(r"\s*(\w+)\s+as\s*\(", text[pos:], re.I)
        if not match:
            raise Unsupported("Unsupported WITH/CTE declaration")
        name = match[1]
        start = pos + match.end() - 1
        end = closing_paren(text, start)
        ctes[name] = text[start + 1:end].strip()
        pos = end + 1
        if text[pos:].lstrip().startswith(","):
            pos += len(text[pos:]) - len(text[pos:].lstrip()) + 1
            continue
        return ctes, text[pos:].strip()


def top_level_from(query):
    match = re.match(r"^\s*select\b", query, re.I)
    if not match:
        raise Unsupported("Expected a SELECT")
    start, depth, quote = match.end(), 0, None
    for i in range(start, len(query)):
        ch = query[i]
        if ch in "'\"":
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
        elif quote is None:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and re.match(r"from\b", query[i:], re.I) and (i == 0 or query[i - 1].isspace()):
                return query[start:i].strip(), query[i + 4:].strip()
    raise Unsupported("No top-level FROM")


def sources_from(tail):
    if tail.startswith("{{"):
        end = tail.find("}}")
        if end < 0:
            raise Unsupported("Unterminated dbt source/ref")
        primary = tail[:end + 2]
    else:
        match = re.match(r"^(\w+)\b", tail)
        if not match:
            raise Unsupported("Unsupported FROM source")
        primary = match[1]
    sources = {primary: primary}
    for match in re.finditer(r"\bjoin\s+(\w+)\b", tail, re.I):
        sources[match[1]] = match[1]
    return primary, sources


def selected_expression(projection, target):
    expressions = split_commas(projection)
    explicit, stars = [], []
    for field in expressions:
        alias = re.match(r"^(.*?)\s+as\s+(\w+)\s*$", field, re.I | re.S)
        if alias:
            expr, name = alias[1].strip(), alias[2]
        else:
            expr = field.strip()
            col = COLUMN.fullmatch(expr)
            name = col[2] if col else None
        if name == target:
            explicit.append(expr)
        if expr == "*" or re.fullmatch(r"\w+\.\*", expr):
            stars.append(expr)
    if len(explicit) == 1:
        return explicit[0]
    if len(explicit) > 1 or len(stars) != 1:
        raise Unsupported(f"Column {target} is missing or ambiguous in SELECT")
    return stars[0]


def trace(repo, model, target):
    paths = list((repo / "models").rglob(f"{model}.sql"))
    if len(paths) != 1:
        raise Unsupported(f"Model {model} does not resolve to exactly one SQL file")
    steps, warnings = [], []
    seen = set()

    def model_query(file, column):
        marker = (str(file), "final", column)
        if marker in seen:
            raise Unsupported("Cyclic lineage path")
        seen.add(marker)
        ctes, final = parse_ctes(file.read_text(encoding="utf-8"))
        return query(file, "final", final, ctes, column)

    def follow(file, scope, ctes, source_name, column):
        if source_name in ctes:
            marker = (str(file), source_name, column)
            if marker in seen:
                raise Unsupported("Cyclic CTE lineage path")
            seen.add(marker)
            return query(file, source_name, ctes[source_name], ctes, column)
        ref = REF.fullmatch(source_name)
        if ref:
            next_files = list((repo / "models").rglob(f"{ref[1]}.sql"))
            if len(next_files) != 1:
                raise Unsupported(f"Ref {ref[1]} is missing or ambiguous")
            return model_query(next_files[0], column)
        source = SOURCE.fullmatch(source_name)
        if source:
            return {"source": f"{source[1]}.{source[2]}.{column}", "expression_kind": "source_column"}
        raise Unsupported(f"Unresolved SQL source: {source_name}")

    def query(file, scope, sql, ctes, column):
        projection, from_tail = top_level_from(sql)
        primary, sources = sources_from(from_tail)
        expr = selected_expression(projection, column)
        steps.append({"file": str(file.relative_to(repo)), "scope": scope,
                      "column": column, "expression": " ".join(expr.split())})
        if expr == "*":
            if len(sources) != 1:
                raise Unsupported("Unqualified star with multiple input relations")
            return follow(file, scope, ctes, primary, column)
        star = re.fullmatch(r"(\w+)\.\*", expr)
        if star:
            if star[1] not in sources:
                raise Unsupported("Unresolved qualified star")
            if len(sources) > 1:
                warnings.append("Qualified star crosses a join; row multiplicity has not been validated")
            return follow(file, scope, ctes, sources[star[1]], column)
        direct = COLUMN.fullmatch(expr)
        if direct:
            qualifier, source_column = direct.groups()
            if qualifier and qualifier not in sources:
                raise Unsupported(f"Unresolved qualifier: {qualifier}")
            if not qualifier and len(sources) != 1:
                raise Unsupported("Unqualified column with multiple inputs")
            if qualifier and qualifier != primary:
                join = re.search(
                    rf"\b(?:left|inner|right|full)?\s*join\s+{re.escape(qualifier)}\s+on\s+"
                    r"((?:\w+\.)?\w+\s*=\s*(?:\w+\.)?\w+)", from_tail, re.I)
                if not join:
                    raise Unsupported(f"No simple join condition for {qualifier}")
                steps[-1]["join_predicate"] = " ".join(join[1].split())
                warnings.append("Join key is visible, but one-to-one cardinality was not checked against rows")
            return follow(file, scope, ctes, sources[qualifier] if qualifier else primary, source_column)
        macro = MACRO.fullmatch(expr)
        if macro:
            macro_file = repo / "macros/cents_to_dollars.sql"
            if not macro_file.is_file() or "adapter.dispatch('cents_to_dollars')" not in macro_file.read_text(encoding="utf-8"):
                raise Unsupported("Macro dispatch is missing or changed")
            warnings.append("cents_to_dollars is adapter-dispatched; transformation is not compiled or executed")
            result = follow(file, scope, ctes, primary, macro[1])
            result["expression_kind"] = "adapter_dispatched_macro"
            return result
        if re.match(r"^row_number\s*\(\s*\)\s*over\s*\(", expr, re.I):
            warnings.append("Window expression inputs and ordering are recorded, not proven by SQL compilation")
            return {"source": None, "expression_kind": "row_number_window", "expression": " ".join(expr.split())}
        raise Unsupported(f"Unresolved expression for {column}: {expr[:90]}")

    try:
        result = model_query(paths[0], target)
        return {"status": "candidate_lineage", "origin": result["source"],
                "expression_kind": result["expression_kind"], "computed_expression": result.get("expression"),
                "steps": steps, "warnings": warnings}
    except Unsupported as exc:
        return {"status": "needs_review", "origin": None, "steps": steps,
                "warnings": warnings + [str(exc)]}


def yaml_metric(repo, model_name, metric_name):
    for file in (repo / "models").rglob("*.yml"):
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        for model in data.get("models", []):
            if model["name"] == model_name:
                matches = [m for m in model.get("metrics", []) if m["name"] == metric_name]
                if len(matches) != 1:
                    raise Unsupported("Metric definition missing or ambiguous")
                return model, matches[0], str(file.relative_to(repo))
    raise Unsupported("Model YAML missing")


def evaluate(repo, expected_commit):
    commit = repository_commit(repo)
    if commit != expected_commit:
        raise ValueError(f"Expected {expected_commit}, found {commit}")
    cases = []
    for model_name, metric_name in (("orders", "order_total"),
                                    ("order_items", "revenue"),
                                    ("orders", "new_customer_orders")):
        model, metric, evidence = yaml_metric(repo, model_name, metric_name)
        expression = metric.get("expr", metric_name)
        record = {"metric": metric_name, "model": model_name, "yaml_evidence": evidence,
                  "aggregation": metric.get("agg"), "metric_expression": expression,
                  "filter": metric.get("filter"), "measure_lineage": None,
                  "filter_lineage": None, "relationship_label": "not_evaluated"}
        if isinstance(expression, str) and IDENT.fullmatch(expression):
            record["measure_lineage"] = trace(repo, model_name, expression)
        elif expression == 1:
            record["measure_lineage"] = {"status": "constant_one", "origin": None}
        else:
            record["measure_lineage"] = {"status": "needs_review", "origin": None,
                                         "warnings": ["Complex YAML metric expression"]}
        if metric.get("filter"):
            match = re.fullmatch(r"\s*\{\{\s*Dimension\('([^']+)'\)\s*}}\s*=\s*1\s*", metric["filter"])
            entity_key = next((c["name"] for c in model.get("columns", [])
                               if isinstance(c.get("entity"), dict) and c["entity"].get("type") == "primary"), None)
            if match and entity_key and match[1].startswith(entity_key + "__"):
                column = match[1][len(entity_key) + 2:]
                record["filter_lineage"] = trace(repo, model_name, column)
                record["filter_lineage"]["unresolved_semantic_filter"] = metric["filter"].strip()
                record["filter_lineage"]["warnings"].append("MetricFlow Dimension binding was inferred from text, not compiled")
            else:
                record["filter_lineage"] = {"status": "needs_review", "origin": None,
                                            "warnings": ["Unresolved MetricFlow filter"]}
        cases.append(record)
    return {"corpus": "dbt-labs/jaffle-shop", "commit": commit,
            "scope": "three selected metric paths in source SQL, without dbt compilation or data reconciliation",
            "cases": cases}


def check(report):
    a, b, c = report["cases"]
    assert a["measure_lineage"]["origin"] == "ecom.raw_orders.order_total"
    assert a["measure_lineage"]["expression_kind"] == "adapter_dispatched_macro"
    assert b["measure_lineage"]["origin"] == "ecom.raw_products.price"
    assert b["measure_lineage"]["expression_kind"] == "adapter_dispatched_macro"
    joined = next(s for s in b["measure_lineage"]["steps"] if s["scope"] == "joined")
    assert joined["join_predicate"] == "order_items.product_id = products.product_id"
    assert c["measure_lineage"]["status"] == "constant_one"
    assert c["filter_lineage"]["expression_kind"] == "row_number_window"
    assert "partition by customer_id" in c["filter_lineage"]["computed_expression"].lower()
    assert "order by ordered_at asc" in c["filter_lineage"]["computed_expression"].lower()
    assert all(case["relationship_label"] == "not_evaluated" for case in report["cases"])
    try:
        selected_expression("a.*, b.*", "some_column")
    except Unsupported:
        pass
    else:
        raise AssertionError("Ambiguous star should not be traced")


def markdown(report):
    a, b, c = report["cases"]
    lines = ["# Selected dbt lineage paths at pinned revision", "",
             f"Public corpus: `dbt-labs/jaffle-shop` at `{report['commit']}`.",
             "The script traces three selected metrics through a documented SQL subset and records candidate origins. It does not compile dbt, execute source rows, validate join cardinality, or assign metric relationship labels.", "",
             "| Metric | Observed candidate path | Remaining uncertainty |",
             "| --- | --- | --- |",
             f"| `order_total` | `orders.order_total` → `stg_orders.order_total` → `ecom.raw_orders.order_total` | `cents_to_dollars` is adapter-dispatched; star pass-through is inspected only in this subset. |",
             f"| `revenue` | `order_items.product_price` → `stg_products.product_price` → `ecom.raw_products.price` | Join `{next(s['join_predicate'] for s in b['measure_lineage']['steps'] if 'join_predicate' in s)}` has no row-level cardinality check; conversion macro uncompiled. |",
             f"| `new_customer_orders` | `SUM(1)` filtered by `customer_order_number = 1`, whose SQL expression is `row_number() over (partition by customer_id order by ordered_at asc)` | MetricFlow Dimension binding and tie behavior remain unverified. |",
             "", "All three relationships to other metrics remain `not_evaluated`. These manually selected probes are not extraction coverage or matcher accuracy estimates. Detailed file and CTE evidence appears in `public_lineage_report.json`.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = evaluate(args.repo.resolve(), args.expected_commit)
    if args.check:
        check(report)
    (ROOT / "public_lineage_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_lineage_report.md").write_text(markdown(report), encoding="utf-8")
    print("Traced three selected metric paths: " + ", ".join(
        f"{case['metric']}={case['measure_lineage']['status']}" for case in report["cases"])
        + ("; pinned-path checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
