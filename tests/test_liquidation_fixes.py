#!/usr/bin/env python3
"""
Unit tests for coinglass/tools/liquidations.py fixes.

Tests:
1. Fallback self-sum when "All" row returns zeros
2. Zero-data guard in sentiment analysis
3. Edge cases (empty data, missing fields)
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# conftest.py handles core.http_client stubbing and path setup
http_mod = sys.modules["core.http_client"]

# Now safe to import
from coinglass.tools.liquidations import (  # noqa: E402
    get_liquidations,
    get_liquidation_aggregated,
)


def _make_response(all_long, all_short, exchanges):
    """Build a mock API response."""
    data = [{"exchange": "All",
             "long_liquidation_usd": all_long,
             "short_liquidation_usd": all_short,
             "liquidation_usd": (all_long or 0) + (all_short or 0)}]
    for name, lng, sht in exchanges:
        data.append({"exchange": name,
                     "long_liquidation_usd": lng,
                     "short_liquidation_usd": sht,
                     "liquidation_usd": (lng or 0) + (sht or 0)})
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"code": "0", "data": data}
    resp.raise_for_status = MagicMock()
    return resp


class TestLiquidationFallbackSum(unittest.TestCase):
    """Test Fix 1: self-sum fallback when 'All' row is zero."""

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_normal_all_row(self, _key):
        """When 'All' row has valid data, use it directly."""
        http_mod.proxied_get.return_value = _make_response(
            5_000_000, 3_000_000,
            [("Binance", 3_000_000, 2_000_000),
             ("OKX", 2_000_000, 1_000_000)])

        result = get_liquidations("BTC", "h24")

        self.assertIsNotNone(result)
        self.assertEqual(result["long_liquidations_usd"], 5_000_000)
        self.assertEqual(result["short_liquidations_usd"], 3_000_000)
        self.assertEqual(result["total_liquidations_usd"], 8_000_000)

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_zero_all_row_fallback(self, _key):
        """When 'All' row is zero but exchanges have data, self-sum."""
        http_mod.proxied_get.return_value = _make_response(
            0, 0,
            [("Binance", 3_000_000, 2_000_000),
             ("OKX", 2_000_000, 1_500_000),
             ("Bybit", 1_000_000, 500_000)])

        result = get_liquidations("BTC", "h24")

        self.assertIsNotNone(result)
        self.assertEqual(result["long_liquidations_usd"], 6_000_000)
        self.assertEqual(result["short_liquidations_usd"], 4_000_000)
        self.assertEqual(result["total_liquidations_usd"], 10_000_000)
        self.assertAlmostEqual(result["long_percent"], 60.0)
        self.assertAlmostEqual(result["short_percent"], 40.0)

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_truly_zero_market(self, _key):
        """When everything is genuinely zero, return zeros."""
        http_mod.proxied_get.return_value = _make_response(
            0, 0, [("Binance", 0, 0), ("OKX", 0, 0)])

        result = get_liquidations("BTC", "h24")

        self.assertIsNotNone(result)
        self.assertEqual(result["total_liquidations_usd"], 0)

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_none_values_treated_as_zero(self, _key):
        """None values in API response should be treated as 0."""
        data = [
            {"exchange": "All",
             "long_liquidation_usd": None,
             "short_liquidation_usd": None,
             "liquidation_usd": None},
            {"exchange": "Binance",
             "long_liquidation_usd": 1_000_000,
             "short_liquidation_usd": None,
             "liquidation_usd": 1_000_000}
        ]
        resp = MagicMock()
        resp.json.return_value = {"code": "0", "data": data}
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_liquidations("BTC", "h24")

        self.assertIsNotNone(result)
        self.assertEqual(result["long_liquidations_usd"], 1_000_000)
        self.assertEqual(result["short_liquidations_usd"], 0)


class TestSentimentZeroGuard(unittest.TestCase):
    """Test Fix 2: zero-data guard in sentiment analysis."""

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_zero_data_no_balanced_label(self, _key):
        """Zero liquidation data should NOT say 'Balanced'."""
        http_mod.proxied_get.return_value = _make_response(
            0, 0, [])

        result = get_liquidation_aggregated("BTC", "h24")

        # get_liquidations returns None when data is empty
        # so get_liquidation_aggregated returns None
        # This is acceptable — no misleading label produced
        if result is not None:
            analysis = result.get("analysis", {})
            self.assertNotIn("Balanced", analysis.get("sentiment", ""))

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_zero_total_from_zero_all_row(self, _key):
        """All-zero with exchanges = 0 produces 'No data'."""
        http_mod.proxied_get.return_value = _make_response(
            0, 0, [("Binance", 0, 0)])

        result = get_liquidation_aggregated("BTC", "h24")

        self.assertIsNotNone(result)
        analysis = result.get("analysis", {})
        self.assertIn("No liquidation data", analysis["sentiment"])
        self.assertEqual(analysis["dominant_side"], "none")

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_bearish_sentiment(self, _key):
        """75% long liquidations -> heavily bearish."""
        http_mod.proxied_get.return_value = _make_response(
            7_500_000, 2_500_000,
            [("Binance", 7_500_000, 2_500_000)])

        result = get_liquidation_aggregated("BTC", "h24")

        analysis = result["analysis"]
        self.assertIn("Heavily bearish", analysis["sentiment"])
        self.assertEqual(analysis["dominant_side"], "longs")

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_bullish_sentiment(self, _key):
        """80% short liquidations -> heavily bullish."""
        http_mod.proxied_get.return_value = _make_response(
            2_000_000, 8_000_000,
            [("Binance", 2_000_000, 8_000_000)])

        result = get_liquidation_aggregated("BTC", "h24")

        analysis = result["analysis"]
        self.assertIn("Heavily bullish", analysis["sentiment"])
        self.assertEqual(analysis["dominant_side"], "shorts")

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_fallback_triggers_correct_sentiment(self, _key):
        """Fallback sum should produce correct sentiment."""
        # All row zero, but exchanges show 80% longs
        http_mod.proxied_get.return_value = _make_response(
            0, 0,
            [("Binance", 8_000_000, 2_000_000)])

        result = get_liquidation_aggregated("BTC", "h24")

        self.assertEqual(result["total_liquidations_usd"], 10_000_000)
        analysis = result["analysis"]
        self.assertIn("bearish", analysis["sentiment"].lower())


class TestEdgeCases(unittest.TestCase):

    @patch("coinglass.tools.liquidations._get_api_key", return_value=None)
    def test_no_api_key(self, _key):
        result = get_liquidations("BTC")
        self.assertIsNone(result)

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_empty_data(self, _key):
        resp = MagicMock()
        resp.json.return_value = {"code": "0", "data": []}
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_liquidations("BTC")
        self.assertIsNone(result)

    @patch("coinglass.tools.liquidations._get_api_key", return_value="test")
    def test_api_error_code(self, _key):
        resp = MagicMock()
        resp.json.return_value = {"code": "40001", "msg": "Invalid param"}
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_liquidations("BTC")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
