"""
Aave V3 Yield Farming — supply/withdraw tokens and view positions via on-chain calls.

Supply flow:
1. Get wallet address via Privy wallet service
2. Pre-flight balanceOf check via eth_call
3. TX1: ERC-20 approve(pool, amount) via wallet service
4. TX2: pool.supply(asset, amount, onBehalfOf, referralCode) via wallet service

Withdraw flow:
1. Get wallet address
2. Single TX: pool.withdraw(asset, amount_or_max, to) via wallet service

Positions flow (read-only):
1. getUserAccountData(wallet) via eth_call → 6 × uint256

No new dependencies — uses eth_utils.keccak (already in requirements) + manual ABI encoding.
Reuses _wallet_request and _is_fly_machine from tools/wallet.py.
"""

import logging
import os

import aiohttp
from eth_utils import keccak

from tools.wallet import _wallet_request, _is_fly_machine

logger = logging.getLogger(__name__)

# ── Supported Chains ─────────────────────────────────────────────────────────

SUPPORTED_CHAINS = {
    "ethereum": 1,
    "arbitrum": 42161,
    "polygon": 137,
    "optimism": 10,
    "avalanche": 43114,
    "base": 8453,
}

# ── Aave V3 Pool Addresses ──────────────────────────────────────────────────

AAVE_V3_POOL = {
    1:     "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",  # Ethereum
    42161: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Arbitrum
    137:   "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Polygon
    10:    "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Optimism
    43114: "0x794a61358D6845594F94dc1DB02A252b5b4814aD",  # Avalanche
    8453:  "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",  # Base
}

# ── Public RPC URLs (overridable via RPC_URL_{chain_id} env var) ─────────────

RPC_URLS = {
    1:     "https://eth.llamarpc.com",
    42161: "https://arb1.arbitrum.io/rpc",
    137:   "https://polygon-rpc.com",
    10:    "https://mainnet.optimism.io",
    43114: "https://api.avax.network/ext/bc/C/rpc",
    8453:  "https://mainnet.base.org",
}

# ── Token Registry ───────────────────────────────────────────────────────────
# {chain_id: {symbol: (address, decimals)}}

