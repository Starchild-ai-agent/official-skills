"""
Suite D: Crypto Safety Layer Validation
Tests shared/crypto_safety.py — pre/post-transaction safety checks
"""
from shared.crypto_safety import (
    get_finality_info, format_finality_message,
    estimate_gas_needed, suggest_slippage,
    verification_checklist,
    L2_WITHDRAWAL_CHALLENGE, GAS_ESTIMATES
)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'patches'))


PASSED = 0
FAILED = 0


def run_check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")


print("\n🧪 Suite D: Crypto Safety Layer\n")

# D1: Known chain finality


def t_finality_known():
    info = get_finality_info("ethereum")
    assert info["known"] is True
    assert info["wait_seconds"] == 180
    assert info["confirmations"] == 12
    assert "3 min" in info["description"]


run_check("get_finality_info returns correct data for ethereum", t_finality_known)

# D2: Unknown chain fallback


def t_finality_unknown():
    info = get_finality_info("zetachain")
    assert info["known"] is False
    assert info["wait_seconds"] == 60  # Default
    assert "Unknown chain" in info["description"]


run_check("get_finality_info returns safe defaults for unknown chain", t_finality_unknown)

# D3: All supported chains have finality data


def t_finality_all_chains():
    for chain in ["ethereum", "arbitrum", "base", "optimism", "polygon", "linea", "solana", "hyperliquid"]:
        info = get_finality_info(chain)
        assert info["known"] is True, f"{chain} should be known"
        assert info["wait_seconds"] > 0 or chain == "solana", f"{chain} should have wait time"


run_check("All 8 major chains have finality data", t_finality_all_chains)

# D4: L2 withdrawal challenge periods


def t_l2_challenges():
    for chain in ["arbitrum", "base", "optimism"]:
        assert chain in L2_WITHDRAWAL_CHALLENGE, f"{chain} should have challenge period"
        assert L2_WITHDRAWAL_CHALLENGE[chain] == 7 * 86400, f"{chain} should be 7 days"


run_check("L2s have 7-day challenge periods", t_l2_challenges)

# D5: Finality message format


def t_finality_message():
    msg = format_finality_message("ethereum", tx_hash="0xabc123def456")
    assert "⏳" in msg
    assert "0xabc123def" in msg  # Truncated hash
    assert "etherscan.io" in msg
    assert "3 min" in msg


run_check("format_finality_message includes emoji, truncated hash, explorer, time", t_finality_message)

# D6: L2 finality message includes withdrawal warning


def t_finality_l2_warning():
    msg = format_finality_message("arbitrum")
    assert "7-day" in msg or "7 day" in msg, f"Should warn about challenge period, got: {msg}"


run_check("L2 finality message warns about withdrawal challenge period", t_finality_l2_warning)

# D7: Gas estimation known operation


def t_gas_known():
    r = estimate_gas_needed("eth_transfer")
    assert r["estimated_gas_units"] == 21000
    assert r["buffered_gas_units"] == int(21000 * 1.2)
    assert "ETH" in r["message"] or "gas" in r["message"].lower()


run_check("Gas estimate: eth_transfer = 21000 units + 20% buffer", t_gas_known)

# D8: Gas estimation unknown operation


def t_gas_unknown():
    r = estimate_gas_needed("exotic_defi_thing")
    assert r["estimated_gas_units"] == 200000  # Default
    assert r["buffered_gas_units"] > 200000


run_check("Gas estimate: unknown operation gets 200K default", t_gas_unknown)

# D9: Gas estimates cover common operations


def t_gas_coverage():
    for op in [
        "eth_transfer",
        "erc20_transfer",
        "erc20_approve",
        "swap_simple",
        "swap_complex",
        "aave_deposit",
            "aave_withdraw"]:
        assert op in GAS_ESTIMATES, f"{op} should have gas estimate"


run_check("Gas estimates cover 7 common operations", t_gas_coverage)

# D10: Slippage — stablecoin pair


def t_slippage_stable():
    r = suggest_slippage("USDC", "USDT")
    assert r["category"] == "stablecoin_swap"
    assert r["suggested_slippage"] == 0.001  # 0.1%


run_check("Slippage: USDC/USDT = 0.1% (stablecoin)", t_slippage_stable)

# D11: Slippage — major pair


def t_slippage_major():
    r = suggest_slippage("ETH", "USDC")
    assert r["category"] == "major_pair"
    assert r["suggested_slippage"] == 0.005  # 0.5%


run_check("Slippage: ETH/USDC = 0.5% (major pair)", t_slippage_major)

# D12: Slippage — volume-based classification


def t_slippage_volume():
    r_high = suggest_slippage("DOGE", "USDT", volume_24h=50_000_000)
    assert r_high["category"] == "major_pair"
    r_low = suggest_slippage("PEPE", "USDT", volume_24h=50_000)
    assert r_low["category"] == "small_cap"


run_check("Slippage: uses 24h volume to classify liquidity", t_slippage_volume)

# D13: Slippage — default for unknown tokens


def t_slippage_default():
    r = suggest_slippage("RANDOM", "TOKEN")
    assert r["category"] == "default"
    assert r["suggested_slippage"] == 0.01  # 1%


run_check("Slippage: unknown tokens get 1% default", t_slippage_default)

# D14: Slippage message is human-readable


def t_slippage_message():
    r = suggest_slippage("BTC", "USDC")
    assert "BTC" in r["message"]
    assert "USDC" in r["message"]
    assert "%" in r["slippage_pct"]


run_check("Slippage suggestion includes readable message", t_slippage_message)

# D15: Verification checklist basic


def t_checklist_basic():
    c = verification_checklist("swap", "ethereum", tx_hash="0xabc")
    assert "swap" in c.lower()
    assert "ethereum" in c.lower()
    assert "0xabc" in c
    assert "balance" in c.lower() and "verify" in c.lower()  # Suggests verification step


run_check("Verification checklist includes operation, chain, tx hash", t_checklist_basic)

# D16: Verification checklist with expected outcomes


def t_checklist_expected():
    c = verification_checklist(
        "deposit", "arbitrum", tx_hash="0x123",
        expected={"balance_change": "+1000 USDC", "position_change": "collateral +1000"}
    )
    assert "+1000 USDC" in c
    assert "collateral" in c


run_check("Verification checklist includes expected balance/position changes", t_checklist_expected)

print(f"\n{'='*50}")
print(f"Results: {PASSED}/{PASSED+FAILED} passed")
print(f"{'='*50}")


# ---- pytest-compatible entry point ----
def test_all_checks_pass():
    """Wraps the standalone test suite for pytest discovery."""
    assert FAILED == 0, f"{FAILED} check(s) failed — run this file standalone for details"
