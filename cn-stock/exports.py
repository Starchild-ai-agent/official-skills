"""
cn-stock skill — China A-share data layer (Tushare via sc-proxy).

Source strategy:
  - Tushare Pro HTTP API (POST http://api.tushare.pro/)
  - All traffic routed through sc-proxy (transparent-proxy `tushare` plugin),
    which injects the real TUSHARE_TOKEN and bills the call.
  - No need for a local TUSHARE_TOKEN env var; this skill sends the fake token
    and sc-proxy replaces it before the request reaches Tushare.

Most functions return:
  {"ok": bool, "source": str, "data": <payload>, "error": str|None, "ts": int}

Code format input:
  - Pure 6-digit code: "603186" / "300476" / "000001"
  - ts_code with exchange suffix: "000001.SZ" / "600000.SH" / "830799.BJ"
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Skills run inside the agent runtime where core.http_client is importable.
# proxied_post automatically routes through sc-proxy when STARCHILD_API_PROXY_*
# env vars are present (production), and falls through to a direct request when
# not (only useful for local debug, where the fake token will be rejected).
from core.http_client import proxied_post


TUSHARE_URL = "http://api.tushare.pro/"
FAKE_TOKEN = "fake-tushare-key-12345"

_NAME_CACHE: Optional[Dict[str, str]] = None


# ---------- helpers ----------

def _now() -> int:
    return int(time.time())


def _result(ok: bool, source: str, data: Any, error: Optional[str] = None) -> Dict[str, Any]:
    return {"ok": ok, "source": source, "data": data, "error": error, "ts": _now()}


def _to_ts_code(code: str) -> str:
    c = code.strip().upper()
    if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", c):
        return c
    if re.fullmatch(r"\d{6}", c):
        if c.startswith(("60", "68", "90")):
            return f"{c}.SH"
        if c.startswith(("00", "20", "30")):
            return f"{c}.SZ"
        if c.startswith(("4", "8")):
            return f"{c}.BJ"
        return f"{c}.SH"
    raise ValueError(f"invalid code format: {code}")


def _date_str(ts_sec: int) -> str:
    return time.strftime("%Y%m%d", time.localtime(ts_sec))


def _call(api_name: str, fields: str = "", **params) -> pd.DataFrame:
    """POST to Tushare via sc-proxy. Raises on upstream/transport error."""
    payload = {
        "api_name": api_name,
        "token": FAKE_TOKEN,
        "params": params,
        "fields": fields,
    }
    headers = {"SC-CALLER-ID": "skill:cn-stock"}
    r = proxied_post(TUSHARE_URL, json=payload, headers=headers, timeout=30)
    if r.status_code >= 500:
        raise RuntimeError(f"upstream {r.status_code}: {r.text[:200]}")
    try:
        j = r.json()
    except Exception as e:
        raise RuntimeError(f"non-json response (status={r.status_code}): {str(e)} body={r.text[:200]}")
    if not isinstance(j, dict):
        raise RuntimeError(f"unexpected response shape: {str(j)[:200]}")
    if j.get("code") != 0:
        raise RuntimeError(j.get("msg") or f"tushare error: {j}")
    data = j.get("data") or {}
    cols = data.get("fields") or []
    items = data.get("items") or []
    return pd.DataFrame(items, columns=cols)


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


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or len(df) == 0:
        return []
    out = []
    for rec in df.to_dict(orient="records"):
        one = {}
        for k, v in rec.items():
            if v != v:  # NaN
                one[k] = None
            elif hasattr(v, "isoformat"):
                one[k] = v.isoformat()
            else:
                one[k] = v
        out.append(one)
    return out


def _name_map() -> Dict[str, str]:
    global _NAME_CACHE
    if _NAME_CACHE is not None:
        return _NAME_CACHE
    df = _call("stock_basic", exchange="", list_status="L", fields="ts_code,name")
    _NAME_CACHE = {str(r["ts_code"]): str(r["name"]) for _, r in df.iterrows()} if df is not None else {}
    return _NAME_CACHE


def _latest_daily_pair(ts_code: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Exception]]:
    start = _date_str(_now() - 45 * 86400)
    end = _date_str(_now())

    def _q():
        df = _call("daily", ts_code=ts_code, start_date=start, end_date=end)
        if df is None or len(df) == 0:
            return None, None
        d = df.sort_values("trade_date", ascending=False)
        cur = d.iloc[0].to_dict()
        prev = d.iloc[1].to_dict() if len(d) > 1 else None
        return cur, prev

    res, err = _retry(_q)
    if res is None:
        return None, None, err
    return res[0], res[1], None


# ---------- 1. Latest quote snapshot ----------

def get_realtime_quote(code: str) -> Dict[str, Any]:
    """Latest available quote snapshot (daily close + daily_basic valuation).

    Note: without independent realtime permissions on the upstream provider,
    this is end-of-day data, not intraday tick.
    """
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    cur, _prev, err = _latest_daily_pair(ts_code)
    if cur is None:
        return _result(False, "all_failed", None, error=str(err))

    def _db():
        return _call("daily_basic", ts_code=ts_code, trade_date=str(cur.get("trade_date")))

    db, db_err = _retry(_db)
    db_row = db.iloc[0].to_dict() if db is not None and len(db) > 0 else {}

    name = None
    try:
        name = _name_map().get(ts_code)
    except Exception:
        name = None

    close = float(cur.get("close") or 0)
    prev_close = float(cur.get("pre_close")) if cur.get("pre_close") is not None else None
    pct = float(cur.get("pct_chg")) if cur.get("pct_chg") is not None else None

    out = {
        "code": code,
        "ts_code": ts_code,
        "name": name,
        "trade_date": str(cur.get("trade_date")),
        "open": float(cur.get("open")) if cur.get("open") is not None else None,
        "high": float(cur.get("high")) if cur.get("high") is not None else None,
        "low": float(cur.get("low")) if cur.get("low") is not None else None,
        "close": close,
        "last": close,
        "prev_close": prev_close,
        "change": float(cur.get("change")) if cur.get("change") is not None else None,
        "pct_change": pct,
        "volume_lots": float(cur.get("vol")) if cur.get("vol") is not None else None,
        "turnover_yuan": float(cur.get("amount")) * 1000 if cur.get("amount") is not None else None,
        "turnover_rate_pct": float(db_row.get("turnover_rate")) if db_row.get("turnover_rate") is not None else None,
        "volume_ratio": float(db_row.get("volume_ratio")) if db_row.get("volume_ratio") is not None else None,
        "pe": float(db_row.get("pe")) if db_row.get("pe") is not None else None,
        "pe_ttm": float(db_row.get("pe_ttm")) if db_row.get("pe_ttm") is not None else None,
        "pb": float(db_row.get("pb")) if db_row.get("pb") is not None else None,
        "total_mcap": float(db_row.get("total_mv")) * 10000 if db_row.get("total_mv") is not None else None,
        "float_mcap": float(db_row.get("circ_mv")) * 10000 if db_row.get("circ_mv") is not None else None,
    }

    source = "tushare:daily+daily_basic" if db is not None else "tushare:daily"
    if db is None and db_err:
        out["daily_basic_error"] = str(db_err)

    if pct is None and prev_close:
        out["pct_change"] = round((close - prev_close) / prev_close * 100, 4)

    return _result(True, source, out)


# ---------- 2. Company profile ----------

def get_company_info(code: str) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    def _q():
        return _call("stock_company", ts_code=ts_code)

    df, err = _retry(_q)
    if df is None or len(df) == 0:
        return _result(False, "all_failed", None, error=str(err))
    return _result(True, "tushare:stock_company", df.iloc[0].to_dict())


# ---------- 3. Financial indicators ----------

def get_financial(code: str, max_periods: int = 12) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - 8 * 365 * 86400)
    end = _date_str(_now())

    def _q():
        return _call("fina_indicator", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None or len(df) == 0:
        return _result(False, "all_failed", None, error=str(err))

    d = df.sort_values("end_date", ascending=False).head(max_periods)
    metrics = [
        "eps", "dt_eps", "roe", "roe_dt", "grossprofit_margin", "netprofit_margin",
        "q_sales_yoy", "q_profit_yoy", "q_netprofit_yoy", "debt_to_assets",
        "ocfps", "basic_eps_yoy", "tr_yoy", "or_yoy",
    ]

    out: Dict[str, List[Dict[str, Any]]] = {}
    for m in metrics:
        if m not in d.columns:
            continue
        arr = []
        for _, r in d.iterrows():
            v = r.get(m)
            if v is None or v != v:
                continue
            arr.append({"period": str(r.get("end_date")), "value": float(v) if hasattr(v, "real") else v})
        if arr:
            out[m] = arr

    return _result(True, "tushare:fina_indicator", out)


# ---------- 4. Shareholders ----------

def get_holders(code: str, top: int = 10) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - 3 * 365 * 86400)
    end = _date_str(_now())

    def _q():
        return _call("top10_holders", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None or len(df) == 0:
        return _result(False, "all_failed", None, error=str(err))

    d = df.sort_values(["end_date", "ann_date"], ascending=False)
    latest_end = str(d.iloc[0].get("end_date"))
    latest = d[d["end_date"].astype(str) == latest_end].head(top)
    return _result(True, "tushare:top10_holders", _df_to_records(latest))


# ---------- 5. Fund flow ----------

def get_fund_flow(code: str, days: int = 10) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - max(days + 15, 40) * 86400)
    end = _date_str(_now())

    def _q():
        return _call("moneyflow", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))

    d = df.sort_values("trade_date", ascending=False).head(days)
    return _result(True, "tushare:moneyflow", _df_to_records(d))


# ---------- 6. Historical K-line ----------

def get_kline(code: str, period: str = "daily", start: str = "", end: str = "", adjust: str = "", limit: int = 120) -> Dict[str, Any]:
    """
    period: daily | weekly | monthly
    adjust: '' (unadjusted only — qfq/hfq requires the SDK pro_bar wrapper)
    start/end: YYYYMMDD
    """
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    if adjust in ("qfq", "hfq"):
        return _result(False, "bad_param", None,
                       error="adjusted K-line (qfq/hfq) not supported in HTTP path; "
                             "use unadjusted bars and apply adjust factor separately if needed")

    if not end:
        end = _date_str(_now())
    if not start:
        days_back = {"daily": 260, "weekly": 1200, "monthly": 3600}.get(period, 260)
        start = _date_str(_now() - days_back * 86400)

    api_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
    api = api_map.get(period)
    if not api:
        return _result(False, "bad_param", None, error="period must be daily|weekly|monthly")

    def _q():
        return _call(api, ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    d = df.sort_values("trade_date", ascending=False).head(limit)
    return _result(True, f"tushare:{period}", _df_to_records(d))


# ---------- 7. Bid-ask snapshot ----------

def get_bid_ask(code: str) -> Dict[str, Any]:
    """L1-L5 bid/ask: requires separate realtime permission/source; not in baseline."""
    _ = code
    return _result(
        False,
        "not_available",
        None,
        error="bid/ask L1-L5 not provided in baseline Tushare permissions",
    )


# ---------- 8. Concept / industry boards ----------

def get_concept_boards(top: int = 30, sort_by: str = "count") -> Dict[str, Any]:
    def _q():
        return _call("ths_index", exchange="A", type="N")

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))

    d = df
    if sort_by in d.columns:
        d = d.sort_values(sort_by, ascending=False)
    return _result(True, "tushare:ths_index", _df_to_records(d.head(top)))


def get_stock_concepts(code: str) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    def _q():
        return _call("ths_member", ts_code=ts_code)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    return _result(True, "tushare:ths_member", _df_to_records(df))


# ---------- 9. Dragon-tiger list ----------

def get_lhb(code: str, days: int = 30) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    rows = []
    for i in range(max(days + 7, 20)):
        d = _date_str(_now() - i * 86400)
        try:
            df = _call("top_list", trade_date=d)
        except Exception:
            continue
        if df is None or len(df) == 0:
            continue
        part = df[df["ts_code"].astype(str) == ts_code]
        if len(part) > 0:
            rows.append(part)

    if not rows:
        return _result(True, "tushare:top_list", [])

    full = pd.concat(rows, ignore_index=True)
    if "trade_date" in full.columns:
        full = full.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:top_list", _df_to_records(full))


# ---------- 10. Market-wide ranking ----------

def get_top_movers(direction: str = "up", limit: int = 30) -> Dict[str, Any]:
    trade_date = None
    for i in range(10):
        d = _date_str(_now() - i * 86400)
        try:
            df = _call("daily", trade_date=d)
            if df is not None and len(df) > 0:
                trade_date = d
                break
        except Exception:
            continue

    if not trade_date:
        return _result(False, "all_failed", None, error="failed to get recent market daily snapshot")

    try:
        df_daily = _call("daily", trade_date=trade_date)
        if df_daily is None or len(df_daily) == 0:
            return _result(False, "all_failed", None, error="empty daily snapshot")

        names = _name_map()
        d = df_daily.copy()
        d["name"] = d["ts_code"].map(names)

        if direction == "up":
            d = d.sort_values("pct_chg", ascending=False)
            cols = ["ts_code", "name", "close", "pct_chg", "vol", "amount"]
        elif direction == "down":
            d = d.sort_values("pct_chg", ascending=True)
            cols = ["ts_code", "name", "close", "pct_chg", "vol", "amount"]
        elif direction == "turnover":
            db = _call("daily_basic", trade_date=trade_date,
                       fields="ts_code,turnover_rate,turnover_rate_f,volume_ratio,total_mv,circ_mv")
            if db is not None and len(db) > 0:
                d = d.merge(db, on="ts_code", how="left")
            d = d.sort_values("turnover_rate", ascending=False)
            cols = ["ts_code", "name", "close", "pct_chg", "turnover_rate", "volume_ratio", "total_mv", "circ_mv", "amount"]
        else:
            return _result(False, "bad_param", None, error="direction must be up|down|turnover")

        keep = [c for c in cols if c in d.columns]
        out = d[keep].head(limit)
        return _result(True, "tushare:daily(+daily_basic)", _df_to_records(out))
    except Exception as e:
        return _result(False, "all_failed", None, error=str(e))


# ---------- 11. One-shot full report ----------

def get_full_report(code: str) -> Dict[str, Any]:
    """Combined snapshot bundle. News is intentionally out of scope —
    use a normal web search tool for news instead."""
    return {
        "quote": get_realtime_quote(code),
        "company": get_company_info(code),
        "holders": get_holders(code, top=10),
        "fund_flow": get_fund_flow(code, days=5),
    }


# ===========================================================================
# Extended endpoints (v1.3): common Tushare APIs that were previously missing.
# All routed through the same `_call` helper (sc-proxy / fake token).
# ===========================================================================


# ---------- 12. Trade calendar ----------

def get_trade_calendar(start: str = "", end: str = "", exchange: str = "SSE",
                       open_only: bool = True) -> Dict[str, Any]:
    """Trading day calendar. start/end: YYYYMMDD. open_only=True keeps trading days only."""
    if not end:
        end = _date_str(_now())
    if not start:
        start = _date_str(_now() - 90 * 86400)

    def _q():
        return _call("trade_cal", exchange=exchange, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if open_only and "is_open" in df.columns:
        df = df[df["is_open"].astype(int) == 1]
    return _result(True, "tushare:trade_cal", _df_to_records(df))


# ---------- 13. Stock list (filter / discovery) ----------

def get_stock_list(market: str = "", industry: str = "",
                   list_status: str = "L", limit: int = 0) -> Dict[str, Any]:
    """All A-share listed stocks; optional market/industry filter.
    market: '主板' | '创业板' | '科创板' | '北交所' | '' (all)
    industry: e.g. '银行', '半导体', '' (all)
    list_status: 'L' (listed) | 'D' (delisted) | 'P' (paused)
    """
    fields = "ts_code,symbol,name,area,industry,market,list_date,act_name,act_ent_type"

    def _q():
        return _call("stock_basic", exchange="", list_status=list_status, fields=fields)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if market and "market" in df.columns:
        df = df[df["market"] == market]
    if industry and "industry" in df.columns:
        df = df[df["industry"].astype(str).str.contains(industry, na=False)]
    if limit and limit > 0:
        df = df.head(limit)
    return _result(True, "tushare:stock_basic", _df_to_records(df))


# ---------- 14. Three financial statements ----------

def _statement(api: str, code: str, period: str, max_periods: int) -> Dict[str, Any]:
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - 6 * 365 * 86400)
    end = _date_str(_now())
    kw = dict(ts_code=ts_code, start_date=start, end_date=end)
    if period:
        kw["period"] = period

    def _q():
        return _call(api, **kw)

    df, err = _retry(_q)
    if df is None or len(df) == 0:
        return _result(False, "all_failed", None, error=str(err))
    d = df.sort_values("end_date", ascending=False).head(max_periods)
    return _result(True, f"tushare:{api}", _df_to_records(d))


def get_income_statement(code: str, max_periods: int = 8, period: str = "") -> Dict[str, Any]:
    """利润表. period optional: 'YYYY1231'/'YYYY0930'/'YYYY0630'/'YYYY0331'."""
    return _statement("income", code, period, max_periods)


def get_balance_sheet(code: str, max_periods: int = 8, period: str = "") -> Dict[str, Any]:
    """资产负债表."""
    return _statement("balancesheet", code, period, max_periods)


def get_cashflow_statement(code: str, max_periods: int = 8, period: str = "") -> Dict[str, Any]:
    """现金流量表."""
    return _statement("cashflow", code, period, max_periods)


# ---------- 15. Earnings forecast / express ----------

def get_earnings_forecast(code: str, limit: int = 8) -> Dict[str, Any]:
    """业绩预告 (forecast)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    def _q():
        return _call("forecast", ts_code=ts_code)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "ann_date" in df.columns:
        df = df.sort_values("ann_date", ascending=False)
    return _result(True, "tushare:forecast", _df_to_records(df.head(limit)))


