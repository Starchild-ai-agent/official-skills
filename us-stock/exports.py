"""
us-stock skill — US equities data with multi-source fallback.

Source priority:
  1. twelvedata (already paid, fast & accurate)  — realtime prices, K-line
  2. yfinance (free, broad coverage)              — fundamentals, holders, financials, news
  3. SEC EDGAR (free, authoritative)              — future: 13F / Form 4 deep dives

All functions return:
  {"ok": bool, "source": str, "data": <payload>, "error": str|None, "ts": int}

Symbol format:
  - Pure US ticker: "AAPL" / "MSFT" / "BRK.B" / "NVDA"
  - Exchange suffix not required for US stocks
"""
from __future__ import annotations
import sys, time, json
from typing import Any, Dict, List, Optional

# Reuse the existing (paid) twelvedata skill.
# We can't `from exports import ...` because this file is also `exports.py` —
# Python's module cache would alias them. Load by explicit file path instead.
import importlib.util as _ilu
_HAS_TD = False
twelvedata_quote = twelvedata_time_series = twelvedata_price = twelvedata_quote_batch = None
try:
    _td_path = "/data/workspace/skills/twelvedata/exports.py"
    _spec = _ilu.spec_from_file_location("_twelvedata_exports", _td_path)
    _td_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_td_mod)
    twelvedata_quote = _td_mod.twelvedata_quote
    twelvedata_time_series = _td_mod.twelvedata_time_series
    twelvedata_price = _td_mod.twelvedata_price
    twelvedata_quote_batch = _td_mod.twelvedata_quote_batch
    _HAS_TD = True
except Exception as _e:
    _HAS_TD = False

try:
    import yfinance as yf
except ImportError:
    yf = None


# ---------- helpers ----------

def _now() -> int:
    return int(time.time())

def _result(ok: bool, source: str, data: Any, error: Optional[str] = None) -> Dict[str, Any]:
    return {"ok": ok, "source": source, "data": data, "error": error, "ts": _now()}

def _retry(func, tries: int = 2, sleep: float = 0.5):
    last = None
    for i in range(tries):
        try:
            return func(), None
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(sleep)
    return None, last

def _df_to_records(df) -> List[Dict[str, Any]]:
    """pandas DataFrame → JSON-safe list of dicts. Handles NaN / Timestamp."""
    if df is None or len(df) == 0:
        return []
    out = []
    for rec in df.reset_index().to_dict(orient="records") if hasattr(df, "reset_index") else df.to_dict(orient="records"):
        clean = {}
        for k, v in rec.items():
            if v is None:
                clean[str(k)] = None
            elif hasattr(v, "isoformat"):
                clean[str(k)] = v.isoformat()
            elif isinstance(v, float) and v != v:  # NaN
                clean[str(k)] = None
            else:
                clean[str(k)] = v
        out.append(clean)
    return out

def _safe(d: dict, key: str, default=None):
    v = d.get(key)
    if v is None: return default
    if isinstance(v, float) and v != v: return default
    return v


# ---------- 1. Realtime quote ----------

def get_realtime_quote(symbol: str, prepost: bool = False) -> Dict[str, Any]:
    """
    Realtime quote: price, change, OHLC, volume, 52w range, market cap.
      prepost=True → include pre/after-hours fields (TwelveData only).
    Primary: twelvedata (paid, low-latency, supports prepost).
    Fallback: yfinance fast_info (free, ~1 min lag).
    """
    if _HAS_TD:
        def _td():
            kw = {"symbol": symbol}
            if prepost:
                kw["prepost"] = True
            r = twelvedata_quote(**kw)
            if r.get("status") == "error":
                raise RuntimeError(r.get("message"))
            return r
        q, err = _retry(_td)
        if q and q.get("symbol"):
            fw = q.get("fifty_two_week", {}) or {}
            out = {
                "symbol": q.get("symbol"),
                "name": q.get("name"),
                "exchange": q.get("exchange"),
                "currency": q.get("currency"),
                "datetime": q.get("datetime"),
                "open": _to_f(q.get("open")),
                "high": _to_f(q.get("high")),
                "low": _to_f(q.get("low")),
                "close": _to_f(q.get("close")),
                "last": _to_f(q.get("close")),
                "prev_close": _to_f(q.get("previous_close")),
                "change": _to_f(q.get("change")),
                "pct_change": _to_f(q.get("percent_change")),
                "volume": _to_i(q.get("volume")),
                "avg_volume": _to_i(q.get("average_volume")),
                "is_market_open": q.get("is_market_open"),
                "52w_high": _to_f(fw.get("high")),
                "52w_low": _to_f(fw.get("low")),
                "52w_high_pct": _to_f(fw.get("high_change_percent")),
                "52w_low_pct": _to_f(fw.get("low_change_percent")),
            }
            if prepost:
                for k in ("premarket_change","premarket_change_percent",
                          "postmarket_change","postmarket_change_percent",
                          "extended_change","extended_percent_change","extended_price"):
                    if k in q and q[k] not in (None, "", "NaN"):
                        out[k] = _to_f(q[k])
            return _result(True, "twelvedata:quote", out)

    if yf is None:
        return _result(False, "no_source", None, error="twelvedata failed and yfinance not installed")

    def _yf():
        t = yf.Ticker(symbol)
        fi = t.fast_info
        return dict(fi)
    fi, err = _retry(_yf)
    if fi:
        out = {
            "symbol": symbol,
            "currency": fi.get("currency"),
            "exchange": fi.get("exchange"),
            "open": fi.get("open"),
            "high": fi.get("dayHigh"),
            "low": fi.get("dayLow"),
            "last": fi.get("lastPrice"),
            "prev_close": fi.get("previousClose"),
            "volume": fi.get("lastVolume"),
            "avg_volume": fi.get("tenDayAverageVolume"),
            "52w_high": fi.get("yearHigh"),
            "52w_low": fi.get("yearLow"),
            "market_cap": fi.get("marketCap"),
            "shares": fi.get("shares"),
        }
        if out.get("last") and out.get("prev_close"):
            out["change"] = round(out["last"] - out["prev_close"], 4)
            out["pct_change"] = round((out["last"] - out["prev_close"]) / out["prev_close"] * 100, 4)
        return _result(True, "yfinance:fast_info", out)
    return _result(False, "all_failed", None, error=str(err))


