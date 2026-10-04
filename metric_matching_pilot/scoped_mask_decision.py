#!/usr/bin/env python3
"""Development-only scoped class output for a narrow aggregate-mask pattern.

This consumes the unchanged pinned I1 packet. It does not use seed values,
practice worksheets, or prior method predictions. A class output is a method
prediction, never an independently adjudicated reference label.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from development_decision_probe import MASK, REPO, probe_signal, verify_packet


HERE = Path(__file__).resolve().parent
REPORT = HERE / "scoped_mask_decision_report.md"
CATEGORY_FLAG = re.compile(r"is_(food|drink)_item\Z", re.I)


def _scope_text(masked: dict, base: dict, flag: str) -> bool:
    """Accept only the affirmative, single-category wording seen in this pilot."""
    category = CATEGORY_FLAG.fullmatch(flag)
    concept = base.get("metric_name")
    masked_doc, base_doc = masked.get("description"), base.get("description")
    if (category is None or not isinstance(concept, str) or not concept
            or not isinstance(masked_doc, str) or not isinstance(base_doc, str)):
        return False
    concept = concept.lower().replace("_", " ")
    masked_doc = " ".join(masked_doc.lower().split())
    base_doc = " ".join(base_doc.lower().split())
    # Full matches reject negation, exclusions, extra categories, and claims
    # that contradict the named mask. Tax is the base card's distinct exclusion.
    return (re.fullmatch(rf"(?:the )?{re.escape(concept)} from "
                         rf"{category.group(1).lower()}s? in each order\.?", masked_doc) is not None
            and re.fullmatch(rf"sum of the product {re.escape(concept)} "
                             r"for each order item\. excludes tax\.", base_doc) is not None)


def _pinned_description(card: dict) -> bool:
    """The exact card description must occur inside its verified declaration."""
    description = card.get("description")
    if not isinstance(description, str) or not description.strip():
        return False
    try:
        declared_file = Path(card["declared_file"])
        if not str(declared_file).startswith("models/") or ".." in declared_file.parts:
            return False
        start, end = card["declared_span_text_located"]
        excerpt = (REPO / declared_file).read_text().splitlines()[start - 1:end]
    except (KeyError, OSError, TypeError, ValueError):
        return False
    return any(line.strip() == "description: " + description for line in excerpt)


def documented_scope(left: dict, right: dict) -> bool:
    """Require affirmative scope wording in both pinned declarations."""
    for masked, base in ((left, right), (right, left)):
        if not masked["input_measures"] or not base["input_measures"]:
            continue
        expression = masked["input_measures"][0]["owners"][0]["expr"]
        match = MASK.fullmatch(expression or "")
        if match is None:
            continue
        return (_scope_text(masked, base, match.group(1))
                and _pinned_description(masked) and _pinned_description(base))
    return False


def run() -> dict:
    packet = verify_packet()
    cards = {card["metric_id"]: card for card in packet["cards"]}
    rows = []
    for pair in packet["pairs"]:
        left, right = cards[pair["a"]], cards[pair["b"]]
        signal, reason, evidence = probe_signal(left, right)
        # A changed contribution population is already the definition of the
        # broad scope-variant class. This rule does not assert any equality,
        # subset ordering, or rollup. All non-mask patterns abstain.
        label = ("temporal_or_scope_variant" if signal == "conditional_scope_hypothesis"
                 and documented_scope(left, right) else "abstain")
        rows.append({"pair_id": pair["pair_id"], "left": left["metric_name"],
                     "right": right["metric_name"], "left_description": left.get("description"),
                     "right_description": right.get("description"), "decision": label,
                     "evidence": evidence, "reason": reason})
    counts = Counter(row["decision"] for row in rows)
    assert len(rows) == packet["pair_count"] == sum(counts.values())
    return {"packet_sha256": "78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb",
            "pair_set_sha256": packet["pair_set_sha256"], "counts": dict(counts), "rows": rows}


def main() -> None:
    result = run()
    selected = [r for r in result["rows"] if r["decision"] != "abstain"]
    selected_ids = ", ".join(f"`{r['pair_id']}`" for r in selected)
    table = "\n".join(f"| `{r['left']}` / `{r['right']}` | `{r['decision']}` | "
                      f"Published descriptions: {r['left_description']!r} / {r['right_description']!r}. "
                      f"{r['evidence'].split(' Missing:', 1)[0]} |"
                      for r in selected)
    REPORT.write_text(f"""# Scoped aggregate-mask class output (development only)

The unchanged I1 packet SHA-256 is `{result['packet_sha256']}`; its complete
19-metric/171-pair set SHA-256 is `{result['pair_set_sha256']}`. The source and
generated SQL hashes and declaration spans are rechecked by
`development_decision_probe.py` before this rule runs. It consumes the same two
I1 cards per pair as the frozen comparators; the 18 mixed-scope pairs abstain.

**Method outputs:** {result['counts'].get('temporal_or_scope_variant', 0)}
`temporal_or_scope_variant` decisions and {result['counts'].get('abstain', 0)}
abstentions, at the cards' **ungrouped compiled scope only**. These are method
predictions, not human gold or accuracy estimates. The earlier conservative
runner is still frozen and has zero decisions; this is a separately versioned
development rule, not a retroactive change to its results.

**Selected pair IDs:** {selected_ids}.

| Pair | Scoped class output | Source-linked evidence and remaining numerical obligations |
| --- | --- | --- |
{table}

The class means that both declarations sum the same base expression from the
same semantic model, and one uses an explicit CASE predicate to zero masked
row contributions. Under the packet's broad rubric, this documents a shared
revenue concept with changed contribution scope. It says **nothing** about
numeric subset order, equivalence, whether food and drink exhaust all product
types, NULL-to-zero policy, or substitution at a different grain or time rule.
Fresh day-grain MetricFlow queries and upstream flag tracing are separate
development checks; they are not inputs to this packet-only rule. If they
contradict the scope interpretation, retract or narrow this rule before any
held-out study. The source links remain text-located and parser coverage is
restricted to the exact `SUM(CASE WHEN flag THEN x ELSE 0 END)` versus `SUM(x)`
shape. The additional lexical guard accepts only `is_food_item` or
`is_drink_item` with an affirmative full-description match to “the
<base metric> from <category>[s] in each order.” It also requires the base
card's full “sum of the product <base metric> for each order item. Excludes
tax.” wording and checks both exact descriptions in their pinned declaration
spans. This deliberately narrow development vocabulary abstains on other
categories and alternate legitimate descriptions. It rejects negated and
multi-category flags, missing or contradictory descriptions, and reversed
CASE polarity. `python -B metric_matching_pilot/scoped_mask_guard_checks.py`
checks nine in-memory adversarial card mutations and the exact 2/171 output;
no pinned packet or source file is changed. All other relationships abstain.
No new held-out source or worksheet was inspected, and no method-superiority
claim follows.
""")
    print(json.dumps({"pairs": len(result["rows"]), "counts": result["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
