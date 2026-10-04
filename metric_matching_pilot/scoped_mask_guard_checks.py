#!/usr/bin/env python3
"""Development checks for the narrow scoped-mask documentation guard.

Only in-memory copies of verified I1 cards are mutated. No packet or source is
rewritten, and these assertions do not compare predictions to reference labels.
"""

from __future__ import annotations

from copy import deepcopy

from scoped_mask_decision import _scope_text, documented_scope, run
from development_decision_probe import MASK, verify_packet


EXPECTED = {
    "metric.jaffle_shop.drink_revenue||metric.jaffle_shop.revenue",
    "metric.jaffle_shop.food_revenue||metric.jaffle_shop.revenue",
}


def main() -> None:
    packet = verify_packet()
    cards = {card["metric_name"]: card for card in packet["cards"]}
    food, base = cards["food_revenue"], cards["revenue"]
    drink = cards["drink_revenue"]
    assert documented_scope(food, base) and documented_scope(base, food)
    assert documented_scope(drink, base) and documented_scope(base, drink)

    def assert_rejected(name: str, change, *, lexical: bool = True) -> None:
        masked, plain = deepcopy(food), deepcopy(base)
        change(masked, plain)
        expression = masked["input_measures"][0]["owners"][0]["expr"]
        match = MASK.fullmatch(expression)
        if lexical:
            assert match is not None, name  # The SQL-shape gate alone cannot explain rejection.
            assert not _scope_text(masked, plain, match.group(1)), name
        else:
            assert match is None, name  # Reversed CASE polarity fails the shape gate.
        assert not documented_scope(masked, plain), name
        rejected.append(name)

    def expression(masked: dict, flag: str) -> None:
        masked["input_measures"][0]["owners"][0]["expr"] = (
            f"case when {flag} then product_price else 0 end")

    rejected: list[str] = []
    assert_rejected("negated category flag", lambda m, b: expression(m, "is_not_food_item"))
    assert_rejected("disjunctive category flag", lambda m, b: expression(m, "is_food_or_drink_item"))
    assert_rejected("negated description", lambda m, b: m.update(description="The revenue from not food in each order"))
    assert_rejected("exclusion description", lambda m, b: m.update(description="The revenue from food in each order. Excludes drinks."))
    assert_rejected("contradictory scope", lambda m, b: m.update(description="The revenue from drinks in each order"))
    assert_rejected("contradictory base scope", lambda m, b: b.update(description="Sum of the product revenue for each order item. Excludes food."))
    assert_rejected("missing masked description", lambda m, b: m.pop("description"))
    assert_rejected("missing base description", lambda m, b: b.pop("description"))
    assert_rejected("reversed CASE polarity", lambda m, b: m["input_measures"][0]["owners"][0].update(
        expr="case when is_food_item then 0 else product_price end"), lexical=False)

    result = run()
    selected = {row["pair_id"] for row in result["rows"] if row["decision"] != "abstain"}
    assert len(result["rows"]) == 171 and selected == EXPECTED
    assert result["counts"] == {"temporal_or_scope_variant": 2, "abstain": 169}
    print(f"171 pairs: 2 scoped decisions ({', '.join(sorted(selected))}); "
          f"169 abstentions; {len(rejected)} adversarial mutations rejected")


if __name__ == "__main__":
    main()
