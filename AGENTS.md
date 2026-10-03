# RideTab — instructions for Cursor

You are implementing the plan in `PLAN.md`. Read that file before writing code.

## Product

Intern commute ride tab in a group chat. Does not book cars. Theme is FinTech.

One ledger. Two doors: Photon Spectrum and Fetch.ai (ACP / Agentverse / ASI:One). Never duplicate split math.

## Build order

1. Ledger + tests from `GOLDEN_TRANSCRIPT.md` (integer cents, append-only events, derived nets)
2. Intents that only emit structured actions; the model does not compute money
3. `POST /act` + Spectrum **terminal** provider
4. Python uAgent ACP shim that calls `/act`, plus an ASI:One review/detail card of nets
5. Spectrum `imessage.config()` last, same message loop

## Allowed actions

`rsvp`, `record_fare`, `record_payback`, `get_balance`, `undo`, `clarify`

## Confirmation

After every fare or payback: who paid, how much, riders, even split, who owes whom, full running net.

## Do not add

Booking, maps, Uber/Lyft APIs, Venmo, auth, a dashboard, a second ledger, a second agent personality, Payment Protocol unless asked.
