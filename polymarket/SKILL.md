---
name: polymarket
version: 2.0.0
description: Browse, analyze, and trade on Polymarket prediction markets using the official Rust CLI. Market discovery, live prices, orderbook analysis, position tracking, trading (limit/market orders), CTF token operations, contract approvals, and cross-chain bridge deposits. User-managed authentication via private key configuration.
tools:
  # Market Data (6)
  - polymarket_markets
  - polymarket_event
  - polymarket_tags
  - polymarket_price
  - polymarket_book
  - polymarket_leaderboard
  # Trading (8)
  - polymarket_place_limit_order
  - polymarket_place_market_order
  - polymarket_cancel_order
  - polymarket_cancel_all_orders
  - polymarket_get_orders
  - polymarket_get_balances
  - polymarket_get_positions
  - polymarket_get_trades
  # Approvals (2)
  - polymarket_check_approvals
  - polymarket_set_approvals
  # CTF Operations (3)
  - polymarket_ctf_split
  - polymarket_ctf_merge
  - polymarket_ctf_redeem
  # Bridge (2)
  - polymarket_bridge_deposit
  - polymarket_bridge_status
metadata:
  starchild:
    emoji: "🔮"
    skillKey: polymarket
    requires:
      bins: ["polymarket"]
      env: []  # User manages private key via polymarket wallet commands
    install:
      - kind: shell
        command: "curl -sSL https://raw.githubusercontent.com/Polymarket/polymarket-cli/main/install.sh | sh"
        bins: ["polymarket"]
        description: "Install Polymarket CLI (official Rust binary)"
user-invocable: true
disable-model-invocation: false
---

# Polymarket Prediction Markets

Browse, analyze, and trade on Polymarket — the world's largest prediction market platform on Polygon. Market prices represent crowd-implied probabilities (0.0-1.0 = 0%-100%) of real-world event outcomes.

