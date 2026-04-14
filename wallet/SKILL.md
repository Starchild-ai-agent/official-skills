---
name: wallet
version: 3.3.0
description: "Multi-chain wallet — balances, transfers, signing, policy (EVM 16 chains + Solana)"
author: starchild
tags: [wallet, evm, solana, transfer, sign, policy, debank, birdeye]
tools:
  - wallet_info
  - wallet_balance
  - wallet_sol_balance
  - wallet_get_all_balances
  - wallet_transfer
  - wallet_sign_transaction
  - wallet_sign
  - wallet_sign_typed_data
  - wallet_transactions
  - wallet_sol_transfer
  - wallet_sol_sign_transaction
  - wallet_sol_sign
  - wallet_sol_transactions
  - wallet_get_policy
  - wallet_propose_policy
tool_module: wallet.wallet
---

# 💰 Wallet Skill

Multi-chain wallet for EVM (16 chains) + Solana. Balances, transfers, signing, policy management. Chain names auto-mapped to DeBank chain IDs (e.g. `avalanche` → `avax`).

## Tools

| Tool | Description |
|------|-------------|
| `wallet_info` | Get all wallet addresses |
| `wallet_balance` | EVM balance on a chain (DeBank) |
| `wallet_sol_balance` | Solana balance (Birdeye) |
| `wallet_get_all_balances` | All chains at once |
| `wallet_transfer` | **Broadcast** EVM tx (gas sponsored) |
| `wallet_sign_transaction` | Sign EVM tx (no broadcast) |
| `wallet_sign` | EIP-191 message signing |
| `wallet_sign_typed_data` | EIP-712 typed data signing |
| `wallet_transactions` | EVM tx history |
| `wallet_sol_transfer` | **Broadcast** Solana tx |
| `wallet_sol_sign_transaction` | Sign Solana tx (no broadcast) |
| `wallet_sol_sign` | Solana message signing |
| `wallet_sol_transactions` | Solana tx history |
| `wallet_get_policy` | Check policy status |
| `wallet_propose_policy` | Propose policy (sends to UI) |

## Key Facts

- **Gas is sponsored** on EVM chains — user doesn't need ETH for gas
- **Policy default: OFF** (allow-all). Only when user enables policy do transactions need UI confirmation
- **Supported EVM chains**: ethereum, base, arbitrum, optimism, polygon, linea, bsc, avalanche, fantom, gnosis, zksync, scroll, blast, mantle, celo, aurora
- **Balance sources**: DeBank (EVM), Birdeye (Solana), wallet-service (fallback)

## Workflow

### Check Balances
1. Single chain: `wallet_balance(chain="base")` or `wallet_sol_balance()`
2. All at once: `wallet_get_all_balances()`

### Send Transaction (EVM)
1. Check balance: `wallet_balance(chain=...)`
2. Transfer: `wallet_transfer(to=..., amount=..., chain_id=...)`
3. Verify: `wallet_transactions()` or check balance again

### Policy Management
1. Check: `wallet_get_policy(chain_type="ethereum")`
2. If user wants to enable: `wallet_propose_policy(chain_type, rules, title, description)`
3. User confirms in UI → policy applied

### Standard Wildcard Policy (when needed)
```
rules = [
  {"name": "Deny key export", "method": "exportPrivateKey", "conditions": [], "action": "DENY"},
  {"name": "Allow all", "method": "*", "conditions": [], "action": "ALLOW"},
]
```

### Policy Modes — CRITICAL DECISION TABLE

⚠️ **DENY > ALLOW in Privy.** `DENY *` overrides ALL ALLOW rules. NEVER mix them.

| Mode | Rules | Effect |
|------|-------|--------|
| **Allow-all** (default) | `DENY exportPrivateKey` + `ALLOW *` | Everything allowed except key export |
| **Deny-all** (lockdown) | `DENY exportPrivateKey` + `DENY *` | Nothing works. No ALLOW rules! |
| **Whitelist** (selective) | `DENY exportPrivateKey` + specific ALLOW rules only | Only whitelisted ops work, rest implicitly denied |

### Mode 1: Allow-All (Standard Wildcard)
```
rules = [
  {"name": "Deny key export", "method": "exportPrivateKey", "conditions": [], "action": "DENY"},
  {"name": "Allow all", "method": "*", "conditions": [], "action": "ALLOW"},
]
```

### Mode 2: Deny-All (Lockdown)
```
rules = [
  {"name": "Deny key export", "method": "exportPrivateKey", "conditions": [], "action": "DENY"},
  {"name": "Deny all actions", "method": "*", "conditions": [], "action": "DENY"},
]
# ⚠️ NO ALLOW rules here — DENY * would override them!
```

### Mode 3: Whitelist (Selective Allow)
```
rules = [
  {"name": "Deny key export", "method": "exportPrivateKey", "conditions": [], "action": "DENY"},
  {"name": "Allow transfer to Uniswap", "method": "eth_sendTransaction", "conditions": [
    {"field_source": "ethereum_transaction", "field": "to", "operator": "eq", "value": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"}
  ], "action": "ALLOW"},
]
# ⚠️ NO "DENY *" here! enabled=true already denies everything not ALLOWed.
# Adding DENY * would override the ALLOW rules above (DENY > ALLOW).
```

## Privy Policy Rules — Key Constraints

| Rule | Details |
|------|---------|
| **Default behavior** | `enabled=true` → deny-all unless explicitly ALLOWed |
| **DENY > ALLOW** | DENY always wins when both match |
| **Empty conditions** | Only `exportPrivateKey` and `*` (wildcard) allow `conditions: []` |
| **TX methods need conditions** | `eth_sendTransaction`, `eth_signTransaction`, `eth_signTypedData_v4`, `eth_signUserOperation`, `signAndSendTransaction`, etc. ALL require ≥1 condition |
| **Valid field_sources** | EVM: `ethereum_transaction` (to/value/chain_id), `ethereum_calldata` (function_name), `ethereum_typed_data_domain` (chainId/verifyingContract), `ethereum_typed_data_message`, `system` |
| **Valid operators** | `eq`, `gt`, `gte`, `lt`, `lte`, `in` (array, max 100 values) |
| **Dual chain** | Call `wallet_propose_policy` TWICE for EVM + Solana |

## Gotchas

- `wallet_propose_policy` sends SSE event to frontend — needs streaming context
- DeBank/Birdeye keys are auto-injected by sc-proxy
- `wallet_balance` requires `chain` param — use `wallet_get_all_balances` for discovery
- For both EVM + Solana policy, call `wallet_propose_policy` TWICE
