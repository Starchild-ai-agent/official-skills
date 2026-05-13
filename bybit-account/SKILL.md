---
name: bybit-account
version: 1.1.0
description: Bybit 只读账户追踪（统一交易账户）— 余额、持仓、订单、成交、出入金、转账、交易流水、风险场景分析
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

只读 Bybit 账户追踪技能，基于官方 `pybit` 库。
适用于账户跟踪、日报周报、风险提醒、资金流归因。

## Prerequisites

### 1) API Key
在 Bybit API Management 创建 Key，**只勾选 Read**。

### 2) 环境变量
```
BYBIT_RO_API_KEY=...
BYBIT_RO_SECRET=...
```

### 3) 地区限制（必须）
Bybit 对服务器 IP 有地理封锁。脚本默认通过 SC 内网 HK 代理：
```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```
注入方式：`session.client.proxies.update({'http': HK, 'https': HK})`。
**不要**用 `HTTP(proxies=...)` 构造（pybit 不支持）。

## Scripts

```bash
python3 skills/bybit-account/scripts/bybit_account.py <action> [options]
python3 skills/bybit-account/scripts/account_scenarios.py <scenario> [options]
```

## Important: FUND Account is Separate

`get_wallet_balance` 在 v5 **只支持 UNIFIED**，资金账户（FUND）必须用 `get_coins_balance(accountType='FUND')`。`summary` 和 `portfolio_snapshot` 已自动两边都查并合并。

持仓查询：`linear` 必须按 `settleCoin` 分别拉（USDT/USDC），`inverse` 用 BTC。`summary` 和 `perp_risk` 已自动扫描三种结算币。

## Actions

- `summary`: 一键汇总（UNIFIED + FUND + 多结算币持仓）
- `wallet_balance`/`coin_balance`/`funding_balance`/`account_info`/`fee_rates`/`collateral_info`
- `positions`/`open_orders`/`order_history`/`executions`
- `deposits`/`withdrawals`/`internal_transfers`/`universal_transfers`
- `transaction_log`/`borrow_history`/`server_time`

## Scenarios

- `portfolio_snapshot`: 全账户快照（钱包+持仓）
- `perp_risk`: 合约风险监控（IM/MM 比率 + 未实现亏损）
- `cashflow`: 充提+转账+交易流水归集
- `trading_activity`: 按 category 的近期成交活跃度

## Common Usage

```bash
python3 skills/bybit-account/scripts/bybit_account.py summary
python3 skills/bybit-account/scripts/account_scenarios.py portfolio_snapshot
python3 skills/bybit-account/scripts/account_scenarios.py perp_risk --loss-threshold 5000
python3 skills/bybit-account/scripts/account_scenarios.py cashflow --limit 100
python3 skills/bybit-account/scripts/account_scenarios.py trading_activity --categories spot,linear
```

## Important Parameters

- `--account-type`: UNIFIED（默认）/ CONTRACT / SPOT / FUND / INVESTMENT / OPTION
- `--category`: spot / linear / inverse / option
- `--settle`: linear/inverse 持仓必须指定结算币（默认 USDT）

## Notes

- pybit 的 HTTP 构造函数不接受 `proxies` 参数；必须在构造后通过 `client.proxies` 注入。
- `linear` 持仓必须指定 `settleCoin` 或 `symbol` 之一。
- 大额 fills 建议按时间窗口分页拉取。
