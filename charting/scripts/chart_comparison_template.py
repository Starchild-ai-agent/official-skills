#!/usr/bin/env python3
"""Compare two assets (crypto vs commodity, stock vs crypto, etc.) with multiple visualization modes.

Supports three comparison modes:
1. Normalized to 100 - Both assets start at 100, shows relative performance
2. Dual-axis - Actual prices on separate Y axes
3. Percentage change - Shows +/- percentage from starting point

Usage: Copy to scripts/, customize the Config section, run with:
    python3 scripts/my_comparison.py
"""
import os
import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
# Config — customize these for each comparison
# ============================================================
# Asset 1 (Crypto via CoinGecko)
ASSET1_TYPE = "crypto"  # "crypto"
ASSET1_ID = "bitcoin"  # CoinGecko coin ID
ASSET1_LABEL = "BTC"
ASSET1_COLOR = "#f7931a"  # Bitcoin orange

# Asset 2 (Stock/Forex/Commodity via Twelve Data)
ASSET2_TYPE = "twelvedata"  # "twelvedata"
ASSET2_SYMBOL = "XAU/USD"  # Twelve Data symbol (XAU/USD for gold, AAPL for Apple, EUR/USD for forex)
ASSET2_LABEL = "Gold"
ASSET2_COLOR = "#ffd700"  # Gold color

# Time range
DAYS = 90

# Comparison mode: "normalized", "dual_axis", or "percentage"
COMPARISON_MODE = "normalized"

# Output
OUTPUT_FILE = "output/btc_vs_gold_comparison.png"

# ============================================================
# Fetch Asset 1 (Crypto from CoinGecko)
# ============================================================
def fetch_crypto_data(coin_id, days):
    """Fetch crypto OHLC data from CoinGecko."""
    api_key = os.getenv("COINGECKO_API_KEY")
    if not api_key:
        print("ERROR: COINGECKO_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    now = int(time.time())
    from_ts = now - (days * 86400)

    # Auto-select interval
    interval = "hourly" if days <= 31 else "daily"

    url = f"https://pro-api.coingecko.com/api/v3/coins/{coin_id}/ohlc/range"
    params = {"vs_currency": "usd", "from": from_ts, "to": now, "interval": interval}
    headers = {"x-cg-pro-api-key": api_key}

    # Retry logic
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            raw = resp.json()

            if not isinstance(raw, list) or len(raw) == 0:
                raise ValueError("Empty or invalid data received from CoinGecko")

            # Convert to DataFrame
            df = pd.DataFrame(raw, columns=["Timestamp", "Open", "High", "Low", "Close"])
            df["Date"] = pd.to_datetime(df["Timestamp"], unit="ms")
            df.set_index("Date", inplace=True)
            df.drop(columns=["Timestamp"], inplace=True)

            return df
        except Exception as e:
            if attempt == 2:
                print(f"ERROR: Failed to fetch {coin_id} data: {e}", file=sys.stderr)
                sys.exit(1)
            time.sleep(2 ** attempt)

# ============================================================
# Fetch Asset 2 (Stock/Forex/Commodity from Twelve Data)
# ============================================================
def fetch_twelvedata(symbol, days):
    """Fetch time series data from Twelve Data."""
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        print("ERROR: TWELVEDATA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Auto-select interval
    interval = "1h" if days <= 31 else "1day"

    # Calculate outputsize (Twelve Data returns newest first)
    outputsize = days * 24 if interval == "1h" else days
    outputsize = min(outputsize, 5000)  # Max 5000 points

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key
    }

    # Retry logic
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if "status" in data and data["status"] == "error":
                raise ValueError(f"Twelve Data API Error: {data.get('message', 'Unknown error')}")

            if "values" not in data or len(data["values"]) == 0:
                raise ValueError("Empty or invalid data received from Twelve Data")

            # Reverse data (Twelve Data returns newest first)
            values = data["values"][::-1]

            # Convert to DataFrame
            df = pd.DataFrame(values)
            df["Date"] = pd.to_datetime(df["datetime"])
            df.set_index("Date", inplace=True)
            df = df[["open", "high", "low", "close"]].astype(float)
            df.columns = ["Open", "High", "Low", "Close"]

            return df
        except Exception as e:
            if attempt == 2:
                print(f"ERROR: Failed to fetch {symbol} data: {e}", file=sys.stderr)
                sys.exit(1)
            time.sleep(2 ** attempt)

# ============================================================
# Fetch Data
# ============================================================
print(f"Fetching {ASSET1_LABEL} data...")
df1 = fetch_crypto_data(ASSET1_ID, DAYS)

print(f"Fetching {ASSET2_LABEL} data...")
df2 = fetch_twelvedata(ASSET2_SYMBOL, DAYS)

# Align dates (use Close prices for comparison)
df1_close = df1[["Close"]].rename(columns={"Close": ASSET1_LABEL})
df2_close = df2[["Close"]].rename(columns={"Close": ASSET2_LABEL})

# Merge on date index (inner join to get overlapping dates)
df = pd.merge(df1_close, df2_close, left_index=True, right_index=True, how="inner")

if len(df) == 0:
    print("ERROR: No overlapping data between assets", file=sys.stderr)
    sys.exit(1)

print(f"Comparing {len(df)} data points...")

# ============================================================
# TradingView Dark Theme
# ============================================================
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(14, 8))
fig.patch.set_facecolor('#131722')
ax.set_facecolor('#131722')

