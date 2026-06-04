#!/usr/bin/env python3
"""Futu / moomoo CLI — self-contained, connects to a LOCAL OpenD gateway.

Futu does NOT expose a public cloud API. You must run the OpenD gateway program
on a machine yourself (default 127.0.0.1:11111), log into it, and this CLI talks
to it over a local socket. Credentials live in OpenD, never here. See SKILL.md
for how to install + run OpenD.

Paper/live guard: every account row carries `trd_env` (SIMULATE=paper, REAL=live).
The CLI resolves the account whose trd_env matches --profile. Live placement
unlocks the trade context with FUTU_TRADE_PWD_MD5 and additionally requires
--confirm-live.

Symbols use the Futu format: `HK.00700`, `US.AAPL`, `SH.600519`.

Subcommands: status | account | positions | orders | quote | history | place | cancel
Output: JSON on stdout. Requires `pip install futu-api` AND a running OpenD.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Mapping

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11111
LIVE_TRADE_PWD_ENV = "FUTU_TRADE_PWD_MD5"
_ENV_TO_TRD = {"paper": "SIMULATE", "live": "REAL"}
_SIDE = {"buy": "BUY", "sell": "SELL"}


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


def env_host() -> str:
    return os.environ.get("FUTU_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST


def env_port() -> int:
    try:
        return int(os.environ.get("FUTU_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def trd_market() -> str:
    return os.environ.get("FUTU_TRD_MARKET", "HK").strip().upper() or "HK"


def security_firm() -> str:
    return os.environ.get("FUTU_SECURITY_FIRM", "FUTUSECURITIES").strip().upper() or "FUTUSECURITIES"


def env_acc_id() -> int:
    try:
        return int(os.environ.get("FUTU_ACC_ID", "0") or 0)
    except ValueError:
        return 0


def tcp_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def require_futu():
    import futu  # type: ignore
    return futu


def first(row: Mapping[str, Any], names: tuple[str, ...], default: Any = None) -> Any:
    if not isinstance(row, Mapping):
        return default
    for n in names:
        v = row.get(n, None)
        if v is not None:
            return v
    return default


def unwrap(result: Any):
    if not isinstance(result, (list, tuple)) or len(result) < 2:
        return result
    futu = require_futu()
    ret_code, data = result[0], result[1]
    if ret_code != getattr(futu, "RET_OK", 0):
        return None
    return data


def records(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    to_dict = getattr(data, "to_dict", None)
    if callable(to_dict) and hasattr(data, "columns"):
        try:
            return list(to_dict("records"))
        except Exception:  # noqa: BLE001
            pass
    if isinstance(data, Mapping):
        return [dict(data)]
    if isinstance(data, (list, tuple)):
        return [dict(i) if isinstance(i, Mapping) else {"value": i} for i in data]
    return []


def assert_gateway() -> None:
    if not tcp_port_open(env_host(), env_port()):
        raise RuntimeError(
            f"No Futu OpenD gateway listening at {env_host()}:{env_port()}. "
            "Start OpenD, log in, and confirm the API port (see SKILL.md)."
        )


def trade_ctx():
    assert_gateway()
    futu = require_futu()
    market = getattr(futu.TrdMarket, trd_market(), getattr(futu.TrdMarket, "HK"))
    firm = getattr(futu.SecurityFirm, security_firm(), getattr(futu.SecurityFirm, "FUTUSECURITIES"))
    try:
        return futu.OpenSecTradeContext(filter_trdmarket=market, host=env_host(), port=env_port(), security_firm=firm)
    except TypeError:
        return futu.OpenSecTradeContext(host=env_host(), port=env_port())


def quote_ctx():
    assert_gateway()
    futu = require_futu()
    return futu.OpenQuoteContext(host=env_host(), port=env_port())


def trd_env_enum(profile: str):
    futu = require_futu()
    name = _ENV_TO_TRD.get(profile, "SIMULATE")
    return getattr(futu.TrdEnv, name, futu.TrdEnv.SIMULATE)


def trd_env_of(row: Mapping[str, Any]) -> str:
    return str(first(row, ("trd_env", "trdEnv"), "")).upper()


def acc_id_of(row: Mapping[str, Any]) -> int:
    try:
        return int(first(row, ("acc_id", "accId"), 0) or 0)
    except (TypeError, ValueError):
        return 0


def resolve_acc_id(profile: str, ctx: Any) -> int:
    rows = records(unwrap(ctx.get_acc_list()))
    want = _ENV_TO_TRD.get(profile, "SIMULATE")
    cfg_acc = env_acc_id()
    if cfg_acc:
        target = next((r for r in rows if acc_id_of(r) == cfg_acc), None)
        if target is None:
            raise RuntimeError(f"Configured FUTU_ACC_ID {cfg_acc} not found in OpenD account list")
        if trd_env_of(target) != want:
            raise RuntimeError(f"FUTU_ACC_ID {cfg_acc} trd_env {trd_env_of(target)!r} != profile {want!r}")
        return cfg_acc
    matching = [r for r in rows if trd_env_of(r) == want]
    if not matching:
        raise RuntimeError(f"No Futu account with trd_env {want!r} for profile {profile!r}; check OpenD login")
    return acc_id_of(matching[0])


def close(ctx: Any) -> None:
    try:
        ctx.close()
    except Exception:  # noqa: BLE001
        pass


def unlock_if_live(profile: str, ctx: Any, futu) -> str | None:
    if profile != "live":
        return None
    pwd = os.environ.get(LIVE_TRADE_PWD_ENV, "").strip()
    if not pwd:
        return f"live order requires {LIVE_TRADE_PWD_ENV} (MD5 of Futu trade password) in .env"
    ret, data = ctx.unlock_trade(password_md5=pwd, is_unlock=True)
    if ret != getattr(futu, "RET_OK", 0):
        return f"Futu unlock_trade failed: {data}"
    return None


# --------------------------------------------------------------------------- #
# converters
# --------------------------------------------------------------------------- #
def account_to_dict(r):
    return {"power": first(r, ("power",)), "total_assets": first(r, ("total_assets",)),
            "cash": first(r, ("cash",)), "market_val": first(r, ("market_val",)),
            "available_funds": first(r, ("available_funds",)), "securities_assets": first(r, ("securities_assets",))}


def position_to_dict(r):
    return {"code": first(r, ("code",)), "qty": first(r, ("qty",)), "can_sell_qty": first(r, ("can_sell_qty",)),
            "cost_price": first(r, ("cost_price",)), "market_val": first(r, ("market_val",)),
            "pl_ratio": first(r, ("pl_ratio",)), "pl_val": first(r, ("pl_val",)),
            "position_side": str(first(r, ("position_side",), ""))}


def order_to_dict(r):
    return {"order_id": first(r, ("order_id",)), "code": first(r, ("code",)), "stock_name": first(r, ("stock_name",)),
            "trd_side": str(first(r, ("trd_side",), "")), "order_type": str(first(r, ("order_type",), "")),
            "order_status": str(first(r, ("order_status",), "")), "qty": first(r, ("qty",)), "price": first(r, ("price",)),
            "dealt_qty": first(r, ("dealt_qty",)), "dealt_avg_price": first(r, ("dealt_avg_price",)),
            "create_time": str(first(r, ("create_time",), ""))}


def deal_to_dict(r):
    return {"deal_id": first(r, ("deal_id",)), "order_id": first(r, ("order_id",)), "code": first(r, ("code",)),
            "qty": first(r, ("qty",)), "price": first(r, ("price",)), "trd_side": str(first(r, ("trd_side",), "")),
            "create_time": str(first(r, ("create_time",), ""))}


def quote_to_dict(r):
    return {"code": first(r, ("code",)), "last": first(r, ("last_price",)), "open": first(r, ("open_price",)),
            "high": first(r, ("high_price",)), "low": first(r, ("low_price",)), "prev_close": first(r, ("prev_close_price",)),
            "volume": first(r, ("volume",)), "ask": first(r, ("ask_price",)), "bid": first(r, ("bid_price",)),
            "time": str(first(r, ("update_time",), ""))}


def bar_to_dict(r):
    return {"code": first(r, ("code",)), "time": str(first(r, ("time_key",), "")), "open": first(r, ("open",)),
            "close": first(r, ("close",)), "high": first(r, ("high",)), "low": first(r, ("low",)),
            "volume": first(r, ("volume",)), "turnover": first(r, ("turnover",))}


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_status(profile: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "ok", "broker": "futu", "profile": profile,
        "gateway": {"host": env_host(), "port": env_port(), "open": tcp_port_open(env_host(), env_port())},
        "trd_env": _ENV_TO_TRD.get(profile, "SIMULATE"),
    }
    try:
        require_futu()
        report["sdk_installed"] = True
    except ModuleNotFoundError:
        report.update(status="error", sdk_installed=False, error="futu-api not installed; run `pip install futu-api`")
        return report
    if not report["gateway"]["open"]:
        report.update(status="error", error=f"OpenD gateway not reachable at {env_host()}:{env_port()}")
        return report
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(profile, ctx)
        report["acc_id"] = acc_id
    except Exception as exc:  # noqa: BLE001
        report.update(status="error", error=str(exc))
    finally:
        close(ctx)
    return report


def cmd_account(profile: str) -> dict[str, Any]:
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(profile, ctx)
        rows = records(unwrap(ctx.accinfo_query(trd_env=trd_env_enum(profile), acc_id=acc_id)))
        return {"status": "ok", "broker": "futu", "profile": profile, "acc_id": acc_id,
                "assets": [account_to_dict(r) for r in rows]}
    finally:
        close(ctx)


def cmd_positions(profile: str) -> dict[str, Any]:
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(profile, ctx)
        rows = records(unwrap(ctx.position_list_query(trd_env=trd_env_enum(profile), acc_id=acc_id)))
        return {"status": "ok", "broker": "futu", "profile": profile, "acc_id": acc_id,
                "positions": [position_to_dict(r) for r in rows]}
    finally:
        close(ctx)


def cmd_orders(profile: str, executions: bool) -> dict[str, Any]:
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(profile, ctx)
        env = trd_env_enum(profile)
        orders = records(unwrap(ctx.order_list_query(trd_env=env, acc_id=acc_id)))
        res = {"status": "ok", "broker": "futu", "profile": profile, "acc_id": acc_id,
               "open_orders": [order_to_dict(r) for r in orders]}
        if executions:
            deals = records(unwrap(ctx.deal_list_query(trd_env=env, acc_id=acc_id)))
            res["executions"] = [deal_to_dict(r) for r in deals]
        return res
    finally:
        close(ctx)


def cmd_quote(symbol: str) -> dict[str, Any]:
    ctx = quote_ctx()
    try:
        code = symbol.strip().upper()
        rows = records(unwrap(ctx.get_market_snapshot([code])))
        return {"status": "ok", "broker": "futu", "symbol": code, "quote": quote_to_dict(rows[0]) if rows else {}}
    finally:
        close(ctx)


_KLTYPE = {"1m": "K_1M", "5m": "K_5M", "15m": "K_15M", "30m": "K_30M",
           "1h": "K_60M", "4h": "K_60M", "1d": "K_DAY", "1w": "K_WEEK", "1M": "K_MON"}


def cmd_history(symbol: str, period: str, limit: int) -> dict[str, Any]:
    futu = require_futu()
    ktype = getattr(futu.KLType, _KLTYPE.get(period, "K_DAY"), getattr(futu.KLType, "K_DAY"))
    ctx = quote_ctx()
    try:
        code = symbol.strip().upper()
        rows = records(unwrap(ctx.request_history_kline(code, ktype=ktype, max_count=int(limit))))
        return {"status": "ok", "broker": "futu", "symbol": code, "period": period,
                "bars": [bar_to_dict(r) for r in rows]}
    finally:
        close(ctx)


def cmd_place(args) -> dict[str, Any]:
    side_key = (args.side or "").strip().lower()
    if side_key not in _SIDE:
        return {"status": "error", "error": "side must be 'buy' or 'sell'"}
    order_kind = (args.type or "market").strip().lower()
    if order_kind not in ("market", "limit"):
        return {"status": "error", "error": "type must be 'market' or 'limit'"}
    if args.notional is not None:
        return {"status": "error", "error": "Futu requires --qty (whole shares), not --notional"}
    if args.qty is None:
        return {"status": "error", "error": "--qty is required"}
    try:
        qty_int = int(args.qty)
    except (TypeError, ValueError):
        return {"status": "error", "error": "quantity must be a whole number of shares"}
    if qty_int <= 0:
        return {"status": "error", "error": "quantity must be positive"}
    price = 0.0
    if order_kind == "limit":
        if args.limit_price is None:
            return {"status": "error", "error": "limit order requires --limit-price"}
        price = float(args.limit_price)
    code = (args.symbol or "").strip().upper()
    if not code:
        return {"status": "error", "error": "symbol is required"}

    futu = require_futu()
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(args.profile, ctx)
        env = trd_env_enum(args.profile)
        unlock_err = unlock_if_live(args.profile, ctx, futu)
        if unlock_err:
            return {"status": "error", "error": unlock_err}
        trd_side = getattr(futu.TrdSide, _SIDE[side_key])
        otype = futu.OrderType.MARKET if order_kind == "market" else futu.OrderType.NORMAL
        ret, data = ctx.place_order(price=price, qty=qty_int, code=code, trd_side=trd_side,
                                    order_type=otype, trd_env=env, acc_id=acc_id)
        if ret != getattr(futu, "RET_OK", 0):
            return {"status": "error", "error": f"Futu place_order rejected: {data}"}
        rows = records(data)
        order_id = str(first(rows[0], ("order_id",), "")) if rows else ""
        if not order_id:
            return {"status": "error", "error": f"Futu accepted but returned no order_id: {data}"}
        return {"status": "ok", "broker": "futu", "order_id": order_id, "symbol": code, "side": side_key,
                "profile": args.profile, "trd_env": _ENV_TO_TRD.get(args.profile), "acc_id": acc_id,
                "order_type": order_kind, "quantity": qty_int, "limit_price": price if order_kind == "limit" else None}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    finally:
        close(ctx)


def cmd_cancel(args) -> dict[str, Any]:
    oid = str(args.order_id or "").strip()
    if not oid:
        return {"status": "error", "error": "order_id is required"}
    futu = require_futu()
    ctx = trade_ctx()
    try:
        acc_id = resolve_acc_id(args.profile, ctx)
        env = trd_env_enum(args.profile)
        unlock_err = unlock_if_live(args.profile, ctx, futu)
        if unlock_err:
            return {"status": "error", "error": unlock_err}
        ret, data = ctx.modify_order(futu.ModifyOrderOp.CANCEL, oid, 0, 0, trd_env=env, acc_id=acc_id)
        if ret != getattr(futu, "RET_OK", 0):
            return {"status": "error", "error": f"Futu cancel rejected: {data}"}
        res = {"status": "ok", "broker": "futu", "order_id": oid, "profile": args.profile,
               "trd_env": _ENV_TO_TRD.get(args.profile), "acc_id": acc_id}
        if args.symbol:
            res["symbol"] = args.symbol.strip().upper()
        return res
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    finally:
        close(ctx)


def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description="Futu / moomoo CLI (local OpenD gateway)")
    p.add_argument("--profile", default="paper", choices=["paper", "live"])
    p.add_argument("--confirm-live", action="store_true", help="required to place/cancel on a LIVE (REAL) account")
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
        err("LIVE order blocked: re-run with --confirm-live to trade on a live (REAL) account")

    try:
        dispatch = {
            "status": lambda: cmd_status(args.profile),
            "account": lambda: cmd_account(args.profile),
            "positions": lambda: cmd_positions(args.profile),
            "orders": lambda: cmd_orders(args.profile, args.executions),
            "quote": lambda: cmd_quote(args.symbol),
            "history": lambda: cmd_history(args.symbol, args.period, args.limit),
            "place": lambda: cmd_place(args),
            "cancel": lambda: cmd_cancel(args),
        }
        out(dispatch[args.cmd]())
    except ModuleNotFoundError as exc:
        err(f"futu-api not installed; run `pip install futu-api` ({exc})")
    except Exception as exc:  # noqa: BLE001
        err(str(exc))


if __name__ == "__main__":
    main()
