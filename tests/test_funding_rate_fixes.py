#!/usr/bin/env python3
"""
Unit tests for coinglass/tools/funding_rate.py fixes.

Tests:
1. 8h normalization of funding rates across exchanges
2. Mixed interval handling (1h, 4h, 8h)
3. Edge cases (missing data, None rates)

The implementation normalizes all rates to 8h-equivalent,
then annualizes as: rate_8h * 3 * 365 * 100 (percent).
"""
import sys
import unittest
from unittest.mock import patch, MagicMock

# conftest.py handles core.http_client stubbing and path setup
http_mod = sys.modules["core.http_client"]

from coinglass.tools.funding_rate import get_symbol_funding_rate  # noqa: E402


def _make_funding_response(exchanges):
    """Build mock get_funding_rates() result.

    exchanges: list of (name, rate, predicted_rate, interval_h)
    The actual API returns a nested structure:
    {"code": "0", "data": [{"symbol": "BTC", "uMarginList": [...]}]}
    """
    margin_list = []
    for name, rate, predicted, interval_h in exchanges:
        margin_list.append({
            "exchangeName": name,
            "rate": rate,
            "predictedRate": predicted,
            "fundingIntervalHours": interval_h,
            "nextFundingTime": 1765497600000,
        })
    return {
        "code": "0",
        "data": [{"symbol": "BTC", "uMarginList": margin_list}]
    }


class TestFundingRateNormalization(unittest.TestCase):
    """Test Fix: 8h normalization of funding rates."""

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_8h_exchange_unchanged(self, _key):
        """8h funding interval rates should stay same when normalized."""
        rate = 0.01  # 0.01 (1%) per 8h
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", rate, rate, 8),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        self.assertIsNotNone(result)
        # 8h rate → 8h equivalent = rate * (8/8) = rate
        self.assertAlmostEqual(result["rate_8h_equivalent"], rate, places=6)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_1h_exchange_scaled_up(self, _key):
        """1h funding interval should be multiplied by 8 for 8h equivalent."""
        rate = 0.001  # 0.001 per 1h
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Bybit", rate, rate, 1),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        self.assertIsNotNone(result)
        # 1h * (8/1) = 8h equivalent
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], rate * 8, places=6)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_4h_exchange_scaled_up(self, _key):
        """4h funding interval should be multiplied by 2 for 8h equivalent."""
        rate = 0.005  # 0.005 per 4h
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("OKX", rate, rate, 4),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        self.assertIsNotNone(result)
        # 4h * (8/4) = 8h equivalent
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], rate * 2, places=6)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_average_normalizes_mixed_intervals(self, _key):
        """Average should use 8h-normalized rates, not raw."""
        # Binance: 0.01 per 8h → 8h eq = 0.01
        # Bybit:   0.001 per 1h → 8h eq = 0.008
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", 0.01, 0.01, 8),
            ("Bybit", 0.001, 0.001, 1),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        # average_8h = (0.01 + 0.008) / 2 = 0.009
        expected_avg = (0.01 + 0.001 * 8) / 2
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], expected_avg, places=6)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_average_mixed_real_world(self, _key):
        """Real-world scenario: 3 exchanges with different intervals
        that all normalize to the same 8h-equivalent."""
        # All rates chosen to normalize to 0.01 per 8h:
        # Binance: 0.01 per 8h → 0.01
        # OKX:     0.005 per 4h → 0.01
        # Bybit:   0.00125 per 1h → 0.01
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", 0.01, 0.01, 8),
            ("OKX", 0.005, 0.005, 4),
            ("Bybit", 0.00125, 0.00125, 1),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        # All normalize to same 8h rate → average = 0.01
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], 0.01, places=6)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_annualized_rate(self, _key):
        """Annualized rate = rate_8h * 3 * 365 * 100 (percent)."""
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", 0.01, 0.01, 8),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        # 0.01 * 3 * 365 * 100 = 1095.0%
        expected_annual = 0.01 * 3 * 365 * 100
        self.assertAlmostEqual(
            result["annualized_percent"], expected_annual, places=2)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_exchange_not_found(self, _key):
        """Empty data array should return None."""
        resp = MagicMock()
        resp.json.return_value = {"code": "0", "data": []}
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("NONEXISTENTCOIN")
        self.assertIsNone(result)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_specific_exchange_normalization(self, _key):
        """When querying a specific exchange, rate_8h_equivalent is set."""
        rate = 0.002  # 0.002 per 4h
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("OKX", rate, rate, 4),
            ("Binance", 0.01, 0.01, 8),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC", exchange="OKX")

        self.assertIsNotNone(result)
        self.assertEqual(result["exchange"], "OKX")
        # 0.002 * (8/4) = 0.004
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], rate * 2, places=6)


class TestFundingRateEdgeCases(unittest.TestCase):

    @patch("coinglass.tools.funding_rate._get_api_key", return_value=None)
    def test_no_api_key(self, _key):
        result = get_symbol_funding_rate("BTC")
        self.assertIsNone(result)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_none_rates_excluded(self, _key):
        """Exchanges with None rates should be excluded from average."""
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", 0.01, 0.01, 8),
            ("OKX", None, None, 8),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")

        self.assertIsNotNone(result)
        # Average should only include Binance (0.01 per 8h)
        self.assertAlmostEqual(
            result["rate_8h_equivalent"], 0.01, places=6)
        self.assertEqual(result["num_exchanges"], 1)

    @patch("coinglass.tools.funding_rate._get_api_key", return_value="test")
    def test_all_none_rates_returns_none(self, _key):
        """If all rates are None, should return None."""
        resp = MagicMock()
        resp.json.return_value = _make_funding_response([
            ("Binance", None, None, 8),
            ("OKX", None, None, 4),
        ])
        resp.raise_for_status = MagicMock()
        http_mod.proxied_get.return_value = resp

        result = get_symbol_funding_rate("BTC")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
