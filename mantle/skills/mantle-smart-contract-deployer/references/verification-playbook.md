# Verification Playbook

Use this workflow to plan or validate verification of externally deployed contracts on Mantle explorers.

## Required inputs

- deployed contract address
- contract source path and contract name
- compiler version
- optimizer enabled/runs
- constructor arguments (raw and encoded)
- linked library addresses (if any)

## Steps

1. Confirm deployed bytecode exists at target address.
2. Prepare verification payload for explorer API/UI submission (or provide manual submission instructions when tooling is unavailable).
3. Poll verification status from explorer responses until success/failure/timeout.
4. Record verification link or identifier.

## Common failures and fixes

- Compiler mismatch:
  - Rebuild with exact compiler version used at deployment.
- Optimizer mismatch:
  - Match enable flag and run count exactly.
- Constructor args mismatch:
  - Re-encode with precise argument order and types.
- Metadata/library mismatch:
  - Provide fully qualified library mapping.

## Evidence requirements

- Keep full request payload snapshot (excluding secrets).
- Keep explorer response body and timestamp.
- Do not claim the agent submitted deployment/verification transactions; execution happens externally.
- Do not claim "verified" without explicit success response.
