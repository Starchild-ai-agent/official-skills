---
name: scaffold
description: End to end guide to take an idea build an app to production, if you are starting an app from scratch this skill must be fetched first.
---

## Checklist

[ ] - Plan architecture and folder structure
[ ] - Decide which components of the app will be onchain
[ ] - Scaffold the project
[ ] - Initialize git repo (`git init && git add -A && git commit -m "initial commit"`)
[ ] - Don't build exisiting contracts from scratch, use Openzeppelin contracts where ever possible
[ ] - Build smart contracts
[ ] - Deploy smart contracts — fetch `wallet/` skill, then deploy using the agent wallet and Safe multisig. **This must happen before building the frontend** because the frontend needs the deployed contract addresses.
[ ] - Verify smart contracts post deployment — use the verification API to verify on all explorers with one call.
[ ] - (If the app needs historical/queryable onchain data) Initialize an indexer — fetch `indexer/` skill. The indexer is initialized in an `indexer/` folder after the contract is deployed AND verified.
[ ] - Build frontend using the deployed contract addresses. Use Wagmi, Next.js and Shadcn if user has no preferences
[ ] - **Apply known gotchas** (see section below) — bump `tsconfig.json` target to ES2020 right after `create-next-app`, etc.
[ ] - Commit all changes to git (`git add -A && git commit`)

## Known gotchas — apply up front

These are well-known paper-cuts you will hit mid-build if you skip them. Patch them when you scaffold, not after the typechecker screams.

### Next.js default tsconfig target is too low for viem/wagmi

`create-next-app` generates `"target": "ES2017"`. viem, wagmi, and most onchain code use BigInt literals (`0n`, `1n`) everywhere — amounts, gas, event args, block numbers — so a fresh Next.js project fails typechecking with `TS2737: BigInt literals are not available when targeting lower than ES2020` the moment you `useReadContract` or `getLogs`.

Bump the target immediately after running `npx create-next-app`:

```bash
cd web
jq '.compilerOptions.target = "ES2020"' tsconfig.json > tsconfig.tmp && mv tsconfig.tmp tsconfig.json
```

