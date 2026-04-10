---
name: mantle-defi-operator
description: Use when a Mantle DeFi task needs discovery, venue comparison, or execution-ready planning with verified contracts, preflight evidence, and an external handoff.
---

# Mantle Defi Operator

## Overview

Coordinate deterministic pre-execution planning for Mantle DeFi intents. This skill should orchestrate verified address lookup, preflight evidence, and execution handoff steps instead of duplicating specialized address, risk, or portfolio analysis.

## CLI-First Transaction Building

**ALWAYS use `mantle-cli` commands to build unsigned transactions.** The CLI produces correct calldata with verified addresses and ABI encoding. Do NOT:
- Manually construct calldata or hex-encode function calls
- Extract contract addresses from text responses and build transactions yourself
- Add a `from` field to unsigned transactions — this breaks Privy and other signers

### Tool Discovery via Capability Catalog

Before building any transaction, consult the **Capability Catalog** via CLI for the authoritative list of available tools, their read/write nature, wallet requirements, and call ordering:

```bash
mantle-cli catalog list --json                    # all capabilities
mantle-cli catalog list --category execute --json  # only tx-building commands
mantle-cli catalog search "swap" --json            # keyword search
mantle-cli catalog show mantle_buildSwap --json    # full details + CLI command template
```

Each entry includes:
- `category: query` — read-only, no state change, no wallet needed for most
- `category: analyze` — computed insights (APR, risk, recommendations), read-only
- `category: execute` — builds unsigned transactions, requires wallet address
- `workflow_before` — tells you which tools to call before a given tool
- `cli_command` — the exact CLI command template with placeholders

### Available CLI commands for DeFi operations:

```bash
# Swap operations
mantle-cli swap build-swap --provider <dex> --in <token> --out <token> --amount <n> --recipient <addr> --json
mantle-cli swap approve --token <token> --spender <router> --amount <n> --json
mantle-cli swap wrap-mnt --amount <n> --json
mantle-cli swap unwrap-mnt --amount <n> --json
mantle-cli swap pairs --json

# Aave V3 lending
mantle-cli aave supply --asset <token> --amount <n> --on-behalf-of <addr> --json
mantle-cli aave borrow --asset <token> --amount <n> --on-behalf-of <addr> --json
mantle-cli aave repay --asset <token> --amount <n|max> --on-behalf-of <addr> --json
mantle-cli aave withdraw --asset <token> --amount <n|max> --to <addr> --json
mantle-cli aave markets --json

# Liquidity provision
mantle-cli lp find-pools --token-a <t> --token-b <t> --json           # ALWAYS START HERE — discover ALL pools
mantle-cli lp pool-state <pool-or-tokens> --json
mantle-cli lp suggest-ticks <pool-or-tokens> --json
mantle-cli lp analyze <pool-or-tokens> [--investment-usd <n>] --json  # Deep pool analysis: APR, risk, range comparison
mantle-cli lp positions --owner <addr> --json
mantle-cli lp add --provider <dex> --token-a <t> --token-b <t> (--amount-a <n> --amount-b <n> | --amount-usd <n>) --recipient <addr> --json
mantle-cli lp remove --provider <dex> --recipient <addr> --token-id <id> (--liquidity <n> | --percentage <1-100>) --json
mantle-cli lp collect-fees --provider <p> --token-id <id> --recipient <addr> --json

# Read operations (no signing needed)
mantle-cli defi swap-quote --in <token> --out <token> --amount <n> --provider best --json
mantle-cli defi lending-markets --json
mantle-cli account balance <addr> --tokens USDC,USDT0 --json
```

All `--json` outputs contain `unsigned_tx` with `to`, `data`, `value`, `chainId` — pass this directly to the signer **without adding `from`**.

## When Not to Use

- Use `mantle-address-registry-navigator` when the task is only address lookup, whitelist validation, or anti-phishing review.
- Use `$mantle-risk-evaluator` when the task is only to return a `pass` / `warn` / `block` preflight verdict.
- Use `$mantle-portfolio-analyst` when the task is only balance coverage, allowance exposure, or spender-risk review.
- Stay in `discovery_only` mode when the user is exploring venues and has not asked for execution-ready planning.

## Quick Checklist

