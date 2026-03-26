---
name: "polymarket"
version: 2.4.0
description: Place real bets on Polymarket prediction markets using the agent wallet. Buy/sell outcome tokens, check balances, manage orders. Requires USDC.e (bridged USDC) on Polygon and wallet policy allowing EIP-712 signing. 🚀 Optimized workflow + auto VPN detection!
author: starchild
tags: [polymarket, trading, prediction-markets, polygon, defi]
tools:
  - polymarket_lookup
  - polymarket_search
  - polymarket_quick_prepare
  - polymarket_get_positions
  - polymarket_get_balance
  - polymarket_get_orders
  - polymarket_get_trades
  - polymarket_post_order
  - polymarket_orderbook
  - polymarket_rr_analysis
  - polymarket_cancel_order
  - polymarket_cancel_all
  - polymarket_prepare_order
  - polymarket_auth
  - wallet_sign_typed_data
  - wallet_transfer
  - web_search
  - web_fetch
metadata:
  starchild:
    emoji: "🎲"
    skillKey: polymarket-trade
    requires:
      env:
        - POLY_API_KEY
        - POLY_SECRET
        - POLY_PASSPHRASE
        - POLY_WALLET
        # VPN is auto-detected (no config needed!)
---

# Polymarket Trading Skill

Trade on Polymarket CLOB using the agent's Polygon wallet in **EOA mode** (signature_type=0).

## Architecture

| Mode | sig_type | How it works | Gas? |
|---|---|---|---|
| **EOA (we use this)** | `0` | Agent wallet = signer AND maker. No proxy. | Yes — POL for one-time approvals |
| Safe/Proxy | `2` | Gnosis Safe proxy holds funds, EOA signs. | No (relayer pays) |

**Why EOA?** Simpler — no proxy deployment, no relayer. Only gas cost is ~$0.01 POL for one-time approvals. CLOB orders are gasless after that.

## Quick Start

### For Users: "I want to trade on Polymarket"

Just say **"I want to trade on Polymarket"** and the agent will:

1. ✅ Check if you have credentials (auto-detects from `.env`)
2. ✅ If not, walk you through creating them (one signature, saves automatically)
3. ✅ Check your USDC.e balance on Polygon (swap from native USDC if needed)
4. ✅ You're ready to trade!

**That's it!** No manual config needed. The agent handles everything.

**Note:** If you have native USDC, the agent will help you swap to USDC.e first.

---

## ⚠️ CRITICAL: USDC.e Required (Not Native USDC)

**Polymarket ONLY accepts USDC.e (bridged USDC) on Polygon.**

| Token | Address | Works with Polymarket? |
|-------|---------|------------------------|
| **USDC.e (bridged)** | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | ✅ YES |

**If you have native USDC:** You must swap it to USDC.e first using 1inch or another DEX.

**Why?** Polymarket's contracts predate Circle's native USDC deployment on Polygon. The USDC.e address is hardcoded into their exchange contracts and cannot be changed.

---

## VPN Auto-Detection (Zero Configuration!)

**No setup required!** The skill automatically handles geo-blocking:

### How It Works

1. **First request**: Tries direct access (fast path)
2. **If 403 geo-block detected**:
   - Automatically tests all VPN regions in parallel (br, ar, mx, my, th, au, za)
   - Picks the fastest working region
   - Retries the request through VPN
   - Caches the working region to `.polymarket_vpn_cache.json`
3. **Subsequent requests**: Uses cached VPN region automatically

**Zero configuration, zero manual intervention!**

### Optional Overrides

Only needed for debugging or advanced use:

```bash
# Force a specific VPN region (skip auto-detection)
POLY_VPN_REGION=br  # Options: br, ar, mx, my, th, au, za

# Force direct access (disable VPN even on 403)
POLY_DISABLE_VPN=true
```

### Performance

- **Not geo-blocked**: Direct access (~0.5s per request)
- **First request when geo-blocked**: Auto-detection + retry (~3-5s one-time cost)
- **Subsequent requests**: Cached VPN region (~0.7s per request)

