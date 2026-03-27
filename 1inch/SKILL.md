---
name: 1inch
version: 2.0.0
description: Script-first 1inch swap skill (no system tool dependency). Uses local scripts + 1inch API + wallet service.
author: starchild
tags: [1inch, dex, swap, evm, script-first]
metadata:
  starchild:
    emoji: "🦄"
    skillKey: 1inch
    requires:
      env: [ONEINCH_API_KEY, WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# 1inch (Script-First, Install-and-Use)

This skill is designed for your architecture: **do not rely on platform-injected tools**.

- ✅ Uses only skill-local scripts under `skills/1inch/scripts/`
- ✅ Agent executes scripts via `bash` (`python3 ...`)
- ✅ No `oneinch_*` tool calls required

---

## Why this version fixes “tool not found”

Old design depended on runtime tool registration (`oneinch_quote`, `oneinch_swap`, ...).
If tool injection fails, agent is blocked.

New design uses deterministic local scripts:

1. call 1inch HTTP API directly
2. call wallet service directly (OIDC via `/.fly/api`)
3. print JSON result

So after install, the agent always has a runnable path.

---

## Files

- `scripts/_oneinch_lib.py` — shared client + wallet/OIDC helpers
- `scripts/tokens.py` — token search/list
- `scripts/quote.py` — quote only
- `scripts/check_allowance.py` — allowance check
- `scripts/approve.py` — approve tx broadcast
- `scripts/swap.py` — swap execution (optional auto-approve)
- `scripts/run_swap_flow.py` — one-command flow (quote + optional approve + swap + post-trade balance verification)

---

## Environment

Required:
- `ONEINCH_API_KEY`
- `WALLET_SERVICE_URL` (default fallback exists)
- **sc-proxy connectivity** for 1inch API (**mandatory**)

Assumptions:
- Running on Fly Machine with `/.fly/api` unix socket for OIDC token minting.

### sc-proxy requirement (critical)

This skill enforces 1inch calls through sc-proxy.

- It reads proxy from `HTTP_PROXY/HTTPS_PROXY` first, else falls back to `PROXY_HOST` + `PROXY_PORT`.
- If no proxy env is found, scripts fail fast with a clear error instead of silently direct-connecting.

---

## Supported chains

`ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis`

---

## Agent execution rules (IMPORTANT)

When user asks for 1inch actions, follow this exact pattern:

1. **Never call `oneinch_*` tools**
2. Run local scripts with `bash` + `python3 skills/1inch/scripts/<script>.py ...`
3. Parse JSON output and respond with concise summary
4. For write actions, always do post-check using wallet balance tools (if available) or rerun script-based checks

### Canonical mapping

- “查 token 地址 / 列 token” → `tokens.py`
- “先报价 / 看能换多少” → `quote.py`
- “检查授权” → `check_allowance.py`
- “授权” → `approve.py`
- “执行兑换” → `swap.py`

---

## Command examples

### 1) Search token

```bash
python3 skills/1inch/scripts/tokens.py --chain polygon --search POL --limit 10
```

### 2) Quote: 1 USDC -> POL

```bash
python3 skills/1inch/scripts/quote.py --chain polygon --from USDC --to POL --amount 1
```

### 3) Check allowance (USDC)

```bash
python3 skills/1inch/scripts/check_allowance.py --chain polygon --token USDC
```

### 4) Approve USDC (unlimited)

```bash
python3 skills/1inch/scripts/approve.py --chain polygon --token USDC
```

### 5) Swap: 1 USDC -> POL (auto-approve if needed)

```bash
python3 skills/1inch/scripts/swap.py --chain polygon --from USDC --to POL --amount 1 --slippage 1.0 --auto-approve
```

### 6) One-command full flow (recommended)

```bash
python3 skills/1inch/scripts/run_swap_flow.py --chain polygon --from USDC --to POL --amount 1 --slippage 1.0 --auto-approve
```

Tune retries when needed:

```bash
python3 skills/1inch/scripts/run_swap_flow.py --chain polygon --from USDC --to POL --amount 1 --slippage 1.0 --auto-approve --swap-retries 3 --swap-retry-backoff 2
```

---

## Default workflow for “买 X USDC 的 POL”

Preferred deterministic sequence:

1. `run_swap_flow.py --auto-approve`
2. Read JSON result and report quote, tx submission result, and verification deltas

Fallback manual sequence (if user asks step-by-step):
1. `quote.py` (confirm expected output)
2. `swap.py --auto-approve`
3. Verify with fresh balances (before/after)

If swap returns wallet policy rejection:
- load `wallet-policy` skill
- propose wildcard baseline (`DENY exportPrivateKey`, `ALLOW *`)
- after user confirms, rerun swap command

---

## Error handling

- `Unknown chain` → ask user to choose supported chain
- `1inch API 4xx/5xx` → show raw error; `run_swap_flow.py` automatically retries transient `/swap` 5xx (default: 2 retries with exponential backoff)
- `Not enough <token> balance` from 1inch → likely symbol mapped to a different token variant (e.g. USDC.e vs USDC); rerun with explicit token address from `tokens.py`
- `Wallet API 4xx/5xx` → show raw error, do not fabricate tx hash
- `insufficient allowance` (without auto-approve) → rerun with `--auto-approve` or run `approve.py`
- `policy` rejection → propose policy update then retry

---

## Notes

- Amount input is **human units** (e.g. `--amount 1` = 1 USDC), script handles decimal conversion.
- Token symbol resolution comes from 1inch `/tokens` on the selected chain.
- If a symbol has multiple variants on a chain (e.g., `USDC` / `USDC.e`), prefer passing **token contract address** explicitly to avoid ambiguity.
- For native token input, use `native` / `ETH`.

---

## Quick smoke test

```bash
python3 skills/1inch/scripts/quote.py --chain polygon --from USDC --to POL --amount 1
```

If this works, the skill is operational in script mode.
