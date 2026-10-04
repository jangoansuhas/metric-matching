#!/usr/bin/env python3
"""Build a label-free, same-input GTM metric packet from pinned source and compiled artifacts.

This bounded adapter emits syntactic evidence, not semantic labels or row checks.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

from extract_dbt_metric_branches import COMMIT, MODEL, extract


ROOT = Path(__file__).resolve().parent
DEFAULT_REPO = ROOT.parent / "public_corpus" / "gtm-funnel-analytics"
SOURCE_REPORT = "dbt_metric_branches_report.json"
FIELD_REPORT = "compiled_metric_fields_report.json"
OUTPUT = "conditional_evidence_packet.json"
SUMMARY = "conditional_evidence_packet.md"
UNKNOWNS = ("join_cardinality", "null_policy", "missing_groups", "time_zone",
            "units", "snapshot", "grouping_set_expansion")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_source(repo: Path) -> str:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != COMMIT:
        raise ValueError(f"Checkout at {head}, expected {COMMIT}")
    return subprocess.run(["git", "-C", str(repo), "show", f"{COMMIT}:{MODEL}"],
                          capture_output=True, text=True, check=True).stdout


def branch_id(branch: dict) -> str:
    return f"{branch['metric_name']}@{branch['grain']}"


def indexing(branches: list[dict]) -> dict[str, dict]:
    found = {branch_id(b): b for b in branches}
    if len(found) != len(branches) or len(found) != 11:
        raise ValueError("Expected 11 unique metric_name@grain branches")
    if any(b.get("parse_status") == "unsupported" for b in branches):
        raise ValueError("Unsupported branch cannot silently enter packet")
    return found


def field_names(uses: list[dict]) -> list[str]:
    return sorted({u["use"]["field"] for u in uses if u.get("use", {}).get("field")})


def build(repo: Path) -> dict:
    source_bytes = (ROOT / SOURCE_REPORT).read_bytes()
    fields_bytes = (ROOT / FIELD_REPORT).read_bytes()
    source_report = json.loads(source_bytes)
    field_report = json.loads(fields_bytes)
    source_sql = git_source(repo)
    regenerated = extract(source_sql)
    if (source_report["source"]["commit"] != COMMIT or source_report["source"]["path"] != MODEL
            or regenerated["branches"] != source_report["branches"]):
        raise ValueError("Source branch report does not match pinned Git object")
    source = indexing(source_report["branches"])

    artifact = field_report["artifact_provenance"]
    if (artifact["git_head"] != COMMIT or artifact["source_branch_report_sha256"] != digest(source_bytes)
            or artifact["source_git_object_sha256"] != digest(source_sql.encode())):
        raise ValueError("Compiled field report provenance mismatch")
    manifest_path = repo / artifact["manifest"]
    manifest_bytes = manifest_path.read_bytes()
    if digest(manifest_bytes) != artifact["manifest_sha256"]:
        raise ValueError("dbt manifest changed")
    manifest = json.loads(manifest_bytes)
    node = manifest["nodes"][artifact["manifest_node"]]
    compiled_record = artifact["compiled_artifacts"][artifact["manifest_node"]]
    compiled_path = repo / compiled_record["path"]
    compiled_bytes = compiled_path.read_bytes()
    if (digest(compiled_bytes) != compiled_record["sha256"]
            or node["compiled_code"].strip() != compiled_bytes.decode().strip()):
        raise ValueError("Compiled metric artifact no longer matches manifest")
    compiled = indexing(extract(compiled_bytes.decode())["branches"])
    traced = {branch_id(b): b for b in field_report["branches"]}
    if set(source) != set(compiled) or set(source) != set(traced):
        raise ValueError("Source, compiled, and traced branch IDs differ")

    cards = []
    for ident in sorted(source):
        s, c, t = source[ident], compiled[ident], traced[ident]
        if s["ordinal"] != c["ordinal"] or s["ordinal"] != t["ordinal"]:
            raise ValueError(f"Branch order changed for {ident}")
        if (t["source_value"]["expression"] != s["expressions"]["value"]
                or t["compiled_value"]["expression"] != c["expressions"]["value"]):
            raise ValueError(f"Value trace mismatch for {ident}")
        if t["review_status"] != "needs_review":
            raise ValueError(f"Unexpected review status for {ident}")
        cards.append({
            "id": ident, "metric_name": s["metric_name"], "grain": s["grain"],
            "source_ref": s["source_ref"],
            "value_expr": c["expressions"]["value"], "where_expr": c["where"],
            "period_expr": c["expressions"]["period_start"],
            "segment_expr": c["expressions"]["segment"], "group_by": c["group_by"],
            "time_key": s["period_time_key"] or (s["time_filter_keys"][0] if len(s["time_filter_keys"]) == 1 else None),
            "value_input_fields": field_names(t["value_fields"]),
            "filter_input_fields": field_names(t["branch_filter_fields"]),
            "source_location": s["location"],
            "compiled_location": {"path": compiled_record["path"],
                                  "start_line": c["location"]["start_line"],
                                  "end_line": c["location"]["end_line"]},
            "review_flags": sorted(set(s["review_flags"] + t["review_flags"])),
            "unknown_semantics": {key: None for key in UNKNOWNS},
        })
    ids = [card["id"] for card in cards]
    pairs = [{"left_id": a, "right_id": b} for a, b in itertools.combinations(ids, 2)]
    if len(cards) != 11 or len(pairs) != 55:
        raise ValueError("Incomplete evidence packet")
    return {
        "schema_version": 1,
        "provenance": {
            "project": "jross21/gtm-funnel-analytics", "commit": COMMIT,
            "source_model": MODEL, "compiled_model": compiled_record["path"],
            "dbt_version": artifact["dbt_version"],
            "input_sha256": {SOURCE_REPORT: digest(source_bytes), FIELD_REPORT: digest(fields_bytes),
                             "source_git_object": digest(source_sql.encode()),
                             "manifest": digest(manifest_bytes), "compiled_model": digest(compiled_bytes)},
            "evidence_scope": "Pinned source branches and local compiled dbt artifacts; no row values or labels",
        },
        "cards": cards, "pairs": pairs,
    }


def markdown(packet: dict) -> str:
    lines = ["# Label-free GTM conditional-decision input", "",
             f"Pinned `{packet['provenance']['project']}@{COMMIT}`; dbt {packet['provenance']['dbt_version']}.",
             f"{len(packet['cards'])} branch cards and {len(packet['pairs'])} unordered pairs. The packet has no labels, row totals, or reconciliation outcomes.", "",
             "| ID | Source ref | Value expression | WHERE | Grain / grouping | Review |",
             "| --- | --- | --- | --- | --- | --- |"]
    for card in packet["cards"]:
        clean = lambda s: (s or "—").replace("\n", " ").replace("|", "\\|")
        lines.append(f"| `{card['id']}` | `{card['source_ref']}` | `{clean(card['value_expr'])}` | "
                     f"`{clean(card['where_expr'])}` | `{clean(card['group_by'])}` | "
                     f"{', '.join(card['review_flags']) or 'none'} |")
    lines += ["", "Each card also records the source and compiled lines, period and segment expressions, field-use names and seven explicitly unknown semantics in JSON. Refs and headers are syntactic provenance, and unexpanded grouping and unknown time/NULL/rounding rules prevent an equivalence assertion.", "",
              "The package requires the pinned repository and local dbt compiled artifacts to reproduce; these are outside the ZIP. See `conditional_method_contract.md` for the method boundary. Neither this table nor its ordering is a gold label or method feature.", ""]
    return "\n".join(lines)


def self_check() -> None:
    toy = [{"metric_name": "a", "grain": "month"},
           {"metric_name": "a", "grain": "window"}]
    assert branch_id(toy[0]) != branch_id(toy[1])
    assert field_names([{"use": {"field": "z"}}, {"use": {"field": "a"}},
                        {"use": {"field": "a"}}]) == ["a", "z"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--check", action="store_true", help="Verify regeneration without writing")
    args = parser.parse_args()
    self_check()
    packet = build(args.repo)
    rendered = {OUTPUT: json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
                SUMMARY: markdown(packet)}
    for filename, value in rendered.items():
        path = ROOT / filename
        if args.check:
            if path.read_text(encoding="utf-8") != value:
                raise ValueError(f"Stale output: {filename}")
        else:
            path.write_text(value, encoding="utf-8")
    print(f"{len(packet['cards'])} cards; {len(packet['pairs'])} pairs; "
          f"{'verified' if args.check else 'wrote packet'}")


if __name__ == "__main__":
    main()
