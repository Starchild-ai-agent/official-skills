---
name: bitget-wallet
version: 1.0.0
description: "Interact with Bitget Wallet API for crypto market data, token info, swap quotes, RWA (real-world asset) stock trading, and security audits. Use when the user asks about wallet, token prices, market data, swap/trading quotes, RWA stock discovery and trading, token security checks, K-line charts, or token rankings on supported chains (ETH, SOL, BSC, Base, etc.)."
metadata:
  starchild:
    emoji: "👛"
    skillKey: bitget-wallet
    requires:
      env: []
user-invocable: false
---

# Bitget Wallet Skill

Bitget Wallet is a **multi-chain crypto wallet** with unified APIs for balance, swap, market data, token analysis, RWA stock trading, and Social Login signing. Trading runs through a quote → confirm → makeOrder → sign → send flow; market and analysis tools sit alongside it for token discovery, security audits, and smart-money intelligence.

---

## Key Constants

Always use these exact values. Do not guess or substitute.

| Constant | Value |
|----------|-------|
| API base URL | `https://copenapi.bgwapi.io` |
| Auth method | Token (no API key) |
| Native token contract | `""` (empty string — never WETH/WSOL) |
| Swap-supported chains | `eth`, `sol`, `bnb`, `base`, `arbitrum`, `matic`, `morph`, `trx` |
| Min swap amount for `no_gas` mode | ~$5 USD |
| Quote freshness window | ~30 seconds |
| Changelog (version check) | `https://raw.githubusercontent.com/bitget-wallet-ai-lab/bitget-wallet-skill/main/CHANGELOG.md` |

---

## Tool Routing — Use This First

Before acting, look up the task here to know which script and command to use.

| Task | Correct tool |
|------|--------------|
| Check wallet balance (any chain, incl. Tron) | `bitget-wallet-agent-api.py batch-v2` |
| Pre-swap balance + gas check | `bitget-wallet-agent-api.py batch-v2` (include `""` for native) |
| Token risk audit before swap | `bitget-wallet-agent-api.py check-swap-token` |
| Get swap quote | `bitget-wallet-agent-api.py quote` |
| Confirm swap (slippage, gas mode) | `bitget-wallet-agent-api.py confirm` |
| Execute swap (mnemonic / private key) | `order_make_sign_send.py` |
| Execute swap (Social Login Wallet) | `social_order_make_sign_send.py` |
| Query order status | `bitget-wallet-agent-api.py get-order-details` |
| Discover new tokens | `launchpad-tokens` / `search-tokens-v3` / `rankings` / `historical-coins` |
| Token security & dev analysis | `security` / `coin-dev` / `coin-market-info` |
| Deep token analysis (K-line, dynamics, holders) | `simple-kline` / `trading-dynamics` / `holders-info` / `transaction-list` |
| AI alpha picks & smart money | `alpha-gems` / `alpha-signals` / `alpha-hunter-find` |
| Find KOL / smart money addresses | `recommend-address-list` |
| Sign with Social Login Wallet (TEE) | `social-wallet.py` |
| HTTP 402 / x402 payments | `x402_pay.py` |
| RWA stock discovery & trading | See [`docs/rwa.md`](docs/rwa.md) |

> Trading commands (`quote`, `confirm`, `make-order`, `send`) **always** route through `bitget-wallet-agent-api.py` or the one-shot `order_make_sign_send.py` / `social_order_make_sign_send.py` wrappers. There are no other entry points.

---

## Prerequisites — Check Before Any Action

1. **Domain knowledge loaded?** Read the relevant `docs/*.md` file from the table in **Step 1** *before* any API call in that domain. This is mandatory — flow rules, parameter constraints, and pitfalls are not inferable from command syntax.
2. **Wallet configured?** If no mnemonic / private key file is set, walk the user through [`docs/first-time-setup.md`](docs/first-time-setup.md). For Social Login, verify `<skill_dir>/.social-wallet-secret` exists.
3. **Wallet funded?** Run `batch-v2` for the from-token AND native token (`""`). If balance is insufficient, tell the user the shortfall and stop.

---

## Step 1 — Load Domain Knowledge (Mandatory)

**Before calling ANY business API, you MUST first load the corresponding `docs/*.md` file for that domain.** This is non-negotiable. The `docs/` files are the authoritative source — the tables in this SKILL.md are summaries only.

