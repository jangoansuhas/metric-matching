#!/usr/bin/env python3
"""Reproduce name-only candidate retrieval diagnostics on selected development cases.

No labels, source signatures, SQL, or pair membership enter the scoring functions.
The selected pairs are diagnostic probes, not a judged retrieval universe or gold.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUTS = (
    "public_corpus_report.json",
    "public_pair_proposals.json",
    "public_second_review.json",
    "cards.json",
    "pairs.json",
    "expected.json",
    "public_positive_candidate.json",
)
METHODS = ("exact", "token_jaccard", "jaro_winkler", "soundex")
ALGORITHM_VERSION = "development_name_baselines_v1"
WORD = re.compile(r"[a-z0-9]+")
CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
SOUNDEX_GROUPS = ("BFPV", "CGJKQSXZ", "DT", "L", "MN", "R")
SOUNDEX_CODES = {letter: str(index) for index, group in enumerate(SOUNDEX_GROUPS, 1)
                 for letter in group}


def read_inputs():
    documents, hashes = {}, {}
    for name in INPUTS:
        raw = (ROOT / name).read_bytes()
        documents[name] = json.loads(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return documents, hashes


def normalized(name):
    """ASCII alphanumeric words, split on punctuation/underscores and camel case."""
    if not isinstance(name, str) or not name:
        raise ValueError("Metric name must be a nonempty string")
    words = WORD.findall(CAMEL_BOUNDARY.sub(" ", name).casefold())
    if not words:
        raise ValueError(f"Metric name has no ASCII tokens: {name!r}")
    return " ".join(words)


def soundex(name):
    """American Soundex on all name tokens concatenated; H/W do not reset runs."""
    letters = "".join(c for c in normalized(name).upper() if "A" <= c <= "Z")
    if not letters:
        return "0000"
    first = letters[0]
    previous = SOUNDEX_CODES.get(first, "")
    digits = []
    for letter in letters[1:]:
        if letter in "HW":
            continue
        code = SOUNDEX_CODES.get(letter, "")
        if code and code != previous:
            digits.append(code)
        previous = code  # Vowels and Y separate equal consonants.
    return (first + "".join(digits) + "000")[:4]


def jaro(first, second):
    """Standard Jaro character matching with half the matched transpositions."""
    if first == second:
        return 1.0
    if not first or not second:
        return 0.0
    window = max(0, max(len(first), len(second)) // 2 - 1)
    matched_first = [False] * len(first)
    matched_second = [False] * len(second)
    matches = 0
    for i, character in enumerate(first):
        for j in range(max(0, i - window), min(len(second), i + window + 1)):
            if not matched_second[j] and character == second[j]:
                matched_first[i] = matched_second[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    a = [c for c, matched in zip(first, matched_first) if matched]
    b = [c for c, matched in zip(second, matched_second) if matched]
    transpositions = sum(x != y for x, y in zip(a, b)) / 2
    return (matches / len(first) + matches / len(second)
            + (matches - transpositions) / matches) / 3


def scores(left, right):
    a, b = normalized(left), normalized(right)
    tokens_a, tokens_b = set(a.split()), set(b.split())
    similarity = jaro(a, b)
    if similarity >= 0.7:
        prefix = 0
        for x, y in zip(a[:4], b[:4]):
            if x != y:
                break
            prefix += 1
        similarity += 0.1 * prefix * (1 - similarity)
    return {
        "exact": float(a == b),
        "token_jaccard": round(len(tokens_a & tokens_b) / len(tokens_a | tokens_b), 6),
        "jaro_winkler": round(similarity, 6),
        "soundex": float(soundex(left) == soundex(right)),
    }


def unique_index(entries, description):
    index = {}
    for entry in entries:
        if entry["id"] in index:
            raise ValueError(f"Duplicate {description} ID: {entry['id']}")
        normalized(entry["name"])
        index[entry["id"]] = entry
    return index


def public_inventory(corpus):
    metrics = corpus["metrics"]
    if len(metrics) != corpus["metric_count"]:
        raise ValueError("Public metric count does not match the extraction report")
    return unique_index(({"id": f"{m['model']}.{m['name']}" if m["model"] else m["name"],
                          "name": m["name"]} for m in metrics), "public metric")


def rank_pair(left_id, right_id, inventory):
    if left_id not in inventory or right_id not in inventory or left_id == right_id:
        raise ValueError(f"Invalid selected pair: {left_id!r}, {right_id!r}")
    query = inventory[left_id]["name"]
    ranked = [(candidate_id, scores(query, entry["name"]))
              for candidate_id, entry in inventory.items() if candidate_id != left_id]
    target = next(values for candidate_id, values in ranked if candidate_id == right_id)
    results = {}
    for method in METHODS:
        ordered = sorted(ranked, key=lambda item: (-item[1][method], item[0]))
        positive = [(candidate_id, values[method]) for candidate_id, values in ordered
                    if values[method] > 0]
        value = target[method]
        preceding = sum(values[method] > value for _, values in ranked)
        tied = sum(values[method] == value for _, values in ranked) if value > 0 else 0
        results[method] = {
            "score": value,
            "rank_range": [preceding + 1, preceding + tied] if tied else None,
            "positive_score_candidates": len(positive),
            "top_three_positive": [{"id": candidate_id, "score": score}
                                   for candidate_id, score in positive[:3]],
        }
    return {"left": left_id, "right": right_id,
            "left_name": query, "right_name": inventory[right_id]["name"],
            "candidate_count": len(ranked),
            "methods": results}


def selected_pairs(pairs, inventory, left_key, right_key):
    rows = []
    ids = set()
    for pair in pairs:
        if pair["id"] in ids:
            raise ValueError(f"Duplicate selected pair: {pair['id']}")
        ids.add(pair["id"])
        left, right = left_key(pair), right_key(pair)
        rows.append({"id": pair["id"], **rank_pair(left, right, inventory)})
    return rows


def metric_id(side):
    return f"{side['model']}.{side['metric']}"


def positive_pair(source):
    names = []
    for description in source["pair"]:
        metric = description.split(" (", 1)[0]
        if not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", metric):
            raise ValueError(f"Unsupported positive pair description: {description!r}")
        names.append(metric)
    if (len(names) != 2 or source["candidate_id"] != "POS-001"
            or not source["status"].startswith("conditional_cross_grain_candidate_")):
        raise ValueError("Unexpected conditional candidate")
    return {"id": source["candidate_id"], "left": names[0], "right": names[1],
            "methods": scores(names[0].split(".")[1], names[1].split(".")[1]),
            "rank_range": None, "reason_no_rank": "No complete semantic-project metric inventory in the supplied source",
            "semantic_commit": source["semantic_commit"],
            "dbt_submodule_commit": source["dbt_submodule_commit"],
            "source_status": source["status"],
            "source_conditions": {
                "daily_dates_compared": source["sample"]["dates_compared"],
                "daily_dates_with_different_values": source["sample"]["dates_with_different_values"],
                "orders_without_items_requiring_coalesce": source["sample"]["orders_without_items"],
            }}


def generate():
    data, hashes = read_inputs()
    corpus = data["public_corpus_report.json"]
    pack = data["public_pair_proposals.json"]
    second = data["public_second_review.json"]
    if (corpus["commit"] != pack["commit"] or corpus["corpus"] != pack["corpus"]
            or set(second["labels"]) != {p["id"] for p in pack["pairs"]}):
        raise ValueError("Public corpus/pairs/review provenance mismatch")
    public = selected_pairs(pack["pairs"], public_inventory(corpus),
                            lambda pair: metric_id(pair["left"]),
                            lambda pair: metric_id(pair["right"]))

    cards = data["cards.json"]
    fixture = unique_index(({"id": card["id"], "name": card["name"]}
                            for card in cards), "fixture card")
    synthetic_pairs = data["pairs.json"]["pairs"]
    if set(data["expected.json"]) != {p["id"] for p in synthetic_pairs}:
        raise ValueError("Synthetic pair/expected-label provenance mismatch")
    synthetic = selected_pairs(synthetic_pairs, fixture,
                               lambda pair: pair["left"], lambda pair: pair["right"])

    negative = next(p for p in pack["pairs"] if p["id"] == "JS-008")
    if (negative["proposed_label"] != "related" or second["labels"]["JS-008"] != "related"
            or data["expected.json"]["P4_filter_change"]["label"] != "candidate_definition_drift"):
        raise ValueError("Illustration labels changed; re-examine the prose")
    positive = positive_pair(data["public_positive_candidate.json"])
    return {
        "schema_version": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "purpose": "development_only_candidate_retrieval_diagnostics",
        "relationship_classification": "not_performed",
        "evaluation_status": "selected_cases_not_held_out_gold_no_effectiveness_estimate",
        "input_scope": "metric name only, excluding query itself; never model, source expression, labels, or pair hints",
        "methods": {
            "exact": "1 iff normalized ordered name tokens are identical, else 0",
            "token_jaccard": "|unique token intersection| / |unique token union|",
            "jaro_winkler": "standard Jaro; Winkler prefix up to 4, scale 0.1 only if Jaro >= 0.7",
            "soundex": "1 iff four-character American Soundex codes of concatenated name tokens agree, else 0",
        },
        "normalization": "ASCII alphanumeric tokens, casefold, split camel case and nonalphanumeric separators; Jaro-Winkler uses space-joined tokens; Soundex ignores digits",
        "score_precision": "round to six decimals before ranking; positive score > 0; ties share a rank range, zero-score targets are unranked",
        "source_sha256": hashes,
        "cohorts": {
            "public_jaffle": {"corpus": corpus["corpus"], "commit": corpus["commit"],
                              "inventory_source": "public_corpus_report.json:metrics",
                              "inventory_size": len(corpus["metrics"]),
                              "extraction_status_counts": corpus["yaml_status_counts"],
                              "selection_source": "public_pair_proposals.json:pairs",
                              "selected_pairs": public},
            "synthetic_fixture": {"inventory_source": "cards.json (hand-authored cards)",
                                  "inventory_size": len(cards),
                                  "selection_source": "pairs.json:pairs",
                                  "selected_pairs": synthetic},
        },
        "conditional_pair_only": positive,
        "illustrations": [
            {"id": "JS-008", "role": "hard negative for unconditional equivalence",
             "label_provenance": "public_pair_proposals.json and user-submitted public_second_review.json both say related; no independent gold",
             "observation": "lifetime_spend versus lifetime_spend_pretax share name tokens but differ in tax inclusion"},
            {"id": "P4_filter_change", "role": "synthetic same-name hard negative for unchanged definition",
             "label_provenance": "expected.json: candidate_definition_drift, hand-authored cards.json",
             "observation": "pipeline_arr v0/v1 have the same name but different stage filters"},
            {"id": "POS-001", "role": "conditional positive case study, not gold",
             "label_provenance": "public_positive_candidate.json, pinned semantic and dbt revisions",
             "observation": "orders.subtotal and order_items.revenue match on aligned sample days; order-grain comparison requires an outer join and COALESCE for zero-item orders"},
        ],
        "limits": [
            "The ten public pairs were selected for review; the other inventory pairs have not all been judged. No Recall@k or retrieval accuracy follows.",
            "The seven fixture pairs and cards were constructed by hand. Do not pool them with naturally occurring public cases as a benchmark.",
            "A positive lexical score signals a candidate, not equivalence; a zero score cannot rule out conditional equivalence.",
            "POS-001 has no complete same-project candidate inventory here, so its pair score has no rank; finite observed equality and one translating engine do not establish native cross-engine or future equality.",
        ],
    }


def cell(result):
    score = result["score"]
    span = result["rank_range"]
    rank = "unranked" if span is None else str(span[0]) if span[0] == span[1] else f"{span[0]}–{span[1]}"
    return f"{score:.3f} / {rank}"


def markdown(report):
    public = report["cohorts"]["public_jaffle"]
    synthetic = report["cohorts"]["synthetic_fixture"]
    lines = ["# Development-only name retrieval baselines", "",
             f"Algorithm: `{report['algorithm_version']}` in `run_development_baselines.py` (Python standard library only).",
             "Scores use **metric names only** for all four methods. The ranking excludes the query metric; it never reads labels or source signatures. No relationship classification is performed.", "",
             "Normalization splits underscores, punctuation, and camel case, then casefolds ASCII alphanumeric tokens. Exact compares the ordered normalized text. Jaccard uses unique token sets. Jaro–Winkler uses the normalized text, standard Jaro matching and a four-character prefix boost of 0.1 when Jaro ≥ 0.7. American Soundex concatenates tokens, ignores digits, and compares four-character codes. Scores are rounded to six decimals before ranking; a score of 0 is unranked. A rank range shows all candidates tied at that positive score; the top-three list in JSON breaks ties by candidate ID for display.", "",
             f"## Public Jaffle Shop: {len(public['selected_pairs'])} selected pairs against {public['inventory_size']} extracted metrics", "",
             f"Source: `public_corpus_report.json` and `public_pair_proposals.json`, pinned at `{public['commit']}`. Each query has {public['inventory_size'] - 1} other candidates. The extraction reports {public['extraction_status_counts'].get('partial_signature', 0)} partial signatures and {public['extraction_status_counts'].get('needs_review', 0)} needing review, so this inventory supplies names rather than complete verified source cards. These selected pairs were reviewed, but the full inventory was not judged for each query.", "",
             "| Case: query → selected target | Exact score / rank | Token Jaccard | Jaro–Winkler | Soundex |",
             "| --- | ---: | ---: | ---: | ---: |"]
    for row in public["selected_pairs"]:
        values = row["methods"]
        lines.append(f"| `{row['id']}`: `{row['left']}` → `{row['right']}` | "
                     + " | ".join(cell(values[m]) for m in METHODS) + " |")
    lines += ["", f"## Constructed SQLite fixture: {len(synthetic['selected_pairs'])} selected pairs against {synthetic['inventory_size']} hand-authored cards", "",
              "Source: `cards.json` and `pairs.json`; card IDs distinguish versioned definitions with identical names. Each query has "
              + f"{synthetic['inventory_size'] - 1} other cards. This is a separate synthetic diagnostic.", "",
              "| Case: query card → selected target card | Exact score / rank | Token Jaccard | Jaro–Winkler | Soundex |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for row in synthetic["selected_pairs"]:
        values = row["methods"]
        lines.append(f"| `{row['id']}`: `{row['left']}` (`{row['left_name']}`) → "
                     f"`{row['right']}` (`{row['right_name']}`) | "
                     + " | ".join(cell(values[m]) for m in METHODS) + " |")
    positive = report["conditional_pair_only"]
    lines += ["", "## Conditional positive without an inventory", "",
              f"`{positive['id']}`: `{positive['left']}` → `{positive['right']}` from `public_positive_candidate.json` "
              f"(semantic commit `{positive['semantic_commit']}`, dbt submodule `{positive['dbt_submodule_commit']}`). "
              + ", ".join(f"{m}={positive['methods'][m]:.3f}" for m in METHODS) + ". **No rank:** the supplied candidate file is a pair case study, not a complete metric inventory.", "",
              f"The pinned sample has {positive['source_conditions']['daily_dates_with_different_values']} differing aligned daily totals across "
              f"{positive['source_conditions']['daily_dates_compared']} dates; {positive['source_conditions']['orders_without_items_requiring_coalesce']} zero-item orders require an outer join and COALESCE at order grain. This is conditional sample evidence, not an unconditional cross-engine or future-data equivalence label.", "",
              "## Reading the probes", "",
              "- `JS-008` is a hard negative for **unconditional equivalence**: the first analyst and user-submitted labels both call tax-inclusive `lifetime_spend` versus `lifetime_spend_pretax` *related*, despite similar names. Review independence is unverified; this does not make it a `non_match` relationship.",
              "- Constructed `P4_filter_change` has the exact same metric name in v0 and v1, yet the hand-authored stage filters differ; the fixture records candidate definition drift.",
              "- `POS-001` is the conditional positive above. Its names can be lexically dissimilar even when aligned sample totals reconcile under stated conditions.", "",
              "All ten selected public pairs and all seven constructed pairs appear above; examples illustrate failure modes and were not used to choose features, weights, cutoffs, or performance figures. Labels remain source context and never enter ranking. No accuracy, precision, Recall@k, or claim of baseline effectiveness is estimated from these selected cases. The full per-query top-three positive candidates, tie ranges, source hashes, and source statuses are in `development_baselines_report.json`.", "",
              "Reproduce: `python3 metric_matching_pilot/run_development_baselines.py` from the workspace root; verify committed outputs without rewriting them with `python3 metric_matching_pilot/run_development_baselines.py --check`.", ""]
    return "\n".join(lines)


def self_check():
    if (soundex("Robert") != "R163" or soundex("Rupert") != "R163"
            or soundex("Ashcraft") != "A261"
            or abs(jaro("MARTHA", "MARHTA") - 0.9444444444444445) > 1e-12
            or scores("MARTHA", "MARHTA")["jaro_winkler"] != 0.961111
            or scores("same_name", "same_name")["exact"] != 1.0
            or scores("food_revenue", "drink_revenue")["token_jaccard"] != round(1 / 3, 6)):
        raise ValueError("Baseline implementation sanity check failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate in-memory regeneration against saved outputs")
    args = parser.parse_args()
    self_check()
    report = generate()
    outputs = {
        "development_baselines_report.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        "development_baselines_report.md": markdown(report),
    }
    for filename, content in outputs.items():
        path = ROOT / filename
        if args.check:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Report out of date: {filename}; run without --check")
        else:
            path.write_text(content, encoding="utf-8")
    print(f"{len(report['cohorts']['public_jaffle']['selected_pairs'])} public + "
          f"{len(report['cohorts']['synthetic_fixture']['selected_pairs'])} synthetic selected pairs; "
          f"1 conditional pair-only score; {'verified' if args.check else 'wrote reports'}")


if __name__ == "__main__":
    main()
