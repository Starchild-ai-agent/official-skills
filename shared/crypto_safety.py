"""
Crypto-Specific Safety Checks
==============================
解决 19 个 crypto workflow issues:
1. 交易后无 finality 等待/验证
2. 无 gas 预估逻辑
3. 无滑点保护默认值
4. 跨链操作无状态追踪

这些是通用的 pre/post-transaction 检查，所有交易类 skill 应该复用。
"""

from typing import Optional

# ── Chain Finality Constants ──────────────────────

CHAIN_FINALITY = {
    # chain_id: (expected_seconds, min_confirmations, description)
    "ethereum":  (180, 12, "~3 min for finality (12 blocks × 12s)"),
    "arbitrum":  (15, 1, "~15s (L2, but 7-day challenge period for withdrawals to L1)"),
    "base":      (15, 1, "~15s (L2, 7-day challenge for L1 withdrawals)"),
    "optimism":  (15, 1, "~15s (L2, 7-day challenge for L1 withdrawals)"),
    "polygon":   (120, 64, "~2 min (64 confirmations for safety)"),
    "linea":     (60, 1, "~60s (zkRollup, proof takes longer)"),
    "solana":    (0.4, 1, "~400ms per slot, finalized in ~13s (32 slots)"),
    "hyperliquid": (2, 1, "~2s (L1, single slot finality)"),
}

L2_WITHDRAWAL_CHALLENGE = {
    "arbitrum": 7 * 24 * 3600,  # 7 days
    "base": 7 * 24 * 3600,
    "optimism": 7 * 24 * 3600,
}


def get_finality_info(chain: str) -> dict:
    """Get finality expectations for a chain. Used in post-tx messaging."""
    info = CHAIN_FINALITY.get(chain.lower())
    if not info:
        return {
            "chain": chain,
            "wait_seconds": 60,
            "confirmations": 6,
            "description": f"Unknown chain '{chain}' — defaulting to 60s wait",
            "known": False,
        }
    return {
        "chain": chain,
        "wait_seconds": info[0],
        "confirmations": info[1],
        "description": info[2],
        "known": True,
    }


def format_finality_message(chain: str, tx_hash: str = "") -> str:
    """
    Generate user-facing message about when a transaction will be confirmed.
    Small models should include this in responses after any on-chain action.
    """
    info = get_finality_info(chain)
    parts = [f"⏳ Transaction submitted"]
    if tx_hash:
        explorer = _get_explorer_url(chain, tx_hash)
        parts[0] += f": [{tx_hash[:10]}...]({explorer})"

    parts.append(f"   Expected confirmation: {info['description']}")

    # L2 withdrawal warning
    challenge = L2_WITHDRAWAL_CHALLENGE.get(chain.lower())
    if challenge:
        parts.append(
            f"   ⚠️ Note: Withdrawals to L1 have a {challenge // 86400}-day challenge period"
        )

    return '\n'.join(parts)


# ── Gas Estimation ────────────────────────────────

DEFAULT_GAS_BUFFER = 1.2  # 20% buffer over estimate

# Rough gas costs in native token units for common operations
GAS_ESTIMATES = {
    "eth_transfer": 21000,
    "erc20_transfer": 65000,
    "erc20_approve": 46000,
    "swap_simple": 150000,
    "swap_complex": 350000,  # multi-hop
    "aave_deposit": 250000,
    "aave_withdraw": 300000,
}


def estimate_gas_needed(operation: str, chain: str = "ethereum") -> dict:
    """
    Pre-transaction gas sanity check.
    Returns estimated gas units + suggestion text.
    """
    gas_units = GAS_ESTIMATES.get(operation, 200000)
    buffered = int(gas_units * DEFAULT_GAS_BUFFER)

    return {
        "operation": operation,
        "estimated_gas_units": gas_units,
        "buffered_gas_units": buffered,
        "message": (
            f"Estimated gas for {operation}: ~{gas_units:,} units. "
            f"Ensure sufficient {_native_token(chain)} for gas on {chain}."
        ),
    }


# ── Slippage Protection ──────────────────────────

