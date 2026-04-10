---
name: mantle-openclaw-competition
description: Use when OpenClaw needs to execute DeFi operations for the asset accumulation competition on Mantle. Covers swap, LP, and Aave lending workflows with whitelisted assets and protocols.
---

# OpenClaw Competition — DeFi Operations Guide

## Overview

This skill provides everything OpenClaw needs to execute DeFi operations in the Mantle asset accumulation competition. Each participant starts with 100 MNT in a fresh wallet and competes to grow total portfolio value (USD) through whitelisted protocol interactions.

## Tooling — CLI Only (Mandatory)

**DO NOT enable or connect the `mantle-mcp` MCP server.** All on-chain operations MUST be performed via the `mantle-cli` command-line tool with `--json` output. This eliminates MCP tool-schema overhead and reduces per-session token cost.

### Setup

```bash
npm install github:mantle-xyz/mantle-agent-scaffold   # installs mantle-cli
npx mantle-cli --help                                  # verify the CLI is available
```

### Key rules

- **Always append `--json`** to every command so the output is machine-parseable JSON.
- **Never start or connect to the MCP server.** Do not configure `mantle-mcp` in any MCP client settings.
- **Never fabricate calldata** — always use `mantle-cli` build commands.
- **Never add a `from` field** to unsigned transactions — the signer determines `from`.

### Discover available commands

Before using the CLI for the first time, run:

```bash
mantle-cli catalog list --json          # list all 37 capabilities with category, auth, and CLI command template
mantle-cli catalog search "swap" --json # find swap-related capabilities
mantle-cli catalog show <tool-id> --json # full details for a specific capability
```

Each catalog entry includes:
- `category`: `query` (read-only) | `analyze` (computed insights) | `execute` (builds unsigned tx)
- `auth`: `none` | `optional` | `required` (whether a wallet address is needed)
- `cli_command`: the exact CLI command template with placeholders
- `workflow_before`: which tools to call before this one

## When to Use

- User asks to swap tokens on Mantle
- User asks to add/remove liquidity on a DEX
- User asks to supply/borrow on Aave V3
- User asks about available assets or trading pairs
- User asks how to maximize yield or portfolio value

## Whitelisted Assets

Only these assets count toward the competition score:

### Core Tokens

| Symbol | Address | Decimals |
|--------|---------|----------|
| MNT | Native gas token | 18 |
| WMNT | `0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8` | 18 |
| WETH | `0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111` | 18 |
| USDC | `0x09Bc4E0D864854c6aFB6eB9A9cdF58aC190D0dF9` | 6 |
| USDT0 | `0x779Ded0c9e1022225f8E0630b35a9b54bE713736` | 6 |
| MOE | `0x4515A45337F461A11Ff0FE8aBF3c606AE5dC00c9` | 18 |

### xStocks RWA Tokens (Fluxion V3 pools, all paired with USDC, fee_tier 3000)

| Symbol | Address | Pool (USDC pair) |
|--------|---------|-----------------|
| wTSLAx | `0x43680abf18cf54898be84c6ef78237cfbd441883` | `0x5e7935d70b5d14b6cf36fbde59944533fab96b3c` |
| wAAPLx | `0x5aa7649fdbda47de64a07ac81d64b682af9c0724` | `0x2cc6a607f3445d826b9e29f507b3a2e3b9dae106` |
| wCRCLx | `0xa90872aca656ebe47bdebf3b19ec9dd9c5adc7f8` | `0x43cf441f5949d52faa105060239543492193c87e` |
| wSPYx | `0xc88fcd8b874fdb3256e8b55b3decb8c24eab4c02` | `0x373f7a2b95f28f38500eb70652e12038cca3bab8` |
| wHOODx | `0x953707d7a1cb30cc5c636bda8eaebe410341eb14` | `0x4e23bb828e51cbc03c81d76c844228cc75f6a287` |
| wMSTRx | `0x266e5923f6118f8b340ca5a23ae7f71897361476` | `0x0e1f84a9e388071e20df101b36c14c817bf81953` |
| wNVDAx | `0x93e62845c1dd5822ebc807ab71a5fb750decd15a` | `0xa875ac23d106394d1baaae5bc42b951268bc04e2` |
| wGOOGLx | `0x1630f08370917e79df0b7572395a5e907508bbbc` | `0x66960ed892daf022c5f282c5316c38cb6f0c1333` |
| wMETAx | `0x4e41a262caa93c6575d336e0a4eb79f3c67caa06` | `0x782bd3895a6ac561d0df11b02dd6f9e023f3a497` |
| wQQQx | `0xdbd9232fee15351068fe02f0683146e16d9f2cea` | `0x505258001e834251634029742fc73b5cab4fd67d` |

