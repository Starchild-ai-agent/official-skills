#!/usr/bin/env python3
"""Check wallet preflight status for x402 payments.

Usage:
  python3 scripts/preflight.py [--network <network>] [--amount-atomic <amount>]

Outputs JSON: {signable_networks, balances, funded_rails, warnings, blockers}
Exit code: 0 if all preflight checks pass, 1 if blockers exist.
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
    parser.add_argument("--network", default=None, help="Specific network to check")
    parser.add_argument("--amount-atomic", type=int, default=1000000, help="Amount in atomic units (default 1 USDC)")
    args = parser.parse_args()
    
    result = {
        "signable_networks": [],
        "balances": {},
        "funded_rails": [],
        "warnings": [],
        "blockers": [],
        "preflight_reqs": {}
    }
    
    try:
        from client import payment_preflight, PrivySigner, PAYABLE_USDC
        
        # Get signer
        try:
            signer = PrivySigner.from_cached()
        except Exception as e:
            result["blockers"].append(f"Privysigner load failed: {str(e)}")
            print(json.dumps(result))
            return 1
        
        if not getattr(signer, "address", None):
            result["blockers"].append("Signer has no address configured")
            print(json.dumps(result))
            return 1
        
        # Determine networks to check
        networks_to_check = None
        if args.network:
            networks_to_check = [args.network]
        else:
            networks_to_check = list(PAYABLE_USDC.keys())
        
        # Run preflight
        preflight = payment_preflight(args.amount_atomic, networks=networks_to_check)
        
        # Extract results
        result["signable_networks"] = preflight.get("signable_networks", [])
        result["balances"] = preflight.get("balances", {})
        result["funded_rails"] = preflight.get("funded_rails", [])
        result["warnings"].extend(preflight.get("warnings", []))
        result["preflight_reqs"] = preflight.get("preflight_reqs", {})
        
        # Check blockers
        if preflight.get("blockers"):
            result["blockers"].extend(preflight["blockers"])
        
        if not result["signable_networks"]:
            result["blockers"].append("No signable networks found")
        
        if not result["funded_rails"] and result["signable_networks"]:
            result["warnings"].append(f"No funded rails for {args.amount_atomic} atomic units")
        
        print(json.dumps(result, indent=2))
        return 0 if not result["blockers"] else 1
    
    except Exception as e:
        result["blockers"].append(f"{type(e).__name__}: {str(e)}")
        print(json.dumps(result))
        return 1

if __name__ == "__main__":
    sys.exit(main())
