---
name: 1inch
version: 2.2.0
description: 1inch DEX aggregator — same-chain swap, cross-chain Fusion+, limit orders. Native tools, no Fly dependency.
author: starchild
tags: [1inch, dex, swap, evm, limit-order, cross-chain]
metadata:
  starchild:
    emoji: "🦄"
    skillKey: 1inch
user-invocable: true
disable-model-invocation: false
---

# 🦄 1inch Skill v2.2.0

Same-chain swap · Cross-chain Fusion+ · Limit Orders

**Architecture:** All tools are native functions in `exports.py`.  
**Signing:** `wallet_sign_transaction` / `wallet_sign_typed_data` (platform wallet, no Fly dependency).  
**API:** All calls via sc-proxy (credentials auto-injected, zero user config).

---

## ⛔ ROUTING RULES — READ FIRST

```
IF user asks: swap / 兑换 / 换币 / buy / sell (same chain)
  → oneinch_quote (preview) → oneinch_swap (execute)

IF user asks: cross-chain / 跨链 / bridge swap
  → oneinch_cross_chain_quote → oneinch_cross_chain_swap

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

### Cross-Chain Fusion+ (3 tools)

| Tool | Type | Purpose |
|------|------|---------|
| `oneinch_cross_chain_quote` | READ | Cross-chain quote (gasless intent) |
| `oneinch_cross_chain_status` | READ | Check Fusion+ order status |
| `oneinch_cross_chain_swap` | WRITE | Execute cross-chain swap (long-running, ~10min) |

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

## Cross-Chain Flow

```
1. oneinch_cross_chain_quote(src_chain, dst_chain, src_token, dst_token, amount)
2. oneinch_cross_chain_swap(...)   # long-running (~10min), use sessions_spawn
3. oneinch_cross_chain_status(order_hash)  # poll if spawned
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
| `needs_approval: true` | Run `oneinch_approve` first |
| `Policy violation` | Load `wallet-policy` skill, propose wildcard policy |
| `1inch API 4xx` | Show raw error; check token address and chain |
| `No transaction data` | Check src/dst address validity |
| Cross-chain timeout | Use `oneinch_cross_chain_status(order_hash)` to poll later |

---

## Key Addresses

- 1inch Router v6 / LOP v4: `0x111111125421cA6dc452d289314280a0f8842A65`
- Native ETH: `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`
