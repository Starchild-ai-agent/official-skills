---
name: elfa
version: 1.0.1
description: |
  ELFA AI — real-time crypto social intelligence and automated condition-engine skills for AI agents.

  Track trending tokens, surface narratives, search mentions, run market analysis, and build automated trigger-based workflows.
description: >-
  ELFA AI crypto social intelligence — trending tokens, narratives, mention search, automated trigger workflows.
---

# ELFA AI (Official Onboarding Entry)

This is an **official onboarding entry** for discovering ELFA skills in the Starchild catalog.
The full ELFA skill implementation lives in ELFA's upstream repository.

## When to use



## What ELFA Does

ELFA is **real-time data infrastructure for financial AI** — the nervous system that gets the right information to the right decision-maker at the right moment.

### Core Capabilities

**Social Intelligence**
- Trending tokens by mention count (Twitter & Telegram)
- Top mentions for any ticker symbol ($SOL, $BTC, etc.)
- Keyword mention search across social platforms
- Smart follower & engagement stats for any account
- AI-powered event summaries and token intros

**Narrative & Market Analysis**
- Trending narrative clusters (what the market is talking about)
- Token-related news aggregation
- AI chat for market analysis, account reviews, and token research
- Real-time social sentiment tracking

**Auto Condition Engine**
- Builder Chat — AI-assisted query building
- Create automated trigger queries (e.g., "Alert me when BTC crosses 100k")
- Multi-condition triggers (e.g., "BTC + ETH breakout confirmation")
- RSI-based dip-buy strategies with TP/SL
- Portfolio check automation (e.g., 4h recurring checks on BTC, ETH, SOL)
- SSE streaming for real-time notifications
- Exchange integrations (GRVT, Hyperliquid) for automated execution

**GRVT Trading Bot**
- Self-hosted Elfa Auto → GRVT perpetual futures bot
- FastAPI receiver with EIP-712 signing
- SQLite registry for strategy management
- Telegram alerts for trade events
- OTOCO (One-Triggers-Other-Cancels-One) TP/SL execution

## Install

```bash
npx skills add elfa-ai/skills
```

This installs both `elfa-ai` and `elfa-grvt-bot` skills via the Skills CLI.

## Optional: List Available ELFA Skills First

```bash
npx skills add elfa-ai/skills --list
```

## Optional: Install Specific ELFA Skill(s)

```bash
npx skills add elfa-ai/skills --skill elfa-ai
npx skills add elfa-ai/skills --skill elfa-grvt-bot
```

## Update

```bash
npx skills update
```

## API Key

Get a free key (1,000 credits) at **[go.elfa.ai/claude-skills](https://go.elfa.ai/claude-skills)**

```bash
export ELFA_API_KEY=your_key_here
```

Free tier works with most endpoints. Trending narratives and AI chat require a paid plan.

Alternatively, use **x402 keyless payments** to pay per request with USDC on Base (no signup required).

## Notes

- This official entry exists so users can discover ELFA from the Official Skills catalog.
- Actual installation always pulls from `elfa-ai/skills`.
- If upstream changes, follow upstream docs and versions as source of truth.
- Full documentation: **[docs.elfa.ai](https://docs.elfa.ai)**

---

Powered by [Elfa AI](https://go.elfa.ai/claude-visit)
