#!/usr/bin/env python3
"""A bounded, synthetic metric-card comparison pilot; see README for limits."""

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = ("concept", "source_measure", "expression_kind", "grain", "filters",
            "time_rule", "business_state", "unit")


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def query_values(db, view):
    # The view name is sourced from a local card, not external SQL input.
    if not view.replace("_", "").isalnum():
        raise ValueError("Unexpected view name")
    rows = db.execute(f"SELECT entity_key, value FROM {view} ORDER BY entity_key").fetchall()
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate entity key in view {view}")
    return dict(rows)


def compared_values(left, right):
    differences = [{"entity_key": key, "left": left.get(key), "right": right.get(key)}
                   for key in sorted(left.keys() | right.keys())
                   if left.get(key) != right.get(key)]
    return {"equal_sample_values": not differences, "sample_differences": differences,
            "left_values": left, "right_values": right}


def downstream_of(metric_key, dependencies):
    reached, frontier = set(), [metric_key]
    while frontier:
        current = frontier.pop()
        for model, parents in dependencies.items():
            if current in parents and model not in reached:
                reached.add(model)
                frontier.append(model)
    return sorted(reached)


def decide(db, pair, cards, dependencies):
    left, right = cards[pair["left"]], cards[pair["right"]]
    values = compared_values(query_values(db, left["view"]),
                             query_values(db, right["view"]))
    result = {"pair_id": pair["id"], "left": left["name"], "right": right["name"],
              "left_evidence": left["evidence_location"],
              "right_evidence": right["evidence_location"], **values}

    missing = [f"{side}.{key}" for side, card in (("left", left), ("right", right))
               for key in REQUIRED if card.get(key) is None]
    if missing:
        result.update(label="needs_review", reason=f"Missing card fields: {', '.join(missing)}")
        return result

    if left.get("metric_key") == right.get("metric_key") and left.get("version") != right.get("version") and left.get("metric_key"):
        changed = [key for key in REQUIRED if left[key] != right[key]]
        result.update(label="candidate_definition_drift" if changed else "needs_review",
                      reason=f"Simulated version change; changed signature fields: {', '.join(changed) or 'none'}",
                      changed_fields=changed,
                      downstream_models=downstream_of(left["metric_key"], dependencies))
        return result

    if left["concept"] != right["concept"]:
        result.update(label="non_match", reason="Distinct annotated business concepts; sample counts may coincide")
        return result

    if "mapping_check_sql" in pair:
        aligned = (left["grain"] == right["grain"] and
                   left["time_rule"] == right["time_rule"] and
                   left["business_state"] == right["business_state"] and
                   left["unit"] == right["unit"] and
                   left["expression_kind"] == right["expression_kind"] == "sum" and
                   right.get("native_grain") is not None and
                   right["native_grain"] != right["grain"])
        mapping = [{"entity_key": entity, "mappings": n}
                   for entity, n in db.execute(pair["mapping_check_sql"]).fetchall() if n != 1]
        result["mapping_violations"] = mapping
        result["mapping_evidence"] = pair["mapping_evidence"]
        if mapping:
            result.update(label="needs_review", reason="Eligible detail rows lack exactly one hierarchy mapping")
        elif not aligned:
            result.update(label="needs_review", reason="Required rollup signature fields do not align")
        elif not values["equal_sample_values"]:
            result.update(label="needs_review", reason="Mapped sample values do not reconcile")
        else:
            result.update(label="provisional_cross_grain_equivalent",
                          reason="One mapping per eligible opportunity and matching sample rollup; source rules and historical snapshots still need independent validation")
        return result

    if left["business_state"] != right["business_state"] or left["time_rule"] != right["time_rule"] or left["filters"] != right["filters"]:
        fields = [key for key in ("business_state", "time_rule", "filters") if left[key] != right[key]]
        result.update(label="temporal_or_scope_variant", reason=f"Annotated rules differ: {', '.join(fields)}")
        return result

    direct_fields = ("source_measure", "expression_kind", "grain", "filters", "time_rule", "business_state", "unit")
    if all(left[key] == right[key] for key in direct_fields):
        if values["equal_sample_values"]:
            result.update(label="direct_equivalent", reason="Cards identify one source measure and aligned rules; sample rows agree")
        else:
            result.update(label="needs_review", reason="Cards suggest a direct alias but sample rows disagree")
    else:
        result.update(label="needs_review", reason="Insufficient supported reconciliation for the shared concept")
    return result


def markdown(results):
    descriptions = {
        "P1_alias": "Opportunity booking passthrough and `total_` alias",
        "P2_rollup": "Account ARR and filtered opportunity ARR rollup",
        "P3_live_vs_booking": "Updated live product quote and frozen booking",
        "P4_filter_change": "Pipeline stage filter expanded in simulated v1",
        "P5_fanout": "Rollup using a duplicated hierarchy mapping",
        "P6_missing_time": "Account views agree, but one card omits time",
        "P7_equal_counts": "Customer and product counts happen to agree",
    }
    lines = ["# Synthetic pilot evidence", "",
             "All seven cases are constructed; their labels are not an accuracy estimate.", "",
             "| Case | Decision | Sample values | Key observation |",
             "| --- | --- | --- | --- |"]
    for r in results:
        if r["sample_differences"]:
            example = r["sample_differences"][0]
            sample = f"{example['entity_key']}: {example['left']} vs {example['right']}"
        else:
            key = sorted(r["left_values"])[0]
            sample = f"{key}: {r['left_values'][key]} = {r['right_values'][key]}"
        reason = r["reason"].replace("|", "\\|")
        lines.append(f"| {descriptions[r['pair_id']]} | `{r['label']}` | {sample} | {reason} |")
    lines.extend(["", "The alias is supported by supplied cards and SQL in this fixture. The cross-grain decision is **provisional**: the mapping check and matching rows establish only a sample result. The fanout and missing-time cases abstain. The pipeline change is a **candidate** drift, not a claim that the change was unintended.", "",
                  "Downstream models flagged for the constructed pipeline change: `sales_pipeline_dashboard`, `executive_forecast`. This dependency graph was provided by hand.", "",
                  "Run `python3 pilot.py --check` to recreate the machine-readable `report.json`. See `README.md` for scope and limitations.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify hand-labeled, critical scenarios")
    args = parser.parse_args()
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT / "sql/fixture.sql").read_text(encoding="utf-8"))
    db.executescript((ROOT / "sql/metric_views.sql").read_text(encoding="utf-8"))
    cards = {card["id"]: card for card in read_json("cards.json")}
    config = read_json("pairs.json")
    results = [decide(db, pair, cards, config["model_dependencies"]) for pair in config["pairs"]]
    report = {"fixture": "publicly shareable, synthetic SQLite rows",
              "method": "hand-authored cards; hand-selected pairs; guarded decisions; finite sample reconciliation",
              "results": results}
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "report.md").write_text(markdown(results), encoding="utf-8")
    if args.check:
        expected = read_json("expected.json")
        assert set(expected) == {r["pair_id"] for r in results}, "Fixture pairs and expectations diverged"
        for r in results:
            for field, value in expected[r["pair_id"]].items():
                assert r.get(field) == value, f"{r['pair_id']} {field}: {r.get(field)!r} != {value!r}"
    print(f"{len(results)} constructed cases; labels: " + ", ".join(f"{r['pair_id']}={r['label']}" for r in results))
    print("Wrote report.json and report.md" + ("; scenario checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