Uses the official [Polymarket Rust CLI](https://github.com/Polymarket/polymarket-cli) for all operations.

## Overview

**What you can do:**
- 📊 **Market Discovery** - Browse active markets by volume, category, or recency
- 💰 **Price Analysis** - Get live probabilities, spreads, and liquidity depth
- 📈 **Position Tracking** - Monitor open positions with PnL
- 🔄 **Trading** - Place limit/market orders, manage positions
- 🔧 **CTF Operations** - Split, merge, and redeem conditional tokens on-chain
- ✅ **Approvals** - Manage contract approvals for trading
- 🌉 **Bridge Deposits** - Cross-chain deposits from EVM, Solana, Bitcoin

**Authentication:** Market data is public (no auth). Trading and on-chain operations require wallet configuration via `polymarket wallet` commands.

## Setup & Configuration

### 1. Install the Polymarket CLI

The skill installer automatically installs the binary via:
```bash
curl -sSL https://raw.githubusercontent.com/Polymarket/polymarket-cli/main/install.sh | sh
```

Or install manually:
- **Homebrew (macOS/Linux)**: `brew tap Polymarket/polymarket-cli && brew install polymarket`
- **Build from source**: `git clone https://github.com/Polymarket/polymarket-cli && cd polymarket-cli && cargo install --path .`

### 2. Configure Your Wallet

**Option A: Import existing private key**
```bash
polymarket wallet import 0xYOUR_PRIVATE_KEY
```

**Option B: Create new wallet**
```bash
polymarket wallet create
```

**Option C: Use environment variable**
```bash
export POLYMARKET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
```

The configuration is stored at `~/.config/polymarket/config.json`:
```json
{
  "private_key": "0x...",
  "chain_id": 137,
  "signature_type": "proxy"
}
```

⚠️ **IMPORTANT - No Agent Wallet Integration:**

This skill does **NOT** support agent-managed wallets (like Privy or other embedded wallet systems). You must provide your own Ethereum/Polygon private key that you control directly. The agent cannot access or export wallet keys on your behalf.

**Why?** The Polymarket CLI requires direct private key access to sign transactions. For security, this skill does not integrate with any wallet abstraction layers.

### 3. Set Contract Approvals (One-Time Setup)

Before trading, approve Polymarket contracts for USDC and CTF tokens:

**Check approval status:**
```
polymarket_check_approvals()
```

**Set all approvals** (requires MATIC for gas):
```
polymarket_set_approvals()
```

This sends 6 on-chain transactions and only needs to be done once per wallet.

## Tool Reference

### Market Discovery Tools (6) — No Auth Required

| Tool | Purpose | Required Params | Optional Params |
|------|---------|-----------------|-----------------|
| `polymarket_markets` | Browse/filter markets to get valid slugs | (none) | `status` (active/closed/all), `sort` (volume/liquidity/created_at), `limit`, `offset` |
| `polymarket_price` | Get live probability + token IDs | `market_id` (slug or condition ID) | (none) |
| `polymarket_event` | Get all sub-markets for an event | `event_id` | (none) |
| `polymarket_book` | Check orderbook depth & spread | `token_id` (from price) | (none) |
| `polymarket_tags` | List all market categories | (none) | (none) |
| `polymarket_leaderboard` | Top traders by profit | (none) | `period` (week/month/year/all), `order_by` (pnl/volume/trades), `limit` |

### Trading Tools (8) — Require Wallet Configuration

| Tool | Purpose | Required Params | Notes |
|------|---------|-----------------|-------|
| `polymarket_place_limit_order` | Place GTC limit order | `token_id`, `side` (buy/sell), `price` (0.01-0.99), `size` (shares) | Optional: `post_only` (maker-only) |
| `polymarket_place_market_order` | Place FOK market order | `token_id`, `side`, `amount` ($ for BUY, shares for SELL) | Optional: `price` (slippage limit) |
| `polymarket_get_positions` | View open positions + PnL | `address` (wallet address) | — |
| `polymarket_get_balances` | Check USDC balance | (none) | — |
| `polymarket_get_orders` | View open orders | (none) | Optional: `market` filter |
| `polymarket_get_trades` | Trade history | (none) | Optional: `limit` (default 50) |
| `polymarket_cancel_order` | Cancel specific order | `order_id` | — |
| `polymarket_cancel_all_orders` | Cancel ALL open orders | (none) | ⚠️ Use with caution |

### Contract Approval Tools (2) — One-Time Setup

| Tool | Purpose | Notes |
|------|---------|-------|
| `polymarket_check_approvals` | Check ERC-20/ERC-1155 approval status | Optional: `address` param |
| `polymarket_set_approvals` | Approve all contracts for trading | Sends 6 on-chain txs, requires MATIC gas |

### CTF Token Operation Tools (3) — On-Chain Operations

| Tool | Purpose | Required Params | Notes |
|------|---------|-----------------|-------|
| `polymarket_ctf_split` | Split USDC into outcome tokens | `condition_id` (0x...), `amount` (USDC) | Requires MATIC for gas |
| `polymarket_ctf_merge` | Merge tokens back to USDC | `condition_id`, `amount` | Must hold BOTH outcome tokens |
| `polymarket_ctf_redeem` | Redeem winning tokens after resolution | `condition_id` | Only for resolved markets |

### Bridge Deposit Tools (2) — Cross-Chain Deposits

| Tool | Purpose | Required Params | Notes |
|------|---------|-----------------|-------|
| `polymarket_bridge_deposit` | Get deposit addresses for bridging | `address` (Polygon destination) | Supports EVM, Solana, Bitcoin |
| `polymarket_bridge_status` | Check deposit status | `deposit_address` | Shows pending/completed deposits |

## Step-by-Step Workflows

### Workflow 1: Check Event Probability (Read-Only)

**User asks:** "What are the odds Trump wins the 2024 election?"

**Step 1:** Find the market
```
polymarket_markets(status="active", sort="volume", limit=20)
```

**Result:** Returns list with exact slugs:
```json
{
  "slug": "will-donald-trump-win-the-2024-us-presidential-election",
  "question": "Will Donald Trump win the 2024 US Presidential Election?",
  "outcomes": ["Yes", "No"]
}
```

**Step 2:** Get live probability
```
polymarket_price(market_id="will-donald-trump-win-the-2024-us-presidential-election")
```

**Result:** Returns current probability (e.g., 0.62 = 62% chance)

---

### Workflow 2: Deep Market Analysis

**User asks:** "How liquid is the Bitcoin $100K market?"

**Step 1:** Discover market
```
polymarket_markets(status="active", sort="volume", limit=10)
```

**Step 2:** Get price + token ID
```
polymarket_price(market_id="<exact-slug-from-step-1>")
```

**Result:** Returns `clobTokenIds` array (e.g., `["123456", "789012"]` for Yes/No)

**Step 3:** Check orderbook depth
```
polymarket_book(token_id="123456")
```

**Result:** Returns bid/ask levels, spread, liquidity depth

---

### Workflow 3: Place a Trade

**User asks:** "Buy $100 of Yes shares at 65%"

**Prerequisites:**
1. Wallet configured: `polymarket wallet import 0x...`
2. Approvals set: `polymarket_set_approvals()`

**Step 1:** Find market + get token ID
```
polymarket_price(market_id="<exact-slug>")
```

**Step 2:** Place limit order
```
polymarket_place_limit_order(
  token_id="123456",
  side="buy",
  price=0.65,
  size=153.85,  # $100 / 0.65
  post_only=false
)
```

**Alternative:** Market order (instant execution)
```
polymarket_place_market_order(
  token_id="123456",
  side="buy",
  amount=100,  # $100 to spend
  price=0.70   # worst acceptable price (slippage protection)
)
```

---

### Workflow 4: Split Collateral into Shares (On-Chain)

**User asks:** "Convert $50 USDC into Yes/No shares for a market"

**Prerequisites:**
1. Wallet configured and funded with USDC + MATIC (gas)
2. Approvals set

**Step 1:** Get condition ID from market
```
polymarket_price(market_id="<market-slug>")
```

**Result:** Extract `conditionId` or `condition_id` from response

**Step 2:** Split collateral
```
polymarket_ctf_split(
  condition_id="0xABC123...",
  amount=50
)
```

**Result:** Transaction hash, you now hold 50 Yes + 50 No shares

**Later:** Merge back to USDC (if holding both):
```
polymarket_ctf_merge(
  condition_id="0xABC123...",
  amount=50
)
```

---

### Workflow 5: Redeem Winning Position

**User asks:** "Market resolved, redeem my winning tokens"

**Step 1:** Check position
```
polymarket_get_positions(address="0xYOUR_ADDRESS")
```

**Step 2:** Redeem (requires resolved market)
```
polymarket_ctf_redeem(condition_id="0xABC123...")
```

**Result:** Winning tokens converted to USDC (1 token = $1)

---

### Workflow 6: Bridge Deposits from Other Chains

**User asks:** "How do I deposit USDC from Ethereum mainnet?"

**Step 1:** Get deposit addresses
```
polymarket_bridge_deposit(address="0xYOUR_POLYGON_ADDRESS")
```

**Result:** Deposit addresses for EVM chains, Solana, Bitcoin

**Step 2:** Send assets to the provided deposit address (via wallet)

**Step 3:** Monitor status
```
polymarket_bridge_status(deposit_address="<address-from-step-1>")
```

**Result:** Shows pending/completed deposits

---

## Interpreting Prices

Polymarket prices = probabilities. Each share pays $1 if the outcome occurs.

| Price Range | Interpretation |
|-------------|---------------|
| $0.90-$1.00 | Near-certain — strong consensus |
| $0.70-$0.89 | Strong consensus — likely to happen |
| $0.50-$0.69 | Lean yes, significant uncertainty |
| $0.30-$0.49 | Lean no, but uncertain |
| $0.01-$0.29 | Unlikely — market thinks probably not |

## Spread & Liquidity Analysis

| Spread | Meaning |
|--------|---------|
| < $0.02 | Tight — reliable price signal, high confidence |
| $0.02-$0.05 | Normal — decent liquidity |
| $0.05-$0.10 | Wide — lower confidence, less liquid |
| > $0.10 | Very wide — unreliable, thin market |

Check `polymarket_book` to see actual depth. A tight spread with shallow depth can still be unreliable.

## Multi-Outcome & Negative Risk Markets

- **Binary markets**: Yes/No — prices sum to ~$1.00
- **Multi-outcome**: 3+ outcomes (e.g. "Who wins?") — all outcomes sum to ~$1.00
- **Negative risk (`neg_risk=true`)**: Market uses a special mechanism where shares are minted as a group. Prices still represent probabilities.

Always iterate all outcomes — never hardcode Yes/No.

## Common Patterns

- **Sentiment check**: Prediction prices as leading indicators for crypto/political events
- **Event risk assessment**: Combine prediction market odds with crypto price data for risk analysis
- **Contrarian signals**: Extreme probabilities ($0.95+) with declining volume may indicate complacency
- **Smart money tracking**: Leaderboard reveals top traders and their performance

## Troubleshooting

### CLI Installation Issues

**Error: "Polymarket CLI not found"**
- Install via: `curl -sSL https://raw.githubusercontent.com/Polymarket/polymarket-cli/main/install.sh | sh`
- Or use Homebrew: `brew tap Polymarket/polymarket-cli && brew install polymarket`
- Verify installation: `polymarket --version`

### Wallet Configuration Issues

**Error: "Failed to derive credentials" or "No private key configured"**
- Import your private key: `polymarket wallet import 0xYOUR_KEY`
- Or use environment variable: `export POLYMARKET_PRIVATE_KEY=0xYOUR_KEY`
- Check configuration: `polymarket wallet show`

### Trading Errors

| Error | Cause | Solution |
|-------|-------|----------|
| **"Insufficient allowance"** | Contracts not approved | Run `polymarket_set_approvals()` |
| **"Insufficient balance"** | Not enough USDC | Deposit USDC to your wallet |
| **"Order failed"** | Invalid price/size | Check token_id is correct, price is 0.01-0.99 |
| **"Transaction failed"** (CTF ops) | Out of MATIC for gas | Add MATIC to your Polygon wallet |

### Market Discovery Issues

| Error | Cause | Solution |
|-------|-------|----------|
| **"Market not found"** | Slug typo or market doesn't exist | Use `polymarket_markets()` to get exact slug |
| **Empty results** | Too restrictive filters | Broaden search criteria |

### On-Chain Operation Issues

**Error: "Insufficient funds for gas"**
- CTF operations (split/merge/redeem) and approvals require MATIC on Polygon
- Get MATIC: Bridge from other chains or use faucets for testnet

**Error: "Cannot merge - insufficient balance"**
- Merging requires holding BOTH outcome tokens in equal amounts
- Check your positions: `polymarket_get_positions(address="0xYOUR_ADDRESS")`

## Security Best Practices

🔒 **Private Key Management:**
- Never share your private key
- Store config file (`~/.config/polymarket/config.json`) securely
- Use environment variables for temporary sessions
- Consider using a dedicated trading wallet with limited funds

⚠️ **Trading Safety:**
- Start with small amounts to test the integration
- Always verify market details before placing orders
- Use `post_only` for limit orders to avoid unexpected fills
- Set slippage limits on market orders via the `price` parameter

🔐 **On-Chain Operations:**
- Verify condition IDs carefully before CTF operations
- Keep some MATIC for gas fees (CTF ops typically cost ~$0.10-0.50)
- Test approvals on small amounts first

## CLI Command Reference

For advanced users who want to use the CLI directly:

**Market discovery:**
- `polymarket markets list --limit 10`
- `polymarket markets search "bitcoin"`
- `polymarket markets get <slug>`

**Trading:**
- `polymarket clob create-order --token <id> --side buy --price 0.5 --size 10`
- `polymarket clob orders`
- `polymarket clob balance --asset-type collateral`

**CTF operations:**
- `polymarket ctf split --condition 0x... --amount 10`
- `polymarket ctf merge --condition 0x... --amount 10`
- `polymarket ctf redeem --condition 0x...`

**Approvals:**
- `polymarket approve check`
- `polymarket approve set`

**JSON output (for scripting):**
- Add `-o json` to any command: `polymarket -o json markets list --limit 5`

See full CLI docs: https://github.com/Polymarket/polymarket-cli

## Additional Resources

- **Official CLI Repo**: https://github.com/Polymarket/polymarket-cli
- **Polymarket Platform**: https://polymarket.com
- **Documentation**: https://docs.polymarket.com
- **Discord**: https://discord.gg/polymarket
