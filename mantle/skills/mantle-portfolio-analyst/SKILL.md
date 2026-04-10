---
name: mantle-portfolio-analyst
description: Use when a Mantle task needs wallet balances, token holdings, allowance exposure, or unlimited-approval review before a DeFi or security decision.
---

# Mantle Portfolio Analyst

## Overview

Build deterministic, read-only wallet analysis on Mantle. Enumerate balances and allowances, then highlight approval risk in a structured report.

## Workflow

1. Confirm inputs:
   - `wallet_address`
   - `network` (`mainnet` or `sepolia`)
   - optional token/spender scope
2. Validate requested wallet and chain context:
   - `mantle-cli registry validate <address> --json`
   - `mantle-cli chain info --json`
   - `mantle-cli chain status --json`
3. Determine analysis scope:
   - token list from user input or `mantle://registry/tokens`
   - spender list from user input or `mantle://registry/protocols`
4. Fetch native balance with `mantle-cli account balance <address> --json`.
5. Fetch ERC-20 balances with `mantle-cli account token-balances <address> --tokens <list> --json`.
6. Fetch token-spender allowances with `mantle-cli account allowances <owner> --pairs <token:spender,...> --json`.
7. If a token's metadata is missing, use `mantle-cli token info <token> --json` for that token and keep missing fields as `unknown` when unresolved.
8. Classify approval risk using these rules:
   - `low`: allowance is zero, or tightly bounded and clearly below wallet balance/expected use.
   - `medium`: allowance is non-zero and larger than immediate expected use, but still bounded.
   - `high`: allowance is very large relative to expected use, or intentionally broad with unclear user intent.
   - `critical`: `is_unlimited=true` from tool output, or allowance equals/near-max integer (value >= 2^255).
   - Always include a rationale sentence with each risk label.
   - Mark spender trust as `unknown` unless verified from `mantle://registry/protocols` or user-confirmed.
   - Highlight all `high` and `critical` approvals at top of summary.
   - If token decimals are missing, classify using raw value and downgrade confidence.
9. Return a formatted report with findings, confidence, and explicit coverage/partial gaps.

## Guardrails

- Use `mantle-cli` read-only commands only for this skill (`mantle-cli account balance`, `mantle-cli account token-balances`, `mantle-cli account allowances`, `mantle-cli token info`, chain/address validation helpers). Do NOT enable or connect to the MCP server.
- Stay read-only; do not construct or send transactions.
- Do not reference direct JSON-RPC calls (`eth_*`) as if they are callable tools in this workflow.
- Do not guess token decimals or symbols if calls fail.
- Validate checksummed addresses for wallet, token, and spender. If an address fails checksum validation or is the zero address (`0x0000...0000`), stop and return an error message explaining the issue -- do not proceed with queries against an invalid address.
- Mark missing token metadata as `unknown` and continue.
- If RPC responses are inconsistent, report partial coverage explicitly.
- Keep both `raw` and `normalized` values in output. Prefer normalized values from tool responses; convert manually only when decimals are explicitly known. If decimals are unavailable, keep raw only and lower confidence.
- Verify response chain/network matches the requested input. Detect and report partial failures via tool-level `partial` flags and per-entry `error` fields.
- If scope is unknown and cannot be discovered, report that coverage is partial instead of inventing token or spender targets.

## Report Format

Always use this exact report structure, even when the user query is scoped to a specific token, spender, or subset. Omit sections only if they are genuinely empty (e.g., no allowances found), but keep all section headers. For scoped queries, populate only the relevant entries within each section and note the applied filter in the summary.

```text
Mantle Portfolio Report
- wallet:
- network:
- chain_id:
- collected_at_utc:

Native Balance
- MNT:

Token Balances
- token: <symbol_or_label>
  address:
  balance_raw:
  decimals:
  balance_normalized:

Allowance Exposure
- token:
  spender:
  allowance_raw:
  allowance_normalized:
  risk_level: low | medium | high | critical
  rationale:

Summary
- tokens_with_balance:
- allowances_checked:
- unlimited_or_near_unlimited_count:
- key_risks:
- confidence:
```

## References

- `references/rpc-readonly-workflow.md`
- `references/allowance-risk-rules.md`
