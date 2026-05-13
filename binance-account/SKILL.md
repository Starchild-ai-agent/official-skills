---
name: binance-account
version: 2.0.0
description: Read-only Binance account tracking (spot + USD-M futures) — balances, positions, orders, fills, deposits/withdrawals, funding income, snapshot, and risk scenarios.
author: starchild
tags: [binance, account, readonly, tracking, futures, spot]
metadata:
  starchild:
    emoji: "🏦"
    skillKey: binance-account
    requires:
      env:
        - BINANCE_RO_API_KEY
        - BINANCE_RO_SECRET
    install:
      - kind: pip
        package: python-binance
      - kind: pip
        package: python-dotenv
user-invocable: true
---

# Binance Account (Read-Only)

Read-only Binance account tracker built on the widely used `python-binance` library.
Use it for account tracking, daily/weekly reports, risk alerts, and cashflow attribution.

## How to Get a Binance API Key (Read-Only)

1. Sign in at [binance.com](https://www.binance.com), top-right avatar → **API Management**
   - Direct link: https://www.binance.com/en/my/settings/api-management
2. **Create API** → **System generated**
3. Complete 2FA verification (email + Authenticator / SMS)
4. Name the key → submit
5. **Copy** `API Key` + `Secret Key` immediately (Secret is shown only once)
6. **Edit restrictions**:
   - ✅ Enable only `Enable Reading`
   - ❌ Disable trading, withdrawal, and all write permissions
   - **Leave the IP whitelist empty** (binding an IP causes cloud calls to be rejected)
7. Set the values into this skill's environment variables

Reference: [Binance official tutorial](https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072)

## Prerequisites

### 1) API key permissions
In Binance API Management, create a read-only key. Enable only:
- ✅ Enable Reading
- ❌ Disable trading and withdrawal

### 2) Environment variables
```bash
BINANCE_RO_API_KEY=...
BINANCE_RO_SECRET=...
```

### 3) Geo restriction (required)
Binance frequently returns `451 Restricted Location` from server environments.
This skill defaults to the SC internal HK proxy:

```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```

Do not set a global `HTTP_PROXY` — it would break routing for other services.

## Scripts

### Base query script
```bash
python3 skills/binance-account/scripts/bn_account.py <action> [options]
```

### Scenario script
```bash
python3 skills/binance-account/scripts/account_scenarios.py <scenario> [options]
```

## Actions

- `summary`: one-shot summary
- `spot_balance` / `futures_balance` / `futures_positions`
- `spot_orders` / `futures_orders` / `spot_trades` / `futures_trades`
- `deposits` / `withdrawals` / `funding_income` / `account_snapshot`

## Scenarios

- `portfolio_snapshot`: full account snapshot
- `perp_risk`: futures risk monitoring (margin ratio + unrealized loss)
- `cashflow`: deposits + withdrawals + funding income aggregation
- `trading_activity`: recent trades by symbol

## Common usage

```bash
python3 skills/binance-account/scripts/bn_account.py summary
python3 skills/binance-account/scripts/account_scenarios.py portfolio_snapshot
python3 skills/binance-account/scripts/account_scenarios.py perp_risk --loss-threshold 5000
python3 skills/binance-account/scripts/account_scenarios.py cashflow
python3 skills/binance-account/scripts/account_scenarios.py trading_activity --symbol BTCUSDT
```

## Notes

- IP whitelist is best left empty for cloud usage.
- Use time-windowed pagination for high-frequency trade pulls.
