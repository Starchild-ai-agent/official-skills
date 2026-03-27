#!/usr/bin/env python3
"""
TaAPI Indicators Module

Fetch pre-calculated technical analysis indicators from TaAPI.IO including
RSI, MACD, Bollinger Bands, Moving Averages, and 200+ other indicators.

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- TAAPI_API_KEY: Your TaAPI.IO API key (get free key at taapi.io)

Usage Example:
    from tools.taapi.indicators import get_indicator

    # Get RSI for Bitcoin
    rsi = get_indicator("rsi", exchange="binance", symbol="BTC/USDT", interval="1h")

    # Get MACD
    macd = get_indicator("macd", exchange="binance", symbol="BTC/USDT", interval="4h")

CLI Usage:
    python indicators.py --indicator rsi --exchange binance --symbol BTC/USDT --interval 1h
    python indicators.py --indicator macd --exchange binance --symbol ETH/USDT --interval 4h
    python indicators.py --indicator bbands --exchange binance --symbol BTC/USDT --interval 1d
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional, List

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

from core.http_client import proxied_get, proxied_post

# TaAPI Configuration
BASE_URL = "https://api.taapi.io"

# Supported indicators
INDICATORS = [
    "rsi", "macd", "bbands", "ema", "sma", "stoch", "adx", "cci", "roc",
    "willr", "atr", "obv", "mfi", "ao", "kc", "dmi", "ichimoku", "psar"
]

# Supported exchanges
EXCHANGES = ["binance", "binancefutures", "bitstamp", "gateio", "bybit", "okex"]

# Supported intervals
INTERVALS = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "12h", "1d", "1w"]


def get_indicator(
    indicator: str,
    exchange: str,
    symbol: str,
    interval: str,
    backtrack: int = 0,
    backtracks: Optional[int] = None,
    max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Fetch pre-calculated indicator from TaAPI.

    Args:
        indicator: Indicator name (rsi, macd, bbands, etc.)
        exchange: Exchange name (binance, binancefutures, etc.)
        symbol: Trading pair in COIN/MARKET format (BTC/USDT)
        interval: Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w)
        backtrack: Number of candles to backtrack (0 = latest)
        backtracks: Number of historical values to return

    Returns:
        Dictionary with indicator values or None if request fails
    """
    api_key = os.getenv('TAAPI_API_KEY') or os.getenv('TA_API_KEY')
    if not api_key:
        print("Error: TAAPI_API_KEY not found in environment variables", file=sys.stderr)
        return None

    # Validate inputs
    if indicator.lower() not in INDICATORS:
        print(f"Warning: {indicator} not in common indicators list", file=sys.stderr)

    # Build request URL
    url = f"{BASE_URL}/{indicator.lower()}"

    params = {
        'secret': api_key,
        'exchange': exchange.lower(),
        'symbol': symbol,
        'interval': interval
    }

    if backtrack > 0:
        params['backtrack'] = backtrack

    if backtracks is not None and backtracks > 0:
        params['backtracks'] = backtracks

    try:
        response = proxied_get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Add metadata
        result = {
            'indicator': indicator,
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'values': data
        }

        return dict(**result)  # structured response

    except Exception as e:
        # Handle HTTP errors
        if hasattr(e, 'response') and e.response is not None:
            status = e.response.status_code
            if status == 401:
                print("Error: Invalid API key", file=sys.stderr)
            elif status == 429:
                print("Error: Rate limit exceeded", file=sys.stderr)
            else:
                print(f"HTTP Error: {status} - {e.response.text}", file=sys.stderr)
        else:
            print(f"Request Error: {str(e)}", file=sys.stderr)
        return None


def get_multiple_indicators(
    indicators: List[str],
    exchange: str,
    symbol: str,
    interval: str,
    max_results: int = 100) -> Dict[str, Any]:
    """
    Fetch multiple indicators at once (sequential - use bulk_indicators for faster).

    Args:
        indicators: List of indicator names
        exchange: Exchange name
        symbol: Trading pair
        interval: Timeframe

    Returns:
        Dictionary with all indicator values
    """
    results = {}

    for indicator in indicators:
        data = get_indicator(indicator, exchange, symbol, interval)
        if data:
            results[indicator] = data['values']

    return results


