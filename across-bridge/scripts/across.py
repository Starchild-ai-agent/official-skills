#!/usr/bin/env python3
"""
Across Protocol Bridge — official skill core module.

Two high-level functions cover the entire cross-chain flow:

  bridge_quote(...)   → live quote (output amount, fees, fill time, route)
  bridge_execute(...) → end-to-end: approval (if needed) + deposit + verify arrival

Both are thin wrappers around the Across `/swap` API, which returns ready-to-sign
transaction data (approval + bridge calldata) in one call. No manual ABI encoding,
no multi-step orchestration by the caller.

Run from bash:
    python3 -c "from core.skill_tools.across import bridge_quote; ..."
    python3 -c "from core.skill_tools.across import bridge_execute; ..."

Or import in a script:
    from core.skill_tools.across import bridge_quote, bridge_execute
"""

import json
import time
import requests

# ─── Chain registry ───────────────────────────────────────────────────────────

CHAIN_IDS = {
    "ethereum": 1, "mainnet": 1, "eth": 1,
    "arbitrum": 42161, "arb": 42161,
    "optimism": 10, "op": 10,
    "base": 8453,
    "polygon": 137, "matic": 137,
    "bsc": 56, "binance": 56,
    "linea": 59144,
    "zksync": 324, "era": 324,
    "scroll": 534352,
    "mantle": 5000,
}

CHAIN_NAMES = {
    1: "ethereum",
    42161: "arbitrum",
    10: "optimism",
    8453: "base",
    137: "polygon",
    56: "bsc",
    59144: "linea",
    324: "zksync",
    534352: "scroll",
    5000: "mantle",
}

# ─── Token registry (symbol → {chain_id: address}) ────────────────────────────
# Native ETH uses the zero address as inputToken/outputToken; the Across /swap
# API handles native ETH wrapping/unwrapping automatically.

