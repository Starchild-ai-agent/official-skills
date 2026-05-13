#!/usr/bin/env python3
"""
Bybit Read-Only Account Query Tool
Uses official pybit library with HK VPN proxy.
Supports Unified Trading Account (spot/derivatives/options).
"""
import os, sys, json, argparse
from dotenv import load_dotenv
load_dotenv("/data/workspace/.env")

from pybit.unified_trading import HTTP

HK_PROXY = "http://hk:x@sc-vpn.internal:8080"


def session():
    s = HTTP(testnet=False,
             api_key=os.environ.get("BYBIT_RO_API_KEY", ""),
             api_secret=os.environ.get("BYBIT_RO_SECRET", ""))
    s.client.proxies.update({"http": HK_PROXY, "https": HK_PROXY})
    return s


def fmt(d): print(json.dumps(d, ensure_ascii=False, indent=2))


# ── Actions ────────────────────────────────────────────────────────────────────

def wallet_balance(args):
    """统一账户钱包余额（含每币种权益）"""
    kw = {'accountType': (args.account_type or 'UNIFIED').upper()}
    if args.asset: kw['coin'] = args.asset.upper()
    fmt(session().get_wallet_balance(**kw))

def coin_balance(args):
    """指定币种的精确余额"""
    fmt(session().get_coin_balance(
        accountType=(args.account_type or 'UNIFIED').upper(),
        coin=(args.asset or 'USDT').upper()))

def account_info(args):
    """账户配置（统一账户模式、保证金模式等）"""
    fmt(session().get_account_info())

def fee_rates(args):
    """手续费率（默认 linear 永续合约）"""
    kw = {'category': (args.category or 'linear')}
    if args.symbol: kw['symbol'] = args.symbol.upper()
    fmt(session().get_fee_rates(**kw))

def collateral_info(args):
    """抵押品信息（统一账户每币种抵押率）"""
    fmt(session().get_collateral_info())

def positions(args):
    """合约持仓"""
    cat = (args.category or 'linear')
    kw = {'category': cat}
    if args.symbol:
        kw['symbol'] = args.symbol.upper()
    else:
        # linear/inverse 必须传 symbol/settleCoin/baseCoin 之一
        kw['settleCoin'] = (args.settle or 'USDT').upper()
    fmt(session().get_positions(**kw))

def open_orders(args):
    """当前挂单"""
    cat = (args.category or 'linear')
    kw = {'category': cat}
    if args.symbol: kw['symbol'] = args.symbol.upper()
    elif cat in ('linear', 'inverse'):
        kw['settleCoin'] = (args.settle or 'USDT').upper()
    fmt(session().get_open_orders(**kw))

def order_history(args):
    """历史订单"""
    fmt(session().get_order_history(
        category=(args.category or 'linear'),
        symbol=(args.symbol or '').upper() or None,
        limit=args.limit or 50))

def executions(args):
    """成交明细"""
    fmt(session().get_executions(
        category=(args.category or 'linear'),
        symbol=(args.symbol or '').upper() or None,
        limit=args.limit or 50))

def deposits(args):
    """充值记录"""
    fmt(session().get_deposit_records())

def withdrawals(args):
    """提币记录"""
    fmt(session().get_withdrawal_records())

def internal_transfers(args):
    """内部转账记录（账户间）"""
    fmt(session().get_internal_transfer_records())

def universal_transfers(args):
    """子账户间转账记录"""
    fmt(session().get_universal_transfer_records())

def transaction_log(args):
    """统一账户交易流水（资金费/手续费/盈亏）"""
    fmt(session().get_transaction_log())

def borrow_history(args):
    """借币历史（统一账户保证金借币）"""
    fmt(session().get_borrow_history())

def server_time(args):
    """服务器时间（公共，用于诊断网络）"""
    fmt(session().get_server_time())


def summary(args):
    """一键汇总：钱包+持仓+挂单"""
    s = session()
    bal = s.get_wallet_balance(accountType='UNIFIED')
    pos = s.get_positions(category='linear', settleCoin='USDT')
    orders = s.get_open_orders(category='linear', settleCoin='USDT')
    spot_orders = s.get_open_orders(category='spot')

    if bal.get('retCode') == 0:
        wlist = bal['result']['list'][0] if bal['result']['list'] else {}
        coins = wlist.get('coin', [])
        nonzero = [c for c in coins if float(c.get('walletBalance', 0) or 0) > 0]
        wallet_summary = {
            'totalEquity':           wlist.get('totalEquity'),
            'totalWalletBalance':    wlist.get('totalWalletBalance'),
            'totalAvailableBalance': wlist.get('totalAvailableBalance'),
            'totalMarginBalance':    wlist.get('totalMarginBalance'),
            'accountIMRate':         wlist.get('accountIMRate'),
            'accountMMRate':         wlist.get('accountMMRate'),
            'coins_nonzero':         sorted(nonzero, key=lambda x: -float(x.get('usdValue', 0) or 0)),
        }
    else:
        wallet_summary = bal

    out = {
        'wallet': wallet_summary,
        'open_positions': [p for p in pos.get('result', {}).get('list', []) if float(p.get('size', 0) or 0) != 0],
        'open_orders_linear': orders.get('result', {}).get('list', []),
        'open_orders_spot':   spot_orders.get('result', {}).get('list', []),
    }
    fmt(out)


ACTIONS = {
    'summary':              summary,
    'wallet_balance':       wallet_balance,
    'coin_balance':         coin_balance,
    'account_info':         account_info,
    'fee_rates':            fee_rates,
    'collateral_info':      collateral_info,
    'positions':            positions,
    'open_orders':          open_orders,
    'order_history':        order_history,
    'executions':           executions,
    'deposits':             deposits,
    'withdrawals':          withdrawals,
    'internal_transfers':   internal_transfers,
    'universal_transfers':  universal_transfers,
    'transaction_log':      transaction_log,
    'borrow_history':       borrow_history,
    'server_time':          server_time,
}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description='Bybit Read-Only Account Tool')
    p.add_argument('action', choices=ACTIONS.keys())
    p.add_argument('--asset',        default=None, help='Coin, e.g. USDT, BTC')
    p.add_argument('--symbol',       default=None, help='Symbol, e.g. BTCUSDT')
    p.add_argument('--account-type', default=None, dest='account_type', help='UNIFIED/CONTRACT/SPOT/FUND/INVESTMENT/OPTION')
    p.add_argument('--category',     default=None, help='spot/linear/inverse/option')
    p.add_argument('--settle',       default=None, help='Settle coin for linear/inverse')
    p.add_argument('--limit',        type=int, default=None)
    args = p.parse_args()

    try:
        ACTIONS[args.action](args)
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)