def _to_f(v):
    try: return float(v) if v not in (None, "", "NaN") else None
    except: return None

def _to_i(v):
    try: return int(float(v)) if v not in (None, "", "NaN") else None
    except: return None


# ---------- 2. Company profile + shares info ----------

def get_company_info(symbol: str) -> Dict[str, Any]:
    """
    Company background + shares outstanding + holder %.
    Source: yfinance.get_info()  (one call, ~120 fields, we extract the useful ones)
    """
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        return yf.Ticker(symbol).get_info()
    info, err = _retry(_yf, tries=2, sleep=0.8)
    if not info:
        return _result(False, "all_failed", None, error=str(err))

    out = {
        "symbol": symbol,
        "name": _safe(info, "longName") or _safe(info, "shortName"),
        "exchange": _safe(info, "fullExchangeName") or _safe(info, "exchange"),
        "sector": _safe(info, "sector"),
        "industry": _safe(info, "industry"),
        "country": _safe(info, "country"),
        "city": _safe(info, "city"),
        "state": _safe(info, "state"),
        "website": _safe(info, "website"),
        "employees": _safe(info, "fullTimeEmployees"),
        "business_summary": _safe(info, "longBusinessSummary"),

        # Shares & market cap (the core ask)
        "market_cap": _safe(info, "marketCap"),
        "enterprise_value": _safe(info, "enterpriseValue"),
        "shares_outstanding": _safe(info, "sharesOutstanding"),
        "float_shares": _safe(info, "floatShares"),
        "shares_short": _safe(info, "sharesShort"),
        "short_ratio": _safe(info, "shortRatio"),
        "short_pct_of_float": _safe(info, "shortPercentOfFloat"),
        "pct_held_insiders": _safe(info, "heldPercentInsiders"),
        "pct_held_institutions": _safe(info, "heldPercentInstitutions"),

        # Valuation
        "trailing_pe": _safe(info, "trailingPE"),
        "forward_pe": _safe(info, "forwardPE"),
        "price_to_book": _safe(info, "priceToBook"),
        "price_to_sales": _safe(info, "priceToSalesTrailing12Months"),
        "peg_ratio": _safe(info, "trailingPegRatio") or _safe(info, "pegRatio"),
        "eps_trailing": _safe(info, "trailingEps"),
        "eps_forward": _safe(info, "forwardEps"),
        "book_value": _safe(info, "bookValue"),

        # Dividends
        "dividend_rate": _safe(info, "dividendRate"),
        "dividend_yield": _safe(info, "dividendYield"),
        "payout_ratio": _safe(info, "payoutRatio"),
        "ex_dividend_date": _safe(info, "exDividendDate"),

        # Risk / performance
        "beta": _safe(info, "beta"),
        "52w_high": _safe(info, "fiftyTwoWeekHigh"),
        "52w_low": _safe(info, "fiftyTwoWeekLow"),
        "50d_avg": _safe(info, "fiftyDayAverage"),
        "200d_avg": _safe(info, "twoHundredDayAverage"),

        # Margins / profitability
        "profit_margins": _safe(info, "profitMargins"),
        "operating_margins": _safe(info, "operatingMargins"),
        "gross_margins": _safe(info, "grossMargins"),
        "return_on_equity": _safe(info, "returnOnEquity"),
        "return_on_assets": _safe(info, "returnOnAssets"),
        "revenue_growth": _safe(info, "revenueGrowth"),
        "earnings_growth": _safe(info, "earningsGrowth"),

        # Analyst ratings
        "recommendation": _safe(info, "recommendationKey"),
        "target_mean_price": _safe(info, "targetMeanPrice"),
        "target_high": _safe(info, "targetHighPrice"),
        "target_low": _safe(info, "targetLowPrice"),
        "num_analysts": _safe(info, "numberOfAnalystOpinions"),
    }
    return _result(True, "yfinance:info", out)


