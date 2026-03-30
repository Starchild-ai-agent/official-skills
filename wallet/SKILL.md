---
name: wallet
version: 1.1.0
description: "Multi-chain wallet operations - balance, transfers, signing, policy management via Privy Server Wallets (EVM + Solana)"
tools:
  - wallet_info
  - wallet_transfer
  - wallet_sign_transaction
  - wallet_sign
  - wallet_sign_typed_data
  - wallet_balance
  - wallet_get_all_balances
  - wallet_transactions
  - wallet_sol_transfer
  - wallet_sol_sign_transaction
  - wallet_sol_sign
  - wallet_sol_balance
  - wallet_sol_transactions
  - wallet_get_policy
  - wallet_propose_policy
metadata:
  starchild:
    emoji: "💰"
    skillKey: wallet
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
---

# Wallet

Agent on-chain wallets (one per chain: EVM + Solana). Auth is automatic via Fly OIDC — no API keys needed.

## Tools Quick Reference

### Multi-Chain
- `wallet_info()` — all wallet addresses
- `wallet_get_all_balances()` — **PRIMARY** complete portfolio across ALL chains with USD values
- `wallet_get_policy(chain_type)` — current policy status/rules

### EVM
- `wallet_balance(chain)` — balance on specific chain. **chain is REQUIRED** (`ethereum`, `base`, `arbitrum`, `optimism`, `polygon`, `linea`)
- `wallet_transactions(chain, limit)` — recent tx history (default: ethereum, limit 20)
- `wallet_transfer(to, amount, chain_id, data)` — sign + broadcast on-chain (policy-gated)
- `wallet_sign_transaction(to, amount, ...)` — sign WITHOUT broadcasting
- `wallet_sign(message)` — EIP-191 personal_sign
- `wallet_sign_typed_data(domain, types, primaryType, message)` — EIP-712

### Solana
- `wallet_sol_balance()` — SOL + SPL tokens with USD values
- `wallet_sol_transactions(limit)` — recent tx history
- `wallet_sol_transfer(transaction, caip2)` — sign + broadcast (base64 tx)
- `wallet_sol_sign_transaction(transaction)` — sign WITHOUT broadcasting
- `wallet_sol_sign(message)` — sign base64 message

## Key Rules

**EVM amounts are in wei** (strings): `"1000000000000000000"` = 1 ETH. Formula: `wei = eth * 10^18`

**Polygon**: Use `asset="pol"` NOT `"matic"`. Call `wallet_balance(chain="polygon", asset="pol")`.

**Contract calls**: `wallet_transfer(to=contract, amount="0", data="0x...", chain_id=...)` — amount is "0" for non-payable calls.

**Asset discovery**: Omit `asset` parameter to discover ALL tokens on a chain. Use `wallet_get_all_balances()` for everything at once.

## Common Workflows

**Pre-Transfer**: `wallet_info()` → `wallet_balance(chain)` → `wallet_transfer(to, amount)` → `wallet_transactions(limit=1)` to confirm.

**Full Portfolio**: `wallet_get_all_balances()` — covers Ethereum, Base, Arbitrum, Optimism, Polygon, Linea, Solana in one call.

**Prove Ownership**: `wallet_sign(message="...")` (EVM) or `wallet_sol_sign(message="...")` (Solana).

## Chain IDs

| Chain | ID | Native |
|-------|----|--------|
| Ethereum | 1 | eth |
| Base | 8453 | eth |
| Optimism | 10 | eth |
| Arbitrum | 42161 | eth |
| Polygon | 137 | **pol** |
| Linea | 59144 | eth |

Solana CAIP-2: mainnet `solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp`, devnet `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1`

## Policy & Security

- **No policy = allow-all**. Once enabled → deny-by-default, only ALLOW rules pass.
- Privy TEE enforced — even compromised agents can't bypass policy.
- `wallet_propose_policy()` proposes rules; user must approve in frontend.

## Errors

| Error | Fix |
|-------|-----|
| "Not running on a Fly Machine" | Wallet requires Fly deployment |
| "Policy violation" | Check allowlist/limits via `wallet_get_policy()` |
| HTTP 404 | Wallet not created yet |
| HTTP 403 | OIDC token expired — auto-refreshes, retry |
