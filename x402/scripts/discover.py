#!/usr/bin/env python3
"""Discover and probe x402 payment rails for a given URL.

Usage:
  python3 scripts/discover.py --url <URL> [--max-usd <amount>]

Outputs JSON: {url, max_usd, funded_rails: [...], recommended_rail, all_rails: [{network, amount, ...}]}
Exit code: 0 on success, 1 if URL unreachable or no rails found.
"""
import sys
import json
import os
import argparse

# Add workspace to path so wallet skill imports work
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
WS = os.path.abspath(os.path.join(SKILL, "..", ".."))
sys.path.insert(0, SKILL)
sys.path.insert(0, WS)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Target service URL")
    parser.add_argument("--max-usd", type=float, default=None, help="Max payment in USD")
    args = parser.parse_args()
    
    result = {
        "url": args.url,
        "max_usd": args.max_usd,
        "funded_rails": [],
        "recommended_rail": None,
        "all_rails": [],
        "error": None
    }
    
    try:
        # Import here so missing deps fail gracefully
        from client import probe_402, usdc_balances, PrivySigner
        
        # Probe the URL for payment rails
        probed = probe_402(args.url)
        if not probed or probed.get("error"):
            result["error"] = probed.get("error", "No 402 payment challenge found")
            print(json.dumps(result))
            return 1
        
        # Extract accepts and normalize
        accepts = probed.get("accepts", [])
        if not accepts:
            result["error"] = "No payment rails returned"
            print(json.dumps(result))
            return 1
        
        # Get signer address for balance checks (best-effort)
        try:
            signer = PrivySigner.from_cached()
            evm_addr = getattr(signer, "address", None)
        except Exception:
            evm_addr = None
        
        # Probe balances
        networks = {str(a.get("network", "")) for a in accepts}
        balances = usdc_balances(networks, evm_addr=evm_addr)
        
        # Process each rail
        for accept in accepts:
            rail = {
                "network": accept.get("network"),
                "amount": accept.get("amount"),
                "max_amount_required": accept.get("max_amount_required"),
                "balance_atomic": balances.get(str(accept.get("network", ""))),
                "funded": False
            }
            try:
                amt = int(str(accept.get("amount", 0)))
                bal = balances.get(str(accept.get("network", "")))
                if bal is not None and bal >= amt:
                    rail["funded"] = True
                    result["funded_rails"].append(str(accept.get("network")))
            except (ValueError, TypeError):
                pass
            result["all_rails"].append(rail)
        
        # Recommend the first funded rail, or first rail if none funded
        if result["funded_rails"]:
            result["recommended_rail"] = result["funded_rails"][0]
        elif result["all_rails"]:
            result["recommended_rail"] = result["all_rails"][0].get("network")
        
        print(json.dumps(result, indent=2))
        return 0
    
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
        print(json.dumps(result))
        return 1

if __name__ == "__main__":
    sys.exit(main())
