#!/usr/bin/env python3
"""
Common OKX account analysis scenarios (read-only).
Generates structured JSON for tracking/reporting/alerts.
"""
import os, json, argparse
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/data/workspace/.env')

import okx.Account as Account
import okx.Trade as Trade
import okx.Funding as Funding

HK_PROXY = 'http://hk:x@sc-vpn.internal:8080'


def _creds():
    return dict(
        api_key=os.environ.get('OKX_RO_API_KEY', ''),
        api_secret_key=os.environ.get('OKX_RO_SECRET', ''),
        passphrase=os.environ.get('OKX_RO_PASSPHRASE', ''),
        flag='0', proxy=HK_PROXY)

def print_json(d): print(json.dumps(d, ensure_ascii=False, indent=2))


def scenario_portfolio_snapshot(args):
    """Scenario 1: full portfolio snapshot (unified + funding + positions)"""
    a = Account.AccountAPI(**_creds())
    f = Funding.FundingAPI(**_creds())

    bal = a.get_account_balance()
    fb = f.get_balances()
    pos = a.get_positions()

    bdata = bal['data'][0] if bal.get('code') == '0' else {}
    details = [d for d in bdata.get('details', []) if float(d.get('eq', 0) or 0) > 1e-9]
    fb_rows = [x for x in fb.get('data', []) if float(x.get('bal', 0) or 0) > 1e-9]
    open_pos = [p for p in pos.get('data', []) if float(p.get('pos', 0) or 0) != 0]

    out = {
        'scenario': 'portfolio_snapshot',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'unified': {
            'totalEq': bdata.get('totalEq'),
            'adjEq':   bdata.get('adjEq'),
            'mgnRatio': bdata.get('mgnRatio'),
            'nonzero_assets': len(details),
            'details': sorted(details, key=lambda x: -float(x.get('eqUsd', 0) or 0)),
        },
        'funding': {
            'nonzero_assets': len(fb_rows),
            'balances': fb_rows,
        },
        'open_positions_count': len(open_pos),
        'open_positions': open_pos,
    }
    print_json(out)


def scenario_perp_risk(args):
    """Scenario 2: perpetual/futures risk monitoring"""
    a = Account.AccountAPI(**_creds())
    pos = a.get_positions(instType='SWAP')
    risk = a.get_position_risk()

    bal = a.get_account_balance()
    bdata = bal['data'][0] if bal.get('code') == '0' else {}
    mgn_ratio = float(bdata.get('mgnRatio', 0) or 0) if bdata.get('mgnRatio') else None
    upl = sum(float(p.get('upl', 0) or 0) for p in pos.get('data', []))

    out = {
        'scenario': 'perp_risk',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'account_mgn_ratio': mgn_ratio,
        'total_unrealized_pnl_usdt': upl,
        'risk_alert': {
            'mgn_ratio_below_3': (mgn_ratio is not None and 0 < mgn_ratio < 3),
            'unrealized_loss_gt_threshold': upl < -abs(float(args.loss_threshold)),
        },
        'positions': [p for p in pos.get('data', []) if float(p.get('pos', 0) or 0) != 0],
        'risk_detail': risk.get('data', []),
    }
    print_json(out)


def scenario_cashflow(args):
    """Scenario 3: deposits/withdrawals + recent bills (cashflow)"""
    f = Funding.FundingAPI(**_creds())
    a = Account.AccountAPI(**_creds())

    dep = f.get_deposit_history()
    wd = f.get_withdrawal_history()
    bills = a.get_account_bills()

    deps = dep.get('data', [])
    wds  = wd.get('data', [])
    bs   = bills.get('data', [])

    by_subtype = defaultdict(lambda: {'count': 0, 'sum': 0.0})
    for b in bs:
        st = b.get('subType', 'UNKNOWN')
        by_subtype[st]['count'] += 1
        try:
            by_subtype[st]['sum'] += float(b.get('balChg', 0) or 0)
        except (TypeError, ValueError):
            pass

    out = {
        'scenario': 'cashflow',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'deposit_count': len(deps),
        'withdraw_count': len(wds),
        'bills_count_7d': len(bs),
        'bills_by_subtype': dict(by_subtype),
        'deposits': deps[:args.limit],
        'withdraws': wds[:args.limit],
    }
    print_json(out)


def scenario_trading_activity(args):
    """Scenario 4: recent fills activity by instrument type"""
    t = Trade.TradeAPI(**_creds())
    out_rows = []
    for inst in [s.strip().upper() for s in (args.inst_types or 'SPOT,SWAP').split(',') if s.strip()]:
        try:
            r = t.get_fills_history(instType=inst)
            fills = r.get('data', [])
        except Exception as e:
            out_rows.append({'instType': inst, 'error': str(e)[:120]})
            continue

        by_sym = defaultdict(lambda: {'count': 0, 'buy_qty': 0.0, 'sell_qty': 0.0, 'buy_quote': 0.0, 'sell_quote': 0.0})
        for f in fills:
            sym = f.get('instId')
            qty = float(f.get('fillSz', 0) or 0)
            px  = float(f.get('fillPx', 0) or 0)
            quote = qty * px
            by_sym[sym]['count'] += 1
            if f.get('side') == 'buy':
                by_sym[sym]['buy_qty'] += qty
                by_sym[sym]['buy_quote'] += quote
            else:
                by_sym[sym]['sell_qty'] += qty
                by_sym[sym]['sell_quote'] += quote

        out_rows.append({
            'instType': inst,
            'fills_total': len(fills),
            'symbols': dict(by_sym),
        })

    out = {
        'scenario': 'trading_activity',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'rows': out_rows,
    }
    print_json(out)


SCENARIOS = {
    'portfolio_snapshot': scenario_portfolio_snapshot,
    'perp_risk':          scenario_perp_risk,
    'cashflow':           scenario_cashflow,
    'trading_activity':   scenario_trading_activity,
}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='OKX account analysis scenarios (read-only)')
    p.add_argument('scenario', choices=SCENARIOS.keys())
    p.add_argument('--limit', type=int, default=100)
    p.add_argument('--loss-threshold', type=float, default=5000.0)
    p.add_argument('--inst-types', default='', help='comma-separated, e.g. SPOT,SWAP,FUTURES')
    args = p.parse_args()
    SCENARIOS[args.scenario](args)
