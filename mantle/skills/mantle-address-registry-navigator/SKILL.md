---
name: mantle-address-registry-navigator
description: Use when a Mantle task needs a verified contract or token address, whitelist validation, anti-phishing checks, or safe registry-backed lookup before onchain interaction.
---

# Mantle Address Registry Navigator

## Overview

Resolve addresses from trusted sources only and fail closed when data is missing or stale. Never synthesize contract addresses from memory.

## Source Priority

1. `mantle-cli token resolve <symbol> --json` for token symbol/name requests.
2. `mantle-cli registry resolve <identifier> --json` for contract key, alias, or label requests.
3. Local registry file: `assets/registry.json` (fallback/manual cross-check only).
4. If no source provides a verified match, stop and return a blocked result.
5. **If CLI commands fail** (connection error, tool not found, or offline mode), skip to the local registry fallback (step 3) and cap confidence at `medium`. Note the CLI unavailability in the response `notes` field.

## Lookup Workflow

1. Normalize the request:
   - `network` (`mainnet` or `sepolia`; local registry fallback maps `sepolia` to `testnet`)
   - `identifier` (contract key, symbol, or alias)
   - `category` (system, token, bridge, `defi`, or `any`)
   - optional `protocol_id` + `contract_role` when a DeFi request names a protocol but not a registry key
2. Resolve candidates via source priority. For local DeFi fallback, prefer exact `key` matches first, then exact `protocol_id` + `contract_role`.
3. Validate the chosen candidate with `mantle-cli registry validate <address> --json` and registry metadata:
   - `valid_format` is `true`.
   - Address is not the zero address.
   - Entry environment matches request.
   - Entry status is usable (`active`) for execution.
   - Entry has provenance (`source.url` and `source.retrieved_at`).
   - If the request names an intended action, the entry `supports` that action.
4. Return one canonical result with provenance metadata.
5. If multiple candidates remain ambiguous, ask a clarifying question instead of choosing arbitrarily.
6. **Verification requests** (user supplies an address and asks if it is official): First resolve the canonical address for the named contract/token using the same source priority (tools first, then local registry). Then compare the user-supplied address against the resolved canonical address. Return the Verification Mismatch format.

## Safety Rules

- Never output guessed addresses.
- Never treat user-supplied addresses as trusted without registry/tool verification.
- Mark deprecated or paused contracts as non-executable.
- Never return placeholder/template values from `assets/registry.json` (for example `REPLACE_WITH_EIP55_CHECKSUM_ADDRESS`).
- If registry freshness is unknown, label confidence as `low` and request manual confirmation.
- If a DeFi request names a protocol and multiple active entries exist for that protocol (even if they share the same `contract_role`), stop and ask which specific contract the user needs. Use the Clarification Needed format and list all matching candidates.

## Response Format

### Successful Lookup

```text
Address Resolution Result
- identifier:
- network:
- address:
- category:
- status:
- source_url:
- source_retrieved_at:
- confidence: high | medium | low
- notes:
```

### Blocked / Not Found

When no verified entry exists, return this structure instead of guessing:

```text
Address Resolution Result
- identifier: [requested identifier]
- network: [requested network]
- address: BLOCKED
- category: [requested or inferred category]
- status: not_found
- source_url: N/A
- source_retrieved_at: N/A
- confidence: none
- notes: [why lookup failed — e.g., "No verified entry in tools or local registry for this identifier."]
```

### Verification Mismatch (Anti-Phishing)

When the user supplies an address and asks whether it is official, compare against the registry and return:

```text
Address Verification Result
- queried_address: [user-supplied address]
- identifier: [matched registry key, if any]
- network: [network]
- registry_address: [address from registry, or NONE]
- match: true | false
- status: [registry entry status, or not_found]
- source_url: [registry source URL, or N/A]
- source_retrieved_at: [registry timestamp, or N/A]
- confidence: high | medium | low
- notes: [explanation — e.g., "Address does not match the verified Aave v3 Pool entry."]
```

### Clarification Needed

When multiple candidates remain and the request is ambiguous, do NOT pick one. Instead respond with:

```text
Clarification Needed
- identifier: [requested identifier]
- network: [network]
- candidates:
  1. [key] — [label] ([contract_role]) — [address]
  2. [key] — [label] ([contract_role]) — [address]
- question: [ask the user which specific contract they need]
```

## Resources

- `assets/registry.json`
- `references/address-registry-playbook.md`