**Cache persists across restarts** - VPN selection happens once and works forever!

---

## First-Time Setup (Automatic)

When you first use Polymarket tools, the agent will automatically:

### 1. Create API Credentials

The `polymarket_auth` tool will:
- Get your wallet address
- Build an EIP-712 `ClobAuth` message
- Ask you to sign it (free, no gas)
- Submit to Polymarket CLOB API
- **Save credentials to `.env` automatically**
- Credentials work **immediately** (no restart needed!)

**Technical Details:**

Domain: `{ name: "ClobAuthDomain", version: "1", chainId: 137, verifyingContract: "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E" }`
Types: `ClobAuth: [address, timestamp(string), nonce(uint256), message(string)]`
Message: `{ address: WALLET, timestamp: NOW, nonce: "0", message: "This message attests that I control the given wallet" }`

**Flow:**
1. Sign with `wallet_sign_typed_data`
2. POST `https://clob.polymarket.com/auth/api-key` with L1 auth headers
3. Save to `.env`: `POLY_API_KEY`, `POLY_SECRET`, `POLY_PASSPHRASE`, `POLY_WALLET`

### 2. Fund Your Wallet (If Needed)
Send to the agent wallet address on Polygon:
- **USDC.e (bridged USDC)** `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` — betting bankroll
  - ⚠️ **NOT native USDC** (`0x3c499c...`)! Polymarket only accepts USDC.e
  - If you have native USDC, swap it first using the 1inch skill
- **POL** (~1 POL / ~$0.20) — gas for approval txs

### 4. Approve USDC (One-Time, needs POL)
Approve both CTF Exchange contracts to spend USDC (max allowance):

```python
from eth_abi import encode
from eth_utils import function_signature_to_4byte_selector
sel = function_signature_to_4byte_selector("approve(address,uint256)")
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC.e (bridged), NOT native USDC!
# Approval 1: CTF Exchange
data1 = sel + encode(['address','uint256'], ['0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E', 2**256-1])
# wallet_transfer(to=USDC_E, amount="0", chain_id=137, data="0x"+data1.hex())
# Approval 2: CTF Exchange Neg-Risk
data2 = sel + encode(['address','uint256'], ['0xC5d563A36AE78145C45a50134d48A1215220f80a', 2**256-1])
# wallet_transfer(to=USDC_E, amount="0", chain_id=137, data="0x"+data2.hex())
```

### 4. Verify Setup
```
polymarket_get_balance()
```
Should show your USDC balance and allowance. You're ready to trade!

---

## How Credentials Work

**New Dynamic Loading (No Restart Needed!):**
- Credentials are read from `.env` **every time** a tool is called
- When `polymarket_auth` saves credentials, they work **immediately**
- No container restart required
- No browser refresh needed

**Where credentials are stored:**
- `/data/workspace/.env` — read automatically by all tools

**Required credentials:**
```
POLY_API_KEY=...
POLY_SECRET=...
POLY_PASSPHRASE=...
POLY_WALLET=0xYour_Address
```

### Wallet Policy
Agent needs: `eth_signTypedData_v4` (order signing) + `eth_sendTransaction` on chain 137 (approvals).

---

## API Endpoints

Polymarket has three separate APIs for different purposes:

| API | Base URL | What it handles | Auth? | VPN? |
|-----|----------|-----------------|-------|------|
| **CLOB API** | `clob.polymarket.com` | Orders, balance, orderbook, pricing | ✅ HMAC L2 | ⚠️ Optional |
| **Data API** | `data-api.polymarket.com` | Positions, trades (historical/settled) | ❌ Public | ❌ No |
| **Gamma API** | `gamma-api.polymarket.com` | Markets, events, search | ❌ Public | ❌ No |

### Key Differences: EOA Mode

We use **EOA mode (signature_type=0)** which means:
- ❌ **NO proxy wallet** - Your raw wallet is the maker
- ✅ All trades execute directly from your wallet
- ✅ All positions belong to your wallet address