## Whitelisted Protocols & Contracts

### DEX: Merchant Moe (Liquidity Book AMM)

| Contract | Address | Operations |
|----------|---------|-----------|
| MoeRouter | `0xeaEE7EE68874218c3558b40063c42B82D3E7232a` | swap |
| LB Router V2.2 | `0x013e138EF6008ae5FDFDE29700e3f2Bc61d21E3a` | swap, add/remove LP |

**Key pairs:**
- USDC/USDT0: bin_step=1 (stablecoin)
- WMNT/USDC: bin_step=20
- WMNT/USDT0: bin_step=20
- WMNT/USDe: bin_step=20
- USDe/USDT0: bin_step=1

### DEX: Agni Finance (Uniswap V3 fork)

| Contract | Address | Operations |
|----------|---------|-----------|
| SwapRouter | `0x319B69888b0d11cEC22caA5034e25FfFBDc88421` | swap |
| PositionManager | `0x218bf598D1453383e2F4AA7b14fFB9BfB102D637` | add/remove LP |

**Key pairs:**
- WETH/WMNT: fee_tier=500 (0.05%)
- USDC/WMNT: fee_tier=10000 (1%)
- USDT0/WMNT: fee_tier=500 (0.05%)
- mETH/WETH: fee_tier=500 (0.05%)

### DEX: Fluxion (Uniswap V3 fork, native to Mantle)

| Contract | Address | Operations |
|----------|---------|-----------|
| SwapRouter | `0x5628a59df0ecac3f3171f877a94beb26ba6dfaa0` | swap |
| PositionManager | `0x2b70c4e7ca8e920435a5db191e066e9e3afd8db3` | add/remove LP |

**All xStocks pools**: USDC paired, fee_tier=3000 (0.3%). See xStocks table above for pool addresses.

### Lending: Aave V3

| Contract | Address | Operations |
|----------|---------|-----------|
| Pool | `0x458F293454fE0d67EC0655f3672301301DD51422` | supply, borrow, repay, withdraw |
| ProtocolDataProvider | `0x487c5c669D9eee6057C44973207101276cf73b68` | read-only queries |

**Supported reserve assets:** WETH, WMNT, USDT0, USDC, USDe, sUSDe, FBTC, syrupUSDT, wrsETH, GHO

## DeFi Operations — Step-by-Step

### How to Swap Tokens

**Pre-condition:** You have the input token in your wallet.

```
1. mantle-cli swap pairs --json
   → Find the pair and its params (bin_step or fee_tier)

2. mantle-cli defi swap-quote --in X --out Y --amount 10 --provider best --json
   → Get the expected output and minimum_out

3. mantle-cli account allowances <wallet> --pairs X:<router> --json
   → Check if already approved

4. IF allowance < amount:
   mantle-cli swap approve --token X --spender <router> --amount <amount> --json
   → Sign and broadcast

5. mantle-cli swap build-swap --provider <dex> --in X --out Y --amount 10 --recipient <wallet> --amount-out-min <from_quote> --json
   → Sign and broadcast
```

**For MNT → Token swaps:** Wrap MNT first with `mantle-cli swap wrap-mnt --amount <n> --json`, then swap WMNT.

### How to Add Liquidity

**Agni / Fluxion (V3 concentrated liquidity):**
```
1. Approve both tokens for the PositionManager
   mantle-cli swap approve --token <tokenA> --spender <position_manager> --amount <n> --json
   mantle-cli swap approve --token <tokenB> --spender <position_manager> --amount <n> --json

2. mantle-cli lp add \
     --provider agni \
     --token-a WMNT --token-b USDC \
     --amount-a 5 --amount-b 4 \
     --recipient <wallet> \
     --fee-tier 10000 \
     --tick-lower <lower> --tick-upper <upper> \
     --json

3. Sign and broadcast → Receive NFT position
```

