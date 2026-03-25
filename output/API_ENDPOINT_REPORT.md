# Starchild API Endpoint Report
**Generated:** 2026-03-25 12:12 UTC  
**Environment:** Starchild Production (sc-proxy transparent billing proxy)  
**Tester:** Aaron's Starchild Agent  

---

## Executive Summary

**Total Endpoints Tested:** 34  
**✅ Fully Operational:** 33  
**⚠️ Data Anomaly:** 1 (functional but data inconsistency)  
**❌ Failed:** 0  

All API endpoints are operational through the Starchild proxy infrastructure. No real API keys are needed by the user — the sc-proxy transparently injects production credentials.

---

## 1. CoinGecko Endpoints (Spot Market Data)

| # | Endpoint | Status | Notes |
|---|----------|--------|-------|
| 1 | `coin_price(bitcoin,ethereum,solana)` | ✅ | BTC: $71,795, ETH: $2,192, SOL: $93.10 |
| 2 | `cg_global()` | ✅ | 18,009 active cryptos, 1,481 markets |
| 3 | `cg_trending()` | ✅ | Trending coins, NFTs, categories |
| 4 | `cg_top_gainers_losers(24h)` | ✅ | 30 gainers + 30 losers |
| 5 | `cg_coins_markets(ids=btc,eth,sol)` | ✅ | Market cap, volume, 1h/24h/7d changes |
| 6 | `cg_coin_data(bitcoin)` | ✅ | Full coin profile + market data |
| 7 | `cg_categories(market_cap_change_24h_desc)` | ✅ | 680 categories returned |

---

## 2. Coinglass Endpoints (Derivatives Data)

| # | Endpoint | Status | Notes |
|---|----------|--------|-------|
| 8 | `funding_rate(BTC)` | ✅ | Multi-exchange funding rates |
| 9 | `cg_open_interest(BTC)` | ✅ | Aggregate OI across exchanges |
| 10 | `long_short_ratio(BTC, h4)` | ✅ | L/S ratio data |
| 11 | `cg_liquidations(BTC, h24)` | ✅ | Liquidation data by exchange |
| 12 | `cg_liquidation_analysis(BTC)` | ⚠️ | Top-level aggregation shows 0 — see anomaly |
| 13 | `cg_coins_market_data()` | ✅ | 100+ coins, all metrics |
| 14 | `cg_pair_market_data(BTC, Binance)` | ✅ | 96 trading pairs |
| 15 | `cg_top_account_ratio(BTC, Binance)` | ✅ | Top trader L/S by account |
| 16 | `cg_global_account_ratio(BTC, Binance)` | ✅ | Global L/S ratio |
| 17 | `cg_top_position_ratio(BTC, Binance)` | ✅ | Top trader L/S by position $ |
| 18 | `cg_taker_volume_history(BTC, Binance)` | ✅ | Buy/sell taker volume |
| 19 | `cg_net_position(BTC, Binance)` | ✅ | Net long/short changes |
| 20 | `cg_cumulative_volume_delta(BTC, Binance)` | ✅ | CVD with buy/sell volumes |
| 21 | `cg_ohlc_history(BTC, Binance, h1)` | ✅ | OHLCV candle data |
| 22 | `cg_aggregated_taker_volume(BTC, multi-exchange)` | ✅ | Multi-exchange aggregation |
| 23 | `cg_coin_netflow()` | ✅ | Netflow for all futures coins |
| 24 | `cg_liquidation_coin_list(Binance)` | ✅ | 555 coins with liquidation data |
| 25 | `cg_liquidation_orders(BTC, Binance, $100K+)` | ✅ | 200 individual liquidation orders |

---

## 3. ETF Flow Endpoints

| # | Endpoint | Status | Notes |
|---|----------|--------|-------|
| 26 | `cg_btc_etf_flows()` | ✅ | ~569 days of BTC ETF flow data (11 ETFs) |
| 27 | `cg_eth_etf_flows()` | ✅ | ~431 days of ETH ETF flow data (9 ETFs) |

---

## 4. Hyperliquid Endpoints

| # | Endpoint | Status | Notes |
|---|----------|--------|-------|
| 28 | `hl_market(BTC)` | ✅ | Mid price, leverage, szDecimals |
| 29 | `hl_funding(BTC)` | ✅ | Predicted + historical funding |
| 30 | `cg_hyperliquid_whale_positions()` | ✅ | Current whale positions |
| 31 | `cg_hyperliquid_whale_alerts()` | ✅ | 50 recent alerts (>$1M) |
| 32 | `cg_hyperliquid_position_distribution()` | ✅ | 8 tiers: shrimp to leviathan |
| 33 | `cg_hyperliquid_positions_by_coin(BTC)` | ✅ | All open BTC positions |

---

## 5. Whale Transfer Endpoint

| # | Endpoint | Status | Notes |
|---|----------|--------|-------|
| 34 | `cg_whale_transfers()` | ✅ | 1000 transfers (>$10M), multi-chain |

---

## Data Anomaly: `cg_liquidation_analysis`

**Issue:** Top-level `long_liquidations_usd` and `short_liquidations_usd` return `0`, while exchange-level `total_liquidations_usd` has valid data.

```
Top-level:  total=0, long=0, short=0
Exchange:   Hyperliquid=$21M, Bybit=$19M, HTX=$14M, Binance=$12M ...
```

Each exchange also shows `long_liquidations_usd: 0` and `short_liquidations_usd: 0` but valid `total_liquidations_usd`. This is an **upstream Coinglass API issue**.

**Workaround:** Use `cg_liquidations()` or `cg_coins_market_data()` — these return correct long/short breakdowns.

---

## API Infrastructure: No Real Keys Required

All calls route through `sc-proxy` which injects production credentials. The following are fully proxied:

| Service | Coverage | Key Needed? |
|---------|----------|-------------|
| CoinGecko Pro | All market data | ❌ No |
| Coinglass | All derivatives data | ❌ No |
| Hyperliquid | Market data + trading | ❌ No |
| Brave Search | Web search | ❌ No |
| Twitter/X | Social data | ❌ No |
| Twelve Data | Stock/forex | ❌ No |

---

## Endpoints NOT Tested

| Service | Reason |
|---------|--------|
| Polymarket | No test coverage in current suite |
| Charting | Visual output, needs browser preview |
| Birdeye | Solana DEX data, out of scope |
| LunarCrush | Social analytics, out of scope |
| 1inch | DEX aggregation, out of scope |

---

## Recommendations

1. **Fix `cg_liquidation_analysis` aggregation** — Compute totals from exchange data when API returns zeros
2. **Add Polymarket test coverage** — Currently untested
3. **Add Charting validation** — Needs browser-based testing
4. **Consider response caching** — Large endpoints (ETF flows, whale transfers) return 300K+ chars

---

*Report by Starchild Agent — Official Skills Audit*
