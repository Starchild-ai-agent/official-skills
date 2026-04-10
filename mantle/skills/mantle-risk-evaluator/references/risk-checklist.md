# Risk Checklist

Apply all checks before execution intent is approved.

## Input completeness

- `operation_type` present
- `chain/environment` present
- token and amount fields present
- target contract/router/pool address present

Fail if any mandatory field is missing.

## Slippage check

- Compare proposed slippage against user-defined cap.
- If no user cap exists, apply default from `risk-threshold-guidance.md`.
- Fail when cap exceeded.

## Liquidity depth check

- Estimate price impact from quote/simulation context.
- Warn on moderate impact, fail on severe impact (threshold-driven).
- If liquidity data unavailable, set warn with reduced confidence.

## Address safety check

- Verify all addresses against trusted registry/tooling.
- Flag unknown, suspicious, or blacklisted addresses.
- Fail on blacklisted/explicitly flagged addresses.

## Allowance scope check

- Detect approvals broader than required for intended amount.
- Warn on broad allowances.
- Fail if operation requires new unlimited approval without user confirmation.

## Gas and deadline sanity

- Check gas estimate reasonableness versus recent baseline.
- Check transaction deadline is not stale and not excessively long.
- Warn or fail according to threshold profile.

## Finalization rule

- Any `fail` in critical categories => final verdict `block`.
- No `fail` and at least one `warn` => final verdict `warn`.
- All checks pass => final verdict `pass`.
