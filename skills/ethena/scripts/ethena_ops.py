"""
Ethena USDe/sUSDe operations — generates calldata for Privy wallet transactions.
Usage: python scripts/ethena_ops.py <action> [args]
Actions:
  approve <amount_usde>         — Generate approve calldata for USDe → sUSDe
  deposit <amount_usde> <receiver> — Generate deposit calldata (ERC4626)
  cooldown <amount>             — Generate cooldownAssets calldata
  unstake <receiver>            — Generate unstake calldata
  rate                          — Fetch current sUSDe/USDe exchange rate
"""
import sys
import json
import re
from decimal import Decimal

# Contract addresses
USDE = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"
SUSDE = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
USDE_SILO = "0x7FC7c91D556B400AFa565013E3F32055a0713425"

# USDe has 18 decimals
DECIMALS = 18


def to_wei(amount_str: str) -> int:
    """Convert human-readable amount to wei (18 decimals).
    Uses Decimal to avoid float precision loss on large values."""
    return int(Decimal(amount_str) * Decimal(10 ** DECIMALS))


def validate_address(addr: str) -> str:
    """Validate EVM address format. Returns address or raises."""
    if not re.match(r'^0x[0-9a-fA-F]{40}$', addr):
        print(f"Error: invalid EVM address: {addr}", file=sys.stderr)
        sys.exit(1)
    return addr


def encode_uint256(val: int) -> str:
    return hex(val)[2:].zfill(64)


def encode_address(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


def approve_calldata(amount_wei: int) -> dict:
    """ERC20 approve(spender, amount) — approve sUSDe to spend USDe."""
    # approve(address,uint256) = 0x095ea7b3
    selector = "095ea7b3"
    data = "0x" + selector + encode_address(SUSDE) + encode_uint256(amount_wei)
    return {
        "to": USDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Approve sUSDe contract to spend {amount_wei} USDe wei"
    }


def deposit_calldata(amount_wei: int, receiver: str) -> dict:
    """ERC4626 deposit(uint256 assets, address receiver)."""
    # deposit(uint256,address) = 0x6e553f65
    selector = "6e553f65"
    data = "0x" + selector + encode_uint256(amount_wei) + encode_address(receiver)
    return {
        "to": SUSDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Deposit {amount_wei} USDe wei into sUSDe vault for {receiver}"
    }


def cooldown_calldata(amount_wei: int) -> dict:
    """cooldownAssets(uint256 assets) — start 7-day cooldown."""
    # keccak256("cooldownAssets(uint256)")[:4] = 0xcdac52ed
    selector = "cdac52ed"
    data = "0x" + selector + encode_uint256(amount_wei)
    return {
        "to": SUSDE,
        "amount": "0",
        "chain_id": 1,
        "data": data,
        "description": f"Start 7-day cooldown for {amount_wei} USDe wei worth of sUSDe"
    }


def unstake_calldata(receiver: str) -> dict:
    """unstake(address receiver) — claim USDe after cooldown."""
    # keccak256("unstake(address)")[:4] = 0xf2888dbb
    selector = "f2888dbb"
    data = "0x" + selector + encode_address(receiver)
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

    if action == "approve":
        amount = sys.argv[2] if len(sys.argv) > 2 else "1000"
        wei = to_wei(amount)
        result = approve_calldata(wei)
        print(json.dumps(result, indent=2))

    elif action == "deposit":
        if len(sys.argv) < 4:
            print("Usage: deposit <amount_usde> <receiver_address>",
                  file=sys.stderr)
            sys.exit(1)
        amount = sys.argv[2]
        receiver = validate_address(sys.argv[3])
        wei = to_wei(amount)
        result = deposit_calldata(wei, receiver)
        print(json.dumps(result, indent=2))

    elif action == "cooldown":
        amount = sys.argv[2] if len(sys.argv) > 2 else "1000"
        wei = to_wei(amount)
        result = cooldown_calldata(wei)
        print(json.dumps(result, indent=2))

    elif action == "unstake":
        if len(sys.argv) < 3:
            print("Usage: unstake <receiver_address>",
                  file=sys.stderr)
            sys.exit(1)
        receiver = validate_address(sys.argv[2])
        result = unstake_calldata(receiver)
        print(json.dumps(result, indent=2))

    elif action == "rate":
        print("To check sUSDe rate, query the sUSDe contract:")
        print(f"  totalAssets() and totalSupply() on {SUSDE}")
        print("  rate = totalAssets / totalSupply")
        print(
            f"  Use: web_fetch('https://api.etherscan.io/api?module=proxy&action=eth_call&to={SUSDE}&data=0x01e1d114')")

    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
