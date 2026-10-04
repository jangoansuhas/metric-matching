#!/usr/bin/env python3
"""Audit independent public rollup/alias examples and a real metric-code change."""

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

import duckdb
import yaml


ROOT = Path(__file__).resolve().parent
GTM_COMMIT = "a71232c123a5fb78da9b52d4246950ee48591c00"
RILL_COMMIT = "c35c312174431273726a1d6cfc030717babe5a88"
CHANGE = "10a9bce8f0181623d8c596fbed7df37244666cc4"
PARENT = "3516d3d144979d23ceded2a1a72efcbddd452800"
RILL_PATH = "rill-openrtb-prog-ads/metrics/bids_metrics.yaml"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def anchor(repo, commit, path, snippet):
    lines = git(repo, "show", f"{commit}:{path}").splitlines()
    positions = [i for i, line in enumerate(lines, 1) if snippet in line]
    if not positions:
        raise ValueError(f"Missing expected source at {commit}:{path}: {snippet}")
    return f"https://github.com/{'jross21/gtm-funnel-analytics' if repo.name == 'gtm-funnel-analytics' else 'rilldata/rill-examples'}/blob/{commit}/{path}#L{positions[0]}"


def check(gtm, rill):
    gtm, rill = gtm.resolve(), rill.resolve()
    if git(gtm, "rev-parse", "HEAD") != GTM_COMMIT or git(rill, "rev-parse", "HEAD") != RILL_COMMIT:
        raise ValueError("Public checkout is not at its pinned revision")
    if git(rill, "rev-parse", f"{CHANGE}^") != PARENT:
        raise ValueError("Historical Rill parent is not pinned")
    subprocess.run(["git", "-C", str(rill), "merge-base", "--is-ancestor", CHANGE, "HEAD"], check=True)

    metric = next(m for m in yaml.safe_load((gtm / "metrics_catalog.yml").read_text())["metrics"]
                  if m["name"] == "pipeline_created")
    if (metric["expected"]["value"], metric["maps_to"]["model"]) != (6884381.39, "fct_opportunities"):
        raise ValueError("GTM catalog metric changed")
    gtm_sql = (gtm / "models/marts/metrics/fct_metric_values.sql").read_text()
    where = "where is_net_new_pipeline and created_month between {{ window_start }} and {{ window_end }}"
    if gtm_sql.count(where) != 2:
        raise ValueError("Monthly and window branch filters differ from pinned source")
    recon_sql = (gtm / "models/marts/reconciliation/rpt_metric_reconciliation.sql").read_text()
    if "from canon_pipeline as c" not in recon_sql or "c.value as canonical_value" not in recon_sql:
        raise ValueError("The canonical report is no longer a direct projection")

    results = json.loads((gtm / "target/run_results.json").read_text())
    statuses = {entry["unique_id"]: entry["status"] for entry in results["results"]}
    for name, status in [("model.arcline.fct_metric_values", "success"),
                         ("model.arcline.rpt_metric_reconciliation", "success"),
                         ("test.arcline.assert_metric_values_match_catalog", "pass"),
                         ("test.arcline.assert_recon_canonical_is_reconciled", "pass")]:
        if statuses.get(name) != status:
            raise ValueError(f"Required dbt result missing: {name} expected {status}")
    database = gtm / "arcline_singlethread.duckdb"
    con = duckdb.connect(str(database), read_only=True)
    try:
        rollups = con.execute("""SELECT COALESCE(m.segment, w.segment) AS segment,
               m.month_count, m.month_total, w.value,
               ROUND(m.month_total - w.value, 2) AS difference
            FROM (SELECT segment, COUNT(*) AS month_count, ROUND(SUM(value), 2) AS month_total
                  FROM main.fct_metric_values
                  WHERE metric_name = 'pipeline_created' AND grain = 'month'
                  GROUP BY segment) m
            FULL JOIN (SELECT segment, value FROM main.fct_metric_values
                       WHERE metric_name = 'pipeline_created' AND grain = 'window') w
            USING(segment) ORDER BY segment""").fetchall()
        alias = con.execute("""SELECT v.value, r.variant_value, r.canonical_value, r.abs_delta
            FROM main.fct_metric_values v JOIN main.rpt_metric_reconciliation r
              ON v.metric_name = r.metric_name
            WHERE v.metric_name = 'pipeline_created' AND v.grain = 'window'
              AND v.segment = 'All' AND r.variant_key = 'canonical'""").fetchall()
        other_variants = con.execute("""SELECT COUNT(*) FROM main.rpt_metric_reconciliation
            WHERE metric_name = 'pipeline_created' AND variant_key <> 'canonical'
            AND abs_delta <> 0""").fetchone()[0]
    finally:
        con.close()
    if len(alias) != 1 or len(rollups) != 4 or any(row[4] is None or row[4] != 0 for row in rollups):
        raise ValueError("GTM positive relationships did not reconcile")
    if any(value != 6884381.39 for value in alias[0][:3]) or alias[0][3] != 0 or other_variants != 4:
        raise ValueError("GTM canonical alias or negative controls changed")

    older = yaml.safe_load(git(rill, "show", f"{PARENT}:{RILL_PATH}"))
    newer = yaml.safe_load(git(rill, "show", f"{CHANGE}:{RILL_PATH}"))
    before = {measure["name"]: measure["expression"].strip() for measure in older["measures"]}
    after = {measure["name"]: measure["expression"].strip() for measure in newer["measures"]}
    expected = {
        "ctr": ("sum(click_reg_cnt)*1.0/sum(imp_cnt)",
                "sum(click_reg_cnt)*1.0/nullif(sum(imp_cnt),0)"),
        "ecpm": ("sum(media_spend_usd)*1.0/1000/sum(imp_cnt)",
                 "sum(media_spend_usd)*1.0/1000/nullif(sum(imp_cnt),0)"),
    }
    if {name: (before[name], after[name]) for name in expected} != expected:
        raise ValueError("Pinned historical measure change differs from expected")
    other_changes = sorted(name for name in before.keys() & after.keys()
                           if before[name] != after[name] and name not in expected)
    if other_changes:
        raise ValueError(f"Other measure expressions changed in the historical commit: {other_changes}")
    demo = duckdb.connect()
    try:
        sample = []
        for numerator, denominator in [(3, 4), (1, 0), (0, 0)]:
            old, new = demo.execute("SELECT ? * 1.0 / ?, ? * 1.0 / NULLIF(?,0)",
                                    [numerator, denominator, numerator, denominator]).fetchone()
            sample.append({"numerator": numerator, "denominator": denominator,
                           "without_guard": None if old is None else str(old),
                           "with_guard": None if new is None else str(new)})
    finally:
        demo.close()

    return {
        "public_projects": ["jross21/gtm-funnel-analytics", "rilldata/rill-examples"],
        "gtm": {"commit": GTM_COMMIT,
                "corpus_kind": "synthetic and explicitly designed for metric reconciliation",
                "dbt_result_counts": dict(Counter(statuses.values())),
                "monthly_to_window": [{"segment": row[0], "monthly_rows": row[1],
                                       "monthly_total": str(row[2]), "window_value": str(row[3]),
                                       "difference": str(row[4])} for row in rollups],
                "canonical_alias": {"source_value": str(alias[0][0]),
                                    "reconciliation_variant": str(alias[0][1]),
                                    "reconciliation_canonical": str(alias[0][2]),
                                    "difference": str(alias[0][3])},
                "noncanonical_pipeline_variants_with_nonzero_delta": other_variants,
                "source_links": {
                    "catalog": anchor(gtm, GTM_COMMIT, "metrics_catalog.yml", "name: pipeline_created"),
                    "monthly": anchor(gtm, GTM_COMMIT, "models/marts/metrics/fct_metric_values.sql", "'pipeline_created', 'month'"),
                    "window": anchor(gtm, GTM_COMMIT, "models/marts/metrics/fct_metric_values.sql", "'pipeline_created', 'window'"),
                    "alias": anchor(gtm, GTM_COMMIT, "models/marts/reconciliation/rpt_metric_reconciliation.sql", "'Canonical (this repo)'"),
                },
                "interpretation": "Cross-grain reconciliation of two computations of the same KPI, plus a direct downstream alias; these are designed development positives, not independent enterprise duplicates or held-out gold labels."},
        "rill": {"head": RILL_COMMIT, "before_commit": PARENT, "after_commit": CHANGE,
                 "expression_changes": {name: {"before": pair[0], "after": pair[1],
                                               "before_link": anchor(rill, PARENT, RILL_PATH, f'expression: "{pair[0]}"'),
                                               "after_link": anchor(rill, CHANGE, RILL_PATH, f'expression: "{pair[1]}"')}
                                        for name, pair in expected.items()},
                 "duckdb_1_4_4_constructed_demo": sample,
                 "status": "real_commit_changes_zero_denominator_behavior_source_verified_data_unexecuted",
                 "limit": "The Rill parquet sources were not loaded; this DuckDB fixture illustrates the expression-level behavior, not observed production rows or a Rill runtime result."},
    }


