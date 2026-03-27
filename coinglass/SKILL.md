---
name: coinglass
version: 3.0.0
description: Comprehensive crypto derivatives data - funding rates, open interest, liquidations, long/short ratios, Hyperliquid whale tracking, volume analysis, ETF flows, futures market data
tools:
  - funding_rate
  - long_short_ratio
  - cg_open_interest
  - cg_liquidations
  - cg_liquidation_analysis
  - cg_supported_coins
  - cg_supported_exchanges
  - cg_global_account_ratio
  - cg_top_account_ratio
  - cg_top_position_ratio
  - cg_taker_exchanges
  - cg_net_position
  - cg_net_position_v2
  - cg_coin_liquidation_history
  - cg_pair_liquidation_history
  - cg_liquidation_coin_list
  - cg_liquidation_orders
  - cg_hyperliquid_whale_alerts
  - cg_hyperliquid_whale_positions
  - cg_hyperliquid_positions_by_coin
  - cg_hyperliquid_position_distribution
  - cg_coins_market_data
  - cg_pair_market_data
  - cg_ohlc_history
  - cg_taker_volume_history
  - cg_aggregated_taker_volume
  - cg_cumulative_volume_delta
  - cg_coin_netflow
  - cg_whale_transfers
  - cg_btc_etf_flows
  - cg_btc_etf_premium_discount
  - cg_btc_etf_history
  - cg_btc_etf_list
  - cg_hk_btc_etf_flows
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
    total_tools: 37
    requires:
      env:
        - COINGLASS_API_KEY

user-invocable: false
disable-model-invocation: false
---

# Coinglass

37 tools for crypto derivatives, whale tracking, volume analysis, liquidations, and ETF flows.

**Rate Limit**: 6000 req/min | **Symbols**: Standard (BTC, ETH, SOL)

## Tools

### Derivatives
- `funding_rate(symbol, exchange?)` — Funding rates
- `long_short_ratio(symbol, interval?)` — L/S ratios
- `cg_open_interest(symbol)` — OI across exchanges
- `cg_liquidations(symbol, time?)` — Recent liquidations
- `cg_liquidation_analysis(symbol)` — Liquidation heatmap

### Advanced L/S & Positioning
- `cg_global_account_ratio(symbol, interval?)` — Retail sentiment
- `cg_top_account_ratio(symbol, exchange, interval?)` — Smart money accounts
- `cg_top_position_ratio(symbol, exchange, interval?)` — Smart money positions
- `cg_taker_exchanges(symbol, interval?)` — Taker buy/sell by exchange
- `cg_net_position(symbol, exchange, interval?)` — Net positioning

### Liquidations
- `cg_coin_liquidation_history(symbol, interval?, limit?)` — Historical
- `cg_pair_liquidation_history(symbol, exchange, interval?)` — Per-pair
- `cg_liquidation_coin_list(exchange)` — All coins (1h/4h/12h/24h)
- `cg_liquidation_orders(symbol, exchange?)` — Individual orders (7d, max 200)

### Hyperliquid Whales
- `cg_hyperliquid_whale_alerts()` — Large position changes
- `cg_hyperliquid_whale_positions()` — Current whale positions
- `cg_hyperliquid_positions_by_coin(symbol)` — All positions for coin
- `cg_hyperliquid_position_distribution(symbol)` — Size distribution

### Market Data
- `cg_coins_market_data()` — All coins overview (100+, single call)
- `cg_pair_market_data(symbol, exchange)` — Single pair details
- `cg_ohlc_history(symbol, interval?, limit?)` — Price OHLC
- `cg_taker_volume_history(symbol, interval?)` — Taker buy/sell
- `cg_aggregated_taker_volume(symbol)` — Cross-exchange aggregated

### Volume & Flow
- `cg_cumulative_volume_delta(symbol, interval?)` — CVD
- `cg_coin_netflow(symbol, interval?)` — Exchange net in/outflows
- `cg_whale_transfers(symbol?)` — On-chain transfers >$10M

### ETFs
- BTC: `cg_btc_etf_flows()`, `cg_btc_etf_premium_discount()`, `cg_btc_etf_history()`, `cg_btc_etf_list()`, `cg_hk_btc_etf_flows()`
- ETH: `cg_eth_etf_flows()`, `cg_eth_etf_list()`, `cg_eth_etf_premium_discount()`, `cg_hk_eth_etf_flows()`
- SOL: `cg_sol_etf_flows()`, `cg_sol_etf_list()`
- XRP: `cg_xrp_etf_flows()`, `cg_xrp_etf_list()`

## Interpretation

| Signal | Bullish | Bearish |
|--------|---------|---------|
| Funding (8h) | <-0.05% (fear) | >+0.05% (greed) |
| OI + Price | OI↑ Price↑ (new longs) | OI↑ Price↓ (new shorts) |
| L/S Ratio | <0.7 (crowded short) | >1.5 (crowded long) |
| CVD vs Price | CVD↑ Price↓ (accumulation) | CVD↓ Price↑ (distribution) |
| ETF Flows | Large inflows + premium | Outflows + discount |

## Multi-Metric Patterns

- **Positioning**: funding + L/S + liquidations
- **Smart money**: CVD + taker volume + whale alerts
- **Institutional**: ETF flows + whale transfers + OI
- **Smart vs retail**: `cg_top_account_ratio` vs `cg_global_account_ratio`

## Tips

- Prefer `cg_coins_market_data()` over looping `cg_pair_market_data()`
- History endpoints accept: `interval`, `limit` (max 1000), `start_time`/`end_time`
- Supported exchanges: Binance, OKX, Bybit, Gate, KuCoin, MEXC, CME, Hyperliquid, dYdX
