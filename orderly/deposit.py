"""
Orderly Network Deposit & Withdraw — smart contract deposits and EIP-712 withdrawals.

Deposit flow (on-chain):
1. ensure_registered() → get account_id
2. Query getDepositFee() via eth_call to Arbitrum RPC
3. TX1: ERC-20 approve(vault, amount) via wallet service
4. TX2: vault.deposit(accountId, brokerHash, tokenHash, amount) via wallet service

Withdraw flow (API + EIP-712):
1. ensure_registered() → get account_id
2. GET /v1/withdraw_nonce (Ed25519 signed)
3. Sign EIP-712 Withdraw message via Privy wallet
4. POST /v1/withdraw_request (Ed25519 signed)

No new dependencies — uses eth_utils.keccak (already in requirements) + manual ABI encoding.
"""

import json
import logging
import os
import time

import aiohttp
from eth_utils import keccak

from tools.wallet import _wallet_request, _is_fly_machine
from . import signing

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

VAULT_ADDRESS = "0x816f722424B49Cf1275cc86DA9840Fbd5a6167e9"

USDC_ADDRESSES = {
    42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Arbitrum
    1: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",      # Ethereum
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # Base
    10: "0x0b2c639c533813f4aa9d7837caf62653d097ff85",      # Optimism
}

USDC_DECIMALS = 6

DEFAULT_ARBITRUM_RPC = "https://arb1.arbitrum.io/rpc"

BROKER_HASH = keccak(b"woofi_pro")   # bytes32
TOKEN_HASH = keccak(b"USDC")         # bytes32

# ── ABI Encoding (manual, no web3 dependency) ───────────────────────────────


def _encode_approve(spender: str, amount: int) -> str:
    """Encode ERC-20 approve(address, uint256) calldata."""
    # selector: keccak256("approve(address,uint256)")[:4]
    selector = keccak(b"approve(address,uint256)")[:4]
    # address → left-padded to 32 bytes
    addr_bytes = bytes.fromhex(spender.replace("0x", "")).rjust(32, b"\x00")
    # uint256 → big-endian 32 bytes
    amount_bytes = amount.to_bytes(32, "big")
    return "0x" + (selector + addr_bytes + amount_bytes).hex()


def _encode_deposit(account_id: str, broker_hash: bytes, token_hash: bytes, amount_base: int) -> str:
    """
    Encode vault deposit(VaultDepositFE) calldata.

    VaultDepositFE = (bytes32 accountId, bytes32 brokerHash, bytes32 tokenHash, uint128 tokenAmount)
    Solidity: deposit((bytes32,bytes32,bytes32,uint128))
    """
    # Function selector for deposit((bytes32,bytes32,bytes32,uint128))
    selector = keccak(b"deposit((bytes32,bytes32,bytes32,uint128))")[:4]

    # Struct with all static fields — encoded inline (no offset pointer)
    # account_id: hex string → bytes32
    acct_bytes = bytes.fromhex(account_id.replace("0x", "")).ljust(32, b"\x00")
    if len(acct_bytes) > 32:
        acct_bytes = acct_bytes[:32]

    # broker_hash and token_hash are already bytes32
    broker_bytes = broker_hash.rjust(32, b"\x00")[:32]
    token_bytes = token_hash.rjust(32, b"\x00")[:32]

    # uint128 → padded to 32 bytes
    amount_bytes = amount_base.to_bytes(32, "big")

    return "0x" + (selector + acct_bytes + broker_bytes + token_bytes + amount_bytes).hex()


def _encode_get_deposit_fee(receiver: str, account_id: str, broker_hash: bytes, token_hash: bytes, amount_base: int) -> str:
    """
    Encode getDepositFee(address,(bytes32,bytes32,bytes32,uint128)) calldata.

    The vault's getDepositFee requires the receiver address and the full
    VaultDepositFE struct to calculate the LayerZero cross-chain fee.
    """
    selector = keccak(b"getDepositFee(address,(bytes32,bytes32,bytes32,uint128))")[:4]

    # address → left-padded to 32 bytes
    recv_bytes = bytes.fromhex(receiver.replace("0x", "")).rjust(32, b"\x00")

    # struct fields (all static, encoded inline — no offset pointer)
    acct_bytes = bytes.fromhex(account_id.replace("0x", "")).ljust(32, b"\x00")[:32]
    broker_bytes = broker_hash.rjust(32, b"\x00")[:32]
    token_bytes = token_hash.rjust(32, b"\x00")[:32]
    amount_bytes = amount_base.to_bytes(32, "big")

    return "0x" + (selector + recv_bytes + acct_bytes + broker_bytes + token_bytes + amount_bytes).hex()


# ── RPC Helper ───────────────────────────────────────────────────────────────


def _get_rpc_url(chain_id: int = 42161) -> str:
    """Get RPC URL for the given chain."""
    if chain_id == 42161:
        return os.environ.get("ARBITRUM_RPC_URL", DEFAULT_ARBITRUM_RPC)
    raise ValueError(f"No RPC configured for chain {chain_id}")


async def _eth_call(to: str, data: str, chain_id: int = 42161) -> str:
    """Execute a read-only eth_call via JSON-RPC."""
    rpc_url = _get_rpc_url(chain_id)
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


# ── Deposit Flow ─────────────────────────────────────────────────────────────


