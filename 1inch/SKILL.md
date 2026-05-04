---
name: 1inch
version: 2.1.1
description: Script-first 1inch swap skill (no system tool dependency). Uses local scripts + 1inch API + wallet service.
delivery: script
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

---

## Script Reference (CLI args)

This skill exposes scripts (not Python functions). Run them via `bash` +
`python3 skills/1inch/scripts/<name>.py <args>`. All scripts emit JSON on
stdout — parse with `json.loads(...)` or just print the output.

### Common arguments

| Arg | Required | Notes |
|---|---|---|
| `--chain` | yes | One of `ethereum`, `arbitrum`, `base`, `optimism`, `polygon`, `bsc`, `avalanche`, `gnosis` |
| `--from`, `--to` | yes (swap/quote) | Token symbol (`USDC`, `POL`, etc.) or contract address. Use `native` / `ETH` for native gas token. |
| `--amount` | yes (swap/quote) | Human units (e.g. `1` = 1 USDC, decimal conversion handled internally) |
| `--slippage` | optional | Percent (default `1.0`) |
| `--token` | yes (allowance/approve) | Token symbol or address |
| `--auto-approve` | optional flag | swap/run_swap_flow only — auto-broadcasts approve if allowance insufficient |
| `--swap-retries` | optional | run_swap_flow only — retries on `/swap` 5xx (default `2`) |
| `--swap-retry-backoff` | optional | run_swap_flow only — backoff seconds (default `1`) |

### Scripts

| Script | Purpose | Required args |
|---|---|---|
| `tokens.py` | List or search tokens on a chain | `--chain` + `--search SYM` and/or `--limit N` |
| `quote.py` | Get quote (no broadcast) | `--chain --from --to --amount` |
| `check_allowance.py` | Check ERC-20 allowance to 1inch router | `--chain --token` |
| `approve.py` | Broadcast approve tx (unlimited) | `--chain --token` |
| `swap.py` | Execute swap | `--chain --from --to --amount` (+ optional `--slippage`, `--auto-approve`) |
| `run_swap_flow.py` | One-command quote + (auto-approve) + swap + post-trade balance check | Same as `swap.py` (+ optional retry args) |

### Recommended flow

For ANY user "swap X for Y" request, default to `run_swap_flow.py
--auto-approve`. It handles the full chain end-to-end and verifies via
wallet balance read after broadcast.

If user asks "just quote, don't execute" → `quote.py` only.

### Output schema (run_swap_flow.py)

JSON with these top-level keys:
- `quote` — `{fromToken, toToken, fromAmount, toAmount, estimatedGas, ...}`
- `approve` — `{required, txHash, success}` (only if `--auto-approve`)
- `swap` — `{txHash, success, error?}`
- `verification` — `{from_balance_before, from_balance_after, to_balance_before, to_balance_after, delta_in, delta_out}`

If wallet returns a policy rejection, `swap.success = false` and
`swap.error` will mention `policy`. Load the `wallet-policy` skill,
propose a wildcard baseline, then rerun.
