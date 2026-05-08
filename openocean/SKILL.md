---
name: openocean
version: 1.0.0
description: OpenOcean DEX aggregator adapter for Starchild wallet (quote, approval, and swap execution with balance-delta verification)
author: starchild
tags: [openocean, dex, swap, evm, ethereum, aggregator]
tools:
  - openocean_gas_price
  - openocean_quote
  - openocean_swap
metadata:
  starchild:
    emoji: "🌊"
    skillKey: openocean
user-invocable: true
disable-model-invocation: false
---

# OpenOcean Skill (Starchild Adapter)

Use this skill when user asks to:
- get OpenOcean quote
- execute swap via OpenOcean route
- run OpenOcean trade through Starchild wallet

## Tools

- `openocean_gas_price(chain='ethereum')`
- `openocean_quote(chain, in_token, out_token, amount_wei, slippage='1')`
- `openocean_swap(chain, in_token, out_token, amount_wei, slippage='1', verify_timeout_seconds=90, poll_interval_seconds=5)`

## Current Scope

- ✅ Ethereum mainnet execution path tested (ETH -> ERC20 and ERC20 -> ETH)
- ✅ Uses Starchild `wallet_transfer` to broadcast
- ✅ Built-in ERC20 approval flow (checks allowance and sends approve when needed)
- ✅ Verifies result by balance delta (works when tx hash is delayed)

## Safety Checklist

1. First run `openocean_quote` and show output.
2. Confirm amount and slippage with user.
3. Execute with small amount first.
4. Require verification result (`verified_by_balance_delta=true`) before claiming success.