async def deposit_usdc(amount: float) -> dict:
    """
    Deposit USDC into Orderly trading account.

    Flow:
    1. ensure_registered() → account_id
    2. getDepositFee() via eth_call
    3. TX1: approve(vault, amount) on USDC contract
    4. TX2: deposit(accountId, brokerHash, tokenHash, amount) on vault

    Args:
        amount: USDC amount (e.g. 34.08)

    Returns:
        dict with approve_tx_hash, deposit_tx_hash, amount_deposited, fee_paid
    """
    if not _is_fly_machine():
        raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    chain_id = signing._get_chain_id()
    usdc_address = USDC_ADDRESSES.get(chain_id)
    if not usdc_address:
        raise ValueError(f"No USDC address configured for chain {chain_id}")

    # 1. Ensure registered
    account_id = await signing.ensure_registered()
    wallet_address = await signing._get_wallet_address()
    logger.info(f"Orderly deposit: account={account_id}, wallet={wallet_address}, amount={amount} USDC")

    # 2. Calculate base amount (USDC has 6 decimals)
    amount_base = int(amount * (10 ** USDC_DECIMALS))

    # 3. Get deposit fee (requires receiver address and full struct)
    fee_data = _encode_get_deposit_fee(wallet_address, account_id, BROKER_HASH, TOKEN_HASH, amount_base)
    fee_hex = await _eth_call(VAULT_ADDRESS, fee_data, chain_id)
    fee_wei = int(fee_hex, 16)
    logger.info(f"Orderly deposit fee: {fee_wei} wei ({fee_wei / 1e18:.8f} ETH)")

    # 4. TX1: approve
    approve_data = _encode_approve(VAULT_ADDRESS, amount_base)
    logger.info(f"Orderly deposit: sending approve TX (amount_base={amount_base})")
    approve_result = await _wallet_request("POST", "/agent/transfer", {
        "to": usdc_address,
        "amount": "0",
        "data": approve_data,
        "chain_id": chain_id,
    })
    approve_tx = approve_result.get("tx_hash", approve_result.get("hash", "unknown"))
    logger.info(f"Orderly deposit: approve TX = {approve_tx}")

    # 5. TX2: deposit
    deposit_data = _encode_deposit(account_id, BROKER_HASH, TOKEN_HASH, amount_base)
    logger.info(f"Orderly deposit: sending deposit TX (fee={fee_wei} wei)")
    deposit_result = await _wallet_request("POST", "/agent/transfer", {
        "to": VAULT_ADDRESS,
        "amount": str(fee_wei),
        "data": deposit_data,
        "chain_id": chain_id,
    })
    deposit_tx = deposit_result.get("tx_hash", deposit_result.get("hash", "unknown"))
    logger.info(f"Orderly deposit: deposit TX = {deposit_tx}")

    return {
        "approve_tx_hash": approve_tx,
        "deposit_tx_hash": deposit_tx,
        "amount_deposited": amount,
        "amount_base_units": amount_base,
        "fee_paid_wei": fee_wei,
        "chain_id": chain_id,
    }


# ── Withdraw Flow ────────────────────────────────────────────────────────────


async def withdraw_usdc(amount: float) -> dict:
    """
    Withdraw USDC from Orderly trading account.

    Flow:
    1. ensure_registered() → account_id, wallet_address
    2. GET /v1/withdraw_nonce (Ed25519 signed)
    3. Sign EIP-712 Withdraw message via Privy wallet
    4. POST /v1/withdraw_request (Ed25519 signed)

    Args:
        amount: USDC amount (e.g. 10.0)

    Returns:
        dict with withdraw response and amount
    """
    if not _is_fly_machine():
        raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    chain_id = signing._get_chain_id()

    # 1. Ensure registered
    account_id = await signing.ensure_registered()
    wallet_address = await signing._get_wallet_address()
    logger.info(f"Orderly withdraw: account={account_id}, amount={amount} USDC")

    # 2. Get withdraw nonce
    nonce = await signing.get_withdraw_nonce()
    logger.info(f"Orderly withdraw: nonce={nonce}")

    # 3. Build and sign EIP-712 Withdraw message
    timestamp = int(time.time() * 1000)
    amount_base = int(amount * (10 ** USDC_DECIMALS))

    message = {
        "brokerId": signing._get_broker_id(),
        "chainId": chain_id,
        "receiver": wallet_address,
        "token": "USDC",
        "amount": amount_base,
        "withdrawNonce": nonce,
        "timestamp": timestamp,
    }

    result = await _wallet_request("POST", "/agent/sign-typed-data", {
        "domain": signing.WITHDRAW_DOMAIN,
        "types": signing.WITHDRAW_TYPES,
        "primaryType": "Withdraw",
        "message": message,
    })

    signature = signing._reconstruct_signature(result)
    logger.info(f"Orderly withdraw: EIP-712 signature obtained")

    # 4. POST /v1/withdraw_request
    from .client import _get_client
    client = _get_client()

    withdraw_body = {
        "signature": signature,
        "userAddress": wallet_address,
        "verifyingContract": signing.WITHDRAW_DOMAIN["verifyingContract"],
        "message": message,
    }

    withdraw_result = await client._private_request(
        "POST", "/v1/withdraw_request", body=withdraw_body
    )
    logger.info(f"Orderly withdraw: result={withdraw_result}")

    return {
        "withdraw_result": withdraw_result,
        "amount": amount,
        "amount_base_units": amount_base,
        "chain_id": chain_id,
        "receiver": wallet_address,
    }