def markdown(report):
    g, r = report["gtm"], report["rill"]
    lines = ["# Independent public-project audit: positive controls and real metric change", "",
             f"**GTM source.** [jross21/gtm-funnel-analytics](https://github.com/jross21/gtm-funnel-analytics/tree/{g['commit']}) is an unrelated but synthetic, deliberately reconciled Salesforce/HubSpot example. With dbt-core 1.11.6, dbt-duckdb 1.10.1, DuckDB 1.4.4 and one dbt thread, the local build recorded 44 successful nodes, 111 passing tests and 8 no-op exposures. The model tables reopened and were queried in DuckDB. An alternate local profile omits a redundant ICU download; the source metric SQL is unchanged.", "",
             "| `pipeline_created` segment | Month rows | Sum of monthly values ($) | Window value ($) | Difference ($) |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for row in g["monthly_to_window"]:
        lines.append(f"| {row['segment']} | {row['monthly_rows']} | {row['monthly_total']} | {row['window_value']} | {row['difference']} |")
    a=g["canonical_alias"]
    lines += ["", f"The separate reconciliation table's `canonical` row republishes the `All` window metric: source {a['source_value']}, reported variant {a['reconciliation_variant']}, reported canonical {a['reconciliation_canonical']}, delta {a['difference']}. Four intentionally naive pipeline variants have nonzero deltas. The month and window branches use the same filters; the month-to-window relationship is a **designed cross-grain reconciliation**, while the report row is a **direct lineage alias**, not a separately computed duplicate.", "",
              "Pinned GTM evidence: " + "; ".join(f"[{key}]({url})" for key, url in g["source_links"].items()) + ".", "",
              f"**Rill history.** [rilldata/rill-examples](https://github.com/rilldata/rill-examples/commit/{r['after_commit']}) has a real historical change from `{r['before_commit']}` to `{r['after_commit']}` in `rill-openrtb-prog-ads/metrics/bids_metrics.yaml`. Both `ctr` and `ecpm` gained `NULLIF(sum(imp_cnt),0)` in their denominators:", "",
              "| Measure | Earlier expression | Later expression |", "| --- | --- | --- |"]
    for name, item in r["expression_changes"].items():
        lines.append(f"| `{name}` | [`{item['before']}`]({item['before_link']}) | [`{item['after']}`]({item['after_link']}) |")
    lines += ["", "A constructed DuckDB 1.4.4 division check returned `0.75` for `3/4` both ways, `inf` versus NULL for `1/0`, and `nan` versus NULL for `0/0`. Thus the change preserves ordinary nonzero-denominator values but alters zero-denominator behavior in that SQL engine. We did not load Rill's remote parquet or run the Rill service; actual source-row frequency and impact are unknown.", "",
              "**Paper status.** These two independent public projects add a cross-grain positive control, a direct alias control, and a real versioned edge-case change to the development set. They are synthetic/examples, selected after inspection, and not held-out or independently adjudicated. Do not claim matching accuracy, prevalence, enterprise scale, or demonstrated superiority from them.", ""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gtm-repo",type=Path,required=True)
    parser.add_argument("--rill-repo",type=Path,required=True)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    result=check(args.gtm_repo,args.rill_repo)
    if args.check:
        assert len(result["gtm"]["monthly_to_window"]) == 4
        assert all(float(x["difference"]) == 0 for x in result["gtm"]["monthly_to_window"])
        assert result["gtm"]["canonical_alias"]["source_value"] == "6884381.39"
        assert result["rill"]["duckdb_1_4_4_constructed_demo"][1]["with_guard"] is None
    (ROOT/"unrelated_public_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    (ROOT/"unrelated_public_audit.md").write_text(markdown(result))
    print("GTM: 4 matching segment rollups and 1 direct alias; Rill: 2 changed expressions"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
