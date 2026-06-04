#!/usr/bin/env python3
"""Alpaca broker CLI — self-contained, credentials from workspace/.env.

Cloud REST broker (no local gateway). Paper and live use SEPARATE key pairs and
SEPARATE hosts, so a paper key physically cannot touch the live account — that
is the real paper/live guard. Live order placement additionally requires the
explicit --confirm-live flag.

Subcommands: status | account | positions | orders | quote | history | place | cancel
Output: JSON on stdout. Requires `pip install alpaca-py`.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

PAPER_HOST = "https://paper-api.alpaca.markets"
LIVE_HOST = "https://api.alpaca.markets"


# --------------------------------------------------------------------------- #
# env + helpers
# --------------------------------------------------------------------------- #
def load_env() -> None:
    """Load workspace/.env into os.environ without external deps."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


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


def as_iter(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def resolve_keys(profile: str) -> tuple[str, str, bool]:
    """Return (api_key, secret_key, is_paper) for the chosen profile.

    Paper uses ALPACA_API_KEY / ALPACA_SECRET_KEY.
    Live uses ALPACA_LIVE_API_KEY / ALPACA_LIVE_SECRET_KEY.
    """
    if profile == "live":
        key = os.environ.get("ALPACA_LIVE_API_KEY", "").strip()
        secret = os.environ.get("ALPACA_LIVE_SECRET_KEY", "").strip()
        return key, secret, False
    key = os.environ.get("ALPACA_API_KEY", "").strip()
    secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    return key, secret, True


def trading_client(profile: str):
    from alpaca.trading.client import TradingClient  # type: ignore

    key, secret, is_paper = resolve_keys(profile)
    if not key or not secret:
        which = "ALPACA_LIVE_API_KEY/ALPACA_LIVE_SECRET_KEY" if profile == "live" else "ALPACA_API_KEY/ALPACA_SECRET_KEY"
        raise RuntimeError(f"missing {which} in .env")
    return TradingClient(key, secret, paper=is_paper)


def data_client(profile: str):
    from alpaca.data.historical import StockHistoricalDataClient  # type: ignore

    key, secret, _ = resolve_keys(profile)
    if not key or not secret:
        raise RuntimeError("missing Alpaca data keys in .env")
    return StockHistoricalDataClient(key, secret)


def data_feed():
    from alpaca.data.enums import DataFeed  # type: ignore

    feed = os.environ.get("ALPACA_FEED", "iex").strip().lower()
    return DataFeed.SIP if feed == "sip" else DataFeed.IEX


# --------------------------------------------------------------------------- #
# read ops
# --------------------------------------------------------------------------- #
def cmd_status(profile: str) -> dict[str, Any]:
    key, secret, is_paper = resolve_keys(profile)
    report: dict[str, Any] = {
        "status": "ok",
        "broker": "alpaca",
        "profile": profile,
        "is_paper": is_paper,
        "host": PAPER_HOST if is_paper else LIVE_HOST,
        "keys_present": bool(key and secret),
    }
    try:
        import alpaca  # noqa: F401
        report["sdk_installed"] = True
    except ModuleNotFoundError:
        report["status"] = "error"
        report["sdk_installed"] = False
        report["error"] = "alpaca-py not installed; run `pip install alpaca-py`"
        return report
    if not (key and secret):
        report["status"] = "error"
        report["error"] = "Alpaca keys missing in .env"
        return report
    try:
        acct = trading_client(profile).get_account()
        report["account"] = {
            "account_number": obj_get(acct, "account_number"),
            "status": str(obj_get(acct, "status", "")),
            "currency": obj_get(acct, "currency"),
            "buying_power": obj_get(acct, "buying_power"),
        }
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = str(exc)
    return report


def cmd_account(profile: str) -> dict[str, Any]:
    a = trading_client(profile).get_account()
    _, _, is_paper = resolve_keys(profile)
    return {
        "status": "ok", "broker": "alpaca", "profile": profile, "is_paper": is_paper,
        "account": {
            "account_number": obj_get(a, "account_number"),
            "status": str(obj_get(a, "status", "")),
            "currency": obj_get(a, "currency"),
            "cash": obj_get(a, "cash"),
            "equity": obj_get(a, "equity"),
            "buying_power": obj_get(a, "buying_power"),
            "portfolio_value": obj_get(a, "portfolio_value"),
            "pattern_day_trader": obj_get(a, "pattern_day_trader"),
            "trading_blocked": obj_get(a, "trading_blocked"),
        },
    }


def position_to_dict(p: Any) -> dict[str, Any]:
    return {
        "symbol": obj_get(p, "symbol"), "side": str(obj_get(p, "side", "")),
        "quantity": obj_get(p, "qty"), "average_cost": obj_get(p, "avg_entry_price"),
        "market_value": obj_get(p, "market_value"), "current_price": obj_get(p, "current_price"),
        "unrealized_pnl": obj_get(p, "unrealized_pl"), "cost_basis": obj_get(p, "cost_basis"),
    }


def cmd_positions(profile: str) -> dict[str, Any]:
    rows = [position_to_dict(p) for p in as_iter(trading_client(profile).get_all_positions())]
    return {"status": "ok", "broker": "alpaca", "profile": profile, "positions": rows}


def order_to_dict(o: Any) -> dict[str, Any]:
    return {
        "order_id": str(obj_get(o, "id", "")), "symbol": obj_get(o, "symbol"),
        "side": str(obj_get(o, "side", "")),
        "order_type": str(obj_get(o, "order_type", "") or obj_get(o, "type", "")),
        "quantity": obj_get(o, "qty"), "notional": obj_get(o, "notional"),
        "filled_qty": obj_get(o, "filled_qty"), "filled_avg_price": obj_get(o, "filled_avg_price"),
        "limit_price": obj_get(o, "limit_price"), "status": str(obj_get(o, "status", "")),
        "submitted_at": str(obj_get(o, "submitted_at", "")),
    }


def cmd_orders(profile: str, executions: bool) -> dict[str, Any]:
    client = trading_client(profile)
    from alpaca.trading.requests import GetOrdersRequest  # type: ignore
    from alpaca.trading.enums import QueryOrderStatus  # type: ignore

    open_orders = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))
    result = {
        "status": "ok", "broker": "alpaca", "profile": profile,
        "open_orders": [order_to_dict(o) for o in as_iter(open_orders)],
    }
    if executions:
        closed = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.CLOSED))
        result["executions"] = [order_to_dict(o) for o in as_iter(closed) if obj_get(o, "filled_qty")]
    return result


