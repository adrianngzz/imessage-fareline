"""Turn one chat line into one action. No split math in here."""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.request
from collections.abc import Callable

import certifi

from fareline.money import dollars_to_cents
from fareline.people import PEOPLE, canonical

Model = Callable[[str, str, dict], dict]

_NAME = "(" + "|".join(name.lower() for name in PEOPLE) + ")"
_WHO = ", ".join(PEOPLE)
_AMOUNT = r"\$?\s*(\d+(?:\.\d{1,2})?)"


def interpret(
    text: str,
    speaker: str,
    roster: dict | None = None,
    model: Model | None = None,
) -> dict:
    """Keyword parse first, so the golden transcript does not depend on a model."""
    roster = roster or {}
    parsed = keyword_intent(text, speaker, roster)
    if parsed["action"] != "clarify" or model is None:
        return parsed
    try:
        return validate_action(model(text, speaker, roster), speaker)
    except Exception as exc:
        print(f"LLM fallback: {type(exc).__name__}: {exc}", flush=True)
        return parsed


def keyword_intent(text: str, speaker: str, roster: dict | None = None) -> dict:
    roster = roster or {}
    body = " ".join(text.strip().split())
    lowered = body.lower()
    who = canonical(speaker)

    if re.search(r"\bundo\b|that'?s wrong", lowered):
        return {"action": "undo"}

    named_balance = re.search(rf"what does {_NAME} owe", lowered)
    if named_balance:
        return {"action": "get_balance", "person": canonical(named_balance.group(1))}
    if re.search(r"what do i owe|what(?:'s| is) my balance|running net", lowered):
        if who is None:
            return _clarify(f"Who's asking? Use {_WHO}.")
        return {"action": "get_balance", "person": who}

    if re.search(r"\bwho(?:'s|s| is)\s+(coming|in|riding|going)\b", lowered):
        return _rsvp(who, True)

    if re.search(r"\b(i'm|im|i am)\s+out\b", lowered):
        return _rsvp(who, False)
    if re.search(r"\b(i'm|im|i am)\s+in\b", lowered):
        return _rsvp(who, True)
    if re.fullmatch(r"(yes|yeah|yep|yup|yea)[.!]*", lowered):
        return _rsvp(who, True)
    if re.fullmatch(r"(no|nope|nah)[.!]*", lowered):
        return _rsvp(who, False)
    if re.search(r"\b(?:count me in|i(?:'ll| will) ride)\b", lowered):
        return _rsvp(who, True)

    payback = re.search(rf"\b(?:i\s+)?(?:just\s+)?paid\s+{_NAME}\s+{_AMOUNT}\b", lowered)
    if payback:
        if who is None:
            return _clarify(f"Who paid? Use {_WHO}.")
        cents = dollars_to_cents(payback.group(2))
        payee = canonical(payback.group(1))
        if cents is None or payee is None:
            return _clarify("How much did you pay, and who did you pay?")
        if payee == who:
            return _clarify("Who did you pay?")
        return {"action": "record_payback", "from": who, "to": payee, "amount_cents": cents}

    fare_amount = re.search(rf"\b(?:i|we)\s+paid\s+{_AMOUNT}\b", lowered)
    named_payer = None
    if fare_amount is None:
        named = re.search(rf"\b{_NAME}\s+paid\s+{_AMOUNT}\b", lowered)
        if named:
            named_payer = canonical(named.group(1))
            fare_amount = named
            amount_group = 2
        else:
            amount_group = 1
    else:
        amount_group = 1
    total = re.search(rf"\b(?:the\s+)?total\s+is\s+{_AMOUNT}\b", lowered)
    if fare_amount or total:
        match = fare_amount or total
        group_index = amount_group if fare_amount else 1
        cents = dollars_to_cents(match.group(group_index))
        if cents is None:
            return _clarify("How much was the fare?")
        payer = named_payer or who
        if payer is None:
            return _clarify("Who paid?")
        riders = _riders_from_text(lowered, payer, roster, mentioned_rode="rode" in lowered)
        if not riders:
            return _clarify("Who rode?")
        return {
            "action": "record_fare",
            "payer": payer,
            "amount_cents": cents,
            "riders": riders,
        }

    if re.search(r"\bpaid\b", lowered) and not re.search(r"\d", lowered):
        return _clarify("How much was the fare, and who rode?")

    return _clarify("Tell me who's in, who paid, or ask what you owe.")


