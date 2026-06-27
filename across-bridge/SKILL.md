---
name: across-bridge
version: 1.0.0
description: |
  Bridge ETH and ERC-20 tokens across EVM chains via Across Protocol v3.
  One function for a quote, one function for the entire end-to-end bridge
  (approval + deposit + arrival verification).

  Use when the user wants to move tokens between chains (e.g. "bridge 50 USDC
  from Base to Arbitrum", "send ETH from Ethereum to Optimism", "move USDT
  Arbitrum → Base"). Supports Ethereum, Arbitrum, Optimism, Base, Polygon,
  BSC, Linea, zkSync, Scroll, Mantle. Fast settlement (seconds to minutes).
author: starchild
tags: [bridge, defi, cross-chain, across, evm, ethereum, arbitrum, base, optimism]
delivery: script
metadata:
  starchild:
    emoji: 🌉
    skillKey: across-bridge
    requires:
      bins: [python3]
    install:
      - kind: pip
        package: requests
---

# 🌉 Across Bridge

Bridge tokens between EVM chains using [Across Protocol](https://across.to) v3.
Across is an intent-based bridge: relayers front the liquidity on the
destination chain and get repaid on the origin chain, so settlement is fast
(seconds to a few minutes) and fees are low (0.05–0.5%).

## When to Use

- **Cross-chain token transfer**: "bridge 50 USDC from Base to Arbitrum"
- **L1 ↔ L2 movement**: "send 0.01 ETH from Ethereum to Optimism"
- **Stablecoin hops**: "move USDT from Arbitrum to Base"
- **Speed matters**: Across fills in seconds–minutes vs native bridges (7 days)

## Supported Chains

Ethereum · Arbitrum · Optimism · Base · Polygon · BSC · Linea · zkSync · Scroll · Mantle

## Supported Tokens

ETH · WETH · USDC · USDT · WBTC · DAI

## How to Call

All operations are Python functions exposed under `core.skill_tools`. Because
the skill name contains a hyphen, use the `_modules` dict to access it:

```bash
python3 - <<'EOF'
from core.skill_tools import _modules
across = _modules["across-bridge"]
import json
q = across.bridge_quote(from_chain="base", to_chain="arbitrum",
                        token="USDC", amount=1, wallet="0x...")
print(json.dumps(q, indent=2))
EOF
```

### `bridge_quote(from_chain, to_chain, token, amount, wallet=None)`

Get a live quote — no on-chain action. Returns output amount, fees, estimated
fill time, and (if `wallet` is provided) ready-to-sign approval + bridge
transactions.

### `bridge_execute(from_chain, to_chain, token, amount, wallet, confirm_arrival=True)`

**One call does everything:**

1. Fetches a fresh quote from Across `/swap`
2. Sends ERC-20 approval to the SpokePool (if needed; skipped for native ETH)
3. Sends the `depositV3` bridge transaction
4. Polls the destination-chain balance until funds arrive (or timeout)

Returns a full receipt with `status`, `output_amount`, `approval_tx`,
`bridge_tx`, and `arrival_confirmed`.

### `bridge_status(origin_chain, deposit_tx_hash)`

Check the fill status of a submitted deposit via Across's status API.

## Workflows

### Just get a quote (no execution)

```bash
python3 - <<'EOF'
from core.skill_tools import _modules
across = _modules["across-bridge"]
import json
q = across.bridge_quote(from_chain="base", to_chain="arbitrum",
                        token="USDC", amount=50)
print(json.dumps(q, indent=2))
EOF
```

Key fields in the response:
- `output_amount_human` — tokens the recipient will receive
- `fees.total_pct` — fee percentage (e.g. `4688000000000000` = 0.47%)
- `estimated_fill_time_sec` — expected settlement time
- `needs_approval` — whether an ERC-20 approve is required before bridging

### Bridge end-to-end (the common case)

```bash
python3 - <<'EOF'
from core.skill_tools import _modules
across = _modules["across-bridge"]
import json
r = across.bridge_execute(from_chain="base", to_chain="arbitrum",
                          token="USDC", amount=1,
                          wallet="0x0B52...Eb16")
print(json.dumps(r, indent=2, default=str))
EOF
```

That single call handles approval + deposit + arrival verification. No need
to manually call `wallet_transfer` or encode calldata — the Across `/swap`
API returns ready-to-sign transactions and this skill dispatches them.

### Check status of a submitted deposit

```bash
python3 - <<'EOF'
from core.skill_tools import _modules
across = _modules["across-bridge"]
import json
s = across.bridge_status(origin_chain="base", deposit_tx_hash="0x...")
print(json.dumps(s, indent=2))
EOF
```

## Acceptance / Red-Flag Guidance

**Good routes:**
- Fee < 0.5% · fill time < 60s · output ≈ input (minus small fee)

**Warn the user before proceeding if:**
- Fee > 1% (expensive route or very small amount — min deposit applies)
- Fill time > 10 minutes (congested route)
- Amount below `limits.min_deposit` (quote will flag `isAmountTooLow`)

## Key Facts

- **Native ETH**: `msg.value` carries the amount; no approval step. Across
  handles wrapping/unwrapping automatically.
- **ERC-20**: `msg.value` = 0; an `approve(spokePool, amount)` is required
  first. `bridge_execute` sends this automatically.
- **Quotes are live** from `app.across.to/api/swap` and valid for ~30s.
  `bridge_execute` re-fetches right before broadcasting.
- **Gas is sponsored** by default via the Starchild wallet — the user doesn't
  need native tokens on the origin chain for gas.
- **Settlement**: Across relayers typically fill within seconds to a few
  minutes. `bridge_execute` polls the destination balance for up to 180s.
- **Wallet**: uses the Starchild Agent Wallet (same as the `wallet` skill).
  No separate wallet connection needed.

## Dependencies

- `requests` (pip)
- `core.skill_tools.wallet` (platform — for signing/broadcasting)

## Tested Routes

This skill was validated with a real on-chain bridge: 1 USDC Base → Arbitrum,
confirmed arrived on destination within ~35 seconds, fee 0.47%.
