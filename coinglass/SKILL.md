---
name: coinglass
version: 3.0.0
description: Comprehensive crypto derivatives data - funding rates, open interest, liquidations, long/short ratios, Hyperliquid whale tracking, volume analysis, ETF flows, futures market data
tools:
  # Basic Derivatives (7 tools)
  - funding_rate
  - long_short_ratio
  - cg_open_interest
  - cg_liquidations
  - cg_liquidation_analysis
  - cg_supported_coins
  - cg_supported_exchanges

  # Advanced Long/Short Ratios (6 tools)
  - cg_global_account_ratio
  - cg_top_account_ratio
  - cg_top_position_ratio
  - cg_taker_exchanges
  - cg_net_position
  - cg_net_position_v2

  # Advanced Liquidations (4 tools)
  - cg_coin_liquidation_history
  - cg_pair_liquidation_history
  - cg_liquidation_coin_list
  - cg_liquidation_orders

  # Hyperliquid Whale Tracking (4 tools)
  - cg_hyperliquid_whale_alerts
  - cg_hyperliquid_whale_positions
  - cg_hyperliquid_positions_by_coin
  - cg_hyperliquid_position_distribution

  # Futures Market Data (5 tools)
  - cg_coins_market_data
  - cg_pair_market_data
  - cg_ohlc_history
  - cg_taker_volume_history
  - cg_aggregated_taker_volume

  # Volume & Flow Analysis (4 tools)
  - cg_cumulative_volume_delta
  - cg_coin_netflow
  - cg_whale_transfers

  # Bitcoin ETF Data (5 tools)
  - cg_btc_etf_flows
  - cg_btc_etf_premium_discount
  - cg_btc_etf_history
  - cg_btc_etf_list
  - cg_hk_btc_etf_flows

  # Other ETF Data (8 tools)
  - cg_eth_etf_flows
  - cg_eth_etf_list
  - cg_eth_etf_premium_discount
  - cg_sol_etf_flows
  - cg_sol_etf_list
  - cg_xrp_etf_flows
  - cg_xrp_etf_list
  - cg_hk_eth_etf_flows

metadata:
  starchild:
    emoji: "📈"
    skillKey: coinglass
    plan: professional
    api_version: v4
    version: 3.0.0
    total_tools: 37
    requires:
      env:
        - COINGLASS_API_KEY

user-invocable: false
disable-model-invocation: false
---

# Coinglass

37 tools for crypto derivatives, whale tracking, volume analysis, liquidations, and ETF flows.

**Rate Limit**: 6000 req/min | **API**: V4 (V2 compat) | **Symbols**: Standard (BTC, ETH, SOL)

## Tools by Category

### 1. Basic Derivatives (7)
- `funding_rate(symbol, exchange?)` — Current funding rates
- `long_short_ratio(symbol, exchange?, interval?)` — L/S ratios
- `cg_open_interest(symbol)` — OI across exchanges
- `cg_liquidations(symbol, time?)` — Recent liquidations
- `cg_liquidation_analysis(symbol)` — Liquidation heatmap
- `cg_supported_coins()` / `cg_supported_exchanges()` — Reference data

### 2. Advanced L/S Ratios (6)
- `cg_global_account_ratio(symbol, interval?)` — Retail sentiment
- `cg_top_account_ratio(symbol, exchange, interval?)` — Smart money accounts
- `cg_top_position_ratio(symbol, exchange, interval?)` — Smart money positions
- `cg_taker_exchanges(symbol, interval?)` — Taker buy/sell by exchange
- `cg_net_position(symbol, exchange, interval?)` / `cg_net_position_v2(symbol)` — Net positioning

### 3. Liquidations (4)
- `cg_coin_liquidation_history(symbol, interval?, limit?)` — Historical liquidation data
- `cg_pair_liquidation_history(symbol, exchange, interval?, limit?)` — Per-pair history
- `cg_liquidation_coin_list(exchange)` — All coins on an exchange (1h/4h/12h/24h)
- `cg_liquidation_orders(symbol, exchange?)` — Recent individual orders (max 200, 7 days)

