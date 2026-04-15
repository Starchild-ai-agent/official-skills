---
name: 1inch
version: 4.1.0
description: 1inch DEX aggregator — EVM same-chain swap, SOL↔EVM cross-chain Fusion+, limit orders. Native tools, no Fly dependency, no aiohttp.
author: starchild
tags: [1inch, dex, swap, evm, solana, limit-order, cross-chain]
metadata:
  starchild:
    emoji: "🦄"
    skillKey: 1inch
user-invocable: true
disable-model-invocation: false
---

# 🦄 1inch Skill v4.1.0

Same-chain swap · Cross-chain Fusion+ (EVM↔EVM + SOL↔EVM) · Limit Orders

**Architecture:** All tools are native functions in `exports.py`. `__init__.py` BaseTool/`register()` path is NOT used by the platform — platform skill-loader only reads `exports.py` top-level functions.  
**Signing:** `_wallet_request("POST", "/agent/transfer", {...})` via platform internal API (broadcasts tx). Do NOT use `wallet_sign_transaction` (sign-only, never broadcasts).  
**API:** All calls via sc-proxy (credentials auto-injected, zero user config).

---

## ⛔ ROUTING RULES — READ FIRST

```
IF user asks: swap / 兑换 / 换币 / buy / sell (same chain)
  → oneinch_quote (preview) → oneinch_swap (execute)

IF user asks: cross-chain / 跨链 / bridge swap (EVM↔EVM)
  → oneinch_cross_chain_quote → oneinch_cross_chain_swap

IF user asks: SOL → EVM cross-chain / Solana 跨链到 ETH/ARB/BASE
  → oneinch_sol_cross_chain_quote → oneinch_sol_to_evm_swap

IF user asks: EVM → SOL cross-chain / 跨链到 Solana
  → oneinch_cross_chain_quote(dst_chain="solana") → oneinch_cross_chain_swap

⛔ IF user asks: Solana 内部 swap / SOL→USDC / Solana token swap (SAME CHAIN)
  → DO NOT use 1inch. Use Jupiter skill instead.
  → 1inch has NO Solana-internal swap API (no Router contract on Solana)

IF user asks: limit order / 限价单 / 挂单 / 目标价格买卖
  → oneinch_create_limit_order

IF user asks: check my orders / 我的订单 / 挂单状态
  → oneinch_get_orders / oneinch_get_order

IF user asks: cancel order / 取消限价单
  → oneinch_cancel_limit_order

NEVER call bash or python3 scripts/ — use native tools only
NEVER use wallet_transfer directly for swaps — always oneinch_swap
```

---

## Tools

### Same-Chain Swap (5 tools)

| Tool | Type | Purpose |
|------|------|---------|
| `oneinch_tokens` | READ | Search token addresses on a chain |
| `oneinch_quote` | READ | Get swap quote (no tx) |
| `oneinch_check_allowance` | READ | Check ERC-20 approval status |
| `oneinch_approve` | WRITE | Approve token for router |
| `oneinch_swap` | WRITE | Execute swap (best route across 200+ DEXes) |

### Cross-Chain Fusion+ EVM↔EVM / EVM→SOL (3 tools)

| Tool | Type | Purpose |
|------|------|---------|
| `oneinch_cross_chain_quote` | READ | Quote EVM↔EVM or EVM→Solana |
| `oneinch_cross_chain_status` | READ | Check Fusion+ order status |
| `oneinch_cross_chain_swap` | WRITE | Execute EVM↔EVM or EVM→SOL swap (~4-10min) |

### Cross-Chain Fusion+ SOL→EVM (2 tools)

| Tool | Type | Purpose |
|------|------|---------|
| `oneinch_sol_cross_chain_quote` | READ | Quote for Solana → EVM chain |
| `oneinch_sol_to_evm_swap` | WRITE | Execute SOL→EVM swap, returns signed_tx for broadcast |

### Limit Orders / Orderbook (4 tools)

| Tool | Type | Purpose |
|------|------|---------|
| `oneinch_get_orders` | READ | List open limit orders for a wallet |
| `oneinch_get_order` | READ | Get specific order by hash |
| `oneinch_create_limit_order` | WRITE | Create & submit EIP-712 signed limit order |
| `oneinch_cancel_limit_order` | WRITE | Cancel order on-chain |

---

## Supported Chains

`ethereum` · `arbitrum` · `base` · `optimism` · `polygon` · `bsc` · `avalanche` · `gnosis`

**Cross-chain also supports Solana** (chain_id=`501`, name=`"solana"`)  
Solana internal swap is NOT supported — use **Jupiter skill** instead.

---

## Standard Swap Flow

```
1. oneinch_tokens(chain, search="USDC")     # find token address
2. oneinch_check_allowance(chain, token)    # check if approved
3. oneinch_approve(chain, token)            # approve if needed
4. oneinch_quote(chain, src, dst, amount)   # preview rate
5. oneinch_swap(chain, src, dst, amount)    # execute
```

## Limit Order Flow

