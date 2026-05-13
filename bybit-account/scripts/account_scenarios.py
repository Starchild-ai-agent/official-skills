#!/usr/bin/env python3
"""
Common Bybit account analysis scenarios (read-only).
Generates structured JSON for tracking/reporting/alerts.
"""
import os, json, argparse
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv('/data/workspace/.env')

from pybit.unified_trading import HTTP

HK_PROXY = 'http://hk:x@sc-vpn.internal:8080'


def session():
    s = HTTP(testnet=False,
             api_key=os.environ.get('BYBIT_RO_API_KEY', ''),
             api_secret=os.environ.get('BYBIT_RO_SECRET', ''))
    s.client.proxies.update({"http": HK_PROXY, "https": HK_PROXY})
    return s


def print_json(d): print(json.dumps(d, ensure_ascii=False, indent=2))


def scenario_portfolio_snapshot(args):
    """Scenario 1: full portfolio snapshot (UNIFIED wallet + FUND + positions across categories)"""
    s = session()

    # UNIFIED wallet
    bal = s.get_wallet_balance(accountType='UNIFIED')
    wlist = bal['result']['list'][0] if bal['result'].get('list') else {}
    coins = [c for c in wlist.get('coin', []) if float(c.get('walletBalance', 0) or 0) > 0]

    # FUND account — get_wallet_balance only supports UNIFIED, must use get_coins_balance
    fund_rows = []
    try:
        fr = s.get_coins_balance(accountType='FUND')
        fund_rows = [c for c in fr.get('result', {}).get('balance', []) if float(c.get('walletBalance', 0) or 0) > 0]
        fund_rows = sorted(fund_rows, key=lambda x: -float(x.get('walletBalance', 0) or 0))
    except Exception:
        pass

    # Positions across linear (USDT/USDC) + inverse (BTC)
    open_pos = []
    for cat, sc in [('linear', 'USDT'), ('linear', 'USDC'), ('inverse', 'BTC')]:
        try:
            r = s.get_positions(category=cat, settleCoin=sc)
            for p in r.get('result', {}).get('list', []):
                if float(p.get('size', 0) or 0) != 0:
                    p['_category'] = cat
                    open_pos.append(p)
        except Exception:
            pass

    out = {
        'scenario': 'portfolio_snapshot',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'unified_wallet': {
            'totalEquity':           wlist.get('totalEquity'),
            'totalWalletBalance':    wlist.get('totalWalletBalance'),
            'totalAvailableBalance': wlist.get('totalAvailableBalance'),
            'accountIMRate':         wlist.get('accountIMRate'),
            'accountMMRate':         wlist.get('accountMMRate'),
            'coins_nonzero_count':   len(coins),
            'coins_nonzero':         sorted(coins, key=lambda x: -float(x.get('usdValue', 0) or 0)),
        },
        'funding_account': {
            'nonzero_count': len(fund_rows),
            'balances':      fund_rows,
        },
        'open_positions_count': len(open_pos),
        'open_positions': open_pos,
    }

    print_json(out)


def scenario_perp_risk(args):
    """Scenario 2: perpetual risk monitoring"""
    s = session()
    bal = s.get_wallet_balance(accountType='UNIFIED')
    wlist = bal['result']['list'][0] if bal['result'].get('list') else {}

    im = float(wlist.get('accountIMRate', 0) or 0)
    mm = float(wlist.get('accountMMRate', 0) or 0)

    open_pos = []
    upl = 0.0
    for cat, sc in [('linear', 'USDT'), ('linear', 'USDC'), ('inverse', 'BTC')]:
        try:
            r = s.get_positions(category=cat, settleCoin=sc)
            for p in r.get('result', {}).get('list', []):
                if float(p.get('size', 0) or 0) != 0:
                    p['_category'] = cat
                    open_pos.append(p)
                    upl += float(p.get('unrealisedPnl', 0) or 0)
        except Exception:
            pass

    out = {
        'scenario': 'perp_risk',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'account_im_rate': im,
        'account_mm_rate': mm,
        'total_unrealized_pnl': upl,
        'risk_alert': {
            'mm_rate_above_0_6':            mm > 0.6,
            'im_rate_above_0_8':            im > 0.8,
            'unrealized_loss_gt_threshold': upl < -abs(float(args.loss_threshold)),
        },
        'positions': open_pos,
    }
    print_json(out)


def scenario_cashflow(args):
    """Scenario 3: deposits/withdrawals/transfers + transaction log"""
    s = session()

    def safe(fn, **kw):
        try:
            return fn(**kw), None
        except Exception as e:
            return None, str(e)[:120]

    dep, dep_err = safe(s.get_deposit_records)
    wd, wd_err   = safe(s.get_withdrawal_records)
    it, it_err   = safe(s.get_internal_transfer_records)
    ut, ut_err   = safe(s.get_universal_transfer_records)
    tx, tx_err   = safe(s.get_transaction_log)

    def rows(r): return r.get('result', {}).get('list', []) if r else []

    by_type = defaultdict(lambda: {'count': 0, 'sum': 0.0})
    for t in rows(tx):
        typ = t.get('type', 'UNKNOWN')
        by_type[typ]['count'] += 1
        try:
            by_type[typ]['sum'] += float(t.get('change', 0) or 0)
        except (TypeError, ValueError):
            pass

    out = {
        'scenario': 'cashflow',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'deposit_count':  len(rows(dep)),
        'withdraw_count': len(rows(wd)),
        'internal_transfer_count':  len(rows(it)),
        'universal_transfer_count': len(rows(ut)),
        'tx_log_count':   len(rows(tx)),
        'tx_log_by_type': dict(by_type),
        'deposits':  rows(dep)[:args.limit],
        'withdraws': rows(wd)[:args.limit],
        'errors': {
            'deposit': dep_err, 'withdraw': wd_err,
            'internal_transfer': it_err, 'universal_transfer': ut_err, 'tx_log': tx_err,
        }
    }
    print_json(out)


def scenario_trading_activity(args):
    """Scenario 4: recent executions (fills) by category"""
    s = session()
    cats = [c.strip() for c in (args.categories or 'spot,linear').split(',') if c.strip()]
    out_rows = []
    for cat in cats:
        try:
            r = s.get_executions(category=cat, limit=args.limit or 100)
            fills = r.get('result', {}).get('list', [])
        except Exception as e:
            out_rows.append({'category': cat, 'error': str(e)[:120]})
            continue

        by_sym = defaultdict(lambda: {'count': 0, 'buy_qty': 0.0, 'sell_qty': 0.0, 'buy_quote': 0.0, 'sell_quote': 0.0})
        for f in fills:
            sym = f.get('symbol')
            qty = float(f.get('execQty', 0) or 0)
            quote = float(f.get('execValue', 0) or 0)
            by_sym[sym]['count'] += 1
            if (f.get('side') or '').lower() == 'buy':
                by_sym[sym]['buy_qty'] += qty
                by_sym[sym]['buy_quote'] += quote
            else:
                by_sym[sym]['sell_qty'] += qty
                by_sym[sym]['sell_quote'] += quote
        out_rows.append({'category': cat, 'fills_total': len(fills), 'symbols': dict(by_sym)})

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
    p = argparse.ArgumentParser(description='Bybit account analysis scenarios (read-only)')
    p.add_argument('scenario', choices=SCENARIOS.keys())
    p.add_argument('--limit', type=int, default=100)
    p.add_argument('--loss-threshold', type=float, default=5000.0)
    p.add_argument('--categories', default='', help='comma-separated, e.g. spot,linear,inverse')
    args = p.parse_args()
    SCENARIOS[args.scenario](args)
