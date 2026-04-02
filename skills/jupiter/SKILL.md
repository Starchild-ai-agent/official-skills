---
name: jupiter
version: 1.0.0
description: "Jupiter DEX aggregator on Solana — token swaps, limit orders, DCA. Use when user mentions Jupiter, Solana swap, SOL/USDC swap, or Solana DEX aggregator."

metadata:
  starchild:
    emoji: "🪐"
    skillKey: jupiter

user-invocable: true
---

# Jupiter — Solana DEX Aggregator

Jupiter routes swaps across all major Solana DEXes (Raydium, Orca, Phoenix, etc.) for best price. All operations use the **Jupiter Quote + Swap API**.

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet-policy** skill and propose the standard wildcard Solana policy (deny key export + allow `*`).

## Key Token Addresses (Solana)

| Token | Mint Address |
|-------|-------------|
| SOL (wrapped) | `So11111111111111111111111111111111111111112` |
| USDC | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| USDT | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` |
| JUP | `JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN` |

## API Overview

**Base URL**: `https://lite-api.jup.ag` (free, no API key)

### Step 1 — Get Quote

```
GET /swap/v1/quote?
  inputMint=<TOKEN_IN_MINT>
  &outputMint=<TOKEN_OUT_MINT>
  &amount=<AMOUNT_IN_LAMPORTS>
  &slippageBps=50
  &restrictIntermediateTokens=true
```

Response includes `outAmount`, `priceImpactPct`, `routePlan`.

### Step 2 — Get Swap Transaction

```
POST /swap/v1/swap
{
  "quoteResponse": <FULL_QUOTE_RESPONSE>,
  "userPublicKey": "<WALLET_SOL_ADDRESS>",
  "dynamicComputeUnitLimit": true,
  "dynamicSlippage": true,
  "prioritizationFeeLamports": { "priorityLevelWithMaxLamports": { "maxLamports": 1000000, "priorityLevel": "medium" } }
}
```

Response: `{ "swapTransaction": "<base64_serialized_tx>" }`

### Step 3 — Sign and Broadcast

Pass the base64 transaction to `wallet_sol_transfer()`:
```python
wallet_sol_transfer(transaction=swap_tx_base64)
```

## Workflow

1. **Quote**: `bash("python skills/jupiter/scripts/jupiter_ops.py quote <in_mint> <out_mint> <amount>")`
2. **Review**: Show user the quote (output amount, price impact, route)
3. **Build Tx**: `bash("python skills/jupiter/scripts/jupiter_ops.py swap <in_mint> <out_mint> <amount> <wallet_pubkey>")`
4. **Sign**: `wallet_sol_transfer(transaction=<base64_tx>)`
5. **Verify**: `wallet_sol_balance()` to confirm new balances

## Gotchas

- **Amount is in smallest unit** — SOL uses 9 decimals (1 SOL = 1_000_000_000 lamports), USDC uses 6 decimals.
- **`restrictIntermediateTokens=true`** — prevents routing through illiquid tokens. Always use.
- **`dynamicSlippage=true`** — API auto-calculates optimal slippage. Recommended over fixed slippageBps for most swaps.
- **Priority fees** — Solana congestion can cause tx failures. Use `priorityLevel: "medium"` or `"high"` during congestion.
- **Transaction size** — Solana has tx size limits. Complex routes may require multiple txs (the API handles this).
- **SOL wrapping** — Jupiter auto-wraps/unwraps SOL. Use the wrapped SOL mint address.