# Grid
ax.grid(color='#1e222d', linestyle='--', linewidth=0.5)

# ============================================================
# Plot Based on Comparison Mode
# ============================================================
if COMPARISON_MODE == "normalized":
    # Normalize both to 100 at start
    df_norm = df / df.iloc[0] * 100
    ax.plot(df_norm.index, df_norm[ASSET1_LABEL], color=ASSET1_COLOR, linewidth=2, label=ASSET1_LABEL)
    ax.plot(df_norm.index, df_norm[ASSET2_LABEL], color=ASSET2_COLOR, linewidth=2, label=ASSET2_LABEL)
    ax.set_ylabel("Normalized Value (Start = 100)", color='#d1d4dc', fontsize=12)
    ax.axhline(100, color='#d1d4dc', linestyle='--', linewidth=0.7, alpha=0.5)
    title = f"{ASSET1_LABEL} vs {ASSET2_LABEL} — Normalized Comparison ({DAYS}D)"

elif COMPARISON_MODE == "dual_axis":
    # Dual axis with actual prices
    ax.plot(df.index, df[ASSET1_LABEL], color=ASSET1_COLOR, linewidth=2, label=ASSET1_LABEL)
    ax.set_ylabel(f"{ASSET1_LABEL} Price (USD)", color=ASSET1_COLOR, fontsize=12)
    ax.tick_params(axis='y', labelcolor=ASSET1_COLOR)

    # Create second Y axis
    ax2 = ax.twinx()
    ax2.plot(df.index, df[ASSET2_LABEL], color=ASSET2_COLOR, linewidth=2, label=ASSET2_LABEL)
    ax2.set_ylabel(f"{ASSET2_LABEL} Price (USD)", color=ASSET2_COLOR, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=ASSET2_COLOR)
    ax2.set_facecolor('#131722')

    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
              facecolor='#131722', edgecolor='#1e222d', fontsize=10)

    title = f"{ASSET1_LABEL} vs {ASSET2_LABEL} — Dual-Axis Comparison ({DAYS}D)"

elif COMPARISON_MODE == "percentage":
    # Percentage change from start
    df_pct = (df / df.iloc[0] - 1) * 100
    ax.plot(df_pct.index, df_pct[ASSET1_LABEL], color=ASSET1_COLOR, linewidth=2, label=ASSET1_LABEL)
    ax.plot(df_pct.index, df_pct[ASSET2_LABEL], color=ASSET2_COLOR, linewidth=2, label=ASSET2_LABEL)
    ax.set_ylabel("Change from Start (%)", color='#d1d4dc', fontsize=12)
    ax.axhline(0, color='#d1d4dc', linestyle='--', linewidth=0.7, alpha=0.5)
    title = f"{ASSET1_LABEL} vs {ASSET2_LABEL} — Percentage Change ({DAYS}D)"

else:
    print(f"ERROR: Invalid COMPARISON_MODE '{COMPARISON_MODE}'. Use 'normalized', 'dual_axis', or 'percentage'.", file=sys.stderr)
    sys.exit(1)

# ============================================================
# Styling
# ============================================================
ax.set_title(f"\n{title}", color='#d1d4dc', fontsize=14, fontweight='bold')
ax.set_xlabel("Date", color='#d1d4dc', fontsize=12)
ax.tick_params(colors='#d1d4dc')

# Date formatting
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.AutoDateLocator())
fig.autofmt_xdate()

# Legend (skip if dual_axis since we handled it above)
if COMPARISON_MODE != "dual_axis":
    ax.legend(loc='upper left', facecolor='#131722', edgecolor='#1e222d', fontsize=10)

# ============================================================
# Save
# ============================================================
os.makedirs("output", exist_ok=True)
plt.tight_layout()
plt.savefig(OUTPUT_FILE, dpi=150, facecolor='#131722', edgecolor='#131722')

print(f"Chart saved: {OUTPUT_FILE}")

# Print summary stats
start_val1 = df.iloc[0][ASSET1_LABEL]
end_val1 = df.iloc[-1][ASSET1_LABEL]
change1 = ((end_val1 / start_val1) - 1) * 100

start_val2 = df.iloc[0][ASSET2_LABEL]
end_val2 = df.iloc[-1][ASSET2_LABEL]
change2 = ((end_val2 / start_val2) - 1) * 100

print(f"\n{ASSET1_LABEL}: ${start_val1:.2f} → ${end_val1:.2f} ({change1:+.2f}%)")
print(f"{ASSET2_LABEL}: ${start_val2:.2f} → ${end_val2:.2f} ({change2:+.2f}%)")
