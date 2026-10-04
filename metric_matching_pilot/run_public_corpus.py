#!/usr/bin/env python3
"""Measure bounded extraction coverage on a pinned, public dbt repository."""

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import yaml

from extract_signatures import VIEW


ROOT = Path(__file__).resolve().parent
BARE_COLUMN = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def repository_commit(repo):
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def model_grain(model):
    keys = [column["name"] for column in model.get("columns", [])
            if isinstance(column.get("entity"), dict) and column["entity"].get("type") == "primary"]
    return keys[0] if len(keys) == 1 else None


def metric_record(metric, path, model=None):
    name = metric["name"]
    typ = metric.get("type")
    expr = metric.get("expr", name) if model else metric.get("expr")
    record = {"name": name, "model": model["name"] if model else None,
              "metric_type": typ, "aggregation": metric.get("agg"), "expression": expr,
              "filter": metric.get("filter"), "evidence_location": path,
              "source_measure": None, "grain_key": model_grain(model) if model else None,
              "time_dimension": model.get("agg_time_dimension") if model else None,
              "unit": None, "business_state": None, "status": "needs_review", "reasons": []}

    if typ != "simple" or model is None:
        record["reasons"].append("Derived, ratio, or cumulative metric requires dependency/expression resolution")
        record["inputs"] = metric.get("input_metrics", metric.get("input_metric"))
        return record

    if typ == "simple" and not metric.get("agg"):
        record["reasons"].append("Missing aggregation")
        return record

    if metric.get("filter"):
        record["reasons"].append("Metric filter contains unresolved dbt/MetricFlow template")
    if isinstance(expr, str) and BARE_COLUMN.fullmatch(expr):
        record["source_measure"] = f"{model['name']}.{expr}"
        defined_columns = {column["name"] for column in model.get("columns", [])}
        if expr not in defined_columns:
            record["reasons"].append("Expression column is absent from this model's YAML column metadata")
    elif expr == 1:
        record["expression_kind"] = "constant_one"
    else:
        record["reasons"].append("Complex expression requires SQL expression parser")
    if record["grain_key"] is None:
        record["reasons"].append("No unambiguous primary entity in model YAML")
    if record["time_dimension"] is None:
        record["reasons"].append("No aggregate time dimension in model YAML")

    if not record["reasons"]:
        record["status"] = "partial_signature"
        record["reasons"] = ["Business state, unit, and column lineage through model SQL are unverified"]
    return record


def evaluate(repo, expected_commit):
    commit = repository_commit(repo)
    if commit != expected_commit:
        raise ValueError(f"Wrong repository revision: expected {expected_commit}, got {commit}")
    model_dir = repo / "models"
    if not model_dir.is_dir():
        raise ValueError("No models directory in corpus")

    sql_results = []
    for path in sorted(model_dir.rglob("*.sql")):
        content = path.read_text(encoding="utf-8")
        matches = VIEW.findall(content)
        sql_results.append({"path": str(path.relative_to(repo)),
                            "fixture_view_declarations": len(matches),
                            "status": "partial_signature" if matches else "needs_review",
                            "reason": "No CREATE VIEW declaration; dbt model SQL needs its own grammar or compilation" if not matches else "Inspect view extraction separately"})

    metrics = []
    for path in sorted(model_dir.rglob("*.yml")):
        parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        location = str(path.relative_to(repo))
        for model in parsed.get("models", []):
            for metric in model.get("metrics", []):
                metrics.append(metric_record(metric, location, model))
        for metric in parsed.get("metrics", []):
            metrics.append(metric_record(metric, location))

    return {"corpus": "dbt-labs/jaffle-shop", "commit": commit,
            "pyyaml_version": yaml.__version__,
            "scope": "extraction from source SQL and native metric YAML; no compilation, rows, or classification",
            "sql_model_count": len(sql_results),
            "sql_fixture_grammar_count": sum(r["fixture_view_declarations"] > 0 for r in sql_results),
            "metric_count": len(metrics),
            "metric_type_counts": dict(sorted(Counter(r["metric_type"] for r in metrics).items())),
            "yaml_status_counts": dict(sorted(Counter(r["status"] for r in metrics).items())),
            "sql_models": sql_results, "metrics": metrics}


def check(report):
    assert report["sql_model_count"] == 13
    assert report["sql_fixture_grammar_count"] == 0
    assert report["metric_count"] == 23
    assert report["metric_type_counts"] == {"cumulative": 1, "derived": 3, "ratio": 2, "simple": 17}
    metric = {r["name"]: r for r in report["metrics"]}
    assert metric["order_total"]["status"] == "partial_signature"
    assert metric["order_total"]["source_measure"] == "orders.order_total"
    assert metric["order_total"]["grain_key"] == "order_id"
    assert metric["revenue"]["source_measure"] == "order_items.product_price"
    assert metric["revenue"]["grain_key"] == "order_item_id"
    for name in ("food_revenue", "new_customer_orders", "average_order_value"):
        assert metric[name]["status"] == "needs_review", name
    assert metric["new_customer_orders"]["filter"] is not None


def markdown(report):
    metric = {r["name"]: r for r in report["metrics"]}
    examples = [("order_total", "Simple SUM yields a partial signature at order grain."),
                ("revenue", "Referenced product_price is absent from this model's YAML columns."),
                ("food_revenue", "CASE expression requires an expression parser."),
                ("new_customer_orders", "MetricFlow filter template remains unresolved."),
                ("average_order_value", "Derived metric needs its input graph resolved.")]
    lines = ["# Pinned public corpus extraction test", "",
             f"Repository: dbt-labs/jaffle-shop at `{report['commit']}`.",
             f"Environment: Python with PyYAML {report['pyyaml_version']}; no dbt build, warehouse, or row execution.", "",
             "| Diagnostic | Observed result |", "| --- | ---: |",
             f"| dbt SQL model files matching fixture CREATE VIEW grammar | {report['sql_fixture_grammar_count']} / {report['sql_model_count']} |",
             f"| Metric definitions in YAML | {report['metric_count']} |",
             f"| Partial metric signatures | {report['yaml_status_counts'].get('partial_signature', 0)} |",
             f"| Metric definitions requiring review | {report['yaml_status_counts'].get('needs_review', 0)} |", "",
             "| Metric | Status | Boundary observed |", "| --- | --- | --- |"]
    for name, explanation in examples:
        item = metric[name]
        lines.append(f"| `{name}` | `{item['status']}` | {explanation} |")
    lines.extend(["", "Every partial signature still lacks verified business state, unit, and model SQL column lineage. No pair classification or matching accuracy was measured. The repository revision is a public example, not an independently labeled benchmark. Source files remain in their upstream repository; this artifact records extraction observations only.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = evaluate(args.repo.resolve(), args.expected_commit)
    if args.check:
        check(report)
    output = ROOT / "public_corpus_report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_corpus_report.md").write_text(markdown(report), encoding="utf-8")
    print(f"Pinned {report['corpus']}@{report['commit']}: "
          f"{report['sql_fixture_grammar_count']}/{report['sql_model_count']} SQL models match fixture grammar; "
          f"{report['metric_count']} YAML metrics, {report['yaml_status_counts']}"
          + ("; boundary checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
