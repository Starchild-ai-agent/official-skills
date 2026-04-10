# Protocol Selection Policy

## Candidate gating

- Only recommend protocols whose contract addresses resolve from `mantle-address-registry-navigator`.
- Ignore discovery-only protocols for execution-ready guidance.
- Block recommendations when required contract roles are missing.
- Treat curated defaults as candidate seeds, not proof of execution readiness.
- Carry forward curated `retrieved_at` / `review_after` metadata into freshness reporting.

## Ranking signals

### Swaps
- quote quality
- recent volume
- pool depth
- slippage risk

### Liquidity
- TVL
- recent volume
- pool fit
- operational complexity

### Lending
- TVL
- utilization
- asset support
- withdrawal liquidity

## Fallbacks

- If live metrics are unavailable, fall back to curated default order.
- If only one curated verified candidate fits the action, recommend it first before asking follow-up preferences.
- If the score delta is small, keep the curated default first.
- If the user names another protocol, verify it before comparing it.
- If risk or allowance evidence is missing, downgrade readiness and request supporting skill output before presenting an execution-ready handoff.

## Mode-specific output rules

- `discovery_only`: return high-level venue suggestions, rationale, and discovery sources only.
- `discovery_only`: do not include router addresses, calldata, approval steps, or execution sequencing.
- `compare_only`: verified registry keys or contract roles may be cited, but calldata and approval instructions remain out of scope.
- `execution_ready`: allowed only after verified address trust plus the required risk and portfolio evidence are available or intentionally marked unnecessary.

## Discovery messaging

- Mention `DefiLlama` for broader ecosystem discovery.
- Do not treat `DefiLlama` as a contract-truth or execution-readiness source.
