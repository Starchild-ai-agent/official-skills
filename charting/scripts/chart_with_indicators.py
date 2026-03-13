#!/usr/bin/env python3
"""Generate TradingView-style candlestick chart with technical indicators.

Includes: RSI, MACD, Bollinger Bands, EMA/SMA overlays.
Usage: Copy to scripts/, enable the indicators you want in Config, run with:
    python3 scripts/my_chart.py
"""
import os
import sys
import requests
import pandas as pd
import numpy as np
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
DAYS = 90
INTERVAL = None  # None for auto-select, or "daily"/"hourly"
OUTPUT_FILE = "output/btc_90d_indicators.png"

# Toggle indicators (set True/False)
SHOW_EMA = True       # EMA 20 overlay on candles
SHOW_SMA = True       # SMA 50 overlay on candles
SHOW_BBANDS = False   # Bollinger Bands overlay on candles
SHOW_RSI = True       # RSI subplot
SHOW_MACD = True      # MACD subplot

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
# Indicator Calculations
# ============================================================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

# ============================================================
# Build Addplots
# ============================================================
addplots = []
# Track how many subplots we need (panel 1 is reserved for volume if used)
next_panel = 2

# Overlay indicators (on main chart, panel 0)
if SHOW_EMA:
    df["EMA_20"] = df["Close"].ewm(span=20).mean()
    addplots.append(mpf.make_addplot(df["EMA_20"], color='#2196f3', width=1.0))

if SHOW_SMA:
    df["SMA_50"] = df["Close"].rolling(window=50).mean()
    addplots.append(mpf.make_addplot(df["SMA_50"], color='#ff9800', width=1.0))

if SHOW_BBANDS:
    period = 20
    df["BB_Mid"] = df["Close"].rolling(window=period).mean()
    df["BB_Upper"] = df["BB_Mid"] + 2 * df["Close"].rolling(window=period).std()
    df["BB_Lower"] = df["BB_Mid"] - 2 * df["Close"].rolling(window=period).std()
    addplots.append(mpf.make_addplot(df["BB_Mid"], color='#ff9800', width=0.8))
    addplots.append(mpf.make_addplot(df["BB_Upper"], color='#78909c', width=0.6, linestyle='--'))
    addplots.append(mpf.make_addplot(df["BB_Lower"], color='#78909c', width=0.6, linestyle='--'))

# Subplot indicators
panel_ratios = [4, 1]  # Main chart + volume placeholder

if SHOW_RSI:
    df["RSI"] = calc_rsi(df["Close"])
    addplots.append(mpf.make_addplot(df["RSI"], panel=next_panel, color='#b39ddb',
                                      ylabel='RSI', ylim=(0, 100), secondary_y=False))
    addplots.append(mpf.make_addplot([70] * len(df), panel=next_panel, color='#ef5350',
                                      linestyle='--', secondary_y=False, width=0.7))
    addplots.append(mpf.make_addplot([30] * len(df), panel=next_panel, color='#26a69a',
                                      linestyle='--', secondary_y=False, width=0.7))
    panel_ratios.append(2)
    next_panel += 1

if SHOW_MACD:
    df["MACD"], df["Signal"], df["Hist"] = calc_macd(df["Close"])
    hist_colors = ['#26a69a' if v >= 0 else '#ef5350' for v in df["Hist"]]
    addplots.append(mpf.make_addplot(df["MACD"], panel=next_panel, color='#2196f3',
                                      ylabel='MACD', secondary_y=False))
    addplots.append(mpf.make_addplot(df["Signal"], panel=next_panel, color='#ff9800',
                                      secondary_y=False))
    addplots.append(mpf.make_addplot(df["Hist"], panel=next_panel, type='bar',
                                      color=hist_colors, secondary_y=False, width=0.7))
    panel_ratios.append(2)
    next_panel += 1

# ============================================================
# Plot
# ============================================================
os.makedirs("output", exist_ok=True)

# Adjust figure height based on number of panels
fig_height = 8 + 2 * (next_panel - 2)

mpf.plot(
    df, type='candle', style=style, volume=False,
    title=f'\n{COIN_ID.upper()} — {DAYS}D Technical Analysis',
    addplot=addplots if addplots else None,
    panel_ratios=tuple(panel_ratios),
    figsize=(14, fig_height),
    savefig=dict(fname=OUTPUT_FILE, dpi=150, bbox_inches='tight',
                 facecolor='#131722', edgecolor='#131722'),
)

print(f"Chart saved: {OUTPUT_FILE}")
