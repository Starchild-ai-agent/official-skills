---
name: pendle
version: 1.0.0
description: "Pendle Finance integration — swap yield tokens (PT/YT), add/remove liquidity, check implied APY. Use when user mentions Pendle, PT, YT, yield trading, fixed yield, or yield tokenization."

metadata:
  starchild:
    emoji: "🔵"
    skillKey: pendle

user-invocable: true
---

# Pendle — Yield Trading Protocol

Pendle splits yield-bearing assets into Principal Tokens (PT) and Yield Tokens (YT), enabling yield trading. PT = fixed yield at maturity. YT = variable yield exposure. All operations go through a single **Hosted SDK Convert API**.

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`).

## Core Concepts

- **SY (Standardized Yield)** — Wrapper for yield-bearing tokens (stETH, sUSDe, etc.)
- **PT (Principal Token)** — Redeemable for underlying at maturity. Buy at discount = lock in fixed yield.
- **YT (Yield Token)** — Receives all yield until maturity, then worth 0. Long YT = bet on rising yields.
- **Market (LP)** — AMM pool for PT trading. LPs earn swap fees + underlying yield.
- **Implied APY** — Market-priced expected yield. Compare with underlying APY for trade decisions.

## Hosted SDK API

**Base URL**: `https://api-v2.pendle.finance/core`

**Rate limits**: See `references/api-overview.md` if needed. High limit, suitable for most use cases.

### Universal Convert Endpoint

ALL operations (swap, add/remove liquidity, mint/redeem PT+YT) use one endpoint:

```
GET /v2/sdk/{chainId}/convert?tokensIn=...&tokensOut=...&amountsIn=...&receiver=...&slippage=...
```

The API returns a transaction object ready to sign and broadcast.

### Supported Chains

| Chain | ID |
|-------|-----|
| Ethereum | 1 |
| Arbitrum | 42161 |
| BSC | 56 |
| Optimism | 10 |
| Mantle | 5000 |

### Common Operations

**Swap token → PT** (lock in fixed yield):
```
GET /v2/sdk/1/convert?
  receiver=<WALLET>&slippage=0.01
  &tokensIn=<USDC_ADDRESS>
  &tokensOut=<PT_ADDRESS>
  &amountsIn=<AMOUNT_WEI>
  &enableAggregator=true
```

**Swap PT → token** (exit fixed yield position):
```
GET /v2/sdk/1/convert?
  receiver=<WALLET>&slippage=0.01
  &tokensIn=<PT_ADDRESS>
  &tokensOut=<USDC_ADDRESS>
  &amountsIn=<AMOUNT_WEI>
  &enableAggregator=true
```

**Add liquidity** (earn swap fees):
```
tokensIn=<ASSET_ADDRESS>&tokensOut=<MARKET_ADDRESS>
```

**Add liquidity + keep YT** (ZPI):
```
tokensIn=<ASSET>&tokensOut=<MARKET_ADDRESS>,<YT_ADDRESS>
```

**Mint PT + YT** from underlying:
```
tokensIn=<ASSET>&tokensOut=<PT_ADDRESS>,<YT_ADDRESS>
```

**Redeem PT + YT** to underlying:
```
tokensIn=<PT_ADDRESS>,<YT_ADDRESS>&tokensOut=<ASSET>
```

### Market Discovery

```
GET /v1/{chainId}/markets?limit=10
```

Returns available markets with TVL, implied APY, underlying asset, and expiry.

### Response Format

The Convert API returns:
```json
{
  "tx": { "to": "0x...", "data": "0x...", "value": "0" },
  "data": {
    "amountOut": "...",
    "priceImpact": "...",
    "impliedApy": "..."
  }
}
```

The `tx` object can be passed directly to `wallet_transfer()`:
```python
wallet_transfer(to=tx["to"], amount=tx.get("value", "0"), chain_id=1, data=tx["data"])
```

Use `scripts/pendle_ops.py` for API calls and tx construction.

## Decision Framework

| User wants... | Action | Tokens |
|--------------|--------|--------|
| Fixed yield | Buy PT | token → PT |
| Bet on rising yields | Buy YT | token → YT |
| Earn swap fees | Add LP | token → Market |
| LP + yield exposure | Add LP ZPI | token → Market + YT |
| Exit fixed position | Sell PT | PT → token |

## Gotchas

- **PT has expiry** — after maturity, PT is redeemable 1:1 for underlying. Before maturity, PT trades at discount.
- **YT goes to 0 at maturity** — only buy YT if you expect yields to exceed the implied rate before expiry.
- **`enableAggregator=true`** — always set this for better routing through external DEXes.
- **Slippage**: Use 0.01 (1%) as default, tighten for large positions.
- **Token addresses change per market** — always use the API to discover current PT/YT/Market addresses.