def cmd_quote(profile: str, symbol: str) -> dict[str, Any]:
    from alpaca.data.requests import StockLatestQuoteRequest  # type: ignore

    clean = symbol.strip().upper()
    client = data_client(profile)
    quotes = client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=clean, feed=data_feed()))
    q = quotes.get(clean) if isinstance(quotes, Mapping) else obj_get(quotes, clean)
    return {
        "status": "ok", "broker": "alpaca", "symbol": clean,
        "quote": {
            "bid": obj_get(q, "bid_price"), "ask": obj_get(q, "ask_price"),
            "bid_size": obj_get(q, "bid_size"), "ask_size": obj_get(q, "ask_size"),
            "time": str(obj_get(q, "timestamp", "")),
        },
    }


_PERIOD = {
    "1m": ("Minute", 1), "5m": ("Minute", 5), "15m": ("Minute", 15), "30m": ("Minute", 30),
    "1h": ("Hour", 1), "1d": ("Day", 1), "1w": ("Week", 1), "1M": ("Month", 1),
}


def cmd_history(profile: str, symbol: str, period: str, limit: int) -> dict[str, Any]:
    from alpaca.data.requests import StockBarsRequest  # type: ignore
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit  # type: ignore

    unit_name, amount = _PERIOD.get(period, ("Day", 1))
    tf = TimeFrame(amount, getattr(TimeFrameUnit, unit_name))
    clean = symbol.strip().upper()
    client = data_client(profile)
    bars = client.get_stock_bars(StockBarsRequest(symbol_or_symbols=clean, timeframe=tf, limit=int(limit), feed=data_feed()))
    rows = bars.data.get(clean, []) if hasattr(bars, "data") else as_iter(bars)
    return {
        "status": "ok", "broker": "alpaca", "symbol": clean, "period": period,
        "bars": [{
            "time": str(obj_get(b, "timestamp", "")), "open": obj_get(b, "open"),
            "high": obj_get(b, "high"), "low": obj_get(b, "low"),
            "close": obj_get(b, "close"), "volume": obj_get(b, "volume"),
        } for b in as_iter(rows)],
    }


