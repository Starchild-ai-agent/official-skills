# Lending SOP

Use this standard flow for Aave V3 lending operations (supply, borrow, repay, withdraw) on Mantle.

## CRITICAL: Use CLI for Transaction Building

**ALWAYS use `mantle-cli` to build unsigned transactions.** Do NOT manually construct calldata, extract addresses from text, or build approve calls yourself. The CLI handles address resolution, ABI encoding, and whitelist validation correctly.

```bash
# All commands support --json for structured output
mantle-cli aave supply   --asset USDC --amount 1.0 --on-behalf-of 0x... --json
mantle-cli aave borrow   --asset USDC --amount 0.5 --on-behalf-of 0x... --json
mantle-cli aave repay    --asset USDC --amount 0.5 --on-behalf-of 0x... --json
mantle-cli aave repay    --asset USDC --amount max --on-behalf-of 0x... --json
mantle-cli aave withdraw --asset USDC --amount 1.0 --to 0x... --json
mantle-cli aave withdraw --asset USDC --amount max --to 0x... --json
mantle-cli aave markets  --json  # check APY/TVL before deciding
```

For approvals (required before supply/repay):
```bash
mantle-cli swap approve --token USDC --spender 0x458F293454fE0d67EC0655f3672301301DD51422 --amount max --json
```

The CLI outputs `unsigned_tx` with `to`, `data`, `value`, `chainId` — **no `from` field**. Pass this directly to the signer without modification.

## Step 1: Check lending markets

```bash
mantle-cli aave markets --json
```

- Review supply APY, borrow APY, TVL, LTV, and liquidation threshold.
- Confirm the target asset is a supported Aave V3 reserve.
- Supported assets: WETH, WMNT, USDT0, USDC, USDe, sUSDe, FBTC, syrupUSDT, wrsETH, GHO.

## Step 2: Normalize input

- Asset symbol or address
- Amount (decimal, or `max` for repay/withdraw)
- Wallet address (on_behalf_of for supply/borrow/repay, to for withdraw)

## Step 3: Check balance and allowance

```bash
mantle-cli account balance <wallet> --tokens USDC,USDT0 --json
```

- Verify the wallet has sufficient token balance for supply/repay.
- The Aave Pool address is `0x458F293454fE0d67EC0655f3672301301DD51422`.

## Step 4: Approve if needed

If allowance is insufficient for supply or repay:

```bash
mantle-cli swap approve --token USDC \
  --spender 0x458F293454fE0d67EC0655f3672301301DD51422 \
  --amount <exact_or_max> --owner <wallet> --json
```

- The CLI validates the spender against the whitelist.
- Use `--owner` to check existing allowance and skip if already sufficient.
- Sign and broadcast the approve `unsigned_tx` before proceeding to supply/repay.

## Step 5: Build the lending transaction

Use the appropriate CLI command:

| Operation | Command | Key flags |
|-----------|---------|-----------|
| Deposit | `mantle-cli aave supply` | `--asset`, `--amount`, `--on-behalf-of` |
| Borrow | `mantle-cli aave borrow` | `--asset`, `--amount`, `--on-behalf-of`, `--interest-rate-mode` |
| Repay | `mantle-cli aave repay` | `--asset`, `--amount` (or `max`), `--on-behalf-of` |
| Withdraw | `mantle-cli aave withdraw` | `--asset`, `--amount` (or `max`), `--to` |

Always use `--json` to get structured output for the signer.

## Step 6: Sign and broadcast

- Pass the `unsigned_tx` object directly to the external signer.
- **Do NOT add a `from` field** — the signer determines `from` from the signing key.
- **Do NOT modify `to`, `data`, `value`, or `chainId`** fields.

## Step 7: Post-execution verification

- Re-read token balance and aToken balance to confirm the operation.
- For supply: verify aToken balance increased.
- For borrow: verify token balance increased and debt token appeared.
- For repay: verify debt token balance decreased.
- For withdraw: verify aToken balance decreased and token balance increased.
- Check health factor after borrow/withdraw to ensure it remains above 1.0.

## Common pitfalls

- **Missing approve**: supply and repay require prior ERC-20 approval for the Aave Pool.
- **`from` field in unsigned_tx**: NEVER add `from` — this breaks Privy and some signers.
- **Stale allowance**: use `--owner` flag in approve to auto-skip if sufficient.
- **Health factor**: borrow and withdraw reduce health factor — check before proceeding.
- **`max` semantics**: repay max repays full debt; withdraw max withdraws full balance.
