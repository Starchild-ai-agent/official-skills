---
name: okx-account
version: 1.0.0
description: OKX 只读账户追踪（统一账户）— 余额、持仓、订单、成交、出入金、账单、风险场景分析
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

只读 OKX 账户追踪技能，基于官方 `python-okx` 库。
适用于账户跟踪、日报周报、风险提醒、资金流归因。

## Prerequisites

### 1) API Key
在 OKX API Management 创建 Key（**只勾选 Read**），需要 3 项凭据：
`api_key` / `secret` / `passphrase`（创建 Key 时设的密码，非登录密码）。

### 2) 环境变量
```
OKX_RO_API_KEY=...
OKX_RO_SECRET=...
OKX_RO_PASSPHRASE=...
```

### 3) 地区限制（必须）
OKX 对服务器 IP 有地理封锁。脚本默认通过 SC 内网 HK 代理：
```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```
不要设置全局 `HTTP_PROXY`。

## Scripts

```bash
python3 skills/okx-account/scripts/okx_account.py <action> [options]
python3 skills/okx-account/scripts/account_scenarios.py <scenario> [options]
```

## Actions

- `summary`: 一键汇总
- `account_balance`/`account_config`/`positions`/`position_risk`/`fee_rates`/`bills`
- `open_orders`/`order_history`/`fills_history`
- `funding_balance`/`deposits`/`withdrawals`/`currencies`/`funding_rate`

## Scenarios

- `portfolio_snapshot`: 全账户快照
- `perp_risk`: 永续风险监控（保证金率/未实现亏损阈值）
- `cashflow`: 充提 + 7 日账单归集
- `trading_activity`: 按 instType 的近期成交活跃度

## Common Usage

```bash
python3 skills/okx-account/scripts/okx_account.py summary
python3 skills/okx-account/scripts/account_scenarios.py portfolio_snapshot
python3 skills/okx-account/scripts/account_scenarios.py perp_risk --loss-threshold 5000
python3 skills/okx-account/scripts/account_scenarios.py cashflow --limit 100
python3 skills/okx-account/scripts/account_scenarios.py trading_activity --inst-types SPOT,SWAP
```

## Notes

- `passphrase` 易忘——是创建 Key 时设的密码，不是登录密码。
- 创建 Key 时如果绑定 IP 白名单，需要关闭或加入代理出口 IP。
- 高频成交对建议按时间窗口分页抓取。