TOKEN_REGISTRY = {
    1: {
        "USDC":  ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        "USDT":  ("0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        "DAI":   ("0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
        "WETH":  ("0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", 18),
        "WBTC":  ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", 8),
    },
    42161: {
        "USDC":  ("0xaf88d065e77c8cC2239327C5EDb3A432268e5831", 6),
        "USDT":  ("0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", 6),
        "DAI":   ("0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", 18),
        "WETH":  ("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", 18),
        "WBTC":  ("0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", 8),
    },
    137: {
        "USDC":  ("0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", 6),
        "USDT":  ("0xc2132D05D31c914a87C6611C10748AEb04B58e8F", 6),
        "DAI":   ("0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", 18),
        "WETH":  ("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", 18),
        "WBTC":  ("0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6", 8),
    },
    10: {
        "USDC":  ("0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", 6),
        "USDT":  ("0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", 6),
        "DAI":   ("0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", 18),
        "WETH":  ("0x4200000000000000000000000000000000000006", 18),
        "WBTC":  ("0x68f180fcCe6836688e9084f035309E29Bf0A2095", 8),
    },
    43114: {
        "USDC":  ("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", 6),
        "USDT":  ("0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7", 6),
        "DAI":   ("0xd586E7F844cEa2F87f50152665BCbc2C279D8d70", 18),
        "WETH":  ("0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB", 18),
        "WBTC":  ("0x50b7545627a5162F82A992c33b87aDc75187B218", 8),
    },
    8453: {
        "USDC":  ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        "DAI":   ("0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb", 18),
        "WETH":  ("0x4200000000000000000000000000000000000006", 18),
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

UINT256_MAX = 2**256 - 1


def resolve_chain(chain: str) -> int:
    """Resolve chain name to chain_id."""
    name = chain.strip().lower()
    if name not in SUPPORTED_CHAINS:
        supported = ", ".join(sorted(SUPPORTED_CHAINS.keys()))
        raise ValueError(f"Unknown chain '{chain}'. Supported: {supported}")
    return SUPPORTED_CHAINS[name]


def resolve_token(chain_id: int, symbol: str) -> tuple:
    """Resolve token symbol to (address, decimals) for a chain."""
    tokens = TOKEN_REGISTRY.get(chain_id, {})
    key = symbol.strip().upper()
    if key not in tokens:
        available = ", ".join(sorted(tokens.keys())) if tokens else "none"
        chain_name = next((k for k, v in SUPPORTED_CHAINS.items() if v == chain_id), str(chain_id))
        raise ValueError(f"Unknown token '{symbol}' on {chain_name}. Available: {available}")
    return tokens[key]


def _get_rpc_url(chain_id: int) -> str:
    """Get RPC URL for the given chain, with env var override."""
    env_key = f"RPC_URL_{chain_id}"
    return os.environ.get(env_key, RPC_URLS.get(chain_id, ""))


# ── ABI Encoding (manual, no web3 dependency) ───────────────────────────────


def _encode_approve(spender: str, amount: int) -> str:
    """Encode ERC-20 approve(address, uint256) calldata."""
    selector = keccak(b"approve(address,uint256)")[:4]
    addr_bytes = bytes.fromhex(spender.replace("0x", "")).rjust(32, b"\x00")
    amount_bytes = amount.to_bytes(32, "big")
    return "0x" + (selector + addr_bytes + amount_bytes).hex()


def _encode_supply(asset: str, amount: int, on_behalf_of: str, referral_code: int = 0) -> str:
    """Encode Aave V3 supply(address, uint256, address, uint16) calldata."""
    selector = keccak(b"supply(address,uint256,address,uint16)")[:4]
    asset_bytes = bytes.fromhex(asset.replace("0x", "")).rjust(32, b"\x00")
    amount_bytes = amount.to_bytes(32, "big")
    behalf_bytes = bytes.fromhex(on_behalf_of.replace("0x", "")).rjust(32, b"\x00")
    referral_bytes = referral_code.to_bytes(32, "big")
    return "0x" + (selector + asset_bytes + amount_bytes + behalf_bytes + referral_bytes).hex()


def _encode_withdraw(asset: str, amount: int, to: str) -> str:
    """Encode Aave V3 withdraw(address, uint256, address) calldata."""
    selector = keccak(b"withdraw(address,uint256,address)")[:4]
    asset_bytes = bytes.fromhex(asset.replace("0x", "")).rjust(32, b"\x00")
    amount_bytes = amount.to_bytes(32, "big")
    to_bytes = bytes.fromhex(to.replace("0x", "")).rjust(32, b"\x00")
    return "0x" + (selector + asset_bytes + amount_bytes + to_bytes).hex()


def _encode_get_user_account_data(user: str) -> str:
    """Encode Aave V3 getUserAccountData(address) calldata."""
    selector = keccak(b"getUserAccountData(address)")[:4]
    user_bytes = bytes.fromhex(user.replace("0x", "")).rjust(32, b"\x00")
    return "0x" + (selector + user_bytes).hex()


def _encode_balance_of(owner: str) -> str:
    """Encode ERC-20 balanceOf(address) calldata."""
    selector = keccak(b"balanceOf(address)")[:4]
    owner_bytes = bytes.fromhex(owner.replace("0x", "")).rjust(32, b"\x00")
    return "0x" + (selector + owner_bytes).hex()


# ── RPC Helper ───────────────────────────────────────────────────────────────


async def _eth_call(to: str, data: str, chain_id: int) -> str:
    """Execute a read-only eth_call via JSON-RPC."""
    rpc_url = _get_rpc_url(chain_id)
    if not rpc_url:
        raise ValueError(f"No RPC URL configured for chain {chain_id}")

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            rpc_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status >= 400:
                body = await resp.text()
                raise Exception(f"RPC error {resp.status}: {body}")
            result = await resp.json()

    if "error" in result:
        raise Exception(f"RPC error: {result['error']}")

    return result["result"]


# ── Supply Flow ──────────────────────────────────────────────────────────────


async def supply_token(chain: str, token: str, amount: float) -> dict:
    """
    Supply tokens to Aave V3.

    Flow:
    1. Resolve chain + token
    2. Get wallet address
    3. Pre-flight balanceOf check
    4. TX1: approve(pool, amount)
    5. TX2: pool.supply(asset, amount, wallet, 0)
    """
    if not _is_fly_machine():
        raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    chain_id = resolve_chain(chain)
    token_address, decimals = resolve_token(chain_id, token)
    pool_address = AAVE_V3_POOL[chain_id]
    amount_base = int(amount * (10 ** decimals))

    # 1. Get wallet address
    wallet_data = await _wallet_request("GET", "/agent/wallet")
    wallets = wallet_data.get("wallets", wallet_data.get("data", []))
    wallet_address = None
    for w in (wallets if isinstance(wallets, list) else [wallets]):
        if w.get("chain_type") == "ethereum":
            wallet_address = w.get("wallet_address", w.get("address"))
            break
    if not wallet_address:
        raise RuntimeError("No EVM wallet found")

    logger.info(f"Aave supply: {amount} {token} on {chain} (wallet={wallet_address})")

    # 2. Pre-flight balance check
    balance_data = _encode_balance_of(wallet_address)
    balance_hex = await _eth_call(token_address, balance_data, chain_id)
    balance = int(balance_hex, 16)
    if balance < amount_base:
        balance_human = balance / (10 ** decimals)
        raise ValueError(
            f"Insufficient {token} balance: have {balance_human}, need {amount}"
        )

    # 3. TX1: approve
    approve_data = _encode_approve(pool_address, amount_base)
    logger.info(f"Aave supply: sending approve TX (amount_base={amount_base})")
    approve_result = await _wallet_request("POST", "/agent/transfer", {
        "to": token_address,
        "amount": "0",
        "data": approve_data,
        "chain_id": chain_id,
    })
    approve_tx = approve_result.get("tx_hash", approve_result.get("hash", "unknown"))
    logger.info(f"Aave supply: approve TX = {approve_tx}")

    # 4. TX2: supply
    supply_data = _encode_supply(token_address, amount_base, wallet_address, 0)
    logger.info("Aave supply: sending supply TX")
    supply_result = await _wallet_request("POST", "/agent/transfer", {
        "to": pool_address,
        "amount": "0",
        "data": supply_data,
        "chain_id": chain_id,
    })
    supply_tx = supply_result.get("tx_hash", supply_result.get("hash", "unknown"))
    logger.info(f"Aave supply: supply TX = {supply_tx}")

    return {
        "approve_tx_hash": approve_tx,
        "supply_tx_hash": supply_tx,
        "token": token.upper(),
        "amount": amount,
        "amount_base_units": amount_base,
        "chain": chain,
        "chain_id": chain_id,
        "pool": pool_address,
    }


# ── Withdraw Flow ────────────────────────────────────────────────────────────


async def withdraw_token(chain: str, token: str, amount: float = 0, max_withdraw: bool = False) -> dict:
    """
    Withdraw tokens from Aave V3.

    Args:
        chain: Network name
        token: Token symbol
        amount: Amount to withdraw (ignored if max_withdraw=True)
        max_withdraw: If True, withdraw maximum available
    """
    if not _is_fly_machine():
        raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

    if not max_withdraw and amount <= 0:
        raise ValueError("Amount must be positive, or set max=true")

    chain_id = resolve_chain(chain)
    token_address, decimals = resolve_token(chain_id, token)
    pool_address = AAVE_V3_POOL[chain_id]

    if max_withdraw:
        withdraw_amount = UINT256_MAX
    else:
        withdraw_amount = int(amount * (10 ** decimals))

    # 1. Get wallet address
    wallet_data = await _wallet_request("GET", "/agent/wallet")
    wallets = wallet_data.get("wallets", wallet_data.get("data", []))
    wallet_address = None
    for w in (wallets if isinstance(wallets, list) else [wallets]):
        if w.get("chain_type") == "ethereum":
            wallet_address = w.get("wallet_address", w.get("address"))
            break
    if not wallet_address:
        raise RuntimeError("No EVM wallet found")

    logger.info(f"Aave withdraw: {'max' if max_withdraw else amount} {token} on {chain}")

    # 2. Single TX: withdraw
    withdraw_data = _encode_withdraw(token_address, withdraw_amount, wallet_address)
    withdraw_result = await _wallet_request("POST", "/agent/transfer", {
        "to": pool_address,
        "amount": "0",
        "data": withdraw_data,
        "chain_id": chain_id,
    })
    withdraw_tx = withdraw_result.get("tx_hash", withdraw_result.get("hash", "unknown"))
    logger.info(f"Aave withdraw: TX = {withdraw_tx}")

    return {
        "withdraw_tx_hash": withdraw_tx,
        "token": token.upper(),
        "amount": "max" if max_withdraw else amount,
        "chain": chain,
        "chain_id": chain_id,
        "pool": pool_address,
    }


# ── Positions Flow (read-only) ──────────────────────────────────────────────


async def get_user_positions(chain: str) -> dict:
    """
    Get Aave V3 user account data via eth_call.

    Returns:
        totalCollateralBase, totalDebtBase, availableBorrowsBase,
        currentLiquidationThreshold, ltv, healthFactor
        (all denominated in Aave's base currency — USD with 8 decimals)
    """
    if not _is_fly_machine():
        raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

    chain_id = resolve_chain(chain)
    pool_address = AAVE_V3_POOL[chain_id]

    # Get wallet address
    wallet_data = await _wallet_request("GET", "/agent/wallet")
    wallets = wallet_data.get("wallets", wallet_data.get("data", []))
    wallet_address = None
    for w in (wallets if isinstance(wallets, list) else [wallets]):
        if w.get("chain_type") == "ethereum":
            wallet_address = w.get("wallet_address", w.get("address"))
            break
    if not wallet_address:
        raise RuntimeError("No EVM wallet found")

    # eth_call getUserAccountData
    calldata = _encode_get_user_account_data(wallet_address)
    result_hex = await _eth_call(pool_address, calldata, chain_id)

    # Decode 6 × uint256 (each 32 bytes = 64 hex chars)
    raw = result_hex.replace("0x", "")
    if len(raw) < 384:  # 6 * 64
        raise Exception(f"Unexpected response length: {len(raw)} hex chars")

    values = []
    for i in range(6):
        chunk = raw[i * 64 : (i + 1) * 64]
        values.append(int(chunk, 16))

    total_collateral_base = values[0]
    total_debt_base = values[1]
    available_borrows_base = values[2]
    current_liquidation_threshold = values[3]
    ltv = values[4]
    health_factor = values[5]

    # Aave V3 base currency is USD with 8 decimals
    base_decimals = 8

    return {
        "wallet": wallet_address,
        "chain": chain,
        "chain_id": chain_id,
        "total_collateral_usd": total_collateral_base / (10 ** base_decimals),
        "total_debt_usd": total_debt_base / (10 ** base_decimals),
        "available_borrows_usd": available_borrows_base / (10 ** base_decimals),
        "current_liquidation_threshold": current_liquidation_threshold / 100,  # basis points to %
        "ltv": ltv / 100,  # basis points to %
        "health_factor": health_factor / (10 ** 18) if health_factor < UINT256_MAX else "infinite",
        "raw": {
            "totalCollateralBase": str(total_collateral_base),
            "totalDebtBase": str(total_debt_base),
            "availableBorrowsBase": str(available_borrows_base),
            "currentLiquidationThreshold": str(current_liquidation_threshold),
            "ltv": str(ltv),
            "healthFactor": str(health_factor),
        },
    }
