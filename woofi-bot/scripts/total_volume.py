#!/usr/bin/env python3
"""
Get total WOOFi trading volume across all chains for a given period.
Usage: python total_volume.py --period 1m
"""

import requests
import argparse

CHAINS = [
    "bsc", "avax", "polygon", "arbitrum", "optimism", 
    "linea", "base", "mantle", "sonic", "berachain", 
    "hyperevm", "monad", "solana"
]

def get_total_volume(period: str) -> float:
    """Fetch total volume across all chains for the given period."""
    total = 0.0
    
    for chain in CHAINS:
        try:
            url = f"https://api.woofi.com/stat?period={period}&network={chain}"
            r = requests.get(url, timeout=10)
            data = r.json()
            
            if data.get("status") == "ok" and "data" in data:
                for bucket in data["data"]:
                    volume_wei = int(bucket.get("volume_usd", 0))
                    total += volume_wei / 1e18
        except Exception as e:
            print(f"Error fetching {chain}: {e}")
            continue
    
    return total

def main():
    parser = argparse.ArgumentParser(description="Get total WOOFi volume across all chains")
    parser.add_argument("--period", type=str, default="1d", 
                       choices=["1d", "1w", "1m", "3m", "1y", "all"],
                       help="Time period (default: 1d)")
    args = parser.parse_args()
    
    total = get_total_volume(args.period)
    print(f"Total WOOFi volume ({args.period}): ${total:,.0f}")

if __name__ == "__main__":
    main()
