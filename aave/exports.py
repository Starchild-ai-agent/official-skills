"""
Aave script exports (tool-free runtime path).

Usage:
    python3 - <<'PY'
    import asyncio
    from skills.aave.exports import aave_positions

    async def main():
        print(await aave_positions(chain="arbitrum"))

    asyncio.run(main())
    PY
"""

from aave import get_user_positions, supply_token, withdraw_token


async def aave_positions(chain: str):
    return await get_user_positions(chain)


async def aave_supply(chain: str, token: str, amount: float):
    return await supply_token(chain, token, amount)


async def aave_withdraw(chain: str, token: str, amount: float = 0, max: bool = False):
    return await withdraw_token(chain, token, amount, max_withdraw=max)
