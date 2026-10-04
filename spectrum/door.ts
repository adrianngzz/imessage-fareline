/**
 * Photon door. Stable spectrum-ts.
 * Terminal needs no credentials. iMessage is the same loop with SPECTRUM_IMESSAGE=1.
 * Docs: https://photon.codes/docs/spectrum-ts/providers/terminal
 *       https://photon.codes/docs/spectrum-ts/providers/imessage
 */
import { readFileSync } from "node:fs";

import { Spectrum } from "spectrum-ts";
import { terminal } from "spectrum-ts/providers/terminal";

const ACT_URL = process.env.FARELINE_ACT_URL ?? "http://127.0.0.1:8787/act";
const PEOPLE = ["Riley", "Alex", "Sam", "Jordan"];

function loadSenderMap(): Record<string, string> {
  if (process.env.FARELINE_SENDER_MAP) {
    return JSON.parse(process.env.FARELINE_SENDER_MAP);
  }
  try {
    return JSON.parse(readFileSync("senders.json", "utf8"));
  } catch {
    return {};
  }
}

const senderMap = loadSenderMap();

function canonical(name: string): string | undefined {
  return PEOPLE.find((person) => person.toLowerCase() === name.toLowerCase());
}

function resolveSpeaker(message: {
  sender?: { id?: string };
  content: { type: string; text?: string };
}): { speaker: string; text: string } | { error: string } {
  if (message.content.type !== "text" || !message.content.text?.trim()) {
    return { error: "" };
  }
  const text = message.content.text.trim();
  const prefixed = text.match(/^(Riley|Alex|Sam|Jordan)\s*:\s*([\s\S]+)$/i);
  if (prefixed) {
    return { speaker: canonical(prefixed[1]) ?? prefixed[1], text: prefixed[2].trim() };
  }
  const senderId = message.sender?.id ?? "";
  const mapped = senderMap[senderId];
  if (mapped && canonical(mapped)) {
    return { speaker: canonical(mapped) as string, text };
  }
  if (process.env.FARELINE_SPEAKER && canonical(process.env.FARELINE_SPEAKER)) {
    return { speaker: canonical(process.env.FARELINE_SPEAKER) as string, text };
  }
  return {
    error:
      "I don't know which intern this is. In the terminal, start the line with Riley:. On iMessage, add this sender to senders.json.",
  };
}

async function act(speaker: string, text: string): Promise<string> {
  const response = await fetch(ACT_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ speaker, text }),
  });
  if (!response.ok) {
    return "The tab rejected that message. Check that the ledger is running.";
  }
  const body = (await response.json()) as { reply?: string };
  return body.reply || "No reply.";
}

const providers = [terminal.config()];
if (process.env.SPECTRUM_IMESSAGE === "1") {
  const { imessage } = await import("spectrum-ts/providers/imessage");
  providers.push(imessage.config());
}

const projectId = process.env.SPECTRUM_PROJECT_ID;
const projectSecret = process.env.SPECTRUM_PROJECT_SECRET;

const app = await Spectrum({
  ...(projectId && projectSecret ? { projectId, projectSecret } : {}),
  providers,
});

console.log(`Fareline Spectrum door. Ledger: ${ACT_URL}`);
console.log("Terminal: type `Riley: I paid $48, Alex and Sam rode.`");

for await (const [space, message] of app.messages) {
  if (message.direction === "outbound") continue;
  if (message.content.type !== "text") continue;

  const resolved = resolveSpeaker(message);
  await space.responding(async () => {
    if ("error" in resolved) {
      if (resolved.error) await space.send(resolved.error);
      return;
    }
    try {
      await space.send(await act(resolved.speaker, resolved.text));
    } catch {
      await space.send(`The tab isn't reachable at ${ACT_URL}. Start the Python ledger first.`);
    }
  });
}
