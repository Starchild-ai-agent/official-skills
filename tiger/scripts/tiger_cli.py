#!/usr/bin/env python3
"""Tiger Brokers (TigerOpen) CLI — self-contained, credentials from workspace/.env.

Cloud broker via the official `tigeropen` SDK. Auth is RSA-signed static-key:
tiger_id + a local PKCS#1 private key (PEM) + account number. No OAuth, no token
refresh.

Paper/live guard (Tiger's documented discriminator): a paper account number is
exactly 17 numeric digits (e.g. 20191106192858300); standard/global accounts are
not. The chosen --profile must match the account format or the command fails
closed. Live order placement additionally requires --confirm-live.

Subcommands: status | account | positions | orders | quote | history | place | cancel
Output: JSON on stdout. Requires `pip install tigeropen`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

_PAPER_RE = re.compile(r"^\d{17}$")


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


def is_paper_account(account: str | None) -> bool:
    return bool(account) and bool(_PAPER_RE.match(account.strip()))


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def resolve_account(profile: str) -> str:
    if profile == "live":
        return (os.environ.get("TIGER_LIVE_ACCOUNT") or os.environ.get("TIGER_ACCOUNT") or "").strip()
    return (os.environ.get("TIGER_PAPER_ACCOUNT") or os.environ.get("TIGER_ACCOUNT") or "").strip()


def private_key_path() -> Path | None:
    """Return the path to the RSA private key.

    Prefer TIGER_PRIVATE_KEY_PATH. If TIGER_PRIVATE_KEY (inline PEM) is set,
    materialize it to a 0600 temp file once and reuse.
    """
    path = os.environ.get("TIGER_PRIVATE_KEY_PATH", "").strip()
    if path:
        return Path(path).expanduser()
    inline = os.environ.get("TIGER_PRIVATE_KEY", "").strip()
    if inline:
        tmp = Path.home() / ".tiger_private_key.pem"
        if not tmp.exists():
            tmp.write_text(inline.replace("\\n", "\n") + "\n", encoding="utf-8")
            try:
                tmp.chmod(0o600)
            except OSError:
                pass
        return tmp
    return None


def assert_profile(profile: str, account: str) -> None:
    if not account:
        raise RuntimeError("Tiger account not configured (TIGER_ACCOUNT / TIGER_PAPER_ACCOUNT / TIGER_LIVE_ACCOUNT)")
    paper = is_paper_account(account)
    if profile == "paper" and not paper:
        raise RuntimeError("profile=paper but account is not a 17-digit Tiger paper account")
    if profile == "live" and paper:
        raise RuntimeError("profile=live but account is a 17-digit Tiger paper account; use --profile paper")


def client_config(profile: str):
    from tigeropen.common.util.signature_utils import read_private_key  # type: ignore
    from tigeropen.tiger_open_config import TigerOpenClientConfig  # type: ignore

    tiger_id = os.environ.get("TIGER_ID", "").strip()
    if not tiger_id:
        raise RuntimeError("missing TIGER_ID in .env")
    key_path = private_key_path()
    if not key_path or not key_path.exists():
        raise RuntimeError("Tiger private key not found (set TIGER_PRIVATE_KEY_PATH or TIGER_PRIVATE_KEY)")
    account = resolve_account(profile)
    assert_profile(profile, account)
    cfg = TigerOpenClientConfig()
    cfg.private_key = read_private_key(str(key_path))
    cfg.tiger_id = tiger_id
    cfg.account = account
    return cfg, account


def trade_client(profile: str):
    from tigeropen.trade.trade_client import TradeClient  # type: ignore

    cfg, account = client_config(profile)
    return TradeClient(cfg), account


def quote_client(profile: str):
    from tigeropen.quote.quote_client import QuoteClient  # type: ignore

    cfg, _ = client_config(profile)
    return QuoteClient(cfg)


def safe_call(obj: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(obj, name, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except TypeError:
        try:
            return fn(*args)
        except TypeError:
            return fn()


# --------------------------------------------------------------------------- #
# converters
# --------------------------------------------------------------------------- #
def asset_to_dict(i: Any) -> dict[str, Any]:
    return {
        "currency": first(i, ("currency",)),
        "cash": first(i, ("cash", "cash_balance")),
        "net_liquidation": first(i, ("net_liquidation", "net_liquidation_value")),
        "buying_power": first(i, ("buying_power",)),
        "unrealized_pnl": first(i, ("unrealized_pnl", "unrealized_pl")),
    }


def position_to_dict(i: Any) -> dict[str, Any]:
    c = obj_get(i, "contract")
    return {
        "symbol": first(c, ("symbol",)) or first(i, ("symbol",)),
        "currency": first(c, ("currency",)) or first(i, ("currency",)),
        "sec_type": first(c, ("sec_type", "secType")),
        "quantity": first(i, ("quantity", "position_qty", "position")),
        "average_cost": first(i, ("average_cost", "avg_cost")),
        "market_value": first(i, ("market_value",)),
        "unrealized_pnl": first(i, ("unrealized_pnl", "unrealized_pl")),
    }


def order_to_dict(i: Any) -> dict[str, Any]:
    c = obj_get(i, "contract")
    return {
        "order_id": first(i, ("id", "order_id")),
        "symbol": first(c, ("symbol",)) or first(i, ("symbol",)),
        "action": first(i, ("action",)), "order_type": first(i, ("order_type", "type")),
        "quantity": first(i, ("quantity",)), "filled": first(i, ("filled",)),
        "remaining": first(i, ("remaining",)), "avg_fill_price": first(i, ("avg_fill_price",)),
        "limit_price": first(i, ("limit_price",)), "status": str(first(i, ("status",)) or ""),
    }


def quote_to_dict(i: Any) -> dict[str, Any]:
    return {
        "symbol": first(i, ("symbol",)), "last": first(i, ("latest_price", "last_price", "latest")),
        "bid": first(i, ("bid_price", "bid")), "ask": first(i, ("ask_price", "ask")),
        "open": first(i, ("open",)), "high": first(i, ("high",)), "low": first(i, ("low",)),
        "prev_close": first(i, ("pre_close", "prev_close")), "volume": first(i, ("volume",)),
        "time": str(first(i, ("latest_time", "time"), "")),
    }


def bar_to_dict(i: Any) -> dict[str, Any]:
    return {
        "time": str(first(i, ("time", "date"), "")), "open": first(i, ("open",)),
        "high": first(i, ("high",)), "low": first(i, ("low",)),
        "close": first(i, ("close",)), "volume": first(i, ("volume",)),
    }


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_status(profile: str) -> dict[str, Any]:
    account = resolve_account(profile)
    report: dict[str, Any] = {
        "status": "ok", "broker": "tiger", "profile": profile,
        "account": (account[:4] + "***") if account else None,
        "is_paper": is_paper_account(account),
        "tiger_id_present": bool(os.environ.get("TIGER_ID")),
        "private_key_present": bool(private_key_path() and private_key_path().exists()),
    }
    try:
        import tigeropen  # noqa: F401
        report["sdk_installed"] = True
    except ModuleNotFoundError:
        report.update(status="error", sdk_installed=False, error="tigeropen not installed; run `pip install tigeropen`")
        return report
    try:
        assert_profile(profile, account)
        trade, acct = trade_client(profile)
        assets = safe_call(trade, "get_assets", account=acct) or safe_call(trade, "get_assets")
        report["assets_currency"] = [obj_get(a, "currency") for a in as_iter(assets)]
    except Exception as exc:  # noqa: BLE001
        report.update(status="error", error=str(exc))
    return report


def cmd_account(profile: str) -> dict[str, Any]:
    trade, acct = trade_client(profile)
    assets = safe_call(trade, "get_assets", account=acct) or safe_call(trade, "get_assets")
    return {"status": "ok", "broker": "tiger", "profile": profile, "account": acct,
            "is_paper": is_paper_account(acct), "assets": [asset_to_dict(a) for a in as_iter(assets)]}


def cmd_positions(profile: str) -> dict[str, Any]:
    trade, acct = trade_client(profile)
    pos = safe_call(trade, "get_positions", account=acct) or safe_call(trade, "get_positions")
    return {"status": "ok", "broker": "tiger", "profile": profile, "account": acct,
            "positions": [position_to_dict(p) for p in as_iter(pos)]}


def cmd_orders(profile: str, executions: bool) -> dict[str, Any]:
    trade, acct = trade_client(profile)
    op = safe_call(trade, "get_open_orders", account=acct) or safe_call(trade, "get_open_orders")
    res = {"status": "ok", "broker": "tiger", "profile": profile, "account": acct,
           "open_orders": [order_to_dict(o) for o in as_iter(op)]}
    if executions:
        fl = safe_call(trade, "get_filled_orders", account=acct) or safe_call(trade, "get_filled_orders")
        res["executions"] = [order_to_dict(o) for o in as_iter(fl)]
    return res


def cmd_quote(profile: str, symbol: str) -> dict[str, Any]:
    q = quote_client(profile)
    clean = symbol.strip().upper()
    briefs = safe_call(q, "get_stock_briefs", [clean])
    rows = [quote_to_dict(i) for i in as_iter(briefs)]
    return {"status": "ok", "broker": "tiger", "symbol": clean, "quote": rows[0] if rows else {}}


_PERIOD = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
           "1h": "60min", "4h": "60min", "1d": "day", "1w": "week", "1M": "month"}


def cmd_history(profile: str, symbol: str, period: str, limit: int) -> dict[str, Any]:
    q = quote_client(profile)
    clean = symbol.strip().upper()
    bars = safe_call(q, "get_bars", [clean], period=_PERIOD.get(period, "day"), limit=int(limit))
    return {"status": "ok", "broker": "tiger", "symbol": clean, "period": period,
            "bars": [bar_to_dict(b) for b in as_iter(bars)]}


_ACTION = {"buy": "BUY", "sell": "SELL"}
_TIF = {"day": "DAY", "gtc": "GTC"}


def cmd_place(args) -> dict[str, Any]:
    side_key = (args.side or "").strip().lower()
    action = _ACTION.get(side_key)
    if action is None:
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}
    if args.notional is not None:
        return {"status": "error", "error": "Tiger requires --qty (units), not --notional"}
    if args.qty is None:
        return {"status": "error", "error": "--qty is required"}
    qty = float(args.qty)
    if qty <= 0:
        return {"status": "error", "error": "quantity must be positive"}
    type_key = (args.type or "market").strip().lower()
    if type_key not in ("market", "limit"):
        return {"status": "error", "error": "type must be 'market' or 'limit'"}
    px = None
    if type_key == "limit":
        if args.limit_price is None:
            return {"status": "error", "error": "limit order requires --limit-price"}
        px = float(args.limit_price)
    tif = _TIF.get((args.tif or "day").strip().lower())
    if tif is None:
        return {"status": "error", "error": "tif must be 'day' or 'gtc'"}
    symbol = (args.symbol or "").strip().upper()
    if not symbol:
        return {"status": "error", "error": "symbol is required"}

    try:
        from tigeropen.common.util.contract_utils import stock_contract  # type: ignore
        from tigeropen.common.util.order_utils import limit_order, market_order  # type: ignore
        trade, acct = trade_client(args.profile)
        if is_paper_account(acct) and tif == "GTC":
            tif = "DAY"  # paper does not support GTC
        contract = stock_contract(symbol=symbol, currency=args.currency)
        if type_key == "limit":
            order = limit_order(account=acct, contract=contract, action=action, quantity=qty, limit_price=px, time_in_force=tif)
        else:
            order = market_order(account=acct, contract=contract, action=action, quantity=qty, time_in_force=tif)
        returned = trade.place_order(order)
        order_id = obj_get(order, "id", None) or returned
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    if order_id is None:
        return {"status": "error", "error": "Tiger did not return an order id"}
    reason = obj_get(order, "reason", None)
    ostatus = str(obj_get(order, "status", "") or "")
    if ostatus.strip().lower() in ("rejected", "inactive") or (reason and str(reason).strip()):
        return {"status": "error", "error": f"Tiger rejected order: {reason or ostatus}", "order_id": str(order_id)}
    return {"status": "ok", "broker": "tiger", "order_id": str(order_id), "symbol": symbol,
            "side": side_key, "profile": args.profile, "account": acct, "is_paper": is_paper_account(acct),
            "order_type": type_key, "quantity": qty, "limit_price": px, "time_in_force": tif}


def cmd_cancel(args) -> dict[str, Any]:
    if not str(args.order_id or "").strip():
        return {"status": "error", "error": "order_id is required"}
    try:
        trade, acct = trade_client(args.profile)
        try:
            oid: Any = int(args.order_id)
        except (TypeError, ValueError):
            oid = args.order_id
        try:
            trade.cancel_order(id=oid)
        except TypeError:
            trade.cancel_order(order_id=oid)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    res = {"status": "ok", "broker": "tiger", "order_id": str(args.order_id), "profile": args.profile, "account": acct}
    if args.symbol:
        res["symbol"] = args.symbol.strip().upper()
    return res


def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Tiger Brokers CLI")
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
    pp.add_argument("--tif", default="day"); pp.add_argument("--currency", default="USD")
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
        err(f"tigeropen not installed; run `pip install tigeropen` ({exc})")
    except Exception as exc:  # noqa: BLE001
        err(str(exc))


if __name__ == "__main__":
    main()