DEFAULT_SLIPPAGE = {
    "stablecoin_swap": 0.001,   # 0.1% — USDC/USDT/DAI
    "major_pair": 0.005,        # 0.5% — BTC, ETH
    "mid_cap": 0.01,            # 1.0% — top 50 altcoins
    "small_cap": 0.03,          # 3.0% — illiquid tokens
    "default": 0.01,            # 1.0% — when unsure
}

STABLECOINS = {"USDC", "USDT", "DAI", "BUSD", "FRAX", "TUSD", "LUSD", "crvUSD"}


def suggest_slippage(token_a: str, token_b: str, 
                     volume_24h: float = None) -> dict:
    """
    Suggest appropriate slippage tolerance.
    Call this before any swap operation.
    """
    a_upper = token_a.upper()
    b_upper = token_b.upper()

    # Stablecoin-to-stablecoin
    if a_upper in STABLECOINS and b_upper in STABLECOINS:
        category = "stablecoin_swap"
    # Major pairs
    elif a_upper in {"BTC", "ETH", "WBTC", "WETH", "stETH"} or \
         b_upper in {"BTC", "ETH", "WBTC", "WETH", "stETH"}:
        category = "major_pair"
    # Use volume as a proxy for liquidity
    elif volume_24h and volume_24h > 10_000_000:
        category = "major_pair"
    elif volume_24h and volume_24h > 1_000_000:
        category = "mid_cap"
    elif volume_24h and volume_24h < 100_000:
        category = "small_cap"
    else:
        category = "default"

    slippage = DEFAULT_SLIPPAGE[category]
    return {
        "suggested_slippage": slippage,
        "slippage_pct": f"{slippage * 100:.1f}%",
        "category": category,
        "message": (
            f"Suggested slippage for {token_a}/{token_b}: {slippage*100:.1f}% "
            f"({category}). Adjust if trading during high volatility."
        ),
    }


# ── Post-Transaction Verification Template ────────

def verification_checklist(operation: str, chain: str, 
                          tx_hash: str = "", expected: dict = None) -> str:
    """
    Generate a verification checklist for the LLM to follow after a transaction.
    This is a PROMPT for the model, not automated execution.
    """
    checks = [
        f"## Post-Transaction Verification: {operation}",
        f"Chain: {chain} | TX: {tx_hash or 'pending'}",
        "",
        "### Checklist:",
    ]

    finality = get_finality_info(chain)
    checks.append(f"1. ⏳ Wait for confirmation ({finality['description']})")

    if expected:
        if 'balance_change' in expected:
            checks.append(
                f"2. 💰 Verify balance changed by ~{expected['balance_change']} "
                f"(call wallet_balance or hl_account)"
            )
        if 'position_change' in expected:
            checks.append(
                f"3. 📊 Verify position: {expected['position_change']} "
                f"(call hl_account)"
            )
    else:
        checks.append("2. 💰 Call balance tool to verify funds changed")
        checks.append("3. 📊 Call account tool to verify state changed")

    checks.append("4. ✅ Report verified state to user (not estimated)")

    return '\n'.join(checks)


# ── Internal Helpers ──────────────────────────────

def _native_token(chain: str) -> str:
    return {
        "ethereum": "ETH", "arbitrum": "ETH", "base": "ETH",
        "optimism": "ETH", "polygon": "MATIC", "linea": "ETH",
        "solana": "SOL", "hyperliquid": "USDC",
    }.get(chain.lower(), "native token")


def _get_explorer_url(chain: str, tx_hash: str) -> str:
    explorers = {
        "ethereum": f"https://etherscan.io/tx/{tx_hash}",
        "arbitrum": f"https://arbiscan.io/tx/{tx_hash}",
        "base": f"https://basescan.org/tx/{tx_hash}",
        "optimism": f"https://optimistic.etherscan.io/tx/{tx_hash}",
        "polygon": f"https://polygonscan.com/tx/{tx_hash}",
        "linea": f"https://lineascan.build/tx/{tx_hash}",
        "solana": f"https://solscan.io/tx/{tx_hash}",
    }
    return explorers.get(chain.lower(), f"https://blockscan.com/tx/{tx_hash}")
