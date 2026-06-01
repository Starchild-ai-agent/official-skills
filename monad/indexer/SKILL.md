---
name: indexer
description: This skill has instructions to setup a Envio HyperIndex indexer to capture onchain smart contract events. Use when user wants a historical feed or activity feed or some similar tracking feed or feature in their app or wants to capture onchain smart contracts events as a trigger to perform some other actions in their app. Also use this skill when the user wants to debug, restart, promote or delete and existing Envio indexer deployed on Envio Cloud.
---

# Indexer

This skill covers initializing a HyperIndex indexer and deploying/managing it on Envio Cloud using the `envio-cloud` CLI.

## When to fetch this skill

- The user wants to initialize a new indexer for a Monad contract.
- The user wants to deploy a new indexer to Envio Cloud.
- The user wants to inspect, promote, restart, or delete an existing deployment.
- The user wants to manage indexer environment variables or IP allowlists.
- The user wants to debug an indexer that is failing to deploy or sync.
- The user wants the GraphQL API URL for an indexer (e.g. to point a frontend or curl at it).

## Initialize a new indexer

Run the init command inside an `indexer/` folder at the project root. Create the folder first if it doesn't exist.

**Hard prereq: the contract must be both deployed AND verified on a Monad explorer before you run this.** `contract-import` pulls the ABI from the explorer — an unverified contract will fail the import. If the user hasn't verified yet, stop and do that first (see `scaffold/` skill for the verification API).

### Monad mainnet

```bash
mkdir -p indexer && cd indexer
pnpx envio@3.0.0-alpha.21 init contract-import explorer \
  -b monad \
  -c <CONTRACT_ADDRESS> \
  -n <CONTRACT_NAME> \
  -l typescript \
  -d ./ -o ./ \
  --all-events --single-contract --api-token ""
```

### Monad testnet

```bash
mkdir -p indexer && cd indexer
pnpx envio@3.0.0-alpha.21 init contract-import explorer \
  -b monad-testnet \
  -c <CONTRACT_ADDRESS> \
  -n <CONTRACT_NAME> \
  -l typescript \
  -d ./ -o ./ \
  --all-events --single-contract --api-token ""
```

**Notes:**
- `<CONTRACT_ADDRESS>` — the deployed, verified contract address.
- `<CONTRACT_NAME>` — the contract name (matches the Solidity contract, e.g. `MyToken`).
- `--all-events` imports every event in the ABI. Narrow this later by editing `config.yaml` if the user wants only specific events.
- `--single-contract` scaffolds for one contract. Re-run the command for additional contracts, or edit the config by hand.
- `--api-token ""` is intentional — leave it empty.
- `-l typescript` is a flag, not a positional — the envio CLI rejects `typescript` as a bare positional arg.
- The version is pinned to `envio@3.0.0-alpha.21` (use exactly this).

After init, the `indexer/` folder will contain `config.yaml`, `schema.graphql`, and handler stubs. The user edits the handlers to decide what gets stored in the database. Once the code is ready and pushed to GitHub, deploy to Envio Cloud (see below).

### Opt into transaction fields before writing handlers

By default, `event.transaction.*` is typed `never` in generated handlers — accessing `event.transaction.hash` (or any other tx field) is a TypeScript error. Most frontends want the tx hash (for explorer links, dedup, etc.), so opt in explicitly before writing handler code.

Add `field_selection` to `config.yaml`:

```yaml
field_selection:
  transaction_fields:
    - hash
```

Place it at the top level of `config.yaml` (sibling of `networks:`, `contracts:`, etc.), not nested under a network or contract. After editing, re-run `pnpm codegen` (or `pnpx envio@3.0.0-alpha.21 codegen`) so the types regenerate — otherwise `event.transaction.hash` will still be typed `never`.

Add other fields the handlers need (`from`, `to`, `value`, `gasUsed`, `input`, etc.) to the same list. Envio only pulls and types the fields listed here, so keep it minimal. The full set of available fields is in the [Envio field selection docs](https://docs.envio.dev/docs/HyperIndex/configuration-file#field-selection).

## Prerequisites

Before any indexer command will work, the user must have all four of these in place:

1. `envio-cloud` installed globally: `npm install -g envio-cloud`
2. `envio-cloud` logged in: `envio-cloud login` (browser flow, 30-day session)
3. GitHub CLI (`gh`) installed: `brew install gh` on macOS, or see https://cli.github.com/
4. GitHub CLI logged in: `gh auth login`

`gh` is required because Envio Cloud deploys from GitHub — the indexer repo has to be pushed there, and `gh` is how that's done.

### What NOT to do

- **Do not install either CLI for the user.** If one is missing, tell them the exact command and wait.
- **Do not run `envio-cloud login` or `gh auth login` for the user.** Both open a browser and require the user to complete the flow themselves.

If you attempt an `envio-cloud` command without these prereqs, the monskills hook will deny the tool call with a message pointing to the exact missing piece. That's expected — surface the message to the user and wait for them to resolve it.

## Where to look next

This skill is split across reference files. Fetch them on demand:

- [Workflow recipes](./references/envio-cloud-workflows.md) — opinionated sequences for common tasks (first deploy, debug a failing deploy, rotate env vars, allowlist an IP).
- [CLI reference](./references/envio-cloud-cli.md) — every `envio-cloud` command, grouped by area (auth, context, indexer lifecycle, deployment, env, security).

Start with the workflow recipe that matches the user's goal. Drop into the CLI reference only when you need a flag or subcommand not covered there.

## Exit-code contract

Every `envio-cloud` command follows the same exit code convention — check this, not just stdout, when deciding whether a step succeeded:

| Exit code | Meaning | How to react |
|---|---|---|
| `0` | Success | Continue |
| `1` | User error (bad args, unknown indexer, not logged in) | Read stderr, fix the input, retry |
| `2` | API/server error | Not the user's fault. Retry once; if it persists, tell the user and stop. |

## Official docs

https://docs.envio.dev/docs/HyperIndex/envio-cloud-cli
