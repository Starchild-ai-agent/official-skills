# Simulation Backends

Choose backend by availability, fidelity, and reproducibility requirements.
These backends are external and must be run outside the CLI toolchain.

## Backend options

### Local fork (Anvil or equivalent)

- Best for deterministic local replay and rapid iteration.
- Requires archive-capable RPC and correct fork block configuration.
- Good for deep debugging with custom call sequences.

### Managed simulation API (Tenderly or equivalent)

- Best for quick hosted simulation with rich traces.
- Good for team workflows and sharable simulation artifacts.
- Depends on provider uptime and account/project configuration.

## Selection heuristic

1. Use local fork when you need deterministic reproducibility or custom pre-state setup.
2. Use managed simulator when you need speed, traces, and collaboration.
3. If one backend fails, request one retry on an alternate backend before declaring inconclusive.

## Minimum captured fields

- backend name
- network/chain ID
- simulation timestamp (UTC)
- transaction payload
- success/revert status
- gas estimate
- decoded events/logs (if available)
- state diff summary

## Inconclusive conditions

- backend error without trace
- unresolved calldata decoding
- missing token metadata needed for user-facing summary

Return `status: inconclusive` and `do_not_execute_reason` when any inconclusive condition exists.
