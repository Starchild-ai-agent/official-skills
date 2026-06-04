#!/usr/bin/env python3
"""Longbridge / LongPort OpenAPI CLI — self-contained, credentials from .env.

Cloud broker via the official `longport` SDK (formerly `longbridge`). Auth is
static-key: App Key + App Secret + Access Token. These map to the SDK's own env
var names LONGPORT_APP_KEY / LONGPORT_APP_SECRET / LONGPORT_ACCESS_TOKEN.

IMPORTANT — no paper/live discriminator exists in the API. Paper vs live is ONLY
determined by which Access Token you loaded; the API exposes no field, prefix, or
host to verify it. The --profile flag is therefore TRUST-DECLARED and echoed back
as paper_guard="config_declared". Live order placement requires --confirm-live.

Symbols use the Longbridge format: `700.HK`, `AAPL.US`, `000001.SZ`.

Subcommands: status | account | positions | orders | quote | history | place | cancel
Output: JSON on stdout. Requires `pip install longport`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def out(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    sys.exit(0 if payload.get("status") == "ok" else 1)


def err(msg: str) -> None:
    out({"status": "error", "error": msg})


def obj_get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def first(obj: Any, names: tuple[str, ...], default: Any = None) -> Any:
    for n in names:
        v = obj_get(obj, n, None)
        if v is not None:
            return v
    return default


def as_iter(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# --------------------------------------------------------------------------- #
# SDK plumbing — import either `longport` or legacy `longbridge`
# --------------------------------------------------------------------------- #
def require_openapi():
    for pkg in ("longport", "longbridge"):
        try:
            return __import__(f"{pkg}.openapi", fromlist=["openapi"])
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError("Longbridge SDK not installed; run `pip install longport`")


def missing_creds() -> list[str]:
    miss = []
    for var in ("LONGPORT_APP_KEY", "LONGPORT_APP_SECRET", "LONGPORT_ACCESS_TOKEN"):
        if not os.environ.get(var, "").strip():
            miss.append(var)
    return miss


def build_config(openapi):
    config_cls = getattr(openapi, "Config")
    ak = os.environ.get("LONGPORT_APP_KEY", "").strip()
    sk = os.environ.get("LONGPORT_APP_SECRET", "").strip()
    tok = os.environ.get("LONGPORT_ACCESS_TOKEN", "").strip()
    try:
        return config_cls(app_key=ak, app_secret=sk, access_token=tok)
    except TypeError:
        return config_cls.from_apikey(ak, sk, tok)


def trade_context(openapi):
    return getattr(openapi, "TradeContext")(build_config(openapi))


def quote_context(openapi):
    return getattr(openapi, "QuoteContext")(build_config(openapi))


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_status(profile: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "ok", "broker": "longbridge", "profile": profile,
        "paper_guard": "config_declared", "creds_present": not missing_creds(),
    }
    miss = missing_creds()
    if miss:
        report.update(status="error", error=f"missing in .env: {', '.join(miss)}")
        return report
    try:
        openapi = require_openapi()
        report["sdk_installed"] = True
    except ModuleNotFoundError as exc:
        report.update(status="error", sdk_installed=False, error=str(exc))
        return report
    try:
        trade = trade_context(openapi)
        bals = trade.account_balance()
        report["balance_currencies"] = [obj_get(b, "currency") for b in as_iter(bals)]
    except Exception as exc:  # noqa: BLE001
        report.update(status="error", error=str(exc))
    return report


def cmd_account(profile: str) -> dict[str, Any]:
    openapi = require_openapi()
    trade = trade_context(openapi)
    bals = trade.account_balance()
    rows = []
    for b in as_iter(bals):
        rows.append({
            "currency": obj_get(b, "currency"),
            "total_cash": obj_get(b, "total_cash"),
            "net_assets": obj_get(b, "net_assets"),
            "buy_power": obj_get(b, "buy_power"),
            "max_finance_amount": obj_get(b, "max_finance_amount"),
            "init_margin": obj_get(b, "init_margin"),
        })
    return {"status": "ok", "broker": "longbridge", "profile": profile,
            "paper_guard": "config_declared", "balances": rows}


def cmd_positions(profile: str) -> dict[str, Any]:
    openapi = require_openapi()
    trade = trade_context(openapi)
    resp = trade.stock_positions()
    channels = obj_get(resp, "channels", []) or as_iter(resp)
    rows = []
    for ch in as_iter(channels):
        positions = obj_get(ch, "positions", None)
        items = as_iter(positions) if positions is not None else [ch]
        for p in items:
            rows.append({
                "symbol": obj_get(p, "symbol"), "symbol_name": obj_get(p, "symbol_name"),
                "quantity": obj_get(p, "quantity"), "available_quantity": obj_get(p, "available_quantity"),
                "cost_price": obj_get(p, "cost_price"), "currency": obj_get(p, "currency"),
            })
    return {"status": "ok", "broker": "longbridge", "profile": profile,
            "paper_guard": "config_declared", "positions": rows}


_TERMINAL = {"filled", "canceled", "cancelled", "rejected", "expired", "partialwithdrawal"}


def order_to_dict(o: Any) -> dict[str, Any]:
    return {
        "order_id": obj_get(o, "order_id"), "symbol": obj_get(o, "symbol"),
        "side": str(obj_get(o, "side", "")), "order_type": str(obj_get(o, "order_type", "")),
        "quantity": obj_get(o, "quantity"), "executed_quantity": obj_get(o, "executed_quantity"),
        "price": obj_get(o, "price"), "executed_price": obj_get(o, "executed_price"),
        "status": str(obj_get(o, "status", "")), "submitted_at": str(obj_get(o, "submitted_at", "")),
    }


def cmd_orders(profile: str, executions: bool) -> dict[str, Any]:
    openapi = require_openapi()
    trade = trade_context(openapi)
    todays = trade.today_orders()
    rows = [order_to_dict(o) for o in as_iter(todays)]
    open_rows = [r for r in rows if str(r.get("status", "")).lower() not in _TERMINAL]
    res = {"status": "ok", "broker": "longbridge", "profile": profile,
           "paper_guard": "config_declared", "open_orders": open_rows}
    if executions:
        res["executions"] = [r for r in rows if str(r.get("status", "")).lower() == "filled"]
    return res


def cmd_quote(profile: str, symbol: str) -> dict[str, Any]:
    openapi = require_openapi()
    q = quote_context(openapi)
    clean = symbol.strip().upper()
    rows = as_iter(q.quote([clean]))
    item = rows[0] if rows else None
    return {"status": "ok", "broker": "longbridge", "symbol": clean, "quote": {
        "last": first(item, ("last_done",)), "open": first(item, ("open",)),
        "high": first(item, ("high",)), "low": first(item, ("low",)),
        "prev_close": first(item, ("prev_close",)), "volume": first(item, ("volume",)),
        "turnover": first(item, ("turnover",)), "time": str(first(item, ("timestamp",), "")),
    }}


_PERIOD = {"1m": "Min_1", "5m": "Min_5", "15m": "Min_15", "30m": "Min_30",
           "1h": "Min_60", "4h": "Min_60", "1d": "Day", "1w": "Week", "1M": "Month"}


def cmd_history(profile: str, symbol: str, period: str, limit: int) -> dict[str, Any]:
    openapi = require_openapi()
    q = quote_context(openapi)
    clean = symbol.strip().upper()
    period_cls = getattr(openapi, "Period")
    adjust_cls = getattr(openapi, "AdjustType")
    period_enum = getattr(period_cls, _PERIOD.get(period, "Day"), getattr(period_cls, "Day"))
    adjust_enum = getattr(adjust_cls, "NoAdjust", getattr(adjust_cls, "ForwardAdjust", None))
    bars = q.candlesticks(clean, period_enum, int(limit), adjust_enum)
    return {"status": "ok", "broker": "longbridge", "symbol": clean, "period": period,
            "bars": [{
                "time": str(first(b, ("timestamp",), "")), "open": first(b, ("open",)),
                "high": first(b, ("high",)), "low": first(b, ("low",)),
                "close": first(b, ("close",)), "volume": first(b, ("volume",)),
                "turnover": first(b, ("turnover",)),
            } for b in as_iter(bars)]}


_SIDE = {"buy": "Buy", "sell": "Sell"}
_OTYPE = {"market": "MO", "limit": "LO"}
_TIF = {"day": "Day", "gtc": "GoodTilCanceled"}


def cmd_place(args) -> dict[str, Any]:
    from decimal import Decimal

    side_key = (args.side or "").strip().lower()
    if side_key not in _SIDE:
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}
    if args.notional is not None:
        return {"status": "error", "error": "Longbridge requires --qty (shares), not --notional"}
    if args.qty is None:
        return {"status": "error", "error": "--qty is required"}
    qty = float(args.qty)
    if qty <= 0:
        return {"status": "error", "error": "quantity must be positive"}
    type_key = (args.type or "market").strip().lower()
    if type_key not in _OTYPE:
        return {"status": "error", "error": "type must be 'market' or 'limit'"}
    px = None
    if type_key == "limit":
        if args.limit_price is None:
            return {"status": "error", "error": "limit order requires --limit-price"}
        px = float(args.limit_price)
    tif_key = (args.tif or "day").strip().lower()
    if tif_key not in _TIF:
        return {"status": "error", "error": "tif must be 'day' or 'gtc'"}
    symbol = (args.symbol or "").strip().upper()
    if not symbol:
        return {"status": "error", "error": "symbol is required"}

    try:
        openapi = require_openapi()
        order_type_enum = getattr(getattr(openapi, "OrderType"), _OTYPE[type_key])
        side_enum = getattr(getattr(openapi, "OrderSide"), _SIDE[side_key])
        tif_enum = getattr(getattr(openapi, "TimeInForceType"), _TIF[tif_key])
        kwargs: dict[str, Any] = {
            "symbol": symbol, "order_type": order_type_enum, "side": side_enum,
            "submitted_quantity": Decimal(str(qty)), "time_in_force": tif_enum,
        }
        if type_key == "limit":
            kwargs["submitted_price"] = Decimal(str(px))
        trade = trade_context(openapi)
        resp = trade.submit_order(**kwargs)
        order_id = obj_get(resp, "order_id", None)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    if order_id is None:
        return {"status": "error", "error": "Longbridge did not return an order id"}
    return {"status": "ok", "broker": "longbridge", "order_id": str(order_id), "symbol": symbol,
            "side": side_key, "profile": args.profile, "paper_guard": "config_declared",
            "order_type": type_key, "quantity": qty, "limit_price": px, "time_in_force": tif_key}


def cmd_cancel(args) -> dict[str, Any]:
    oid = str(args.order_id or "").strip()
    if not oid:
        return {"status": "error", "error": "order_id is required"}
    try:
        openapi = require_openapi()
        trade = trade_context(openapi)
        trade.cancel_order(oid)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    res = {"status": "ok", "broker": "longbridge", "order_id": oid, "profile": args.profile,
           "paper_guard": "config_declared"}
    if args.symbol:
        res["symbol"] = args.symbol.strip().upper()
    return res


def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Longbridge / LongPort CLI")
    p.add_argument("--profile", default="paper", choices=["paper", "live"])
    p.add_argument("--confirm-live", action="store_true", help="required to place/cancel on a LIVE account")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("account"); sub.add_parser("positions")
    po = sub.add_parser("orders"); po.add_argument("--executions", action="store_true")
    pq = sub.add_parser("quote"); pq.add_argument("--symbol", required=True)
    ph = sub.add_parser("history"); ph.add_argument("--symbol", required=True); ph.add_argument("--period", default="1d"); ph.add_argument("--limit", type=int, default=90)
    pp = sub.add_parser("place")
    pp.add_argument("--symbol", required=True); pp.add_argument("--side", required=True)
    pp.add_argument("--qty", type=float); pp.add_argument("--notional", type=float)
    pp.add_argument("--type", default="market"); pp.add_argument("--limit-price", type=float)
    pp.add_argument("--tif", default="day")
    pc = sub.add_parser("cancel"); pc.add_argument("--order-id", required=True); pc.add_argument("--symbol")
    args = p.parse_args()

    if args.cmd in ("place", "cancel") and args.profile == "live" and not args.confirm_live:
        err("LIVE order blocked: re-run with --confirm-live to trade on a live account")

    try:
        dispatch = {
            "status": lambda: cmd_status(args.profile),
            "account": lambda: cmd_account(args.profile),
            "positions": lambda: cmd_positions(args.profile),
            "orders": lambda: cmd_orders(args.profile, args.executions),
            "quote": lambda: cmd_quote(args.profile, args.symbol),
            "history": lambda: cmd_history(args.profile, args.symbol, args.period, args.limit),
            "place": lambda: cmd_place(args),
            "cancel": lambda: cmd_cancel(args),
        }
        out(dispatch[args.cmd]())
    except ModuleNotFoundError as exc:
        err(str(exc))
    except Exception as exc:  # noqa: BLE001
        err(str(exc))


if __name__ == "__main__":
    main()
