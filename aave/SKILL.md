---
name: aave
version: 1.0.1
description: Supply and withdraw tokens on Aave V3 lending pools
delivery: script
metadata:
  starchild:
    emoji: "🏦"
    skillKey: aave
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# Aave V3 Yield Farming

Supply tokens into Aave V3 lending pools to earn yield, withdraw at any time, and view positions across multiple chains.

Supported Networks: Ethereum, Arbitrum, Base, Optimism, Polygon, Avalanche.

## Runtime Mode

This skill is script-only. It does not register `aave_*` tools.

Call via Python exports:
- `aave_positions(chain)`
- `aave_supply(chain, token, amount)`
- `aave_withdraw(chain, token, amount=0, max=False)`

Imports:
`from skills.aave.exports import aave_positions, aave_supply, aave_withdraw`

Wallet dependency is runtime-only via `core.wallet_runtime`.

## Prerequisites

Before supply/withdraw, wallet policy must allow the transaction path.

## Supported Tokens by Chain

| Chain | USDC | USDT | DAI | WETH | WBTC |
|-------|------|------|-----|------|------|
| Ethereum | yes | yes | yes | yes | yes |
| Arbitrum | yes | yes | yes | yes | yes |
| Polygon | yes | yes | yes | yes | yes |
| Optimism | yes | yes | yes | yes | yes |
| Avalanche | yes | yes | yes | yes | yes |
| Base | yes | — | yes | yes | — |

## Script Examples

Read positions:

```python
import asyncio
from skills.aave.exports import aave_positions

async def main():
    result = await aave_positions(chain="arbitrum")
    print(result)

asyncio.run(main())
```

Supply 100 USDC:

```python
import asyncio
from skills.aave.exports import aave_supply

async def main():
    result = await aave_supply(chain="arbitrum", token="USDC", amount=100)
    print(result)

asyncio.run(main())
```

Withdraw partial / all:

```python
import asyncio
from skills.aave.exports import aave_withdraw

async def main():
    part = await aave_withdraw(chain="arbitrum", token="USDC", amount=50)
    print(part)
    full = await aave_withdraw(chain="arbitrum", token="USDC", max=True)
    print(full)

asyncio.run(main())
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown chain` | Invalid chain name | Use: ethereum, arbitrum, base, optimism, polygon, avalanche |
| `Unknown token` | Token not available on that chain | Check supported tokens table |
| `Insufficient balance` | Not enough tokens in wallet | Check wallet balance before supply |
| `Amount must be positive` | Zero or negative amount | Use a positive number |
| `Policy violation` | Wallet policy blocks transaction | Update wallet policy |
| `Not running on a Fly Machine` | Local dev environment | Supply/withdraw require deployed env with wallet |