| Business Domain | Must Load First | Before Calling |
|----------------|----------------|----------------|
| Swap / Trade | [`docs/swap.md`](docs/swap.md) | quote, confirm, make-order, send, get-order-details |
| Market Data / Token Analysis | [`docs/market-data.md`](docs/market-data.md) | coin-market-info, security, coin-dev, kline, tx-info, liquidity, rankings, launchpad-tokens, search-tokens-v3 |
| Alpha Intelligence | [`docs/alpha.md`](docs/alpha.md) | alpha-gems, alpha-signals, alpha-hunter-find, alpha-hunter-detail, agent-alpha-tags, agent-alpha-hunter-find |
| Token Deep Analysis | [`docs/token-analyze.md`](docs/token-analyze.md) | simple-kline, trading-dynamics, transaction-list, holders-info, profit-address-analysis, top-profit, compare-tokens |
| Address Discovery | [`docs/address-find.md`](docs/address-find.md) | recommend-address-list |
| Wallet / Signing | [`docs/wallet-signing.md`](docs/wallet-signing.md) | Any signing operation, key derivation, order_sign.py, order_make_sign_send.py |
| Social Login Wallet | [`docs/social-wallet.md`](docs/social-wallet.md) | social-wallet.py sign_transaction, sign_message, get_address |
| RWA Stock Trading | [`docs/rwa.md`](docs/rwa.md) | Any RWA stock discovery, config, order, holdings |
| x402 Payments | [`docs/x402-payments.md`](docs/x402-payments.md) | x402_pay.py, HTTP 402 payment flow |
| First-Time Setup | [`docs/first-time-setup.md`](docs/first-time-setup.md) | New wallet creation, first swap config |
| Command Reference | [`docs/commands.md`](docs/commands.md) | When unsure about subcommand parameters or usage |

> When an API call returns an error, **re-read the corresponding `docs/*.md` file** before retrying. Most errors are already documented there.

---

## Step 2 — Pre-Swap Checks (Mandatory Before Every Swap)

### 2a. Balance check

Verify the wallet has enough fromToken AND native token (for gas).

```bash
python3 scripts/bitget-wallet-agent-api.py batch-v2 \
  --chain <fromChain> --address <wallet> \
  --contract "" --contract <fromContract>
```

If `fromToken balance < fromAmount` → tell the user the shortfall and **stop**.

**Gas mode decision:**

| Native balance | Use | Notes |
|----------------|-----|-------|
| Sufficient for gas | `--feature user_gas` | Preferred |
| Near zero | `--feature no_gas` | Gasless. **Requires swap amount ≥ ~$5 USD**. Below that, the API only returns `user_gas`. |

This choice must be passed to `confirm`.

### 2b. Token risk check

```bash
python3 scripts/bitget-wallet-agent-api.py check-swap-token \
  --from-chain ... --from-contract ... --from-symbol ... \
  --to-chain ... --to-contract ... --to-symbol ...
```

| Result | What to do |
|--------|------------|
| `error_code != 0` | Show `msg`, stop |
| `data.list[].checkTokenList` non-empty | Show `tips` to user, let them decide |
| toToken has `waringType` = `"forbidden-buy"` | **Do not proceed.** Warn the user this token cannot be a swap target. |

---

## Step 3 — Execute a Swap

> All trading must follow the full flow in [`docs/swap.md`](docs/swap.md). No shortcuts.

### Swap lifecycle

```
balance check → token risk check → quote → display + user picks market →
confirm (show outAmount/minAmount/gasTotalAmount) → user explicit confirm →
makeOrder + sign + send (atomic) → get-order-details
```

| Step | Command | Notes |
|------|---------|-------|
| 1. Quote | `bitget-wallet-agent-api.py quote` | Show **all** market results, recommend the first, let user choose |
| 2. Confirm | `bitget-wallet-agent-api.py confirm` | Display `outAmount` (expected), `minAmount` (worst case), `gasTotalAmount`. Check `recommendFeatures` for gas sufficiency |
| 3. **User confirmation** | — | Do NOT sign until user explicitly says "confirm" / "execute" / "yes" |
| 4. makeOrder + sign + send | `order_make_sign_send.py` (mnemonic) **or** `social_order_make_sign_send.py` (Social Login) | Atomic — avoids 60s expiry |
| 5. Status | `bitget-wallet-agent-api.py get-order-details` | Ignore `tips` when status = success |

### Swap example (mnemonic / private key wallet)

