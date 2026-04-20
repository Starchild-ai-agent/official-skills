---
name: jupiter
version: 1.2.0
description: "Jupiter DEX aggregator on Solana — token swaps, limit orders, DCA. Use when user mentions Jupiter, Solana swap, SOL/USDC swap, or Solana DEX aggregator."

metadata:
  starchild:
    emoji: "🪐"
    skillKey: jupiter

user-invocable: true
---

# Jupiter — Solana DEX Aggregator

Jupiter routes swaps across all Solana DEXes (Raydium, Orca, Phoenix…) for best price.

## ⛽ Gas & Cost — Read This First

- **Gas is always paid from wallet SOL balance.** No gas sponsorship on Solana.
- `wallet_sol_transfer` does NOT work for Jupiter — it's for send-SOL only.
- Swaps cost ~0.0002–0.001 SOL in fees (priority fee + rent deposit for new token accounts).
- Limit orders cost ~0.002 SOL to create (on-chain account rent).
- Always call `wallet_sol_balance()` before operating to confirm SOL > 0.01.

## ⛔ HARD RULES

- **ALWAYS use `ultra/v1/order`** — NOT `swap/v1/quote` + `swap/v1/swap` (deprecated)
- **Pass wallet pubkey to `jupiter_swap` only when intending to execute** — omitting it returns a quote-only result (no transaction), which is correct for price checks
- **NEVER pass numeric `makingAmount`/`takingAmount`** — must be strings or API returns ZodError 400
- **NEVER use `/ultra/v1/execute` for limit orders** — limit orders MUST go through `jupiter_broadcast_tx()` (Solana RPC)
- **NEVER omit user confirmation** before executing a swap or limit order
- **ALWAYS call `wallet_sol_balance()`** after swap to verify balances changed
- **NEVER mention DCA** — lite-api does not support it

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet** skill and propose the standard wildcard Solana policy (deny key export + allow `*`).

## Key Token Addresses (Solana)

| Token | Mint Address | Decimals |
|-------|-------------|---------|
| SOL   | `So11111111111111111111111111111111111111112` | 9 |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` | 6 |
| USDT | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` | 6 |
| JUP  | `JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN` | 6 |
| BONK | `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` | 5 |
| WIF  | `EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm` | 6 |
| JTO  | `jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL` | 6 (NOT 9) |

For unlisted tokens: ask user for mint address directly — token search API is deprecated.

## Available Tools (from exports.py)

| Tool | What it does |
|------|-------------|
| `jupiter_price(token)` | USD price of any token |
| `jupiter_swap(in, out, amount, wallet?)` | Quote only (no wallet) or quote + tx (wallet provided) |
| `jupiter_execute_swap(signed_tx, request_id, in_mint?, out_mint?)` | Broadcast swap via `/ultra/v1/execute` ← swap only |
| `jupiter_broadcast_tx(signed_tx)` | Broadcast via Solana RPC ← limit orders + cancel |
| `jupiter_limit_create(in, out, making, taking, maker)` | Create limit order |
| `jupiter_limit_orders(wallet, history=False)` | List open or historical orders |
| `jupiter_limit_cancel(order_pubkey, maker)` | Cancel an open order |

## Swap Workflow (End-to-End)

```
1. quote = jupiter_swap("SOL", "USDC", 0.01, wallet_pubkey)
   └─ returns: in_amount, out_amount, in_usd, out_usd, transaction, request_id

2. Show user: amount in/out, USD values, price_impact_pct — wait for confirm

3. signed = wallet_sol_sign_transaction(quote["transaction"])

4. result = jupiter_execute_swap(signed["signed_transaction"], quote["request_id"])
   └─ returns: status ("Success"), signature, in_amount, out_amount

5. wallet_sol_balance()  ← verify balances changed
```

**Key facts:**
- `jupiter_execute_swap` → POST `/ultra/v1/execute` — only for Ultra swaps
- `transaction` is `null` if wallet pubkey is missing/invalid — retry step 1 with a valid wallet
- Swap is atomic: if it fails, nothing is deducted (except gas fee)

## Limit Order Workflow (End-to-End)

```
1. order = jupiter_limit_create(
       input_token="SOL",    # selling
       output_token="USDC",  # buying
       making_amount=0.06,   # 0.06 SOL to sell
       taking_amount=3.0,    # want at least 3 USDC (sets target price)
       maker=wallet_pubkey
   )
   └─ returns: order_pubkey, transaction, implied_price, next_step

2. Show user: implied price, amounts — wait for confirm

3. signed = wallet_sol_sign_transaction(order["transaction"])
   ⚠️  Sign and broadcast within ~90 seconds — blockhash expires.

4. result = jupiter_broadcast_tx(signed["signed_transaction"])
   └─ returns: {"success": True, "signature": "..."} or {"success": False, "error": "..."}
   ⚠️  Use jupiter_broadcast_tx, NOT jupiter_execute_swap — different endpoints!

5. jupiter_limit_orders(wallet_pubkey)  ← confirm order_pubkey appears
   Note: if order fills instantly (implied price ≤ market), check orderHistory instead
```

