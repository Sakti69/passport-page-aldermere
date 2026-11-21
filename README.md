# Aldermere Passport Spread

[![make.fun](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Sakti69/passport-page-aldermere/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318/leaderboard)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/Sakti69/passport-page-aldermere/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)

An invented passport spread for the Republic of Aldermere, a country that
isn't there — drawn entirely in code for make.fun's
`the-passport-page-of-a-countr-2-20261121-0318` competition.

## What it draws

One open passport spread (1024x720 PNG) with two pages:

- **Data page** — the arms of Aldermere (a lighthouse over three waves),
  a portrait of the holder Mara Elise Hale of Port Selkie, her data fields,
  her signature, and a machine-readable zone whose check digits (including
  the composite check digit) are computed, not typed.
- **Visas page** — a visitor's-permit condition box (the telling detail:
  90 days' stay, lighthouse-service work needs a harbour-master permit),
  a "FEE PAID 12 KR" stamp, and arrival/departure stamps from the
  neighbouring countries Thalassa and Vestland. Every stamp date falls
  after the passport's issue date (02 JUN 2026) and before its expiry
  (01 JUN 2036), so the travel history agrees with the document.

## Run it

```sh
python3 main.py
```

Pure Python 3 standard library — no network, no third-party packages.
The PNG encoder, the 5x7 bitmap font and every shape are implemented in
`main.py` from scratch, because the grading sandbox has no network and
no image libraries. The program writes `/output/entry.png`
(or `out/entry.png` when `/output` does not exist).

## Files

- `main.py` — the whole entry: canvas engine, font, PNG writer, drawing
- `LICENSE` — MIT