**Positions** (`polymarket_get_positions`):
- Uses public **Data API** (`data-api.polymarket.com/positions?user={wallet}`)
- Shows settled/finalized positions
- No auth needed, no VPN needed
- Query parameter: `user={your_wallet_address}`

**Trades** (`polymarket_get_trades`):
- Uses public **Data API** (`data-api.polymarket.com/trades?user={wallet}`)
- Shows historical trade activity
- No auth needed, no VPN needed
- Query parameter: `user={your_wallet_address}`

**Orders** (`polymarket_get_orders`):
- Uses authenticated **CLOB API** (`clob.polymarket.com/data/orders`)
- Shows currently open orders
- Requires L2 auth (VPN optional, only if geo-blocked)

**Balance** (`polymarket_get_balance`):
- Uses authenticated **CLOB API** (`clob.polymarket.com/balance-allowance`)
- Shows USDC balance and allowances
- Requires L2 auth (VPN optional, only if geo-blocked)

---

## Contracts (Polygon)

| Contract | Address | Notes |
|---|---|---|
| CTF Exchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E` | Main exchange |
| CTF Exchange (neg-risk) | `0xC5d563A36AE78145C45a50134d48A1215220f80a` | For neg-risk markets |
| **USDC.e (bridged)** | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | ✅ Supported |

## ⚠️ MANDATORY: User Confirmation Before Betting

**NEVER place a bet without explicit user confirmation.** Always:
1. Research & analyze → present findings
2. Suggest bet with R/R → user reviews
3. User requests changes → adjust
4. **User explicitly confirms** → ONLY THEN execute

## Available Tools

### Market Discovery
- `polymarket_lookup` - Look up market from URL or slug
- `polymarket_search` - Search for markets
- `polymarket_orderbook` - Analyze orderbook depth
- `polymarket_rr_analysis` - Risk/reward analysis

### Trading
- 🚀 **`polymarket_quick_prepare`** - **FAST** one-shot preparation (balance + orderbook + R/R + order prep in ONE call)
- `polymarket_prepare_order` - Prepare order for signing (manual workflow)
- `polymarket_post_order` - Post signed order
- `polymarket_cancel_order` - Cancel specific order
- `polymarket_cancel_all` - Cancel all orders
- `polymarket_get_balance` - Check USDC balance
- `polymarket_get_orders` - List open orders
- `polymarket_get_positions` - View positions
- `polymarket_get_trades` - Trade history

### Authentication
- `polymarket_auth` - Create API credentials (one-time setup)

## Workflow: Link → Bet

### 🚀 FAST Workflow (Recommended)

Use `polymarket_quick_prepare` for speed - combines 4+ operations into ONE tool call:

**Steps:**
1. **Lookup market** → `polymarket_lookup(url)`
2. **Quick prepare** → `polymarket_quick_prepare(token_id="123456", side="YES", size_usd=10)`
   - ✅ Checks balance
   - ✅ Analyzes orderbook
   - ✅ Calculates R/R
   - ✅ Prepares order
   - Returns everything in one response!
3. **Sign** → `wallet_sign_typed_data(eip712)`
4. **Post** → `polymarket_post_order(token_id, signature, meta)`

**Total: 4 tool calls vs 8+ in manual workflow** ⚡

---

### Manual Workflow (Original)

### 1. Market Lookup
```
polymarket_lookup(url_or_slug="https://polymarket.com/event/...")
```

### 2. Research
- Read resolution criteria, end date, sources
- `web_search` for news, expert opinions, data
- Assess market price vs estimated fair probability
- Present: overview, prices, key facts, probability estimate, edge

### 3. Orderbook & R/R
```
polymarket_orderbook(token_id="123456")
polymarket_rr_analysis(token_id="123456", side="YES", size_usd=20)
```

### 4. Present Suggested Bet (WAIT for confirmation)
```
📊 Suggested Bet:
  Market: "Will X happen?"
  Side: YES @ $0.35 (market: 35%, est: 55%)
  Size: $20 → 57.14 tokens
  Win: +$37.14 | Lose: -$20.00 | R/R: 1:1.86