**Merchant Moe (Liquidity Book):**
```
1. Approve both tokens for LB Router (0x013e138EF6008ae5FDFDE29700e3f2Bc61d21E3a)
   mantle-cli swap approve --token <tokenA> --spender 0x013e138EF6008ae5FDFDE29700e3f2Bc61d21E3a --amount <n> --json
   mantle-cli swap approve --token <tokenB> --spender 0x013e138EF6008ae5FDFDE29700e3f2Bc61d21E3a --amount <n> --json

2. mantle-cli lp add \
     --provider merchant_moe \
     --token-a WMNT --token-b USDe \
     --amount-a 5 --amount-b 4 \
     --recipient <wallet> \
     --bin-step 20 \
     --active-id <from_pool> \
     --delta-ids '[-5,-4,-3,-2,-1,0,1,2,3,4,5]' \
     --distribution-x '[0,0,0,0,0,0,1e17,1e17,2e17,2e17,3e17]' \
     --distribution-y '[3e17,2e17,2e17,1e17,1e17,0,0,0,0,0,0]' \
     --json

3. Sign and broadcast → Receive LB tokens
```

### How to Use Aave V3

**Supply (earn interest):**
```
1. mantle-cli swap approve --token USDC --spender 0x458F293454fE0d67EC0655f3672301301DD51422 --amount 100 --json
   → Sign and broadcast

2. mantle-cli aave supply --asset USDC --amount 100 --on-behalf-of <wallet> --json
   → Sign and broadcast → Receive aUSDC (grows with interest)
```

**Borrow (leverage):**
```
1. Supply collateral first (see above)
2. mantle-cli aave borrow --asset USDC --amount 50 --on-behalf-of <wallet> --json
   → Sign and broadcast → Receive USDC, incur variableDebtUSDC
```

**Repay:**
```
1. mantle-cli swap approve --token USDC --spender 0x458F293454fE0d67EC0655f3672301301DD51422 --amount 50 --json
2. mantle-cli aave repay --asset USDC --amount 50 --on-behalf-of <wallet> --json
   OR --amount max to repay full debt
```

**Withdraw:**
```
1. mantle-cli aave withdraw --asset USDC --amount 50 --to <wallet> --json
   OR --amount max for full balance
```

### How to Analyze Pools Before LP

Before adding liquidity, analyze the pool to choose the best range and estimate returns:

```
1. mantle-cli lp find-pools --token-a WMNT --token-b USDC --json
   → Discover all available pools across Agni, Fluxion, Merchant Moe

2. mantle-cli defi analyze-pool --token-a WMNT --token-b USDC --fee-tier 3000 --provider agni --investment 1000 --json
   → Get fee APR, multi-range comparison, risk assessment, investment projections

3. mantle-cli lp suggest-ticks --token-a WMNT --token-b USDC --fee-tier 3000 --provider agni --json
   → Get tick range suggestions (wide/moderate/tight strategies)
```

## Safety Rules

1. **CLI only — never use MCP** — All operations via `mantle-cli ... --json`. Do not enable or connect to the MCP server.
2. **Never fabricate calldata** — Always use `mantle-cli` build commands. Never construct tx data manually.
3. **Always check allowance before approve** — Don't approve if already sufficient.
4. **Always get a quote before swap** — Use `mantle-cli defi swap-quote` to know expected output.
5. **Wait for tx confirmation** — Do not build the next tx until the previous one is confirmed on-chain.
6. **Show `human_summary`** — Present every build command's summary to the user before signing.
7. **Value field is hex** — The `unsigned_tx.value` is hex-encoded (e.g., "0x0"). Pass it directly to the signer.
8. **MNT is gas** — All gas costs are in MNT, not ETH.

## Competition Scoring

```
Net Value (USD) = Sum(token holdings * price) + Sum(aToken balances * price) - Sum(debtToken balances * price)
```

- aToken balances grow over time (interest earned)
- debtToken balances grow over time (interest owed)
- LP positions valued by underlying token amounts
- Only interactions with whitelisted contracts count
