---
name: mantle-risk-evaluator
description: Use when a Mantle state-changing intent needs pre-execution slippage, liquidity, address-safety, allowance-scope, or gas/deadline checks.
---

# Mantle Risk Evaluator

## Overview

Run a mandatory pre-flight checklist and return a clear `pass`, `warn`, or `block` verdict. Prevent unsafe execution when any critical condition fails.

## Workflow

1. Normalize intent input:
   - operation type
   - token in/out and amount
   - target protocol/router/pool addresses
   - user risk parameters (slippage cap, deadline, max gas preference)
2. Execute the checklist (see Checklist section below).
3. Apply the threshold table (see Thresholds section below). Use user-specified parameters first; use defaults only when user constraints are absent.
4. Classify each item:
   - `pass`
   - `warn`
   - `fail`
5. Produce final verdict:
   - `pass`: no fails, optional warns.
   - `warn`: no critical fails, but user confirmation required.
   - `block`: one or more critical fails.

## Mandatory Input Fields

All of the following MUST be present in the intent. If any is missing, immediately set the final verdict to `block` with blocking reason "mandatory field missing":

- `operation_type`
- `chain/environment`
- token in/out and amount
- target contract/router/pool address

## Checklist

### 1. Slippage check
- The "proposed slippage" is the slippage tolerance the user (or protocol) has set for this transaction.
- ALWAYS compare the proposed slippage against the default threshold table below, regardless of whether the user set it themselves.
- A user choosing a high slippage tolerance does NOT make it safe -- the default thresholds still apply.
- If the user also specifies a separate, stricter cap, apply whichever is more restrictive.
- Fail when proposed slippage exceeds the fail threshold (> 1.0% by default).

### 2. Liquidity depth check
- Estimate price impact from quote/simulation context.
- Warn on moderate impact, fail on severe impact (see thresholds).
- If liquidity data is unavailable, set warn with note "reduced confidence".

### 3. Address safety check
- Verify all addresses against trusted registry/tooling.
- `pass`: trusted and verified source.
- `warn`: unknown but not explicitly flagged.
- `fail`: flagged, blacklisted, or malformed address.

### 4. Allowance scope check
- Detect approvals broader than required for intended amount.
- `pass`: existing allowance fits intended spend scope.
- `warn`: allowance materially larger than intended spend.
- `fail`: new or existing near-unlimited approval without explicit user confirmation. Near-unlimited heuristic: raw allowance `>= 2^255`.

### 5. Gas and deadline sanity
- Check gas estimate reasonableness versus recent baseline.
- Check transaction deadline is not stale and not excessively long.
- Apply thresholds below.

## Thresholds (defaults when user has not specified)

| Check | Warn | Fail |
|---|---|---|
| Slippage | > 0.5% | > 1.0% |
| Estimated price impact | > 2% | > 5% |
| Deadline horizon | > 20 minutes | > 60 minutes |
| Gas deviation from baseline | > 20% | > 40% |

## Verdict Rules

- Any `fail` in ANY checklist item => final verdict **block**.
- No `fail` and at least one `warn` => final verdict **warn**.
- All checks `pass` => final verdict **pass**.

### Confidence policy
- `high`: all required signals present and consistent.
- `medium`: one non-critical signal missing.
- `low`: key signals missing (e.g., no liquidity data or unresolved address provenance).
- If confidence is low, downgrade verdict one level toward caution (`pass` -> `warn`, `warn` -> `block`).

## Blocking Conditions

- Planned slippage exceeds user cap or exceeds 1.0% default.
- Address risk check fails (flagged, blacklisted, or malformed counterparty).
- Liquidity depth indicates severe price impact beyond 5%.
- Gas deviation from baseline exceeds 40%.
- Near-unlimited allowance (>= 2^255) without explicit user confirmation.
- Mandatory intent field is missing (cannot evaluate safely).

## Output Format

Always use this exact structure. You MUST include ALL five checklist items in every response, even when blocking early due to missing fields. For checks that cannot be evaluated (e.g., because a required input is missing), mark them as `fail` with details explaining why (e.g., "cannot evaluate -- required field missing").

```text
Mantle Preflight Risk Report
- operation:
- environment:
- evaluated_at_utc:

Checklist
- slippage_check: pass | warn | fail
  details:
- liquidity_depth_check: pass | warn | fail
  details:
- address_safety_check: pass | warn | fail
  details:
- allowance_scope_check: pass | warn | fail
  details:
- gas_and_deadline_check: pass | warn | fail
  details:

Final Verdict
- status: pass | warn | block
- blocking_reasons:
- user_action_required:
```

## References

- `references/risk-checklist.md`
- `references/risk-threshold-guidance.md`
