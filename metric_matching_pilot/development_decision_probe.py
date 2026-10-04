#!/usr/bin/env python3
"""One-rule, fail-closed signal probe over the frozen public development packet.

Run: python -B metric_matching_pilot/development_decision_probe.py
Writes only the adjacent Markdown report. No evaluation labels are read.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent / "public_corpus/jaffle-shop-sidemantic/jaffle-shop"
PACKET = HERE / "compiled_jaffle_i1_packet.json"
REPORT = HERE / "development_decision_probe_report.md"
PACKET_SHA256 = "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb"
MASK = re.compile(r"case\s+when\s+([A-Za-z_]\w*)\s+then\s+([A-Za-z_]\w*)\s+else\s+0\s+end", re.I)
IDENT = re.compile(r"[A-Za-z_]\w*\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def anchor(path: str, span: list[int]) -> str:
    return f"{path}:{span[0]}–{span[1]}"


def verify_packet() -> dict:
    raw = PACKET.read_bytes()
    check(sha(raw) == PACKET_SHA256, "frozen packet hash changed")
    packet = json.loads(raw)
    commit = packet["source_commit"]
    check(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip() == commit,
          "development commit changed")
    cards, pairs = packet["cards"], packet["pairs"]
    check(len(cards) == packet["metric_count"] == 19 and len(pairs) == packet["pair_count"] == 171,
          "denominator changed")
    ids = [c["metric_id"] for c in cards]
    expected = [f"{a}||{b}" for a, b in itertools.combinations(ids, 2)]
    check(ids == sorted(set(ids)) and [p["pair_id"] for p in pairs] == expected,
          "pair inventory changed")
    canonical = (json.dumps(expected, sort_keys=True, separators=(",", ":")) + "\n").encode()
    check(sha(canonical) == packet["pair_set_sha256"], "pair-set hash changed")

    source_cache: dict[str, str] = {}
    def source(path: str) -> str:
        check(path.startswith("models/") and ".." not in Path(path).parts, f"source path: {path}")
        if path not in source_cache:
            pinned = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO)
            check((REPO / path).read_bytes() == pinned, f"source differs from commit: {path}")
            source_cache[path] = pinned.decode()
        return source_cache[path]

    def span(path: str, loc: list[int]) -> str:
        lines = source(path).splitlines()
        check(len(loc) == 2 and 1 <= loc[0] <= loc[1] <= len(lines), f"invalid span: {path}:{loc}")
        return "\n".join(lines[loc[0] - 1:loc[1]])

    for card in cards:
        name = card["metric_name"]
        check(sha(card["compiled_sql"].encode()) == card["compiled_sql_sha256"], f"SQL hash: {name}")
        text = span(card["declared_file"], card["declared_span_text_located"])
        check(re.search(r"(?m)^\s*- name:\s*" + re.escape(name) + r"\s*$", text) is not None
              and re.search(r"(?m)^\s*type:\s*" + re.escape(card["type"]) + r"\s*$", text) is not None,
              f"metric declaration span: {name}")
        for measure in card["input_measures"]:
            check(measure["owner_count"] == len(measure["owners"]) == 1, f"owner ambiguity: {name}")
            owner = measure["owners"][0]
            excerpt = span(owner["semantic_model_file"], owner["measure_span"])
            check(re.search(r"(?m)^\s*- name:\s*" + re.escape(measure["measure"]) + r"\s*$", excerpt) is not None
                  and re.search(r"(?m)^\s*agg:\s*" + re.escape(owner["agg"]) + r"\s*$", excerpt) is not None,
                  f"measure source span: {name}")
            if owner["expr"] is not None:
                check("expr: " + owner["expr"] in excerpt, f"expression source span: {name}")
        for model in card["source_models"]:
            check(sha(model["raw_sql"].encode()) == model["raw_sql_sha256"], f"model hash: {name}")
            check(source(model["source_file"]).strip() == model["raw_sql"], f"model source: {name}")
    by_id = {c["metric_id"]: c for c in cards}
    for pair in pairs:
        a, b = by_id[pair["a"]], by_id[pair["b"]]
        same = a["sql_scope"] == b["sql_scope"]
        check(pair["scope_compatible"] is same and pair["target_scope"] == (a["sql_scope"] if same else None),
              f"scope inventory: {pair['pair_id']}")
    return packet


def simple_sum(card: dict) -> tuple[dict, dict] | None:
    if card["type"] != "simple" or card["sql_scope"] != "ungrouped" or card["metric_filter"] is not None:
        return None
    if len(card["input_measures"]) != 1:
        return None
    measure = card["input_measures"][0]
    owner = measure["owners"][0]
    if (measure["filter"] is not None or measure["fill_nulls_with"] is not None
            or measure["join_to_timespine"] or owner["agg"] != "sum"
            or owner["non_additive_dimension"] is not None or owner["expr"] is None):
        return None
    # Full match excludes a hidden WHERE, JOIN, or second aggregation.
    pattern = (r"\ASELECT\s+SUM\(" + re.escape(owner["expr"]) + r"\)\s+AS\s+"
               + re.escape(card["metric_name"]) + r"\s+FROM\s+"
               + re.escape(owner["node_relation"]) + r"\s+[A-Za-z_]\w*\s*\Z")
    return (measure, owner) if re.fullmatch(pattern, card["compiled_sql"], re.I) else None


def probe_signal(a: dict, b: dict) -> tuple[str, str, str]:
    sa, sb = simple_sum(a), simple_sum(b)
    if sa and sb:
        for masked, plain, x, y in ((a, b, sa, sb), (b, a, sb, sa)):
            mask_owner, base_owner = x[1], y[1]
            match = MASK.fullmatch(mask_owner["expr"])
            same = all(mask_owner[k] == base_owner[k] for k in
                       ("semantic_model", "model_node", "node_relation", "agg_time_dimension"))
            if (match and IDENT.fullmatch(base_owner["expr"]) and match.group(2) == base_owner["expr"]
                    and same and mask_owner["agg_time_dimension"] and mask_owner["model_node"]
                    and mask_owner["node_relation"] and masked["source_models"] == plain["source_models"]):
                flag = match.group(1)
                check(any(re.search(r"\b" + re.escape(flag) + r"\b", m["raw_sql"])
                          for m in masked["source_models"]), "flag absent from owner model")
                model_evidence = ", ".join(
                    f"`{m['source_file']}` SHA-256 `{m['raw_sql_sha256']}`"
                    for m in masked["source_models"]
                )
                return ("conditional_scope_hypothesis", "conditional_mask",
                        f"`{mask_owner['expr']}` at "
                        f"`{anchor(mask_owner['semantic_model_file'], mask_owner['measure_span'])}` vs "
                        f"`{base_owner['expr']}` at "
                        f"`{anchor(base_owner['semantic_model_file'], base_owner['measure_span'])}`; "
                        f"flag `{flag}`; same owner/model/time "
                        f"`{mask_owner['semantic_model']}` / `{mask_owner['node_relation']}` / "
                        f"`{mask_owner['agg_time_dimension']}`; generated SQL hashes "
                        f"`{masked['compiled_sql_sha256']}` / `{plain['compiled_sql_sha256']}`; "
                        f"owner model {model_evidence} mentions the flag. "
                        "Missing: upstream flag lineage to the source field and classification rule; "
                        "verified boolean type/truth semantics; aligned grouped MetricFlow SQL and time grain; "
                        "null and missing-group policy. Price sign assumptions would also be needed for "
                        "any numeric ordering claim. This is a structural hypothesis, not a taxonomy decision.")
    if {a["type"], b["type"]} == {"simple", "cumulative"}:
        simple, cumulative = (a, b) if a["type"] == "simple" else (b, a)
        if (len(simple["input_measures"]) == len(cumulative["input_measures"]) == 1
                and simple["input_measures"][0]["measure"] == cumulative["input_measures"][0]["measure"]):
            return ("none", "cumulative_no_time_evidence",
                    f"Shared measure `{simple['input_measures'][0]['measure']}`; generated scopes "
                    f"`{simple['sql_scope']}` / `{cumulative['sql_scope']}` do not show a common "
                    "time-grain cumulative transform.")
    if a["sql_scope"] != b["sql_scope"]:
        return "none", "scope_mismatch", "Generated SQL scopes differ; no common compiled grouping."
    for derived, other in ((a, b), (b, a)):
        if derived["type"] == "derived" and other["metric_id"] in derived["manifest_depends_on"]:
            return ("none", "derived_rule_deferred",
                    f"Exact manifest input edge `{other['metric_id']}` in "
                    f"`{derived['metric_id']}`; expression `{derived['type_params_expr']}`. "
                    "A more specific transform has not been ruled out by this one-rule probe.")
    def summary(card: dict) -> str:
        measures = ", ".join(
            f"{m['owners'][0]['agg']}({m['owners'][0]['expr'] or m['measure']})"
            for m in card["input_measures"]
        )
        return f"{card['type']} [{measures}]"
    return ("none", "outside_rule",
            f"`{summary(a)}` vs `{summary(b)}`; conditional-mask prerequisites not met.")


def main() -> None:
    packet = verify_packet()
    cards = {c["metric_id"]: c for c in packet["cards"]}
    rows = [(cards[p["a"]], cards[p["b"]]) for p in packet["pairs"]]
    outcomes = [(a, b, *probe_signal(a, b)) for a, b in rows]
    counts = Counter(row[2] for row in outcomes)
    reasons = Counter(row[3] for row in outcomes if row[2] == "none")
    check(len(outcomes) == 171 == sum(counts.values()), "incomplete denominator")
    hypotheses = [r for r in outcomes if r[2] == "conditional_scope_hypothesis"]
    check(len(hypotheses) + counts["none"] == 171 and sum(reasons.values()) == counts["none"],
          "signal/abstention count mismatch")
    hypothesis_rows = "\n".join(
        f"| `{a['metric_name']}` ↔ `{b['metric_name']}` | `{signal}` | `abstain` | {detail} |"
        for a, b, signal, _, detail in hypotheses
    ) or "| none | — | — |"
    inventory = "\n".join(
        f"| `{a['metric_name']}` ↔ `{b['metric_name']}` | `{signal}` | `abstain` | `{code}` | "
        f"`{anchor(a['declared_file'], a['declared_span_text_located'])}`; "
        f"`{anchor(b['declared_file'], b['declared_span_text_located'])}` — {detail} |"
        for a, b, signal, code, detail in outcomes
    )
    abstentions = "\n".join(f"| `{code}` | {n} |" for code, n in sorted(reasons.items()))
    REPORT.write_text(f"""# One-rule development decision probe

