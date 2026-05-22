---
name: okx
version: 1.0.3
description: |
  OKX OnChainOS: on-chain trading, analytics, security, DeFi, bridging across 20+ chains.

  Use when running OKX-routed on-chain ops (e.g. swap on Ethereum, scan token risk, track smart money, check wallet portfolio).
metadata:
  starchild:
    emoji: "⛓️"
    skillKey: okx-onchainos
    requires:
      bins:
        - npx
        - node
user-invocable: true
disable-model-invocation: false

---

# OKX OnChainOS — Skills Directory

> **What this file is:** a directory page that points to OKX's official
> `onchainos-skills` repo. It contains **no logic of its own** — every sub-skill
> below lives upstream at [`okx/onchainos-skills`](https://github.com/okx/onchainos-skills)
> and is fetched fresh on install, so you always get the latest version.

OKX OnChainOS is a suite of **22 specialized sub-skills** covering on-chain
trading, market analytics, smart-money signals, DeFi investing & positions,
cross-chain bridging, wallet ops, security scanning, payment protocols, and
real-time data streams across 20+ blockchains (Ethereum, Solana, XLayer, Base,
BSC, Arbitrum, Polygon, Optimism, Avalanche, TRON, …).

All sub-skills are driven by a single binary, `onchainos`, which is downloaded
on first use.

---

## How install actually works

```bash
# Install one sub-skill (recommended — pulls just what you need)
npx skills add okx/onchainos-skills@<sub-skill-name>

# Or via long form
npx skills add https://github.com/okx/onchainos-skills --skill <sub-skill-name>
```

There is **no batched "install all"** — install the sub-skills you actually
need. Each sub-skill ships its own SKILL.md + reference docs + trigger phrases.

---

## Authentication options

The CLI binary needs OKX Web3 credentials to call the OnchainOS data layer.
Two paths:

1. **Use your own API Key** — apply at
   [web3.okx.com → Build → Dev Portal](https://web3.okx.com/build/dev-portal),
   then `onchainos wallet login` (silent AK mode). Set `OKX_API_KEY`,
   `OKX_SECRET_KEY`, `OKX_PASSPHRASE` env vars.
2. **Use Starchild's shared proxy** (read-only data only) — sc-proxy auto-injects
   platform credentials for the `web3.okx.com` domain. No setup required;
   billed at $0.001/request through your Starchild credits (rate-limited to
   60 req/min). Trading & wallet ops still require your own login.

For wallet operations (send / swap / sign), additionally run
`onchainos wallet login <email>` to create or attach an OnchainOS TEE wallet
account (private key stays inside the enclave, never on disk).

---

## Sub-skills by category

### 📊 Discovery & Market Data (8)

| Sub-skill | Use for |
|---|---|
| `okx-dex-market` | Real-time prices, K-line / OHLC, index price, wallet PnL, address tracker |
| `okx-dex-token` | Token search, holder distribution (whales / smart money / snipers), top traders, cluster analysis, honeypot/rug checks |
| `okx-dex-signal` | Smart-money / whale / KOL buy signals, top-trader leaderboards |
| `okx-dex-trenches` | Meme launchpad scanning (pump.fun, BSC, X Layer, TRON), dev rug history, bundle/sniper detection, co-investor tracking |
| `okx-dex-social` | Crypto news feed + search, social sentiment ranking, KOL vibe & leaderboard |
| `okx-dex-ws` | WebSocket real-time streams (price, candle, trades, signals, tracker, meme) — CLI + custom script use |
| `okx-defi-portfolio` | View existing DeFi positions across protocols (lending / LP / staking) |
| `okx-dapp-discovery` | Bootstrap router: resolves a named DApp (Polymarket, Aave, Hyperliquid, etc.) to its plugin and forwards the prompt |

### 🔄 Trading & Execution (5)

| Sub-skill | Use for |
|---|---|
| `okx-dex-swap` | Multi-chain DEX aggregation across 500+ liquidity sources — quote, approve, swap |
| `okx-dex-bridge` | Cross-chain swap/transfer via Stargate / Across / Relay / Gas.zip — quote, build, track |
| `okx-dex-strategy` | Limit orders (TP / SL / buy-dip / chase-high) stored & auto-executed in TEE |
| `okx-defi-invest` | DApp-agnostic DeFi yield discovery + deposit/withdraw/claim (no named protocol) |
| `okx-onchain-gateway` | Gas price + estimate, transaction simulation, signed-tx broadcast, order tracking |

### 💼 Wallet (2)

| Sub-skill | Use for |
|---|---|
| `okx-agentic-wallet` | OnchainOS wallet lifecycle: login / verify OTP / status / addresses / balance / send (native + ERC-20 + SPL) / tx history / contract-call |
| `okx-wallet-portfolio` | Read-only portfolio for any public address — total value, all token balances, per-token lookup |

### 🔐 Security (1)

| Sub-skill | Use for |
|---|---|
| `okx-security` | Token risk & honeypot scan, DApp phishing scan, transaction pre-execution sim, signature safety, ERC-20/Permit2 approvals management |

### 💸 Payments (3)

| Sub-skill | Use for |
|---|---|
| `okx-agent-payments-protocol` | **Unified dispatcher** — handles x402 (`exact` / `aggr_deferred`), MPP (`charge` / `session`), and a2a-pay paymentId flows. Auto-detects 402 protocol from response headers. |
| `okx-x402-payment` | Direct x402 signing entry (still supported; new code prefers `okx-agent-payments-protocol`) |
| `okx-a2a-payment` | ⚠️ DEPRECATED — folded into `okx-agent-payments-protocol`. Stub kept only for legacy aliases. |

### 🛠️ Ops & Onboarding (3)

| Sub-skill | Use for |
|---|---|
| `okx-how-to-play` | Entry router for blank/onboarding prompts ("what does this do", "how do I start"). Routes to a concrete workflow in ≤ 3 turns. |
| `okx-growth-competition` | Agentic Wallet exclusive trading competitions: list → join → rank → claim |
| `okx-audit-log` | Audit log file path for offline debugging (`~/.onchainos/audit.jsonl`) |

---

## Quick task → sub-skill map

| I want to… | Sub-skill |
|---|---|
| Check a token price or chart | `okx-dex-market` |
| Search / analyze a token's holders | `okx-dex-token` |
| Follow smart money buys | `okx-dex-signal` |
| Scan new meme launches | `okx-dex-trenches` |
| Stream live market data over WS | `okx-dex-ws` |
| Look at any public wallet | `okx-wallet-portfolio` |
| Manage / send from my own wallet | `okx-agentic-wallet` |
| Swap tokens (same chain) | `okx-dex-swap` |
| Bridge tokens (cross chain) | `okx-dex-bridge` |
| Place a limit order | `okx-dex-strategy` |
| Find best DeFi yield (any protocol) | `okx-defi-invest` |
| Use a specific DApp (Aave, Polymarket, …) | `okx-dapp-discovery` |
| View my DeFi positions | `okx-defi-portfolio` |
| Scan a token / dApp for risk | `okx-security` |
| Estimate gas / simulate / broadcast a tx | `okx-onchain-gateway` |
| Pay an x402 / MPP / a2a-pay gated resource | `okx-agent-payments-protocol` |
| Join a trading competition | `okx-growth-competition` |
| Debug a CLI failure | `okx-audit-log` |

---

## Important notes

- **Chain identifiers**: both human names (`ethereum`, `solana`, `xlayer`) and
  numeric IDs are accepted. Run `onchainos swap chains` or
  `onchainos gateway chains` for the full list.
- **Read-only ops** (market data, signal, security scan, portfolio of a public
  address) work without an OnchainOS wallet login — API Key alone is enough.
- **Trading & sending** require `onchainos wallet login` so the TEE has a key
  to sign with. Wallet creation gives you a fresh address — it does **not**
  import your existing OKX App / extension wallet.
- **Security gate**: when `okx-security` reports a fail, the calling agent
  MUST block the related operation rather than proceed.

---

## Resources

- **Upstream repo**: [okx/onchainos-skills](https://github.com/okx/onchainos-skills)
- **OnchainOS docs**: [OKX Web3 Build — OnchainOS](https://www.okx.com/web3/build/docs/onchain-os/introduction)
- **Skills registry**: [skills.sh/okx/onchainos-skills](https://skills.sh/okx/onchainos-skills)
- **Dev portal (API Key)**: [web3.okx.com/build/dev-portal](https://web3.okx.com/build/dev-portal)
