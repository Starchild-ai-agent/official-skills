---
name: binance-account
version: 1.1.0
description: Binance 只读账户追踪（现货+U本位合约）— 余额、持仓、订单、成交、出入金、资金费、快照与风险场景分析
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

只读 Binance 账户追踪技能，基于广泛使用的 `python-binance` 库。
适用于账户跟踪、日报周报、风险提醒、资金流归因。

## 如何获取 Binance API Key（只读）

1. 登录 [binance.com](https://www.binance.com)，右上角头像 → **API Management**
   - 直达链接：https://www.binance.com/en/my/settings/api-management
2. **Create API** → **System generated**
3. 完成 2FA 验证（邮箱 + 谷歌验证器 / 短信）
4. 给 Key 起名 → 提交
5. **立刻复制** `API Key` + `Secret Key`（Secret 只显示一次）
6. **Edit restrictions**：
   - ✅ 只勾 `Enable Reading`
   - ❌ 关闭交易、提币等所有写权限
   - **IP 白名单留空**（绑定 IP 后云端调用会被拒）
7. 填到本 skill 的环境变量

参考：[Binance 官方教程](https://www.binance.com/en/support/faq/how-to-create-api-keys-on-binance-360002502072)

## Prerequisites

### 1) API Key 权限
在 Binance API Management 创建只读 Key，仅开启：
- ✅ Enable Reading
- ❌ 禁止交易/提币

### 2) 环境变量
```bash
BINANCE_RO_API_KEY=...
BINANCE_RO_SECRET=...
```

### 3) 地区限制（必须）
Binance 在服务器环境常出现 `451 Restricted Location`。
本 skill 脚本默认通过 SC 内网 HK 代理访问：

```python
HK_PROXY = "http://hk:x@sc-vpn.internal:8080"
```

不建议设置全局 `HTTP_PROXY`，避免影响其他服务路由。

## Scripts

### 基础查询脚本
```bash
python3 skills/binance-account/scripts/bn_account.py <action> [options]
```

### 场景分析脚本
```bash
python3 skills/binance-account/scripts/account_scenarios.py <scenario> [options]
```

## Actions（bn_account.py）

- `summary`: 一键汇总（现货余额 + 合约账户 + 当前持仓）
- `spot_balance`: 现货非零余额
- `futures_balance`: U 本位合约钱包余额
- `futures_account`: 合约账户概览（权益/未实现盈亏/可用保证金）
- `futures_positions`: 当前合约持仓
- `spot_orders`: 现货当前挂单
- `spot_order_history`: 现货历史订单
- `futures_orders`: 合约当前挂单
- `trade_history`: 现货成交记录
- `futures_trade_history`: 合约成交记录
- `deposit_history`: 充值记录
- `withdraw_history`: 提币记录
- `income_history`: 合约收入流水（资金费/已实现收益/手续费等）
- `asset_snapshot`: 账户快照（SPOT/MARGIN/FUTURES）
- `funding_rate`: 资金费率与标记价格

## Scenarios（account_scenarios.py）

- `portfolio_snapshot`: 全账户快照（现货+合约）
- `futures_risk`: 合约风险监控（维持保证金占比、未实现亏损阈值）
- `cashflow`: 出入金/划转/资金费流水归集（含接口失败明细）
- `trading_activity`: 指定交易对在 N 天内的交易活跃度、净仓位变化

## Common Usage

```bash
# 1) 一键总览
python3 skills/binance-account/scripts/bn_account.py summary

# 2) 现金流归集
python3 skills/binance-account/scripts/account_scenarios.py cashflow --limit 100

# 3) 合约风险
python3 skills/binance-account/scripts/account_scenarios.py futures_risk --loss-threshold 5000

# 4) 交易活跃度
python3 skills/binance-account/scripts/account_scenarios.py trading_activity --days 30 --symbols BTCUSDT,ETHUSDT,PAXGUSDT
```

## Notes

- 只读 key 下，`futures_account_transfer` 可能返回权限错误（`-1002`），脚本已做回退处理。
- 高交易频率交易对建议按时间窗口分页抓取，避免单次 `limit` 截断历史。
