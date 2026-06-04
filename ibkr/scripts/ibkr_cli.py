#!/usr/bin/env python3
"""Interactive Brokers (IBKR) CLI — self-contained, connects to a LOCAL gateway.

IBKR has no key-based public API. You must run TWS or IB Gateway on a machine
yourself, log in, and enable API socket clients. This CLI connects over a local
socket (default 127.0.0.1:7497 paper / 7496 live). Credentials live in TWS,
never here. See SKILL.md for setup.

Ports: 7497 = TWS paper, 7496 = TWS live, 4002 = IB Gateway paper, 4001 = live.
Paper accounts start with "DU"; live accounts start with "U". The --profile flag
selects the default port and guards the account prefix. Live placement requires
--confirm-live AND a non-readonly connection.

Subcommands: status | account | positions | orders | quote | history | place | cancel
Output: JSON on stdout. Requires `pip install ib_async` AND a running TWS/Gateway.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_HOST = "127.0.0.1"
PROFILE_PORTS = {"paper": 7497, "live": 7496}


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


def env_host() -> str:
    return os.environ.get("IBKR_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST


def env_port(profile: str) -> int:
    explicit = os.environ.get("IBKR_PORT", "").strip()
    if explicit:
        try:
            return int(explicit)
        except ValueError:
            pass
    return PROFILE_PORTS.get(profile, 7497)


def env_client_id() -> int:
    try:
        return int(os.environ.get("IBKR_CLIENT_ID", "1") or 1)
    except ValueError:
        return 1


def env_account() -> str:
    return os.environ.get("IBKR_ACCOUNT", "").strip()


def tcp_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def require_ib():
    import ib_async  # type: ignore
    return ib_async


def connect(profile: str, *, readonly: bool):
    host, port = env_host(), env_port(profile)
    if not tcp_port_open(host, port):
        raise RuntimeError(
            f"No TWS / IB Gateway socket at {host}:{port}. "
            "Open TWS or IB Gateway, log in, and enable API socket clients (see SKILL.md)."
        )
    module = require_ib()
    ib = module.IB()
    try:
        ib.connect(host, port, clientId=env_client_id(), timeout=15.0,
                   readonly=readonly, account=env_account() or "")
    except TypeError:
        ib.connect(host, port, clientId=env_client_id(), timeout=15.0)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Could not connect to TWS / IB Gateway at {host}:{port}: {exc}") from exc
    return ib


def disconnect(ib: Any) -> None:
    try:
        ib.disconnect()
    except Exception:  # noqa: BLE001
        pass


def managed_accounts(ib: Any) -> list[str]:
    accounts = getattr(ib, "managedAccounts", lambda: [])()
    if isinstance(accounts, str):
        return [a.strip() for a in accounts.split(",") if a.strip()]
    return [str(a) for a in accounts if str(a)]


def assert_profile(profile: str, accounts: Iterable[str]) -> None:
    acc = [a for a in accounts if a]
    if profile != "paper" or not acc:
        return
    has_paper = any(a.upper().startswith("DU") for a in acc)
    has_live = any(a.upper().startswith("U") and not a.upper().startswith("DU") for a in acc)
    if not has_paper or has_live:
        raise RuntimeError(
            "profile=paper but connected accounts are not IBKR paper (DU...) accounts; use --profile live if intended"
        )


def make_contract(ib_module, symbol: str, exchange: str, currency: str, sec_type: str):
    sym = symbol.strip().upper()
    stype = sec_type.strip().upper()
    if stype == "STK" and hasattr(ib_module, "Stock"):
        return ib_module.Stock(sym, exchange, currency)
    c = ib_module.Contract()
    c.symbol, c.secType, c.exchange, c.currency = sym, stype, exchange, currency
    return c


def qualify(ib: Any, contract: Any) -> None:
    try:
        ib.qualifyContracts(contract)
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- #
# read ops
# --------------------------------------------------------------------------- #
def cmd_status(profile: str) -> dict[str, Any]:
    host, port = env_host(), env_port(profile)
    report: dict[str, Any] = {
        "status": "ok", "broker": "ibkr", "profile": profile,
        "gateway": {"host": host, "port": port, "open": tcp_port_open(host, port)},
    }
    try:
        require_ib()
        report["sdk_installed"] = True
    except ModuleNotFoundError:
        report.update(status="error", sdk_installed=False, error="ib_async not installed; run `pip install ib_async`")
        return report
    if not report["gateway"]["open"]:
        report.update(status="error", error=f"TWS / IB Gateway not reachable at {host}:{port}")
        return report
    ib = connect(profile, readonly=True)
    try:
        accounts = managed_accounts(ib)
        assert_profile(profile, accounts)
        report["accounts"] = accounts
    except Exception as exc:  # noqa: BLE001
        report.update(status="error", error=str(exc))
    finally:
        disconnect(ib)
    return report


def cmd_account(profile: str) -> dict[str, Any]:
    ib = connect(profile, readonly=True)
    try:
        accounts = managed_accounts(ib)
        acc = env_account()
        summary = list(ib.accountSummary(acc)) if acc else list(ib.accountSummary())
        rows = [{"account": obj_get(i, "account"), "tag": obj_get(i, "tag"),
                 "value": obj_get(i, "value"), "currency": obj_get(i, "currency")} for i in summary]
        all_acc = sorted(set(accounts) | {str(r["account"]) for r in rows if r["account"]})
        assert_profile(profile, all_acc)
        return {"status": "ok", "broker": "ibkr", "profile": profile, "accounts": all_acc, "summary": rows}
    finally:
        disconnect(ib)


def cmd_positions(profile: str) -> dict[str, Any]:
    ib = connect(profile, readonly=True)
    try:
        accounts = managed_accounts(ib)
        assert_profile(profile, accounts)
        acc = env_account()
        rows = []
        for it in ib.positions():
            a = str(obj_get(it, "account", ""))
            if acc and a and a != acc:
                continue
            c = obj_get(it, "contract")
            rows.append({"account": a, "symbol": obj_get(c, "symbol"), "local_symbol": obj_get(c, "localSymbol"),
                         "sec_type": obj_get(c, "secType"), "exchange": obj_get(c, "exchange"),
                         "currency": obj_get(c, "currency"), "con_id": obj_get(c, "conId"),
                         "position": obj_get(it, "position"), "avg_cost": obj_get(it, "avgCost")})
        return {"status": "ok", "broker": "ibkr", "profile": profile, "positions": rows}
    finally:
        disconnect(ib)


def trade_to_dict(t: Any) -> dict[str, Any]:
    c = obj_get(t, "contract")
    o = obj_get(t, "order")
    s = obj_get(t, "orderStatus")
    return {"order_id": obj_get(o, "orderId"), "symbol": obj_get(c, "symbol"),
            "action": obj_get(o, "action"), "order_type": obj_get(o, "orderType"),
            "quantity": obj_get(o, "totalQuantity"), "limit_price": obj_get(o, "lmtPrice"),
            "tif": obj_get(o, "tif"), "status": str(obj_get(s, "status", "")),
            "filled": obj_get(s, "filled"), "remaining": obj_get(s, "remaining"),
            "avg_fill_price": obj_get(s, "avgFillPrice")}


def cmd_orders(profile: str, executions: bool) -> dict[str, Any]:
    ib = connect(profile, readonly=True)
    try:
        accounts = managed_accounts(ib)
        assert_profile(profile, accounts)
        trades = ib.openTrades() or []
        res = {"status": "ok", "broker": "ibkr", "profile": profile,
               "open_orders": [trade_to_dict(t) for t in trades]}
        if executions:
            fills = ib.fills() or []
            ex = []
            for f in fills:
                e = obj_get(f, "execution")
                c = obj_get(f, "contract")
                ex.append({"symbol": obj_get(c, "symbol"), "exec_id": obj_get(e, "execId"),
                           "account": obj_get(e, "acctNumber"), "side": obj_get(e, "side"),
                           "shares": obj_get(e, "shares"), "price": obj_get(e, "price"),
                           "time": str(obj_get(e, "time", ""))})
            res["executions"] = ex
        return res
    finally:
        disconnect(ib)


def cmd_quote(profile: str, symbol: str, exchange: str, currency: str, sec_type: str) -> dict[str, Any]:
    module = require_ib()
    ib = connect(profile, readonly=True)
    try:
        contract = make_contract(module, symbol, exchange, currency, sec_type)
        qualify(ib, contract)
        ticker = ib.reqMktData(contract, "", False, False)
        ib.sleep(2.0)
        try:
            ib.cancelMktData(contract)
        except Exception:  # noqa: BLE001
            pass
        return {"status": "ok", "broker": "ibkr", "symbol": symbol.upper(), "exchange": exchange, "currency": currency,
                "quote": {"bid": obj_get(ticker, "bid"), "ask": obj_get(ticker, "ask"), "last": obj_get(ticker, "last"),
                          "close": obj_get(ticker, "close"), "volume": obj_get(ticker, "volume"),
                          "time": str(obj_get(ticker, "time", ""))}}
    finally:
        disconnect(ib)


def cmd_history(profile: str, symbol: str, exchange: str, currency: str, sec_type: str,
                duration: str, bar_size: str) -> dict[str, Any]:
    module = require_ib()
    ib = connect(profile, readonly=True)
    try:
        contract = make_contract(module, symbol, exchange, currency, sec_type)
        qualify(ib, contract)
        bars = ib.reqHistoricalData(contract, endDateTime="", durationStr=duration, barSizeSetting=bar_size,
                                    whatToShow="TRADES", useRTH=True, formatDate=1)
        return {"status": "ok", "broker": "ibkr", "symbol": symbol.upper(), "duration": duration, "bar_size": bar_size,
                "bars": [{"date": str(obj_get(b, "date", "")), "open": obj_get(b, "open"), "high": obj_get(b, "high"),
                          "low": obj_get(b, "low"), "close": obj_get(b, "close"), "volume": obj_get(b, "volume")}
                         for b in bars]}
    finally:
        disconnect(ib)


# --------------------------------------------------------------------------- #
# write ops (fail-closed)
# --------------------------------------------------------------------------- #
def cmd_place(args) -> dict[str, Any]:
    side_token = (args.side or "").strip().lower()
    if side_token not in ("buy", "sell"):
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}
    if args.notional is not None:
        return {"status": "error", "error": "IBKR requires --qty (units), not --notional"}
    if args.qty is None:
        return {"status": "error", "error": "--qty is required"}
    qty = float(args.qty)
    if qty <= 0:
        return {"status": "error", "error": "quantity must be positive"}
    type_token = (args.type or "market").strip().lower()
    if type_token not in ("market", "limit"):
        return {"status": "error", "error": "type must be 'market' or 'limit'"}
    px = None
    if type_token == "limit":
        if args.limit_price is None:
            return {"status": "error", "error": "limit order requires --limit-price"}
        px = float(args.limit_price)
    tif = (args.tif or "day").strip().upper()
    if tif not in ("DAY", "GTC"):
        return {"status": "error", "error": "tif must be 'day' or 'gtc'"}
    symbol = (args.symbol or "").strip().upper()
    if not symbol:
        return {"status": "error", "error": "symbol is required"}

    module = require_ib()
    ib = connect(args.profile, readonly=False)
    try:
        accounts = managed_accounts(ib)
        assert_profile(args.profile, accounts)
        contract = make_contract(module, symbol, args.exchange, args.currency, args.sec_type)
        qualify(ib, contract)
        action = "BUY" if side_token == "buy" else "SELL"
        if type_token == "limit":
            order = module.LimitOrder(action, qty, px)
        else:
            order = module.MarketOrder(action, qty)
        order.tif = tif
        if env_account():
            order.account = env_account()
        trade = ib.placeOrder(contract, order)
        ib.sleep(1.5)
        status = obj_get(obj_get(trade, "orderStatus"), "status", "")
        order_id = obj_get(obj_get(trade, "order"), "orderId")
        if str(status).strip().lower() in ("rejected", "inactive", "apicancelled", "cancelled"):
            return {"status": "error", "error": f"IBKR rejected order: {status}", "order_id": order_id}
        return {"status": "ok", "broker": "ibkr", "order_id": order_id, "symbol": symbol, "side": side_token,
                "profile": args.profile, "order_type": type_token, "quantity": qty, "limit_price": px,
                "tif": tif, "order_status": str(status)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    finally:
        disconnect(ib)


def cmd_cancel(args) -> dict[str, Any]:
    oid_raw = str(args.order_id or "").strip()
    if not oid_raw:
        return {"status": "error", "error": "order_id is required"}
    try:
        oid = int(oid_raw)
    except ValueError:
        return {"status": "error", "error": "IBKR order_id must be numeric"}
    ib = connect(args.profile, readonly=False)
    try:
        accounts = managed_accounts(ib)
        assert_profile(args.profile, accounts)
        target = None
        for t in (ib.openTrades() or []):
            if obj_get(obj_get(t, "order"), "orderId") == oid:
                target = t
                break
        if target is None:
            return {"status": "error", "error": f"open order {oid} not found"}
        ib.cancelOrder(obj_get(target, "order"))
        ib.sleep(1.0)
        res = {"status": "ok", "broker": "ibkr", "order_id": oid, "profile": args.profile}
        if args.symbol:
            res["symbol"] = args.symbol.strip().upper()
        return res
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    finally:
        disconnect(ib)


def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Interactive Brokers CLI (local TWS / IB Gateway)")
    p.add_argument("--profile", default="paper", choices=["paper", "live"])
    p.add_argument("--confirm-live", action="store_true", help="required to place/cancel on a LIVE account")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status"); sub.add_parser("account"); sub.add_parser("positions")
    po = sub.add_parser("orders"); po.add_argument("--executions", action="store_true")
    for name in ("quote", "history", "place"):
        sp = sub.add_parser(name)
        sp.add_argument("--symbol", required=True)
        sp.add_argument("--exchange", default="SMART")
        sp.add_argument("--currency", default="USD")
        sp.add_argument("--sec-type", default="STK", dest="sec_type")
        if name == "history":
            sp.add_argument("--duration", default="30 D")
            sp.add_argument("--bar-size", default="1 day", dest="bar_size")
        if name == "place":
            sp.add_argument("--side", required=True)
            sp.add_argument("--qty", type=float)
            sp.add_argument("--notional", type=float)
            sp.add_argument("--type", default="market")
            sp.add_argument("--limit-price", type=float)
            sp.add_argument("--tif", default="day")
    pc = sub.add_parser("cancel"); pc.add_argument("--order-id", required=True); pc.add_argument("--symbol")
    args = p.parse_args()

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
            out(cmd_quote(args.profile, args.symbol, args.exchange, args.currency, args.sec_type))
        elif args.cmd == "history":
            out(cmd_history(args.profile, args.symbol, args.exchange, args.currency, args.sec_type, args.duration, args.bar_size))
        elif args.cmd == "place":
            out(cmd_place(args))
        elif args.cmd == "cancel":
            out(cmd_cancel(args))
    except ModuleNotFoundError as exc:
        err(f"ib_async not installed; run `pip install ib_async` ({exc})")
    except Exception as exc:  # noqa: BLE001
        err(str(exc))


if __name__ == "__main__":
    main()
