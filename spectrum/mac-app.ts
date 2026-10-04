/**
 * Group-chat door. Uses this Mac's Messages account through Stable
 * @spectrum-ts/imessage-local. Does not import the cloud iMessage package.
 * Docs: https://photon.codes/docs/spectrum-ts/providers/imessage
 *
 * Needs Messages signed in and Full Disk Access for ~/Library/Messages/chat.db.
 * Set FARELINE_SPACE to the chat id printed on the first inbound message.
 */
import { Spectrum } from "spectrum-ts";
import { localIMessage } from "@spectrum-ts/imessage-local";

import { loadEnv } from "./env.ts";
import { runMessages } from "./run.ts";

loadEnv();

const app = await Spectrum({
  providers: [localIMessage.config()],
});

if (!process.env.FARELINE_SPACE?.trim()) {
  console.log(
    "Watching local Messages. Fareline will not reply until FARELINE_SPACE is the chat id printed below.",
  );
} else {
  console.log(`Replying only in FARELINE_SPACE=${process.env.FARELINE_SPACE}`);
}

await runMessages(app);
