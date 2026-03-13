---
name: 1inch
version: 1.0.0
description: Swap tokens via 1inch DEX aggregator
tools:
  - oneinch_quote
  - oneinch_tokens
  - oneinch_check_allowance
  - oneinch_approve
  - oneinch_swap
  - oneinch_cross_chain_quote
  - oneinch_cross_chain_swap
  - oneinch_cross_chain_status
metadata:
  starchild:
    emoji: "🦄"
    skillKey: 1inch
    requires:
      env: [ONEINCH_API_KEY, WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# 1inch DEX Aggregator

Swap tokens on EVM networks using the 1inch DEX aggregator. 1inch finds the best swap route across DEXes (Uniswap, SushiSwap, Curve, Balancer, etc.) to get the best price. This is **Classic Swap** mode where the user pays gas directly.

**Supported Networks:** Ethereum, Arbitrum, Base, Optimism, Polygon, BSC, Avalanche, Gnosis.

**IMPORTANT:** All tools require a `chain` parameter. Always ask the user which network they want to use before proceeding. Do not assume a default chain.

**Default for spot token swaps.** Use 1inch for buying/selling/swapping tokens. 1inch aggregates liquidity across all major DEXes to get the best price. Hyperliquid spot is only for tokens listed on Hyperliquid's own orderbook — for general spot trading across chains.

## Prerequisites — Wallet Policy

Before executing any swap, the wallet policy must be active. Load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`). This covers all 1inch operations — swap transactions, token approvals, and signing — across all chains.

## Available Tools (8)

### Same-Chain Read-Only Tools

| Tool | Description |
|------|-------------|
| `oneinch_quote` | Get swap price quote (estimated output, gas, route). Requires `chain`. |
| `oneinch_tokens` | Search supported tokens on a network (address, symbol, decimals). Requires `chain`. |
| `oneinch_check_allowance` | Check if a token needs approval before swapping. Requires `chain`. |

### Same-Chain Write Tools (require wallet)

| Tool | Description |
|------|-------------|
| `oneinch_approve` | Approve ERC-20 token for 1inch router spending. Requires `chain`. |
| `oneinch_swap` | Execute a token swap via 1inch. Requires `chain`. |

### Cross-Chain Tools (Fusion+)

Fusion+ enables gasless cross-chain swaps using intent-based atomic swaps. Resolvers handle gas on both chains.

| Tool | Description |
|------|-------------|
| `oneinch_cross_chain_quote` | Get a cross-chain swap quote. Requires `src_chain`, `dst_chain`, `src_token`, `dst_token`, `amount`. |
| `oneinch_cross_chain_swap` | Execute a cross-chain swap (long-running). Requires `src_chain`, `dst_chain`, `src_token`, `dst_token`, `amount`. Optional `preset` (fast/medium/slow). **Recommend running via `sessions_spawn` as it can take up to 10 minutes.** |
| `oneinch_cross_chain_status` | Check status of a cross-chain swap order. Requires `order_hash`. |

## Tool Usage Examples

### Get a quote (price check only)

```
oneinch_quote(
  chain="arbitrum",
  src="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
  dst="<USDC_ADDRESS>",                                  # use oneinch_tokens to find
  amount="1000000000000000000"                            # 1 ETH in wei
)
```

### Search for a token

```
oneinch_tokens(chain="ethereum", search="USDC")
```

### Check if approval is needed

```
oneinch_check_allowance(chain="arbitrum", token_address="<TOKEN_ADDRESS>")
```

### Approve a token

```
oneinch_approve(chain="arbitrum", token_address="<TOKEN_ADDRESS>")
```

### Execute a swap

```
oneinch_swap(
  chain="arbitrum",
  src="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
  dst="<USDC_ADDRESS>",                                  # use oneinch_tokens to find
  amount="1000000000000000000",                           # 1 ETH
  slippage=1.0                                            # 1% slippage
)
```

### Cross-Chain: Get a quote

```
oneinch_cross_chain_quote(
  src_chain="ethereum",
  dst_chain="arbitrum",
  src_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH on Ethereum
  dst_token="<USDC_ADDRESS>",                                  # USDC on Arbitrum
  amount="1000000000000000000"                                  # 1 ETH in wei
)
```

### Cross-Chain: Execute a swap (recommend background task)

```
sessions_spawn(
  message="Execute cross-chain swap: oneinch_cross_chain_swap(src_chain='ethereum', dst_chain='arbitrum', src_token='0xEeee...EEeE', dst_token='<USDC_ADDR>', amount='1000000000000000000', preset='medium')"
)
```

### Cross-Chain: Check order status

```
oneinch_cross_chain_status(order_hash="<ORDER_HASH>")
```

## Common Workflows

**Step 0 for all workflows:** If the wallet policy is not yet active, load the wallet-policy skill and propose the standard wildcard policy before proceeding.

### Swap native ETH for USDC (no approval needed)

1. **Find token address:** `oneinch_tokens(chain="arbitrum", search="USDC")` — get the USDC address on Arbitrum
2. **Quote:** `oneinch_quote(chain="arbitrum", src="0xEeee...EEeE", dst="<USDC_ADDR>", amount="1000000000000000000")`
3. **Swap:** `oneinch_swap(chain="arbitrum", src="0xEeee...EEeE", dst="<USDC_ADDR>", amount="1000000000000000000")`

Native ETH does not require token approval.

### Swap USDC for WETH (approval required)

1. **Find token addresses:** `oneinch_tokens(chain="arbitrum", search="USDC")` and `oneinch_tokens(chain="arbitrum", search="WETH")`
2. **Check allowance:** `oneinch_check_allowance(chain="arbitrum", token_address="<USDC_ADDR>")`
3. **If needs_approval:** `oneinch_approve(chain="arbitrum", token_address="<USDC_ADDR>")`
4. **Swap:** `oneinch_swap(chain="arbitrum", src="<USDC_ADDR>", dst="<WETH_ADDR>", amount="1000000", slippage=1.0)`

### Price check only (no execution)

Use `oneinch_quote` to compare prices without executing. This does not require a wallet.

## Token Addresses

Token addresses differ between networks. Always use `oneinch_tokens(chain="<network>", search="<symbol>")` to discover the correct address for a token on a specific chain.

The native gas token address is the same on all EVM chains: `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`

## Amount Formatting (Wei Conversion)

All amounts must be in wei (the smallest unit of the token):

| Token | 1 Token in Wei | Formula |
|-------|---------------|---------|
| ETH (18 decimals) | `1000000000000000000` | amount × 10^18 |
| USDC (6 decimals) | `1000000` | amount × 10^6 |
| USDT (6 decimals) | `1000000` | amount × 10^6 |

Always check token decimals with `oneinch_tokens` before calculating amounts.

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown chain` | Invalid chain name | Use one of: ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis |
| `insufficient allowance` | Token not approved for 1inch router | Use `oneinch_approve` first |
| `insufficient balance` | Not enough tokens in wallet | Check balance with `wallet_balance` |
| `cannot estimate` | Route not found or amount too small | Try a different amount or token pair |
| `Policy violation` | Wallet policy blocks the transaction | Load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`). |
| `rate limit` | Too many API calls (1 RPS free tier) | Wait a moment and retry |

## Wallet Policy

For 1inch swaps to work, the wallet policy must be active. Use the standard wildcard policy (deny key export + allow `*`) — see Prerequisites section above.
