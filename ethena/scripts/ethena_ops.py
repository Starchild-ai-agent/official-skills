"""
Ethena USDe/sUSDe operations — generates calldata for on-chain transactions.
Usage: python scripts/ethena_ops.py <action> [args]
Actions:
  approve <amount_usde>            — Generate approve calldata for USDe → sUSDe
  deposit <amount_usde> <receiver> — Generate deposit calldata (ERC4626)
  cooldown <amount>                — Generate cooldownAssets calldata
  unstake <receiver>               — Generate unstake calldata
"""
import sys
import json
import re
from decimal import Decimal, InvalidOperation

# Contract addresses (Ethereum Mainnet)
USDE  = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"
SUSDE = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
USDE_SILO = "0x7FC7c91D556B400AFa565013E3F32055a0713425"

DECIMALS = 18
_ADDR_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')


def to_wei(amount_str: str) -> int:
    """Convert human-readable amount to wei (18 decimals)."""
    try:
        d = Decimal(amount_str)
    except InvalidOperation:
        raise ValueError(f"Invalid amount: {amount_str!r}")
    if d < 0:
        raise ValueError(f"Amount must be non-negative, got {amount_str}")
    return int(d * Decimal(10 ** DECIMALS))


def validate_address(addr: str) -> str:
    if not _ADDR_RE.match(addr):
        raise ValueError(f"Invalid EVM address: {addr!r}")
    return addr


def encode_uint256(val: int) -> str:
    return hex(val)[2:].zfill(64)


def encode_address(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


def approve_calldata(amount_wei: int) -> dict:
    """ERC20 approve(spender, amount) — approve sUSDe to spend USDe."""
    # approve(address,uint256) = 0x095ea7b3
    data = "0x095ea7b3" + encode_address(SUSDE) + encode_uint256(amount_wei)
    return {
        "to": USDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Approve sUSDe contract to spend {amount_wei} USDe wei"
    }


def deposit_calldata(amount_wei: int, receiver: str) -> dict:
    """ERC4626 deposit(uint256 assets, address receiver)."""
    validate_address(receiver)
    # deposit(uint256,address) = 0x6e553f65
    data = "0x6e553f65" + encode_uint256(amount_wei) + encode_address(receiver)
    return {
        "to": SUSDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Deposit {amount_wei} USDe wei into sUSDe vault for {receiver}"
    }


def cooldown_calldata(amount_wei: int) -> dict:
    """cooldownAssets(uint256 assets) — start cooldown period."""
    # keccak256("cooldownAssets(uint256)")[:4] = 0xcdac52ed
    data = "0xcdac52ed" + encode_uint256(amount_wei)
    return {
        "to": SUSDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Start cooldown for {amount_wei} USDe wei worth of sUSDe"
    }


def unstake_calldata(receiver: str) -> dict:
    """unstake(address receiver) — claim USDe after cooldown."""
    validate_address(receiver)
    # keccak256("unstake(address)")[:4] = 0xf2888dbb
    data = "0xf2888dbb" + encode_address(receiver)
    return {
        "to": SUSDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Claim unstaked USDe to {receiver} (requires cooldown complete)"
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    try:
        if action == "approve":
            amount = sys.argv[2] if len(sys.argv) > 2 else "1000"
            print(json.dumps(approve_calldata(to_wei(amount)), indent=2))

        elif action == "deposit":
            if len(sys.argv) < 4:
                print("Usage: deposit <amount_usde> <receiver_address>", file=sys.stderr)
                sys.exit(1)
            print(json.dumps(deposit_calldata(to_wei(sys.argv[2]), sys.argv[3]), indent=2))

        elif action == "cooldown":
            amount = sys.argv[2] if len(sys.argv) > 2 else "1000"
            print(json.dumps(cooldown_calldata(to_wei(amount)), indent=2))

        elif action == "unstake":
            if len(sys.argv) < 3:
                print("Usage: unstake <receiver_address>", file=sys.stderr)
                sys.exit(1)
            print(json.dumps(unstake_calldata(sys.argv[2]), indent=2))

        else:
            print(f"Unknown action: {action}")
            sys.exit(1)

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
