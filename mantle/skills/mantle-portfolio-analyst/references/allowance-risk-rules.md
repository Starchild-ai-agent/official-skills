# Allowance Risk Rules

Use these rules to classify spender approval exposure.

## Inputs

- Token address
- Spender address
- Allowance raw value
- Token decimals (if known)
- `is_unlimited` flag from `mantle-cli account allowances` output (preferred when present)

## Risk levels

- `low`
  - Allowance is zero.
  - Or allowance is tightly bounded and clearly below wallet balance/expected use.
- `medium`
  - Allowance is non-zero and larger than immediate expected use, but still bounded.
- `high`
  - Allowance is very large relative to expected use.
  - Or allowance appears intentionally broad with unclear user intent.
- `critical`
  - `is_unlimited=true` from tool output.
  - Or allowance equals or is effectively near-max integer approval.
  - Typical near-max detection: value >= `2^255`.

## Reporting rules

- Always include rationale text with each risk label.
- Mark spender trust status as `unknown` unless verified from `mantle://registry/protocols` or user-confirmed protocol.
- Highlight all `high` and `critical` approvals at top of summary.
- If token decimals are missing, classify using raw value and downgrade confidence.

## Caveats

- Unlimited approval is not automatically malicious; it is an exposure signal.
- Risk scoring is heuristic and should be combined with protocol trust checks and intent context.
