#!/usr/bin/env python3
"""Check the frozen development comparison's boundaries, not its match quality.

No labels, held-out source, warehouse data, or prior method decisions are read.
Run with the pinned SQLGlot environment used by the AST comparator.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from compiled_ast_lineage_baseline import _normal_ast, _outer, _parse, sqlglot
from compiled_jaffle_packet import sha256
from run_compiled_development_comparison import (
    EXPECTED_PACKET_SHA256, EXPECTED_PAIR_SET_SHA256, _validate, generate,
)


HERE = Path(__file__).resolve().parent
PACKET = HERE / "compiled_jaffle_i1_packet.json"


def main() -> None:
    assert sqlglot is not None and sqlglot.__version__ == "30.20.0", "pinned SQLGlot required"
    packet_bytes = PACKET.read_bytes()
    assert sha256(packet_bytes) == EXPECTED_PACKET_SHA256
    packet = json.loads(packet_bytes)
    assert packet["pair_set_sha256"] == EXPECTED_PAIR_SET_SHA256

    # Parse every distinct query, including the grouped-offset metric that has
    # no comparable peer in this revision's full pair frame.
    for card in packet["cards"]:
        tree = _parse(card["compiled_sql"])
        _outer(tree, card["sql_scope"])
        _normal_ast(tree)

    report = generate(PACKET)
    rows = report["rows"]
    assert len(rows) == len({r["pair_id"] for r in rows}) == 171
    assert {r["pair_id"] for r in rows} == {p["pair_id"] for p in packet["pairs"]}
    assert sum(not r["scope_compatible"] for r in rows) == 18
    assert report["parser"] == {"name": "sqlglot", "version": "30.20.0", "dialect": "duckdb"}
    assert "run_compiled_development_comparison.py" in report["method_sha256"]
    assert "compiled_proposed_method.py" in report["method_sha256"]
    assert "compiled_proposed_development_contract.md" in report["method_sha256"]
    assert report["numeric_eligibility_counts"] == {"eligible_declaration_only": 9, "unknown": 10}
    for method, anchors in report["candidate_ranking_by_anchor_comparable_only"].items():
        assert len(anchors) == 18, method
        for anchor, partners in anchors.items():
            assert anchor not in partners and len(partners) == len(set(partners)) == 17, (method, anchor)
    for row in rows:
        for key in ("ast_lineage_i1", "constraint_aware_i1", "proposed_i1"):
            assert row[key]["decision"] == "abstain"  # Current unverified numeric eligibility.
            score = row[key].get("candidate_score")
            assert score is None or isinstance(score, (int, float)) and 0 <= score <= 1
            if not row["scope_compatible"]:
                assert row[key]["signal"] == "incompatible_generated_scope"
                assert score is None

    compatible = [row for row in rows if row["scope_compatible"]]
    for row in compatible:
        checks = row["constraint_aware_i1"]["prerequisites"]
        assert checks["base_population"]["state"] == "unknown"
        deps = checks["manifest_dependency_alignment"]
        assert (deps["state"] == "verified") == (deps["left"] == deps["right"])
        if row["constraint_aware_i1"]["signal"] == "cross_model_source_expression":
            assert row["constraint_aware_i1"]["candidate_score"] == 0

    by_names = {(r["a"].rsplit(".", 1)[-1], r["b"].rsplit(".", 1)[-1]): r for r in rows}
    same_scalar = by_names[("cumulative_revenue", "revenue")]
    assert same_scalar["ast_lineage_i1"]["syntax_decision"] == "same_ast"
    assert same_scalar["ast_lineage_i1"]["decision"] == "abstain"
    assert same_scalar["proposed_i1"]["signal"] == "time_semantics_review"
    assert by_names[("drink_orders", "food_orders")]["constraint_aware_i1"]["signal"] == "documented_filter_variant"
    assert by_names[("drink_orders", "food_orders")]["proposed_i1"]["signal"] == "filter_scope_review"
    assert by_names[("order_gross_profit", "order_total")]["ast_lineage_i1"]["decision"] == "abstain"
    assert by_names[("order_cost", "order_gross_profit")]["proposed_i1"]["signal"] == "declared_input_review"
    assert all(not r["proposed_i1"].get("candidate_hypothesis")
               for r in rows if r["proposed_i1"]["signal"] == "same_model_review")

    # Certification of numeric eligibility alone must not turn generated SQL
    # and unresolved grain/NULL/missing-group/join/snapshot facts into a label.
    from compiled_ast_lineage_baseline import compare as ast_compare
    from compiled_constraint_baseline import compare as constraint_compare
    from compiled_proposed_method import compare as proposed_compare
    named = {card["metric_name"]: card for card in packet["cards"]}
    order = dict(named["orders"], numeric_eligibility_status="certified_numeric")
    new_order = dict(named["new_customer_orders"], numeric_eligibility_status="certified_numeric")
    assert ast_compare(order, new_order)["decision"] == "abstain"
    assert constraint_compare(order, new_order)["decision"] == "abstain"
    assert proposed_compare(order, new_order)["decision"] == "abstain"
    bare_a = dict(order, source_status="verified_ungrouped", grain="order",
                  units="count", snapshot_state="current", join_cardinality="no_join",
                  missing_group_rule="zero", null_policy="zero")
    bare_b = dict(new_order, source_status="verified_ungrouped", grain="order",
                  units="count", snapshot_state="current", join_cardinality="no_join",
                  missing_group_rule="zero", null_policy="zero")
    assert ast_compare(bare_a, bare_b)["decision"] == "abstain"
    try:
        _validate("injected", {"signal": "forged", "decision": "direct_equivalent",
                               "candidate_score": 1.0, "evidence": [], "reason": "unsupported"})
    except ValueError as exc:
        assert "unsupported on the frozen development packet" in str(exc)
    else:
        raise AssertionError("the frozen runner accepted an unauthenticated semantic decision")

    # Even if a caller adds a worksheet, label, or altered SQL to a copy, the
    # comparison must reject it before either method sees the altered cards.
    with TemporaryDirectory() as tmp:
        modified = json.loads(packet_bytes)
        modified["cards"][0]["gold_label"] = "direct_equivalent"
        bad = Path(tmp) / "injected_packet.json"
        bad.write_text(json.dumps(modified))
        try:
            generate(bad)
        except ValueError as exc:
            assert "frozen label-free input" in str(exc)
        else:
            raise AssertionError("altered packet was accepted")
    print("verified three I1 methods, frozen frame, 19 parser inputs, 18 per-anchor rankings, scope/abstention controls, and tamper rejection")


if __name__ == "__main__":
    main()
