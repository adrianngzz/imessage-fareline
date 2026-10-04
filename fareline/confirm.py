"""Confirmation text. This is the group-chat UI."""

from fareline.ledger import fare_shares
from fareline.money import aligned_net, money, signed_net
from fareline.people import PEOPLE


def running_net(nets: dict[str, int]) -> str:
    rows = [f"  {name:<7}{aligned_net(nets[name])}" for name in PEOPLE]
    return "Running net:\n" + "\n".join(rows)


def format_rsvp(person: str, is_in: bool, roster_in: list[str], roster_out: list[str]) -> str:
    word = "in" if is_in else "out"
    inn = ", ".join(roster_in) if roster_in else "—"
    out = ", ".join(roster_out) if roster_out else "—"
    return f"{person} is {word} for today’s ride. In: {inn}. Out: {out}."


def format_fare(payer: str, amount_cents: int, riders: list[str], nets: dict[str, int]) -> str:
    shares = fare_shares(amount_cents, riders, payer)
    base = amount_cents // len(riders)
    remainder = amount_cents - base * len(riders)
    if remainder:
        split = f"Even split: {money(base)} each. Extra {money(remainder)} stays with {payer}."
    else:
        split = f"Even split: {money(base)} each."
    owes = [
        f"{rider} owes {payer} {money(shares[rider])}"
        for rider in riders
        if rider != payer
    ]
    lines = [
        f"Got it — {payer} paid {money(amount_cents)}. Riders: {', '.join(riders)}.",
        split,
        *owes,
        "",
        running_net(nets),
    ]
    return "\n".join(lines)


def format_payback(
    frm: str,
    to: str,
    amount_cents: int,
    settlements: list[dict],
    nets: dict[str, int],
) -> str:
    cleared = not any(row["from"] == frm and row["to"] == to for row in settlements)
    lines = [f"Got it — {frm} paid {to} {money(amount_cents)}."]
    if cleared:
        lines.append(f"{frm} is settled with {to}.")
    for row in settlements:
        lines.append(f"{row['from']} owes {row['to']} {money(row['amount_cents'])}.")
    lines.append("")
    lines.append(running_net(nets))
    return "\n".join(lines)


def format_balance(person: str, ledger) -> str:
    mine = [row for row in ledger.settlements() if row["from"] == person]
    lines: list[str] = []
    if mine:
        parts = [f"you owe {row['to']} {money(row['amount_cents'])}" for row in mine]
        if len(parts) == 1:
            owed = parts[0]
        else:
            owed = ", ".join(parts[:-1]) + f", and {parts[-1]}"
        lines.append(f"{person}, {owed}.")
    else:
        partners = ledger.counterparties(person)
        if len(partners) == 1:
            lines.append(f"{person}, you’re settled with {partners[0]}. You still have no other debts.")
        elif partners:
            names = ", ".join(partners[:-1]) + f" and {partners[-1]}"
            lines.append(f"{person}, you’re settled with {names}. You still have no other debts.")
        else:
            lines.append(f"{person}, you don’t owe anyone.")
        for row in ledger.settlements():
            if row["from"] != person:
                lines.append(f"{row['from']} owes {row['to']} {money(row['amount_cents'])}.")
    lines.append("")
    lines.append(running_net(ledger.nets()))
    return "\n".join(lines)


def format_undo(kind: str, nets: dict[str, int]) -> str:
    label = "fare" if kind == "fare" else "payback"
    return f"Undid the last {label}.\n\n{running_net(nets)}"


def nets_card(title: str, nets: dict[str, int]) -> dict:
    """ASI:One detail card. The chat text already committed the ledger."""
    return {
        "title": title,
        "summary_rows": [
            {"label": name, "value": signed_net(nets[name])}
            for name in PEOPLE
        ],
        "ctas": [
            {"label": "Looks right", "selection": {"action": "ack"}, "primary": True},
            {"label": "Undo last", "selection": {"action": "undo"}},
        ],
    }
