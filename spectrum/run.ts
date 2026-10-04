/**
 * One Spectrum message loop. Terminal, cloud iMessage, and local iMessage
 * all call this. Stable docs: https://photon.codes/docs/spectrum-ts/messages
 */
import { readFileSync } from "node:fs";

import { act, ledgerUrl } from "./act.ts";
import { contactName } from "./contacts.ts";
import { loadSpeakers, saveSpeakers } from "./memory.ts";
import { resolveSpeaker } from "./speakers.ts";
import { acceptSpace } from "./spaces.ts";

export type SpectrumMessage = {
  direction: "inbound" | "outbound";
  platform: string;
  content: { type: string; text?: string };
  sender?: { id?: string };
};

export type SpectrumSpace = {
  id: string;
  responding: (fn: () => Promise<void>) => Promise<void>;
  send: (text: string) => Promise<unknown>;
};

export type SpectrumApp = {
  messages: AsyncIterable<[SpectrumSpace, SpectrumMessage]>;
};

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

export async function runMessages(app: SpectrumApp): Promise<void> {
  const senderMap = loadSenderMap();
  const memory = loadSpeakers();
  const fallback = process.env.FARELINE_SPEAKER;

  console.log(`Fareline Spectrum door. Ledger: ${ledgerUrl()}`);

  for await (const [space, message] of app.messages) {
    if (message.direction === "outbound") continue;
    if (message.content.type !== "text" || !message.content.text?.trim()) continue;
    if (!acceptSpace(message.platform, space.id)) continue;

    const senderId = message.sender?.id ?? "";
    const named =
      message.platform === "local_imessage" || message.platform === "imessage"
        ? contactName(senderId)
        : undefined;
    const resolved = resolveSpeaker({
      platform: message.platform,
      senderId,
      text: message.content.text,
      senderMap,
      memory,
      contactName: named,
      fallbackSpeaker: fallback,
    });
    saveSpeakers(memory);
    if ("ignore" in resolved) continue;

    await space.responding(async () => {
      if ("hello" in resolved) {
        await space.send(resolved.hello);
        return;
      }
      if ("error" in resolved) {
        const senderId = message.sender?.id;
        if (senderId) console.log(`Unknown sender ${senderId} in ${space.id}.`);
        await space.send(resolved.error);
        return;
      }
      try {
        await space.send(await act(resolved.speaker, resolved.text));
      } catch {
        await space.send(`The tab isn't reachable at ${ledgerUrl()}. Start the Python ledger first.`);
      }
    });
  }
}