def validate_action(raw: object, speaker: str) -> dict:
    if not isinstance(raw, dict):
        return _clarify("Tell me who's in, who paid, or ask what you owe.")
    action = raw.get("action")
    who = canonical(speaker)

    if action == "clarify":
        question = raw.get("question")
        if not isinstance(question, str) or not question.strip():
            return _clarify("Who paid, how much was the fare, and who rode?")
        return {"action": "clarify", "question": question.strip()}
    if action == "undo":
        return {"action": "undo"}
    if action == "rsvp":
        person = canonical(raw.get("person")) or who
        return _rsvp(person, raw.get("in") is True or raw.get("in") == "true")
    if action == "get_balance":
        person = canonical(raw.get("person")) or who
        if person is None:
            return _clarify("Who are you asking about?")
        return {"action": "get_balance", "person": person}
    if action == "record_payback":
        frm = canonical(raw.get("from")) or who
        to = canonical(raw.get("to"))
        cents = _cents(raw.get("amount_cents"))
        if frm is None or to is None or cents is None or frm == to:
            return _clarify("Who paid whom, and how much?")
        return {"action": "record_payback", "from": frm, "to": to, "amount_cents": cents}
    if action == "record_fare":
        payer = canonical(raw.get("payer")) or who
        cents = _cents(raw.get("amount_cents"))
        if payer is None or cents is None:
            return _clarify("Who paid, and how much was the fare?")
        riders_in = raw.get("riders")
        if not isinstance(riders_in, list) or not riders_in:
            return _clarify("Who rode?")
        riders: list[str] = []
        for name in riders_in:
            person = canonical(name)
            if person is None:
                return _clarify(f"I only know {_WHO}. Who rode?")
            if person not in riders:
                riders.append(person)
        if payer not in riders:
            riders.append(payer)
        riders = [person for person in PEOPLE if person in riders]
        return {
            "action": "record_fare",
            "payer": payer,
            "amount_cents": cents,
            "riders": riders,
        }
    return _clarify("Tell me who's in, who paid, or ask what you owe.")


def model_from_env() -> Model | None:
    asi_key = os.environ.get("ASI_ONE_API_KEY") or os.environ.get("ASI1_API_KEY")
    key = os.environ.get("FARELINE_LLM_API_KEY") or asi_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    base = os.environ.get("FARELINE_LLM_BASE_URL") or os.environ.get("ASI1_BASE_URL")
    if not base:
        base = "https://api.asi1.ai/v1" if asi_key else "https://api.openai.com/v1"
    base = base.rstrip("/")
    if os.environ.get("FARELINE_LLM_MODEL"):
        model_name = os.environ["FARELINE_LLM_MODEL"]
    elif "asi1.ai" in base:
        model_name = "asi1"
    else:
        model_name = "gpt-4o-mini"

    def call(text: str, speaker: str, roster: dict) -> dict:
        inn = [person for person in PEOPLE if roster.get(person) is True]
        out = [person for person in PEOPLE if roster.get(person) is False]
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Speaker: {speaker}\n"
                        f"In today: {', '.join(inn) or 'nobody yet'}. "
                        f"Out: {', '.join(out) or 'nobody yet'}.\n"
                        f"Message: {text}"
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            body = json.loads(response.read().decode())
        content = body["choices"][0]["message"]["content"]
        return _extract_json(content)

    return call


_SYSTEM = """You turn one intern commute group-chat line into one JSON object. You do not split fares or decide who owes whom.

Known people: Adrian, Tessa, John. "I" and "me" mean the speaker.
Convert dollars to integer cents in amount_cents. $48 is 4800. $16.50 is 1650. Never output a float.

Reply with only one of:
{"action":"rsvp","person":"Adrian","in":true}
{"action":"record_fare","payer":"Adrian","amount_cents":4800,"riders":["Adrian","Tessa","John"]}
{"action":"record_payback","from":"Tessa","to":"Adrian","amount_cents":1600}
{"action":"get_balance","person":"Tessa"}
{"action":"undo"}
{"action":"clarify","question":"one question"}

"Who's coming" / "who's in" means the speaker is in. Yes / yeah / yep is rsvp in. No / nope is rsvp out.
The payer is always a rider. If payer, riders, or amount are missing, return clarify and ask one question.
Never invent a payment, a rider, or an amount."""


def _riders_from_text(lowered: str, payer: str, roster: dict, mentioned_rode: bool) -> list[str]:
    found = [name for name in (canonical(item) for item in re.findall(_NAME, lowered)) if name]
    others = [person for person in PEOPLE if person in found and person != payer]
    if mentioned_rode or others:
        companions = others
    else:
        companions = [person for person in PEOPLE if roster.get(person) is True and person != payer]
    if not companions:
        return []
    return [person for person in PEOPLE if person == payer or person in companions]


def _rsvp(person: str | None, is_in: bool) -> dict:
    if person is None:
        return _clarify(f"Who is in or out? Use {_WHO}.")
    return {"action": "rsvp", "person": person, "in": is_in}


def _cents(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0 and value == int(value):
        return int(value)
    if isinstance(value, str):
        try:
            number = int(value)
        except ValueError:
            return None
        return number if number > 0 else None
    return None


def _clarify(question: str) -> dict:
    return {"action": "clarify", "question": question}


def _extract_json(text: str) -> dict:
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        start = body.find("{")
        end = body.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(body[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("model did not return an object")
    return parsed
