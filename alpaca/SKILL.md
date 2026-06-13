---
name: alpaca
version: 1.0.1
description: >-
  Alpaca brokerage — trade & monitor US stocks/ETFs (paper + live): positions, orders, quotes; cloud API.
author: starchild
tags: [alpaca, broker, us-stocks, etf, trading, paper-trading]
metadata:
  starchild:
    emoji: "🦙"
    skillKey: alpaca
    requires:
      env:
        - ALPACA_API_KEY
        - ALPACA_SECRET_KEY
    install:
      - kind: pip
        package: alpaca-py
user-invocable: true
---

## When to use

Alpaca brokerage — US stocks & ETFs. Account, positions, orders, quotes, history, and order placement (paper + live).

Use when the user wants to check or trade a US-stock account on Alpaca (e.g. "Alpaca buying power", "buy 1 AAPL on Alpaca paper", "my Alpaca positions"). Cloud API, runs directly in the container.

## What this is

☁️ **Cloud broker** — Alpaca exposes a public REST API, so this runs **directly in the Starchild container**, no local gateway needed. US equities and ETFs.

Paper and live are fully separated: **different key pairs, different hosts** (`paper-api.alpaca.markets` vs `api.alpaca.markets`). A paper key physically cannot touch the live account. Live order placement additionally requires the `--confirm-live` flag.

## Get your API keys

1. Sign up at [alpaca.markets](https://alpaca.markets) (US brokerage; paper trading is free and needs no funding).
2. **Paper keys:** log in → switch to **Paper Trading** (toggle top-left) → **Home** → "API Keys" panel → **Generate New Keys**. Copy the **Key ID** and **Secret Key** (secret shown once).
3. **Live keys (optional, real money):** switch to **Live Trading** → same API Keys panel → generate. These are a *different* pair from paper.
4. Market data: the free **IEX** feed works out of the box. **SIP** (full-market) needs a paid data subscription.

## Configure (.env)

Request via secure input — never paste keys in chat. Variables:

| Variable | Required | Notes |
|---|---|---|
| `ALPACA_API_KEY` | yes (paper) | paper Key ID |
| `ALPACA_SECRET_KEY` | yes (paper) | paper Secret |
| `ALPACA_LIVE_API_KEY` | only for live | live Key ID |
| `ALPACA_LIVE_SECRET_KEY` | only for live | live Secret |
| `ALPACA_FEED` | no | `iex` (default) or `sip` |

## Usage

`pip install alpaca-py` (first run). All commands print JSON. Default profile is `paper`.

```bash
python skills/alpaca/scripts/alpaca_cli.py status
python skills/alpaca/scripts/alpaca_cli.py account
python skills/alpaca/scripts/alpaca_cli.py positions
python skills/alpaca/scripts/alpaca_cli.py orders [--executions]
python skills/alpaca/scripts/alpaca_cli.py quote --symbol AAPL
python skills/alpaca/scripts/alpaca_cli.py history --symbol AAPL --period 1d --limit 90
# place (paper): qty OR notional, market OR limit
python skills/alpaca/scripts/alpaca_cli.py place --symbol AAPL --side buy --qty 1 --type market
python skills/alpaca/scripts/alpaca_cli.py place --symbol AAPL --side buy --notional 500 --type limit --limit-price 180
python skills/alpaca/scripts/alpaca_cli.py cancel --order-id <id>
# live: must add --profile live AND --confirm-live
python skills/alpaca/scripts/alpaca_cli.py --profile live --confirm-live place --symbol AAPL --side buy --qty 1
```

Periods: `1m 5m 15m 30m 1h 1d 1w 1M`. Alpaca supports fractional `--notional` (dollar amount) orders.

## Gotchas

- `status` is the health check — it reports SDK install state, key presence, and pings the account. Run it first.
- Free IEX data can be sparse/delayed off-hours; use `sip` only if the account has the paid feed.
- Live trading is real money. The `--confirm-live` gate is intentional; never auto-add it.
