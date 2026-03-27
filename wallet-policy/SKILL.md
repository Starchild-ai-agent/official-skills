---
name: wallet-policy
version: 1.1.0
description: "Generate Privy wallet policy rules from natural language."
metadata:
  starchild:
    emoji: "🛡️"
    skillKey: wallet-policy
user-invocable: true
---

# Wallet Policy Generator

Generate wallet security policy rules and propose them via `wallet_propose_policy`. **Always use the tool — never output rules as code blocks.**

For dual-chain requests (EVM + Solana), call `wallet_propose_policy` **twice**.

## Policy Engine Basics

1. **No policy = allow-all.** Once attached, it's **deny-by-default** (unmatched requests denied).
2. **DENY wins** over ALLOW if both match.
3. **Multiple conditions = AND** (all must match).
4. **Solana**: every instruction must individually match an ALLOW rule.

## Default: Wildcard Policy

For any dapp/service, propose this unless user explicitly requests tighter rules:

```
wallet_propose_policy(
  chain_type="ethereum",
  title="Enable Wallet Operations",
  description="Allows all transactions. Blocks key export. Each tx still requires user approval.",
  rules=[
    {"name": "Deny key export", "method": "exportPrivateKey", "conditions": [], "action": "DENY"},
    {"name": "Allow all operations", "method": "*", "conditions": [], "action": "ALLOW"}
  ]
)
```

## Rule Schema

```json
{"name": "string (1-50 chars)", "method": "<method>", "conditions": [<condition>...], "action": "ALLOW|DENY"}
```

**Methods**: `eth_sendTransaction`, `eth_signTransaction`, `eth_signTypedData_v4`, `eth_signUserOperation`, `eth_sign7702Authorization`, `signTransaction` (Solana), `signAndSendTransaction` (Solana), `exportPrivateKey`, `*` (wildcard)

Note: `personal_sign` and `signMessage` are NOT valid policy methods. Use `*` to cover them.

**Condition**: `{"field_source": "<source>", "field": "<name>", "operator": "<op>", "value": "<string>"|[...]}`

**Operators**: `eq`, `gt`, `gte`, `lt`, `lte`, `in` (array, max 100). **Never use `in_condition_set`** — use `in` instead.

## Condition Types

### EVM

| Source | Fields | Notes |
|--------|--------|-------|
| `ethereum_transaction` | `to`, `value` (wei string), `chain_id` (string) | For `eth_sendTransaction/eth_signTransaction` |
| `ethereum_calldata` | `<fn>.<param>` (e.g. `transfer.to`) | Requires `abi` field in condition |
| `ethereum_typed_data_domain` | `chainId`, `verifyingContract` | For `eth_signTypedData_v4` |
| `ethereum_typed_data_message` | Field from typed data | Requires `typed_data` field |
| `ethereum_7702_authorization` | `contract` | For `eth_sign7702Authorization` |

### Solana

| Source | Fields | Notes |
|--------|--------|-------|
| `solana_program_instruction` | `programId` | Match by program |
| `solana_system_program_instruction` | `instructionName`, `Transfer.to`, `Transfer.lamports` | 1 SOL = 10^9 lamports |
| `solana_token_program_instruction` | `instructionName`, `TransferChecked.mint/amount/destination` | SPL token transfers |

### Special
| Source | Fields |
|--------|--------|
| `system` | `current_time` (ISO 8601, with `gt`/`lt` for time windows) |

## Common Recipes

### EVM Address Allowlist
```json
{"name": "Allow treasury", "method": "eth_sendTransaction",
 "conditions": [{"field_source": "ethereum_transaction", "field": "to", "operator": "in", "value": ["0xAddr1...", "0xAddr2..."]}],
 "action": "ALLOW"}
```

### EVM Value Cap (≤ 1 ETH)
```json
{"conditions": [{"field_source": "ethereum_transaction", "field": "value", "operator": "lte", "value": "1000000000000000000"}]}
```

### Chain Restriction (Arbitrum only)
```json
{"conditions": [{"field_source": "ethereum_transaction", "field": "chain_id", "operator": "eq", "value": "42161"}]}
```

### Solana SOL Transfer Cap (≤ 1 SOL)
```json
{"name": "Cap SOL", "method": "signAndSendTransaction",
 "conditions": [
   {"field_source": "solana_system_program_instruction", "field": "instructionName", "operator": "eq", "value": "Transfer"},
   {"field_source": "solana_system_program_instruction", "field": "Transfer.lamports", "operator": "lte", "value": "1000000000"}
 ], "action": "ALLOW"}
```

### Solana USDC Allowlist
```json
{"conditions": [
  {"field_source": "solana_token_program_instruction", "field": "TransferChecked.mint", "operator": "eq", "value": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"},
  {"field_source": "solana_token_program_instruction", "field": "TransferChecked.destination", "operator": "in", "value": ["RecipientATA..."]}
]}
```

## Wei / Lamports Reference

| Amount | Wei (EVM) | Lamports (SOL) | USDC (6 dec) |
|--------|-----------|----------------|--------------|
| 0.01 | 10000000000000000 | 10000000 | 10000 |
| 0.1 | 100000000000000000 | 100000000 | 100000 |
| 1 | 1000000000000000000 | 1000000000 | 1000000 |
| 100 | 100000000000000000000 | 100000000000 | 100000000 |

## Chain IDs

| Chain | ID |
|-------|----|
| Ethereum | 1 |
| Polygon | 137 |
| Arbitrum | 42161 |
| Optimism | 10 |
| Base | 8453 |
| Linea | 59144 |

## Do NOT

- Output rules as code blocks — always call `wallet_propose_policy`
- Use `in_condition_set` — use `in` operator instead
- Mix EVM/Solana field_sources with wrong chain_type
- Use `ethereum_transaction` with `eth_signTypedData_v4` — use `ethereum_typed_data_domain`
- Use custom restrictive rules unless user explicitly asks — default to wildcard
