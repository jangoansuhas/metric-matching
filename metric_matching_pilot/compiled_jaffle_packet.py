#!/usr/bin/env python3
"""Freeze one label-free I1 evidence packet from the pinned Jaffle development build.

This packet is for development diagnostics only. It does not create reference
labels, infer metric equivalence, or inspect a held-out repository.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path


VERSION = "compiled_jaffle_i1_packet_v2"
COMMIT = "7be2c5838dbdeca8e915d4e46db70e910753d7f6"
ADAPTER_SHA256 = "7b90ef37dfb1cce9c0a15f211ef89fb56106a0f1eb8817ed0ae405ad05ce09fe"
MANIFEST_SHA256 = "8cb6b5d2241c629b92b04bd87c10e39d57f88c6a996f3ec624d0042876811d42"
SEMANTIC_SHA256 = "bfcc846a7e4425056d61cfaec2c1857f9328544315a18f83e075c09c36896e51"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def checked_bytes(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    actual = sha256(data)
    if actual != expected:
        raise ValueError(f"{path}: expected SHA-256 {expected}, got {actual}")
    return data


def _source_models(manifest: dict, input_measures: list[dict]) -> list[dict]:
    names = sorted({node for measure in input_measures
                    for owner in measure.get("owners", [])
                    for node in owner.get("model_node", [])})
    models = []
    for name in names:
        node = manifest["nodes"].get(name)
        if node is None or node.get("resource_type") != "model":
            raise ValueError(f"missing model node {name}")
        models.append({
            "node": name,
            "source_file": node.get("original_file_path"),
            "raw_sql": node.get("raw_code"),
            "depends_on": sorted(node.get("depends_on", {}).get("nodes", [])),
            "raw_sql_sha256": sha256((node.get("raw_code") or "").encode("utf-8")),
        })
    return models


def build(bundle: Path) -> dict:
    meta = json.loads((bundle / "run_metadata.json").read_text())
    if meta.get("commit") != COMMIT or meta.get("adapter_script_sha256") != ADAPTER_SHA256:
        raise ValueError("source commit or adapter version changed")
    checked_bytes(bundle / "inputs" / "run_adapter.py", ADAPTER_SHA256)
    manifest = json.loads(checked_bytes(bundle / "manifests" / "manifest.json", MANIFEST_SHA256))
    semantic = json.loads(checked_bytes(bundle / "manifests" / "semantic_manifest.json", SEMANTIC_SHA256))
    source_bytes = (bundle / "provenance.json").read_bytes()
    source = json.loads(source_bytes)
    if len(source) != len(semantic["metrics"]) or len(source) != 19:
        raise ValueError("expected complete 19-metric development inventory")
    metric_nodes = {node["name"]: (uid, node) for uid, node in manifest["metrics"].items()}
    cards = []
    for record in source:
        name = record["metric"]
        uid, node = metric_nodes[name]
        if record["declared_file"] != node["original_file_path"]:
            raise ValueError(f"declaration path mismatch: {name}")
        if sorted(record["manifest_depends_on"] or []) != sorted(node.get("depends_on", {}).get("nodes", [])):
            raise ValueError(f"manifest dependency mismatch: {name}")
        successful = [attempt for attempt in record["explain_attempts"] if attempt.get("sql_file")]
        if len(successful) != 1:
            raise ValueError(f"expected one generated SQL for {name}")
        attempt = successful[0]
        sql_path = bundle / attempt["sql_file"]
        sql = checked_bytes(sql_path, attempt["sql_sha256"]).decode("utf-8")
        scope = "metric_time" if attempt["group_by"] == "metric_time" else "ungrouped"
        status = ("verified_metric_time_only" if scope == "metric_time" else "verified_ungrouped")
        if record["compiled_sql_status"] != status:
            raise ValueError(f"SQL scope mismatch for {name}")
        measures = record["input_measures"]
        if any(measure["owner_count"] != 1 or len(measure["owners"]) != 1 for measure in measures):
            raise ValueError(f"ambiguous measure ownership for {name}")
        cards.append({
            "metric_id": uid,
            "metric_name": name,
            "name": name,
            "declared_file": record["declared_file"],
            "declared_span_text_located": record["declared_span_text_located"],
            "description": record["description"],
            "type": record["type"],
            "metric_filter": record["metric_filter"],
            "type_params_expr": record["type_params_expr"],
            "numerator": record["numerator"],
            "denominator": record["denominator"],
            "input_metrics": record["input_metrics"],
            "cumulative_type_params": record["cumulative_type_params"],
            "input_measures": measures,
            "manifest_depends_on": record["manifest_depends_on"],
            "source_models": _source_models(manifest, measures),
            "compiled_sql": sql,
            "compiled_sql_sha256": attempt["sql_sha256"],
            "sql_scope": scope,
            "source_status": "metricflow_sql_generated_not_executed",
            "numeric_eligibility_status": "not_certified_by_compiled_bundle",
            # These are not inferred from names, one finite output, or a dbt ref.
            "grain": None,
            "units": None,
            "snapshot_state": None,
            "join_cardinality": None,
            "missing_group_rule": None,
            "null_policy": None,
        })
    cards.sort(key=lambda card: card["metric_id"])
    ids = [card["metric_id"] for card in cards]
    if len(set(ids)) != 19:
        raise ValueError("duplicate metric IDs")
    scope_by_id = {card["metric_id"]: card["sql_scope"] for card in cards}
    pairs = [{"pair_id": f"{a}||{b}", "a": a, "b": b,
              "target_scope": scope_by_id[a] if scope_by_id[a] == scope_by_id[b] else None,
              "scope_compatible": scope_by_id[a] == scope_by_id[b]}
             for a, b in itertools.combinations(ids, 2)]
    if len(pairs) != 171:
        raise ValueError("expected full 19 choose 2 pair frame")
    return {
        "packet_version": VERSION,
        "source_commit": COMMIT,
        "adapter_sha256": ADAPTER_SHA256,
        "source_sha256": {"manifest": MANIFEST_SHA256, "semantic_manifest": SEMANTIC_SHA256,
                          "provenance": sha256(source_bytes)},
        "metric_count": len(cards),
        "pair_count": len(pairs),
        "pair_set_sha256": sha256(canonical([pair["pair_id"] for pair in pairs])),
        "scope_policy": "Compare only identical generated SQL scopes; otherwise abstain. No other time-grouped SQL was generated.",
        "cards": cards,
        "pairs": pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, default=Path(__file__).resolve().parent.parent / "metric_provenance_verification")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("compiled_jaffle_i1_packet.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = canonical(build(args.bundle))
    if args.check:
        if args.output.read_bytes() != data:
            raise SystemExit("development packet differs from frozen output")
        print("development packet OK", sha256(data))
    else:
        args.output.write_bytes(data)
        print("wrote", args.output, "sha256", sha256(data))


if __name__ == "__main__":
    main()