```
1. oneinch_check_allowance(chain, maker_asset)   # check approval
2. oneinch_approve(chain, maker_asset)            # approve if needed
3. oneinch_create_limit_order(                    # submit order
     chain, maker_asset, taker_asset,
     making_amount, taking_amount,
     expiry_seconds=86400
   )
4. oneinch_get_orders(chain)                      # check status later
5. oneinch_cancel_limit_order(chain, order_hash)  # cancel if needed
```

## Cross-Chain Flow (EVM↔EVM or EVM→SOL)

```
1. oneinch_approve(src_chain, src_token)              # 首次必须，每条链单独执行
2. oneinch_cross_chain_quote(src_chain, dst_chain, src_token, dst_token, amount)
3. oneinch_cross_chain_swap(...)   # 主会话直接调用，勿用 sessions_spawn（子任务无钱包）
4. oneinch_cross_chain_status(order_hash)  # 查询状态

# EVM → Solana: dst_chain="solana", receiver=<SOL base58 address>
# Solana → EVM:
1. oneinch_sol_cross_chain_quote(src_token, dst_chain, dst_token, amount)
2. oneinch_sol_to_evm_swap(...)  # returns {order_hash, signed_tx_b64}
   # broadcast signed_tx_b64 to Solana mainnet
```

---

## Amount Units

All amounts in **wei** (smallest unit):
- 1 USDC = `1000000` (6 decimals)
- 1 ETH/WETH = `1000000000000000000` (18 decimals)
- Use `oneinch_tokens` to get decimals for any token

---

## Error Handling

| Error | Action |
|-------|--------|
| `Unknown chain` | Use supported chain name |
| `needs_approval: true` | Run `oneinch_approve` first (approve each chain separately — ARB/BASE USDC need their own approve) |
| `Policy violation` | Load `wallet-policy` skill, propose wildcard policy |
| `1inch API 4xx` | Show raw error; check token address and chain |
| `No transaction data` | Check src/dst address validity |
| Cross-chain timeout | Use `oneinch_cross_chain_status(order_hash)` to poll later |
| `No ethereum wallet configured` | `_get_wallet_address()` failed — check `/app/tools/wallet.py` `_wallet_request("GET", "/agent/wallet")` is reachable |
| 429 Rate limit (cross-chain concurrent) | Add 20s delay between parallel swap launches; `_fusion_get/_fusion_post` should include backoff retry (P2) |

---

## ⚠️ Known Architecture Constraints

### 1. Platform只走 `exports.py`
```
✅ exports.py 顶层函数  →  native tool 注册成功
❌ __init__.py register() / BaseTool  →  平台不走这条路径，工具 not found
```
**规则：** 所有新工具必须在 `exports.py` 定义顶层函数。`__init__.py` 的 `register()` 只保留 stub、不写业务逻辑。

### 2. Tx 广播必须用 `/agent/transfer`，不能用 `/agent/sign-transaction`
```python
# ✅ 正确 — 签名 + 广播
asyncio.run(_wallet_request("POST", "/agent/transfer", {
    "to": ..., "data": ..., "value": ..., "amount": "0", "chain_id": cid
}))

# ❌ 错误 — 只签名，tx 从未发出，allowance 永远不更新
asyncio.run(_wallet_request("POST", "/agent/sign-transaction", {...}))
```

### 3. Fusion+ API 域名必须用 `.com`
```python
FUSION_BASE = "https://api.1inch.com/fusion-plus"   # ✅
# "https://api.1inch.dev/fusion-plus"               # ❌ 死域名
```

### 4. Fusion+ Quoter 必须用 v1.1
```
/quoter/v1.1/quote/receive   ✅
/quoter/v1.0/quote/receive   ❌ 旧版，返回 404 或错误格式
```

### 5. `sessions_spawn` 子任务无法访问钱包签名
跨链 swap 需要 `_wallet_request` 签名，子会话中无钱包实例。  
**规则：** 跨链 swap 必须在主会话中直接调用工具，不能 `sessions_spawn`。

### 6. 每条链 USDC 需单独 Approve
ARB/BASE 的 USDC approve 独立于 ETH 主网，初次跨链前必须对每条链分别执行 `oneinch_approve`。

---

## 实测数据（ETH/ARB/BASE 两两双向，2025）

| 方向 | 发送 | 到账 | 滑点 | 结算时间 |
|------|------|------|------|---------|
| ETH → ARB | 2 USDC | 1.871 USDC | 6.4% | 125s |
| ARB → ETH | 2 USDC | 1.872 USDC | 6.4% | 92s |
| ETH → BASE | 2 USDC | 1.856 USDC | 7.2% | 123s |
| BASE → ETH | 2 USDC | 1.906 USDC | 4.7% | 110s |
| ARB → BASE | 2 USDC | 1.944 USDC | 2.8% | 47s |
| BASE → ARB | 2 USDC | 1.964 USDC | 1.8% | 79s |

平均滑点：~4.9%（含跨链结算费）  
平均结算：~96s

---

## Key Addresses

- 1inch Router v6 / LOP v4: `0x111111125421cA6dc452d289314280a0f8842A65`
- Native ETH: `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`
