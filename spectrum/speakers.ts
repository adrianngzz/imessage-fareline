/** Map a chat line onto Adrian, Tessa, or John. No ledger math. */

import { phoneKey } from "./contacts.ts";

export const PEOPLE = ["Adrian", "Tessa", "John"] as const;

const PREFIX = new RegExp(`^(${PEOPLE.join("|")})\\s*:\\s*([\\s\\S]+)$`, "i");
const INTRO = new RegExp(`^i(?:'m| am)\\s+(${PEOPLE.join("|")})\\s*[.!]?\\s*$`, "i");

export function canonical(name: string): string | undefined {
  return PEOPLE.find((person) => person.toLowerCase() === name.toLowerCase());
}

export type SpeakerInput = {
  platform: string;
  senderId: string;
  text: string;
  senderMap: Record<string, string>;
  memory: Map<string, string>;
  contactName?: string;
  fallbackSpeaker?: string;
};

export type SpeakerResult =
  | { speaker: string; text: string }
  | { hello: string }
  | { error: string }
  | { ignore: true };

export function resolveSpeaker(input: SpeakerInput): SpeakerResult {
  const text = input.text.trim();
  if (!text) return { ignore: true };

  const prefixed = text.match(PREFIX);
  if (prefixed) {
    const person = canonical(prefixed[1]) ?? prefixed[1];
    const body = prefixed[2].trim();
    if (input.senderId) input.memory.set(input.senderId, person);
    if (!body) return { hello: `Hi ${person}. Say you're in, tell me a fare, or ask what you owe.` };
    return { speaker: person, text: body };
  }

  const intro = text.match(INTRO);
  if (intro) {
    const person = canonical(intro[1]);
    if (!person) return { error: "Who's speaking? Use Adrian, Tessa, or John." };
    if (input.senderId) input.memory.set(input.senderId, person);
    return { hello: `Hi ${person}. Say you're in, tell me a fare, or ask what you owe.` };
  }

  const mapped = senderPerson(input.senderMap, input.senderId);
  if (mapped) return { speaker: mapped, text };

  const remembered = input.memory.get(input.senderId);
  if (remembered && canonical(remembered)) {
    return { speaker: remembered, text };
  }

  const fromContacts = input.contactName ? personFromContact(input.contactName) : undefined;
  if (fromContacts) {
    if (input.senderId) input.memory.set(input.senderId, fromContacts);
    return { speaker: fromContacts, text };
  }

  if (input.platform === "terminal" && input.fallbackSpeaker && canonical(input.fallbackSpeaker)) {
    return { speaker: canonical(input.fallbackSpeaker) as string, text };
  }

  const seen = input.contactName?.trim() || input.senderId || "this sender";
  return {
    error: `I don't know which intern ${seen} is. Start one line with Adrian: and I'll remember this phone.`,
  };
}

function senderPerson(senderMap: Record<string, string>, senderId: string): string | undefined {
  const direct = canonical(senderMap[senderId] ?? "");
  if (direct) return direct;
  const email = senderId.includes("@") ? senderId.trim().toLowerCase() : undefined;
  const phone = email ? undefined : phoneKey(senderId);
  for (const [key, value] of Object.entries(senderMap)) {
    const person = canonical(value);
    if (!person) continue;
    if (email && key.trim().toLowerCase() === email) return person;
    if (phone && phoneKey(key) === phone) return person;
  }
  return undefined;
}

function personFromContact(name: string): string | undefined {
  const full = canonical(name);
  if (full) return full;
  const first = name.trim().split(/\s+/)[0];
  return first ? canonical(first) : undefined;
}
