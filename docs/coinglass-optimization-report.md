# Coinglass Skill Optimization Report

> Generated: 2026-03-25 | Audit: official-skills-audit

## Executive Summary

Live diagnostic testing of the Coinglass skill revealed **3 data accuracy bugs** in liquidation and funding rate tools. All 3 are fixable on our side without changes to the upstream Coinglass API.

---

## Issues We Can Fix (Our Side)

### BUG-1: Liquidation "All" Row Returns Zero — No Fallback
**File:** `coinglass/tools/liquidations.py` (lines 169–200)
**Severity:** High
**Impact:** `get_liquidations()` reports $0 total liquidations even when individual exchanges show millions.

**Root Cause:** The function trusts the aggregated "All" row from the API. When the API returns `long_liquidations_usd: 0` and `short_liquidations_usd: 0` in the "All" row (while `total_liquidations_usd` is non-zero), our code reports zero.

**Fix:** When "All" row long/short are both 0 but exchange rows have data, fall back to self-summing exchange rows.

**Test Coverage:** 12 unit tests (`tests/test_liquidation_fixes.py`)

---

### BUG-2: Sentiment Analysis Crashes on Zero Data
**File:** `coinglass/tools/liquidations.py` (sentiment analysis section)
**Severity:** Medium
**Impact:** When BUG-1 triggers (zero data), the sentiment analysis labels the market "balanced" or produces division-by-zero errors instead of returning "unavailable".

**Root Cause:** No zero-data guard before computing long/short ratios and dominant side.

**Fix:** Add zero-data guard: if total liquidations == 0, return `dominant_side: "unknown"`, `sentiment: "Data unavailable"`.

**Test Coverage:** Included in BUG-1 test suite (5 specific sentiment tests)

---

### BUG-3: Funding Rate Interval Normalization Missing
**File:** `coinglass/tools/funding_rate.py` (lines 200–205)
**Severity:** Medium
**Impact:** `get_symbol_funding_rate()` averages funding rates across exchanges without normalizing for different funding intervals. A 1h exchange (dYdX at 0.001%) and an 8h exchange (Binance at 0.008%) produce a misleading average of 0.0045% instead of the correct ~0.008%.

**Root Cause:** Different exchanges use different funding intervals:
- **8h intervals:** Binance, OKX, Bybit, Bitget, Gate, HTX, CoinEx
- **4h intervals:** Kraken
- **1h intervals:** dYdX

The code averages raw rates without scaling to a common base.

**Fix:** Normalize all rates to 8h-equivalent before averaging. Map known exchanges to their interval, scale accordingly (1h × 8, 4h × 2, 8h × 1).

**Test Coverage:** 11 unit tests (`tests/test_funding_rate_fixes.py`)

---

## Issues Requiring Data Source (API) Changes

### ISSUE-A: "All" Row Inconsistency in Liquidation API
**Endpoint:** Coinglass liquidation endpoints
**Problem:** The "All" aggregated row sometimes returns `long_liquidations_usd: 0, short_liquidations_usd: 0` while `total_liquidations_usd` is non-zero. This is an API-level data inconsistency.
**Ideal Fix:** API should ensure `long + short ≈ total` in the "All" row, or not return the "All" row when breakdown data is unavailable.
**Our Workaround:** BUG-1 fix (self-sum fallback) ✅

### ISSUE-B: Missing Funding Interval Metadata
**Endpoint:** Coinglass funding rate endpoints
**Problem:** The API doesn't consistently include the funding interval period per exchange in the response data. We have to maintain a hardcoded mapping of exchange → interval.
**Ideal Fix:** API should include `funding_interval_hours` field per exchange in the response.
**Our Workaround:** BUG-3 fix (hardcoded interval map) ✅ — works but needs maintenance when exchanges change intervals.

### ISSUE-C: Stale Exchange Data in Liquidation Responses
**Endpoint:** Coinglass liquidation endpoints
**Problem:** Some exchange rows return all-zero values even for active trading pairs, suggesting stale or missing data feeds.
**Ideal Fix:** API should omit exchanges with no recent data or flag them as stale.
**Our Workaround:** Filter out all-zero exchange rows before summing ✅

---

## Test Results Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_liquidation_fixes.py` | 12 | ✅ All pass |
| `test_funding_rate_fixes.py` | 11 | ✅ All pass |
| **Full suite** | **1183** | **✅ All pass** |

## Files Modified

| File | Changes |
|------|---------|
| `coinglass/tools/liquidations.py` | Fallback sum logic, zero-data guard |
| `coinglass/tools/funding_rate.py` | 8h normalization for cross-exchange averages |
| `tests/test_liquidation_fixes.py` | 12 new unit tests |
| `tests/test_funding_rate_fixes.py` | 11 new unit tests |
| `tests/conftest.py` | Shared `core.http_client` stub |

## Recommendation

All 3 bugs should be patched in the official skills repo. The fixes are backward-compatible and improve data accuracy without requiring any API changes. The hardcoded exchange interval map (BUG-3) should be reviewed quarterly as exchanges occasionally change their funding schedules.
