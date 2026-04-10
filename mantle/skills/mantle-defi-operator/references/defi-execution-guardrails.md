# DeFi Pre-Execution Guardrails

Apply these controls before any potential state-changing DeFi action.

## Tool discovery via Capability Catalog

- Read `mantle://registry/capabilities` to discover available tools before constructing any plan.
- Use `category` to filter: `query` for reads, `analyze` for insights, `execute` for transaction building.
- Use `auth` to check wallet requirements: `required` tools need a wallet address, `none` tools don't.
- Use `workflow_before` to understand call ordering (e.g., `getSwapQuote` before `buildSwap`).
- For simple read-only tasks (query/analyze), the Capability Catalog is sufficient — no skill loading needed.
- For execution planning, continue with the guardrails below.

## Capability boundary (CLI-only)

- All on-chain operations use `mantle-cli` commands with `--json`. Do NOT enable or connect to the MCP server.
- The CLI is read-focused for queries and builds unsigned transactions for writes — it does not sign, broadcast, deploy, or execute transactions.
- This skill must stop at analysis + plan generation.
- Never fabricate tx hashes, receipts, or settlement outcomes.

## Coordination boundary

- Use this skill to assemble a final plan, not to replace specialized address, risk, or portfolio skills.
- Route address trust to `mantle-address-registry-navigator`.
- Route pass/warn/block verdicts to `$mantle-risk-evaluator`.
- Route allowance and balance evidence to `$mantle-portfolio-analyst` when approval scope or wallet coverage matters.

## Address trust

- Resolve execution-ready token/router/pool/position-manager addresses from the shared `mantle-address-registry-navigator` registry.
- Mark the plan as blocked for unverified or malformed addresses.
- Mention the selected registry key in the final handoff.
- Discovery-only protocols may be mentioned for comparison, but they are not execution targets until their contracts are verified.
- Live metrics may influence ranking, but they never establish address trust.

## Intent completeness

- Ensure operation type, token amounts, recipient, slippage cap, and deadline are present.
- Mark the plan as blocked if any mandatory field is missing.

## Risk coupling

- Require latest preflight verdict from `$mantle-risk-evaluator` when available.
- For `warn`/`high-risk` outcomes, require explicit user confirmation.
- For `block` outcomes, do not produce an execution-ready plan.

## Allowance controls

- Prefer minimal required approval over unlimited approval.
- Use `$mantle-portfolio-analyst` when allowance scope, spender exposure, or balance coverage needs read-only evidence.
- If unlimited approval is requested, require explicit user acknowledgement.
- Include an explicit allowance re-check in the external execution checklist.

## Execution handoff integrity

- Use deterministic route and calldata inputs from selected quote/liquidity context.
- Record required call sequence and parameter values for the external executor.
- Define post-execution reconciliation checks (balances/allowances/slippage) to run after user-confirmed execution.
