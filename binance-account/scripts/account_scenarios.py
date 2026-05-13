#!/usr/bin/env python3
"""
Common Binance account analysis scenarios (read-only).
Generates structured JSON for tracking/reporting/alerts.
"""
import os, json, argparse
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
from binance.client import Client

load_dotenv('/data/workspace/.env')
HK_PROXY = 'http://hk:x@sc-vpn.internal:8080'


def get_client():
    return Client(
        api_key=os.environ.get('BINANCE_RO_API_KEY', ''),
        api_secret=os.environ.get('BINANCE_RO_SECRET', ''),
        requests_params={'proxies': {'https': HK_PROXY, 'http': HK_PROXY}}
    )


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def scenario_portfolio_snapshot(args):
    """Scenario 1: full portfolio snapshot (spot+futures)"""
    c = get_client()
    spot = c.get_account()
    futures = c.futures_account()

    balances = [b for b in spot['balances'] if float(b['free']) + float(b['locked']) > 1e-9]
    positions = [p for p in futures.get('positions', []) if float(p['positionAmt']) != 0]

    out = {
        'scenario': 'portfolio_snapshot',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'spot_nonzero_assets': len(balances),
        'spot_balances': balances,
        'futures': {
            'totalWalletBalance': futures.get('totalWalletBalance'),
            'totalUnrealizedProfit': futures.get('totalUnrealizedProfit'),
            'availableBalance': futures.get('availableBalance'),
            'positions': positions,
        }
    }
    print_json(out)


def scenario_futures_risk(args):
    """Scenario 2: futures risk monitoring"""
    c = get_client()
    f = c.futures_account()
    positions = [p for p in f.get('positions', []) if float(p['positionAmt']) != 0]

    # basic risk indicators from account-level fields
    wallet = float(f.get('totalWalletBalance', 0) or 0)
    unreal = float(f.get('totalUnrealizedProfit', 0) or 0)
    margin = float(f.get('totalMarginBalance', 0) or 0)
    maint = float(f.get('totalMaintMargin', 0) or 0)
    ratio = (maint / margin) if margin > 0 else 0

    out = {
        'scenario': 'futures_risk',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'account': {
            'totalWalletBalance': wallet,
            'totalUnrealizedProfit': unreal,
            'totalMarginBalance': margin,
            'totalMaintMargin': maint,
            'maint_margin_ratio': ratio,
        },
        'open_positions': positions,
        'alerts': {
            'maint_margin_ratio_gt_0_6': ratio > 0.6,
            'unrealized_loss_gt_threshold': unreal < -abs(float(args.loss_threshold)),
        }
    }
    print_json(out)


def scenario_cashflow(args):
    """Scenario 3: deposit/withdraw/transfer/funding cashflow"""
    c = get_client()

    def safe_call(fn, *a, **kw):
        try:
            return fn(*a, **kw), None
        except Exception as e:
            return None, str(e)

    dep, dep_err = safe_call(c.get_deposit_history, limit=args.limit)
    wd, wd_err = safe_call(c.get_withdraw_history, limit=args.limit)
    inc, inc_err = safe_call(c.futures_income_history, limit=args.limit)

    # transfer history: read-only keys often cannot call futures_account_transfer
    # fallback to new_transfer_history (works with MAIN_UMFUTURE type on this account)
    tr = []
    transfer_errors = []

    r, e = safe_call(c.futures_account_transfer, limit=args.limit)
    if e:
        transfer_errors.append({'endpoint': 'futures_account_transfer', 'error': e})
    elif r:
        tr.extend(r if isinstance(r, list) else [r])

    for t in ['MAIN_UMFUTURE', 'MAIN_MARGIN', 'UMFUTURE_MAIN']:
        r, e = safe_call(c.new_transfer_history, type=t, limit=args.limit)
        if e:
            transfer_errors.append({'endpoint': f'new_transfer_history({t})', 'error': e})
            continue
        if isinstance(r, dict) and 'rows' in r:
            tr.extend(r.get('rows', []))
        elif isinstance(r, list):
            tr.extend(r)

    # summarize income by type
    by_type = defaultdict(float)
    for x in (inc or []):
        t = x.get('incomeType', 'UNKNOWN')
        by_type[t] += float(x.get('income', 0) or 0)

    out = {
        'scenario': 'cashflow',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'deposit_count': len(dep or []),
        'withdraw_count': len(wd or []),
        'futures_transfer_count': len(tr),
        'futures_income_count': len(inc or []),
        'futures_income_by_type': dict(sorted(by_type.items(), key=lambda kv: -abs(kv[1]))),
        'deposits': dep or [],
        'withdraws': wd or [],
        'transfers': tr,
        'futures_income': inc or [],
        'errors': {
            'deposit_error': dep_err,
            'withdraw_error': wd_err,
            'income_error': inc_err,
            'transfer_errors': transfer_errors,
        }
    }
    print_json(out)


def scenario_trading_activity(args):
    """Scenario 4: spot trading activity by symbol in lookback window"""
    c = get_client()

    # user provides comma-separated symbols, default core symbols
    symbols = [s.strip().upper() for s in (args.symbols or 'BTCUSDT,ETHUSDT,PAXGUSDT,DODOUSDT').split(',') if s.strip()]
    start_ms = int((datetime.now(timezone.utc).timestamp() - args.days * 86400) * 1000)

    rows = []
    for sym in symbols:
        try:
            trades = c.get_my_trades(symbol=sym, startTime=start_ms, limit=1000)
        except Exception as e:
            rows.append({'symbol': sym, 'error': str(e)[:120]})
            continue

        buy_qty = sum(float(t['qty']) for t in trades if t['isBuyer'])
        buy_quote = sum(float(t['quoteQty']) for t in trades if t['isBuyer'])
        sell_qty = sum(float(t['qty']) for t in trades if not t['isBuyer'])
        sell_quote = sum(float(t['quoteQty']) for t in trades if not t['isBuyer'])

        rows.append({
            'symbol': sym,
            'trades': len(trades),
            'buy_qty': buy_qty,
            'buy_quote': buy_quote,
            'sell_qty': sell_qty,
            'sell_quote': sell_quote,
            'net_qty': buy_qty - sell_qty,
        })

    out = {
        'scenario': 'trading_activity',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'days': args.days,
        'rows': rows,
    }
    print_json(out)


SCENARIOS = {
    'portfolio_snapshot': scenario_portfolio_snapshot,
    'futures_risk': scenario_futures_risk,
    'cashflow': scenario_cashflow,
    'trading_activity': scenario_trading_activity,
}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Binance account analysis scenarios (read-only)')
    p.add_argument('scenario', choices=SCENARIOS.keys())
    p.add_argument('--limit', type=int, default=100, help='records per API for cashflow scenario')
    p.add_argument('--days', type=int, default=30, help='lookback days for trading_activity scenario')
    p.add_argument('--symbols', default='', help='comma-separated symbols for trading_activity')
    p.add_argument('--loss-threshold', type=float, default=5000.0, help='loss threshold for futures_risk alert')
    args = p.parse_args()

    SCENARIOS[args.scenario](args)
