#!/usr/bin/env python3
"""
OKX Read-Only Account Query Tool
Uses official python-okx library with HK VPN proxy.
Supports unified account: spot/margin/swap/futures/options.
"""
import os, sys, json, argparse
from dotenv import load_dotenv
load_dotenv("/data/workspace/.env")

import okx.Account as Account
import okx.Trade as Trade
import okx.Funding as Funding
import okx.PublicData as PublicData

HK_PROXY = "http://hk:x@sc-vpn.internal:8080"


def _creds():
    return dict(
        api_key=os.environ.get("OKX_RO_API_KEY", ""),
        api_secret_key=os.environ.get("OKX_RO_SECRET", ""),
        passphrase=os.environ.get("OKX_RO_PASSPHRASE", ""),
        flag="0",
        proxy=HK_PROXY,
    )

def acct(): return Account.AccountAPI(**_creds())
def trade(): return Trade.TradeAPI(**_creds())
def fund(): return Funding.FundingAPI(**_creds())
def public(): return PublicData.PublicAPI(flag="0", proxy=HK_PROXY)

def fmt(d): print(json.dumps(d, ensure_ascii=False, indent=2))


# ── Actions ────────────────────────────────────────────────────────────────────

def account_balance(args):
    """统一账户余额（含权益/可用/已用保证金，所有币种）"""
    r = acct().get_account_balance(ccy=(args.asset or '').upper())
    fmt(r)

def account_config(args):
    """账户配置（账户模式、杠杆、是否多仓位等）"""
    fmt(acct().get_account_config())

def positions(args):
    """合约/期权持仓"""
    fmt(acct().get_positions(instType=(args.inst_type or '').upper()))

def position_risk(args):
    """持仓总风险（统一账户视角的风险率）"""
    fmt(acct().get_position_risk())

def fee_rates(args):
    """当前手续费率（按 instType）"""
    fmt(acct().get_fee_rates(instType=(args.inst_type or 'SPOT').upper()))

def bills(args):
    """近 7 天账单（资金变动流水）"""
    fmt(acct().get_account_bills())

def open_orders(args):
    """当前挂单"""
    fmt(trade().get_order_list(instType=(args.inst_type or '').upper()))

def order_history(args):
    """历史订单（默认 SPOT，最近 7 天）"""
    fmt(trade().get_orders_history(instType=(args.inst_type or 'SPOT').upper()))

def fills_history(args):
    """成交明细（默认 SPOT，最近 3 个月）"""
    fmt(trade().get_fills_history(instType=(args.inst_type or 'SPOT').upper()))

def funding_balance(args):
    """资金账户余额（与统一账户分开）"""
    r = fund().get_balances(ccy=(args.asset or '').upper())
    fmt(r)

def deposits(args):
    """充值记录"""
    fmt(fund().get_deposit_history())

def withdrawals(args):
    """提币记录"""
    fmt(fund().get_withdrawal_history())

def currencies(args):
    """所有支持币种 / 链信息"""
    fmt(fund().get_currencies(ccy=(args.asset or '').upper()))

def funding_rate(args):
    """合约资金费率（默认 SWAP）"""
    inst = (args.symbol or 'BTC-USDT-SWAP').upper()
    fmt(public().get_funding_rate(instId=inst))


def summary(args):
    """一键汇总：统一账户 + 资金账户 + 当前持仓 + 当前挂单"""
    a = acct()
    f = fund()
    t = trade()

    bal = a.get_account_balance()
    fb = f.get_balances()
    pos = a.get_positions()
    orders = t.get_order_list()

    if bal.get('code') == '0':
        bdata = bal['data'][0]
        details = [d for d in bdata.get('details', []) if float(d.get('eq', 0) or 0) > 1e-9]
        bsum = {
            'totalEq': bdata.get('totalEq'),
            'isoEq':   bdata.get('isoEq'),
            'adjEq':   bdata.get('adjEq'),
            'mgnRatio': bdata.get('mgnRatio'),
            'details_nonzero': sorted(details, key=lambda x: -float(x.get('eqUsd', 0) or 0)),
        }
    else:
        bsum = bal

    if fb.get('code') == '0':
        fb_nonzero = [x for x in fb['data'] if float(x.get('bal', 0) or 0) > 1e-9]
    else:
        fb_nonzero = []

    out = {
        'unified_account': bsum,
        'funding_account_nonzero': fb_nonzero,
        'open_positions': [p for p in pos.get('data', []) if float(p.get('pos', 0) or 0) != 0],
        'open_orders':    orders.get('data', []),
    }
    fmt(out)


ACTIONS = {
    'summary':           summary,
    'account_balance':   account_balance,
    'account_config':    account_config,
    'positions':         positions,
    'position_risk':     position_risk,
    'fee_rates':         fee_rates,
    'bills':             bills,
    'open_orders':       open_orders,
    'order_history':     order_history,
    'fills_history':     fills_history,
    'funding_balance':   funding_balance,
    'deposits':          deposits,
    'withdrawals':       withdrawals,
    'currencies':        currencies,
    'funding_rate':      funding_rate,
}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description='OKX Read-Only Account Tool')
    p.add_argument('action', choices=ACTIONS.keys())
    p.add_argument('--asset',     default=None, help='Coin filter, e.g. USDT, BTC')
    p.add_argument('--inst-type', default=None, dest='inst_type', help='SPOT/MARGIN/SWAP/FUTURES/OPTION')
    p.add_argument('--symbol',    default=None, help='Instrument id, e.g. BTC-USDT-SWAP')
    args = p.parse_args()

    try:
        ACTIONS[args.action](args)
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False))
        sys.exit(1)
