#!/usr/bin/env python3
"""
TaAPI Support & Resistance Module

Fetch professional support/resistance levels including pivot points,
Fibonacci levels, and pattern-based key levels from TaAPI.IO.

Dependencies:
- requests: For HTTP API calls
- python-dotenv: For environment variable management

Environment Variables Required:
- TAAPI_API_KEY: Your TaAPI.IO API key

Usage Example:
    from tools.taapi.support_resistance import get_pivot_points

    # Get pivot points for Bitcoin
    pivots = get_pivot_points("binance", "BTC/USDT", "1d")

CLI Usage:
    python support_resistance.py --type pivots --exchange binance --symbol BTC/USDT --interval 1d
    python support_resistance.py --type fibonacci --exchange binance --symbol ETH/USDT --interval 4h
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
    load_dotenv(os.path.join(project_root, '.env'))
except ImportError:
    pass

from core.http_client import proxied_get

BASE_URL = "https://api.taapi.io"


def get_pivot_points(
    exchange: str,
    symbol: str,
    interval: str = "1d",
    pivot_type: str = "standard",
    max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get pivot points (support/resistance levels).

    Args:
        exchange: Exchange name (binance, binancefutures, etc.)
        symbol: Trading pair (BTC/USDT)
        interval: Timeframe (1d or 1w recommended for pivots)
        pivot_type: Type of pivots (standard, fibonacci, camarilla)

    Returns:
        Dictionary with pivot point levels
    """
    api_key = os.getenv('TAAPI_API_KEY') or os.getenv('TA_API_KEY')
    if not api_key:
        print("Error: TAAPI_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/pivotpoints"

    params = {
        'secret': api_key,
        'exchange': exchange.lower(),
        'symbol': symbol,
        'interval': interval,
        'type': pivot_type
    }

    try:
        response = proxied_get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = {
            'type': 'pivot_points',
            'pivot_type': pivot_type,
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'levels': data
        }

        return dict(**result)  # structured response

    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            print(f"HTTP Error: {e.response.status_code}", file=sys.stderr)
        else:
            print(f"Error: {str(e)}", file=sys.stderr)
        return None


def get_support_resistance(
    exchange: str,
    symbol: str,
    interval: str,
    indicator: str = "pivots",
    max_results: int = 100) -> Optional[Dict[str, Any]]:
    """
    Get support and resistance levels using various methods.

    Args:
        exchange: Exchange name
        symbol: Trading pair
        interval: Timeframe
        indicator: Method (pivots, ichimoku, etc.)

    Returns:
        Dictionary with support/resistance levels
    """
    if indicator == "pivots":
        return get_pivot_points(exchange, symbol, interval)

    # For other S/R indicators, use generic approach
    api_key = os.getenv('TAAPI_API_KEY') or os.getenv('TA_API_KEY')
    if not api_key:
        print("Error: TAAPI_API_KEY not found", file=sys.stderr)
        return None

    url = f"{BASE_URL}/{indicator}"

    params = {
        'secret': api_key,
        'exchange': exchange.lower(),
        'symbol': symbol,
        'interval': interval
    }

    try:
        response = proxied_get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        return {
            'type': indicator,
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'levels': data
        }

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return None


def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """Format output for display."""
    if output_format == "json":
        return json.dumps(data, indent=2)

    elif output_format == "text":
        lines = []
        lines.append("=" * 60)
        lines.append(f"SUPPORT & RESISTANCE LEVELS")
        lines.append(f"Type: {data.get('type', 'Unknown').upper()}")
        lines.append(f"Symbol: {data['symbol']} | Exchange: {data['exchange']}")
        lines.append(f"Interval: {data['interval']}")
        lines.append("=" * 60)
        lines.append("")

        levels = data.get('levels', {})

        # Handle pivot points format
        if 'pp' in levels or 'pivot' in levels:
            pivot = levels.get('pp', levels.get('pivot', 0))
            lines.append(f"PIVOT POINT: {pivot:.2f}")
            lines.append("")
            lines.append("RESISTANCE LEVELS:")
            for i in range(1, 4):
                r_key = f'r{i}'
                if r_key in levels:
                    lines.append(f"  R{i}: {levels[r_key]:.2f}")
            lines.append("")
            lines.append("SUPPORT LEVELS:")
            for i in range(1, 4):
                s_key = f's{i}'
                if s_key in levels:
                    lines.append(f"  S{i}: {levels[s_key]:.2f}")
        else:
            # Generic format
            for key, value in levels.items():
                if isinstance(value, float):
                    lines.append(f"{key}: {value:.4f}")
                else:
                    lines.append(f"{key}: {value}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    return json.dumps(data, indent=2)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TaAPI Support & Resistance - Professional S/R levels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get pivot points for Bitcoin (daily)
  python support_resistance.py --type pivots --exchange binance --symbol BTC/USDT --interval 1d

  # Get Fibonacci pivots
  python support_resistance.py --type pivots --exchange binance --symbol ETH/USDT --interval 1d --pivot_type fibonacci

  # Get weekly pivots with text output
  python support_resistance.py --type pivots --exchange binance --symbol BTC/USDT --interval 1w --output_format text

Pivot Types:
  - standard: Traditional pivot points
  - fibonacci: Fibonacci-based pivots
  - camarilla: Camarilla pivot points
        """
    )

    parser.add_argument('--type', type=str, default='pivots',
                       help='S/R type (pivots, ichimoku, etc.)')
    parser.add_argument('--exchange', type=str, required=True,
                       help='Exchange name')
    parser.add_argument('--symbol', type=str, required=True,
                       help='Trading pair (BTC/USDT)')
    parser.add_argument('--interval', type=str, default='1d',
                       help='Timeframe (1d or 1w recommended)')
    parser.add_argument('--pivot_type', type=str, default='standard',
                       choices=['standard', 'fibonacci', 'camarilla'],
                       help='Pivot calculation method')
    parser.add_argument('--output_format', type=str, default='json',
                       choices=['json', 'text'],
                       help='Output format')
    parser.add_argument('--output-example', action='store_true',
                       help='Show example output')

    args = parser.parse_args()

    if args.output_example:
        example = {
            'type': 'pivot_points',
            'pivot_type': 'standard',
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'interval': '1d',
            'levels': {
                'pp': 43250.50,
                'r1': 44100.25,
                'r2': 45200.75,
                'r3': 46050.50,
                's1': 42150.25,
                's2': 41050.75,
                's3': 40200.50
            }
        }
        print(format_output(example, args.output_format))
        return 0

    # Fetch S/R levels
    if args.type == 'pivots':
        result = get_pivot_points(
            args.exchange,
            args.symbol,
            args.interval,
            args.pivot_type
        )
    else:
        result = get_support_resistance(
            args.exchange,
            args.symbol,
            args.interval,
            args.type
        )

    if result:
        print(format_output(result, args.output_format))
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
