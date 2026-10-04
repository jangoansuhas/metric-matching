#!/usr/bin/env python3
"""Narrow AST mask comparator on the unchanged, public Jaffle I1 packet.

The decision function receives only two packet cards. A small, fail-closed SQL
parser builds ASTs for the exact single-table, ungrouped SUM shapes in scope;
unsupported SQL abstains. ``verify_packet`` is reused solely for the pinned
packet/source/compiled-SQL integrity checks, never for its probe or decisions.

Run: python3 -B metric_matching_pilot/ast_mask_baseline.py
No labels, proposed outputs, built values, or held-out sources are inputs.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from development_decision_probe import verify_packet


HERE = Path(__file__).resolve().parent
REPO = HERE.parent / "public_corpus/jaffle-shop-sidemantic/jaffle-shop"
LEXEME = re.compile(r'\s+|"(?:[^"]|"")*"|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[().]')
IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
ATOMIC_ITEM_FLAG = re.compile(r"is_([a-z][a-z0-9]*)_item\Z")
RESERVED = frozenset({"select", "sum", "as", "from", "where", "join", "on",
                      "group", "by", "having", "order", "limit", "case",
                      "when", "then", "else", "end", "union"})


@dataclass(frozen=True)
class Column:
    name: str


@dataclass(frozen=True)
class Zero:
    pass


@dataclass(frozen=True)
class Case:
    flag: Column
    value: Column
    otherwise: Zero


@dataclass(frozen=True)
class SumSelect:
    argument: Column | Case
    output_name: str
    relation: tuple[str, ...]
    relation_alias: str | None


@dataclass(frozen=True)
class Token:
    value: str
    kind: str


class UnsupportedSQL(ValueError):
    """Outside this deliberately narrow AST grammar."""


def tokenize(sql: str) -> list[Token]:
    tokens = []
    offset = 0
    while offset < len(sql):
        match = LEXEME.match(sql, offset)
        if match is None:
            raise UnsupportedSQL("unrecognized SQL token")
        lexeme = match.group()
        offset = match.end()
        if lexeme.isspace():
            continue
        if lexeme.startswith('"'):
            tokens.append(Token(lexeme[1:-1].replace('""', '"'), "quoted"))
        elif IDENT.fullmatch(lexeme):
            tokens.append(Token(lexeme.lower(), "name"))
        elif lexeme.isdigit():
            tokens.append(Token(lexeme, "integer"))
        else:
            tokens.append(Token(lexeme, "punctuation"))
    return tokens


class Parser:
    def __init__(self, sql: str):
        self.tokens = tokenize(sql)
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> Token:
        token = self.peek()
        if token is None:
            raise UnsupportedSQL("incomplete SQL")
        self.pos += 1
        return token

    def expect(self, value: str) -> None:
        token = self.take()
        if token.kind == "quoted" or token.value != value.lower():
            raise UnsupportedSQL(f"expected {value}")

    def name(self) -> str:
        token = self.take()
        if token.kind not in {"name", "quoted"} or (
                token.kind == "name" and token.value in RESERVED):
            raise UnsupportedSQL("expected identifier")
        return token.value

    def end(self) -> None:
        if self.peek() is not None:
            raise UnsupportedSQL("extra SQL clause or expression")

    def expression(self) -> Column | Case:
        if self.peek() == Token("case", "name"):
            self.expect("case")
            self.expect("when")
            flag = Column(self.name())
            self.expect("then")
            value = Column(self.name())
            self.expect("else")
            zero = self.take()
            if zero != Token("0", "integer"):
                raise UnsupportedSQL("CASE must have literal ELSE 0")
            self.expect("end")
            return Case(flag, value, Zero())
        return Column(self.name())

    def relation(self) -> tuple[str, ...]:
        parts = [self.name()]
        while self.peek() == Token(".", "punctuation"):
            self.take()
            parts.append(self.name())
        return tuple(parts)


def parse_expression(raw: str) -> Column | Case:
    parser = Parser(raw)
    node = parser.expression()
    parser.end()
    return node


def parse_relation(raw: str) -> tuple[str, ...]:
    parser = Parser(raw)
    relation = parser.relation()
    parser.end()
    return relation


def parse_sum_select(raw: str) -> SumSelect:
    parser = Parser(raw)
    parser.expect("select")
    parser.expect("sum")
    parser.expect("(")
    argument = parser.expression()
    parser.expect(")")
    parser.expect("as")
    output_name = parser.name()
    parser.expect("from")
    relation = parser.relation()
    alias = parser.name() if parser.peek() is not None else None
    parser.end()  # rejects WHERE, JOIN, GROUP BY, a second projection, etc.
    return SumSelect(argument, output_name, relation, alias)


@dataclass(frozen=True)
class CardView:
    card: dict
    measure: dict
    owner: dict
    query: SumSelect


def view(card: dict) -> tuple[CardView | None, str]:
    """Require source expression and generated query to have the same AST."""
    if (card["type"] != "simple" or card["sql_scope"] != "ungrouped"
            or card["metric_filter"] is not None or len(card["input_measures"]) != 1):
        return None, "unsupported_card"
    measure = card["input_measures"][0]
    if measure["owner_count"] != 1 or len(measure["owners"]) != 1:
        return None, "unsupported_card"
    owner = measure["owners"][0]
    if (measure["filter"] is not None or measure["fill_nulls_with"] is not None
            or measure["join_to_timespine"] or owner["agg"] != "sum"
            or owner["non_additive_dimension"] is not None or not owner["expr"]):
        return None, "unsupported_card"
    try:
        query = parse_sum_select(card["compiled_sql"])
        declared = parse_expression(owner["expr"])
        relation = parse_relation(owner["node_relation"])
    except UnsupportedSQL:
        return None, "unsupported_ast"
    if (query.argument != declared or query.relation != relation
            or query.output_name != card["metric_name"].lower()
            or not query.relation_alias):
        return None, "source_compiled_ast_mismatch"
    return CardView(card, measure, owner, query), "parsed"


def documented(masked: CardView, base: CardView, flag: str) -> bool:
    """The description must name the base concept and the flag's scope term."""
    concept = base.card["metric_name"].lower().replace("_", " ")
    terms = [part for part in flag.lower().split("_")
             if part not in {"is", "item", "items", "product", "flag"}]
    description = masked.card.get("description")
    if (not isinstance(description, str) or not isinstance(base.card.get("description"), str)
            or not concept or not terms):
        return False
    prose = description.lower()
    if not re.search(r"\b" + re.escape(concept) + r"\b", prose):
        return False
    if not any(re.search(r"\b" + re.escape(term) + r"[a-z]*\b", prose)
               for term in terms):
        return False
    # verify_packet already compared each complete source file with the pinned
    # Git blob. Re-bind both descriptions to their exact declaration spans.
    for view_ in (masked, base):
        card = view_.card
        start, end = card["declared_span_text_located"]
        lines = (REPO / card["declared_file"]).read_text().splitlines()[start - 1:end]
        if not any(line.strip() == "description: " + card["description"] for line in lines):
            return False
    return True


