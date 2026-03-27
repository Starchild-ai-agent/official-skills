---
name: 1inch
version: 2.0.0
description: Script-first 1inch swap skill. Uses local scripts + 1inch API + wallet service. No system tool dependency.
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

# 1inch (Script-First)

DEX swap via local scripts — no `oneinch_*` tool calls. All scripts under `skills/1inch/scripts/`.

**Chains:** ethereum, arbitrum, base, optimism, polygon, bsc, avalanche, gnosis

## Scripts

| Script | Purpose |
|--------|---------|
| `tokens.py --chain X --search Y` | Token search/list |
| `quote.py --chain X --from A --to B --amount N` | Get quote |
| `check_allowance.py --chain X --token A` | Check approval |
| `approve.py --chain X --token A` | Approve (unlimited) |
| `swap.py --chain X --from A --to B --amount N --slippage 1.0 --auto-approve` | Execute swap |
| `run_swap_flow.py --chain X --from A --to B --amount N --slippage 1.0 --auto-approve` | **Full flow** (recommended) |

All scripts: `python3 skills/1inch/scripts/<script>.py <args>`

## Default Workflow

For "swap X USDC to POL":
```bash
python3 skills/1inch/scripts/run_swap_flow.py --chain polygon --from USDC --to POL --amount 1 --slippage 1.0 --auto-approve
```
Read JSON result → report quote, tx result, balance deltas.

**Manual fallback:** `quote.py` → `swap.py --auto-approve` → verify balances.

## Error Handling

| Error | Fix |
|-------|-----|
| Unknown chain | Use supported chain name |
| API 4xx/5xx | Show raw error; `run_swap_flow.py` auto-retries 5xx (2 retries, exp backoff) |
| Not enough balance | Symbol may be wrong variant (USDC vs USDC.e) — use explicit address from `tokens.py` |
| Insufficient allowance | Rerun with `--auto-approve` or run `approve.py` first |
| Policy rejection | Load wallet-policy skill → propose wildcard policy → retry |

## Notes

- Amounts in **human units** (`--amount 1` = 1 USDC), scripts handle decimal conversion
- Native token: use `native` or `ETH`
- Multiple variants on chain (USDC/USDC.e) → pass contract address explicitly
- Requires sc-proxy (reads `HTTP_PROXY`/`HTTPS_PROXY` or `PROXY_HOST`+`PROXY_PORT`)
- Smoke test: `python3 skills/1inch/scripts/quote.py --chain polygon --from USDC --to POL --amount 1`
