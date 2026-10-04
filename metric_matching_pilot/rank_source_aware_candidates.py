#!/usr/bin/env python3
"""Development-only candidate rankings on the pinned GTM metric-branch universe.

All unordered pairs are scored without labels or observed data. Source matches are
literal syntactic clues, not evidence that metric values are interchangeable.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

# Import only the existing lexical scoring functions; do not create bytecode files.
sys.dont_write_bytecode = True
from run_development_baselines import ALGORITHM_VERSION as NAME_VERSION  # noqa: E402
from run_development_baselines import METHODS as NAME_METHODS  # noqa: E402
from run_development_baselines import scores as name_scores  # noqa: E402


ROOT = Path(__file__).resolve().parent
INPUT = "dbt_metric_branches_report.json"
PINNED_COMMIT = "a71232c123a5fb78da9b52d4246950ee48591c00"
PINNED_PATH = "models/marts/metrics/fct_metric_values.sql"
METHODS = (*NAME_METHODS, "source_aware")
FEATURES = ("name_tokens", "source_ref", "value", "where", "period_start", "segment", "grain")
ALGORITHM_VERSION = "gtm_source_aware_candidates_v1"
TEMPLATE = re.compile(r"\{[{%]|[}%]\}")
KNOWN_FLAGS = frozenset({"field_lineage_not_traced", "grouping_sets_not_expanded",
                         "jinja_not_expanded", "dbt_macro_not_expanded"})


def branch_id(branch: dict) -> str:
    name, grain = branch["metric_name"], branch["grain"]
    if not isinstance(name, str) or not name or not isinstance(grain, str) or not grain:
        raise ValueError("Every branch requires a nonempty metric_name and grain")
    return f"{name}@{grain}"


def inventory(source: dict) -> dict[str, dict]:
    if (source["source"]["commit"] != PINNED_COMMIT
            or source["source"]["path"] != PINNED_PATH):
        raise ValueError("GTM source revision changed; review the probe before ranking")
    branches = source["branches"]
    if (len(branches) != 11 or source["counts"]["union_all_branches"] != 11
            or len({b["ordinal"] for b in branches}) != 11):
        raise ValueError("The pinned 11-branch universe changed; review before ranking")
    indexed = {branch_id(branch): branch for branch in branches}
    if len(indexed) != 11:
        raise ValueError("Duplicate metric_name+grain branch ID")
    return dict(sorted(indexed.items()))


def usable(branch: dict) -> bool:
    """Unexpected extraction/flags or missing source fields cause source abstention."""
    expressions = branch.get("expressions")
    return (branch.get("parse_status") == "extracted"
            and branch.get("grain") in ("month", "window")
            and isinstance(branch.get("source_ref"), str) and bool(branch["source_ref"])
            and not TEMPLATE.search(branch["source_ref"])
            and isinstance(expressions, dict)
            and all(isinstance(expressions.get(field), str) and expressions[field]
                    for field in ("value", "period_start", "segment"))
            and (branch.get("where") is None or isinstance(branch["where"], str))
            and isinstance(branch.get("review_flags"), list)
            and all(isinstance(flag, str) and flag in KNOWN_FLAGS
                    for flag in branch["review_flags"]))


def evidence_flags(left: dict, right: dict) -> list[str]:
    flags = set()
    source_text = []
    for branch in (left, right):
        reported = branch.get("review_flags")
        if isinstance(reported, list):
            flags.update(flag for flag in reported if isinstance(flag, str))
        else:
            flags.add("missing_review_flags")
        expressions = branch.get("expressions")
        if isinstance(expressions, dict):
            source_text.extend(expressions.values())
        source_text.append(branch.get("where"))
    if left.get("grouping_sets") or right.get("grouping_sets"):
        flags.add("grouping_sets_not_expanded")
    if (left.get("macro_calls_unexpanded") or right.get("macro_calls_unexpanded")):
        flags.add("dbt_macro_not_expanded")
    if any(TEMPLATE.search(value) for value in source_text if isinstance(value, str)):
        flags.add("jinja_not_expanded")
    if left.get("field_lineage") != "traced" or right.get("field_lineage") != "traced":
        flags.add("field_lineage_not_traced")
    return sorted(flags)


def literal_match(left: str | None, right: str | None) -> int | None:
    """No SQL normalization; null WHERE on both sides means shared local absence."""
    if any(TEMPLATE.search(value) for value in (left, right) if value is not None):
        return None  # Do not award credit for matching unexpanded template text.
    return int(left == right)


def source_score(left: dict, right: dict, token_score: float) -> dict:
    flags = evidence_flags(left, right)
    if not usable(left) or not usable(right):
        return {"score": None, "feature_scores": None, "unscored_features": list(FEATURES),
                "evidence_status": "abstained_unsupported_extraction", "evidence_flags": flags,
                "relationship_decision": "abstain"}
    comparisons = {
        "name_tokens": token_score,
        "source_ref": literal_match(left["source_ref"], right["source_ref"]),
        "value": literal_match(left["expressions"]["value"], right["expressions"]["value"]),
        "where": literal_match(left["where"], right["where"]),
        "period_start": literal_match(left["expressions"]["period_start"],
                                      right["expressions"]["period_start"]),
        "segment": literal_match(left["expressions"]["segment"],
                                 right["expressions"]["segment"]),
        "grain": int(left["grain"] == right["grain"]),
    }
    # Equal, predeclared weights. Unscored template fields contribute zero; the
    # denominator stays fixed so missing evidence never increases a score.
    value = round(sum(comparisons[f] or 0 for f in FEATURES) / len(FEATURES), 6)
    unscored = [field for field in FEATURES if comparisons[field] is None]
    unexpanded = any(flag.endswith("not_expanded") for flag in flags)
    return {"score": value, "feature_scores": comparisons,
            "unscored_features": unscored,
            "evidence_status": ("unexpanded_syntax_syntactic_only" if unexpanded
                                else "source_text_only_unverified"),
            "evidence_flags": flags, "relationship_decision": "abstain"}


def ranked_candidates(query: str, ids: list[str], pair_index: dict) -> dict:
    result = {}
    for method in METHODS:
        items = []
        for candidate in ids:
            if candidate == query:
                continue
            pair = pair_index[tuple(sorted((query, candidate)))]
            score = (pair["source_aware"]["score"] if method == "source_aware"
                     else pair["name_only"][method])
            item = {"id": candidate, "score": score}
            if method == "source_aware":
                item["evidence_status"] = pair["source_aware"]["evidence_status"]
            items.append(item)
        for item in items:
            value = item["score"]
            if value is not None and value > 0:
                ahead = sum(other["score"] is not None and other["score"] > value
                            for other in items)
                tied = sum(other["score"] == value for other in items)
                item["rank_range"] = [ahead + 1, ahead + tied]
            else:
                item["rank_range"] = None  # Zero and abstentions are unranked.
        items.sort(key=lambda item: (item["score"] is None,
                                     -(item["score"] or 0), item["id"]))
        result[method] = {
            "positive_score_candidates": sum(item["score"] is not None and item["score"] > 0
                                             for item in items),
            "abstained_candidates": sum(item["score"] is None for item in items),
            "candidate_list": items,
        }
    return result


def diagnostic(pairs: dict, queries: dict) -> dict:
    """Requested display case only; called after all pair scores and ranks exist."""
    left, right = "pipeline_created@month", "pipeline_created@window"
    pair = pairs[tuple(sorted((left, right)))]
    directions = {}
    for query, target in ((left, right), (right, left)):
        directions[query] = {
            method: {
                "target": next(item for item in queries[query]["methods"][method]["candidate_list"]
                               if item["id"] == target),
                "top_three_positive": [item for item in queries[query]["methods"][method]["candidate_list"]
                                       if item["score"] is not None and item["score"] > 0][:3],
            } for method in METHODS
        }
    return {"ids": [left, right], "role": "post_scoring_diagnostic_not_success_or_gold",
            "name_only": pair["name_only"], "source_aware": pair["source_aware"],
            "directions": directions}


def generate() -> dict:
    raw = (ROOT / INPUT).read_bytes()
    source = json.loads(raw)
    indexed = inventory(source)
    ids = list(indexed)
    pair_index = {}
    for left, right in itertools.combinations(ids, 2):
        names = name_scores(indexed[left]["metric_name"], indexed[right]["metric_name"])
        pair_index[(left, right)] = {
            "left": left, "right": right, "name_only": names,
            "source_aware": source_score(indexed[left], indexed[right], names["token_jaccard"]),
        }
    queries = {query: {"metric_name": indexed[query]["metric_name"],
                       "grain": indexed[query]["grain"],
                       "methods": ranked_candidates(query, ids, pair_index)} for query in ids}
    # Make bidirectional ranks explicit for every unordered pair; each range is
    # computed against the complete 10-candidate universe for that query.
    for (left, right), pair in pair_index.items():
        pair["query_rank_ranges"] = {
            query: {method: next(item["rank_range"] for item in queries[query]["methods"][method]["candidate_list"]
                                 if item["id"] == target)
                    for method in METHODS}
            for query, target in ((left, right), (right, left))
        }
    report = {
        "schema_version": 1, "algorithm_version": ALGORITHM_VERSION,
        "purpose": "development_only_candidate_retrieval_probe",
        "source": source["source"], "input_file": INPUT,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "universe": {"id_rule": "metric_name@grain", "branch_ids": ids,
                     "branch_count": len(ids), "unordered_pair_count": len(pair_index),
                     "candidate_count_per_query": len(ids) - 1},
        "methods": {
            "name_only": {"algorithm_version": NAME_VERSION, "names_only": list(NAME_METHODS),
                          "definition": "Identical run_development_baselines.scores functions on metric_name; no source fields"},
            "source_aware": {
                "features_in_order": list(FEATURES),
                "weights": {field: f"1/{len(FEATURES)}" for field in FEATURES},
                "formula": "round(sum(feature score or 0 for each of seven features) / 7, 6)",
                "name_tokens": "existing six-decimal token_jaccard on metric_name",
                "source_fields": "literal exact text after extraction for source_ref, value, WHERE, period_start and segment; exact grain",
                "null_where": "two absent local WHERE clauses score 1 as syntax only; otherwise a null/non-null mismatch scores 0",
                "unexpanded": "either side containing Jinja template delimiters makes that field unscored (null), with zero contribution and fixed denominator",
                "abstention": "unsupported parse, unknown grain, unexpected flags or missing required fields give a null source score",
                "status": "source text, unexpanded syntax and untraced field lineage are review evidence; no equivalence classification",
            },
            "ranking": "six-decimal scores; positive scores have tied rank ranges; zero/null unranked; display ties by branch ID; query excluded",
        },
        "pairs": list(pair_index.values()), "queries": queries,
        "diagnostic": diagnostic(pair_index, queries),
        "limits": [
            "No complete judged-anchor set for these 11 queries is supplied to this probe; do not calculate accuracy, precision or Recall@k.",
            "Pair scores retrieve candidates only. All relationship decisions abstain, including identical names or source text.",
            "Refs identify source relations, not field lineage; upstream filters, cardinality and SQL semantics are not traced.",
            "GROUPING SETS, Jinja declarations and dbt macros remain unexpanded. Matching segment projections do not prove matching segment rows.",
            "Month and window are separate aggregation grains; this report uses no sampled values or reconciliation outcomes.",
            "Equal feature weights and zero credit for unexpanded fields are development heuristics, not learned or calibrated parameters.",
        ],
    }
    validate_report(report)
    return report


def validate_report(report: dict) -> None:
    ids = report["universe"]["branch_ids"]
    pairs = report["pairs"]
    if len(ids) != 11 or len(pairs) != 55 or len(report["queries"]) != 11:
        raise ValueError("Incomplete branch/pair/query enumeration")
    if {(p["left"], p["right"]) for p in pairs} != set(itertools.combinations(ids, 2)):
        raise ValueError("Missing or duplicated unordered pair")
    for query, details in report["queries"].items():
        for method in METHODS:
            items = details["methods"][method]["candidate_list"]
            if len(items) != 10 or {item["id"] for item in items} != set(ids) - {query}:
                raise ValueError(f"Incomplete candidates: {query} / {method}")
            for item in items:
                rank = item["rank_range"]
                if (item["score"] is None or item["score"] <= 0) != (rank is None):
                    raise ValueError("Unranked/positive score mismatch")
                if rank is not None and not (1 <= rank[0] <= rank[1] <= 10):
                    raise ValueError("Invalid rank range")
    if any(pair["source_aware"]["relationship_decision"] != "abstain" for pair in pairs):
        raise ValueError("Source score cannot declare equivalence")


def self_check() -> None:
    def fixture(grain="month", where="x = 1", period="cohort_month"):
        return {"metric_name": "same_name", "grain": grain, "parse_status": "extracted",
                "source_ref": "fct_x", "expressions": {"value": "count(*)", "segment": "segment",
                                                     "period_start": period},
                "where": where, "review_flags": ["field_lineage_not_traced"],
                "field_lineage": "not_traced", "grouping_sets": False,
                "macro_calls_unexpanded": []}

    a, b = fixture(), fixture(grain="window", where="x = {{ var('x') }}",
                              period="{{ window_start }}")
    probe = source_score(a, b, 1.0)
    if (probe["score"] != round(4 / 7, 6)
            or probe["unscored_features"] != ["where", "period_start"]
            or probe["evidence_status"] != "unexpanded_syntax_syntactic_only"
            or source_score(b, a, 1.0) != probe):
        raise ValueError("Unexpanded source and symmetry self-check failed")
    if source_score(a, fixture(where="x = 2"), 1.0)["score"] != round(6 / 7, 6):
        raise ValueError("Different WHERE clauses earned credit")
    altered = {**a, "label": "equivalent", "reviewer_conclusion": "yes",
               "sample_equality": True, "pair_id": "chosen"}
    if source_score(a, altered, 1.0) != source_score(a, a, 1.0):
        raise ValueError("Forbidden metadata influenced source scoring")
    if source_score(a, {**a, "parse_status": "unsupported"}, 1.0)["score"] is not None:
        raise ValueError("Unsupported syntax did not abstain")
    if (source_score(a, {**a, "expressions": None}, 1.0)["score"] is not None
            or source_score(a, {**a, "review_flags": ["unknown_syntax"]}, 1.0)["score"] is not None):
        raise ValueError("Missing or unknown source evidence did not abstain")
    ids = ["a", "b", "c", "d"]
    test_pairs = {}
    for left, right in itertools.combinations(ids, 2):
        value = 1.0 if left == "a" and right in ("b", "c") else 0.0
        test_pairs[(left, right)] = {"name_only": {method: value for method in NAME_METHODS},
                                     "source_aware": {"score": value,
                                                      "evidence_status": "syntactic_only"}}
    ranked = ranked_candidates("a", ids, test_pairs)["source_aware"]["candidate_list"]
    if ([(item["id"], item["rank_range"]) for item in ranked]
            != [("b", [1, 2]), ("c", [1, 2]), ("d", None)]):
        raise ValueError("Tied ranks or zero-score exclusion self-check failed")
    if name_scores("same_name", "same_name")["exact"] != 1.0:
        raise ValueError("Existing lexical baseline unavailable")


def score_text(value: float | None) -> str:
    return "abstain" if value is None else f"{value:.6f}"


def range_text(value: list[int] | None) -> str:
    if value is None:
        return "unranked"
    return str(value[0]) if value[0] == value[1] else f"{value[0]}–{value[1]}"


def markdown(report: dict) -> str:
    universe = report["universe"]
    source = report["source"]
    lines = ["# GTM source-aware candidate retrieval: development probe", "",
             f"Pinned input: `{report['input_file']}` (SHA-256 `{report['input_sha256']}`), "
             f"`{source['project']}` at `{source['commit']}`, `{source['path']}`.",
             f"Algorithm `{ALGORITHM_VERSION}`; existing lexical functions `{NAME_VERSION}`. "
             f"All {universe['unordered_pair_count']} unordered pairs of {universe['branch_count']} "
             "unique `metric_name@grain` branches are below. Every query ranks the same other 10 branches.", "",
             "## Fixed scoring rules", "",
             "Name-only exact, token Jaccard, Jaro–Winkler and Soundex use the existing baseline "
             "functions on `metric_name` only. The source-aware score gives **1/7 each** to name token "
             "Jaccard and literal equality of source ref, value expression, local WHERE, period-start "
             "expression, segment expression and grain. SQL text is not parsed or normalized again. "
             "Both absent local WHERE clauses earn syntactic credit. Any field containing Jinja on "
             "either side is unscored and contributes zero with the fixed denominator. Scores are "
             "rounded to six decimals before ranking; positive ties share a rank range. Zero and "
             "abstained scores have no rank. Display ties use branch ID order.", "",
             "All source-aware decisions abstain on equivalence. The pinned branches contain "
             "unexpanded syntax and untraced field lineage; each pair carries an evidence status, "
             "flags and per-feature scores in JSON. Unsupported extraction or missing required "
             "source fields would abstain from source scoring. No labels, pair IDs, reviewer results "
             "or sampled values enter any score.", "",
             "## All unordered pairs", "",
             "Scores are retrieval clues, not pair labels. Full bidirectional rank ranges and the "
             "ten-candidate list for every query and method are in JSON.", "",
             "| Branch A | Branch B | Exact | Jaccard | Jaro–Winkler | Soundex | Source-aware |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for pair in report["pairs"]:
        values = [pair["name_only"][method] for method in NAME_METHODS]
        lines.append(f"| `{pair['left']}` | `{pair['right']}` | "
                     + " | ".join(score_text(value) for value in (*values, pair["source_aware"]["score"]))
                     + " |")
    diag = report["diagnostic"]
    lines += ["", "## Requested month/window diagnostic", "",
              f"`{diag['ids'][0]}` ↔ `{diag['ids'][1]}` is selected **after scoring** "
              "for inspection; it is not a judged success. The source ref and value expression "
              "match literally, as does the segment projection. The local WHERE includes unexpanded "
              "Jinja and receives no credit; period-start expressions and grain differ. GROUPING SETS "
              "remain unexpanded, so matching projected segment text does not establish matching "
              "segment rows. Month and window are distinct aggregations.", "",
              "| Query → target | Method | Score | Target rank range | First three positive candidates (score; rank range) |",
              "| --- | --- | ---: | ---: | --- |"]
    for query, methods in diag["directions"].items():
        target_id = next(other for other in diag["ids"] if other != query)
        for method in METHODS:
            details = methods[method]
            target = details["target"]
            top = ", ".join(f"`{item['id']}` ({score_text(item['score'])}; {range_text(item['rank_range'])})"
                            for item in details["top_three_positive"]) or "—"
            lines.append(f"| `{query}` → `{target_id}` | `{method}` | "
                         f"{score_text(target['score'])} | {range_text(target['rank_range'])} | {top} |")
    lines += ["", "## Limits", ""]
    lines += [f"- {limit}" for limit in report["limits"]]
    lines += ["", "This universe has no complete set of judged anchors. No accuracy, precision, "
              "Recall@k or effectiveness estimate is reported. Scores and rank positions alone "
              "cannot establish cross-grain equivalence.", "",
              "Reproduce: `python3 metric_matching_pilot/rank_source_aware_candidates.py`. "
              "Verify without writing: `python3 metric_matching_pilot/rank_source_aware_candidates.py --check`.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Regenerate and compare both reports without writing")
    args = parser.parse_args()
    self_check()
    report = generate()
    outputs = {
        "source_aware_candidates_report.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        "source_aware_candidates_report.md": markdown(report),
    }
    for filename, content in outputs.items():
        path = ROOT / filename
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"Report out of date: {filename}; regenerate without --check")
        else:
            path.write_text(content, encoding="utf-8")
    print(f"{report['universe']['unordered_pair_count']} pairs, "
          f"{len(report['queries'])} queries; {'verified' if args.check else 'wrote reports'}")


if __name__ == "__main__":
    main()
