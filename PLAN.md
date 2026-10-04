# Fareline — MHacks 2026 weekend plan

Working name: **Fareline**. One intern group chat. One running tab for shared Ubers and Lyfts. The agent lives in the thread. It never books the car.

**Deadline:** Sunday, Oct 4, 2026, noon ET.
**Now:** Saturday evening. You have one night and Sunday morning. Treat that as about 18 hours, not a full weekend.

Photon is the product. Fetch.ai is the same agent on a second door, not a second product. If you split into “the iMessage app” and “the Fetch chatbot,” you will lose both tracks.

---

## 0. Lock these in the next 15 minutes

Do this before anyone opens a code editor.

1. **Theme: FinTech.** You are tracking who paid, who rode, and who settled. That is a ledger. Sustainability (fewer solo Ubers) is a one-line story, not the prize pitch. Actually Intelligent is true of the NL parsing, but FinTech is what judges can score in 90 seconds.
2. **One product, two doors.** The product is the group-chat commute tab. Door 1 is iMessage via Photon Spectrum. Door 2 is ASI:One via Agentverse. Same ledger. Same four intents. Same confirmation text.
3. **Demo is one thread, three beats.** Fare → payback → “what do I owe?” If those three work, you have a prize-shaped demo. Everything else is optional.
4. **Do not build:** booking, maps, Uber/Lyft APIs, Venmo/Zelle payouts, auth, a database product, a web dashboard, a second agent personality, or a multi-agent marketplace. Those burn the night.
5. **Create accounts now, in parallel, while someone else writes the roster names.** You will need them before code matters:
  - [photon.codes](https://photon.codes) project (`SPECTRUM_PROJECT_ID` / `SPECTRUM_PROJECT_SECRET`)
  - [agentverse.ai](https://agentverse.ai) + API key
  - [asi1.ai](https://asi1.ai) (chat + developer key if you run the agent off-platform)
  - MHacks Devpost
  - A **public** GitHub repo (this workspace is a new project until you click Create repo)

Demo names: **Adrian, Tessa, John**. Adrian is the Apple ID signed into Messages on this Mac. Spectrum replies from that account; it is not a fourth person on the tab.

---



## 1. What you are actually building

The real story: four interns shared multi-stop Lyft/Ubers, ending at the office (ending at each home on the way back, after work). Whoever saw the cheapest quote ordered. Riders changed day to day. The fare was split evenly among that day’s riders. The issue was, there was a lot of labor involved in checking prices on Uber vs Lyft, and each person had different quotes; also, because different people attended work that day, the total had to be divided amongst the right people, and nobody could remember the running net. -- The running net balance is the challenge we're trying to overcome with our AI agent today. 

Fareline sits in the group chat and does four things in natural language:


| Someone says                                          | Agent does                                                                                                   |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| “I’m in” / “I’m out”                                  | Updates today’s rider roster                                                                                 |
| “I paid $48, Tessa and John rode.” / "The total is $48" | Splits evenly, remembers who paid, either based on the message, or the chat history of today's rider roster. |
| “I just paid Adrian $16.”                               | Moves that amount off the balance                                                                            |
| “What do I owe?”                                      | Answers from the running net                                                                                 |


After every fare or payback it repeats **who, how much, and the new net** so the group can correct it.

That last sentence is the product. The confirmation is the UI. If the group can see a wrong split and fix it in chat, you do not need a dashboard.

---

## 2. How to build this AI agent

An agent is not “an LLM in a loop.” For this hackathon it is four layers. Build them in this order. Do not skip ahead.

```
message  →  intent  →  tool  →  confirmation
  (chat)     (LLM)    (ledger)     (chat + card)
```



### Layer 1 — The ledger (not AI)

This is the product. Pure functions. No network. No Spectrum. No Fetch.

State you need:

- **People:** edsger fran gabriel herb (stable aliases; later map iMessage sender IDs onto these names)
- **Today’s roster:** who is in / out for the next ride
- **Ledger entries:** append-only list of `fare` and `payback` events
- **Nets:** derived, never stored as the source of truth

Rules that match the intern story:

- A fare is `amount / number_of_riders`, even split, including the payer.
- The payer is owed their share from each other rider. If edsger pays $48 and edsger, gabriel, and herb rode, each share is $16. fran owes edsger $16. gabriel owes edsger $16. edsger's net goes +$32.
- The person who books (Edsger) will always be a rider.
- A payback is “A paid B $X.” Subtract X from what A owes B. Nets are pairwise and should also collapse to a per-person running total.
- “What do I owe?” answers in the speaker’s voice from current nets, plus the shortest settlement list (who should pay whom).
- Persist to a JSON file or SQLite. If the process restarts, the nets must be the same. That is how you prove a **real balance update**, not a chat hallucination.

Write tests for these four cases before any model call:

1. Adrian pays $48; Adrian, Tessa, John rode → Tessa −16, John −16, Adrian +32
2. Tessa pays Adrian $16 → Tessa 0 vs Adrian, John still −16
3. John is out, then a fare that does not include John → John’s net unchanged
4. “What do I owe?” as Tessa after (1) and before (2) → “You owe Adrian $16”

### Layer 2 — Intents (this is the “AI”)

The model’s only job is to turn messy chat into one of these structured calls:

```
{ action: "rsvp",          person, in: true|false, date?: "today" }
{ action: "record_fare",   payer, amount_cents, riders: string[] }
{ action: "record_payback", from, to, amount_cents }
{ action: "get_balance",   person }
{ action: "undo" }          // optional, one-level, for "wait that's wrong"
{ action: "clarify",       question }
```

That is the whole tool surface. Use whatever LLM you already have access to (OpenAI, Anthropic, ASI:One). Keep the system prompt short: intern commute tab, even splits, never invent a payment, ask one clarifying question if payer/riders/amount are missing.

Do **not** let the model compute the math. It extracts names and dollars. The ledger computes cents.

Use integer cents everywhere (`4800`, not `48.0`). Display dollars.

### Layer 3 — Confirmation (the group’s trust loop)

After every fare or payback, the reply must look like this, every time:

```
Got it — Adrian paid $48.00. Riders: Adrian, Tessa, John.
Even split: $16.00 each.
Tessa owes Adrian $16.00
John owes Adrian $16.00

Running net:
  Adrian +$32.00
  Tessa  −$16.00
  John   −$16.00
```

Same shape after a payback. Same shape on “what do I owe?” (just skip the event recap and answer the person). The group can then say “wait, John rode too” and you undo or record a correction. Judges will see this as intelligent because it is inspectable.

### Layer 4 — Doors (adapters only)

Spectrum and Fetch.ai do not own state. They parse a message, call the same `handle(text, speaker)` function, and send back the confirmation.

```
                    ┌─────────────────────┐
                    │  ledger + intents   │
                    │  handle(text, who)  │
                    └──────────┬──────────┘
               ┌───────────────┴───────────────┐
               │                               │
     ┌─────────▼────────┐           ┌──────────▼──────────┐
     │ Photon Spectrum  │           │ Fetch.ai uAgent     │
     │ terminal → iMsg  │           │ ACP → Agentverse    │
     └──────────────────┘           │      → ASI:One      │
                                    └─────────────────────┘
```

**Language split that fits both tracks:**

- **TypeScript brain** (ledger, intents, confirmation). Photon Spectrum is TypeScript. Build the product here.
- **Thin Python uAgent** that implements Agent Chat Protocol and HTTP-calls the TypeScript brain. Fetch.ai judges see a real registered agent. You do not rewrite the ledger in Python.

Alternative if you are faster in Python: put the brain in Python and have a 40-line Spectrum process POST to it. Either way, **one brain**.

Host the brain as a tiny local HTTP server (`POST /act` with `{ speaker, text }`, `GET /nets` for the demo proof). The Python agent and Spectrum both call it.

---



## 3. How to use Cursor to build it

Cursor is the implementation teammate. You stay the architect. The plan above is the spec you paste into the first agent chat.

### Set Cursor up once (30 minutes, Saturday evening)

1. Put this repo in Cursor. Add a short `AGENTS.md` later that restates: one ledger, four intents, confirmation format, no booking.
2. Add **Photon docs** as a skill / MCP. Stable Spectrum docs live at [photon.codes/docs](https://photon.codes/docs). The skill index is [photon.codes/docs/skill.md](https://photon.codes/docs/skill.md). When you ask Cursor to write Spectrum code, tell it **Stable**, not Beta. The packages and env vars differ.
3. Add **Agentverse MCP** so Cursor can look up registration instead of guessing:
  - SSE: `https://mcp.agentverse.ai/sse`
  - Lite: `https://mcp-lite.agentverse.ai/mcp`
4. Open a second Cursor chat titled **ledger-only**. A third later titled **spectrum-terminal**. A fourth titled **fetch-acp**. Do not let one monster chat do all three. Context rot is how you get a second product by accident.
5. Keep a file called `GOLDEN_TRANSCRIPT.md` with the exact four demo lines. Every chat must treat that file as the acceptance test.



### The Cursor loop that works at a hackathon

**Chat 1 — ledger-only**

> Implement only `src/ledger.ts` and tests. No HTTP, no LLM, no Spectrum. These four cases must pass: [paste the test cases]. Integer cents. Append-only events. Nets are derived.

Do not accept code until you run the tests yourself.

**Chat 2 — intents**

> Add `src/intents.ts`. The model may only emit the six actions in PLAN.md. It must not compute splits. If amount, payer, or riders are missing, return `clarify`. Use the golden transcript as fixtures. Stub the model so tests do not need a live key.

**Chat 3 — local door**

> Add a `POST /act` server and a Spectrum **terminal** provider that calls `handle()`. No iMessage. No project credentials. I will type the golden transcript in the TUI.

**Chat 4 — Fetch door**

> Add a Python uAgent that implements Agent Chat Protocol from the Fetch hackpack. On `TextContent`, POST to `/act`. Reply with the confirmation text. After fare/payback, also attach an ASI:One **review** or **detail** card of the new nets. Persist so a second “what do I owe?” reads the file, not the last sentence.

**Chat 5 — iMessage, last**

> Add `imessage.config()` next to the existing terminal provider. Same `app.messages` loop. Read `SPECTRUM_PROJECT_ID` and `SPECTRUM_PROJECT_SECRET` from env. Do not fork the handler.



### Prompts that keep Cursor honest

- “Do not add a feature that is not in `GOLDEN_TRANSCRIPT.md`.”
- “Show me the confirmation string for case 1 before writing Spectrum code.”
- “The Fetch agent must call `/act`. If you duplicate the split math in Python, stop.”
- “Spectrum terminal first. iMessage is a provider line, not a rewrite.”



### What to do yourself, not in Cursor

- Account dashboards, API keys, ngrok/tunnel URLs
- Agentverse keywords and README badges
- The iMessage group with three teammates’ phones
- The two demo videos
- Devpost + ASI:One Submission Agent
- Saying no when Cursor offers a React dashboard



### Cursor as the judge rehearsal

Near the end, start a fresh chat, paste `PLAN.md` + the README you will submit, and ask: “You are a Photon judge with 90 seconds. What is broken or unclear?” Then a second: “You are a Fetch.ai judge. Is this a chatbot wrapper or a tool-using agent? What would you need to see in ASI:One?” Fix those two answers, not new features.

---



## 4. When to think about Photon Spectrum

Spectrum is not one switch. It is three rungs. Climb them in order.

### Rung 1 — Tonight: Spectrum as a local harness, not iMessage

Photon’s SDK (`spectrum-ts`) has a **terminal provider** that needs no credentials and no phone line. You write the same `for await (const [space, message] of app.messages)` loop you will use on iMessage.

```ts
import { Spectrum } from "spectrum-ts";
import { terminal } from "spectrum-ts/providers/terminal";

const app = await Spectrum({
  providers: [terminal.config()],
});
```

**This is the moment you start using Spectrum.** Not when the iMessage line is live. The terminal TUI is a real Spectrum space. Typing indicators, replies, and the message stream are the same API. If the golden transcript works here, iMessage is a provider swap.

Do this as soon as the ledger tests pass. Saturday night. Do not wait for Photon booth credentials to “start Spectrum.”

Docs: [Getting started](https://photon.codes/docs/spectrum-ts/getting-started), [Terminal](https://photon.codes/docs/spectrum-ts/providers/terminal).

### Rung 2 — After Fetch is discoverable: add the cloud iMessage provider

Only then:

```ts
import { imessage } from "spectrum-ts/providers/imessage";

const app = await Spectrum({
  projectId: process.env.SPECTRUM_PROJECT_ID!,
  projectSecret: process.env.SPECTRUM_PROJECT_SECRET!,
  providers: [
    terminal.config(),
    imessage.config(),
  ],
});
```

Same loop. `message.platform` tells you where it came from.

**Why wait:** cloud iMessage needs a Photon project, a managed line, and a group thread. Those are booth-and-dashboard problems. They do not help you finish the ledger. They will eat two hours if you start them first. Fetch.ai registration also needs a public HTTPS endpoint and an ASI:One chat you can share. That is the riskier prize checklist, so finish it before you chase a pretty iMessage screenshot.

Photon demo requirement from you: **one thread, a fare, a payback, a balance check.** That is 90 seconds of iMessage once the line works. Budget **Sunday 8:00–10:00 AM** for it, not Saturday night.

### Rung 3 — Fallback only: local Mac Messages

If Spectrum Cloud lines are delayed or you cannot get a dedicated group:

- `@spectrum-ts/imessage-local` reads this Mac’s Messages database
- Needs macOS, Messages signed in, Full Disk Access to `~/Library/Messages/chat.db`
- No project credentials
- Weaker group features (no typing, reactions, group create)

Use this only if Rung 2 fails and you still need an iMessage video. Keep it in a separate entry file (`mac-app.ts`) so you do not drag native SQLite into a cloud deploy. Docs: [iMessage provider](https://photon.codes/docs/spectrum-ts/providers/imessage).

### Do not do these with Spectrum

- Do not start by pairing a phone.
- Do not build a custom iMessage App card unless the text confirmation already works.
- Do not use `@spectrum-ts/imessage-local` as the main architecture.
- Do not create a second handler “for iMessage tone.”
- Do not wait on Spectrum to start the Fetch agent. They share a brain, not a process.



### Photon judge picture

A group thread named something like “Intern commute.” The Fareline line is in the chat. You type the three beats. The agent replies in the confirmation format. That is the whole Photon demo. Terminal footage is a backup if iMessage flakes on camera.

---



## 5. Fetch.ai is the same agent, with proof the ledger moved

[MHacks 2026 Fetch hackpack](https://www.fetch.ai/events/hackathons/mhacks-2026/hackpack)

Judges are not scoring a nicer chatbot. The challenge text: understand intent **and take meaningful action**. Mandatory:


| Must have                        | What you do                                                                               |
| -------------------------------- | ----------------------------------------------------------------------------------------- |
| Registered on Agentverse         | Launch / Connect Agent, Chat Protocol, public HTTPS endpoint, evaluate registration       |
| Agent Chat Protocol (ACP)        | `Protocol(spec=chat_protocol_spec)`, ack every `ChatMessage`, `publish_manifest=True`     |
| Discoverable in ASI:One          | Keywords + README that say intern commute splits, ride tab, “I paid $48”, “what do I owe” |
| Tool execution, not chat         | `/act` mutates the JSON/SQLite ledger                                                     |
| Whole workflow inside ASI:One    | Fare, payback, balance. No custom frontend                                                |
| Public GitHub + run instructions | Agent name, address, how to talk to it                                                    |
| Innovation Lab category          | Badges below in the README                                                                |


Badges (required wording from the hackpack):

```markdown
![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)
```



### What “a real balance update” means

A chat reply that *says* “Alex owes Riley $16” is not enough. You need a judge to believe the world changed.

Do all four, in the ASI:One video:

1. Before: ask “what does Alex owe?” → $0 (or empty tab).
2. Action: “Riley paid $48, Alex and Sam rode.”
3. Visible mutation: an ASI:One **review** or **detail** card listing the new nets (not only the text bubble). Cards: [ASI:One Interactive Cards](https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards). Preview payloads in the [card playground](https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-card-playground) before you wire them.
4. After: a **new** message, “what do I owe?” as Alex → $16, read from persisted state. If you restart the agent between 3 and 4 and it still answers $16, say that out loud in the video.

`GET /nets` in a browser or a second ASI:One turn is the proof. A hallucinated sentence is not.

### Hosted vs local agent

- **Fastest:** Agentverse hosted agent (platform injects `ASI1_API_KEY` / `ASI1_BASE_URL`). Use this only if you are willing to keep a small Python brain in sync, or if the hosted agent HTTP-calls your laptop via a tunnel.
- **Cleaner for one brain:** local uAgent + Cloudflare Tunnel / ngrok HTTPS → Agentverse “Connect Agent” → Chat Protocol → Evaluate Registration. Keep the tunnel up through judging.

Identity rule: the seed that created the running agent is the seed you register. Do not generate a new identity between run and evaluate.

### Discovery keywords to paste into Agentverse

`ride split`, `uber split`, `lyft split`, `intern commute`, `group chat tab`, `who owes whom`, `I paid`, `I'm in`, `what do I owe`, `payback`, `settlement`

README should include example utterances and the agent address.

### Skip unless you are done early

- Payment Protocol / FET monetization (bonus, not required)
- Multi-agent orchestration (one agent with tools is enough; “meaningful action” is the ledger write)
- Custom card trees (predefined `review` / `detail` is enough)



### Submit twice

Devpost alone is not enough.

1. Devpost project (code, video, theme FinTech).
2. In ASI:One, message **MHacks Submission Agent**. Lead creates the team; everyone else joins with the Team ID. Status is not done until it says **Submitted**.

Have these URLs before you open the Submission Agent ([official steps](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0)):

- Public GitHub URL
- Agentverse profile URL(s): `https://agentverse.ai/agents/details/agent1q.../profile`
- ASI:One shared chat URL: sidebar search → **Current chat → Share chat** → `https://asi1.ai/shared-chat/...`
- Demo video URL (optional in the form, required by the hackpack as a 3–5 min video — record it anyway)

---



## 6. Clock: what you should be doing

Times in ET. Slide them if you started later; do not slide the order.

### Saturday 6:00–7:00 PM — paper and accounts

- Lock theme, names, golden transcript.
- Create Photon, Agentverse, ASI:One, Devpost, public GitHub.
- One person writes `GOLDEN_TRANSCRIPT.md` by hand. Another installs Node/Bun + Python + `uagents`.
- Cursor: Photon skill + Agentverse MCP.



### Saturday 7:00–9:30 PM — ledger and tests

- Cursor chat 1 only.
- Ledger + four tests green.
- JSON persist + `GET /nets`.
- No Spectrum iMessage. No Agentverse yet.

**Gate:** you can run a 10-line script that prints the confirmation for the golden fare.

### Saturday 9:30–11:00 PM — intents + Spectrum terminal

- Cursor chats 2 and 3.
- Live or stubbed LLM. Golden transcript works in the Spectrum TUI.
- Record a 20-second screen grab of the TUI. That is your Photon backup footage.

**Gate:** you have used Spectrum. You have not touched iMessage.

### Saturday 11:00 PM–1:30 AM — Fetch door

- `POST /act` is stable.
- Python uAgent + ACP from the hackpack sample.
- Tunnel up. Register on Agentverse. Evaluate. Confirm it appears in ASI:One (Agents toggle on).
- Wire a review/detail card of nets after fare and payback.

**Gate:** from ASI:One you can record a fare and then ask a balance question in a new turn and get the mutated net.

### Saturday 1:30–2:00 AM — stop

Sleep. A broken iMessage line at 4 AM will not ship. The gates above are the prize-eligible product.

### Sunday 8:00–10:00 AM — Photon iMessage

- Add `imessage.config()`.
- Get the Fareline line into one group with three phones (or two phones and a simulator).
- Run the three beats. Record the screen, Apple Messages, not a slide.
- If Cloud fails by 9:00, switch to `imessage-local` or submit the terminal footage plus an honest “same Spectrum loop” caption.



### Sunday 10:00–11:15 AM — videos and README

Two short videos, or one 4-minute video with two chapters:

1. **Photon (90 sec):** group thread, fare, payback, “what do I owe?”
2. **Fetch (90 sec):** discover the agent in ASI:One, same three beats, card shows nets, second turn proves persistence. Say the agent address out loud.

README must include: what it is, how to run locally, agent name + address, both badges, env vars, “does not book rides,” theme FinTech.

### Sunday 11:15–11:50 AM — submit

- Push to public GitHub.
- Devpost.
- ASI:One → MHacks Submission Agent → lead creates team → teammates join → status **Submitted**.
- Paste Agentverse profile + shared-chat URLs. Do not skip those; they are how Fetch judges find you.



### Sunday 11:50–noon — do not add features

If something is broken, shorten the demo, do not extend the code.

---



## 7. Golden transcript (type this in every door)

Keep names and dollars fixed so the videos match the tests.

```
Riley: I'm in
Agent: Riley is in for today’s ride. In: Riley. Out: —

Alex: I'm in
Sam: I'm in
Jordan: I'm out
Agent: Roster — in: Riley, Alex, Sam. Out: Jordan.

Riley: I paid $48, Alex and Sam rode.
Agent: <confirmation: $16 each, Alex owes Riley $16, Sam owes Riley $16, nets>

Alex: I just paid Riley $16.
Agent: <confirmation: Alex → Riley $16, Alex net $0 vs Riley, Sam still −$16>

Alex: What do I owe?
Agent: Alex, you’re settled with Riley. You still have no other debts.
       Sam owes Riley $16.00.
```

Photon official demo can drop the RSVP lines if time is tight: fare, payback, balance. Keep RSVP in the Fetch chat to show a fourth intent.

---



## 8. Risks and the fallback for each


| Risk                           | Fallback                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------- |
| LLM flakes on names            | Keyword fallback: `/in`, `/out`, `paid`, `owes` regex so the demo never depends on the model      |
| Spectrum Cloud line not ready  | Terminal TUI video + same code path; then `imessage-local`                                        |
| Agentverse cannot reach laptop | Hosted agent that calls the same `/act` through a tunnel; keep tunnel process owned by one person |
| Tunnel dies during judging     | Restart script on the laptop; print the agent address on a sticky                                 |
| Fight about cents/rounding     | Always divide in cents, remainder to the payer so totals match the fare                           |
| Someone wants to add Venmo     | No. Say the confirmation out loud and move on                                                     |
| Two people fork the ledger     | One `handle()` owner. Adapters only                                                               |


---



## 9. How you will know you are done

You are done when all of these are true, not when the code feels clever:

- [ ] Tests for the four ledger cases pass
- [ ] Spectrum terminal plays the golden transcript
- [ ] Agent is on Agentverse, Chat Protocol enabled, findable in ASI:One
- [ ] ASI:One fare changes `GET /nets` / a follow-up balance question
- [ ] iMessage or terminal video of fare → payback → balance
- [ ] README has Innovation Lab + hackathon badges, agent name, agent address
- [ ] Devpost submitted
- [ ] MHacks Submission Agent status is **Submitted**
- [ ] Shared ASI:One chat URL and Agentverse profile URL are in that submission

---



## 10. Links

**Photon / Spectrum (Stable)**

- [Introduction](https://photon.codes/docs/spectrum-ts/introduction)
- [Getting started](https://photon.codes/docs/spectrum-ts/getting-started)
- [iMessage](https://photon.codes/docs/spectrum-ts/providers/imessage)
- [Terminal](https://photon.codes/docs/spectrum-ts/providers/terminal)
- [Docs skill for Cursor](https://photon.codes/docs/skill.md)
- [spectrum-ts](https://github.com/photon-hq/spectrum-ts)

**Fetch.ai / MHacks**

- [MHacks 2026 hackpack](https://www.fetch.ai/events/hackathons/mhacks-2026/hackpack)
- [Submission steps](https://docs.google.com/document/d/1UDW-X1C24hxZviFOQzjTeh0pXRNAoflMb8lhJqZP9Z0)
- [ASI:One-compatible uAgent](https://innovationlab.fetch.ai/resources/docs/agentverse/agentverse-sdk-uagents)
- [Enable Chat Protocol](https://docs.agentverse.ai/documentation/getting-started/enable-chat-protocol.mdx)
- [Interactive cards](https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards)
- Agentverse MCP: `https://mcp.agentverse.ai/sse` or `https://mcp-lite.agentverse.ai/mcp`

