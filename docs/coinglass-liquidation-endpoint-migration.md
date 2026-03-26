# Coinglass Liquidation Endpoint Migration

**Date:** 2026-03-26  
**Author:** Starchild Audit Bot  
**Branch:** `feat/m7-small-model-autoresearch`  
**Status:** ✅ Complete

---

## Problem

The `cg_liquidations` and `cg_liquidation_analysis` tools returned **zero values** for `long_liquidations_usd` and `short_liquidations_usd`, making the data unusable for sentiment analysis.

### Root Cause

The underlying Coinglass API endpoint `/api/futures/liquidation/exchange-list` returns per-exchange rows where `long_liquidation_usd` and `short_liquidation_usd` are always `0`, while `liquidation_usd` (total) contains a valid number.

This is a **Coinglass API-level issue** — the data simply isn't populated in this endpoint. It is not a parsing bug in our code.

### Evidence (Starchild Live Test, 2026-03-26)

| Exchange | long_liquidation_usd | short_liquidation_usd | liquidation_usd |
|----------|---------------------:|----------------------:|----------------:|
| Hyperliquid | 0 | 0 | 22,218,025 |
| Bybit | 0 | 0 | 20,016,614 |
| Binance | 0 | 0 | 15,756,629 |
| OKX | 0 | 0 | 13,735,756 |

**Result:** `long_percent = 0%`, `short_percent = 0%` — sentiment analysis always says "No data" or "Balanced", which is misleading.

---

## Solution

Replaced the broken `exchange-list` endpoint with the `/api/futures/liquidation/coin-list` endpoint, which **does** return correct long/short breakdowns.

### Replacement Endpoint Validation

| Endpoint | long/short split | Data quality | Status |
|----------|:---:|---|---|
| `/liquidation/exchange-list` | ❌ | long/short always 0 | **Deprecated** |
| `/liquidation/coin-list` | ✅ | BTC: L=4.4M, S=2.9M | **Now used** |
| `/liquidation/aggregated-history` | ✅ | Hourly time series | Unchanged |
| `/liquidation/pair-history` | ✅ | Per-exchange time series | Unchanged |

### Code Changes

**File:** `coinglass/tools/liquidations.py`

1. **Removed** dependency on `/api/futures/liquidation/exchange-list`
2. **Added** `_fetch_coin_list()` helper that calls `/api/futures/liquidation/coin-list`
3. **Modified** `get_liquidations()`:
   - New `exchange` parameter (optional) — single exchange or aggregate all
   - Iterates exchange list, filters by symbol, sums long/short from coin-list response
   - Uses time-window suffixes (`_1h`, `_4h`, `_12h`, `_24h`) from coin-list fields
4. **Updated** `get_liquidation_aggregated()`:
   - Unchanged interface
   - Now receives correct long/short data from `get_liquidations()`
   - Sentiment analysis produces meaningful results

### API Mapping

| Old (broken) | New (working) |
|---|---|
| `GET /liquidation/exchange-list?symbol=BTC&range=24h` | `GET /liquidation/coin-list?exchange=Binance` (per exchange, filter by symbol) |

---

## Test Results

### Unit Tests: 8/8 Passed

| Test | Description | Result |
|------|-------------|--------|
| `test_long_short_not_zero` | Core fix validation | ✅ |
| `test_percentages_correct` | 70/30 split accuracy | ✅ |
| `test_time_windows` | h1, h4, h12, h24 all work | ✅ |
| `test_analysis_sentiment` | Bearish when longs > 70% | ✅ |
| `test_zero_data_no_misleading_sentiment` | No "Balanced" on zero data | ✅ |
| `test_symbol_filtering` | Only returns requested symbol | ✅ |
| `test_api_error_returns_none` | Graceful error handling | ✅ |
| `test_multi_exchange_aggregation` | Aggregates >1 exchange | ✅ |

### Starchild Live Validation

Confirmed via Starchild's installed `cg_liquidation_coin_list` tool:
- BTC 24h: long=4,435,580 USD, short=2,936,487 USD ✅
- Percentages: 60.2% / 39.8% ✅
- Sentiment: "Moderately bearish pressure" (correct) ✅

### Flake8

Both `liquidations.py` and `test_liquidations_fix.py` pass flake8 (max-line-length=100) with zero warnings.

---

## Impact

- **`cg_liquidations` tool:** Now returns accurate long/short data
- **`cg_liquidation_analysis` tool:** Sentiment analysis now meaningful
- **No breaking changes:** Same response schema, same function signatures
- **New feature:** Optional `exchange` parameter for single-exchange queries

## Files Changed

| File | Change |
|------|--------|
| `coinglass/tools/liquidations.py` | Rewritten to use coin-list endpoint |
| `tests/test_liquidations_fix.py` | New: 8 unit tests |
| `docs/coinglass-liquidation-endpoint-migration.md` | This document |
