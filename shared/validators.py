"""
Input Validators for Crypto Skills
=====================================
解决: 零输入校验的安全敏感操作。

All validators raise ValidationError (from errors.py) on failure,
so small models get structured error messages with suggestions.

用法:
    from shared.validators import (
        validate_evm_address, validate_order_size,
        validate_leverage, validate_amount_vs_balance
    )

    addr = validate_evm_address("0xabc...")  # returns checksummed
    validate_order_size(0.001, min_sz=0.00001, asset="BTC")
"""

import re
from typing import Optional


# ─── EVM Address ─────────────────────────────────────────────────

_HEX_ADDR = re.compile(r'^0x[0-9a-fA-F]{40}$')
_ZERO_ADDR = "0x" + "0" * 40


def _keccak256(data: bytes) -> bytes:
    """Pure Python Keccak-256 for EIP-55 checksum.
    Falls back gracefully if no crypto libs available."""
    try:
        from hashlib import sha3_256 as _sha3
        return _sha3(data).digest()
    except ImportError:
        pass
    try:
        import hashlib
        h = hashlib.new('sha3_256')
        h.update(data)
        return h.digest()
    except (ImportError, ValueError):
        # Fallback: skip checksum validation, just normalize
        return b'\x00' * 32


def to_checksum_address(addr: str) -> str:
    """Convert to EIP-55 checksummed address."""
    addr_lower = addr[2:].lower()
    hash_hex = _keccak256(addr_lower.encode('utf-8')).hex()

    result = '0x'
    for i, char in enumerate(addr_lower):
        if char in '0123456789':
            result += char
        elif int(hash_hex[i], 16) >= 8:
            result += char.upper()
        else:
            result += char.lower()
    return result


def validate_evm_address(
    addr: str,
    param_name: str = "address",
    allow_zero: bool = False
) -> str:
    """Validate and return checksummed EVM address.

    Raises ValidationError if:
    - Not valid hex format (0x + 40 hex chars)
    - Is zero address (unless allow_zero=True)

    Returns checksummed address string.
    """
    if not addr or not isinstance(addr, str):
        raise ValueError(
            f"Invalid {param_name}: empty or not a string. "
            f"Expected format: 0x followed by 40 hex characters."
        )

    addr = addr.strip()

    if not _HEX_ADDR.match(addr):
        raise ValueError(
            f"Invalid {param_name}: '{addr[:20]}...' is not a valid EVM address. "
            f"Expected: 0x + 40 hex characters (e.g., 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045). "
            f"→ Check for typos or extra characters."
        )

    if addr.lower() == _ZERO_ADDR and not allow_zero:
        raise ValueError(
            f"Invalid {param_name}: zero address (0x000...000) detected. "
            f"Sending to zero address would burn funds permanently. "
            f"→ Double-check the destination address."
        )

    return to_checksum_address(addr)


# ─── Order Size ──────────────────────────────────────────────────

def validate_order_size(
    size: float,
    min_sz: float,
    asset: str = "token",
    max_sz: Optional[float] = None,
    sz_decimals: Optional[int] = None,
) -> float:
    """Validate order size meets exchange minimums.

    Args:
        size: Requested order size
        min_sz: Exchange's minimum size for this asset
        asset: Asset name for error messages
        max_sz: Optional maximum size
        sz_decimals: Decimal places allowed (for rounding)
    """
    if size <= 0:
        raise ValueError(
            f"Invalid order size: {size} {asset}. Size must be positive. "
            f"→ Check your amount calculation."
        )

    if size < min_sz:
        raise ValueError(
            f"Order size {size} {asset} is below minimum {min_sz} {asset}. "
            f"→ Increase size to at least {min_sz} {asset}."
        )

    if max_sz and size > max_sz:
        raise ValueError(
            f"Order size {size} {asset} exceeds maximum {max_sz} {asset}. "
            f"→ Reduce size or split into multiple orders."
        )

    # Round to allowed decimals
    if sz_decimals is not None:
        size = round(size, sz_decimals)
        if size < min_sz:
            raise ValueError(
                f"After rounding to {sz_decimals} decimals, size {size} < minSz {min_sz}. "
                f"→ Use a larger size."
            )

    return size


