---
name: wallet
version: 3.5.1
description: |
  Multi-chain wallet: EVM and Solana balances, transfers, signing, and policy.

  Use when checking balances, sending tokens, signing typed data, or proposing a wallet policy (e.g. send 10 USDC on Base, sign EIP-712, Solana balance).
author: starchild
tags: [wallet, evm, solana, transfer, sign, policy, debank, birdeye]
delivery: script
metadata:
  starchild:
    emoji: 💰
    skillKey: wallet
---

# 💰 Wallet Skill

Multi-chain wallet for EVM (DeBank-supported chains) + Solana. Balances,
transfers, signing, and policy management. **Script skill** — call the functions
below via bash; no wallet tools are registered.

## How to call

All read/transfer/sign operations are Python functions in `core.skill_tools.wallet`.
Run them from bash and read the JSON result:

```bash
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_balance(chain='base')))"
```

The **one** operation that is NOT a script function is proposing a wallet policy
— it needs to render a confirmation card in the UI, so it goes through the native
`frontend_action` tool (see Policy Management below).

## Functions (`from core.skill_tools import wallet`)

| Function | Description |
|----------|-------------|
| `wallet_info()` | Get all wallet addresses |
| `wallet_balance(chain, address="", asset="")` | EVM balance on a chain (DeBank). `chain` required |
| `wallet_sol_balance(address="", asset="")` | Solana balance (Birdeye) |
| `wallet_get_all_balances(evm_address="", sol_address="")` | All chains at once |
| `wallet_transfer(to, amount, chain_id=1, data="", **kw)` | **Broadcast** EVM tx (gas sponsored by default) |
| `wallet_sign_transaction(to, amount, chain_id=1, data="", **kw)` | Sign EVM tx (no broadcast) |
| `wallet_sign(message)` | EIP-191 message signing |
| `wallet_sign_typed_data(domain, types, primaryType, message)` | EIP-712 typed data signing |
| `wallet_transactions(chain="ethereum", asset="", limit=20)` | EVM tx history |
| `wallet_sol_transfer(transaction, caip2=...)` | **Broadcast** Solana tx (base64) |
| `wallet_sol_sign_transaction(transaction)` | Sign Solana tx (no broadcast) |
| `wallet_sol_sign(message)` | Solana message signing |
| `wallet_sol_transactions(chain="solana", asset="sol", limit=20)` | Solana tx history |
| `wallet_get_policy(chain_type="ethereum")` | Check policy status |
| `validate_and_clean_rules(rules, chain_type)` | Pre-validate policy rules before proposing |

## Key Facts

- **Amounts are in wei** for EVM (`wallet_transfer` / `wallet_sign_transaction`). 0.01 ETH = `10000000000000000`. For ERC-20 token sends, `amount` is `0` (native) and the transfer is encoded in `data` calldata.
- **Gas is sponsored by default** on EVM chains — user doesn't need native tokens for gas. Falls back to user-paid if unavailable. Pass `sponsor=False` to pay gas from wallet balance.
- **Policy default: OFF** (allow-all). Only when policy is enabled do transactions need UI confirmation.
- **Supported EVM chains**: All DeBank-supported chains. Common names auto-mapped (e.g. `avalanche` → `avax`, `bsc` → `bsc`, `zksync` → `era`). The 16 common chains (ethereum, base, arbitrum, optimism, polygon, linea, bsc, avalanche, fantom, gnosis, zksync, scroll, blast, mantle, celo, aurora) have built-in fallback mapping.
- **Balance sources**: DeBank (EVM), Birdeye (Solana), wallet-service (fallback). DeBank/Birdeye keys are auto-injected by sc-proxy.

## Workflows

### Check balances
```bash
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_balance(chain='base')))"
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_get_all_balances()))"
```

### Send a transaction (EVM)
Always verify balance before, and the result/history after.
```bash
# 1. check
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_balance(chain='base')))"
# 2. transfer (amount in wei)
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_transfer(to='0x...', amount='10000000000000000', chain_id=8453)))"
# 3. verify
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_transactions(chain='base')))"
```

### Sign EIP-712 typed data
```bash
python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_sign_typed_data(domain={...}, types={...}, primaryType='Permit', message={...})))"
```

## Policy Management

Checking policy is a script function; **proposing** a policy uses the native
`frontend_action` tool (it renders a signature card in the UI — a script cannot).

1. Check current policy:
   ```bash
   python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.wallet_get_policy(chain_type='ethereum')))"
   ```
2. (Optional) pre-validate rules:
   ```bash
   python3 -c "from core.skill_tools import wallet; import json; print(json.dumps(wallet.validate_and_clean_rules([...], 'ethereum')))"
   ```
3. Propose — call the **`frontend_action` tool** (not a script):
   ```
   frontend_action(action_type="update_wallet_policy", chain_type="ethereum", rules=[...])
   ```
   The user confirms + signs in the UI. **Call once per chain** (EVM + Solana = two calls).

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
| **Dual chain** | Call `frontend_action(action_type="update_wallet_policy", ...)` TWICE for EVM + Solana |

## Gotchas

- Policy proposal goes through the `frontend_action` tool — needs an active SSE session (won't work from a background task).
- `wallet_balance` requires `chain` — use `wallet_get_all_balances` for discovery.
- For both EVM + Solana policy, call `frontend_action` TWICE (one per chain_type).
