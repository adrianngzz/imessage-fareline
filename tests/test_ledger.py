import json
import threading
import urllib.request
from pathlib import Path

from fareline.handle import handle
from fareline.intents import interpret, validate_action
from fareline.ledger import Ledger
from fareline.server import serve

FARE = """Got it — Riley paid $48.00. Riders: Riley, Alex, Sam.
Even split: $16.00 each.
Alex owes Riley $16.00
Sam owes Riley $16.00

Running net:
  Riley  +$32.00
  Alex   −$16.00
  Sam    −$16.00
  Jordan  $0.00"""

PAYBACK = """Got it — Alex paid Riley $16.00.
Alex is settled with Riley.
Sam owes Riley $16.00.

Running net:
  Riley  +$16.00
  Alex    $0.00
  Sam    −$16.00
  Jordan  $0.00"""


def test_fare_split_and_nets(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Riley", 4800, ["Riley", "Alex", "Sam"])
    assert ledger.nets() == {"Riley": 3200, "Alex": -1600, "Sam": -1600, "Jordan": 0}


def test_payback_clears_one_pair(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Riley", 4800, ["Riley", "Alex", "Sam"])
    ledger.record_payback("Alex", "Riley", 1600)
    assert ledger.nets() == {"Riley": 1600, "Alex": 0, "Sam": -1600, "Jordan": 0}
    assert ledger.settlements() == [{"from": "Sam", "to": "Riley", "amount_cents": 1600}]


def test_jordan_out_is_unchanged(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.rsvp("Jordan", False)
    ledger.record_fare("Riley", 4800, ["Riley", "Alex", "Sam"])
    assert ledger.roster["Jordan"] is False
    assert ledger.nets()["Jordan"] == 0


def test_balance_before_payback(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    reply = handle("I paid $48, Alex and Sam rode.", "Riley", ledger)["reply"]
    assert reply == FARE
    balance = handle("What do I owe?", "Alex", ledger)["reply"]
    assert "Alex, you owe Riley $16.00." in balance


def test_golden_transcript(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    assert "In: Riley" in handle("I'm in", "Riley", ledger)["reply"]
    handle("I'm in", "Alex", ledger)
    handle("I'm in", "Sam", ledger)
    roster = handle("I'm out", "Jordan", ledger)["reply"]
    assert "In: Riley, Alex, Sam" in roster
    assert "Out: Jordan" in roster

    fare = handle("I paid $48, Alex and Sam rode.", "Riley", ledger)
    assert fare["reply"] == FARE
    assert fare["card_kind"] == "detail"
    assert fare["nets_cents"]["Riley"] == 3200

    payback = handle("I just paid Riley $16.", "Alex", ledger)
    assert payback["reply"] == PAYBACK
    assert payback["card_kind"] == "detail"

    balance = handle("What do I owe?", "Alex", ledger)
    assert balance["card"] is None
    assert "you’re settled with Riley" in balance["reply"]
    assert "Sam owes Riley $16.00." in balance["reply"]
    assert "Alex    $0.00" in balance["reply"]


def test_who_is_coming_two_yeses(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    asked = handle("Who's coming this morning?", "Riley", ledger)
    assert asked["action"] == "rsvp"
    assert "Riley is in" in asked["reply"]
    assert asked["roster"] == {"in": ["Riley"], "out": []}

    assert handle("yes", "Alex", ledger)["action"] == "rsvp"
    second = handle("yeah I'll ride", "Sam", ledger)
    assert second["action"] == "rsvp"
    assert "In: Riley, Alex, Sam" in second["reply"]
    assert "Out: —" in second["reply"]
    assert ledger.roster["Jordan"] is None


def test_total_uses_roster_and_skips_jordan(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    handle("I'm in", "Riley", ledger)
    handle("I'm in", "Alex", ledger)
    handle("I'm in", "Sam", ledger)
    handle("I'm out", "Jordan", ledger)
    result = handle("The total is $48", "Riley", ledger)
    assert result["reply"] == FARE
    assert result["nets_cents"]["Jordan"] == 0


def test_remainder_stays_with_payer(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Riley", 4801, ["Riley", "Alex", "Sam"])
    assert ledger.nets() == {"Riley": 3200, "Alex": -1600, "Sam": -1600, "Jordan": 0}


def test_undo_is_one_level(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    handle("I paid $48, Alex and Sam rode.", "Riley", ledger)
    undone = handle("wait that's wrong", "Riley", ledger)
    assert undone["nets_cents"] == {"Riley": 0, "Alex": 0, "Sam": 0, "Jordan": 0}
    assert "Undid the last fare." in undone["reply"]
    again = handle("undo", "Alex", ledger)
    assert again["reply"] == "Nothing to undo."


def test_reload_keeps_nets(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    first = Ledger(path)
    first.record_fare("Riley", 4800, ["Riley", "Alex", "Sam"])
    second = Ledger(path)
    assert second.nets()["Alex"] == -1600


def test_missing_riders_clarify(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    result = handle("I paid $48", "Riley", ledger)
    assert result["action"] == "clarify"
    assert result["nets_cents"]["Riley"] == 0


def test_keyword_wins_over_model() -> None:
    calls: list[str] = []

    def model(text: str, speaker: str, roster: dict) -> dict:
        calls.append(text)
        return {"action": "undo"}

    action = interpret("I paid $48, Alex and Sam rode.", "Riley", {}, model)
    assert action["action"] == "record_fare"
    assert action["amount_cents"] == 4800
    assert calls == []


def test_model_fills_gaps_and_cannot_pass_a_share() -> None:
    def model(text: str, speaker: str, roster: dict) -> dict:
        return {
            "action": "record_fare",
            "payer": "Riley",
            "amount_cents": 4800,
            "riders": ["Alex", "Sam"],
            "share": 16,
        }

    action = interpret("covered the lyft", "Riley", {}, model)
    assert action["riders"] == ["Riley", "Alex", "Sam"]
    assert "share" not in action
    validated = validate_action({"action": "record_fare", "amount_cents": 48.5}, "Riley")
    assert validated["action"] == "clarify"


def test_act_and_nets_http(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    server = serve(ledger, port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.dumps(
            {"speaker": "Riley", "text": "I paid $48, Alex and Sam rode."}
        ).encode()
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/act",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            body = json.loads(response.read().decode())
        assert body["reply"] == FARE
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/nets") as response:
            nets = json.loads(response.read().decode())
        assert nets["nets_cents"]["Sam"] == -1600
    finally:
        server.shutdown()
        server.server_close()
