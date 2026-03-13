#!/usr/bin/env python3
"""Generate TradingView-style candlestick chart for stocks, forex, or commodities using Twelve Data.

Usage: Copy to scripts/, customize the Config section, run with:
    python3 scripts/my_stock_chart.py
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
SYMBOL = "AAPL"  # Stock (AAPL, MSFT, TSLA), Forex (EUR/USD), or Commodity (XAU/USD for gold)
DAYS = 30
INTERVAL = None  # None for auto-select, or "1h", "1day", etc.
OUTPUT_FILE = "output/aapl_30d_chart.png"

# ============================================================
# Smart Interval Selection
# ============================================================
def select_interval(days):
    """Auto-select optimal interval based on time range."""
    if days <= 31:
        return "1h"  # Hourly for short term
    else:
        return "1day"  # Daily for longer periods

if INTERVAL is None:
    INTERVAL = select_interval(DAYS)

# ============================================================
# Fetch OHLC from Twelve Data with Error Handling
# ============================================================
API_KEY = os.getenv("TWELVEDATA_API_KEY")
if not API_KEY:
    print("ERROR: TWELVEDATA_API_KEY not set", file=sys.stderr)
    sys.exit(1)

# Calculate outputsize
if INTERVAL == "1h":
    outputsize = DAYS * 24
else:  # daily or longer
    outputsize = DAYS

outputsize = min(outputsize, 5000)  # Max 5000 points

url = "https://api.twelvedata.com/time_series"
params = {
    "symbol": SYMBOL,
    "interval": INTERVAL,
    "outputsize": outputsize,
    "apikey": API_KEY
}

# Retry logic with exponential backoff
raw = None
for attempt in range(3):
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Check for API errors
        if "status" in data and data["status"] == "error":
            raise ValueError(f"Twelve Data API Error: {data.get('message', 'Unknown error')}")

        # Validate response
        if "values" not in data or len(data["values"]) == 0:
            raise ValueError("Empty or invalid data received from API")

        raw = data["values"]
        break  # Success
    except Exception as e:
        if attempt == 2:  # Last attempt
            print(f"ERROR: Failed to fetch data after 3 attempts: {e}", file=sys.stderr)
            sys.exit(1)
        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s

# ============================================================
# Build DataFrame
# ============================================================
# IMPORTANT: Twelve Data returns newest first, so reverse the list
raw = raw[::-1]

df = pd.DataFrame(raw)
df["Date"] = pd.to_datetime(df["datetime"])
df.set_index("Date", inplace=True)

# Convert to float and rename columns
df = df[["open", "high", "low", "close"]].astype(float)
df.columns = ["Open", "High", "Low", "Close"]

# Optional: Add volume if available (Twelve Data includes volume for stocks)
if "volume" in raw[0]:
    df["Volume"] = [float(x["volume"]) for x in raw]

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

# Display volume if available
show_volume = "Volume" in df.columns

mpf.plot(
    df, type='candle', style=style, volume=show_volume,
    title=f'\n{SYMBOL} — {DAYS}D Candlestick',
    figsize=(14, 8),
    savefig=dict(fname=OUTPUT_FILE, dpi=150, bbox_inches='tight',
                 facecolor='#131722', edgecolor='#131722'),
)

print(f"Chart saved: {OUTPUT_FILE}")
