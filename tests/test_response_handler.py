"""
Unit tests for utils/response_handler.py — the four immutable logic modules.
Tests use real API response shapes captured from Coinglass/CoinGecko tools.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.response_handler import (  # noqa: E402
    intercept,
    process_liquidation_data,
    enforce_model_budget,
    handle_api_error,
    normalize_funding,
    normalize_funding_response,
    TOP_COINS_FALLBACK,
    EXCHANGE_INTERVALS,
)


# ═══════════════════════════════════════════════════════════
# MODULE A: Liquidation Zero-Value Isolation
# ═══════════════════════════════════════════════════════════


class TestModuleA:
    """Tests for process_liquidation_data."""

    def test_recompute_from_exchange_breakdown(self):
        """When total=0 but exchanges have data, recompute total."""
        data = {
            "total_liquidations_usd": 0,
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "exchanges": [
                {"exchange": "Bybit", "total_liquidation_usd": 3_425_679},
                {"exchange": "Binance", "total_liquidation_usd": 932_349},
                {"exchange": "OKX", "total_liquidation_usd": 210_747},
            ],
        }
        result = process_liquidation_data(data)
        assert result["_patch"] == "module_a_recomputed"
        assert result["total_liquidations_usd"] == pytest.approx(
            4_568_775, rel=0.01
        )
        assert result["sentiment"] == "data_partial"
        assert "$" in result["interpretation"]

    def test_true_zero_no_liquidations(self):
        """When everything is genuinely zero, mark neutral."""
        data = {
            "total_liquidations_usd": 0,
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "exchanges": [],
        }
        result = process_liquidation_data(data)
        assert result["_patch"] == "module_a_zero"
        assert result["sentiment"] == "neutral"
        assert result["dominant_side"] == "none"

    def test_total_nonzero_but_split_zero(self):
        """Total > 0, but long/short both 0 → structural data loss."""
        data = {
            "total_liquidations_usd": 5_000_000,
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "exchanges": [],
        }
        result = process_liquidation_data(data)
        assert result["_patch"] == "module_a_partial"
        assert result["sentiment"] == "data_partial"
        assert result["dominant_side"] == "unknown"

    def test_normal_long_dominant(self):
        """75% long liquidations → bearish pressure."""
        data = {
            "total_liquidations_usd": 10_000_000,
            "long_liquidations_usd": 7_500_000,
            "short_liquidations_usd": 2_500_000,
            "exchanges": [],
        }
        result = process_liquidation_data(data)
        assert result["_patch"] == "module_a_normal"
        assert result["dominant_side"] == "longs"
        assert result["sentiment"] == "bearish_pressure"
        assert result["long_ratio"] == 0.75

    def test_normal_short_dominant(self):
        """80% short liquidations → bullish pressure."""
        data = {
            "total_liquidations_usd": 10_000_000,
            "long_liquidations_usd": 2_000_000,
            "short_liquidations_usd": 8_000_000,
            "exchanges": [],
        }
        result = process_liquidation_data(data)
        assert result["dominant_side"] == "shorts"
        assert result["sentiment"] == "bullish_pressure"

    def test_balanced_liquidations(self):
        """50/50 split → balanced."""
        data = {
            "total_liquidations_usd": 10_000_000,
            "long_liquidations_usd": 5_000_000,
            "short_liquidations_usd": 5_000_000,
            "exchanges": [],
        }
        result = process_liquidation_data(data)
        assert result["dominant_side"] == "balanced"
        assert result["sentiment"] == "neutral"

    def test_exchange_uses_liquidation_usd_key(self):
        """Some exchanges use 'liquidation_usd' instead of 'total_liquidation_usd'."""
        data = {
            "total_liquidations_usd": 0,
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "exchanges": [
                {"exchange": "Test", "liquidation_usd": 1_000_000},
            ],
        }
        result = process_liquidation_data(data)
        assert result["_patch"] == "module_a_recomputed"
        assert result["total_liquidations_usd"] == 1_000_000


# ═══════════════════════════════════════════════════════════
# MODULE B: Response Size Budget Enforcer
# ═══════════════════════════════════════════════════════════


class TestModuleB:
    """Tests for enforce_model_budget."""

    def test_truncate_raw_list(self):
        """Large list gets truncated to max_items."""
        data = list(range(500))
        result = enforce_model_budget(data, max_items=10)
        assert len(result["results"]) == 10
        assert result["metadata"]["total_found"] == 500
        assert result["metadata"]["displayed"] == 10

    def test_truncate_coinglass_dict(self):
        """Coinglass-format dict with 'data' key."""
        data = {"code": "0", "data": list(range(200))}
        result = enforce_model_budget(data, tool_name="cg_coins_market_data")
        assert len(result["data"]) == 10
        assert result["_truncation"]["total_found"] == 200

    def test_whale_transfers_limit(self):
        """cg_whale_transfers has hard limit of 5."""
        data = list(range(100))
        result = enforce_model_budget(data, tool_name="cg_whale_transfers")
        assert result["metadata"]["displayed"] == 5

    def test_small_list_unchanged(self):
        """Lists under limit pass through unchanged."""
        data = [1, 2, 3]
        result = enforce_model_budget(data, max_items=10)
        assert result == [1, 2, 3]

    def test_small_dict_unchanged(self):
        """Small dicts pass through unchanged."""
        data = {"symbol": "BTC", "price": 71000}
        result = enforce_model_budget(data)
        assert result == data

    def test_known_tools_have_limits(self):
        """All known large tools have defined limits."""
        from utils.response_handler import KNOWN_LARGE_TOOLS

        for tool, limit in KNOWN_LARGE_TOOLS.items():
            assert isinstance(tool, str)
            assert limit is None or isinstance(limit, int)


# ═══════════════════════════════════════════════════════════
# MODULE C: Error Attribution Redirector
# ═══════════════════════════════════════════════════════════


class TestModuleC:
    """Tests for handle_api_error."""

    def test_invalid_symbol(self):
        """Unknown symbol → invalid_symbol category."""
        result = handle_api_error(
            "Failed to fetch",
            symbol="INVALIDCOIN999",
            tool_name="cg_open_interest",
        )
        assert result["category"] == "invalid_symbol"
        assert result["_patch"] == "module_c"

    def test_api_key_reclassified(self):
        """'API key' errors reclassified as param errors in sc-proxy env."""
        result = handle_api_error(
            "Invalid API Key or insufficient permissions.",
            symbol="BTC",
            tool_name="funding_rate",
        )
        assert result["category"] == "param_error"
        assert "sc-proxy" in result["message"]

    def test_rate_limit_detected(self):
        result = handle_api_error("429 Too Many Requests")
        assert result["category"] == "rate_limit"

    def test_timeout_detected(self):
        result = handle_api_error("Connection timed out after 30s")
        assert result["category"] == "network"

    def test_502_detected(self):
        result = handle_api_error("502 Bad Gateway")
        assert result["category"] == "network"

    def test_unknown_error(self):
        result = handle_api_error("Something unexpected happened")
        assert result["category"] == "unknown"
        assert result["_patch"] == "module_c"

    def test_top_coins_fallback_has_majors(self):
        """Verify TOP_COINS_FALLBACK contains major coins."""
        for coin in ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB"]:
            assert coin in TOP_COINS_FALLBACK


# ═══════════════════════════════════════════════════════════
# MODULE D: Funding Rate APR Normalizer
# ═══════════════════════════════════════════════════════════


class TestModuleD:
    """Tests for normalize_funding and normalize_funding_response."""

    def test_8h_exchange_unchanged(self):
        """8h rate normalized to 8h → same value."""
        result = normalize_funding(0.000916, exchange="Binance")
        assert result["normalized_8h"] == 0.000916
        assert result["interval"] == "8h"
        assert result["_patch"] == "module_d"

    def test_1h_exchange_scaled(self):
        """1h rate × 8 = 8h equivalent."""
        result = normalize_funding(0.00125, exchange="Hyperliquid")
        assert result["normalized_8h"] == 0.01
        assert result["interval"] == "1h"

    def test_apr_calculation(self):
        """APR = rate_8h × 3 × 365."""
        result = normalize_funding(0.001, interval_hrs=8)
        expected_apr = 0.001 * 3 * 365  # = 1.095
        assert result["annualized_apr"] == pytest.approx(expected_apr, rel=0.001)

    def test_negative_rate(self):
        """Negative funding rates preserved correctly."""
        result = normalize_funding(-0.005, exchange="OKX")
        assert result["normalized_8h"] == -0.005
        assert result["annualized_apr"] < 0

    def test_unknown_exchange_defaults_8h(self):
        """Unknown exchange uses 8h default."""
        result = normalize_funding(0.001, exchange="SomeNewExchange")
        assert result["interval"] == "8h"
        assert result["normalized_8h"] == 0.001

    def test_full_response_processing(self):
        """Process an entire funding_rate() response."""
        resp = {
            "code": "0",
            "data": [
                {
                    "symbol": "BTC",
                    "uMarginList": [
                        {
                            "rate": 0.000916,
                            "exchangeName": "Binance",
                            "fundingIntervalHours": 8,
                        },
                        {
                            "rate": 0.00125,
                            "exchangeName": "Hyperliquid",
                            "fundingIntervalHours": 1,
                        },
                    ],
                    "cMarginList": [],
                }
            ],
        }
        result = normalize_funding_response(resp)
        entries = result["data"][0]["uMarginList"]
        assert entries[0]["normalized_8h"] == 0.000916
        assert entries[1]["normalized_8h"] == 0.01
        assert all(e["_patch"] == "module_d" for e in entries)

    def test_exchange_intervals_coverage(self):
        """Verify all major exchanges have defined intervals."""
        for exchange in [
            "Binance", "OKX", "Bybit", "Hyperliquid",
            "dYdX", "Kraken", "Bitfinex",
        ]:
            assert exchange in EXCHANGE_INTERVALS


# ═══════════════════════════════════════════════════════════
# MASTER INTERCEPTOR
# ═══════════════════════════════════════════════════════════


class TestInterceptor:
    """Tests for the master intercept() function."""

    def test_error_string_intercepted(self):
        """Error strings route through Module C."""
        result = intercept(
            "cg_open_interest",
            "❌ Error: Check COINGLASS_API_KEY.",
            symbol="INVALIDCOIN999",
        )
        assert result["_patch"] == "module_c"
        assert result["category"] == "invalid_symbol"

    def test_error_dict_intercepted(self):
        """Error dicts route through Module C."""
        result = intercept(
            "cg_liquidations",
            {"status": "error", "message": "429 rate limit exceeded"},
        )
        assert result["category"] == "rate_limit"

    def test_liquidation_routes_to_module_a(self):
        """cg_liquidations responses route through Module A."""
        data = {
            "total_liquidations_usd": 5_000_000,
            "long_liquidations_usd": 4_000_000,
            "short_liquidations_usd": 1_000_000,
            "exchanges": [],
        }
        result = intercept("cg_liquidations", data, symbol="BTC")
        assert result["_patch"] == "module_a_normal"

    def test_funding_routes_to_module_d(self):
        """funding_rate responses route through Module D."""
        resp = {
            "code": "0",
            "data": [
                {
                    "symbol": "BTC",
                    "uMarginList": [
                        {
                            "rate": 0.001,
                            "exchangeName": "Binance",
                            "fundingIntervalHours": 8,
                        }
                    ],
                    "cMarginList": [],
                }
            ],
        }
        result = intercept("funding_rate", resp, symbol="BTC")
        assert result["data"][0]["uMarginList"][0]["_patch"] == "module_d"

    def test_budget_always_applied(self):
        """Module B runs on every response (last in chain)."""
        big_list = list(range(500))
        result = intercept("cg_whale_transfers", big_list)
        assert "metadata" in result
        assert result["metadata"]["displayed"] == 5

    def test_passthrough_for_unknown_tool(self):
        """Unknown tools still get budget enforcement."""
        data = {"some": "data"}
        result = intercept("unknown_tool", data)
        assert result == data