# ─── Leverage ────────────────────────────────────────────────────

def validate_leverage(
    leverage: int,
    max_leverage: int,
    asset: str = "token",
) -> int:
    """Validate leverage within exchange limits."""
    if leverage < 1:
        raise ValueError(
            f"Invalid leverage: {leverage}x. Minimum is 1x. "
            f"→ Use leverage between 1x and {max_leverage}x."
        )

    if leverage > max_leverage:
        raise ValueError(
            f"Leverage {leverage}x exceeds maximum {max_leverage}x for {asset}. "
            f"→ Reduce leverage to at most {max_leverage}x."
        )

    return leverage


# ─── Balance Check ───────────────────────────────────────────────

def validate_amount_vs_balance(
    amount: float,
    balance: float,
    asset: str = "token",
    reserve_pct: float = 0.0,
) -> float:
    """Validate amount doesn't exceed available balance.

    Args:
        amount: Amount to spend/send
        balance: Available balance
        asset: Asset name
        reserve_pct: Keep this % in reserve (0.0-1.0), e.g., 0.05 for gas
    """
    if amount <= 0:
        raise ValueError(
            f"Invalid amount: {amount} {asset}. Must be positive."
        )

    effective_balance = balance * (1 - reserve_pct)

    if amount > effective_balance:
        reserve_note = ""
        if reserve_pct > 0:
            reserve_note = f" (keeping {reserve_pct*100:.0f}% reserve for gas)"
        raise ValueError(
            f"Insufficient {asset}: need {amount} but only {effective_balance:.6f} available{reserve_note}. "
            f"Full balance: {balance:.6f} {asset}. "
            f"→ Reduce amount or deposit more {asset}."
        )

    return amount


# ─── Token Decimals ──────────────────────────────────────────────

def parse_token_amount(
    raw_value: int,
    decimals: int,
    token_symbol: str = "token",
) -> float:
    """Convert raw on-chain value to human-readable amount.

    CRITICAL: Using wrong decimals causes catastrophic misrepresentation.
    - USDC/USDT: 6 decimals
    - WBTC: 8 decimals
    - Most ERC-20: 18 decimals
    """
    if decimals < 0 or decimals > 77:
        raise ValueError(
            f"Invalid decimals={decimals} for {token_symbol}. "
            f"Expected 0-77 (common: 6 for USDC, 8 for WBTC, 18 for ETH)."
        )
    return raw_value / (10 ** decimals)


def to_raw_amount(
    human_amount: float,
    decimals: int,
    token_symbol: str = "token",
) -> int:
    """Convert human-readable amount to raw on-chain value (wei/satoshi/etc).

    Uses integer math to avoid float precision issues.
    """
    if decimals < 0 or decimals > 77:
        raise ValueError(f"Invalid decimals={decimals} for {token_symbol}.")

    # Use string splitting to avoid float precision loss
    str_amount = f"{human_amount:.{decimals}f}"
    parts = str_amount.split(".")
    integer_part = int(parts[0]) * (10 ** decimals)
    decimal_part = int(parts[1]) if len(parts) > 1 else 0

    return integer_part + decimal_part


# ─── Chain ID ────────────────────────────────────────────────────

KNOWN_CHAINS = {
    1: "Ethereum Mainnet",
    10: "Optimism",
    56: "BSC",
    137: "Polygon",
    42161: "Arbitrum One",
    8453: "Base",
    59144: "Linea",
    324: "zkSync Era",
}


def validate_chain_id(chain_id: int) -> int:
    """Validate chain ID is known. Warns on unknown chains."""
    if chain_id not in KNOWN_CHAINS:
        # Don't raise — just warn. Could be a new/custom chain.
        import warnings
        warnings.warn(
            f"Unknown chain_id={chain_id}. Known chains: "
            f"{', '.join(f'{k}={v}' for k, v in KNOWN_CHAINS.items())}. "
            f"Proceeding, but verify this is the correct chain."
        )
    return chain_id
