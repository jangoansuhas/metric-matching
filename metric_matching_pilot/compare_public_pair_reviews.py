#!/usr/bin/env python3
"""Compare a submitted second review with first proposals and evidence-based recommendations."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW_FILE_ID = "libfile_2fb3d91e705c8191b72c7842414bde39"


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def parse_submitted_review(path, expected_ids, valid_labels):
    source = path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## (JS-\d{3}):", source)
    if not sections or len(sections) % 2 != 1:
        raise ValueError("Review headings not recognized")
    labels = {}
    for i in range(1, len(sections), 2):
        pair_id, body = sections[i], sections[i + 1]
        found = re.search(r"\*\*Reviewer label:\*\*\s*`([^`]+)`", body)
        if pair_id in labels or not found or found[1] not in valid_labels:
            raise ValueError(f"Invalid or repeated label for {pair_id}")
        labels[pair_id] = found[1]
    if set(labels) != set(expected_ids):
        raise ValueError(f"Missing/unexpected pair IDs: {set(labels) ^ set(expected_ids)}")
    return labels


def compare(proposals, second, decisions, author_decisions, seed):
    p = {entry["id"]: entry for entry in proposals["pairs"]}
    d = {entry["id"]: entry for entry in decisions["decisions"]}
    a = {entry["id"]: entry for entry in author_decisions["decisions"]}
    if set(p) != set(second["labels"]) or set(p) != set(d):
        raise ValueError("Pair IDs do not align")
    if not set(a) <= set(p) or len(a) != len(author_decisions["decisions"]):
        raise ValueError("Invalid author decision IDs")
    if not proposals["commit"] == decisions["commit"] == author_decisions["commit"] == seed["commit"]:
        raise ValueError("Different public revisions")
    rows = []
    for pair_id, first in p.items():
        second_label = second["labels"][pair_id]
        recommendation = d[pair_id]
        accepted = a.get(pair_id)
        if accepted and accepted["accepted_label"] != recommendation["recommended_label"]:
            raise ValueError(f"Author decision does not match recommendation for {pair_id}")
        rows.append({"id": pair_id,
                     "pair": f"{first['left']['model']}.{first['left']['metric']} / {first['right']['model']}.{first['right']['metric']}",
                     "first_label": first["proposed_label"], "second_label": second_label,
                     "recommended_label": recommendation["recommended_label"],
                     "agreement": first["proposed_label"] == second_label,
                     "author_decision": accepted,
                     "reason": recommendation["reason"]})
    counts = Counter("agreement" if row["agreement"] else "disagreement" for row in rows)
    remaining = sum(not row["agreement"] and not row["author_decision"] for row in rows)
    return {"corpus": proposals["corpus"], "commit": proposals["commit"],
            "review_source": second["source"],
            "status": ("partial_author_adjudication_not_benchmark_ground_truth" if remaining
                       else "all_disagreements_author_decided_not_benchmark_ground_truth"),
            "counts": dict(counts), "first_analyst_label_revisions": sum(
                row["recommended_label"] != row["first_label"] for row in rows),
            "author_accepted_disagreements": sum(bool(row["author_decision"]) and not row["agreement"] for row in rows),
            "unresolved_disagreements": remaining,
            "rows": rows,
            "seed_evidence": {"js001": seed["js001"], "js010": seed["js010"]}}


def markdown(report):
    accepted = [row["id"] for row in report["rows"] if row["author_decision"]]
    open_pairs = [row["id"] for row in report["rows"] if not row["agreement"] and not row["author_decision"]]
    next_gate = (f"decide {', '.join(open_pairs)} and record the decision and reason"
                 if open_pairs else "confirm the six initially agreed labels under the frozen annotation rules and identify natural positive equivalents")
    lines = ["# Public metric-pair review comparison", "",
             f"Pinned repository revision: `{report['commit']}`. A user-submitted sheet supplied a second label set; its claimed independence was not externally verified. The proposed labels below are analyst recommendations. The author accepted {', '.join(accepted)} on September 27, 2026; no independent adjudicator confirmation is recorded. These are not benchmark ground truth.", "",
             "| Pair | First label | Submitted label | Recommended label | Author decision |", "| --- | --- | --- | --- | --- |"]
    for row in report["rows"]:
        author_status = "accepted by author" if row["author_decision"] else "—"
        lines.append(f"| {row['id']} | `{row['first_label']}` | `{row['second_label']}` | `{row['recommended_label']}` | {author_status} |")
    lines += ["", f"Initial agreement: {report['counts'].get('agreement', 0)}/10; disagreements: {report['counts'].get('disagreement', 0)}/10. Of the four initial disagreements, {report['author_accepted_disagreements']} have author-accepted decisions and {report['unresolved_disagreements']} remain open. The first analyst revised {report['first_analyst_label_revisions']} proposed label after inspecting the submitted review and seed evidence.", "",
              "## Disagreements", ""]
    for row in report["rows"]:
        if not row["agreement"]:
            decision_note = "Author accepted: " if row["author_decision"] else "Pending: "
            lines.append(f"- **{row['id']} ({row['pair']}):** {decision_note}{row['reason']}")
    lines += ["", "The submitted JS-008 label agrees, but its suggested location-rate adjustment is not required by the visible model: `customers.sql` sums the `tax_paid` order field into `lifetime_tax_paid`. The source-backed reconciliation and daily-time counterexample are in `public_seed_reconciliation.md`.", "",
              "Author-accepted rules: tax-inclusive order total and pretax item revenue are related but not equivalent across grains (JS-001); identical additive input with disjoint category predicates yields a scope variant (JS-005); counts of distinct but directly linked business entities are related when the model explicitly connects them (JS-007); equal all-time sums with different default daily time assignments are a time-rule variant, not unqualified cross-grain equivalence (JS-010). These pairs are not interchangeable.", "",
              f"Next gate: {next_gate}. Obtain independent adjudication or explicitly state the annotation process before freezing a gold-label version. Until then, do not calculate matcher accuracy.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-file", type=Path, help="Original user-submitted review; omit to reuse normalized labels")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    proposals = load("public_pair_proposals.json")
    if args.review_file:
        labels = parse_submitted_review(args.review_file,
                                        [p["id"] for p in proposals["pairs"]], proposals["labels"])
        second = {"source": {"filename": args.review_file.name,
                             "library_file_id": REVIEW_FILE_ID,
                             "independence": "claimed in submission; not independently verified"},
                  "labels": labels}
        (ROOT / "public_second_review.json").write_text(json.dumps(second, indent=2) + "\n", encoding="utf-8")
    else:
        second = load("public_second_review.json")
    report = compare(proposals, second, load("public_pair_resolution_recommendations.json"),
                     load("public_pair_author_decisions.json"), load("public_seed_reconciliation.json"))
    if args.check:
        assert report["counts"] == {"disagreement": 4, "agreement": 6}
        assert report["first_analyst_label_revisions"] == 1
        assert report["author_accepted_disagreements"] == 4
        assert report["unresolved_disagreements"] == 0
        assert {r["id"] for r in report["rows"] if r["author_decision"]} == {"JS-001", "JS-005", "JS-007", "JS-010"}
        assert {r["id"] for r in report["rows"] if not r["agreement"]} == {
            "JS-001", "JS-005", "JS-007", "JS-010"}
        assert report["seed_evidence"]["js001"]["tax_paid_cents"] > 0
        assert report["seed_evidence"]["js010"]["daily_dates_with_different_values"] > 0
    (ROOT / "public_pair_review_comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / "public_pair_review_comparison.md").write_text(markdown(report), encoding="utf-8")
    print(f"Compared {len(report['rows'])} labels: {report['counts']}; wrote evidence-backed recommendations"
          + ("; checks passed" if args.check else ""))


if __name__ == "__main__":
    main()