(If `jq` isn't available, open `tsconfig.json` and change `"target": "ES2017"` to `"target": "ES2020"`.)

## Scaffolding

Before jumping into writing code, use plan mode to plan the architecture of the app.

| Folder | Component |
| --- | --- |
| web/ | Web app frontend, backend routes also in case of [Next.js](https://nextjs.org/docs/app/getting-started/installation) or similar app (if the user does not have a preference go with [Next.js](https://nextjs.org/docs/app/getting-started/installation) and [shadcn](https://ui.shadcn.com/docs/installation) components) |
| contracts/ | Smart contracts (could be a [Foundry project](https://www.getfoundry.sh/introduction/getting-started), if the user does not have a preference use [Foundry](https://www.getfoundry.sh/introduction/getting-started)) |
| indexer/ | (Optional) HyperIndex indexer for querying historical onchain events. Created via `indexer/` skill after the contract is deployed and verified. |

## Decide what to put onchain

Put it onchain if it involves:
- **Trustless ownership** — who owns this token/NFT/position?
- **Trustless exchange** — swapping, trading, lending, borrowing
- **Composability** — other contracts need to call it
- **Censorship resistance** — must work even if your team disappears
- **Permanent commitments** — votes, attestations, proofs

Keep it offchain if it involves:
- User profiles, preferences, settings
- Search, filtering, sorting
- Images, videos, metadata (store on IPFS, reference onchain)
- Business logic that changes frequently
- Anything that doesn't involve value transfer or trust

**Judgment calls:**
- Reputation scores → offchain compute, onchain commitments (hashes or attestations)
- Price data → offchain oracles writing onchain (Chainlink)
- Game state → depends on stakes. Poker with real money? Onchain. Leaderboard? Offchain.

## Don't try to build smart contracts from scratch

It is very likely that depending on the usecase of the smart contract, there is an Openzeppelin smart contract available to build on top of instead of building from scratch.

For example: Don't rebuild ERC20, ERC721 and other well known token types from scratch build on top of Openzeppelin contracts since they are heavily audited.

All Openzeppelin smart contracts can be found here: https://github.com/OpenZeppelin/openzeppelin-contracts/tree/master/contracts and you can use the below command to install it (Foundry should be already installed).

```bash
# --no-git avoids adding the dep as a git submodule — required when the contracts/
# folder is not (yet) its own git repo, which is the default in monskills scaffolds
# because the outer project directory owns the git history.
forge install --no-git OpenZeppelin/openzeppelin-contracts
```

## Use Wagmi in Frontend

Use the [wagmi](https://wagmi.sh/react/getting-started) v3 library for making smart contracts from Frontend.

For wallet connection and authentication use Para — embedded MPC wallets (email / passkey / social login) plus external-wallet connect. The `wallet-integration` skill walks through the `@getpara/cli` workflow (`para init` + `ParaProvider` + `para doctor` against the already-scaffolded frontend, plus the Monad-specific wagmi wiring). Don't run `para create` — scaffolding is owned by this skill.

## Use useSendTransactionSync whereever it can be used

Monad supports eth_sendRawTransactionSync RPC method and useSendTransactionSync uses that RPC method to send transaction and get the receipt in the same function call, that way the UI can be much more fast.

## Verification (All Explorers)

**ALWAYS use the verification API.** It verifies on all 3 explorers (MonadVision, Socialscan, Monadscan) with one call. Do NOT use `forge verify-contract` as your first choice.

### Step 1: Get Verification Data

After deploying, get two pieces of data:

```bash
# 1. Standard JSON input (all source files)
forge verify-contract <ADDR> <CONTRACT> \
  --chain 10143 \
  --show-standard-json-input > /tmp/standard-input.json

# 2. Foundry metadata (from compilation output)
cat out/<Contract>.sol/<Contract>.json | jq '.metadata' > /tmp/metadata.json
```

### Step 2: Call Verification API

```bash
STANDARD_INPUT=$(cat /tmp/standard-input.json)
FOUNDRY_METADATA=$(cat /tmp/metadata.json)

cat > /tmp/verify.json << EOF
{
  "chainId": 10143,
  "contractAddress": "0xYOUR_CONTRACT_ADDRESS",
  "contractName": "src/MyContract.sol:MyContract",
  "compilerVersion": "v0.8.28+commit.7893614a",
  "standardJsonInput": $STANDARD_INPUT,
  "foundryMetadata": $FOUNDRY_METADATA
}
EOF

curl -X POST https://agents.devnads.com/v1/verify \
  -H "Content-Type: application/json" \
  -d @/tmp/verify.json
```

### With Constructor Arguments

Add `constructorArgs` (ABI-encoded, WITHOUT 0x prefix).

Example:

```bash
# Get constructor args
ARGS=$(cast abi-encode "constructor(string,string,uint256)" "MyToken" "MTK" 1000000000000000000000000)
# Remove 0x prefix
ARGS_NO_PREFIX=${ARGS#0x}

# Add to request
"constructorArgs": "$ARGS_NO_PREFIX"
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `chainId` | Yes | 10143 (testnet) or 143 (mainnet) |
| `contractAddress` | Yes | Deployed contract address |
| `contractName` | Yes | Format: `path/File.sol:ContractName` |
| `compilerVersion` | Yes | e.g., `v0.8.28+commit.7893614a` |
| `standardJsonInput` | Yes | From `forge verify-contract --show-standard-json-input` |
| `foundryMetadata` | Yes | From `out/<Contract>.sol/<Contract>.json > .metadata` |
| `constructorArgs` | No | ABI-encoded args WITHOUT 0x prefix |

### Manual Verification (Fallback Only)

**Only use this if the API fails.**

**Testnet:**
```bash
forge verify-contract <ADDR> <CONTRACT> --chain 10143 \
  --verifier sourcify \
  --verifier-url "https://sourcify-api-monad.blockvision.org/"
```

**Mainnet:**
```bash
forge verify-contract <ADDR> <CONTRACT> --chain 143 \
  --verifier sourcify \
  --verifier-url "https://sourcify-api-monad.blockvision.org/"
```

## What to Fetch by Task

| I'm doing... | Fetch these skills |
|--------------|-------------------|
| Choosing a blockchain to build on | `why-monad/` |
| Writing smart contracts | `addresses/` |
| Agent wallet management, deploy smart contracts or perform onchain actions | `wallet/` |
| Adding wallet + auth to a frontend (embedded MPC wallets, social/email/passkey login, plus external-wallet connect — Para) | `wallet-integration/` |
| Adding a historical/activity feed or any feature that requires indexing onchain smart contract events | `indexer/` |
| Building an app from scratch (idea to production) | `scaffold/` (this) |