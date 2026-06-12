---
name: ibkr
version: 1.0.0
description: >-
  Interactive Brokers (IBKR) — global stocks/ETFs/forex/futures via LOCAL TWS or IB Gateway; NOT a cloud key.
author: starchild
tags: [ibkr, interactive-brokers, tws, ib-gateway, broker, global-stocks, forex, futures, trading]
metadata:
  starchild:
    emoji: "📉"
    skillKey: ibkr
    install:
      - kind: pip
        package: ib_async
user-invocable: true
---

## When to use

Interactive Brokers (IBKR) — global stocks/ETFs/forex/futures via a LOCAL TWS or IB Gateway. Account, positions, orders, quotes, history, order placement.

Use when the user wants to check or trade an Interactive Brokers account (e.g. "IBKR positions", "buy 10 AAPL on IBKR paper", "my IB account net liq"). Requires a running TWS / IB Gateway — NOT a cloud key.

## What this is — read this first

🖥️ **Local-gateway broker.** IBKR has **no key-based public API**. You run **Trader Workstation (TWS)** or the lighter **IB Gateway** on a machine, log in, enable the API socket, and this CLI connects over a local socket. Your IBKR credentials live in TWS — they never reach this skill.

**⚠️ This will NOT work from the Starchild container by default**, because TWS runs on *your* computer and the container's `127.0.0.1` is the container itself. Two ways to use it:

1. **Run locally** — run TWS/Gateway + this script on your own computer. (simplest)
2. **Bridge the network** — run IB Gateway on a host the container can reach, add the container's IP to TWS's "Trusted IPs", and set `IBKR_HOST`/`IBKR_PORT`. You handle network/security; never expose the API socket to the open internet.

If `status` says the socket isn't listening, this is why.

## Set up TWS / IB Gateway (one time)

1. Download **TWS** or **IB Gateway** from [interactivebrokers.com](https://www.interactivebrokers.com) → Trading → Platforms. IB Gateway is lighter and headless-friendly; TWS is the full GUI.
2. Log in. **Paper trading:** IBKR gives every account a free paper login (account id starts with `DU`); log into the paper session for testing.
3. Enable the API: **TWS → File → Global Configuration → API → Settings** → check **"Enable ActiveX and Socket Clients"**. For trading, leave **"Read-Only API" unchecked** (read-only blocks order placement). Note the **Socket port**.
4. Default ports: **7497** = TWS paper, **7496** = TWS live, **4002** = IB Gateway paper, **4001** = IB Gateway live.
5. Market data requires the relevant **data subscriptions** on the account, or quotes/bars return empty.

## Configure (.env)

No secret keys — only the gateway location. Request via secure input if non-default.

| Variable | Required | Notes |
|---|---|---|
| `IBKR_HOST` | no | default `127.0.0.1` |
| `IBKR_PORT` | no | overrides the profile default (7497 paper / 7496 live) |
| `IBKR_CLIENT_ID` | no | API client id, default `1` (use distinct ids for concurrent connections) |
| `IBKR_ACCOUNT` | no | pin a specific account code (e.g. `DU1234567`); blank = first managed account |

Paper accounts start with `DU`, live with `U`. `--profile paper` guards against accidentally hitting a live account.

## Usage

`pip install ib_async` (first run). JSON output. Default profile `paper` (port 7497).

```bash
python skills/ibkr/scripts/ibkr_cli.py status                  # checks socket + lists managed accounts
python skills/ibkr/scripts/ibkr_cli.py account
python skills/ibkr/scripts/ibkr_cli.py positions
python skills/ibkr/scripts/ibkr_cli.py orders [--executions]
python skills/ibkr/scripts/ibkr_cli.py quote --symbol AAPL
python skills/ibkr/scripts/ibkr_cli.py history --symbol AAPL --duration "30 D" --bar-size "1 day"
# place (paper): qty in units; market or limit; contract defaults STK/SMART/USD
python skills/ibkr/scripts/ibkr_cli.py place --symbol AAPL --side buy --qty 10 --type limit --limit-price 180 --tif day
python skills/ibkr/scripts/ibkr_cli.py cancel --order-id <numeric-id>
# live (real money): TWS on live port + --confirm-live
python skills/ibkr/scripts/ibkr_cli.py --profile live --confirm-live place --symbol AAPL --side buy --qty 1
```

Non-US / non-stock instruments: pass `--exchange`, `--currency`, `--sec-type` (e.g. `--sec-type CASH --symbol EUR --currency USD --exchange IDEALPRO` for forex). `history` uses IB's `--duration` ("30 D", "1 Y") and `--bar-size` ("1 day", "1 hour", "5 mins").

## Gotchas

- "socket not listening" / connection refused = TWS not running, not logged in, on another machine, wrong port, or API socket disabled. Re-read setup step 3.
- For order placement, **"Read-Only API" must be OFF** in TWS settings — otherwise placement is silently blocked even with `--confirm-live`.
- `cancel` needs the **numeric IBKR order id** and only cancels orders currently open in this session/account.
- Quotes/history return empty without the right **market-data subscription** on the account.
- Use a unique `IBKR_CLIENT_ID` if TWS complains about a client id already in use.
