---
name: bybit-account
version: 2.0.1
description: |
  Read-only Bybit tracking: UTA balance, derivatives positions, orders, fills, PnL.

  Use when monitoring Bybit without trading (e.g. account equity, open perp positions, today's fills, deposit history, risk level).
author: starchild
tags: [bybit, account, readonly, tracking, futures, spot, unified]
metadata:
  starchild:
    emoji: "🅱️"
    skillKey: bybit-account
    requires:
      env:
        - BYBIT_RO_API_KEY
        - BYBIT_RO_SECRET
    install:
      - kind: pip
        package: pybit
      - kind: pip
        package: python-dotenv
user-invocable: true

---

# Bybit Account (Read-Only)

Read-only Bybit account tracker built on the official `pybit` library.
Use it for account tracking, daily/weekly reports, risk alerts, and cashflow attribution.

## How to Get a Bybit API Key (Read-Only)

1. Sign in at [bybit.com](https://www.bybit.com), top-right avatar → **API**
   - Direct link: https://www.bybit.com/app/user/api-management
2. **Create New Key** → **System-generated API Keys**
3. Fill the form:
   - **API key usage**: **API Transaction**
   - **Name**: anything
   - **Permissions**: under **Read-Only** tick `Wallet`, `Positions`, `Trade (read only)`. Do not enable Withdraw or any write permission
   - **IP whitelist**: leave empty
4. Complete 2FA → submit
5. **Copy** `API Key` + `Secret Key` immediately (Secret is shown only once)
6. Set them into this skill's environment variables

Reference: [Bybit official tutorial](https://www.bybit.com/en/help-center/article/How-to-create-your-API-key)

## Prerequisites

### 1) API key
In Bybit API Management create a key with **Read only**.

### 2) Environment variables
```
BYBIT_RO_API_KEY=...
BYBIT_RO_SECRET=...
```

### 3) Geo restriction (required)
Bybit geo-blocks server IPs. Scripts default to the SC internal HK proxy:
```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```
Injection style: `session.client.proxies.update({'http': HK, 'https': HK})`.
**Do not** pass `HTTP(proxies=...)` — pybit doesn't accept that constructor argument.

## Important: FUND account is separate

Bybit v5's `get_wallet_balance` **only supports `accountType=UNIFIED`**. The Funding (FUND) account balance must be fetched via `get_coins_balance(accountType='FUND')`. The `summary` and `portfolio_snapshot` actions automatically query both and merge.

For positions, `linear` requires per-`settleCoin` queries (USDT / USDC) and `inverse` uses BTC. The `summary` and `perp_risk` actions automatically scan all three settlement coins.

## Scripts

```bash
python3 skills/bybit-account/scripts/bybit_account.py <action> [options]
python3 skills/bybit-account/scripts/account_scenarios.py <scenario> [options]
```

## Actions

- `summary`: one-shot summary (UNIFIED + FUND + multi-settle positions)
- `wallet_balance` / `coin_balance` / `funding_balance` / `account_info` / `fee_rates` / `collateral_info`
- `positions` / `open_orders` / `order_history` / `executions`
- `deposits` / `withdrawals` / `internal_transfers` / `universal_transfers`
- `transaction_log` / `borrow_history` / `server_time`

## Scenarios

- `portfolio_snapshot`: full account snapshot (wallet + positions)
- `perp_risk`: derivatives risk monitoring (IM / MM ratio + unrealized loss)
- `cashflow`: deposits + withdrawals + transfers + transaction log
- `trading_activity`: recent fills activity by category

## Common usage

```bash
python3 skills/bybit-account/scripts/bybit_account.py summary
python3 skills/bybit-account/scripts/account_scenarios.py portfolio_snapshot
python3 skills/bybit-account/scripts/account_scenarios.py perp_risk --loss-threshold 5000
python3 skills/bybit-account/scripts/account_scenarios.py cashflow --limit 100
python3 skills/bybit-account/scripts/account_scenarios.py trading_activity --categories spot,linear
```

## Important parameters

- `--account-type`: `UNIFIED` (default) / `CONTRACT` / `SPOT` / `FUND` / `INVESTMENT` / `OPTION`
- `--category`: `spot` / `linear` / `inverse` / `option`
- `--settle`: settle coin for `linear` / `inverse` positions (default `USDT`)

## Notes

- pybit's `HTTP` constructor does not accept `proxies`; you must inject via `client.proxies` after construction.
- `linear` positions require either `settleCoin` or `symbol`.
- Use time-windowed pagination for high-volume fills.
