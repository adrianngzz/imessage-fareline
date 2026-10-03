# Golden transcript

Fixed names: Riley, Alex, Sam, Jordan.
Fixed fare: $48.00. Fixed payback: $16.00.
Use this in ledger tests, Spectrum terminal, iMessage, and ASI:One.

## RSVP

```
Riley: I'm in
Alex: I'm in
Sam: I'm in
Jordan: I'm out
```

Roster must be in: Riley, Alex, Sam. Out: Jordan.

## Fare

```
Riley: I paid $48, Alex and Sam rode.
```

Even split among Riley, Alex, Sam: $16.00 each.
Alex owes Riley $16.00.
Sam owes Riley $16.00.
Jordan unchanged at $0.00.

Running net:

- Riley +$32.00
- Alex −$16.00
- Sam −$16.00
- Jordan $0.00

## Payback

```
Alex: I just paid Riley $16.
```

Alex is settled with Riley.
Sam still owes Riley $16.00.

Running net:

- Riley +$16.00
- Alex $0.00
- Sam −$16.00
- Jordan $0.00

## Balance check

```
Alex: What do I owe?
```

Alex is settled. Sam owes Riley $16.00.

Photon demo minimum if time is tight: fare → payback → balance. Keep RSVP in the Fetch.ai chat.