**Key facts:**
- Min order size: ~$5 USD — smaller returns `{"error": "Order size must be at least 5 USD"}`
- Keepers may fill the order instantly if your implied price is favorable (≤ market)
- `orderKey` field in API response is the order pubkey (not `publicKey`)
- `makingAmount` / `takingAmount` in openOrders are already human-readable (e.g. "0.06"), not raw lamports
- `expiredAt` and `feeBps` must be omitted entirely if not used (don't pass null or 0)

## Cancel Order Workflow

```
1. orders = jupiter_limit_orders(wallet_pubkey)
2. Pick order_pubkey from orders["orders"][n]["order_pubkey"]
3. cancel = jupiter_limit_cancel(order_pubkey, wallet_pubkey)
4. signed = wallet_sol_sign_transaction(cancel["transaction"])
5. jupiter_broadcast_tx(signed["signed_transaction"])
```

## Tool Routing — IF/THEN

```
IF "price" / "how much is X"             → jupiter_price(token)
IF "quote" / "how much can I get"        → jupiter_swap(in, out, amount)  [wallet omitted = quote-only, no tx]
IF "swap" / "exchange" / "convert"       → jupiter_swap(in, out, amount, wallet) → confirm → sign → jupiter_execute_swap(in_mint, out_mint)
IF "limit order" / "buy when price hits" → jupiter_limit_create → sign → jupiter_broadcast_tx
IF "my orders" / "open orders"           → jupiter_limit_orders(wallet)
IF "cancel order"                        → jupiter_limit_orders → jupiter_limit_cancel → sign → jupiter_broadcast_tx
IF token not in KNOWN_TOKENS             → ask user for mint address
```


## Few-Shot Examples

**JUP-01 — "SOL price?"**
```python
jupiter_price("SOL")
# -> {"price_usd": 84.2, ...}
```

**JUP-01b — "How much USDC would I get for 0.5 SOL?" (quote only, no trade)**
```python
jupiter_swap("SOL", "USDC", 0.5)   # wallet_pubkey omitted
# -> {quote_only: True, in_amount: "0.50", out_amount: "42.10",
#     in_usd: "42.1", transaction: None}
# Stop here — show user the rate, no signing needed.
```

**JUP-02 — "Swap 0.01 SOL to USDC"**
```python
quote  = jupiter_swap("SOL", "USDC", 0.01, wallet_pubkey)
# → show: 0.01 SOL → ~0.84 USDC, impact <0.01%
signed = wallet_sol_sign_transaction(quote["transaction"])
result = jupiter_execute_swap(
    signed["signed_transaction"],
    quote["request_id"],
    in_mint=quote["in_mint"],
    out_mint=quote["out_mint"],
)
# → {"status": "Success", "signature": "yUKn...", "in_amount_fmt": "0.01", "out_amount_fmt": "0.84"}
wallet_sol_balance()
```

**JUP-03 — "Set limit: sell 0.06 SOL when USDC price hits $50/SOL"**
```python
# makingAmount=0.06 SOL, takingAmount=3 USDC (= 0.06 * 50)
order  = jupiter_limit_create("SOL", "USDC", 0.06, 3.0, wallet_pubkey)
# → implied_price: "1 USDC = 0.0200 SOL" (i.e. $50/SOL)
signed = wallet_sol_sign_transaction(order["transaction"])  # do this immediately!
result = jupiter_broadcast_tx(signed["signed_transaction"])
# → {"success": True, "signature": "53bp..."}
jupiter_limit_orders(wallet_pubkey)  # or check history if filled instantly
```

**JUP-04 — "My open orders"**
```python
jupiter_limit_orders(wallet_pubkey)
# → {"count": 1, "orders": [{"order_pubkey": "...", "making_amount": "0.06", ...}]}
```

**JUP-05 — "Cancel my order"**
```python
orders = jupiter_limit_orders(wallet_pubkey)
pubkey = orders["orders"][0]["order_pubkey"]
cancel = jupiter_limit_cancel(pubkey, wallet_pubkey)
signed = wallet_sol_sign_transaction(cancel["transaction"])
jupiter_broadcast_tx(signed["signed_transaction"])
```
