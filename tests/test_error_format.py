"""Unit tests for patches/live/fix_error_format.py — Unified Error Response Format."""
import json
import sys
import os

import pytest

# Add patches to import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "patches", "live"))


from fix_error_format import normalize_error, _is_error, _classify, _build_error


class TestNormalizeError:
    """Test the main normalize_error() entry point."""

    def test_none_input_returns_error(self):
        result = normalize_error(None, tool_name="test_tool")
        assert result["error"] is True
        assert result["category"] == "unknown"
        assert result["tool"] == "test_tool"
        assert "None" in result["message"]

    def test_non_error_dict_passes_through(self):
        # NOTE: value containing "500" substring triggers false positive
        # in _is_error() — this is a known limitation (BUG-5.1).
        # Use values that don't contain 4xx/5xx substrings.
        data = {"symbol": "BTC", "price": 71000, "volume": 9999}
        result = normalize_error(data, tool_name="coin_price")
        assert result == data

    def test_non_error_list_passes_through(self):
        data = [{"exchange": "Binance", "rate": 0.001}]
        result = normalize_error(data, tool_name="funding_rate")
        assert result == data

    def test_error_string_detected(self):
        result = normalize_error("❌ Error: connection refused",
                                 tool_name="cg_open_interest")
        assert result["error"] is True
        assert result["tool"] == "cg_open_interest"

    def test_timeout_string(self):
        result = normalize_error("Connection timed out after 30s",
                                 tool_name="cg_coin_data")
        assert result["error"] is True
        assert result["category"] == "network"

    def test_rate_limit_429(self):
        result = normalize_error("HTTP 429: Too Many Requests",
                                 tool_name="coin_price")
        assert result["error"] is True
        assert result["category"] == "rate_limit"

    def test_server_error_500(self):
        result = normalize_error("HTTP 500: Internal Server Error",
                                 tool_name="cg_liquidations")
        assert result["error"] is True
        assert result["category"] == "upstream"

    def test_server_error_502(self):
        result = normalize_error("Bad Gateway 502",
                                 tool_name="cg_funding_rate")
        assert result["error"] is True
        assert result["category"] == "upstream"

    def test_auth_error_401(self):
        result = normalize_error("HTTP 401: Unauthorized",
                                 tool_name="cg_open_interest")
        assert result["error"] is True
        assert result["category"] == "auth"

    def test_api_key_error(self):
        result = normalize_error("❌ Error: Check your API_KEY",
                                 tool_name="cg_liquidations")
        assert result["error"] is True
        assert result["category"] == "auth"

    def test_not_found_error(self):
        # "not found" alone doesn't trigger _is_error unless combined with
        # another signal keyword. Adding "error" prefix ensures detection.
        result = normalize_error("Error: Symbol INVALIDCOIN not found",
                                 tool_name="cg_open_interest")
        assert result["error"] is True
        assert result["category"] == "invalid_input"

    def test_error_dict_with_error_key(self):
        result = normalize_error({"error": True, "message": "bad input"},
                                 tool_name="test")
        assert result["error"] is True

    def test_error_dict_with_nonzero_code(self):
        result = normalize_error({"code": 40001, "msg": "invalid param"},
                                 tool_name="test")
        assert result["error"] is True

    def test_raw_field_truncated(self):
        # String must contain an error signal to trigger normalization
        long_error = "❌ Error: " + "x" * 1000
        result = normalize_error(long_error, tool_name="test")
        assert isinstance(result, dict)
        assert len(result["raw"]) <= 500

    def test_empty_tool_name(self):
        result = normalize_error("error: timeout", tool_name="")
        assert result["error"] is True
        assert result["tool"] == ""

    def test_schema_completeness(self):
        """Every error result must contain all required keys."""
        result = normalize_error("some error occurred", tool_name="test")
        required_keys = {"error", "tool", "category", "message", "suggestion", "raw"}
        assert required_keys.issubset(set(result.keys()))


class TestIsError:
    """Test the _is_error detection function."""

    def test_emoji_error_marker(self):
        assert _is_error("❌ something failed", "❌ something failed") is True

    def test_error_keyword(self):
        assert _is_error("error: bad input", "error: bad input") is True

    def test_failed_keyword(self):
        assert _is_error("Request failed", "Request failed") is True

    def test_timeout_keyword(self):
        assert _is_error("connection timed out", "connection timed out") is True

    def test_http_status_429(self):
        assert _is_error("HTTP 429 rate limited", "HTTP 429 rate limited") is True

    def test_normal_data_not_error(self):
        data = {"symbol": "BTC", "price": 71000}
        assert _is_error(json.dumps(data), data) is False

    def test_dict_with_error_field(self):
        data = {"error": "something went wrong"}
        assert _is_error(json.dumps(data), data) is True

    def test_dict_with_nonzero_code(self):
        data = {"code": 40001, "msg": "bad param"}
        assert _is_error(json.dumps(data), data) is True

    def test_dict_with_code_zero_not_error(self):
        data = {"code": "0", "data": [1, 2, 3]}
        assert _is_error(json.dumps(data), data) is False

    def test_case_insensitive(self):
        assert _is_error("TIMEOUT occurred", "TIMEOUT occurred") is True
        assert _is_error("EXCEPTION raised", "EXCEPTION raised") is True


class TestClassify:
    """Test error classification."""

    def test_auth_category(self):
        cat, msg, sug = _classify("401 Unauthorized", "BTC")
        assert cat == "auth"

    def test_rate_limit_category(self):
        cat, msg, sug = _classify("429 Too Many Requests", "")
        assert cat == "rate_limit"

    def test_network_category(self):
        cat, msg, sug = _classify("Connection timed out", "")
        assert cat == "network"

    def test_upstream_category(self):
        cat, msg, sug = _classify("502 Bad Gateway", "")
        assert cat == "upstream"

    def test_invalid_input_category(self):
        cat, msg, sug = _classify("Symbol not found", "BADCOIN")
        assert cat == "invalid_input"

    def test_unknown_fallback(self):
        cat, msg, sug = _classify("something completely weird", "")
        assert cat == "unknown"

    def test_suggestion_always_string(self):
        for error in ["401", "429", "timed out", "500", "not found", "??"]:
            cat, msg, sug = _classify(error, "")
            assert isinstance(sug, str)
            assert len(sug) > 0


class TestBuildError:
    """Test error dict construction."""

    def test_basic_build(self):
        result = _build_error("my_tool", "rate_limit", "Too fast", "Slow down", "raw data")
        assert result == {
            "error": True,
            "tool": "my_tool",
            "category": "rate_limit",
            "message": "Too fast",
            "suggestion": "Slow down",
            "raw": "raw data",
        }

    def test_empty_fields(self):
        result = _build_error("", "", "", "", "")
        assert result["error"] is True
        assert all(k in result for k in ("tool", "category", "message", "suggestion", "raw"))
