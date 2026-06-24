---
name: okx
version: 1.0.7
description: |
  OKX OnChainOS: on-chain trading, analytics, security, DeFi across 20+ chains.

  Use when running OKX-routed on-chain ops (e.g. swap on Ethereum, scan token risk, track smart money, check wallet portfolio).

  Wallet: default to the user's Agent Wallet (via the `wallet` skill). Only use the OnchainOS TEE wallet (`onchainos wallet login <email>`) when the user explicitly asks for it.
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

OKX OnChainOS is a suite of **16 specialized sub-skills** covering on-chain
trading, market analytics, smart-money signals, DeFi investing & positions,
wallet ops, security scanning, payment protocols, and crypto news & sentiment
across 20+ blockchains (Ethereum, Solana, XLayer, Base, BSC, Arbitrum, Polygon,
Optimism, Avalanche, TRON, …).

Most sub-skills drive a single binary, `onchainos`, which is downloaded on first
use. A subset of capabilities (read-only data) can also be accessed without the
binary, via Starchild's sc-proxy — see **Authentication options** below.

---

## How install actually works

```bash
# Install one sub-skill (recommended — pulls just what you need)
npx skills add okx/onchainos-skills@<sub-skill-name>

# Or via long form
npx skills add https://github.com/okx/onchainos-skills --skill <sub-skill-name>

# Install everything (auto-detects your environment and installs accordingly)
npx skills add okx/onchainos-skills
```

Each sub-skill ships its own SKILL.md + reference docs + trigger phrases, so you
can pull just what you need.

**Plugin marketplace** (alternative):

```text
/plugin marketplace add okx/onchainos-skills
/plugin install onchainos-skills
```

**CLI install** (the `onchainos` binary — auto-detects platform, verifies SHA256,
installs to `~/.local/bin` or `%USERPROFILE%\.local\bin`):

```bash
# macOS / Linux
curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh
# add `-s -- --beta` for the latest pre-release (opt-in only; never downgrades)
```

```powershell
# Windows
irm https://raw.githubusercontent.com/okx/onchainos-skills/main/install.ps1 | iex
```

---

## Wallet — default to the user's Agent Wallet

Use the platform `wallet` skill for signing and broadcasting. OKX DEX
endpoints return unsigned calldata (`{to, value, data, ...}`); feed it to
`wallet_transfer(data=<calldata>)` and you're done. No separate OKX wallet
needed.

Only use the OnchainOS TEE wallet (`onchainos wallet login <email>`) when
the user explicitly asks for it.

---

## Authentication options (read this before invoking anything)

There are two distinct paths. Pick based on what the agent needs to do:

### Path A — Direct HTTP via Starchild sc-proxy (no API Key needed)

For read-only data lookups (prices, K-line, smart-money signals, token
analytics, security checks, public-address portfolios — **≈ 80 % of OnchainOS
capabilities**), the agent can skip the CLI entirely and call
`https://web3.okx.com/...` directly through sc-proxy:

```python
from core.http_client import proxied_get
r = proxied_get(
    "https://web3.okx.com/api/v6/dex/aggregator/supported/chain",
    headers={"SC-CALLER-ID": f"chat:{thread_id}"},
)
```

sc-proxy auto-injects platform OKX credentials, signs each request with
HMAC-SHA256, and bills the caller's Starchild credits.

- **Cost**: $0.001 / request
- **Rate limit**: 60 req/min
- **Setup**: none
- **Limits**: data only — cannot send transactions or manage wallets

### Path B — `onchainos` CLI with your own OKX Web3 API Key

For wallet ops (`wallet login`, `wallet send`, `wallet contract-call`), DEX
swaps that need execution, payments, and any other CLI-driven workflow.

The `onchainos` CLI ships with **built-in sandbox API keys** that work out of the
box for local testing — no setup required. These keys are **shared, rate-limited,
and for evaluation only**: do NOT use them in production or with real assets. Any
failures or losses from using the built-in keys are the caller's responsibility.

For production, bring your own credentials:

1. Apply at [web3.okx.com → Build → Dev Portal](https://web3.okx.com/build/dev-portal)
2. Set env vars (or a `.env` in the project root — never commit it):
   ```bash
   export OKX_API_KEY=<your key>
   export OKX_SECRET_KEY=<your secret>
   export OKX_PASSPHRASE=<your passphrase>
   ```
3. Run any sub-skill's CLI commands.

### Why the CLI can't use sc-proxy

The `onchainos` binary uses Rust's `rustls` TLS stack with **bundled
`webpki-roots`** — a compile-time copy of the Mozilla root CA list. It ignores
the system trust store, ignores `SSL_CERT_FILE`, and has no documented env
override. As a result, sc-proxy's MITM CA is rejected as `UnknownIssuer`, and
the CLI cannot be transparently proxied. Path A (direct HTTP from agent
scripts) is the only way to use platform credentials with OnchainOS today.

Wallet creation (`onchainos wallet login <email>`) gives you a fresh TEE-managed
account — it does NOT import your existing OKX App / extension wallet.

---

## Sub-skills by category

### 📊 Discovery & Market Data (7)

| Sub-skill | Use for |
|---|---|
| `okx-dex-market` | Real-time prices, K-line charts, index prices, wallet PnL analysis, address tracker activities |
| `okx-dex-token` | Token search, metadata, market cap, rankings, liquidity pools, hot tokens, advanced info, holder analysis, top traders, trade history, holder cluster analysis |
| `okx-dex-signal` | Smart money / whale / KOL signal tracking, leaderboard rankings |
| `okx-dex-trenches` | Meme pump/trenches token scanning, dev reputation, bundle detection, aped wallets |
| `okx-dex-social` | Crypto news (latest, by symbol, search, detail, source platforms), market-wide sentiment ranking + per-coin sentiment with trend, per-token vibe timeline + TOP50 KOL leaderboard |
| `okx-defi-portfolio` | DeFi positions and holdings overview across protocols and chains |
| `okx-dapp-discovery` | Third-party DApp discovery and direct plugin routing — currently supports Polymarket, Aave V3, Hyperliquid, PancakeSwap V3 AMM, Morpho V1 Optimizer |

### 🔄 Trading & Execution (3)

| Sub-skill | Use for |
|---|---|
| `okx-dex-swap` | Token swap via DEX aggregation (500+ liquidity sources) |
| `okx-defi-invest` | DeFi product discovery, deposit, withdraw, claim rewards across Aave, Lido, PancakeSwap, Kamino, NAVI and more |
| `okx-onchain-gateway` | Gas estimation, transaction simulation, broadcasting, order tracking |

### 💼 Wallet (2)

| Sub-skill | Use for |
|---|---|
| `okx-agentic-wallet` | Wallet lifecycle: auth, balance, portfolio PnL, send, tx history, contract call |
| `okx-wallet-portfolio` | Public address balance, token holdings, portfolio value |

### 🔐 Security (1)

| Sub-skill | Use for |
|---|---|
| `okx-security` | Security scanning: token risk, DApp phishing, tx pre-execution, signature safety, approval management |

### 💸 Payments (1)

| Sub-skill | Use for |
|---|---|
| `okx-agent-payments-protocol` | Unified payment dispatcher across x402 (`exact` / `aggr_deferred` schemes — TEE or local-key sign), MPP (`charge` / `session` intents — open / voucher / topUp / close, transaction or hash mode), and a2a-pay (paymentId-based create / pay / status). Routes to per-scheme/intent references. |

### 🛠️ Ops (2)

| Sub-skill | Use for |
|---|---|
| `okx-growth-competition` | Agentic Wallet exclusive trading competitions: list, join, view leaderboard, claim rewards |
| `okx-audit-log` | Audit log export and troubleshooting |

---

## Quick task → sub-skill map

| I want to… | Sub-skill | Suggested path |
|---|---|---|
| Check a token price or chart | `okx-dex-market` | A (no key) |
| Search / analyze a token's holders | `okx-dex-token` | A (no key) |
| Follow smart money buys | `okx-dex-signal` | A (no key) |
| Scan new meme launches | `okx-dex-trenches` | A (no key) |
| Look at any public wallet | `okx-wallet-portfolio` | A (no key) |
| Scan a token / dApp for risk | `okx-security` | A (no key) |
| Estimate gas / simulate a tx | `okx-onchain-gateway` | A or B |
| Manage / send from my own wallet | `okx-agentic-wallet` | B (requires login) |
| Swap tokens | `okx-dex-swap` REST + sign with the `wallet` skill (Agent Wallet) |
| Find best DeFi yield (any protocol) | `okx-defi-invest` | B (signing) |
| View my DeFi positions | `okx-defi-portfolio` | A (no key) |
| Use a specific DApp (Aave, Polymarket, …) | `okx-dapp-discovery` | B (full DApp flow) |
| Pay an x402 / MPP / a2a-pay gated resource | `okx-agent-payments-protocol` | B (signing) |
| Join a trading competition | `okx-growth-competition` | B (wallet required) |
| Debug a CLI failure | `okx-audit-log` | B (local CLI logs) |

---

## Workflows — pre-built multi-skill orchestrations

Beyond individual sub-skills, the repo ships **workflow orchestrations** under
`workflows/` that compose several skills into one complete operation. The agent
reads `workflows/INDEX.md` to route a request, then follows the step-by-step
instructions in the matched workflow file.

| Workflow | What it does | CLI command |
|---|---|---|
| Token Research | Price, security, holders, cluster, smart-money signals, optional launchpad deep-dive | `onchainos workflow token-research --address <addr>` |
| Daily Brief | Market pulse + smart money + new-token activity + portfolio alerts | — |
| Smart Money Signals | SM signal list aggregated by token + per-token due diligence | `onchainos workflow smart-money` |
| New Token Screening | MIGRATED launchpad scan + safety & dev enrichment for top 10 | `onchainos workflow new-tokens` |
| Wallet Analysis | 7d/30d PnL, trading behaviour, recent on-chain activity | `onchainos workflow wallet-analysis --address <addr>` |
| Portfolio Check | Balances, total value, 30d PnL overview | `onchainos workflow portfolio --address <addr>` |
| Wallet Monitor | In-session polling — alert on new trades from watched wallets | — |
| Wallet Monitor (WS) | Background WebSocket session for offline wallet monitoring | — |

### Composite CLI commands

Single commands that replace multiple individual tool calls:

```bash
# Token report: info + price + advanced-info + security scan (parallel)
onchainos token report --address <addr> --chain solana

# Full workflow commands
onchainos workflow token-research --address <addr> [--chain solana]
onchainos workflow smart-money [--chain solana]
onchainos workflow new-tokens [--chain solana] [--stage MIGRATED]
onchainos workflow wallet-analysis --address <addr> [--chain ethereum]
onchainos workflow portfolio --address <addr> [--chains ethereum,solana]
```

### Typical skill flows

- **Search & buy**: `okx-dex-token` (find token) → `okx-wallet-portfolio` (check funds) → `okx-dex-swap` (execute trade)
- **Portfolio overview**: `okx-wallet-portfolio` (holdings) → `okx-dex-token` (enrich with analytics) → `okx-dex-market` (price charts)
- **Market research**: `okx-dex-token` (trending/rankings) → `okx-dex-market` (candles/history) → `okx-dex-swap` (trade)
- **Swap & broadcast**: `okx-dex-swap` (get tx data) → sign locally → `okx-onchain-gateway` (broadcast → track order)
- **Pre-flight check**: `okx-onchain-gateway` (estimate gas → simulate → broadcast → track order)
- **Full trading flow**: `okx-dex-token` (search) → `okx-dex-market` (price/chart) → `okx-wallet-portfolio` (check balance) → `okx-dex-swap` (get tx) → `okx-onchain-gateway` (simulate + broadcast + track)
- **Leaderboard → research → trade**: `okx-dex-signal` (top traders by PnL/win rate) → `okx-dex-token` (token analytics) → `okx-dex-swap` (execute trade)
- **Follow smart money**: `okx-dex-signal` (KOL/smart money buys) → `okx-dex-token` (details + holder cluster) → `okx-dex-market` (price chart) → `okx-dex-swap` (trade)

---

## MCP server

The `onchainos` CLI doubles as a native MCP server, exposing its tools to any
MCP-compatible client. Start it with:

```bash
onchainos mcp
```

---

## Important notes

- **Chain identifiers**: both human names (`ethereum`, `solana`, `xlayer`) and
  numeric IDs are accepted. Run `onchainos swap chains` or
  `onchainos gateway chains` for the full list.
- **Read-only ops** (market data, signals, security scan, public-address
  portfolios) work via Path A without any user-supplied API Key.
- **Trading & sending** default to the user's Agent Wallet via the `wallet`
  skill. Only fall back to `onchainos wallet login` when the user asks.
- **Security gate**: when `okx-security` reports a fail, the calling agent
  MUST block the related operation rather than proceed.

---

## Resources

- **Upstream repo**: [okx/onchainos-skills](https://github.com/okx/onchainos-skills)
- **OnchainOS docs**: [OKX Web3 Build — OnchainOS](https://www.okx.com/web3/build/docs/onchain-os/introduction)
- **Skills registry**: [skills.sh/okx/onchainos-skills](https://skills.sh/okx/onchainos-skills)
- **Dev portal (API Key)**: [web3.okx.com/build/dev-portal](https://web3.okx.com/build/dev-portal)