```

### 5. Execute (ONLY after confirmation)
```
# a. Check balance
polymarket_get_balance()

# b. Prepare order (outputs domain/types/message/meta JSON)
polymarket_prepare_order(token_id="123456", side="BUY", price=0.35, size=57.14)

# c. Sign with wallet_sign_typed_data (primaryType: "Order")

# d. Post signed order
polymarket_post_order(token_id="123456", signature="0x...", meta={...})

# e. Verify
polymarket_get_orders()
```

---

## Troubleshooting

### ❌ "I have native USDC, not USDC.e"

**Symptom:** `polymarket_get_balance()` shows $0 even though you have USDC in wallet.

**Cause:** You have Circle's native USDC (`0x3c499c...`) instead of bridged USDC.e (`0x2791...`).

**Fix:** Swap using 1inch skill:
1. Check wallet balance to confirm you have native USDC
2. Use `1inch` skill to swap native USDC → USDC.e
3. Verify USDC.e balance before trading

### ❌ "Not enough balance" error after approvals

**Symptom:** Order post fails with balance error even after approval transactions succeeded.

**Cause:** 10-15 second sync delay between on-chain approval and CLOB API recognition.

**Fix:**
1. Wait 15-30 seconds after approval transactions complete
2. Run `polymarket_get_balance()` to verify balance shows correctly
3. If still failing, wait another 30 seconds and retry order post

### ❌ Order post fails with signature error

**Symptom:** `polymarket_post_order` fails with "invalid signature" or similar error.

**Cause:** Order expired (timestamp too old) or wrong format.

**Fix:**
1. Always use `polymarket_quick_prepare` or `polymarket_prepare_order` - never manually construct
2. Sign and post immediately - orders expire after a few minutes
3. Verify `signature_type=0` for EOA mode

### ❌ Can't find market or token_id

**Symptom:** Search returns no results or wrong market.

**Fix:**
1. Use full Polymarket URL: `polymarket_lookup("https://polymarket.com/event/...")`
2. Try multiple search terms: `polymarket_search("2026 FIFA World Cup winner")`
3. Check Polymarket website for exact market name

### ❌ Approval transaction fails

**Symptom:** Approval transaction reverts or fails.

**Cause:** Insufficient POL for gas.

**Fix:**
1. Check POL balance: `wallet_get_balance(chain_id=137)`
2. Need ~0.5-1 POL for approvals (~$0.10-$0.20)
3. Bridge POL from another chain if needed

### ⚠️ polymarket_get_balance shows $0

**In EOA mode, this can be NORMAL.**

**Why:** USDC.e stays in your wallet until orders fill. Polymarket's balance endpoint shows their internal ledger, which updates after trades execute.

**What to verify:**
1. ✅ You have USDC.e in wallet: Check with `wallet_get_balance(chain_id=137, token_address="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")`
2. ✅ Approvals are set: Check allowances for both CTF Exchange contracts
3. ✅ Ready to trade: USDC.e gets pulled automatically when orders fill

**When it's a problem:** If you've already filled orders and balance still shows $0, then there's a sync issue - wait 30s and check again.

---

## Notes
- **USDC.e ONLY**: Polymarket accepts `0x2791Bca1...` (USDC.e), NOT native USDC `0x3c499c...`
- Prices = probabilities: $0.55 = 55% implied, costs $0.55/token, pays $1 if correct
- tick_size: 0.01 or 0.001 (from market data — always check)
- neg_risk markets use CTF_EXCHANGE_NEG (`0xC5d563A36AE78145C45a50134d48A1215220f80a`)
- Orders are GTC (Good-Til-Canceled) by default
- **Fee rate auto-queries from market** (typically 1000 bps = 10% maker fee)
- Min order ~5 tokens (varies by market)
- EOA = signature_type 0
- **Balance sync**: Wait 15-30s after approvals before posting orders
