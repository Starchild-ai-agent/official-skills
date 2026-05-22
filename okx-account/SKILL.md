---
name: okx-account
version: 2.0.1
description: |
  Read-only OKX tracking: unified-account equity, perp positions, orders, fills, bills.

  Use when monitoring OKX without trading (e.g. account equity, current PnL, recent fills, withdrawal history, margin level).
author: starchild
tags: [okx, account, readonly, tracking, futures, spot, swap]
metadata:
  starchild:
    emoji: "🅾️"
    skillKey: okx-account
    requires:
      env:
        - OKX_RO_API_KEY
        - OKX_RO_SECRET
        - OKX_RO_PASSPHRASE
    install:
      - kind: pip
        package: python-okx
      - kind: pip
        package: python-dotenv
user-invocable: true

---

# OKX Account (Read-Only)

Read-only OKX account tracker built on the official `python-okx` library.
Use it for account tracking, daily/weekly reports, risk alerts, and cashflow attribution.

## How to Get an OKX API Key (Read-Only)

1. Sign in at [okx.com](https://www.okx.com), top-right avatar → **API**
   - Direct link: https://www.okx.com/account/my-api
2. **Create V5 API Key** → complete 2FA verification
3. Fill the form:
   - **API name**: anything
   - **Passphrase**: ⚠️ a brand-new password used to sign API requests, **NOT your login password**. Lose it and you can only delete the key and create a new one.
   - **Permissions**: tick **Read** only, leave Trade / Withdraw off
   - **IP whitelist**: leave empty
4. Submit → **immediately copy and save** all three values: `API Key` / `Secret Key` / `Passphrase` (Secret is shown only once)
5. Set them into this skill's environment variables

Reference: [OKX official tutorial](https://www.okx.com/help/how-can-i-create-an-api-key)

## Prerequisites

### 1) API key
In OKX API Management create a key with **Read only**. OKX requires three credentials: `api_key` / `secret` / `passphrase` (the password you set when creating the key — not the login password).

### 2) Environment variables
```
OKX_RO_API_KEY=...
OKX_RO_SECRET=...
OKX_RO_PASSPHRASE=...
```

### 3) Geo restriction (required)
OKX geo-blocks server IPs. Scripts default to the SC internal HK proxy:
```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```
Do not set a global `HTTP_PROXY`.

## Scripts

```bash
python3 skills/okx-account/scripts/okx_account.py <action> [options]
python3 skills/okx-account/scripts/account_scenarios.py <scenario> [options]
```

## Actions

- `summary`: one-shot summary
- `account_balance` / `account_config` / `positions` / `position_risk` / `fee_rates` / `bills`
- `open_orders` / `order_history` / `fills_history`
- `funding_balance` / `deposits` / `withdrawals` / `currencies` / `funding_rate`

## Scenarios

- `portfolio_snapshot`: full account snapshot
- `perp_risk`: perpetual risk monitoring (margin ratio + unrealized loss thresholds)
- `cashflow`: deposits + withdrawals + 7d bills aggregation
- `trading_activity`: recent fills activity by instType

## Common usage

```bash
python3 skills/okx-account/scripts/okx_account.py summary
python3 skills/okx-account/scripts/account_scenarios.py portfolio_snapshot
python3 skills/okx-account/scripts/account_scenarios.py perp_risk --loss-threshold 5000
python3 skills/okx-account/scripts/account_scenarios.py cashflow --limit 100
python3 skills/okx-account/scripts/account_scenarios.py trading_activity --inst-types SPOT,SWAP
```

## Notes

- The `passphrase` is easy to forget — it is the password you set when creating the key, not your login password.
- If you bound an IP whitelist when creating the key, either disable it or add the proxy egress IP.
- Use time-windowed pagination for high-volume fills.