def directly_projected(models: list[dict], flag: str) -> bool:
    """Require the owner model to select the flag as a bare qualified field.

    This catches a negated/OR expression at this model boundary. It does not
    establish the field's earlier definition or its boolean semantics.
    """
    direct = re.compile(r"^\s*[A-Za-z_][A-Za-z_0-9]*\." + re.escape(flag)
                        + r"\s*,?\s*$", re.I)
    return any(direct.fullmatch(line) for model in models
               for line in model["raw_sql"].splitlines())


def compare(a: dict, b: dict) -> dict:
    """Return a scoped class prediction or an explicit abstention reason."""
    if a["sql_scope"] != b["sql_scope"]:
        return {"decision": "abstain", "reason": "cross_scope"}
    va, ra = view(a)
    vb, rb = view(b)
    if va is None or vb is None:
        return {"decision": "abstain", "reason": ra if va is None else rb}
    for masked, base in ((va, vb), (vb, va)):
        case, plain = masked.query.argument, base.query.argument
        if not (isinstance(case, Case) and isinstance(plain, Column)
                and case.value == plain and case.flag != plain):
            continue
        mo, bo = masked.owner, base.owner
        same_context = (all(mo[k] == bo[k] for k in
                            ("semantic_model", "model_node", "node_relation", "agg_time_dimension"))
                        and all(mo[k] for k in ("semantic_model", "model_node",
                                                     "node_relation", "agg_time_dimension"))
                        and masked.card["source_models"] == base.card["source_models"]
                        and any(model["node"] in mo["model_node"] for model in
                                masked.card["source_models"]))
        if not same_context:
            return {"decision": "abstain", "reason": "source_context_unlinked"}
        flag = case.flag.name
        domain = ATOMIC_ITEM_FLAG.fullmatch(flag)
        if domain is None or domain.group(1).startswith(("not", "non", "no")):
            return {"decision": "abstain", "reason": "non_atomic_or_negative_flag_name"}
        if not directly_projected(masked.card["source_models"], flag):
            return {"decision": "abstain", "reason": "flag_not_directly_projected"}
        if not documented(masked, base, flag):
            return {"decision": "abstain", "reason": "documentation_unlinked"}
        return {"decision": "temporal_or_scope_variant", "reason": "documented_ast_mask",
                "masked": masked.card["metric_name"], "base": base.card["metric_name"],
                "flag": flag, "value": plain.name,
                "masked_measure_span": masked.owner["measure_span"],
                "base_measure_span": base.owner["measure_span"],
                "masked_declaration_span": masked.card["declared_span_text_located"],
                "base_declaration_span": base.card["declared_span_text_located"],
                "source_file": masked.owner["semantic_model_file"],
                "model_file": masked.card["source_models"][0]["source_file"],
                "model_sha256": masked.card["source_models"][0]["raw_sql_sha256"],
                "masked_compiled_sha256": masked.card["compiled_sql_sha256"],
                "base_compiled_sha256": base.card["compiled_sql_sha256"],
                "description": masked.card["description"]}
    return {"decision": "abstain", "reason": "outside_mask_shape"}


def run() -> dict:
    packet = verify_packet()
    cards = {card["metric_id"]: card for card in packet["cards"]}
    rows = []
    for pair in packet["pairs"]:
        outcome = compare(cards[pair["a"]], cards[pair["b"]])
        rows.append({"pair_id": pair["pair_id"], **outcome})
    counts = Counter(row["decision"] for row in rows)
    reasons = Counter(row["reason"] for row in rows)
    assert len(rows) == packet["pair_count"] == 171 == sum(counts.values())
    assert len({row["pair_id"] for row in rows}) == 171
    return {"source_commit": packet["source_commit"],
            "pair_set_sha256": packet["pair_set_sha256"],
            "counts": dict(counts), "reasons": dict(sorted(reasons.items())), "rows": rows}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
