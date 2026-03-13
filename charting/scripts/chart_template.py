#!/usr/bin/env python3
"""Generate TradingView-style candlestick chart.

Usage: Copy to scripts/, customize the Config section, run with:
    python3 scripts/my_chart.py
"""
import os
import sys
import requests
import pandas as pd
import mplfinance as mpf
import time

# ============================================================
# Proxy Auto-Configuration (for deployed environments)
# ============================================================
if not os.getenv("HTTP_PROXY") and os.getenv("PROXY_HOST"):
    host = os.getenv("PROXY_HOST")
    port = os.getenv("PROXY_PORT", "8080")
    # Handle IPv6 addresses
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    proxy_url = f"http://{host}:{port}"
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url

# ============================================================
# Config — customize these for each chart
# ============================================================
COIN_ID = "bitcoin"
DAYS = 30
INTERVAL = None  # None for auto-select, or "daily"/"hourly"
OUTPUT_FILE = "output/btc_30d_chart.png"

# ============================================================
# Smart Interval Selection
# ============================================================
def select_interval(days):
    """Auto-select optimal interval based on time range."""
    if days <= 31:
        return "hourly"  # Max granularity for short term
    else:
        return "daily"   # Efficient for longer periods

if INTERVAL is None:
    INTERVAL = select_interval(DAYS)

# ============================================================
# Fetch OHLC from CoinGecko with Error Handling
# ============================================================
API_KEY = os.getenv("COINGECKO_API_KEY")
if not API_KEY:
    print("ERROR: COINGECKO_API_KEY not set", file=sys.stderr)
    sys.exit(1)

now = int(time.time())
from_ts = now - (DAYS * 86400)

url = f"https://pro-api.coingecko.com/api/v3/coins/{COIN_ID}/ohlc/range"
params = {"vs_currency": "usd", "from": from_ts, "to": now, "interval": INTERVAL}
headers = {"x-cg-pro-api-key": API_KEY}

# Retry logic with exponential backoff
raw = None
for attempt in range(3):
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        # Validate response
        if not isinstance(raw, list) or len(raw) == 0:
            raise ValueError("Empty or invalid data received from API")

        # Validate data format
        if not all(isinstance(item, list) and len(item) == 5 for item in raw):
            raise ValueError("Invalid OHLC data format")

        break  # Success
    except Exception as e:
        if attempt == 2:  # Last attempt
            print(f"ERROR: Failed to fetch data after 3 attempts: {e}", file=sys.stderr)
            sys.exit(1)
        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s

# ============================================================
# Build DataFrame
# ============================================================
df = pd.DataFrame(raw, columns=["Timestamp", "Open", "High", "Low", "Close"])
df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms")
df.set_index("Date", inplace=True)
df.drop(columns=["Timestamp"], inplace=True)

# ============================================================
# TradingView Style
# ============================================================
mc = mpf.make_marketcolors(
    up='#26a69a', down='#ef5350',
    edge='inherit', wick='inherit', volume='inherit', ohlc='inherit',
)
style = mpf.make_mpf_style(
    marketcolors=mc,
    facecolor='#131722', edgecolor='#131722', figcolor='#131722',
    gridcolor='#1e222d', gridstyle='--', y_on_right=True,
    rc={'axes.labelcolor': '#d1d4dc', 'xtick.color': '#d1d4dc',
        'ytick.color': '#d1d4dc', 'font.size': 10},
)

# ============================================================
# Plot
# ============================================================
os.makedirs("output", exist_ok=True)

mpf.plot(
    df, type='candle', style=style, volume=False,
    title=f'\n{COIN_ID.upper()} — {DAYS}D Candlestick',
    figsize=(14, 8),
    savefig=dict(fname=OUTPUT_FILE, dpi=150, bbox_inches='tight',
                 facecolor='#131722', edgecolor='#131722'),
)

print(f"Chart saved: {OUTPUT_FILE}")
