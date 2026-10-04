import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const PATH = "data/imessage-speakers.json";

export function loadSpeakers(path = PATH): Map<string, string> {
  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return new Map();
    return new Map(
      Object.entries(parsed).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
    );
  } catch {
    return new Map();
  }
}

export function saveSpeakers(memory: Map<string, string>, path = PATH): void {
  mkdirSync(dirname(path), { recursive: true });
  const body: Record<string, string> = {};
  for (const [id, person] of memory) body[id] = person;
  writeFileSync(path, JSON.stringify(body, null, 2) + "\n");
}
