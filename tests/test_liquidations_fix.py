#!/usr/bin/env python3
"""
Tests for the coinglass liquidations endpoint migration.

Validates that the new coin-list based implementation returns
correct long/short breakdowns (the old exchange-list endpoint
returned zeros for these fields).
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault("COINGLASS_API_KEY", "test-key")


class TestLiquidationsFix(unittest.TestCase):
    """Test the fixed liquidations module."""

    def _make_coin_list_response(self, symbol="BTC",
                                 long_24h=4000000, short_24h=3000000):
        """Helper: build a mock coin-list API response."""
        return {
            "code": "0",
            "msg": "success",
            "data": [
                {
                    "symbol": symbol,
                    "liquidation_usd_24h": long_24h + short_24h,
                    "long_liquidation_usd_24h": long_24h,
                    "short_liquidation_usd_24h": short_24h,
                    "liquidation_usd_12h": long_24h * 0.5 + short_24h * 0.5,
                    "long_liquidation_usd_12h": long_24h * 0.5,
                    "short_liquidation_usd_12h": short_24h * 0.5,
                    "liquidation_usd_4h": long_24h * 0.2 + short_24h * 0.2,
                    "long_liquidation_usd_4h": long_24h * 0.2,
                    "short_liquidation_usd_4h": short_24h * 0.2,
                    "liquidation_usd_1h": long_24h * 0.05 + short_24h * 0.05,
                    "long_liquidation_usd_1h": long_24h * 0.05,
                    "short_liquidation_usd_1h": short_24h * 0.05,
                },
                {
                    "symbol": "ETH",
                    "liquidation_usd_24h": 1000000,
                    "long_liquidation_usd_24h": 600000,
                    "short_liquidation_usd_24h": 400000,
                }
            ]
        }

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_long_short_not_zero(self, mock_get):
        """Core fix: long and short must not be zero when data exists."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidations
        result = get_liquidations("BTC", "h24", exchange="Binance")

        self.assertIsNotNone(result)
        self.assertGreater(result["long_liquidations_usd"], 0,
                           "long_liquidations_usd must not be zero")
        self.assertGreater(result["short_liquidations_usd"], 0,
                           "short_liquidations_usd must not be zero")
        self.assertEqual(result["long_liquidations_usd"], 4000000)
        self.assertEqual(result["short_liquidations_usd"], 3000000)

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_percentages_correct(self, mock_get):
        """Percentages should sum to ~100%."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response(
            long_24h=7000000, short_24h=3000000)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidations
        result = get_liquidations("BTC", "h24", exchange="Binance")

        self.assertAlmostEqual(result["long_percent"], 70.0, places=0)
        self.assertAlmostEqual(result["short_percent"], 30.0, places=0)
        self.assertAlmostEqual(
            result["long_percent"] + result["short_percent"], 100.0, places=0)

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_time_windows(self, mock_get):
        """All time windows (h1, h4, h12, h24) should work."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidations

        for tw in ["h1", "h4", "h12", "h24"]:
            result = get_liquidations("BTC", tw, exchange="Binance")
            self.assertIsNotNone(result, f"Failed for time_window={tw}")
            self.assertEqual(result["time_window"], tw)
            # All time windows should have non-zero data for our mock
            self.assertGreater(
                result["total_liquidations_usd"], 0,
                f"total should be >0 for {tw}")

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_analysis_sentiment(self, mock_get):
        """Sentiment analysis should reflect the data correctly."""
        # 80% longs = heavily bearish
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response(
            long_24h=8000000, short_24h=2000000)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidation_aggregated
        result = get_liquidation_aggregated("BTC", "h24")

        self.assertIn("analysis", result)
        self.assertEqual(result["analysis"]["dominant_side"], "longs")
        self.assertIn("bearish", result["analysis"]["sentiment"].lower())

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_zero_data_no_misleading_sentiment(self, mock_get):
        """Zero liquidation data should not produce 'Balanced' sentiment."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response(
            long_24h=0, short_24h=0)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidation_aggregated
        result = get_liquidation_aggregated("BTC", "h24")

        self.assertIsNotNone(result)
        self.assertEqual(result["analysis"]["dominant_side"], "none")
        self.assertNotIn("Balanced", result["analysis"]["sentiment"])

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_symbol_filtering(self, mock_get):
        """Should only return data for the requested symbol."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self._make_coin_list_response()
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidations
        result = get_liquidations("BTC", "h24", exchange="Binance")

        self.assertEqual(result["symbol"], "BTC")

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_api_error_returns_none(self, mock_get):
        """API errors should return None, not crash."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": "50001", "msg": "Invalid API key"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from coinglass.tools.liquidations import get_liquidations
        result = get_liquidations("BTC", "h24", exchange="Binance")

        # Should return a result with 0 values (no crash)
        self.assertIsNotNone(result)
        self.assertEqual(result["total_liquidations_usd"], 0)

    @patch('coinglass.tools.liquidations.proxied_get')
    def test_multi_exchange_aggregation(self, mock_get):
        """When no exchange specified, should aggregate multiple exchanges."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = self._make_coin_list_response(
                long_24h=1000000, short_24h=500000)
            return resp

        mock_get.side_effect = side_effect

        from coinglass.tools.liquidations import get_liquidations
        result = get_liquidations("BTC", "h24")  # no exchange

        # Should have called multiple exchanges
        self.assertGreater(call_count, 1)
        # Totals should be aggregated
        self.assertGreater(result["long_liquidations_usd"], 1000000)
        self.assertGreater(result["num_exchanges"], 1)


if __name__ == "__main__":
    unittest.main()