# --------------------------------------------------------------------------- #
# write ops (fail-closed)
# --------------------------------------------------------------------------- #
def cmd_place(args) -> dict[str, Any]:
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest  # type: ignore
    from alpaca.trading.enums import OrderSide, TimeInForce  # type: ignore

    side_token = (args.side or "").strip().lower()
    if side_token not in ("buy", "sell"):
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}
    if (args.qty is None) == (args.notional is None):
        return {"status": "error", "error": "provide exactly one of --qty or --notional"}
    type_token = (args.type or "market").strip().lower()
    if type_token not in ("market", "limit"):
        return {"status": "error", "error": "type must be 'market' or 'limit'"}
    if type_token == "limit" and args.limit_price is None:
        return {"status": "error", "error": "limit order requires --limit-price"}

    symbol = (args.symbol or "").strip().upper()
    if not symbol:
        return {"status": "error", "error": "symbol is required"}

    side = OrderSide.BUY if side_token == "buy" else OrderSide.SELL
    tif = TimeInForce.GTC if (args.tif or "day").strip().lower() == "gtc" else TimeInForce.DAY

    common = {"symbol": symbol, "side": side, "time_in_force": tif}
    if args.qty is not None:
        common["qty"] = float(args.qty)
    else:
        common["notional"] = float(args.notional)

    try:
        if type_token == "limit":
            request = LimitOrderRequest(limit_price=float(args.limit_price), **common)
        else:
            request = MarketOrderRequest(**common)
        order = trading_client(args.profile).submit_order(request)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}

    _, _, is_paper = resolve_keys(args.profile)
    return {
        "status": "ok", "broker": "alpaca", "order_id": str(obj_get(order, "id", "")),
        "symbol": symbol, "side": side_token, "profile": args.profile, "is_paper": is_paper,
        "order_type": type_token, "quantity": args.qty, "notional": args.notional,
        "limit_price": args.limit_price, "order_status": str(obj_get(order, "status", "")),
        "filled_qty": obj_get(order, "filled_qty"),
    }


def cmd_cancel(args) -> dict[str, Any]:
    oid = str(args.order_id or "").strip()
    if not oid:
        return {"status": "error", "error": "order_id is required"}
    try:
        trading_client(args.profile).cancel_order_by_id(oid)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    res = {"status": "ok", "broker": "alpaca", "order_id": oid, "profile": args.profile}
    if args.symbol:
        res["symbol"] = args.symbol.strip().upper()
    return res


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Alpaca broker CLI")
    p.add_argument("--profile", default="paper", choices=["paper", "live"], help="account environment (default: paper)")
    p.add_argument("--confirm-live", action="store_true", help="required to place/cancel on a LIVE account")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("account")
    sub.add_parser("positions")
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

    # live safety gate for write ops
    if args.cmd in ("place", "cancel") and args.profile == "live" and not args.confirm_live:
        err("LIVE order blocked: re-run with --confirm-live to trade on a live account")

    try:
        if args.cmd == "status":
            out(cmd_status(args.profile))
        elif args.cmd == "account":
            out(cmd_account(args.profile))
        elif args.cmd == "positions":
            out(cmd_positions(args.profile))
        elif args.cmd == "orders":
            out(cmd_orders(args.profile, args.executions))
        elif args.cmd == "quote":
            out(cmd_quote(args.profile, args.symbol))
        elif args.cmd == "history":
            out(cmd_history(args.profile, args.symbol, args.period, args.limit))
        elif args.cmd == "place":
            out(cmd_place(args))
        elif args.cmd == "cancel":
            out(cmd_cancel(args))
    except ModuleNotFoundError as exc:
        err(f"alpaca-py not installed; run `pip install alpaca-py` ({exc})")
    except Exception as exc:  # noqa: BLE001
        err(str(exc))


if __name__ == "__main__":
    main()
