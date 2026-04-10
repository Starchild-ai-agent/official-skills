# Mantle Network Basics

Use this file for factual grounding when answering Mantle onboarding, difference, and developer-handoff questions. It supports a reference/onboarding skill rather than an execution workflow.

## Source and freshness

- Primary source: https://docs.mantle.xyz/network/for-developers/quick-access
- Additional sources:
  - https://docs.mantle.xyz/network/system-information/architecture
  - https://docs.mantle.xyz/network/for-developers/resources-and-tooling/node-endpoints-and-providers
- Snapshot verified on: **March 8, 2026**
- If a user asks for the "latest" values or architecture status, re-check the official docs before answering.

## How to use this reference

- Treat `Core model`, `Mantle-Specific Differences`, `Developer Hints`, and `RPC reliability guidance` as the stable-concepts layer.
- Treat `Network details`, `Onboarding tools`, contract links, and architecture notes as dated snapshots verified on **March 8, 2026**.
- If a question asks for "latest", "current", or rollout-status details, use this file to frame the answer and then live-verify before answering conclusively.

## Core model

- Mantle is an Ethereum-aligned Layer 2 execution network.
- Users execute transactions on L2.
- Settlement/security assurances are anchored to Ethereum L1.
- Mantle is EVM-compatible and uses standard Ethereum tooling.
- Gas on Mantle is paid in `MNT`.

## Mantle-Specific Differences

- `MNT` is the gas token, so developers should not assume `ETH`-funded wallets can transact on Mantle.
- Mantle is Ethereum-aligned, but fast L2 transaction inclusion is not the same thing as strongest L1-backed settlement/finality.
- Mantle-specific onboarding constants matter in practice:
  - mainnet `chainId`: `5000`
  - Sepolia testnet `chainId`: `5003`
  - explorer domains and bridge links are Mantle-specific
- Per the Mantle architecture page snapshot verified on **March 8, 2026**, Mantle v2 Skadi is described as using an execution layer, a ZK validity proving module, and Ethereum data availability via blobs.
- Architecture rollout details can evolve, so treat fee behavior, throughput, and "latest architecture" questions as live-verify items.

## Key Tokens on Mantle

**CRITICAL: WETH (bridged ETH) EXISTS on Mantle.** Do not confuse "MNT is the gas token" with "ETH doesn't exist on Mantle." ETH is bridged from L1 and is one of the most actively traded assets.

| Token | Address | Notes |
|-------|---------|-------|
| MNT | native (no contract) | Gas token, native currency |
| WMNT | `0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8` | Wrapped MNT (ERC-20 wrapper for native MNT) |
| WETH | `0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111` | Bridged ETH from L1 — **exists and has deep liquidity** |
| mETH | `0xcDA86A272531e8640cD7F1a92c01839911B90bb0` | Mantle Staked ETH (liquid staking derivative) |
| cmETH | `0xE6829d9a7eE3040e1276Fa75293Bde931859e8fA` | Restaked mETH |
| USDC | `0x09Bc4E0D864854c6aFB6eB9A9cdF58aC190D0dF9` | USD Coin (bridged) |
| USDT0 | `0x779Ded0c9e1022225f8E0630b35a9b54bE713736` | Tether (USDT0 variant) |
| USDe | `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` | Ethena USDe |

**Common mistake to avoid:** Claiming WETH doesn't exist on Mantle. It does — it's bridged ETH at `0xdEAD...1111`, with ~125K ETH total supply and pools on every major DEX (Agni, Fluxion, Merchant Moe).

## Network details (dated Quick Access snapshot)

### Mainnet

- RPC URL: `https://rpc.mantle.xyz`
- WebSocket URL: `wss://rpc.mantle.xyz`
- Chain ID: `5000`
- Token symbol: `MNT`
- Explorer: `https://mantlescan.xyz/`

### Testnet (Sepolia)

- RPC URL: `https://rpc.sepolia.mantle.xyz`
- WebSocket URL: `N/A` (per Quick Access)
- Chain ID: `5003`
- Token symbol: `MNT`
- Explorer: `https://sepolia.mantlescan.xyz/`

## Onboarding tools (dated Quick Access snapshot)

### Mainnet

- Bridge: `https://app.mantle.xyz/bridge`
- Recommended Solidity compiler: `v0.8.23 or below`
- Wrapped MNT: `0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8`

### Testnet (Sepolia)

- Faucet: `https://faucet.sepolia.mantle.xyz/`
- Third-party faucets:
  - `https://faucet.quicknode.com/mantle/sepolia`
  - `https://thirdweb.com/mantle-sepolia-testnet/faucet`
- Bridge: `https://app.mantle.xyz/bridge?network=sepolia`
- Recommended Solidity compiler: `v0.8.23 or below`
- Wrapped MNT: `0x19f5557E23e9914A18239990f6C70D68FDF0deD5`
- Note: Mantle docs indicate Sepolia MNT can be requested directly from faucet (subject to limits).

## Developer Hints

- Fund developer and test wallets with `MNT`, not `ETH`, before attempting transactions on Mantle.
- Use the official chain settings above instead of generic "custom EVM" assumptions.
- Mantle docs currently recommend Solidity `v0.8.23 or below`.
- Official public RPC endpoints are suitable for onboarding and light usage, but production or high-frequency workloads should use dedicated providers.
- For exact contract addresses, token mappings, and bridge-facing metadata, prefer the official address pages and token list links below over memory.
- When debugging UX issues, explain both:
  - `inclusion`: the transaction is visible in an L2 block
  - `L1-backed settlement finality`: the strongest settlement assurance once the L1-side conditions are satisfied

## Contract and token source-of-truth

- L1 system contracts: `https://docs.mantle.xyz/network/system-information/on-chain-system/key-l1-contract-address`
- L2 system contracts: `https://docs.mantle.xyz/network/system-information/off-chain-system/key-l2-contract-address`
- Token list source-of-truth: `https://token-list.mantle.xyz`
- Bridge reference: `https://bridge.mantle.xyz`
- Token-list PR repo (for adding tokens): `https://github.com/mantlenetworkio/mantle-token-lists`

## RPC reliability guidance

- Mantle docs state official RPC endpoints are rate-limited for stability.
- For high-frequency or production workloads, prefer dedicated provider endpoints.
- Provider directory: `https://docs.mantle.xyz/network/for-developers/resources-and-tooling/node-endpoints-and-providers`

## Response rules for this skill

- Use absolute dates when quoting values from this file.
- Treat throughput, fee levels, ecosystem counts, and latency/finality windows as volatile.
- Distinguish:
  - `inclusion`: transaction appears in L2 block.
  - `L1-backed settlement finality`: strongest settlement assurance once L1 conditions are satisfied.
- For exact contract address lookups in execution contexts, cross-check with:
  - Mantle contract address pages above, or
  - `$mantle-address-registry-navigator` (if available in the runtime).

## Difference checklist

When asked "what makes Mantle different", cover:

1. gas token and wallet funding expectations
2. inclusion versus L1-backed settlement/finality
3. current architecture snapshot versus live-verify items
4. onboarding constants such as chain IDs, bridge, explorer, and faucet
5. operational guidance such as RPC rate limits and provider selection