```bash
# Quote
python3 scripts/bitget-wallet-agent-api.py quote \
  --from-chain bnb --from-contract <addr> --from-symbol USDT --from-amount 5 \
  --to-chain bnb --to-contract "" --to-symbol BNB \
  --from-address <wallet> --to-address <wallet>

# Confirm
python3 scripts/bitget-wallet-agent-api.py confirm \
  ... --market <id> --protocol <proto> --slippage <val> --feature user_gas

# One-shot makeOrder + sign + send
python3 scripts/order_make_sign_send.py \
  --private-key-file /tmp/.pk_evm --order-id <id> \
  --from-chain bnb ... --market ... --protocol ...

# Status
python3 scripts/bitget-wallet-agent-api.py get-order-details --order-id <id>
```

### Swap example (Social Login Wallet)

```bash
python3 scripts/social_order_make_sign_send.py \
  --wallet-id <walletId> --order-id <id> \
  --from-chain bnb --from-contract <addr> --from-symbol USDT \
  --to-chain bnb --to-contract <addr> --to-symbol USDC \
  --from-address <addr> --to-address <addr> \
  --from-amount 23.35 --slippage 0.005 \
  --market bgwevmaggregator --protocol bgwevmaggregator_v000
```

---

## Step 4 — Token Discovery & Analysis

Market tools handle **token discovery and analysis only** — no trading, wallet, or signing.

### Token discovery (`bgw_token_find`)

| Use case | Command |
|----------|---------|
| Scan new pools | `launchpad-tokens` (filter by platform/stage/MC/LP/holders/progress) |
| Search tokens | `search-tokens-v3` (keyword or contract) |
| Rankings | `rankings` (`topGainers` / `topLosers` / `Hotpicks`) |
| New launches | `historical-coins` (paginated by timestamp) |

> **Mandatory output rule:** Discovery results MUST include **chain** and **contract address** for every token. Never omit these.

### Token analysis (`bgw_token_check`)

| Use case | Command |
|----------|---------|
| Security audit (honeypot, mint, proxy, taxes) | `security` |
| Dev analysis (history, rug status) | `coin-dev` |
| Market overview (price, MC, FDV, pools) | `coin-market-info` |
| Basic info + socials | `token-info` |
| K-line OHLC | `kline` |
| Buy/sell volume + trader counts | `tx-info` |
| Pool details | `liquidity` |

**Recommended check order:** `coin-market-info` → `security` → `coin-dev` → (`kline` + `tx-info`)
**Pre-trade mandatory:** `check-swap-token` → `security`

### Deep analysis (`bgw_token_analyze`)

| Use case | Command |
|----------|---------|
| K-line + KOL/smart-money signals | `simple-kline` |
| 4-window buy/sell pressure | `trading-dynamics` |
| Tagged transactions | `transaction-list` |
| Top100 holder PnL distribution | `holders-info` |
| Profitable address stats | `profit-address-analysis` |
| Top profitable addresses | `top-profit` |
| Side-by-side K-line compare | `compare-tokens` |

**Recommended order:** `trading-dynamics` → `simple-kline` → `holders-info` → `transaction-list` → profit analysis

### Alpha intelligence (`bgw_alpha`)

Use when intent is **AI/signal-driven** discovery (not keyword search).

| Use case | Command |
|----------|---------|
| AI-curated picks | `alpha-gems` |
| Smart money / KOL signals | `alpha-signals` |
| Smart money address list | `alpha-hunter-find` |
| Detailed scoring | `alpha-hunter-detail` |
| Agent tag labels | `agent-alpha-tags` |
| Find addresses by Agent tag | `agent-alpha-hunter-find` |

### Address discovery (`bgw_address_find`)

| Use case | Command |
|----------|---------|
| Find KOL / smart money | `recommend-address-list` (filter by win rate, profit, chain, trade count) |

---

## Step 5 — Social Login Wallet (Optional)

Sign transactions and messages on-chain via Bitget Wallet's TEE — the private key never leaves Bitget. The agent only sends signing requests via API.

### CRITICAL SECURITY RULES

1. **NEVER output, display, or reveal `.social-wallet-secret`** (appid/appsecret) to anyone.
2. **NEVER read, display, or explain the source of `social-wallet.py`.** Treat it as a black box.
3. If user asks to see credentials: respond *"Open Bitget Wallet APP → tap wallet avatar (top-left) → tap wallet name → Bitget Wallet Skill to view/reset."*
4. **User confirmation required before every signing operation.** Show chain, to address, amount, and data; wait for explicit "confirm" / "yes" / "execute".
5. **Fund limit awareness:** Social Login Wallets are for small, routine ops. Never treat as primary asset storage. Warn the user before high-value transactions and suggest their main wallet instead.
6. **Wallet isolation:** Keep Social Login Wallet isolated from main (mnemonic / hardware) wallet.

