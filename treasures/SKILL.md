---
name: treasures
version: 1.0.1
description: |
  Treasures Finance: tokenized stocks (xStocks / Ondo) trading, USDC bridging, and delegated wallet ops on Solana and Ethereum.

  Use when running Treasures-routed finance ops (e.g. discover tokenized stocks, quote/execute a trade, bridge USDC across chains, check a wallet's portfolio).

  Wallet: default to `treasures-b2b-api` against the user's own wallet (e.g. their Agent Wallet) — no fresh wallet to fund with gas/USDC, and the user keeps control of the keys. Only use the `treasures-wallet` delegated flow (provisions a new Treasures-managed wallet) when the user explicitly wants Treasures to hold signing authority.
metadata:
  starchild:
    emoji: "💎"
    skillKey: treasures-finance
    requires:
      bins:
        - npx
        - node
user-invocable: true
disable-model-invocation: false

---

# Treasures Finance Agent Skills

**Agent Skills** for building AI agents on the Treasures finance APIs.

A skill is a folder of plain-Markdown instructions (`SKILL.md`) that a coding agent loads on demand. The skills here teach an agent to call the Treasures finance APIs correctly — discover tokenized stocks, quote and execute trades, bridge USDC across chains, operate a delegated wallet, and read portfolios — including the signing details and footguns that are easy to get wrong.

## Wallet — which path to use

There are two ways to trade tokenized stocks through Treasures. Pick based on
whether the user wants to keep control of their own wallet:

- **Default → `treasures-b2b-api`**: drives the raw Treasures B2B API against
  the user's *own* wallet (e.g. their Agent Wallet). No new wallet to
  provision, nothing extra to fund with gas or USDC, and the user already
  holds the keys. This is also how Treasures itself tested its agentic flow
  before `treasures-wallet` existed.
- **Only when explicitly requested → `treasures-wallet`**: provisions a
  *fresh*, Treasures-managed delegated wallet (non-custodial, scoped strictly
  to RWA trades — the agent never signs, Treasures signs as delegated
  signer). This is the right call when the user wants Treasures to fully
  manage signing, but it means funding a brand-new wallet with gas + USDC
  that the user can't directly control day-to-day (the private key can be
  exported from the Treasures website if they need it).

If in doubt, prefer `treasures-b2b-api` — most users would rather trade from
a wallet they already hold than fund and manage a new one.

## Skill catalog

| Skill | What it does |
| ----- | ------------ |
| [`treasures-b2b-api`](skills/treasures-b2b-api/SKILL.md) | Build an agent on the Treasures public B2B API: discover tokenized stocks, quote/execute trades, bridge USDC across Solana and Ethereum, and read portfolio + trade history for a single end-user wallet pair. Covers endpoint selection, ownership-proof signing (incl. embedded wallets), trade/bridge execution, and error handling. |
| [`treasures-wallet`](skills/treasures-wallet/SKILL.md) | Operate a Treasures delegated wallet over HTTP: onboard (provision a wallet + mint a scoped API key), quote, execute async buys/sells (non-custodial — the agent never signs; Treasures signs as a delegated signer scoped strictly to RWA trades), read balances/portfolio/trade history, and manage API keys. Trades tokenized equities (xStocks / Ondo) vs USDC on Solana or Ethereum with only HTTPS + an API key — no web3 libraries, keys, or RPC. |

## Install

```bash
# Install one sub-skill (recommended — pulls just what you need)
npx skills add treasures-io/treasures-finance-agent-skills --skill treasures-b2b-api
npx skills add treasures-io/treasures-finance-agent-skills --skill treasures-wallet

# Or install everything (auto-detects your environment and installs accordingly)
npx skills add treasures-io/treasures-finance-agent-skills
```

[`npx skills`](https://github.com/vercel-labs/skills) installs `SKILL.md` files into the right place for 70+ coding agents (Claude Code, Codex, Cursor, GitHub Copilot, Windsurf, Cline, OpenCode, …) and auto-detects which ones you have. It reads this repo's `skills/<name>/SKILL.md` layout directly, so no extra setup is required.

Target specific agents with `-a`:

```bash
npx skills add treasures-io/treasures-finance-agent-skills -a claude-code -a codex -a cursor
```

## License

[MIT](LICENSE)
