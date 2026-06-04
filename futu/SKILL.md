---
name: futu
version: 1.0.0
description: |
  Futu / moomoo (富途/moomoo) — HK/US/A-share/SG stocks via a LOCAL OpenD gateway. Account, positions, orders, quotes, history, order placement.

  Use when the user wants to check or trade a Futu / moomoo / 富途 account (e.g. "Futu positions", "buy 100 HK.00700 on moomoo", "富途 账户资产"). Requires a running OpenD gateway — NOT a cloud key.
author: starchild
tags: [futu, moomoo, 富途, opend, broker, hk-stocks, us-stocks, trading]
metadata:
  starchild:
    emoji: "🐂"
    skillKey: futu
    install:
      - kind: pip
        package: futu-api
user-invocable: true
---

## What this is — read this first

🖥️ **Local-gateway broker.** Futu does **not** expose a public cloud API. Instead you run a gateway program called **OpenD** on a machine, log into it with your Futu account, and this CLI talks to OpenD over a local socket (default `127.0.0.1:11111`). Your Futu credentials live inside OpenD — they never reach this skill.

**⚠️ This means it will NOT work from the Starchild container by default**, because OpenD runs on *your* computer, and the container's `127.0.0.1` is the container itself (a different machine). Two ways to use it:

1. **Run locally** — run OpenD + this script on your own computer where OpenD is logged in. (simplest)
2. **Bridge the network** — run OpenD on a host the container can reach, then set `FUTU_HOST`/`FUTU_PORT` to point at it (you handle the network/firewall/security yourself — exposing OpenD beyond localhost is risky; bind it tightly).

If `status` reports the gateway is not reachable, this is why.

## Set up OpenD (one time)

1. Download **OpenD** for your OS from the [Futu OpenAPI page](https://openapi.futunn.com/futu-api-doc/en/) (富途牛牛 / moomoo → OpenAPI). It comes as a GUI app and a command-line build.
2. You need a funded/opened Futu or moomoo account with **OpenAPI permission enabled** (apply in-app if needed).
3. Launch OpenD and log in with your Futu credentials (+ phone/2FA). Confirm the **API port** it listens on (default `11111`).
4. Keep OpenD running while you use this skill. For paper trading, make sure your account has a **模拟 / paper (SIMULATE)** sub-account.

## Configure (.env)

No secret keys here — only gateway location + (for live) the trade-password MD5. Request via secure input.

| Variable | Required | Notes |
|---|---|---|
| `FUTU_HOST` | no | OpenD host, default `127.0.0.1` |
| `FUTU_PORT` | no | OpenD port, default `11111` |
| `FUTU_TRD_MARKET` | no | trade market filter: `HK` (default) / `US` / `CN` / `SG` |
| `FUTU_SECURITY_FIRM` | no | `FUTUSECURITIES` (default), `FUTUINC`, `FUTUSG` |
| `FUTU_ACC_ID` | no | pin a specific account id; `0` = auto-resolve by environment |
| `FUTU_TRADE_PWD_MD5` | live only | MD5 of your Futu trade password (needed to unlock live orders) |

Paper vs live is resolved from each account's `trd_env` (`SIMULATE` = paper, `REAL` = live); `--profile` picks which one and the CLI fails closed if it can't find a matching account.

## Usage

`pip install futu-api` (first run). JSON output. Default profile `paper`.

```bash
python skills/futu/scripts/futu_cli.py status                 # checks OpenD reachability + resolves account
python skills/futu/scripts/futu_cli.py account
python skills/futu/scripts/futu_cli.py positions
python skills/futu/scripts/futu_cli.py orders [--executions]
python skills/futu/scripts/futu_cli.py quote --symbol HK.00700
python skills/futu/scripts/futu_cli.py history --symbol US.AAPL --period 1d --limit 90
# place (paper SIMULATE): qty in whole shares; market or limit
python skills/futu/scripts/futu_cli.py place --symbol HK.00700 --side buy --qty 100 --type limit --limit-price 350
python skills/futu/scripts/futu_cli.py cancel --order-id <id>
# live (REAL): needs FUTU_TRADE_PWD_MD5 in .env AND --confirm-live
python skills/futu/scripts/futu_cli.py --profile live --confirm-live place --symbol HK.00700 --side buy --qty 100
```

**Symbol format is mandatory:** `<MARKET>.<code>` — `HK.00700`, `US.AAPL`, `SH.600519`, `SZ.000001`. Periods: `1m 5m 15m 30m 1h 1d 1w 1M`.

## Gotchas

- "OpenD gateway not reachable" = OpenD isn't running, not logged in, on a different machine, or a wrong host/port. Re-read the "What this is" section.
- Futu requires **whole-share `--qty`**; no notional orders.
- Live orders need `FUTU_TRADE_PWD_MD5` (the MD5 hash of your trade password, not the password itself). The CLI unlocks the trade context only for live; paper is never unlocked.
- HK/A-share board lots apply — odd-lot quantities may be rejected by the exchange.