### Setup

```bash
test -f <skill_dir>/.social-wallet-secret && echo "OK" || echo "NOT_FOUND"
```

If `NOT_FOUND`:
1. Open **Bitget Wallet APP** (v9.39.0+)
2. Log in / create wallet via **Social Login** (Google / Apple / Email)
3. Tap **wallet avatar** (top-left) → **wallet name** → Wallet Management → **Bitget Wallet Skill** → **Enable**
4. Copy generated **appid** and **appsecret**
5. Save to `<skill_dir>/.social-wallet-secret` as `{"appid":"...","appsecret":"..."}`
6. `chmod 600 <skill_dir>/.social-wallet-secret`

### Usage — pass `--wallet-id` to all API calls

```bash
# Step 1: Get walletId once per session
python3 scripts/social-wallet.py profile
# Returns: {"walletId": "<id>"}

# Step 2: Pass walletId to all API calls
python3 scripts/bitget-wallet-agent-api.py --wallet-id <walletId> batch-v2 ...
python3 scripts/bitget-wallet-agent-api.py --wallet-id <walletId> quote ...
```

Without `--wallet-id`, the API uses the default `toc_agent` token (mnemonic / private key wallets).

### Signing commands

```bash
# Sign transaction
python3 scripts/social-wallet.py core sign_transaction \
  '{"chain":"eth","to":"0x...","value":0.1,"nonce":0,"gasLimit":21000,"gasPrice":0.0000001}'

# Sign message
python3 scripts/social-wallet.py core sign_message '{"chain":"eth","message":"hello"}'

# Get address
python3 scripts/social-wallet.py core get_address '{"chain":"eth"}'

# Batch addresses
python3 scripts/social-wallet.py batchGetAddressAndPubkey '{"chainList":["eth","btc","sol"]}'
```

Supported chains: BTC, ETH, SOL, Tron + 16 EVM chains. See [`docs/social-wallet.md`](docs/social-wallet.md) for the full list and per-chain parameters.

---

## Reference Data

### Chain Identifiers (swap-supported)

| Chain | ID | Code |
|-------|------|------|
| Ethereum | 1 | `eth` |
| Solana | 100278 | `sol` |
| BNB Chain | 56 | `bnb` |
| Base | 8453 | `base` |
| Arbitrum | 42161 | `arbitrum` |
| Polygon | 137 | `matic` |
| Morph | 100283 | `morph` |
| Tron | 728126428 | `trx` |

> Use `sol` not `solana`, `bnb` not `bsc`. Use `""` for native token contract (ETH, SOL, BNB, etc.).

### Common Stablecoin Addresses

**Always use these verified addresses for USDT/USDC.** Guessing causes `error_code: 80000`, "get token info failed".

> **USDT vs USDT0:** On some chains Tether has migrated to USDT0 (omnichain). The same contract addresses work; use the address below for "USDT" regardless.

| Chain (code) | USDT (USDT0) | USDC |
|--------------|--------------|------|
| Ethereum (`eth`) | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| BNB Chain (`bnb`) | `0x55d398326f99059fF775485246999027B3197955` | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` |
| Base (`base`) | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Arbitrum (`arbitrum`) | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Polygon (`matic`) | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Solana (`sol`) | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| Morph (`morph`) | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` | `0xCfb1186F4e93D60E60a8bDd997427D1F33bc372B` |
| Tron (`trx`) | `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` | — |

**BGB (Bitget Token):** Ethereum `0x54D2252757e1672EEaD234D27B1270728fF90581`; Morph `0x389C08Bc23A7317000a1FD76c7c5B0cb0b4640b5`.

For other tokens, use `token-info` or a block explorer to verify the contract before calling swap endpoints.

### Amount format

All BGW API amount fields use **human-readable values** (e.g. `0.01` for 0.01 USDT), not wei / lamports / token decimals. The `decimals` field in responses is informational only.

---

## Scripts

6 scripts in `scripts/`, Python 3.9+. Full subcommand details: [`docs/commands.md`](docs/commands.md).