### 4. Hyperliquid Whales (4)
- `cg_hyperliquid_whale_alerts()` — Recent large position changes
- `cg_hyperliquid_whale_positions()` — Current whale positions
- `cg_hyperliquid_positions_by_coin(symbol)` — All positions for a coin
- `cg_hyperliquid_position_distribution(symbol)` — Position size distribution

### 5. Futures Market Data (5)
- `cg_coins_market_data()` — All coins overview (100+)
- `cg_pair_market_data(symbol, exchange)` — Single pair details
- `cg_ohlc_history(symbol, interval?, limit?)` — Price OHLC
- `cg_taker_volume_history(symbol, interval?, limit?)` — Taker buy/sell volume
- `cg_aggregated_taker_volume(symbol)` — Aggregated across exchanges

### 6. Volume & Flow (3)
- `cg_cumulative_volume_delta(symbol, interval?)` — CVD (buy vs sell pressure)
- `cg_coin_netflow(symbol, interval?)` — Exchange net in/outflows
- `cg_whale_transfers(symbol?)` — Large on-chain transfers (>$10M)

### 7. Bitcoin ETF (5)
- `cg_btc_etf_flows()` — Daily net flows
- `cg_btc_etf_premium_discount()` — NAV premium/discount
- `cg_btc_etf_history()` — Historical data
- `cg_btc_etf_list()` — All BTC ETFs
- `cg_hk_btc_etf_flows()` — Hong Kong BTC ETFs

### 8. Other ETFs (8)
ETH: `cg_eth_etf_flows()`, `cg_eth_etf_list()`, `cg_eth_etf_premium_discount()`, `cg_hk_eth_etf_flows()`
SOL: `cg_sol_etf_flows()`, `cg_sol_etf_list()`
XRP: `cg_xrp_etf_flows()`, `cg_xrp_etf_list()`

## Interpretation Quick Reference

**Funding Rates (8h)**: >+0.05% extreme greed (squeeze risk) | <-0.05% extreme fear (bounce risk) | ±0.01% neutral

**OI + Price**: OI↑ Price↑ = new longs (bullish) | OI↑ Price↓ = new shorts (bearish) | OI↓ Price↑ = short covering | OI↓ Price↓ = long liquidation

**L/S Ratio**: >1.5 crowded long (contrarian bearish) | <0.7 crowded short (contrarian bullish)

**CVD**: CVD↑ Price↑ = healthy uptrend | CVD↓ Price↑ = weak rally (distribution) | CVD↑ Price↓ = accumulation

**ETF Flows**: Large inflows = institutional buying | Premium to NAV = high demand | Discount = weak demand

## Multi-Metric Patterns

- **Positioning extremes**: funding + L/S ratio + liquidations
- **Smart money direction**: CVD + taker volume + whale alerts
- **Institutional conviction**: ETF flows + whale transfers + OI
- **Smart vs retail divergence**: `cg_top_account_ratio` vs `cg_global_account_ratio`

## Efficiency Tips

Prefer batch endpoints: `cg_coins_market_data()` returns 100+ coins in one call. `cg_hyperliquid_whale_alerts()` returns all alerts at once. Don't loop `cg_pair_market_data()` for multiple coins.

Most history endpoints accept: `interval` (1h/4h/12h/24h), `limit` (max 1000), `start_time`/`end_time` (unix ms).

## Notes

- **Update Frequency**: Market data ≤1min, funding every 8h, ETFs daily after market close, whale transfers real-time
- **API Versions**: V4 uses `CG-API-KEY` header, V2 uses `coinglassSecret` — both use same env var
- **Data Limits**: Liquidation orders: 7 days/200 max | Whale transfers: 6 months/min $10M | Hyperliquid alerts: ~200 recent
- **Exchanges**: Binance, OKX, Bybit, Gate, KuCoin, MEXC, CME, Hyperliquid, dYdX — use `cg_supported_exchanges()` for full list