TOKENS = {
    "ETH": {
        1:     "0x0000000000000000000000000000000000000000",
        42161: "0x0000000000000000000000000000000000000000",
        10:    "0x0000000000000000000000000000000000000000",
        8453:  "0x0000000000000000000000000000000000000000",
        137:   "0x0000000000000000000000000000000000000000",
        56:    "0x0000000000000000000000000000000000000000",
        59144: "0x0000000000000000000000000000000000000000",
        324:   "0x0000000000000000000000000000000000000000",
        534352:"0x0000000000000000000000000000000000000000",
        5000:  "0x0000000000000000000000000000000000000000",
    },
    "WETH": {
        1:     "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        10:    "0x4200000000000000000000000000000000000006",
        8453:  "0x4200000000000000000000000000000000000006",
        137:   "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        56:    "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
        59144: "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",
        324:   "0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91",
    },
    "USDC": {
        1:     "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        10:    "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        8453:  "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        137:   "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        56:    "0x8ac76A51cc950d9822D68b83fE1Ad97B32Cd580d",
        59144: "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",
    },
    "USDT": {
        1:     "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        42161: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        10:    "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        137:   "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        56:    "0x55d398326f99059fF775485246999027B3197955",
    },
    "WBTC": {
        1:     "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        42161: "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
        10:    "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
    },
    "DAI": {
        1:     "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        42161: "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        10:    "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        8453:  "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        137:   "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    },
}

DECIMALS = {"ETH": 18, "WETH": 18, "USDC": 6, "USDT": 6, "WBTC": 8, "DAI": 18}

ACROSS_SWAP_API = "https://app.across.to/api/swap"
ACROSS_STATUS_API = "https://app.across.to/api/deposit/status"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_chain(chain):
    """Accept name (str) or id (int/str); return int chain id."""
    if isinstance(chain, int):
        return chain
    s = str(chain).strip().lower()
    if s.isdigit():
        return int(s)
    if s not in CHAIN_IDS:
        raise ValueError(f"Unknown chain '{chain}'. Supported: {sorted(set(CHAIN_IDS))}")
    return CHAIN_IDS[s]


def _resolve_token(symbol, chain_id):
    """Return token address for a symbol on a chain."""
    sym = symbol.upper()
    if sym not in TOKENS:
        raise ValueError(f"Unsupported token '{symbol}'. Supported: {list(TOKENS)}")
    if chain_id not in TOKENS[sym]:
        raise ValueError(f"{sym} not available on chain {chain_id} ({CHAIN_NAMES.get(chain_id, '?')}). "
                         f"Available chains: {list(TOKENS[sym])}")
    return TOKENS[sym][chain_id]


def _to_wei(amount, symbol):
    """Convert human-readable amount to smallest-unit integer."""
    dec = DECIMALS[symbol.upper()]
    if isinstance(amount, str) and amount.isdigit():
        return int(amount)
    return int(round(float(amount) * 10 ** dec))


def _from_wei(amount, symbol):
    """Convert smallest-unit to human-readable float."""
    dec = DECIMALS[symbol.upper()]
    return int(amount) / 10 ** dec


def _fetch_swap(input_token, output_token, amount_wei, origin_id, dest_id, wallet):
    """Call Across /swap and return parsed JSON."""
    params = {
        "inputToken": input_token,
        "outputToken": output_token,
        "amount": str(amount_wei),
        "originChainId": origin_id,
        "destinationChainId": dest_id,
        "depositor": wallet,
        "recipient": wallet,
    }
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    r = requests.get(ACROSS_SWAP_API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


# ─── Public API ───────────────────────────────────────────────────────────────

def bridge_quote(from_chain, to_chain, token, amount, wallet=None):
    """
    Get a live Across bridge quote (no on-chain action).

    Args:
        from_chain: origin chain name ("base") or id (8453)
        to_chain:   destination chain name or id
        token:      token symbol ("USDC", "ETH", "USDT", "WETH", "WBTC", "DAI")
        amount:     human-readable amount (float/str) OR wei integer string
        wallet:     depositor/recipient address (optional for quote-only)

    Returns:
        {
          "route": {"from_chain", "to_chain", "token", "amount", "amount_wei"},
          "output_amount": "995312",           # smallest unit string
          "output_amount_human": 0.995312,
          "fees": {"total_wei", "total_pct", "currency"},
          "estimated_fill_time_sec": 2,
          "spoke_pool": "0x...",
          "needs_approval": true,
          "approval_txns": [...],             # ready-to-send if wallet given
          "bridge_tx": {...},                 # ready-to-send if wallet given
          "limits": {"min_deposit", "max_deposit", ...},
          "raw": {...}                        # full API response
        }
    """
    origin_id = _resolve_chain(from_chain)
    dest_id = _resolve_chain(to_chain)
    sym = token.upper()
    amount_wei = _to_wei(amount, sym)

    input_token = _resolve_token(sym, origin_id)
    output_token = _resolve_token(sym, dest_id)

    if wallet is None:
        wallet = "0x0000000000000000000000000000000000000000"

    data = _fetch_swap(input_token, output_token, amount_wei, origin_id, dest_id, wallet)

    # Parse output amount — /swap nests it under steps.bridge.outputAmount
    output_wei = None
    if "steps" in data and "bridge" in data["steps"]:
        output_wei = data["steps"]["bridge"].get("outputAmount")
    if output_wei is None:
        output_wei = data.get("outputAmount")

    # Fees
    fees_total = None
    fees_pct = None
    if "fees" in data and "total" in data["fees"]:
        ft = data["fees"]["total"]
        fees_total = ft.get("amount")
        fees_pct = ft.get("pct")

    # Fill time
    fill_time = data.get("expectedFillTime")
    if fill_time is None and "steps" in data and "bridge" in data["steps"]:
        fill_time = data["steps"]["bridge"].get("estimatedFillTimeSec")

    # Spoke pool
    spoke = data.get("spokePoolAddress")
    if spoke is None and "steps" in data and "bridge" in data["steps"]:
        spoke = data["steps"]["bridge"].get("spokePoolAddress")

    # Approval + bridge tx
    approval_txns = data.get("approvalTxns", [])
    swap_tx = data.get("swapTx")
    needs_approval = bool(approval_txns)

    # Limits (from suggested-fees; /swap may not include them)
    limits = data.get("limits")

    return {
        "route": {
            "from_chain": CHAIN_NAMES.get(origin_id, origin_id),
            "from_chain_id": origin_id,
            "to_chain": CHAIN_NAMES.get(dest_id, dest_id),
            "to_chain_id": dest_id,
            "token": sym,
            "amount": str(amount),
            "amount_wei": str(amount_wei),
        },
        "output_amount": str(output_wei) if output_wei else None,
        "output_amount_human": _from_wei(int(output_wei), sym) if output_wei else None,
        "fees": {
            "total_wei": str(fees_total) if fees_total else None,
            "total_pct": str(fees_pct) if fees_pct else None,
            "currency": sym,
        },
        "estimated_fill_time_sec": fill_time,
        "spoke_pool": spoke,
        "needs_approval": needs_approval,
        "approval_txns": approval_txns,
        "bridge_tx": swap_tx,
        "limits": limits,
        "raw": data,
    }


def bridge_execute(from_chain, to_chain, token, amount, wallet,
                   confirm_arrival=True, arrival_timeout=180):
    """
    End-to-end bridge: fetch fresh quote → approval (if needed) → deposit → verify.

    Uses the Starchild wallet skill (core.skill_tools.wallet) for signing/broadcast.
    Gas is sponsored by default. Returns a full receipt.

    Args:
        from_chain, to_chain, token, amount: same as bridge_quote
        wallet:     depositor/recipient address (required)
        confirm_arrival: if True, poll destination balance until funds arrive
        arrival_timeout: max seconds to wait for arrival confirmation

    Returns:
        {
          "status": "success" | "failed",
          "route": {...},
          "output_amount": "995312",
          "output_amount_human": 0.995312,
          "approval_tx": {...} | None,
          "bridge_tx": {...},
          "arrival_confirmed": true,
          "elapsed_sec": 12.4
        }
    """
    # Lazy import: core.skill_tools.wallet is only available at runtime in
    # the platform environment, not at module load time.
    try:
        from core.skill_tools import wallet as w
    except Exception:
        import importlib
        w = importlib.import_module("core.skill_tools").wallet

    origin_id = _resolve_chain(from_chain)
    dest_id = _resolve_chain(to_chain)
    sym = token.upper()
    amount_wei = _to_wei(amount, sym)

    t0 = time.time()

    # 1. Fresh quote (quote valid ~30s; re-fetch right before sending)
    q = bridge_quote(from_chain, to_chain, token, amount, wallet)
    if q["bridge_tx"] is None:
        raise RuntimeError(f"Across /swap returned no bridge tx. Raw: {q['raw']}")

    # 2. Approval (if ERC-20 and not yet approved)
    approval_result = None
    if q["needs_approval"]:
        for atx in q["approval_txns"]:
            approval_result = w.wallet_transfer(
                to=atx["to"],
                amount="0",
                chain_id=int(atx["chainId"]),
                data=atx["data"],
            )
        # wait for approval to settle
        time.sleep(6)
        # re-fetch quote so swapTx reflects updated allowance
        q = bridge_quote(from_chain, to_chain, token, amount, wallet)
        if q["bridge_tx"] is None:
            raise RuntimeError("Re-quoted after approval but still no bridge tx.")

    # 3. Bridge deposit
    swap = q["bridge_tx"]
    bridge_result = w.wallet_transfer(
        to=swap["to"],
        amount=swap.get("value", "0"),
        chain_id=int(swap["chainId"]),
        data=swap["data"],
    )

    # 4. Verify arrival on destination
    arrival_confirmed = False
    if confirm_arrival:
        dest_name = CHAIN_NAMES.get(dest_id, dest_id)
        # snapshot pre-balance
        try:
            pre = w.wallet_balance(chain=dest_name)
            pre_amt = _find_token_balance(pre, sym, dest_id)
        except Exception:
            pre_amt = None

        deadline = time.time() + arrival_timeout
        while time.time() < deadline:
            time.sleep(10)
            try:
                post = w.wallet_balance(chain=dest_name)
                post_amt = _find_token_balance(post, sym, dest_id)
            except Exception:
                continue
            if post_amt is not None and pre_amt is not None:
                if post_amt > pre_amt:
                    arrival_confirmed = True
                    break
            elif post_amt is not None and post_amt > 0:
                arrival_confirmed = True
                break

    return {
        "status": "success" if arrival_confirmed or not confirm_arrival else "submitted_unconfirmed",
        "route": q["route"],
        "output_amount": q["output_amount"],
        "output_amount_human": q["output_amount_human"],
        "approval_tx": approval_result,
        "bridge_tx": bridge_result,
        "arrival_confirmed": arrival_confirmed,
        "elapsed_sec": round(time.time() - t0, 1),
    }


def _find_token_balance(balance_resp, symbol, chain_id):
    """Extract a token's raw_amount from a wallet_balance() response."""
    sym = symbol.upper()
    # For native ETH, DeBank returns id == chain name or "eth"
    for t in balance_resp.get("tokens", []):
        if t.get("symbol", "").upper() == sym:
            return int(t.get("raw_amount", 0))
    return None


def bridge_status(origin_chain, deposit_tx_hash):
    """
    Check fill status of a submitted deposit via Across status API.

    Args:
        origin_chain: origin chain name or id
        deposit_tx_hash: the deposit transaction hash on origin chain

    Returns:
        dict from Across /deposit/status (status: filled / pending / etc.)
    """
    origin_id = _resolve_chain(origin_chain)
    params = {"originChainId": origin_id, "depositTxHash": deposit_tx_hash}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    r = requests.get(ACROSS_STATUS_API, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


# ─── CLI (for quick testing / debugging) ──────────────────────────────────────

def _cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 across.py quote   <from> <to> <token> <amount> [wallet]")
        print("  python3 across.py execute <from> <to> <token> <amount> <wallet>")
        print("  python3 across.py status  <from_chain> <deposit_tx_hash>")
        print()
        print("Chains: " + ", ".join(sorted(set(CHAIN_IDS))))
        print("Tokens: " + ", ".join(TOKENS))
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "quote":
        q = bridge_quote(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                         sys.argv[6] if len(sys.argv) > 6 else None)
        # strip raw for readability
        q.pop("raw", None)
        print(json.dumps(q, indent=2))
    elif cmd == "execute":
        r = bridge_execute(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
        print(json.dumps(r, indent=2, default=str))
    elif cmd == "status":
        s = bridge_status(sys.argv[2], sys.argv[3])
        print(json.dumps(s, indent=2))
    else:
        print(f"Unknown command '{cmd}'")
        sys.exit(1)


if __name__ == "__main__":
    _cli()
