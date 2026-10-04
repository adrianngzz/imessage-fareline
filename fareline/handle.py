"""Apply one action to the ledger and build the reply. Doors call this."""

from __future__ import annotations

from fareline.confirm import (
    format_balance,
    format_fare,
    format_payback,
    format_rsvp,
    format_undo,
    nets_card,
)
from fareline.intents import interpret
from fareline.ledger import Ledger
from fareline.people import PEOPLE, canonical


def handle(text: str, speaker: str, ledger: Ledger, model=None) -> dict:
    who = canonical(speaker)
    if who is None:
        return _result(
            "Who's speaking? Use Adrian, Tessa, or John.",
            {"action": "clarify", "question": "Who's speaking?"},
            ledger,
        )

    roster = dict(ledger.roster)
    action = interpret(text, who, roster, model)
    kind = action["action"]

    if kind == "clarify":
        return _result(action["question"], action, ledger)
    if kind == "rsvp":
        ledger.rsvp(action["person"], action["in"])
        reply = format_rsvp(action["person"], action["in"], ledger.in_roster(), ledger.out_roster())
        return _result(reply, action, ledger)
    if kind == "record_fare":
        ledger.record_fare(action["payer"], action["amount_cents"], action["riders"])
        stored = ledger.events[-1]
        reply = format_fare(stored["payer"], stored["amount_cents"], stored["riders"], ledger.nets())
        return _result(reply, action, ledger, card_title="Fareline")
    if kind == "record_payback":
        ledger.record_payback(action["from"], action["to"], action["amount_cents"])
        reply = format_payback(
            action["from"],
            action["to"],
            action["amount_cents"],
            ledger.settlements(),
            ledger.nets(),
        )
        return _result(reply, action, ledger, card_title="Fareline")
    if kind == "get_balance":
        reply = format_balance(action["person"], ledger)
        return _result(reply, action, ledger)
    if kind == "undo":
        event = ledger.undo()
        if event is None:
            return _result("Nothing to undo.", action, ledger)
        reply = format_undo(event["type"], ledger.nets())
        return _result(reply, action, ledger)
    return _result("Tell me who's in, who paid, or ask what you owe.", {"action": "clarify"}, ledger)


def _result(reply: str, action: dict, ledger: Ledger, card_title: str | None = None) -> dict:
    nets = ledger.nets()
    card = nets_card(card_title, nets) if card_title else None
    return {
        "reply": reply,
        "action": action.get("action"),
        "nets_cents": nets,
        "settlements": ledger.settlements(),
        "roster": {"in": ledger.in_roster(), "out": ledger.out_roster()},
        "card_kind": "detail" if card else None,
        "card": card,
        "people": list(PEOPLE),
    }
