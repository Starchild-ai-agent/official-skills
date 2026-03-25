"""
Suite E: End-to-End Crypto Workflow Simulations
Tests the 4 patches working together as an integrated system
"""
from shared.crypto_safety import (
    suggest_slippage, estimate_gas_needed, verification_checklist,
    format_finality_message
)
from shared.retry import RetryConfig, with_retry, retry_api_call
from shared.response import ok, fail, fmt_price
from shared.errors import (
    InsufficientBalanceError
)
import sys
import os
import asyncio
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


def arun_check(name, coro):
    global PASSED, FAILED
    try:
        asyncio.get_event_loop().run_until_complete(coro)
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")


print("\n🧪 Suite E: End-to-End Crypto Workflow Simulations\n")

# E1: Price query fail → structured error → retry → success → formatted response


async def t_price_query_flow():
    """Simulates: CoinGecko price API flaky, retry succeeds, format response"""
    call_count = 0

    @with_retry(config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False))
    async def fetch_price():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("CoinGecko 502")
        return {"price": 67500.0, "change_24h": 3.2, "volume_24h": 25e9}

    data = await fetch_price()
    assert call_count == 3, "Should retry twice then succeed"

    # Format with response module
    response = ok(data=data, summary=fmt_price("BTC", data["price"], data["change_24h"], data["volume_24h"]))
    assert response["status"] == "ok"
    assert "BTC" in response["summary"]
    assert "$67,500" in response["summary"]
arun_check("E1: Price query — retry on 502 → success → formatted response", t_price_query_flow())

# E2: Swap pre-check → safety validation → execute → verification


def t_swap_safety_flow():
    """Simulates: User wants to swap 1000 USDC → ETH on Arbitrum"""
    # Step 1: Slippage check
    slip = suggest_slippage("ETH", "USDC")
    assert slip["suggested_slippage"] == 0.005  # 0.5%

    # Step 2: Gas estimation
    gas = estimate_gas_needed("swap_simple", "arbitrum")
    assert gas["estimated_gas_units"] > 0

    # Step 3: Simulate trade success — build verification checklist
    checklist = verification_checklist(
        "swap ETH/USDC", "arbitrum", tx_hash="0xfake123",
        expected={"balance_change": "-1000 USDC, +~0.35 ETH"}
    )
    assert "arbitrum" in checklist.lower()
    assert "0xfake123" in checklist
    assert "-1000 USDC" in checklist

    # Step 4: Build finality message
    msg = format_finality_message("arbitrum", tx_hash="0xfake123")
    assert "⏳" in msg
    assert "arbiscan.io" in msg


run_check("E2: Swap flow — slippage → gas → execute → verify → finality msg", t_swap_safety_flow)

# E3: Swap rejected by safety — clear error for small model


def t_swap_rejected():
    """Simulates: Slippage too high, balance insufficient"""
    # Pre-check: slippage for illiquid token
    slip = suggest_slippage("OBSCURE", "USDC", volume_24h=10_000)
    assert slip["category"] == "small_cap"
    assert slip["suggested_slippage"] == 0.03  # 3% — high risk

    # Pre-check: balance insufficient
    try:
        raise InsufficientBalanceError(available=50, required=1000, asset="USDC")
    except InsufficientBalanceError as e:
        error_msg = str(e)
        assert "INSUFFICIENT_BALANCE" in error_msg
        assert "950" in error_msg  # Shortfall

    # Format rejection for small model
    rejection = fail(
        "1inch/swap", "Pre-trade check failed",
        got={"balance": 50, "slippage_risk": "high"},
        need={"min_balance": 1000},
        suggestion="Deposit more USDC. Consider reducing amount for this illiquid pair.",
        code="PRE_TRADE_FAIL"
    )
    assert "PRE_TRADE_FAIL" in rejection
    assert "Deposit more USDC" in rejection


run_check("E3: Swap rejected — safety checks produce actionable error", t_swap_rejected)

# E4: Multi-chain balance query — all succeed or fail cleanly


def t_multichain_balance():
    """Simulates: Query balances across 4 chains, 1 fails"""
    results = {}
    chains = ["ethereum", "arbitrum", "base", "solana"]

    for chain in chains:
        try:
            if chain == "base":
                raise ConnectionError("Base RPC down")
            # Simulate success
            results[chain] = ok(
                data=[{"symbol": "ETH", "amount": 1.0, "usd_value": 3500}],
                summary=f"{chain}: $3,500"
            )
        except Exception:
            results[chain] = fail(
                "wallet/balance", f"Failed to query {chain}",
                suggestion=f"Retry {chain} balance check"
            )

    # 3 succeeded, 1 failed — but we have structured data for all
    successes = [c for c, r in results.items() if isinstance(r, dict) and r.get("status") == "ok"]
    failures = [c for c, r in results.items() if isinstance(r, str) and "❌" in r]
    assert len(successes) == 3
    assert len(failures) == 1
    assert "base" in failures

    # Failed chain has actionable error
    assert "Retry" in results["base"]


run_check("E4: Multi-chain balance — 3 ok + 1 fail, all structured", t_multichain_balance)

# E5: Error chain — API fail + retry exhaust + structured final error


async def t_error_chain():
    """Simulates: Coinglass funding rate API completely down"""
    try:
        await retry_api_call(
            _always_fail,
            tool_name="coinglass/funding_rate",
            max_attempts=2,
        )
        assert False, "Should have raised"
    except RuntimeError as e:
        error_str = str(e)
        assert "coinglass/funding_rate" in error_str
        assert "2 attempts" in error_str

    # Now format for the user
    user_error = fail(
        "coinglass/funding_rate",
        "API unreachable after retries",
        suggestion="Coinglass may be down. Try again in a few minutes.",
        code="RETRY_EXHAUSTED"
    )
    assert "RETRY_EXHAUSTED" in user_error
    assert "Try again" in user_error


async def _always_fail():
    raise ConnectionError("connection refused")

arun_check("E5: Error chain — retry exhaust → structured error for user", t_error_chain())

# E6: Integration — all modules importable and compatible


def t_integration_imports():
    """Verify all 4 patches can be imported together without conflicts"""
    from shared import errors, response, retry, crypto_safety
    # Check key functions exist
    assert callable(errors.safe_call)
    assert callable(response.ok)
    assert callable(response.fail)
    assert callable(retry.with_retry)
    assert callable(crypto_safety.suggest_slippage)
    assert callable(crypto_safety.get_finality_info)


run_check("E6: All 4 patches import together without conflicts", t_integration_imports)

# E7: SkillError + response.fail produce consistent format


def t_error_response_consistency():
    """Both error mechanisms should produce ❌ prefixed strings"""
    err = InsufficientBalanceError(available=0, required=100, asset="USDC")
    err_str = str(err)

    resp_str = fail("test/tool", "Not enough USDC", got=0, need=100)

    # Both should start with ❌
    assert err_str.startswith("❌"), f"SkillError should start with ❌: {err_str}"
    assert resp_str.startswith("❌"), f"fail() should start with ❌: {resp_str}"


run_check("E7: SkillError and response.fail both produce ❌-prefixed strings", t_error_response_consistency)

print(f"\n{'='*50}")
print(f"Results: {PASSED}/{PASSED+FAILED} passed")
print(f"{'='*50}")


# ---- pytest-compatible entry point ----
def test_all_checks_pass():
    """Wraps the standalone test suite for pytest discovery."""
    assert FAILED == 0, f"{FAILED} check(s) failed — run this file standalone for details"
