# Fareline

Intern commute tab for a group chat. Someone says who rode and who paid. The ledger splits the fare in cents and answers who owes whom. It does not book the car.

Theme: **FinTech**. One ledger, two doors: iMessage through Photon Spectrum, and ASI:One through a Fetch.ai uAgent. The doors do not split money.

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Agent name: **fareline**.  
Agent address: `agent1qt4svle0njg43593l69cp0xt3366d9d6r99wpkfj2sl0mjf02uj9unaplud`  
Agentverse profile: https://agentverse.ai/agents/details/agent1qt4svle0njg43593l69cp0xt3366d9d6r99wpkfj2sl0mjf02uj9unaplud/profile  
ASI:One shared chat: https://asi1.ai/shared-chat/df7ebce6-f2e8-40bc-9225-60b8ef04bf9a

Keep `data/agent.seed` (or `AGENT_SEED`) the same after you register on Agentverse. Do not generate a new identity.

Fixed demo names: Riley, Alex, Sam, Jordan. Fare $48.00, payback $16.00. See [GOLDEN_TRANSCRIPT.md](./GOLDEN_TRANSCRIPT.md).

## Run the ledger

Python 3.11 or newer. This Mac’s `python3` may be 3.9 from Xcode; use `python3.13` if `python3 --version` says 3.9.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
python -m fareline.golden
python -m fareline
```

The server listens on `http://127.0.0.1:8787`.

- `POST /act` with `{"speaker":"Riley","text":"I paid $48, Alex and Sam rode."}`
- `GET /nets` shows the cents after a restart

Phrases from the golden transcript work with no model key. For messier lines, put `ASI_ONE_API_KEY=...` in a `.env` file in this directory and restart the ledger. The model only emits an action. The ledger computes the split.

## Env

| Variable | Used by | Purpose |
| --- | --- | --- |
| `FARELINE_LEDGER_PATH` | ledger | JSON file. Default `data/ledger.json` |
| `FARELINE_PORT` | ledger | Default `8787` |
| `FARELINE_ACT_URL` | uAgent and Spectrum | Default `http://127.0.0.1:8787/act` |
| `ASI_ONE_API_KEY` | ledger | Optional. Read from `.env`. Uses `https://api.asi1.ai/v1` and model `asi1` |
| `FARELINE_LLM_API_KEY` | ledger | Optional override of the key above |
| `FARELINE_LLM_BASE_URL` | ledger | Optional. Default is ASI:One when `ASI_ONE_API_KEY` is set, otherwise OpenAI |
| `FARELINE_LLM_MODEL` | ledger | Optional. Default `asi1` for ASI:One |
| `AGENT_SEED` | uAgent | Optional. Otherwise the first run writes `data/agent.seed` and reuses it |
| `AGENT_PORT` | uAgent | Default `8001` |
| `AGENT_ENDPOINT` | uAgent | Public `https://…/submit` URL when you tunnel |
| `AGENT_MAILBOX` | uAgent | Set to `1` to use an Agentverse mailbox instead of a tunnel |
| `SPECTRUM_PROJECT_ID` | Spectrum | iMessage only |
| `SPECTRUM_PROJECT_SECRET` | Spectrum | iMessage only |
| `SPECTRUM_IMESSAGE` | Spectrum | Set to `1` to add the iMessage provider |
| `FARELINE_SENDER_MAP` | Spectrum | JSON map of sender id to intern name. Or copy `senders.example.json` to `senders.json` |

## ASI:One / Agentverse door

Start the ledger first. Then:

```bash
AGENT_MAILBOX=1 python agent.py
```

Keep both processes running. In ASI:One, turn **Agents** on and prefix every line with who is speaking:

```
Riley: What do I owe?
Riley: I paid $48, Alex and Sam rode.
Alex: I just paid Riley $16.
Alex: What do I owe?
```

Discovery keywords for the Agentverse profile: `ride split`, `uber split`, `lyft split`, `intern commute`, `group chat tab`, `who owes whom`, `I paid`, `I'm in`, `what do I owe`, `payback`, `settlement`.

## Spectrum door

Start the ledger first. Then:

```bash
bun add spectrum-ts
bun run terminal
```

iMessage, after the terminal transcript works:

```bash
SPECTRUM_IMESSAGE=1 bun spectrum/door.ts
```

Photon and Agentverse setup is in [PLAN.md](./PLAN.md).
