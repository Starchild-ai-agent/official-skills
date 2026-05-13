#!/usr/bin/env python3
"""
Binance Read-Only Account Query Tool
Uses python-binance (official community library) with HK VPN proxy.
Supports Spot + USDM Futures.
"""
import os, sys, json, argparse
from dotenv import load_dotenv
load_dotenv("/data/workspace/.env")

from binance.client import Client

HK_PROXY = "http://hk:x@sc-vpn.internal:8080"

def get_client():
    key    = os.environ.get("BINANCE_RO_API_KEY", "")
    secret = os.environ.get("BINANCE_RO_SECRET", "")
    c = Client(api_key=key, api_secret=secret,
               requests_params={"proxies": {"https": HK_PROXY, "http": HK_PROXY}})
    return c

def fmt(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))

# ── Actions ────────────────────────────────────────────────────────────────────

def spot_balance(args):
    """现货账户余额（过滤零余额）"""
    c = get_client()
    info = c.get_account()
    balances = [
        b for b in info["balances"]
        if float(b["free"]) + float(b["locked"]) > 0.000001
    ]
    fmt({
        "canTrade":       info["canTrade"],
        "canWithdraw":    info["canWithdraw"],
        "makerCommission": info["makerCommission"],
        "takerCommission": info["takerCommission"],
        "balances": sorted(balances, key=lambda x: -float(x["free"]))
    })

def futures_balance(args):
    """U本位合约账户余额"""
    c = get_client()
    data = c.futures_account_balance()
    data = [b for b in data if float(b.get("balance", 0)) != 0]
    fmt(data)

def futures_account(args):
    """U本位合约完整账户（保证金、盈亏、持仓）"""
    c = get_client()
    info = c.futures_account()
    positions = [p for p in info.get("positions", []) if float(p["positionAmt"]) != 0]
    fmt({
        "totalWalletBalance":         info.get("totalWalletBalance"),
        "totalUnrealizedProfit":      info.get("totalUnrealizedProfit"),
        "totalMarginBalance":         info.get("totalMarginBalance"),
        "availableBalance":           info.get("availableBalance"),
        "totalPositionInitialMargin": info.get("totalPositionInitialMargin"),
        "canTrade":                   info.get("canTrade"),
        "positions":                  positions,
    })

def futures_positions(args):
    """当前合约持仓（仅持有中）"""
    c = get_client()
    data = c.futures_position_information()
    open_pos = [p for p in data if float(p["positionAmt"]) != 0]
    fmt(open_pos)

def spot_orders(args):
    """现货当前挂单"""
    c = get_client()
    sym = args.symbol.upper() if args.symbol else None
    orders = c.get_open_orders(symbol=sym) if sym else c.get_open_orders()
    fmt(orders)

def spot_order_history(args):
    """现货历史订单"""
    c = get_client()
    sym = (args.symbol or "BTCUSDT").upper()
    kwargs = {"symbol": sym, "limit": args.limit or 50}
    fmt(c.get_all_orders(**kwargs))

def futures_orders(args):
    """合约当前挂单"""
    c = get_client()
    sym = args.symbol.upper() if args.symbol else None
    orders = c.futures_get_open_orders(symbol=sym) if sym else c.futures_get_open_orders()
    fmt(orders)

def trade_history(args):
    """现货成交记录"""
    c = get_client()
    sym = (args.symbol or "BTCUSDT").upper()
    fmt(c.get_my_trades(symbol=sym, limit=args.limit or 50))

def futures_trade_history(args):
    """合约成交记录"""
    c = get_client()
    sym = (args.symbol or "BTCUSDT").upper()
    fmt(c.futures_account_trades(symbol=sym, limit=args.limit or 50))

def deposit_history(args):
    """充值记录"""
    c = get_client()
    kwargs = {}
    if args.asset:
        kwargs["coin"] = args.asset.upper()
    fmt(c.get_deposit_history(**kwargs))

def withdraw_history(args):
    """提币记录"""
    c = get_client()
    kwargs = {}
    if args.asset:
        kwargs["coin"] = args.asset.upper()
    fmt(c.get_withdraw_history(**kwargs))

def income_history(args):
    """合约收入流水（资金费、手续费返还等）"""
    c = get_client()
    kwargs = {"limit": args.limit or 100}
    if args.symbol:
        kwargs["symbol"] = args.symbol.upper()
    if args.income_type:
        kwargs["incomeType"] = args.income_type
    fmt(c.futures_income_history(**kwargs))

def asset_snapshot(args):
    """账户快照（SPOT / MARGIN / FUTURES）"""
    c = get_client()
    account_type = (args.type or "SPOT").upper()
    fmt(c.get_account_snapshot(type=account_type, limit=7))

def funding_rate(args):
    """当前资金费率"""
    c = get_client()
    kwargs = {}
    if args.symbol:
        kwargs["symbol"] = args.symbol.upper()
    fmt(c.futures_mark_price(**kwargs))

def summary(args):
    """一键汇总：现货余额 + 合约账户概览 + 持仓"""
    c = get_client()

    # Spot
    info = c.get_account()
    spot_balances = [
        b for b in info["balances"]
        if float(b["free"]) + float(b["locked"]) > 0.000001
    ]

    # Futures
    fa = c.futures_account()
    positions = [p for p in fa.get("positions", []) if float(p["positionAmt"]) != 0]

    fmt({
        "spot": {
            "balances": sorted(spot_balances, key=lambda x: -float(x["free"])),
        },
        "futures": {
            "totalWalletBalance":    fa.get("totalWalletBalance"),
            "totalUnrealizedProfit": fa.get("totalUnrealizedProfit"),
            "availableBalance":      fa.get("availableBalance"),
            "openPositions":         positions,
        },
    })

# ── CLI ────────────────────────────────────────────────────────────────────────
ACTIONS = {
    "spot_balance":          spot_balance,
    "futures_balance":       futures_balance,
    "futures_account":       futures_account,
    "futures_positions":     futures_positions,
    "spot_orders":           spot_orders,
    "spot_order_history":    spot_order_history,
    "futures_orders":        futures_orders,
    "trade_history":         trade_history,
    "futures_trade_history": futures_trade_history,
    "deposit_history":       deposit_history,
    "withdraw_history":      withdraw_history,
    "income_history":        income_history,
    "asset_snapshot":        asset_snapshot,
    "funding_rate":          funding_rate,
    "summary":               summary,
}

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Binance Read-Only Account Tool")
    p.add_argument("action", choices=ACTIONS.keys())
    p.add_argument("--symbol",      default=None)
    p.add_argument("--asset",       default=None)
    p.add_argument("--limit",       type=int, default=None)
    p.add_argument("--type",        default=None, help="SPOT/MARGIN/FUTURES for snapshot")
    p.add_argument("--income_type", default=None, help="e.g. FUNDING_FEE")
    args = p.parse_args()

    try:
        ACTIONS[args.action](args)
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)
