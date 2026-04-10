# OpenZeppelin MCP Handoff

Use OpenZeppelin MCP whenever the user needs actual smart contract writing or implementation guidance for a Mantle project.

## Route to OpenZeppelin MCP for

- Solidity contract scaffolding or code generation
- OpenZeppelin inheritance and extension choices
- `Ownable`, `AccessControl`, token, proxy, upgrade, governor, or security module usage
- constructor, initializer, or storage-layout implementation details
- contract refactors tied to OpenZeppelin patterns

## Provide this handoff context

- Mantle environment (`mainnet` or `testnet`)
- contract purpose and user flows
- asset model and token standards involved
- admin and upgradeability requirements
- external Mantle dependencies and known addresses
- deployment constraints or verification requirements already known

## Expected return from OpenZeppelin MCP

- recommended contract modules and inheritance plan
- implementation notes or code guidance
- security-sensitive decisions to review
- inputs needed for testing and deployment

## Boundary

- OpenZeppelin MCP handles contract authoring guidance.
- `mantle-smart-contract-developer` handles Mantle-specific framing, readiness checks, and handoff into `$mantle-smart-contract-deployer`.
