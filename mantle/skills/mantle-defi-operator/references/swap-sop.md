# Swap SOP

Use this standard flow for token swap pre-execution analysis on Mantle.

## CRITICAL: Use CLI for Transaction Building

**ALWAYS use `mantle-cli` to build unsigned transactions.** Do NOT manually construct calldata, extract addresses from text, or build approve calls yourself. The CLI handles address resolution, ABI encoding, pool parameter lookup, multi-hop routing, and whitelist validation correctly.

```bash
# Build the swap transaction — works for both direct and multi-hop routes
mantle-cli swap build-swap --provider fluxion --in WMNT --out BSB \
  --amount 0.5 --recipient 0x... --json

# If approval is needed
mantle-cli swap approve --token WMNT --spender <router_address> \
  --amount <exact_or_max> --owner <wallet> --json

# Check available pairs and pool parameters
mantle-cli swap pairs --provider fluxion --json
```

The CLI outputs `unsigned_tx` with `to`, `data`, `value`, `chainId` — **no `from` field**. Pass this directly to the signer without modification.

## Multi-hop Routing (Built-in)

The CLI **automatically discovers multi-hop routes** when no direct pair exists. You do NOT need to find intermediate pools or build multi-step swaps yourself.

**How it works:** when `--in A --out B` has no direct pool, the CLI tries 2-hop paths via bridge tokens (WMNT, USDC, USDT0, USDe, WETH) using the registered pair registry. If a route `A → bridge → B` exists, it builds a single `exactInput` (V3) or multi-token-path (Merchant Moe) transaction.

**Examples of auto-routed swaps:**

```bash
# WMNT → BSB  (auto-routes: WMNT → USDT0 → BSB on Fluxion)
mantle-cli swap build-swap --provider fluxion --in WMNT --out BSB --amount 0.5 --recipient 0x... --json

# WMNT → wTSLAx  (auto-routes: WMNT → USDC → wTSLAx on Fluxion)
mantle-cli swap build-swap --provider fluxion --in WMNT --out wTSLAx --amount 0.5 --recipient 0x... --json

# WMNT → ELSA  (auto-routes: WMNT → USDT0 → ELSA on Fluxion)
mantle-cli swap build-swap --provider fluxion --in WMNT --out ELSA --amount 0.5 --recipient 0x... --json
```

**What you MUST NOT do:**
- Do NOT manually split a swap into two separate transactions (e.g. WMNT→USDT0 then USDT0→BSB). The CLI handles this as a single atomic multi-hop transaction with better gas efficiency.
- Do NOT search for intermediate pools or bridge tokens yourself. The CLI's route discovery uses the verified pair registry.
- Do NOT use aggregators or external routing services. Only use `mantle-cli swap build-swap`.

**When multi-hop is used**, the response will show:
- `intent: "swap_multihop"` (instead of `"swap"`)
- `human_summary` shows the full path (e.g. "Swap 0.5 WMNT → BSB via WMNT → USDT0 → BSB on Fluxion")
- `warnings` include the route details and fee tiers

## Step 1: Normalize input

- token in/out symbols or addresses
- exact input amount
- recipient address
- slippage cap (default 0.5%)

## Step 2: Select candidate protocol

- Start with curated defaults: `Merchant Moe`, `Agni`, `Fluxion`.
- Use `mantle-cli swap pairs --json` to check available pairs and pool parameters per DEX.
- Resolve the execution-ready router/quoter from `mantle-address-registry-navigator`.
- If the user names another venue, verify its contracts before comparing it.
- For xStocks RWA tokens (wTSLAx, wAAPLx, wNVDAx, etc.) → use **Fluxion** (only DEX with these pools).
- For BSB, ELSA, VOOI → use **Fluxion** (paired with USDT0).

## Step 3: Token metadata

- For tokens in the registry, use their symbol directly.
- For unknown tokens, pass the contract address — the CLI resolves decimals on-chain.

## Step 4: Build the swap

```bash
mantle-cli swap build-swap --provider <dex> --in <token> --out <token> \
  --amount <amount> --recipient <wallet> --json
```

- The CLI auto-resolves pool parameters (fee_tier, bin_step) from the pair registry.
- The CLI auto-discovers multi-hop routes when no direct pair exists.
- Just specify `--in`, `--out`, `--amount`, and `--provider` — the CLI does the rest.

## Step 5: Allowance check and approve

- The swap router address is in the `unsigned_tx.to` field of the build-swap response.
- Check if the input token is approved for that router.
- If insufficient:
  ```bash
  mantle-cli swap approve --token <token> --spender <router_from_tx_to> --amount <exact_or_max> --owner <wallet> --json
  ```

## Step 6: Sign and broadcast

- Pass the `unsigned_tx` object directly to the external signer.
- **Do NOT add a `from` field.**
- **Do NOT modify any fields.**

## Step 7: Post-execution verification

- Re-read balances to confirm the swap completed.
- Compare observed output versus expected.

## Common pitfalls

- **`from` field**: NEVER add `from` to unsigned_tx — breaks Privy and embedded signers.
- **Manual routing**: NEVER manually discover pools or split multi-hop into separate txs — use the CLI's built-in routing.
- **Wrong pool parameters**: NEVER manually specify `--fee-tier` or `--bin-step` for registered pairs — the CLI resolves them automatically.
- **Merchant Moe version enum**: the CLI handles this correctly (V1=0, V2.2=3); do NOT override.
- **Missing approve**: swaps require prior ERC-20 approval for the router contract.
- **Multi-hop slippage**: multi-hop routes have higher slippage risk — always get a quote first when possible.
