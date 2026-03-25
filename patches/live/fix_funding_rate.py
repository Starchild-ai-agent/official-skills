"""
FIX-6: Funding Rate Normalization

BUG-6: Exchanges report funding at different intervals (1h, 4h, 8h).
Comparing raw rates is misleading. This normalizes everything to 8h equivalent.
Also handles missing fundingIntervalHours field.
"""


def normalize_funding_rates(raw_result: dict, target_interval_hours: int = 8) -> dict:
    """
    Normalize all funding rates to a common interval (default 8h).
    
    Kraken 0.01268% per 1h → 0.10144% per 8h
    Binance 0.0409% per 8h → 0.0409% per 8h (unchanged)
    """
    if not isinstance(raw_result, dict):
        return raw_result
    
    data = raw_result.get("data", [])
    if not data:
        return raw_result
    
    for coin_data in data:
        for margin_type in ("uMarginList", "cMarginList"):
            entries = coin_data.get(margin_type, [])
            for entry in entries:
                rate = entry.get("rate")
                if rate is None:
                    continue
                
                interval = entry.get("fundingIntervalHours")
                
                # Infer interval from exchange if missing
                if interval is None:
                    exchange = entry.get("exchangeName", "").lower()
                    # Known 1h exchanges
                    if exchange in ("hyperliquid", "kraken", "coinbase", "lighter", "dydx", "crypto.com"):
                        interval = 1
                    else:
                        interval = 8  # default assumption
                    entry["fundingIntervalHours"] = interval
                    entry["_interval_inferred"] = True
                
                # Normalize to target interval
                if interval != target_interval_hours and interval > 0:
                    multiplier = target_interval_hours / interval
                    entry["rate_normalized_8h"] = round(rate * multiplier, 10)
                    entry["rate_original"] = rate
                else:
                    entry["rate_normalized_8h"] = rate
    
    raw_result["_normalization"] = f"All rates normalized to {target_interval_hours}h equivalent"
    return raw_result


# ─── Self-test ───────────────────────────────────────────
if __name__ == "__main__":
    test = {
        "data": [{
            "symbol": "BTC",
            "uMarginList": [
                {"exchangeName": "Binance", "rate": 0.000409, "fundingIntervalHours": 8},
                {"exchangeName": "Kraken", "rate": 0.0001268, "fundingIntervalHours": 1},
                {"exchangeName": "Hyperliquid", "rate": 0.00125, "fundingIntervalHours": 1},
                {"exchangeName": "Bitfinex", "rate": 0.00404},  # missing interval
                {"exchangeName": "HTX", "rate": -0.0120},       # missing interval
            ],
            "cMarginList": []
        }]
    }
    
    result = normalize_funding_rates(test)
    entries = result["data"][0]["uMarginList"]
    
    # Binance 8h: rate stays the same
    assert entries[0]["rate_normalized_8h"] == 0.000409
    print(f"✅ Binance 8h: {entries[0]['rate']} → {entries[0]['rate_normalized_8h']} (unchanged)")
    
    # Kraken 1h: 0.0001268 * 8 = 0.0010144
    assert abs(entries[1]["rate_normalized_8h"] - 0.0010144) < 0.0000001
    print(f"✅ Kraken  1h: {entries[1]['rate']} → {entries[1]['rate_normalized_8h']} (×8)")
    
    # Hyperliquid 1h: 0.00125 * 8 = 0.01
    assert abs(entries[2]["rate_normalized_8h"] - 0.01) < 0.0000001
    print(f"✅ HL      1h: {entries[2]['rate']} → {entries[2]['rate_normalized_8h']} (×8)")
    
    # Bitfinex: interval inferred (should be 8h default)
    assert entries[3].get("_interval_inferred") == True
    print(f"✅ Bitfinex: interval inferred as {entries[3]['fundingIntervalHours']}h")
    
    # HTX: interval inferred
    assert entries[4].get("_interval_inferred") == True
    print(f"✅ HTX:      interval inferred as {entries[4]['fundingIntervalHours']}h")
    
    print(f"\n🎯 All funding rate normalization patches pass self-test")
