---
name: coingecko
version: 1.0.0
description: CoinGecko crypto price data, charts, market discovery, and global stats
tools:
  - coin_price
  - coin_ohlc
  - coin_chart
  - cg_trending
  - cg_top_gainers_losers
  - cg_new_coins
  - cg_global
  - cg_global_defi
  - cg_categories
  - cg_derivatives
  - cg_derivatives_exchanges
  - cg_coins_list
  - cg_coins_markets
  - cg_coin_data
  - cg_coin_tickers
  - cg_exchanges
  - cg_exchange
  - cg_exchange_tickers
  - cg_exchange_volume_chart
  - cg_nfts_list
  - cg_nft
  - cg_nft_by_contract
  - cg_asset_platforms
  - cg_exchange_rates
  - cg_vs_currencies
  - cg_categories_list
  - cg_search
  - cg_token_price
  - cg_coin_by_contract

metadata:
  starchild:
    emoji: "🦎"
    skillKey: coingecko
    requires:
      env:
        - COINGECKO_API_KEY

user-invocable: false
disable-model-invocation: false
---

# CoinGecko

Crypto spot prices, OHLC, market cap, trending coins, sectors, exchanges, NFTs, global stats.

## Tools

### Prices & Charts
- `coin_price(coin_id, vs_currencies?)` — Current price. Supports symbols (BTC, ETH, SOL)
- `coin_ohlc(coin_id, vs_currency, days)` — OHLC candles
- `coin_chart(coin_id, vs_currency, days)` — Price chart data
- `cg_token_price(contract_addresses=[], vs_currencies)` — By contract address

### Discovery
- `cg_trending()` — Trending coins (24h)
- `cg_top_gainers_losers()` — Top movers
- `cg_new_coins()` — Recently listed
- `cg_coins_markets(vs_currency, order?, per_page?)` — Market rankings
- `cg_search(query)` — Search coins by name

### Coin Details
- `cg_coin_data(id)` — Full coin info
- `cg_coin_tickers(id)` — All trading pairs
- `cg_coin_by_contract(contract_address, platform)` — Lookup by contract

### Exchanges
- `cg_exchanges()` — All exchanges
- `cg_exchange(id)` — Specific exchange
- `cg_exchange_tickers(id)` — Exchange pairs
- `cg_exchange_volume_chart(id, days)` — Volume history

### Global & Sectors
- `cg_global()` — Total market stats
- `cg_global_defi()` — DeFi stats
- `cg_categories()` — Sector performance
- `cg_derivatives()` / `cg_derivatives_exchanges()` — Derivatives data

### NFTs
- `cg_nfts_list()` — Collections
- `cg_nft(id)` / `cg_nft_by_contract(contract)` — NFT details

### Reference
- `cg_coins_list()` — All coin IDs
- `cg_asset_platforms()` — Blockchain platforms
- `cg_vs_currencies()` — Supported quote currencies
- `cg_exchange_rates()` — BTC-denominated rates

## Notes

- **Coin IDs**: Slugs (bitcoin, ethereum, solana). Common symbols auto-resolve: BTC→bitcoin, ETH→ethereum, SOL→solana
- **If unsure**: `cg_search(query="coin name")` first
- Use batch endpoints for multiple coins. `cg_coins_markets` returns up to 250 per page.
