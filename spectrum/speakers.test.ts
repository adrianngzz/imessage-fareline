import assert from "node:assert/strict";
import test from "node:test";

import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { DatabaseSync } from "node:sqlite";

import { contactName } from "./contacts.ts";
import { loadEnv } from "./env.ts";
import { resolveSpeaker } from "./speakers.ts";
import { acceptSpace, resetAnnouncedSpaces } from "./spaces.ts";

test("a name prefix selects the intern and the rest of the line", () => {
  const memory = new Map<string, string>();
  const resolved = resolveSpeaker({
    platform: "local_imessage",
    senderId: "+15555550100",
    text: "Adrian: I paid $48, Tessa and John rode.",
    senderMap: {},
    memory,
  });
  assert.deepEqual(resolved, {
    speaker: "Adrian",
    text: "I paid $48, Tessa and John rode.",
  });
  assert.equal(memory.get("+15555550100"), "Adrian");
});

test("senders.json maps an iMessage address", () => {
  const resolved = resolveSpeaker({
    platform: "local_imessage",
    senderId: "+15555550101",
    text: "What do I owe?",
    senderMap: { "+15555550101": "Tessa" },
    memory: new Map(),
  });
  assert.deepEqual(resolved, { speaker: "Tessa", text: "What do I owe?" });
});

test("a contact first name is the intern, with no prefix", () => {
  const memory = new Map<string, string>();
  const resolved = resolveSpeaker({
    platform: "local_imessage",
    senderId: "+1 (415) 555-0101",
    text: "What do I owe?",
    senderMap: {},
    memory,
    contactName: "Tessa Ng",
  });
  assert.deepEqual(resolved, { speaker: "Tessa", text: "What do I owe?" });
  assert.equal(memory.get("+1 (415) 555-0101"), "Tessa");
});

test("a formatted phone matches senders.json", () => {
  const resolved = resolveSpeaker({
    platform: "local_imessage",
    senderId: "+14155550102",
    text: "I'm in",
    senderMap: { "+1 415-555-0102": "John" },
    memory: new Map(),
  });
  assert.deepEqual(resolved, { speaker: "John", text: "I'm in" });
});

test("contacts lookup reads a first name from an address book", () => {
  const root = mkdtempSync(join(tmpdir(), "fareline-contacts-"));
  const db = new DatabaseSync(join(root, "AddressBook-v22.abcddb"));
  db.exec(`
    CREATE TABLE ZABCDRECORD (Z_PK INTEGER, ZFIRSTNAME TEXT, ZLASTNAME TEXT);
    CREATE TABLE ZABCDPHONENUMBER (ZOWNER INTEGER, ZFULLNUMBER TEXT);
    INSERT INTO ZABCDRECORD VALUES (1, 'John', 'Lee');
    INSERT INTO ZABCDPHONENUMBER VALUES (1, '(734) 555-0199');
  `);
  db.close();
  assert.equal(contactName("+17345550199", root), "John Lee");
  assert.equal(contactName("nobody@example.com", root), undefined);
});

test("terminal fallback speaker does not apply to iMessage", () => {
  const resolved = resolveSpeaker({
    platform: "local_imessage",
    senderId: "unknown",
    text: "I'm in",
    senderMap: {},
    memory: new Map(),
    fallbackSpeaker: "Adrian",
  });
  assert.equal("error" in resolved, true);
});

test("a .env chat id is loaded when the shell has not set one", () => {
  const dir = mkdtempSync(join(tmpdir(), "fareline-env-"));
  const path = join(dir, ".env");
  writeFileSync(path, "FARELINE_SPACE=any;+;abc\n");
  const previous = process.env.FARELINE_SPACE;
  delete process.env.FARELINE_SPACE;
  try {
    loadEnv(path);
    assert.equal(process.env.FARELINE_SPACE, "any;+;abc");
  } finally {
    if (previous === undefined) delete process.env.FARELINE_SPACE;
    else process.env.FARELINE_SPACE = previous;
  }
});

test("local iMessage answers only the named chat", () => {
  resetAnnouncedSpaces();
  const previous = process.env.FARELINE_SPACE;
  process.env.FARELINE_SPACE = "iMessage;+;chat1";
  try {
    assert.equal(acceptSpace("terminal", "tui"), true);
    assert.equal(acceptSpace("imessage", "any;-;+1555"), true);
    assert.equal(acceptSpace("local_imessage", "iMessage;+;chat1"), true);
    assert.equal(acceptSpace("local_imessage", "iMessage;+;other"), false);
  } finally {
    if (previous === undefined) delete process.env.FARELINE_SPACE;
    else process.env.FARELINE_SPACE = previous;
    resetAnnouncedSpaces();
  }
});
