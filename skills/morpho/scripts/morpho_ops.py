"""
Morpho protocol operations — GraphQL queries and calldata generation.
Usage: python scripts/morpho_ops.py <action> [args]
Actions:
  vaults [chain_id]                — List top vaults by TVL
  markets [chain_id]               — List top markets
  position <user_address> [chain]  — Get user vault positions
  approve <asset> <spender> <amt>  — Generate ERC20 approve calldata
  deposit <vault> <amount> <recv> [chain_id]  — Generate ERC4626 deposit calldata
  withdraw <vault> <amount> <recv> [chain_id] — Generate ERC4626 withdraw calldata
"""
import sys
import json
import re
import requests

GRAPHQL_URL = "https://api.morpho.org/graphql"
_ADDR_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')


def validate_address(addr: str) -> str:
    """Validate EVM address format."""
    if not _ADDR_RE.match(addr):
        raise ValueError(f"Invalid EVM address: {addr!r}")
    return addr


def gql_query(query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        resp = requests.post(GRAPHQL_URL, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Morpho API error: {e}") from e


def list_vaults(chain_id: int = 1, limit: int = 10):
    query = """
    query($chainIds: [Int!], $first: Int) {
      vaults(first: $first, orderBy: TotalAssetsUsd, orderDirection: Desc, where: { chainId_in: $chainIds }) {
        items {
          address
          name
          symbol
          asset { symbol decimals address }
          state {
            totalAssetsUsd
            apy
            netApy
            fee
          }
          metadata { curators { name } }
        }
      }
    }
    """
    result = gql_query(query, {"chainIds": [chain_id], "first": limit})
    vaults = result.get("data", {}).get("vaults", {}).get("items", [])
    for v in vaults:
        state = v.get("state") or {}
        asset = v.get("asset") or {}
        meta = v.get("metadata") or {}
        curators = meta.get("curators") or []
        curator_name = curators[0]["name"] if curators else "Unknown"
        tvl = float(state.get("totalAssetsUsd") or 0)
        apy = float(state.get("netApy") or 0) * 100
        print(f"  {v['name']} ({v['symbol']})")
        print(f"    Address: {v['address']}")
        print(f"    Asset: {asset.get('symbol', '?')}")
        print(f"    TVL: ${tvl:,.0f} | Net APY: {apy:.2f}%")
        print(f"    Curator: {curator_name}")
        print()
    return vaults


def list_markets(chain_id: int = 1, limit: int = 10):
    query = """
    query($chainIds: [Int!], $first: Int) {
      markets(first: $first, orderBy: SupplyAssetsUsd, orderDirection: Desc, where: { chainId_in: $chainIds }) {
        items {
          uniqueKey
          loanAsset { symbol address }
          collateralAsset { symbol address }
          state {
            supplyAssetsUsd
            borrowAssetsUsd
            utilization
            supplyApy
            borrowApy
          }
          lltv
        }
      }
    }
    """
    result = gql_query(query, {"chainIds": [chain_id], "first": limit})
    markets = result.get("data", {}).get("markets", {}).get("items", [])
    for m in markets:
        state = m.get("state") or {}
        loan = m.get("loanAsset") or {}
        collateral = m.get("collateralAsset") or {}
        supply_usd = float(state.get("supplyAssetsUsd") or 0)
        borrow_usd = float(state.get("borrowAssetsUsd") or 0)
        util = float(state.get("utilization") or 0) * 100
        supply_apy = float(state.get("supplyApy") or 0) * 100
        borrow_apy = float(state.get("borrowApy") or 0) * 100
        lltv = float(m.get("lltv") or 0) / 1e18 * 100
        print(f"  {collateral.get('symbol', '?')}/{loan.get('symbol', '?')}")
        print(f"    Market: {m['uniqueKey'][:16]}...")
        print(f"    Supply: ${supply_usd:,.0f} ({supply_apy:.2f}% APY)")
        print(f"    Borrow: ${borrow_usd:,.0f} ({borrow_apy:.2f}% APY)")
        print(f"    Utilization: {util:.1f}% | LLTV: {lltv:.0f}%")
        print()
    return markets


def get_positions(user_address: str, chain_id: int = 1):
    query = """
    query($userAddresses: [String!], $chainIds: [Int!]) {
      vaultPositions(where: { userAddress_in: $userAddresses, chainId_in: $chainIds }) {
        items {
          vault { address name asset { symbol } state { netApy } }
          state { assets assetsUsd }
        }
      }
    }
    """
    result = gql_query(query, {
        "userAddresses": [user_address.lower()],
        "chainIds": [chain_id],
    })
    positions = result.get("data", {}).get("vaultPositions", {}).get("items", [])
    if not positions:
        print(f"  No vault positions found for {user_address} on chain {chain_id}")
        return positions
    for p in positions:
        vault = p.get("vault") or {}
        asset = vault.get("asset") or {}
        vault_state = vault.get("state") or {}
        apy = float(vault_state.get("netApy") or 0) * 100
        pos_state = p.get("state") or {}
        usd = float(pos_state.get("assetsUsd") or 0)
        print(f"  {vault.get('name', '?')}")
        print(f"    Deposited: ${usd:,.2f} {asset.get('symbol', '')}")
        print(f"    APY: {apy:.2f}%")
        print()
    return positions

# --- Calldata generation ---


def encode_uint256(val: int) -> str:
    return hex(val)[2:].zfill(64)


def encode_address(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


def approve_calldata(asset: str, spender: str, amount_wei: int,
                     chain_id: int = 1) -> dict:
    validate_address(asset)
    validate_address(spender)
    if amount_wei < 0:
        raise ValueError(f"Amount must be non-negative, got {amount_wei}")
    selector = "095ea7b3"
    data = "0x" + selector + encode_address(spender) + encode_uint256(amount_wei)
    return {"to": asset, "amount": "0", "chain_id": chain_id, "data": data}


def deposit_calldata(vault: str, amount_wei: int, receiver: str,
                     chain_id: int = 1) -> dict:
    validate_address(vault)
    validate_address(receiver)
    if amount_wei <= 0:
        raise ValueError(f"Deposit amount must be positive, got {amount_wei}")
    # ERC4626 deposit(uint256,address) = 0x6e553f65
    selector = "6e553f65"
    data = "0x" + selector + encode_uint256(amount_wei) + encode_address(receiver)
    return {"to": vault, "amount": "0", "chain_id": chain_id, "data": data}


def withdraw_calldata(vault: str, amount_wei: int, receiver: str,
                      chain_id: int = 1) -> dict:
    validate_address(vault)
    validate_address(receiver)
    if amount_wei <= 0:
        raise ValueError(f"Withdraw amount must be positive, got {amount_wei}")
    # ERC4626 withdraw(uint256,address,address) = 0xb460af94
    selector = "b460af94"
    data = ("0x" + selector + encode_uint256(amount_wei)
            + encode_address(receiver) + encode_address(receiver))
    return {"to": vault, "amount": "0", "chain_id": chain_id, "data": data}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    try:
        if action == "vaults":
            chain = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"Top Morpho Vaults (chain {chain}):")
            list_vaults(chain)
        elif action == "markets":
            chain = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"Top Morpho Markets (chain {chain}):")
            list_markets(chain)
        elif action == "position":
            if len(sys.argv) < 3:
                print("Usage: position <user_address> [chain_id]")
                sys.exit(1)
            addr = sys.argv[2]
            chain = int(sys.argv[3]) if len(sys.argv) > 3 else 1
            print(f"Positions for {addr} (chain {chain}):")
            get_positions(addr, chain)
        elif action == "approve":
            if len(sys.argv) < 5:
                print("Usage: approve <asset_addr> <spender_addr> <amount_wei> [chain_id]")
                sys.exit(1)
            chain = int(sys.argv[5]) if len(sys.argv) > 5 else 1
            result = approve_calldata(sys.argv[2], sys.argv[3],
                                      int(sys.argv[4]), chain)
            print(json.dumps(result, indent=2))
        elif action == "deposit":
            if len(sys.argv) < 5:
                print("Usage: deposit <vault_addr> <amount_wei> <receiver_addr> [chain_id]")
                sys.exit(1)
            chain = int(sys.argv[5]) if len(sys.argv) > 5 else 1
            result = deposit_calldata(sys.argv[2], int(sys.argv[3]),
                                      sys.argv[4], chain)
            print(json.dumps(result, indent=2))
        elif action == "withdraw":
            if len(sys.argv) < 5:
                print("Usage: withdraw <vault_addr> <amount_wei> <receiver_addr> [chain_id]")
                sys.exit(1)
            chain = int(sys.argv[5]) if len(sys.argv) > 5 else 1
            result = withdraw_calldata(sys.argv[2], int(sys.argv[3]),
                                       sys.argv[4], chain)
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown action: {action}")
            print(__doc__)
            sys.exit(1)

    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
