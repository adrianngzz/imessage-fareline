"""Append-only fare and payback events. Nets are derived, never stored."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from fareline.people import PEOPLE


class Ledger:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.roster: dict[str, bool | None] = {person: None for person in PEOPLE}
        self.events: list[dict] = []
        self.can_undo = False
        if self.path.exists():
            self._load()

    def rsvp(self, person: str, is_in: bool) -> None:
        with self._lock:
            self.roster[person] = bool(is_in)
            self._save()

    def record_fare(self, payer: str, amount_cents: int, riders: list[str]) -> None:
        riders = _unique(riders)
        if payer not in riders:
            riders.append(payer)
        riders = [person for person in PEOPLE if person in riders]
        if amount_cents <= 0 or not riders:
            raise ValueError("fare needs a positive amount and at least the payer")
        with self._lock:
            self.events.append(
                {
                    "type": "fare",
                    "payer": payer,
                    "amount_cents": amount_cents,
                    "riders": riders,
                }
            )
            self.can_undo = True
            self._save()

    def record_payback(self, frm: str, to: str, amount_cents: int) -> None:
        if frm == to or amount_cents <= 0:
            raise ValueError("payback needs two people and a positive amount")
        with self._lock:
            self.events.append(
                {
                    "type": "payback",
                    "from": frm,
                    "to": to,
                    "amount_cents": amount_cents,
                }
            )
            self.can_undo = True
            self._save()

    def undo(self) -> dict | None:
        """Pop the latest fare or payback. A second undo does nothing until a new one is recorded."""
        with self._lock:
            if not self.can_undo or not self.events:
                return None
            event = self.events.pop()
            self.can_undo = False
            self._save()
            return event

    def in_roster(self) -> list[str]:
        with self._lock:
            return [person for person in PEOPLE if self.roster.get(person) is True]

    def out_roster(self) -> list[str]:
        with self._lock:
            return [person for person in PEOPLE if self.roster.get(person) is False]

    def debt(self) -> dict[str, dict[str, int]]:
        """debt[creditor][debtor] is cents the debtor owes the creditor."""
        with self._lock:
            events = list(self.events)
        table = {creditor: {debtor: 0 for debtor in PEOPLE if debtor != creditor} for creditor in PEOPLE}
        for event in events:
            if event["type"] == "fare":
                share = event["amount_cents"] // len(event["riders"])
                for rider in event["riders"]:
                    if rider != event["payer"]:
                        table[event["payer"]][rider] += share
            elif event["type"] == "payback":
                _apply_payment(table, event["from"], event["to"], event["amount_cents"])
        _collapse(table)
        return table

    def nets(self) -> dict[str, int]:
        table = self.debt()
        nets: dict[str, int] = {}
        for person in PEOPLE:
            credit = sum(table[person].values())
            debit = sum(table[other][person] for other in PEOPLE if other != person)
            nets[person] = credit - debit
        return nets

    def settlements(self) -> list[dict]:
        table = self.debt()
        rows = []
        for creditor in PEOPLE:
            for debtor in PEOPLE:
                if creditor == debtor:
                    continue
                amount = table[creditor][debtor]
                if amount:
                    rows.append({"from": debtor, "to": creditor, "amount_cents": amount})
        return rows

    def counterparties(self, person: str) -> list[str]:
        """People this person has directly owed or been owed by."""
        with self._lock:
            events = list(self.events)
        found: list[str] = []
        for event in events:
            other: str | None = None
            if event["type"] == "fare" and person in event["riders"]:
                if person == event["payer"]:
                    for rider in event["riders"]:
                        if rider != person and rider not in found:
                            found.append(rider)
                else:
                    other = event["payer"]
            elif event["type"] == "payback":
                if event["from"] == person:
                    other = event["to"]
                elif event["to"] == person:
                    other = event["from"]
            if other and other not in found:
                found.append(other)
        return [name for name in PEOPLE if name in found]

    def public_state(self) -> dict:
        nets = self.nets()
        from fareline.money import signed_net

        return {
            "nets_cents": nets,
            "nets_display": {person: signed_net(nets[person]) for person in PEOPLE},
            "settlements": self.settlements(),
            "roster": {"in": self.in_roster(), "out": self.out_roster()},
            "events": list(self.events),
        }

    def _load(self) -> None:
        raw = json.loads(self.path.read_text())
        roster = raw.get("roster") or {}
        for person in PEOPLE:
            value = roster.get(person)
            self.roster[person] = None if value is None else bool(value)
        stored = list(raw.get("events") or [])
        self.events = [event for event in stored if _known_event(event)]
        self.can_undo = bool(raw.get("can_undo", False)) and len(self.events) == len(stored)
        if len(self.events) != len(stored):
            self.can_undo = False
            self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "roster": {person: value for person, value in self.roster.items() if value is not None},
            "events": self.events,
            "can_undo": self.can_undo,
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        tmp.replace(self.path)


def fare_shares(amount_cents: int, riders: list[str], payer: str) -> dict[str, int]:
    """Even split. Any leftover cent stays with the payer, so the parts add up to the fare."""
    others = [rider for rider in riders if rider != payer]
    if not others:
        return {}
    share = amount_cents // len(riders)
    return {rider: share for rider in others}


def _apply_payment(table: dict[str, dict[str, int]], frm: str, to: str, amount: int) -> None:
    owed = table[to][frm]
    if amount <= owed:
        table[to][frm] = owed - amount
        return
    table[to][frm] = 0
    table[frm][to] += amount - owed


def _collapse(table: dict[str, dict[str, int]]) -> None:
    for index, left in enumerate(PEOPLE):
        for right in PEOPLE[index + 1 :]:
            left_is_owed = table[left][right]
            right_is_owed = table[right][left]
            if left_is_owed >= right_is_owed:
                table[left][right] = left_is_owed - right_is_owed
                table[right][left] = 0
            else:
                table[right][left] = right_is_owed - left_is_owed
                table[left][right] = 0


def _known_event(event: dict) -> bool:
    if event.get("type") == "fare":
        names = [event.get("payer"), *(event.get("riders") or [])]
    elif event.get("type") == "payback":
        names = [event.get("from"), event.get("to")]
    else:
        return False
    return all(isinstance(name, str) and name in PEOPLE for name in names)


def _unique(names: list[str]) -> list[str]:
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen
