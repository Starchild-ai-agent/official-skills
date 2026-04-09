---
name: wallet
version: 3.1.0
description: "Multi-chain wallet — balances, transfers, signing, policy (EVM + Solana)"
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

Multi-chain wallet for EVM (6 chains) + Solana. Balances, transfers, signing, policy management.

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
- **Supported EVM chains**: ethereum, base, arbitrum, optimism, polygon, linea
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

## Gotchas

- `wallet_propose_policy` sends SSE event to frontend — needs streaming context
- DeBank/Birdeye keys are auto-injected by sc-proxy
- `wallet_balance` requires `chain` param — use `wallet_get_all_balances` for discovery
- Policy validation: `eth_signTypedData_v4` requires at least one condition
- For both EVM + Solana policy, call `wallet_propose_policy` TWICE