# ---------- 3. Institutional & mutual fund holders ----------

def get_institutional_holders(symbol: str, top: int = 15) -> Dict[str, Any]:
    """Top institutional holders (most recent 13F)."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        df = yf.Ticker(symbol).institutional_holders
        return _df_to_records(df.head(top)) if df is not None else []
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:institutional_holders", res)
    return _result(False, "all_failed", None, error=str(err))


def get_mutualfund_holders(symbol: str, top: int = 15) -> Dict[str, Any]:
    """Top mutual fund holders."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        df = yf.Ticker(symbol).mutualfund_holders
        return _df_to_records(df.head(top)) if df is not None else []
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:mutualfund_holders", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 4. Insider transactions ----------

def get_insider_transactions(symbol: str, limit: int = 20) -> Dict[str, Any]:
    """Recent insider (Form 4) buys/sells."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        df = yf.Ticker(symbol).insider_transactions
        return _df_to_records(df.head(limit)) if df is not None else []
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:insider_transactions", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 5. Financials ----------

def get_financials(symbol: str, statement: str = "income", period: str = "annual",
                   max_periods: int = 5) -> Dict[str, Any]:
    """
    Financial statements.
      statement: 'income' | 'balance' | 'cashflow'
      period: 'annual' | 'quarterly'
    """
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    attr_map = {
        ("income", "annual"): "income_stmt",
        ("income", "quarterly"): "quarterly_income_stmt",
        ("balance", "annual"): "balance_sheet",
        ("balance", "quarterly"): "quarterly_balance_sheet",
        ("cashflow", "annual"): "cashflow",
        ("cashflow", "quarterly"): "quarterly_cashflow",
    }
    attr = attr_map.get((statement, period))
    if not attr:
        return _result(False, "bad_args", None, error=f"unknown {statement}/{period}")
    def _yf():
        df = getattr(yf.Ticker(symbol), attr)
        if df is None or len(df) == 0:
            return {}
        # df columns are period dates, rows are metrics → transpose to {metric: {period: value}}
        cols = list(df.columns)[:max_periods]
        out = {}
        for metric in df.index:
            row = {}
            for col in cols:
                v = df.at[metric, col]
                if v != v:  # NaN
                    continue
                row[str(col)[:10]] = float(v) if hasattr(v, "real") else v
            if row:
                out[str(metric)] = row
        return out
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, f"yfinance:{attr}", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 6. Earnings calendar ----------

def get_earnings(symbol: str, limit: int = 8) -> Dict[str, Any]:
    """Past + upcoming earnings dates with EPS estimate vs actual."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        df = yf.Ticker(symbol).earnings_dates
        return _df_to_records(df.head(limit)) if df is not None else []
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:earnings_dates", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 7. Dividends & splits ----------

def get_dividends(symbol: str, limit: int = 20) -> Dict[str, Any]:
    """Historical dividend payments."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        s = yf.Ticker(symbol).dividends
        if s is None or len(s) == 0:
            return []
        s = s.tail(limit)
        return [{"date": str(idx)[:10], "amount": float(v)} for idx, v in s.items()]
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:dividends", res)
    return _result(False, "all_failed", None, error=str(err))


def get_splits(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """Historical stock splits."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        s = yf.Ticker(symbol).splits
        if s is None or len(s) == 0:
            return []
        s = s.tail(limit)
        return [{"date": str(idx)[:10], "ratio": float(v)} for idx, v in s.items()]
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:splits", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 8. News ----------