- `discovery_only`
  - Return venue suggestions, rationale, and discovery sources only.
  - Do not return router addresses, hex contract addresses (0x...), approval steps, calldata, or sequencing anywhere in the response.
  - Set `handoff_available` to `no`.
- `compare_only`
  - Compare verified venues and call out missing execution inputs.
  - Allow verified registry keys or contract roles (by name, not hex address), but stop short of approval instructions or calldata.
  - Do not include hex contract addresses (0x...) anywhere in the response -- not in rationale, not in fields. Use protocol and role names only.
  - Leave `risk_report_ref` / `portfolio_report_ref` empty or explicitly missing when evidence is not available.
  - Set `handoff_available` to `no`.
- `execution_ready`
  - Require `address_resolution_ref`.
  - Require `risk_report_ref` unless explicitly unnecessary for the operation.
  - Require `portfolio_report_ref` when allowance scope or balance coverage matters, or explain why it is unnecessary.
  - Only then expose approval planning, sequencing, calldata, and `handoff_available: yes`.

## Workflow

1. Normalize intent:
   - `swap`, `add_liquidity`, `remove_liquidity`, or compound flow
   - token addresses, amounts, recipient, deadline, slippage
2. Run prep checks from `references/defi-execution-guardrails.md`.
3. Resolve candidate protocol contracts from `mantle-address-registry-navigator` using the required registry key or protocol role for the requested action.
4. Classify the planning mode:
   - `execution_ready`: verified addresses plus enough quote/risk evidence to produce a handoff
   - `compare_only`: venue comparison is possible, but execution gating is incomplete; also use this mode when the user names an unverified protocol -- list it under `discovery_only` in Protocol Selection, set `readiness: blocked`, and recommend verified curated alternatives
   - `discovery_only`: high-level ecosystem exploration without execution readiness (no specific venue comparison requested)
5. Build the candidate set from `references/curated-defaults.yaml`; carry forward each default's freshness metadata and rationale, and if the user names another protocol, keep it `compare_only` until its contracts are verified.
6. Rank only eligible candidates with live signals from `references/protocol-selection-policy.md`:
   - swaps: quote quality, recent volume, pool depth, slippage risk
   - liquidity: TVL, recent volume, pool fit, operational complexity
   - lending: TVL, utilization, asset support, withdrawal liquidity
   - if live metrics are stale or unavailable, fall back to curated defaults and say so explicitly
   - if only one curated, verified candidate fits the requested action, recommend it first before asking optimization follow-ups
7. Pull supporting evidence before execution planning:
   - address trust from `mantle-address-registry-navigator`
   - preflight verdict from `$mantle-risk-evaluator` when a state-changing path is being prepared
   - allowance and spend-capacity context from `$mantle-portfolio-analyst` when approval scope or wallet coverage matters
8. Structure the result per `planning_mode` using the `Quick Checklist`:
   - `recommended`
   - `also_viable`
   - `discovery_only`
   - mention `DefiLlama` only for broader ecosystem discovery, never as contract truth
9. Load operation SOP only for `execution_ready` planning:
   - swap: `references/swap-sop.md`
   - liquidity: `references/liquidity-sop.md`
   - lending (supply/borrow/repay/withdraw): `references/lending-sop.md`
10. Resolve quote, pool, or market route only after the protocol choice is gated by verified contracts and supporting evidence.
11. If an approval is required, carry forward the allowance evidence and prepare the smallest viable `approve` step.
12. If account supports batching (for example ERC-4337 smart account), note whether approve+action can be safely batched by the external executor.
13. Produce an execution handoff plan (calls, parameters, sequencing, and risk notes). Do not sign, broadcast, deploy, or claim execution.
14. Define post-execution verification checks (balances, allowances, slippage) to run after the user confirms external execution.

## Guardrails

