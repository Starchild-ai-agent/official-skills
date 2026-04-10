# Risk Threshold Guidance

Use user-specified parameters first. Use defaults only when user constraints are absent.

## Default thresholds (recommended baseline)

- Slippage cap:
  - Warn: `> 0.5%`
  - Fail: `> 1.0%`
- Estimated price impact:
  - Warn: `> 2%`
  - Fail: `> 5%`
- Deadline horizon:
  - Warn: `> 20 minutes`
  - Fail: `> 60 minutes`
- Gas deviation from rolling baseline:
  - Warn: `> 20%`
  - Fail: `> 40%`

## Address trust

- `pass`: trusted and verified source
- `warn`: unknown but not explicitly flagged
- `fail`: flagged, blacklisted, or malformed address

## Allowance policy

- `pass`: existing allowance fits intended spend scope
- `warn`: allowance materially larger than intended spend
- `fail`: new or existing near-unlimited approval without explicit user approval

Near-unlimited heuristic:
- raw allowance `>= 2^255`

## Confidence policy

- `high`: all required signals present and consistent
- `medium`: one non-critical signal missing
- `low`: key signals missing (for example no liquidity data or unresolved address provenance)

If confidence is low, downgrade verdict one level toward caution (`pass` -> `warn`, `warn` -> `block`).
