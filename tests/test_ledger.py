import json
import threading
import urllib.request
from pathlib import Path

from fareline.handle import handle
from fareline.intents import interpret, validate_action
from fareline.ledger import Ledger
from fareline.server import serve

FARE = """Got it — Adrian paid $48.00. Riders: Adrian, Tessa, John.
Even split: $16.00 each.
Tessa owes Adrian $16.00
John owes Adrian $16.00

Running net:
  Adrian +$32.00
  Tessa  −$16.00
  John   −$16.00"""

PAYBACK = """Got it — Tessa paid Adrian $16.00.
Tessa is settled with Adrian.
John owes Adrian $16.00.

Running net:
  Adrian +$16.00
  Tessa   $0.00
  John   −$16.00"""


def test_fare_split_and_nets(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Adrian", 4800, ["Adrian", "Tessa", "John"])
    assert ledger.nets() == {"Adrian": 3200, "Tessa": -1600, "John": -1600}


def test_payback_clears_one_pair(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Adrian", 4800, ["Adrian", "Tessa", "John"])
    ledger.record_payback("Tessa", "Adrian", 1600)
    assert ledger.nets() == {"Adrian": 1600, "Tessa": 0, "John": -1600}
    assert ledger.settlements() == [{"from": "John", "to": "Adrian", "amount_cents": 1600}]


def test_john_out_is_unchanged(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.rsvp("John", False)
    ledger.record_fare("Adrian", 4800, ["Adrian", "Tessa"])
    assert ledger.roster["John"] is False
    assert ledger.nets()["John"] == 0
    assert ledger.nets()["Tessa"] == -2400


def test_balance_before_payback(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    reply = handle("I paid $48, Tessa and John rode.", "Adrian", ledger)["reply"]
    assert reply == FARE
    balance = handle("What do I owe?", "Tessa", ledger)["reply"]
    assert "Tessa, you owe Adrian $16.00." in balance


def test_golden_transcript(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    assert "In: Adrian" in handle("I'm in", "Adrian", ledger)["reply"]
    handle("I'm in", "Tessa", ledger)
    roster = handle("I'm in", "John", ledger)["reply"]
    assert "In: Adrian, Tessa, John" in roster
    assert "Out: —" in roster

    fare = handle("I paid $48, Tessa and John rode.", "Adrian", ledger)
    assert fare["reply"] == FARE
    assert fare["card_kind"] == "detail"
    assert fare["nets_cents"]["Adrian"] == 3200

    payback = handle("I just paid Adrian $16.", "Tessa", ledger)
    assert payback["reply"] == PAYBACK
    assert payback["card_kind"] == "detail"

    balance = handle("What do I owe?", "Tessa", ledger)
    assert balance["card"] is None
    assert "you’re settled with Adrian" in balance["reply"]
    assert "John owes Adrian $16.00." in balance["reply"]
    assert "Tessa   $0.00" in balance["reply"]


def test_who_is_coming_two_yeses(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    asked = handle("Who's coming this morning?", "Adrian", ledger)
    assert asked["action"] == "rsvp"
    assert "Adrian is in" in asked["reply"]
    assert asked["roster"] == {"in": ["Adrian"], "out": []}

    assert handle("yes", "Tessa", ledger)["action"] == "rsvp"
    second = handle("yeah I'll ride", "John", ledger)
    assert second["action"] == "rsvp"
    assert "In: Adrian, Tessa, John" in second["reply"]
    assert "Out: —" in second["reply"]


def test_total_uses_roster(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    handle("I'm in", "Adrian", ledger)
    handle("I'm in", "Tessa", ledger)
    handle("I'm in", "John", ledger)
    result = handle("The total is $48", "Adrian", ledger)
    assert result["reply"] == FARE
    assert result["nets_cents"]["John"] == -1600


def test_remainder_stays_with_payer(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    ledger.record_fare("Adrian", 4801, ["Adrian", "Tessa", "John"])
    assert ledger.nets() == {"Adrian": 3200, "Tessa": -1600, "John": -1600}


def test_undo_is_one_level(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    handle("I paid $48, Tessa and John rode.", "Adrian", ledger)
    undone = handle("wait that's wrong", "Adrian", ledger)
    assert undone["nets_cents"] == {"Adrian": 0, "Tessa": 0, "John": 0}
    assert "Undid the last fare." in undone["reply"]
    again = handle("undo", "Tessa", ledger)
    assert again["reply"] == "Nothing to undo."


def test_reload_keeps_nets(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    first = Ledger(path)
    first.record_fare("Adrian", 4800, ["Adrian", "Tessa", "John"])
    second = Ledger(path)
    assert second.nets()["Tessa"] == -1600


def test_missing_riders_clarify(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    result = handle("I paid $48", "Adrian", ledger)
    assert result["action"] == "clarify"
    assert result["nets_cents"]["Adrian"] == 0


def test_keyword_wins_over_model() -> None:
    calls: list[str] = []

    def model(text: str, speaker: str, roster: dict) -> dict:
        calls.append(text)
        return {"action": "undo"}

    action = interpret("I paid $48, Tessa and John rode.", "Adrian", {}, model)
    assert action["action"] == "record_fare"
    assert action["amount_cents"] == 4800
    assert calls == []


def test_model_fills_gaps_and_cannot_pass_a_share() -> None:
    def model(text: str, speaker: str, roster: dict) -> dict:
        return {
            "action": "record_fare",
            "payer": "Adrian",
            "amount_cents": 4800,
            "riders": ["Tessa", "John"],
            "share": 16,
        }

    action = interpret("covered the lyft", "Adrian", {}, model)
    assert action["riders"] == ["Adrian", "Tessa", "John"]
    assert "share" not in action
    validated = validate_action({"action": "record_fare", "amount_cents": 48.5}, "Adrian")
    assert validated["action"] == "clarify"


def test_act_and_nets_http(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.json")
    server = serve(ledger, port=0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payload = json.dumps(
            {"speaker": "Adrian", "text": "I paid $48, Tessa and John rode."}
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
        assert nets["nets_cents"]["John"] == -1600
    finally:
        server.shutdown()
        server.server_close()


def test_old_names_are_dropped_on_load(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text(
        '{"roster":{"Riley":true},"events":[{"type":"fare","payer":"Riley","amount_cents":4800,"riders":["Riley","Alex"]}],"can_undo":true}\n',
        encoding="utf-8",
    )
    ledger = Ledger(path)
    assert ledger.events == []
    assert ledger.nets() == {"Adrian": 0, "Tessa": 0, "John": 0}