- **CLI-FIRST RULE**: ALWAYS use `mantle-cli` commands with `--json` to build unsigned transactions. NEVER manually construct calldata, hex-encode function calls, or extract addresses from text to build transactions yourself. The CLI handles ABI encoding, address validation, pool parameter resolution, and whitelist checks.
- **NO `from` FIELD**: NEVER add a `from` field to `unsigned_tx` objects. The signer determines `from` from the signing key. Adding `from` breaks Privy and other embedded wallet signers.
- **NO MANUAL ROUTING**: NEVER manually discover intermediate pools, split multi-hop swaps into separate transactions, or use external aggregators/routing services. The CLI auto-discovers 2-hop routes via bridge tokens (WMNT, USDC, USDT0, USDe, WETH) when no direct pair exists. Just pass `--in` and `--out` — the CLI handles the routing.
- **FACTORY-FIRST POOL DISCOVERY**: When looking for LP pools, ALWAYS use `mantle-cli lp find-pools --json` which queries factory contracts on-chain. Do NOT rely on DexScreener, subgraphs, or hardcoded lists — they have incomplete coverage.
- **ANALYZE BEFORE LP**: Before adding liquidity, ALWAYS run `mantle-cli defi analyze-pool --json` to get fee APR, multi-range comparison, risk scoring, and investment projections. Do NOT add liquidity based on guesswork about which range or how much to invest.
- **USD AMOUNT MODE**: When the user specifies an investment in USD (e.g. "invest $1000"), use `--amount-usd` instead of manually computing token amounts. The CLI reads pool state and computes the correct token ratio for the target tick range. Do NOT blindly split 50/50.
- **PERCENTAGE REMOVAL**: When the user wants to remove a fraction of a V3 position (e.g. "remove half"), use `--percentage 50` instead of manually reading and computing liquidity amounts. The CLI reads the position on-chain and calculates the exact liquidity to remove.
- **WETH EXISTS ON MANTLE**: WETH (bridged ETH) is at `0xdEAddEaDdeadDEadDEADDEAddEADDEAddead1111` with ~125K ETH supply and pools on all DEXes. Do NOT claim WETH doesn't exist. MNT being the gas token does not mean ETH is absent — ETH is bridged from L1.
- NEVER claim to have signed, broadcast, deployed, or executed any transaction. Do not use phrases like "I executed the swap", "the transaction was submitted", "swap complete", or "funds have been transferred." This skill produces plans only; an external signer/wallet must execute them.
- Act as a coordinator: when specialized address, risk, or portfolio skills apply, cite or request their output instead of re-deriving those judgments from scratch.
- In `discovery_only`, do not provide router addresses, approval steps, calldata, or execution sequencing.
- In `compare_only`, verified registry keys or contract roles may be named, but executable calldata and approval instructions stay out until execution evidence is complete.
- Do not proceed to external execution planning on `warn`/`high-risk` intents without explicit user confirmation.
- Reject unknown or unverified token/router/pool addresses.
- Never treat discovery data as a substitute for a verified registry key.
- If the required contract role cannot be resolved from the shared registry, mark the plan `blocked`.
- Mention discovery-only protocols only after clearly separating them from execution-ready options.
- Keep per-step idempotency notes for external retries.
- If the user asks for onchain execution, provide a handoff checklist and state that an external signer/wallet is required.

## Output Format

**MANDATORY:** Every response MUST use this exact structured template. Do not use prose or free-form text instead of this template. Fill every field; use "not applicable in {planning_mode} mode" for fields that do not apply to the current mode. In `discovery_only` mode, fields under Execution Handoff and Post-Execution Verification Plan must all say "not applicable in discovery_only mode."

```text
Mantle DeFi Pre-Execution Report
- operation_type:
- planning_mode: discovery_only | compare_only | execution_ready
- environment:
- intent_summary:
- analyzed_at_utc:

Preparation
- supporting_skills_used:
- address_resolution_ref:
- risk_report_ref:
- portfolio_report_ref:
- curated_defaults_considered:
- quote_source:
- expected_output_min:
- allowance_status:
- approval_plan:

Protocol Selection
- recommended:
- also_viable:
- discovery_only:
- rationale:
- data_freshness:
- confidence: high | medium | low

Execution Handoff
- recommended_calls:
- calldata_inputs:
- registry_key:
- sequencing_notes:
- batched_execution_possible: yes | no
- handoff_available: yes | no

Post-Execution Verification Plan
- balances_to_recheck:
- allowances_to_recheck:
- slippage_checks:
- anomalies_to_watch:

Status
- preflight_verdict: pass | warn | block | unknown
- readiness: ready | blocked | needs_input
- blocking_issues:
- next_action:
```

## References

- `references/defi-execution-guardrails.md`
- `references/swap-sop.md`
- `references/liquidity-sop.md`
- `references/lending-sop.md`
- `references/curated-defaults.yaml`
- `references/protocol-selection-policy.md`
