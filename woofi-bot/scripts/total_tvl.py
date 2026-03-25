#!/usr/bin/env python3
"""
Get total WOOFi Earn TVL across all chains.
Usage: python total_tvl.py
"""

import requests

CHAINS = [
    "bsc", "avax", "polygon", "arbitrum", "optimism", 
    "linea", "base", "mantle", "sonic", "berachain", 
    "hyperevm", "monad"
]

def get_total_tvl() -> float:
    """Fetch total TVL across all WOOFi Earn vaults."""
    total = 0.0
    
    for chain in CHAINS:
        try:
            url = f"https://api.woofi.com/yield?network={chain}"
            r = requests.get(url, timeout=10)
            data = r.json()
            
            if data.get("status") == "ok" and "data" in data:
                tvl_data = data["data"]
                if "total_deposit" in tvl_data:
                    tvl_wei = int(tvl_data["total_deposit"])
                    total += tvl_wei / 1e18
        except Exception as e:
            print(f"Error fetching {chain}: {e}")
            continue
    
    return total

def main():
    total = get_total_tvl()
    print(f"Total WOOFi Earn TVL: ${total:,.0f}")

if __name__ == "__main__":
    main()
