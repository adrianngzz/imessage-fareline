"""Fetch.ai door. Forwards ASI:One chat to the local ledger. Does not split fares."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    MetadataContent,
    TextContent,
    chat_protocol_spec,
)

from fareline.people import canonical

ACT_URL = os.environ.get("FARELINE_ACT_URL", "http://127.0.0.1:8787/act")
PORT = int(os.environ.get("AGENT_PORT", "8001"))
MAILBOX = os.environ.get("AGENT_MAILBOX") == "1"
SEED_PATH = Path(os.environ.get("FARELINE_SEED_PATH", "data/agent.seed"))


def load_seed() -> str:
    """The seed is the agent identity. Keep the same file from registration through judging."""
    chosen = os.environ.get("AGENT_SEED")
    if chosen:
        return chosen.strip()
    if SEED_PATH.exists():
        return SEED_PATH.read_text().strip()
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    created = f"fareline-{uuid4().hex}"
    SEED_PATH.write_text(created + "\n")
    print(f"Wrote a new agent seed to {SEED_PATH.resolve()}", flush=True)
    print("Keep this file. Do not change it after you register on Agentverse.", flush=True)
    return created


SEED = load_seed()

endpoint = os.environ.get("AGENT_ENDPOINT", f"http://127.0.0.1:{PORT}/submit")
if not endpoint.rstrip("/").endswith("/submit"):
    endpoint = endpoint.rstrip("/") + "/submit"

agent_kwargs: dict = {"name": "fareline", "seed": SEED, "port": PORT}
if MAILBOX:
    agent_kwargs["mailbox"] = True
else:
    agent_kwargs["endpoint"] = [endpoint]

agent = Agent(**agent_kwargs)
chat_proto = Protocol(spec=chat_protocol_spec)

_PREFIX = re.compile(r"^(Riley|Alex|Sam|Jordan)\s*:\s*([\s\S]+)$", re.IGNORECASE)
_INTRO = re.compile(r"^i(?:'m| am)\s+(riley|alex|sam|jordan)\s*[.!]?\s*$", re.IGNORECASE)
_MENTIONS = re.compile(r"^(?:@\S+\s+)+")


def strip_routing(text: str) -> str:
    """ASI:One prepends @agent1q… so Riley: is not at the start of the raw line."""
    return _MENTIONS.sub("", text.strip()).strip()


def message_text(msg: ChatMessage) -> str:
    reader = getattr(msg, "text", None)
    if callable(reader):
        found = reader()
        if isinstance(found, str) and found.strip():
            return found.strip()
    parts = [item.text for item in msg.content if isinstance(item, TextContent) and item.text]
    return "\n".join(parts).strip()


def card_action(text: str) -> str | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and set(data) == {"action"} and data["action"] in {"ack", "undo"}:
        return data["action"]
    return None


def resolve(ctx: Context, sender: str, text: str) -> tuple[str, str, str | None]:
    text = strip_routing(text)
    prefixed = _PREFIX.match(text)
    if prefixed:
        person = canonical(prefixed.group(1)) or ""
        ctx.storage.set(f"speaker:{sender}", person)
        return person, prefixed.group(2).strip(), None
    intro = _INTRO.match(text)
    if intro:
        person = canonical(intro.group(1)) or ""
        ctx.storage.set(f"speaker:{sender}", person)
        return person, "", f"Hi {person}. Say you're in, tell me a fare, or ask what you owe."
    stored = ctx.storage.get(f"speaker:{sender}")
    if isinstance(stored, str) and stored:
        return stored, text, None
    return "", text, None


def post_act(speaker: str, text: str) -> dict:
    request = urllib.request.Request(
        ACT_URL,
        data=json.dumps({"speaker": speaker, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def chat_from(text: str, card_kind: str | None = None, card: dict | None = None) -> ChatMessage:
    content: list = [TextContent(type="text", text=text)]
    if card_kind and card is not None:
        content.append(
            MetadataContent(
                metadata={
                    "card_protocol_version": "1",
                    "requires_card_interaction": "true",
                    "card_kind": card_kind,
                    "card_payload": json.dumps(card),
                    "preferred_drawer_width_px": "420",
                }
            )
        )
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=content,
    )


@chat_proto.on_message(ChatMessage)
async def on_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )
    text = message_text(msg)
    if not text:
        return

    selected = card_action(text)
    if selected == "ack":
        await ctx.send(sender, chat_from("Tab's unchanged."))
        return
    if selected == "undo":
        text = "undo"

    speaker, body, immediate = resolve(ctx, sender, text)
    if immediate:
        await ctx.send(sender, chat_from(immediate))
        return
    if not speaker and body == "undo":
        speaker = "Riley"
    if not speaker:
        await ctx.send(
            sender,
            chat_from("Who's asking? Start the line with Riley:, Alex:, Sam:, or Jordan:."),
        )
        return
    if not body:
        return
    try:
        result = post_act(speaker, body)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        ctx.logger.exception("ledger POST failed")
        await ctx.send(
            sender,
            chat_from(f"The tab isn't reachable at {ACT_URL}. Start the ledger server. ({exc})"),
        )
        return
    await ctx.send(
        sender,
        chat_from(result.get("reply") or "No reply.", result.get("card_kind"), result.get("card")),
    )


@chat_proto.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    ctx.logger.info(f"ack from {sender} for {msg.acknowledged_msg_id}")


agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    print(f"Fareline uAgent address: {agent.address}", flush=True)
    print(f"Calling ledger at {ACT_URL}", flush=True)
    if MAILBOX:
        print("Mailbox mode. Agentverse delivers chat here.", flush=True)
    else:
        print(f"Endpoint: {endpoint}", flush=True)
    print(f"Seed file: {SEED_PATH.resolve()}", flush=True)
    agent.run()
