---
name: jupiter
version: 1.1.0
description: "Jupiter DEX aggregator on Solana — token swaps, limit orders, DCA. Use when user mentions Jupiter, Solana swap, SOL/USDC swap, or Solana DEX aggregator."

metadata:
  starchild:
    emoji: "🪐"
    skillKey: jupiter

user-invocable: true
---

# Jupiter — Solana DEX Aggregator

Jupiter routes swaps across all Solana DEXes (Raydium, Orca, Phoenix…) for best price.

## ⛔ HARD RULES

- **ALWAYS use `ultra/v1/order`** — NOT `swap/v1/quote` + `swap/v1/swap` (deprecated two-step)
- **NEVER pass numeric `makingAmount`/`takingAmount`** — must be strings or API returns ZodError
- **NEVER mention DCA** — lite-api does not support it
- **NEVER omit user confirmation** before executing a swap or limit order
- **HARD LIMIT: max 6 tool calls** per user request
- **ALWAYS call `wallet_sol_balance()`** after swap to verify balances changed

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet-policy** skill and propose the standard wildcard Solana policy (deny key export + allow `*`).

## Key Token Addresses (Solana)

| Token | Mint Address |
|-------|-------------|
| SOL (wrapped) | `So11111111111111111111111111111111111111112` |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| USDT | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` |
| JUP  | `JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN` |
| BONK | `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` |
| WIF  | `EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm` |

For unlisted tokens: ask user for mint address directly — token search API is deprecated.

## API Overview

**Base URL**: `https://lite-api.jup.ag` (free, no API key)

### Swap — Ultra API (primary, always use this)

```
GET /ultra/v1/order?inputMint=<>&outputMint=<>&amount=<lamports>
```

Returns in ONE call: `inAmount`, `outAmount`, `inUsdValue`, `outUsdValue`,
`priceImpactPct`, `transaction` (base64), `requestId`.

After signing, execute via:
```
POST /ultra/v1/execute
{ "signedTransaction": "<base64>", "requestId": "<id>" }
```

### Limit Orders — Trigger API

```
POST /trigger/v1/createOrder
{
  "inputMint": "<>", "outputMint": "<>",
  "maker": "<wallet>", "payer": "<wallet>",
  "params": {
    "makingAmount": "10000000",   ← STRING, not number
    "takingAmount": "90000000"    ← STRING, not number
  },
  "computeUnitPrice": "auto"
}
```

```
GET  /trigger/v1/openOrders?wallet=<>
GET  /trigger/v1/orderHistory?wallet=<>
POST /trigger/v1/cancelOrder  { "order": "<pubkey>", "maker": "<>", "computeUnitPrice": "auto" }
```

**Gotchas (verified live)**:
- `makingAmount`/`takingAmount` → must be strings (int → ZodError 400)
- `expiredAt` → omit entirely if not set (do NOT pass `null`)
- `feeBps` → omit entirely if not set (do NOT pass `0`)

## Tool Routing — IF/THEN

```
IF "SOL price" / "how much is X"         → jupiter_price(token)
IF "quote" / "how much can I get"         → jupiter_quote(in, out, amount)
IF "swap" / "exchange" / "convert"        → jupiter_quote → confirm → jupiter_swap
IF "limit order" / "buy when price hits"  → jupiter_limit_create(...)
IF "my orders" / "open orders"            → jupiter_limit_orders(wallet)
IF "cancel order"                         → jupiter_limit_orders → jupiter_limit_cancel
IF token not in KNOWN_TOKENS              → ask user for mint address
```

## Swap Workflow (End-to-End)

```
1. jupiter_quote(input, output, amount)         ← ultra/v1/order
2. Show user: out_amount, in_usd, out_usd, price_impact_pct
3. Wait for confirmation
4. wallet_sol_sign_transaction(tx=quote["transaction"])
5. POST /ultra/v1/execute { signedTransaction, requestId }
6. wallet_sol_balance()                          ← verify
```

## Limit Order Workflow (End-to-End)

```
1. jupiter_limit_create(in, out, making, taking, maker)
2. Show user: order details, implied price
3. Wait for confirmation
4. wallet_sol_sign_transaction(tx=result["transaction"])
5. Broadcast signed tx
6. jupiter_limit_orders(wallet)                  ← confirm order appears
```

## Few-Shot Examples

**JUP-01 — "SOL price?"**
```
jupiter_price("SOL") → {"price_usd": 148.32, ...}
Reply: "SOL is currently $148.32."
```

**JUP-02 — "Quote: 1 SOL → USDC"**
```
jupiter_quote("SOL", "USDC", 1.0)
→ in_amount=1 SOL (~$148.32), out_amount=148.07 USDC, impact=0.02%
Reply: "1 SOL → ~148.07 USDC (impact 0.02%). Swap?"
```

**JUP-03 — "Swap 0.5 SOL → USDC"**
```
jupiter_quote("SOL","USDC",0.5) → show quote → confirm
jupiter_swap("SOL","USDC",0.5,wallet_pubkey)
wallet_sol_sign_transaction(tx) → execute → wallet_sol_balance()
```

**JUP-04 — "Buy SOL when it hits $120, spend 100 USDC"**
```
# 100 USDC → X SOL at $120/SOL = 0.833 SOL
jupiter_limit_create("USDC","SOL", making=100, taking=0.833, maker=wallet)
→ sign → broadcast → jupiter_limit_orders(wallet) to confirm
```

**JUP-05 — "My open orders"**
```
jupiter_limit_orders(wallet) → display table
```

**JUP-06 — "Cancel my latest order"**
```
jupiter_limit_orders(wallet) → pick most recent pubkey
jupiter_limit_cancel(order_pubkey, maker)
→ sign → broadcast
```

**JUP-07 — "Swap 10 USDC → JUP" (English)**
```
jupiter_quote("USDC","JUP",10.0) → confirm → jupiter_swap(...)
```

**JUP-08 — "WIF mint address?"**
```
Reply directly: EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm
```

## Amount Conversion Reference

| Token | Decimals | 1 unit in lamports |
|-------|----------|--------------------|
| SOL   | 9        | 1_000_000_000      |
| USDC  | 6        | 1_000_000          |
| USDT  | 6        | 1_000_000          |
| JUP   | 6        | 1_000_000          |
| BONK  | 5        | 100_000            |
| WIF   | 6        | 1_000_000          |