Frozen packet: `compiled_jaffle_i1_packet.json`, SHA-256 `{PACKET_SHA256}`; public source commit `{packet['source_commit']}`. All **19 cards / 171 pairs** were retained (pair-set SHA-256 `{packet['pair_set_sha256']}`). Per-card generated SQL and source-model hashes, pinned source text and declaration/measure spans, and pair scope fields passed the script's checks. This probe reads no held-out source or worksheet and makes no human-gold, equivalence, or method-superiority claim.

## Signal rule and classification status

The only signal rule recognizes simple unfiltered `SUM(CASE WHEN flag THEN x ELSE 0 END)` versus simple unfiltered `SUM(x)` with identical owner, model, relation, aggregation time, and verified single-SUM SQL at the shared ungrouped scope. This emits a **conditional scope hypothesis**, not `temporal_or_scope_variant` or any other committed semantic taxonomy decision. The owner model mentions the flag, but the packet does not establish its full upstream lineage, boolean type, or classification rule. Grouped MetricFlow SQL, aligned time/grain, null and missing-group handling, and any price-sign premise for numeric ordering also remain unverified. Derived and cumulative rules are deferred; the shared ungrouped cumulative scalar does not establish a temporal relation.

**Candidate signals: {len(hypotheses)} / 171. No-candidate abstentions: {counts['none']} / 171. Committed semantic decisions: 0 / 171. Scored classification: all 171 undecided (`abstain`).**

| Pair | Candidate signal | Semantic decision | Exact expression, source spans, and missing prerequisites |
| --- | --- | --- | --- |
{hypothesis_rows}

| No-candidate reason | Pairs |
| --- | ---: |
{abstentions}

## Complete 171-pair inventory

Every pair remains semantically undecided. Each row gives both pinned metric declaration spans and its source-linked signal or no-candidate reason. Exact measure spans and SQL hashes for hypotheses are above.

| Pair | Candidate signal | Semantic decision | Reason | Source-linked basis |
| --- | --- | --- | --- | --- |
{inventory}
""")
    print(f"wrote {REPORT}")
    print(f"pairs=171 hypotheses={len(hypotheses)} no_candidate={counts['none']} "
          f"semantic_decisions=0 undecided=171; reasons={dict(sorted(reasons.items()))}")


if __name__ == "__main__":
    main()
