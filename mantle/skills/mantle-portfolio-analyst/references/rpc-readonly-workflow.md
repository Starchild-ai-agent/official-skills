# RPC Read-Only Workflow

Use this guide to gather wallet balances and allowances through `mantle-cli` read-only commands only. Do NOT enable or connect to the MCP server.

## Required inputs

- Wallet address
- Network (`mainnet` or `sepolia`)
- Token set and spender set (user-provided or discovered)

## Call sequence

1. `mantle-cli registry validate <wallet> --json` for wallet format checks.
2. `mantle-cli chain info --json` (and `mantle-cli chain status --json` when available) to confirm network context.
3. `mantle-cli account balance <wallet> --json`
4. `mantle-cli account token-balances <wallet> --tokens <token1>,<token2>,... --json`
5. `mantle-cli account allowances <wallet> --pairs <token1>:<spender1>,<token2>:<spender2> --json`
6. Optional metadata backfill: `mantle-cli token info <token> --json` for tokens with missing symbol/decimals.

## Token and spender discovery

- Prefer explicit user scope first.
- If token scope is missing, read `mantle://registry/tokens` and select a bounded set for coverage.
- If spender scope is missing, read `mantle://registry/protocols` and extract known routers/pools.
- Use `mantle-cli token resolve <symbol> --json` for symbols outside the current scoped list before balance/allowance calls.
- If scope is still unknown, report that coverage is partial instead of inventing targets.

## Normalization rules

- Prefer normalized values already returned by CLI JSON output.
- Convert raw values manually only when decimals are explicitly known.
- Keep both `raw` and `normalized` values in output.
- If decimals are unavailable, keep raw only and mark confidence lower.

## Reliability checks

- Verify response chain/network matches requested input (`mainnet` or `sepolia`).
- Retry transient read failures with bounded attempts; do not switch to guessed tokens/spenders.
- Detect and report partial failures via tool-level `partial` flags and per-entry `error` fields.
- Include `collected_at_utc` values from CLI outputs in the final report.