def bulk_indicators(
    indicators: List[Dict[str, Any]],
    exchange: str,
    symbol: str,
    interval: str,
    max_results: int = 100) -> Dict[str, Any]:
    """
    Fetch up to 20 indicators in ONE API request using TaAPI bulk endpoint.

    This is MUCH faster than individual calls - 1 request instead of N requests.

    Args:
        indicators: List of indicator configs, each can have:
                   - {"indicator": "rsi"}
                   - {"indicator": "macd"}
                   - {"indicator": "ema", "period": 50}
                   - {"id": "custom_id", "indicator": "rsi", "backtrack": 1}
        exchange: Exchange name (binance, binancefutures, etc.)
        symbol: Trading pair (BTC/USDT)
        interval: Timeframe (1h, 4h, 1d, etc.)

    Returns:
        Dictionary with all indicator results keyed by indicator name or custom id

    Example:
        result = bulk_indicators(
            [{"indicator": "rsi"}, {"indicator": "macd"}, {"indicator": "bbands"}],
            "binance", "BTC/USDT", "4h"
        )
    """
    api_key = os.getenv('TAAPI_API_KEY') or os.getenv('TA_API_KEY')
    if not api_key:
        print("Error: TAAPI_API_KEY not found in environment variables", file=sys.stderr)
        return {}

    if len(indicators) > 20:
        print("Warning: Maximum 20 indicators per bulk request. Truncating.", file=sys.stderr)
        indicators = indicators[:20]

    # Build bulk request payload
    payload = {
        "secret": api_key,
        "construct": {
            "exchange": exchange.lower(),
            "symbol": symbol,
            "interval": interval,
            "indicators": indicators
        }
    }

    try:
        response = proxied_post(
            f"{BASE_URL}/bulk",
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()

        # Parse response - TaAPI returns {"data": [...]}
        results = {}
        if "data" in data:
            for item in data["data"]:
                # Get indicator name from the response
                indicator_name = item.get("indicator", "unknown")

                # Check for errors
                if item.get("errors") and len(item["errors"]) > 0:
                    results[indicator_name] = {"error": item["errors"]}
                else:
                    # Store the result values directly
                    results[indicator_name] = item.get("result", {})

        return {
            "exchange": exchange,
            "symbol": symbol,
            "interval": interval,
            "indicators": results
        }

    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        else:
            print(f"Error: {str(e)}", file=sys.stderr)
        return {}


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """Format output for display.

    Formats:
        json: Full JSON with metadata (default)
        concise: Minimal key=value pairs, optimized for agent consumption
        text: Human-readable formatted text
    """
    if output_format == "json":
        return json.dumps(data, indent=2)

    elif output_format == "concise":
        # Token-efficient format for agents (per Anthropic best practices)
        parts = []
        if 'indicators' in data:
            # Bulk mode response
            for ind_name, ind_data in data['indicators'].items():
                if isinstance(ind_data, dict):
                    vals = [f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                            for k, v in ind_data.items() if not k.startswith('error')]
                    parts.append(f"{ind_name}:{','.join(vals)}")
            return f"{data.get('symbol','?')}@{data.get('interval','?')}|" + "|".join(parts)
        elif 'values' in data:
            # Single indicator response
            values = data['values']
            if isinstance(values, dict):
                vals = [f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                        for k, v in values.items()]
                return f"{data.get('indicator','?')}@{data.get('symbol','?')}@{data.get('interval','?')}:{','.join(vals)}"
            else:
                return f"{data.get('indicator','?')}={values}"
        return str(data)

    elif output_format == "text":
        lines = []
        lines.append("=" * 60)
        lines.append(f"INDICATOR: {data['indicator'].upper()}")
        lines.append(f"Symbol: {data['symbol']} | Exchange: {data['exchange']}")
        lines.append(f"Interval: {data['interval']}")
        lines.append("=" * 60)
        lines.append("")

        values = data['values']

        if isinstance(values, dict):
            for key, value in values.items():
                if isinstance(value, float):
                    lines.append(f"{key}: {value:.4f}")
                else:
                    lines.append(f"{key}: {value}")
        elif isinstance(values, list):
            for i, val in enumerate(values):
                lines.append(f"[{i}]: {val}")
        else:
            lines.append(f"Value: {values}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    return json.dumps(data, indent=2)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TaAPI Indicators - Pre-calculated technical indicators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Get RSI for Bitcoin
  python indicators.py --indicator rsi --exchange binance --symbol BTC/USDT --interval 1h

  # Get MACD for Ethereum
  python indicators.py --indicator macd --exchange binance --symbol ETH/USDT --interval 4h

  # BULK MODE - Get multiple indicators in ONE request (FAST!)
  python indicators.py --bulk --indicators rsi,macd,bbands --exchange binance --symbol BTC/USDT --interval 4h

  # Bulk with pivots
  python indicators.py --bulk --indicators rsi,macd,bbands,ema,sma --exchange binance --symbol BTC/USDT --interval 1d

  # Get Bollinger Bands with text output
  python indicators.py --indicator bbands --exchange binance --symbol BTC/USDT --interval 1d --output_format text

  # Get historical values (last 10 candles)
  python indicators.py --indicator rsi --exchange binance --symbol BTC/USDT --interval 1h --backtracks 10

Supported Indicators:
  {', '.join(INDICATORS[:10])}
  ... and 200+ more at taapi.io/indicators/

Supported Exchanges:
  {', '.join(EXCHANGES)}

Supported Intervals:
  {', '.join(INTERVALS)}
        """
    )

    parser.add_argument('--indicator', type=str,
                       help='Single indicator name (rsi, macd, bbands, etc.)')
    parser.add_argument('--bulk', action='store_true',
                       help='Use bulk mode to fetch multiple indicators in ONE request')
    parser.add_argument('--indicators', type=str,
                       help='Comma-separated indicators for bulk mode (e.g., rsi,macd,bbands)')
    parser.add_argument('--exchange', type=str, required=True,
                       help='Exchange name (binance, binancefutures, etc.)')
    parser.add_argument('--symbol', type=str, required=True,
                       help='Trading pair (BTC/USDT, ETH/USDT, etc.)')
    parser.add_argument('--interval', type=str, required=True,
                       help='Timeframe (1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w)')
    parser.add_argument('--backtrack', type=int, default=0,
                       help='Candles to backtrack (0 = latest)')
    parser.add_argument('--backtracks', type=int,
                       help='Number of historical values to return')
    parser.add_argument('--output_format', type=str, default='json',
                       choices=['json', 'concise', 'text'],
                       help='Output format (concise=token-efficient for agents)')
    parser.add_argument('--output-example', action='store_true',
                       help='Show example output')

    args = parser.parse_args()

    if args.output_example:
        example = {
            'indicator': 'rsi',
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'interval': '1h',
            'values': {'value': 65.3421}
        }
        print(format_output(example, args.output_format))
        return 0

    # BULK MODE - fetch multiple indicators in ONE request
    if args.bulk:
        if not args.indicators:
            print("Error: --indicators required for bulk mode (e.g., --indicators rsi,macd,bbands)", file=sys.stderr)
            return 1

        indicator_list = [{"indicator": ind.strip()} for ind in args.indicators.split(",")]
        result = bulk_indicators(indicator_list, args.exchange, args.symbol, args.interval)

        if result:
            print(format_output(result, args.output_format))
            return 0
        else:
            return 1

    # SINGLE INDICATOR MODE
    if not args.indicator:
        print("Error: --indicator required (or use --bulk with --indicators)", file=sys.stderr)
        return 1

    result = get_indicator(
        args.indicator,
        args.exchange,
        args.symbol,
        args.interval,
        args.backtrack,
        args.backtracks
    )

    if result:
        print(format_output(result, args.output_format))
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
