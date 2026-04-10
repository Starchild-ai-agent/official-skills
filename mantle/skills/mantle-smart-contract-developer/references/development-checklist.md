# Development Checklist

Run this checklist before handing a Mantle contract project to deployment planning.

## Product and environment checks

- Confirm the contract's purpose, users, and privileged roles.
- Confirm target environment (`mainnet` or `testnet`).
- Confirm whether the contract must be upgradeable or immutable.
- Confirm whether the contract will hold assets, mint tokens, bridge funds, or control admin actions.

## Mantle-specific integration checks

- Confirm every external contract address is correct for the requested Mantle environment.
- Confirm native gas assumptions use MNT.
- Confirm any bridge, oracle, DEX, vault, or system dependency is explicitly named and environment-correct.
- Confirm frontend or backend integrations know which events, functions, and initialization values they depend on.

## Contract design checks

- Confirm the chosen OpenZeppelin base contracts and access-control model.
- Confirm constructor or initializer inputs are complete and intentional.
- Confirm pause, emergency, or recovery flows are specified when relevant.
- Confirm upgrade authorization and storage-layout constraints are understood when proxies are used.

## Quality checks

- Confirm unit, integration, and failure-path test expectations.
- Confirm the highest-risk behaviors that need focused review.
- Confirm no unresolved TODO, placeholder address, or ambiguous permission remains.

## Handoff gate

- If any required item is unclear, stop and resolve it before deployment planning.
- If all items are clear, produce a development brief and hand off to `$mantle-smart-contract-deployer`.
