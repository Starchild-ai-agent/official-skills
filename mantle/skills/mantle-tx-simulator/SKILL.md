---
name: mantle-tx-simulator
description: Use when a Mantle transaction needs pre-signing simulation evidence, state-diff review, revert analysis, or a WYSIWYS explanation before execution.
---

# Mantle Tx Simulator

## Overview

Prepare simulation handoff packages for external backends and translate returned technical diffs into user-readable expected outcomes before signing or execution.

## Workflow

1. Normalize simulation request:
   - network
   - from/to/value/data
   - optional bundle/multicall context
2. Select an external simulation backend using `references/simulation-backends.md`.
3. Capture pre-state:
   - relevant token balances
   - allowance values
   - nonce and gas context
4. Produce an external simulation handoff package:
   - tx payload and network
   - required pre-state context
   - requested outputs (status/gas/logs/diffs)
5. After external execution evidence is provided, collect:
   - success/revert
   - gas estimate
   - logs/events
   - state diffs
6. Convert technical result into WYSIWYS summary with `references/wysiwys-template.md`.
   - **ALWAYS produce a WYSIWYS section**, even before external simulation results arrive.
   - If no external evidence exists yet, produce a **preliminary WYSIWYS** based on the request parameters, clearly labeled: "PRELIMINARY — not yet verified by simulation."
   - Pre-simulation WYSIWYS must still populate `what_user_gives`, `what_user_gets_min` (mark as "pending simulation"), and `plain_language_outcome`.
7. If simulation evidence is missing, fails, or confidence is low, return `do_not_execute`.
   - Set `do_not_execute_reason` with a specific explanation (e.g., "No external simulation evidence provided", "Simulation reverted", "Incomplete calldata").
   - **Still produce the full Simulation Report output format** even when returning `do_not_execute`.

## Guardrails

- This skill is read-only: it cannot execute transaction simulations directly. Use `mantle-cli` commands for any on-chain reads. Do NOT enable or connect to the MCP server.
- Never broadcast real transactions from this skill.
- Never claim a simulation has run unless external backend output is provided.
- Distinguish simulated estimate from guaranteed execution result.
- If token decimals/pricing context is incomplete, state uncertainty explicitly.
- For bundle flows, describe each step and net effect.
- If asked to run simulation via CLI tools, explain that `mantle-cli` has no tx simulation execution tool and provide external handoff instructions.
- **Always output the full Simulation Report format** for every response, regardless of whether simulation evidence exists, the request is incomplete, or execution is declined. Never respond with only prose — always include the structured report.

## Output Format

```text
Mantle Simulation Report
- execution_mode: external_simulator_handoff
- backend:
- environment:
- simulated_at_utc: <external timestamp if available>
- status: pending_external_simulation | success | revert | inconclusive
- simulation_artifact: <external link/id if available>

State Diff Summary
- assets_debited:
- assets_credited:
- approvals_changed:
- contract_state_changes:

Execution Estimates (simulated — not guaranteed)
- gas_estimate:
- estimated_fee_native:
- slippage_or_price_impact_note:

WYSIWYS
- plain_language_outcome:
- what_user_gives:
- what_user_gets_min:
- do_not_execute_reason: <empty if safe>
- disclaimer: Simulation results are estimates only and do not guarantee on-chain execution outcomes.
```

## References

- `references/simulation-backends.md`
- `references/wysiwys-template.md`
