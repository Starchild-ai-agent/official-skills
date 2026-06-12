---
name: tiger
version: 1.0.0
description: >-
  Tiger Brokers (老虎证券) — US/HK/A-share trading (paper + live): account, positions, orders; cloud tigeropen SDK.
author: starchild
tags: [tiger, 老虎证券, tigeropen, broker, us-stocks, hk-stocks, trading]
metadata:
  starchild:
    emoji: "🐯"
    skillKey: tiger
    requires:
      env:
        - TIGER_ID
        - TIGER_PRIVATE_KEY_PATH
        - TIGER_ACCOUNT
    install:
      - kind: pip
        package: tigeropen
user-invocable: true
---

## When to use

Tiger Brokers (TigerOpen) — US/HK/A-share stocks. Account, positions, orders, quotes, history, and order placement (paper + live).

Use when the user wants to check or trade a Tiger / 老虎证券 account (e.g. "Tiger account assets", "buy 100 700.HK on Tiger", "my Tiger positions"). Cloud API via the official tigeropen SDK, runs in the container.

## What this is

☁️ **Cloud broker** — runs **directly in the container** via the official `tigeropen` SDK. Covers US, HK, and A-share markets.

Auth is **RSA-signed static key**: a `tiger_id` + a local PKCS#1 private key (PEM) + your account number. No OAuth, no token refresh.

**Paper/live guard:** a Tiger paper (sandbox) account number is exactly **17 numeric digits** (e.g. `20191106192858300`); standard/global accounts are not. The chosen `--profile` must match the account format or the command fails closed. Live placement additionally requires `--confirm-live`. Note: paper accounts don't support GTC, so it's auto-forced to DAY.

## Get your credentials

1. Open a Tiger account and apply for API access at the [Tiger Open Platform](https://www.itigerup.com/openapi) (登录 → 开发者 / API).
2. **Generate an RSA key pair** (the platform requires PKCS#1). On any machine:
   ```bash
   openssl genrsa -out tiger_private_key.pem 2048      # PKCS#1 private key
   openssl rsa -in tiger_private_key.pem -pubout -out tiger_public_key.pem
   ```
3. On the Open Platform, paste the **public key** content (between the BEGIN/END lines) to bind it. Note your **`tiger_id`** (developer id) shown there.
4. Find your **account number**: paper account from the sandbox/模拟 section (17 digits); live/standard account from your real account page.
5. Keep the **private key** safe — it never leaves your machine. Provide either its file path or paste the PEM contents via secure input.

## Configure (.env)

Request via secure input — never paste keys/PEM in chat.

| Variable | Required | Notes |
|---|---|---|
| `TIGER_ID` | yes | developer tiger_id |
| `TIGER_PRIVATE_KEY_PATH` | one of these | path to the PKCS#1 PEM file |
| `TIGER_PRIVATE_KEY` | one of these | inline PEM (use `\n` for newlines); written to `~/.tiger_private_key.pem` (0600) |
| `TIGER_PAPER_ACCOUNT` | for paper | 17-digit sandbox account (or set `TIGER_ACCOUNT`) |
| `TIGER_LIVE_ACCOUNT` | for live | real account number (or set `TIGER_ACCOUNT`) |

`TIGER_ACCOUNT` is a fallback used by whichever profile if the profile-specific var isn't set.

## Usage

`pip install tigeropen` (first run; already present in this workspace). JSON output. Default profile `paper`.

```bash
python skills/tiger/scripts/tiger_cli.py status
python skills/tiger/scripts/tiger_cli.py account
python skills/tiger/scripts/tiger_cli.py positions
python skills/tiger/scripts/tiger_cli.py orders [--executions]
python skills/tiger/scripts/tiger_cli.py quote --symbol AAPL
python skills/tiger/scripts/tiger_cli.py history --symbol AAPL --period 1d --limit 90
# place (paper): qty in units only; market or limit; --currency default USD
python skills/tiger/scripts/tiger_cli.py place --symbol AAPL --side buy --qty 1 --type market
python skills/tiger/scripts/tiger_cli.py place --symbol AAPL --side buy --qty 1 --type limit --limit-price 180 --tif day
python skills/tiger/scripts/tiger_cli.py cancel --order-id <id>
# live:
python skills/tiger/scripts/tiger_cli.py --profile live --confirm-live place --symbol AAPL --side buy --qty 1
```

Periods: `1m 5m 15m 30m 1h 1d 1w 1M` (note: `1m`=minute, `1M`=month, case-sensitive). Symbols are bare tickers (`AAPL`, `00700`) — set `--currency` (USD/HKD/...) for non-USD.

## Gotchas

- Tiger has **no notional path** for stocks — always use `--qty` (units), never `--notional`.
- `status` validates the profile/account match (17-digit guard) and pings assets. Run it first.
- If you bound the public key but get auth errors, confirm the key is **PKCS#1** (the `openssl genrsa` output), not PKCS#8.