def get_news(symbol: str, limit: int = 10) -> Dict[str, Any]:
    """Recent news for the ticker (from Yahoo Finance)."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        items = yf.Ticker(symbol).news or []
        out = []
        for it in items[:limit]:
            c = it.get("content") or it
            out.append({
                "title": c.get("title"),
                "summary": c.get("summary"),
                "publisher": (c.get("provider") or {}).get("displayName") if isinstance(c.get("provider"), dict) else c.get("publisher"),
                "pub_date": c.get("pubDate") or c.get("providerPublishTime"),
                "url": (c.get("canonicalUrl") or {}).get("url") if isinstance(c.get("canonicalUrl"), dict) else c.get("link"),
                "type": c.get("contentType"),
            })
        return out
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:news", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 9. K-line / historical bars ----------

def get_kline(symbol: str, interval: str = "1day", outputsize: int = 120,
              start: Optional[str] = None, end: Optional[str] = None) -> Dict[str, Any]:
    """
    Historical OHLCV bars.
      interval: 1day | 1week | 1month | 1h | 5min ...
      outputsize: number of bars (TwelveData accepts up to 5000)
    Primary: twelvedata_time_series (paid, clean).
    Fallback: yfinance history.
    """
    if _HAS_TD:
        def _td():
            kwargs = {"symbol": symbol, "interval": interval, "outputsize": outputsize}
            if start: kwargs["start_date"] = start
            if end: kwargs["end_date"] = end
            r = twelvedata_time_series(**kwargs)
            return r.get("values", []) if isinstance(r, dict) else []
        res, err = _retry(_td)
        if res:
            return _result(True, "twelvedata:time_series", res)

    if yf is None:
        return _result(False, "no_source", None, error="twelvedata failed and yfinance not installed")

    yf_interval = {"1day": "1d", "1week": "1wk", "1month": "1mo",
                   "1h": "1h", "30min": "30m", "15min": "15m", "5min": "5m"}.get(interval, "1d")
    yf_period = {"1d": "1y", "1wk": "5y", "1mo": "max", "1h": "1mo", "30m": "1mo", "15m": "1mo", "5m": "5d"}.get(yf_interval, "1y")

    def _yf():
        hist = yf.Ticker(symbol).history(period=yf_period, interval=yf_interval)
        if hist is None or len(hist) == 0:
            return []
        hist = hist.tail(outputsize)
        return [{
            "datetime": str(idx),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"]) if row["Volume"] == row["Volume"] else 0,
        } for idx, row in hist.iterrows()]
    res, err = _retry(_yf)
    if res:
        return _result(True, "yfinance:history", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 10. Analyst ratings ----------

def get_recommendations(symbol: str, limit: int = 12) -> Dict[str, Any]:
    """Analyst rating summary (latest 4 periods, count by recommendation)."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        df = yf.Ticker(symbol).recommendations
        return _df_to_records(df.head(limit)) if df is not None else []
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:recommendations", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 11. Options chain ----------

def get_options_expirations(symbol: str) -> Dict[str, Any]:
    """All available option expiration dates."""
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        return list(yf.Ticker(symbol).options or [])
    res, err = _retry(_yf)
    if res is not None:
        return _result(True, "yfinance:options", res)
    return _result(False, "all_failed", None, error=str(err))


# ---------- 11. ETF / Fund holdings ----------

def get_etf_holdings(symbol: str, top: int = 15) -> Dict[str, Any]:
    """
    Top holdings of an ETF / mutual fund (e.g. SPY, QQQ, ARKK, VTI).
    Returns top N positions + sector_weightings + asset_classes + description.
    Errors gracefully if symbol is not an ETF.
    """
    if yf is None:
        return _result(False, "no_yfinance", None, error="yfinance not installed")
    def _yf():
        t = yf.Ticker(symbol)
        fd = t.funds_data
        if fd is None:
            return None
        out = {"top_holdings": [], "sector_weightings": {}, "asset_classes": {}, "description": None}
        if fd.top_holdings is not None and len(fd.top_holdings) > 0:
            df = fd.top_holdings.head(top).reset_index()
            for _, row in df.iterrows():
                rec = {}
                for k, v in row.items():
                    if isinstance(v, float) and v != v:
                        rec[str(k)] = None
                    else:
                        rec[str(k)] = float(v) if isinstance(v, (int, float)) else v
                out["top_holdings"].append(rec)
        try:
            sw = fd.sector_weightings
            if sw: out["sector_weightings"] = {k: float(v) for k, v in sw.items() if v == v}
        except Exception: pass
        try:
            ac = fd.asset_classes
            if ac: out["asset_classes"] = {k: float(v) for k, v in ac.items() if v == v}
        except Exception: pass
        try:
            out["description"] = str(fd.description)[:500] if fd.description else None
        except Exception: pass
        return out
    res, err = _retry(_yf)
    if res:
        return _result(True, "yfinance:funds_data", res)
    return _result(False, "all_failed", None,
                   error=str(err) if err else "not an ETF/fund or no holdings data")


# ---------- 12. One-shot full report ----------

def get_full_report(symbol: str) -> Dict[str, Any]:
    """Combined snapshot for Telegram-style replies."""
    return {
        "quote": get_realtime_quote(symbol),
        "company": get_company_info(symbol),
        "institutional_holders": get_institutional_holders(symbol, top=10),
        "insider_transactions": get_insider_transactions(symbol, limit=10),
        "earnings": get_earnings(symbol, limit=4),
        "news": get_news(symbol, limit=8),
    }
