---
name: longbridge
version: 1.0.0
description: |
  Longbridge / LongPort (长桥证券) — US/HK/A-share stocks. Account, positions, orders, quotes, history, and order placement.

  Use when the user wants to check or trade a Longbridge / 长桥 account (e.g. "Longbridge balance", "buy 100 700.HK on Longbridge", "my 长桥 positions"). Cloud API via the official longport SDK, runs in the container.
author: starchild
tags: [longbridge, longport, 长桥证券, broker, us-stocks, hk-stocks, trading]
metadata:
  starchild:
    emoji: "🌉"
    skillKey: longbridge
    requires:
      env:
        - LONGPORT_APP_KEY
        - LONGPORT_APP_SECRET
        - LONGPORT_ACCESS_TOKEN
    install:
      - kind: pip
        package: longport
user-invocable: true
---

## What this is

☁️ **Cloud broker** — runs **directly in the container** via the official `longport` SDK (formerly `longbridge`). Covers US, HK, and A-share markets.

Auth is **static key**: App Key + App Secret + Access Token. These use the SDK's own env var names so they're picked up automatically.

⚠️ **No paper/live discriminator exists in the API.** Paper vs live is determined *only* by which Access Token you loaded — there is no field, account prefix, or host that distinguishes them. So `--profile` here is **trust-declared** (echoed back as `paper_guard: config_declared`); it does not verify anything on the server. Live placement still requires `--confirm-live`. Treat the token you configure as authoritative for which environment you're in.

## Get your credentials

1. Open a Longbridge account, then go to the [LongPort OpenAPI console](https://open.longportapp.com) (开放平台).
2. Apply for / enable OpenAPI access. The console issues three values:
   - **App Key**
   - **App Secret**
   - **Access Token** (has an expiry — regenerate when it lapses)
3. For paper trading, generate the token while your account/environment is in the paper/模拟 mode the platform offers; for live, use the live token. (Same three field names either way.)

## Configure (.env)

Request via secure input — never paste keys in chat. These are the SDK's standard names:

| Variable | Required | Notes |
|---|---|---|
| `LONGPORT_APP_KEY` | yes | App Key |
| `LONGPORT_APP_SECRET` | yes | App Secret |
| `LONGPORT_ACCESS_TOKEN` | yes | Access Token (expires — refresh when needed) |

## Usage

`pip install longport` (first run). JSON output. Default profile `paper` (label only).

```bash
python skills/longbridge/scripts/longbridge_cli.py status
python skills/longbridge/scripts/longbridge_cli.py account
python skills/longbridge/scripts/longbridge_cli.py positions
python skills/longbridge/scripts/longbridge_cli.py orders [--executions]
python skills/longbridge/scripts/longbridge_cli.py quote --symbol 700.HK
python skills/longbridge/scripts/longbridge_cli.py history --symbol AAPL.US --period 1d --limit 90
# place: qty in shares only; market or limit
python skills/longbridge/scripts/longbridge_cli.py place --symbol 700.HK --side buy --qty 100 --type limit --limit-price 350
python skills/longbridge/scripts/longbridge_cli.py cancel --order-id <id>
# live (real money): add --confirm-live (profile is label-only)
python skills/longbridge/scripts/longbridge_cli.py --confirm-live place --symbol AAPL.US --side buy --qty 1
```

**Symbol format is mandatory:** `<ticker>.<market>` — `700.HK`, `AAPL.US`, `000001.SZ`, `600519.SH`. Periods: `1m 5m 15m 30m 1h 1d 1w 1M`.

## Gotchas

- Longbridge has **no notional path** — always `--qty` (shares).
- The Access Token **expires**; if calls start failing auth, regenerate it in the console and update `.env`.
- Because there's no server-side paper/live check, double-check *which token* you loaded before any live order — the CLI can't catch a mislabeled environment for you.
