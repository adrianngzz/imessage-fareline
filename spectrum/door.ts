/**
 * Terminal, plus optional Spectrum Cloud iMessage.
 * Cloud shared-pool lines are one-on-one. Group chats use spectrum/mac-app.ts.
 * Stable: https://photon.codes/docs/spectrum-ts/getting-started
 *         https://photon.codes/docs/spectrum-ts/providers/imessage
 */
import { Spectrum } from "spectrum-ts";
import { terminal } from "spectrum-ts/providers/terminal";

import { loadEnv } from "./env.ts";
import { runMessages } from "./run.ts";

loadEnv();

const providers = [terminal.config()];
if (process.env.SPECTRUM_IMESSAGE === "1") {
  const { imessage } = await import("spectrum-ts/providers/imessage");
  providers.push(imessage.config());
  console.log("Cloud iMessage is on. Shared-pool lines deliver DMs. Groups use npm run imessage.");
}

const projectId = process.env.SPECTRUM_PROJECT_ID;
const projectSecret = process.env.SPECTRUM_PROJECT_SECRET;

const app = await Spectrum({
  ...(projectId && projectSecret ? { projectId, projectSecret } : {}),
  providers,
});

console.log("Terminal: type `Adrian: I paid $48, Tessa and John rode.`");
await runMessages(app);