def get_earnings_express(code: str, limit: int = 8) -> Dict[str, Any]:
    """业绩快报 (express)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    def _q():
        return _call("express", ts_code=ts_code)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "ann_date" in df.columns:
        df = df.sort_values("ann_date", ascending=False)
    return _result(True, "tushare:express", _df_to_records(df.head(limit)))


# ---------- 16. Dividends & adjust factor ----------

def get_dividends(code: str, limit: int = 30) -> Dict[str, Any]:
    """分红送股."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    def _q():
        return _call("dividend", ts_code=ts_code)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "ann_date" in df.columns:
        df = df.sort_values("ann_date", ascending=False)
    return _result(True, "tushare:dividend", _df_to_records(df.head(limit)))


def get_adj_factor(code: str, days: int = 250) -> Dict[str, Any]:
    """复权因子序列 (for computing qfq/hfq prices yourself)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("adj_factor", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:adj_factor", _df_to_records(df))


# ---------- 17. Shareholder count & change ----------

def get_shareholder_count(code: str, periods: int = 12) -> Dict[str, Any]:
    """股东户数 (stk_holdernumber)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - 5 * 365 * 86400)
    end = _date_str(_now())

    def _q():
        return _call("stk_holdernumber", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None or len(df) == 0:
        return _result(False, "all_failed", None, error=str(err))
    if "end_date" in df.columns:
        df = df.sort_values("end_date", ascending=False)
    return _result(True, "tushare:stk_holdernumber", _df_to_records(df.head(periods)))


def get_shareholder_trades(code: str, days: int = 365) -> Dict[str, Any]:
    """股东增减持 (stk_holdertrade)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("stk_holdertrade", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "ann_date" in df.columns:
        df = df.sort_values("ann_date", ascending=False)
    return _result(True, "tushare:stk_holdertrade", _df_to_records(df))


# ---------- 18. Margin trading detail ----------

def get_margin_detail(code: str, days: int = 30) -> Dict[str, Any]:
    """融资融券交易明细 (margin_detail)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("margin_detail", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:margin_detail", _df_to_records(df))


# ---------- 19. Northbound (Stock Connect) ----------

def get_north_holdings(code: str, days: int = 30) -> Dict[str, Any]:
    """沪深股通持股明细 (hk_hold)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("hk_hold", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:hk_hold", _df_to_records(df))


def get_north_flow(days: int = 30) -> Dict[str, Any]:
    """沪深港通资金流向 (moneyflow_hsgt) — daily total north money."""
    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("moneyflow_hsgt", start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:moneyflow_hsgt", _df_to_records(df))


# ---------- 20. Index data ----------

def get_index_basic(market: str = "SSE") -> Dict[str, Any]:
    """指数基本信息. market: SSE|SZSE|MSCI|CSI|CICC|SW|OTH"""
    def _q():
        return _call("index_basic", market=market)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    return _result(True, "tushare:index_basic", _df_to_records(df))


def get_index_kline(index_code: str, period: str = "daily",
                    start: str = "", end: str = "", limit: int = 120) -> Dict[str, Any]:
    """指数 K-line. index_code e.g. '000300.SH' (沪深300), '000001.SH' (上证), '399001.SZ' (深成).
    period: daily | weekly | monthly"""
    if not end:
        end = _date_str(_now())
    if not start:
        days_back = {"daily": 260, "weekly": 1200, "monthly": 3600}.get(period, 260)
        start = _date_str(_now() - days_back * 86400)
    api_map = {"daily": "index_daily", "weekly": "index_weekly", "monthly": "index_monthly"}
    api = api_map.get(period)
    if not api:
        return _result(False, "bad_param", None, error="period must be daily|weekly|monthly")

    def _q():
        return _call(api, ts_code=index_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False).head(limit)
    return _result(True, f"tushare:{api}", _df_to_records(df))


# ---------- 21. Limit prices & limit-board lists ----------

def get_limit_prices(code: str = "", trade_date: str = "", days: int = 30) -> Dict[str, Any]:
    """每日涨跌停价 (stk_limit). Pass `code` (recent N trade dates for that stock)
    OR `trade_date` (whole-market snapshot). If both empty, defaults to today's market.
    `days` only applies in the code mode."""
    if not code and not trade_date:
        trade_date = _date_str(_now())

    def _q():
        if code:
            ts_code = _to_ts_code(code)
            start = _date_str(_now() - days * 86400)
            end = _date_str(_now())
            return _call("stk_limit", ts_code=ts_code, start_date=start, end_date=end)
        return _call("stk_limit", trade_date=trade_date)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:stk_limit", _df_to_records(df))


def get_limit_board(trade_date: str = "", limit_type: str = "") -> Dict[str, Any]:
    """每日涨跌停股票列表 (limit_list_d). limit_type: 'U' (涨停) | 'D' (跌停) | 'Z' (炸板) | '' (all)."""
    if not trade_date:
        trade_date = _date_str(_now())

    def _q():
        kw = dict(trade_date=trade_date)
        if limit_type:
            kw["limit_type"] = limit_type
        return _call("limit_list_d", **kw)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    return _result(True, "tushare:limit_list_d", _df_to_records(df))


# ---------- 22. Block trades & suspended ----------

def get_block_trades(code: str, days: int = 365) -> Dict[str, Any]:
    """大宗交易 (block_trade)."""
    try:
        ts_code = _to_ts_code(code)
    except Exception as e:
        return _result(False, "init_failed", None, error=str(e))

    start = _date_str(_now() - days * 86400)
    end = _date_str(_now())

    def _q():
        return _call("block_trade", ts_code=ts_code, start_date=start, end_date=end)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    if "trade_date" in df.columns:
        df = df.sort_values("trade_date", ascending=False)
    return _result(True, "tushare:block_trade", _df_to_records(df))


def get_suspended(trade_date: str = "") -> Dict[str, Any]:
    """每日停复牌 (suspend_d). Empty trade_date defaults to today."""
    if not trade_date:
        trade_date = _date_str(_now())

    def _q():
        return _call("suspend_d", trade_date=trade_date)

    df, err = _retry(_q)
    if df is None:
        return _result(False, "all_failed", None, error=str(err))
    return _result(True, "tushare:suspend_d", _df_to_records(df))