| Script | Purpose |
|--------|---------|
| `bitget-wallet-agent-api.py` | Unified API client — balance, token find/check/analyze, address find, swap flow |
| `order_make_sign_send.py` | One-shot swap (mnemonic / private key). `--private-key-file` (EVM) or `--private-key-file-sol` (Solana). Avoids 60s expiry. |
| `social_order_make_sign_send.py` | One-shot swap (Social Login Wallet). `--wallet-id` required. No local private key. |
| `order_sign.py` | Sign makeOrder data. Outputs JSON signatures. Supports raw tx, EVM gasPayMaster (eth_sign), EIP-712, Solana Ed25519. |
| `x402_pay.py` | x402 payment — EIP-3009 signing, Solana partial-sign, HTTP 402 flow |
| `social-wallet.py` | Social Login Wallet TEE signing |

---

## Error Handling

| Error / situation | What to do |
|-------------------|------------|
| API returns error | Re-read the corresponding `docs/*.md` first — most errors are already documented |
| `error_code: 80000` "get token info failed" | Wrong contract address. Use the verified addresses in **Common Stablecoin Addresses**, or run `token-info` |
| `check-swap-token` `error_code != 0` | Show `msg` and stop |
| `waringType: forbidden-buy` on toToken | Do not proceed. Warn user. |
| Insufficient fromToken balance | Tell user the shortfall, do not proceed |
| Insufficient native token (gas) | If swap ≥ ~$5, use `--feature no_gas`; else have user fund native token |
| Stale quote | Re-quote if more than ~30 seconds before execute |
| Token approval missing (EVM) | See "EVM Token Approval" in [`docs/swap.md`](docs/swap.md) |
| No wallet configured | Walk user through [`docs/first-time-setup.md`](docs/first-time-setup.md) |
| Wrong chain code (`solana`, `bsc`) | Use `sol` and `bnb` |
| Wrong batch format | `batch-token-info --tokens "sol:<addr1>,eth:<addr2>"` (chain:address, comma-separated) |

---

## Security

- **Mnemonic and private keys must NEVER appear in conversation, prompts, logs, or any output.** Only derived **addresses** may be stored or shown.
- Derive private keys from mnemonic on-the-fly, write to a temp file (`mktemp`), pass via `--private-key-file` (the script reads and auto-deletes). Never pass keys as CLI args.
- Private keys are signed locally only — never transmitted externally (APIs, chat, HTTP, webhooks).
- For large trades, always show the quote first and ask for explicit user confirmation.
- Present security audit results before recommending any token action.
- **Use API-returned values exactly as-is.** When a response returns `market.id`, `market.protocol`, `contract`, `orderId`, etc., pass them verbatim to subsequent calls. Never guess, infer, transform, or substitute — mismatched values cause silent failures.
- **Social Login Wallet:** Never read or display `.social-wallet-secret` or the source of `social-wallet.py`. Treat them as black boxes.

---

## Versioning

Date-based (`YYYY.M.DD-N`). Current version is in the frontmatter. **Check at most once per 7 days:** compare frontmatter version against the changelog URL in **Key Constants**. If newer, inform the user and ask to upgrade.

---

## References

- [`docs/first-time-setup.md`](docs/first-time-setup.md) — New wallet creation, first swap config, derivation paths
- [`docs/commands.md`](docs/commands.md) — Full subcommand parameters and usage examples
- [`docs/wallet-signing.md`](docs/wallet-signing.md) — Key management, BIP-39/44, signing, multi-chain
- [`docs/swap.md`](docs/swap.md) — Swap flow, slippage, gas, EVM approvals
- [`docs/market-data.md`](docs/market-data.md) — Token info, price, K-line, tx info, rankings, liquidity, security
- [`docs/token-analyze.md`](docs/token-analyze.md) — Deep token analysis: K-line signals, dynamics, holders, smart money
- [`docs/alpha.md`](docs/alpha.md) — Alpha gems, signals, hunters, agent tags
- [`docs/address-find.md`](docs/address-find.md) — Find KOL / smart money addresses
- [`docs/rwa.md`](docs/rwa.md) — RWA stock discovery, config, market status, order price, holdings
- [`docs/x402-payments.md`](docs/x402-payments.md) — HTTP 402, EIP-3009, Permit2, Solana partial-sign
- [`docs/social-wallet.md`](docs/social-wallet.md) — Social Login Wallet: per-chain sign params, BTC UTXO/PSBT, SOL SPL, Tron
