#!/usr/bin/env python3
"""Execute a single x402 payment end-to-end.

Usage:
  python3 scripts/buy.py --url <URL> --amount-atomic <amount> [--network <network>]

Outputs JSON: {success, tx_hash, amount_usdc, network, tx_url, error}
Exit code: 0 on success, 1 on failure.
"""
import sys
import json
import os
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
WS = os.path.abspath(os.path.join(SKILL, "..", ".."))
sys.path.insert(0, SKILL)
sys.path.insert(0, WS)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Target service URL")
    parser.add_argument("--amount-atomic", type=int, required=True, help="Amount in atomic units")
    parser.add_argument("--network", default=None, help="Preferred network (optional; auto-selects funded rail if omitted)")
    args = parser.parse_args()
    
    result = {
        "success": False,
        "url": args.url,
        "amount_atomic": args.amount_atomic,
        "amount_usdc": args.amount_atomic / 1e6,
        "network": args.network,
        "tx_hash": None,
        "tx_url": None,
        "error": None
    }
    
    try:
        from client import paid_request
        
        # Execute payment
        # paid_request will:
        //  1. probe the URL for 402 challenge
        #  2. select best rail (prefer_network if given, else funded-first)
        #  3. build & sign transaction
        #  4. broadcast & poll for settlement receipt
        response = paid_request(
            method="GET",
            url=args.url,
            prefer_network=args.network
        )
        
        # Check for payment success
        if response.status_code == 200:
            result["success"] = True
            result["tx_hash"] = response.headers.get("X-TX-Hash")
            # Construct block explorer URL if network known
            if args.network:
                if args.network.startswith("eip155:"):
                    chainid = int(args.network.split(":")[1])
                    explorers = {1: "etherscan.io", 8453: "basescan.org", 56: "bscscan.com"}
                    if chainid in explorers:
                        result["tx_url"] = f"https://{explorers[chainid]}/tx/{result['tx_hash']}"
            result["error"] = None
        else:
            # Payment failed or was rejected
            err_msg = response.text if hasattr(response, "text") else str(response)
            if response.status_code == 402:
                result["error"] = f"Payment required but failed (HTTP 402): {err_msg[:200]}"
            else:
                result["error"] = f"HTTP {response.status_code}: {err_msg[:200]}"
        
        print(json.dumps(result, indent=2))
        return 0 if result["success"] else 1
    
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(json.dumps(result))
        return 1

if __name__ == "__main__":
    sys.exit(main())
