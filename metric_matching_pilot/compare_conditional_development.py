#!/usr/bin/env python3
"""Compare fixed same-input development decisions, then inspect separate public rows.

Row observations never enter the method packet or the three decision scripts.
Run with DuckDB 1.4.4 and PyYAML available for the two public checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from verify_public_positive_candidate import verify as verify_jaffle


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / "public_corpus" / "gtm-funnel-analytics"
JAFFLE = ROOT.parent / "public_corpus" / "jaffle-shop-sidemantic"
DATABASE = REPO / "arcline_singlethread.duckdb"
PACKET = "conditional_evidence_packet.json"
METHODS = ("normalized_sql_lineage_report.json", "constraint_aware_report.json",
           "conditional_decision_report.json")
OUTPUT = "conditional_development_comparison.json"
MARKDOWN = "conditional_development_comparison.md"
DECISIONS = {"direct_candidate", "conditional_candidate", "scope_variant_candidate",
             "related_candidate", "abstain"}
EXAMPLES = (
    ("pipeline_created@month", "pipeline_created@window"),
    ("mql_volume@month", "mql_volume@window"),
    ("mql_to_sal_rate@window", "sal_to_sql_rate@window"),
    ("pipeline_created@window", "sla_compliance@window"),
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pair_key(left: str, right: str) -> tuple[str, str]:
    if left == right:
        raise ValueError("Self-pair")
    return tuple(sorted((left, right)))


def method_reports() -> tuple[dict, dict, dict]:
    raw = (ROOT / PACKET).read_bytes()
    packet = json.loads(raw)
    ids = {card["id"] for card in packet["cards"]}
    expected = {pair_key(p["left_id"], p["right_id"]) for p in packet["pairs"]}
    if len(ids) != 11 or len(expected) != 55:
        raise ValueError("Packet universe changed")
    reports = {}
    for path in METHODS:
        report = json.loads((ROOT / path).read_bytes())
        if report["input_sha256"] != sha(raw):
            raise ValueError(f"Input packet hash mismatch: {path}")
        results = report["results"]
        indexed = {pair_key(r["left_id"], r["right_id"]): r for r in results}
        if len(results) != 55 or set(indexed) != expected:
            raise ValueError(f"Incomplete or duplicated pair results: {path}")
        for r in results:
            if r["decision"] not in DECISIONS or r["evidence_status"] not in (
                    "sufficient_for_source_candidate", "needs_review"):
                raise ValueError(f"Unsupported decision/status in {path}")
            if not isinstance(r["conditions"], dict) or not isinstance(r["reasons"], list):
                raise ValueError(f"Missing per-pair evidence in {path}")
        name = report["method"]
        if name in reports:
            raise ValueError("Duplicate method name")
        reports[name] = {"file": path, "sha256": sha((ROOT / path).read_bytes()),
                         "decision_counts": dict(sorted(Counter(r["decision"] for r in results).items())),
                         "status_counts": dict(sorted(Counter(r["evidence_status"] for r in results).items())),
                         "indexed": indexed}
    if len(reports) != 3:
        raise ValueError("Expected three full-context methods")
    return packet, reports, {"packet_sha256": sha(raw), "cards": len(ids), "pairs": len(expected)}


def months_inclusive(start: date, end: date) -> list[date]:
    if start > end:
        raise ValueError("Inverted analysis window")
    out = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        out.append(date(year, month, 1))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return out


def source_window(cards: list[dict]) -> list[date]:
    branch = next(c for c in cards if c["id"] == "pipeline_created@month")
    dates = re.findall(r"cast\('([0-9]{4}-[0-9]{2}-[0-9]{2})' as date\)", branch["where_expr"] or "", re.I)
    if len(dates) != 2:
        raise ValueError("Window bounds not supported by this sample check")
    return months_inclusive(date.fromisoformat(dates[0]), date.fromisoformat(dates[1]))


def built_rows(packet: dict, database: Path) -> dict:
    import duckdb

    periods = source_window(packet["cards"])
    cards = {c["id"]: c for c in packet["cards"]}
    window_filter_evidence = {}
    for metric in ("pipeline_created", "mql_volume"):
        month, window = cards[f"{metric}@month"], cards[f"{metric}@window"]
        explicitly_aligned = bool(window["where_expr"] and window["time_key"]
                                  and window["where_expr"] == month["where_expr"]
                                  and window["time_key"] == month["time_key"])
        window_filter_evidence[metric] = {
            "window_where_expr": window["where_expr"],
            "window_time_key": window["time_key"],
            "same_explicit_time_filter_as_month": explicitly_aligned,
            "interpretation": (
                "matching explicit time filters are visible; partition and rounding still need review"
                if explicitly_aligned else
                "a constant period label does not restrict source rows; bounded membership is unverified"),
        }
    connection = duckdb.connect(str(database), read_only=True)
    rows = connection.execute(
        "SELECT metric_name, grain, period_start, segment, value FROM fct_metric_values "
        "WHERE metric_name IN ('pipeline_created', 'mql_volume')"
    ).fetchall()
    connection.close()
    observations = {}
    for metric in ("pipeline_created", "mql_volume"):
        subset = [r for r in rows if r[0] == metric]
        segments = sorted({r[3] for r in subset if r[1] == "window"})
        cases = []
        for segment in segments:
            monthly = [r for r in subset if r[1] == "month" and r[3] == segment]
            window = [r for r in subset if r[1] == "window" and r[3] == segment]
            if len(window) != 1 or len({r[2] for r in monthly}) != len(monthly):
                raise ValueError(f"Unexpected built rows for {metric} / {segment}")
            bounded = [r for r in monthly if r[2] in periods]
            absent = [p.isoformat() for p in periods if p not in {r[2] for r in bounded}]
            extra = sorted({r[2].isoformat() for r in monthly if r[2] not in periods})
            if metric == "pipeline_created":
                cents = lambda x: int((Decimal(str(x)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
                month_total = sum(cents(r[4]) for r in monthly)
                bounded_total = sum(cents(r[4]) for r in bounded)
                window_total = cents(window[0][4])
                unit = "cents"
            else:
                if any(r[4] != int(r[4]) for r in monthly + window):
                    raise ValueError("Nonintegral MQL count")
                month_total = sum(int(r[4]) for r in monthly)
                bounded_total = sum(int(r[4]) for r in bounded)
                window_total = int(window[0][4])
                unit = "count"
            cases.append({"segment": segment, "month_rows": len(monthly),
                          "expected_months": len(periods), "absent_months": absent,
                          "extra_months": extra, "monthly_sum": month_total,
                          "bounded_monthly_sum": bounded_total,
                          "all_history_monthly_sum": month_total,
                          "window_value": window_total,
                          "delta": month_total - window_total,
                          "bounded_delta": bounded_total - window_total, "unit": unit,
                          "zero_fill_condition": "absent month row contributes zero when rolling up"})
        observations[metric] = cases
    return {"scope": "GTM local dbt-built synthetic rows; finite observed results",
            "database": database.name, "periods": [p.isoformat() for p in periods],
            "window_filter_evidence": window_filter_evidence, "metrics": observations}


def generate(database: Path, jaffle_repo: Path) -> dict:
    packet, reports, counts = method_reports()
    examples = []
    for a, b in EXAMPLES:
        key = pair_key(a, b)
        examples.append({"pair": [a, b], "methods": {
            name: {field: report["indexed"][key][field]
                   for field in ("decision", "evidence_status", "conditions", "reasons")}
            for name, report in reports.items()}})
    sample = verify_jaffle(jaffle_repo)["sample"]
    return {"purpose": "post_output_development_check_not_gold_or_effectiveness",
            "common_universe": counts,
            "methods": {name: {k: v for k, v in report.items() if k != "indexed"}
                        for name, report in reports.items()},
            "examples_selected_after_method_outputs": examples,
            "observations_outside_method_inputs": {
                "gtm": built_rows(packet, database),
                "jaffle": {"status": "previously_inspected_separate_development_case",
                           "semantic_commit": "8686fe3ea0fd4ceffa08e523a422331bd228ac32",
                           "dbt_submodule_commit": "7be2c5838dbdeca8e915d4e46db70e910753d7f6",
                           "orders": sample["orders"], "orders_without_items": sample["orders_without_items"],
                           "null_sensitive_order_differences": sample["orders_with_null_sensitive_item_subtotal_mismatch"],
                           "after_outer_join_and_coalesce_differences": sample["orders_with_coalesced_item_subtotal_mismatch"],
                           "daily_dates": sample["dates_compared"],
                           "daily_differences": sample["dates_with_different_values"]}},
            "limits": ["No independent human gold for all 55 pairs; decision disagreements cannot be scored as errors or wins.",
                       "Same-input source packets are a bounded GTM model; Jaffle NULL check is a separate selected case.",
                       "Finite row reconciliation is not a universal semantic equivalence proof.",
                       "No Snowflake, native cross-engine comparison, industrial sample, or reviewer-time study was run."]}


def render(r: dict) -> str:
    lines = ["# Conditional method comparison on public development cases", "",
             f"Same label-free packet SHA-256 `{r['common_universe']['packet_sha256']}`; "
             f"{r['common_universe']['cards']} cards and {r['common_universe']['pairs']} pairs.",
             "Methods see the same cards and candidate pairs. Decisions are source-backed **candidates**, not gold relationships.", "",
             "| Method | Decisions | Evidence status |", "| --- | --- | --- |"]
    for name, m in r["methods"].items():
        lines.append(f"| `{name}` | " + ", ".join(f"{k}: {v}" for k, v in m["decision_counts"].items())
                     + " | " + ", ".join(f"{k}: {v}" for k, v in m["status_counts"].items()) + " |")
    lines += ["", "## Development examples after outputs were fixed", "",
              "| Pair | " + " | ".join(f"`{name}`" for name in r["methods"]) + " |",
              "| --- | " + " | ".join("---" for _ in r["methods"]) + " |"]
    for case in r["examples_selected_after_method_outputs"]:
        cells = [f"`{case['methods'][name]['decision']}` ({case['methods'][name]['evidence_status']})"
                 for name in r["methods"]]
        lines.append("| `" + "` ↔ `".join(case["pair"]) + "` | " + " | ".join(cells) + " |")
    gtm = r["observations_outside_method_inputs"]["gtm"]
    lines += ["", "## Row checks kept outside the methods", "",
              "The local GTM synthetic build covers " + ", ".join(gtm["periods"]) + ". "
              "The table sums rounded monthly pipeline cents and counts monthly MQLs before comparing each window scalar. "
              "The bounded sum uses only the displayed seven-month range; all-month sum uses every available monthly row.", "",
              "| Metric | Segment | Month rows | Missing months | Extra months | Bounded sum | All-month sum | Window | Bounded difference | Unit |",
              "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for metric, cases in gtm["metrics"].items():
        for case in cases:
            lines.append(f"| `{metric}` | {case['segment']} | {case['month_rows']} | "
                         f"{', '.join(case['absent_months']) or 'none'} | "
                         f"{', '.join(case['extra_months']) or 'none'} | "
                         f"{case['bounded_monthly_sum']} | {case['all_history_monthly_sum']} | "
                         f"{case['window_value']} | {case['bounded_delta']} | {case['unit']} |")
    mql_extra = sorted({p for c in gtm["metrics"]["mql_volume"] for p in c["extra_months"]})
    lines += ["", "The pipeline window has the same explicit date predicate as its month branch. "
              "The MQL window has no explicit date filter or time key; its constant period label does not bound source rows. " +
              ("No extra MQL month occurs in this build, so the bounded and all-month sums coincide only on this sample. "
               if not mql_extra else f"Extra MQL months occur: {', '.join(mql_extra)}. ") +
              "An added out-of-range MQL row could change the window value while leaving the proposed bounded monthly sum unchanged."]
    j = r["observations_outside_method_inputs"]["jaffle"]
    lines += ["", f"The separate Jaffle development check has {j['orders_without_items']} orders without items: "
              f"{j['null_sensitive_order_differences']} order-level NULL-versus-zero differences before an outer join and COALESCE, "
              f"{j['after_outer_join_and_coalesce_differences']} afterward; "
              f"{j['daily_differences']} differing daily totals across {j['daily_dates']} dates. "
              "It is not part of the GTM pair universe or any method's input.", "",
              "**Interpretation:** Differences in candidate outputs show decisions under bounded syntax and unknown prerequisites, not method accuracy or incremental novelty. A real comparison needs a frozen method, stronger baselines at the same input budget, and independent adjudication on held-out complete anchor universes.", "",
              "Reproduce with DuckDB 1.4.4 and PyYAML after the pinned GTM build and Jaffle clone: "
              "`python3 metric_matching_pilot/compare_conditional_development.py --check`.", ""]
    return "\n".join(lines)


def self_check() -> None:
    assert months_inclusive(date(2025, 12, 1), date(2026, 2, 28)) == [
        date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)]
    assert pair_key("b", "a") == ("a", "b")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--jaffle-repo", type=Path, default=JAFFLE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    self_check()
    report = generate(args.database, args.jaffle_repo)
    outputs = {OUTPUT: json.dumps(report, indent=2, ensure_ascii=False) + "\n",
               MARKDOWN: render(report)}
    for name, content in outputs.items():
        path = ROOT / name
        if args.check:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Stale comparison report: {name}")
        else:
            path.write_text(content, encoding="utf-8")
    print(f"{len(report['methods'])} methods, 55 GTM pairs; "
          f"{'verified' if args.check else 'wrote reports'}")


if __name__ == "__main__":
    main()
