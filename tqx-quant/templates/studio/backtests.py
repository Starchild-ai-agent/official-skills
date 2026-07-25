# -*- coding: utf-8 -*-
"""Backtest history persistence for TQX Studio.

Index (light): data/backtests/index.json  — one summary record per run
Full result (raw API JSON): data/backtests/<run_id>.json — for later analysis/compare
"""
import json
import os
import time
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(BASE, 'data', 'backtests')
os.makedirs(DIR, exist_ok=True)
INDEX = os.path.join(DIR, 'index.json')
_lock = threading.Lock()


def _load():
    if not os.path.exists(INDEX):
        return []
    try:
        with open(INDEX, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save(items):
    tmp = INDEX + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, INDEX)


def record_run(run_id, params, source='ui', btype='factor'):
    """Register a run right after submission. params: market/formula/name/dates/group_number."""
    if not run_id:
        return
    with _lock:
        items = _load()
        if any(it.get('run_id') == run_id for it in items):
            return
        items.insert(0, {
            'run_id': run_id,
            'ts': time.strftime('%Y-%m-%d %H:%M'),
            'source': source,             # ui | agent
            'btype': btype,               # factor | strategy
            'status': 'running',
            'params': {k: params.get(k) for k in
                       ('market', 'formula', 'name', 'code', 'start_date', 'end_date', 'group_number',
                        'adjustment_cycle', 'factor_direction', 'start_capital',
                        'commission_rate', 'slippage', 'frequency')},
            'metrics': {},
        })
        _save(items[:500])


def record_result(run_id, result):
    """Attach a finished result: save raw JSON + extract summary metrics into index."""
    if not run_id or not isinstance(result, dict):
        return
    status = str(result.get('status', '')).upper()
    has_data = bool((result.get('results') or {}).get('nodes'))
    if not (result.get('success') and (has_data or status in ('SUCCESS', 'FINISHED', 'COMPLETED', 'DONE'))):
        return
    with _lock:
        items = _load()
        rec = next((it for it in items if it.get('run_id') == run_id), None)
        if rec is None:
            rec = {'run_id': run_id, 'ts': time.strftime('%Y-%m-%d %H:%M'),
                   'source': 'unknown', 'params': {}, 'metrics': {}}
            items.insert(0, rec)
        if rec.get('status') == 'done':
            return  # already recorded
        # extract summary
        try:
            import agent as _agent
            if rec.get('btype') == 'strategy':
                metrics, group_returns = _agent._parse_strategy_metrics(result), []
            else:
                metrics, group_returns = _agent._parse_factor_metrics(result)
        except Exception:
            metrics, group_returns = {}, []
        rec['status'] = 'done'
        rec['metrics'] = metrics
        rec['group_returns'] = group_returns
        _save(items[:500])
        # full raw payload
        try:
            with open(os.path.join(DIR, f'{run_id}.json'), 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False)
        except Exception:
            pass


def list_all(limit=100):
    with _lock:
        return _load()[:limit]


def get(run_id):
    p = os.path.join(DIR, f'{run_id}.json')
    if not os.path.exists(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# ---------------- equity curve (daily NAV) ----------------
def curve_path(run_id):
    return os.path.join(DIR, '%s.curve.json' % run_id)


def load_curve(run_id):
    p = curve_path(run_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_curve(run_id, points):
    tmp = curve_path(run_id) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'run_id': run_id, 'points': points}, f, ensure_ascii=False)
    os.replace(tmp, curve_path(run_id))


def build_curve(profit_items):
    """TQX profit rows -> ascending [{d, s, b}] (date, strategy cum return, benchmark cum return)."""
    pts = []
    for it in profit_items or []:
        if not isinstance(it, dict):
            continue
        d = str(it.get('gmt_create') or '')
        if len(d) != 8:
            continue
        pts.append({'d': '%s-%s-%s' % (d[:4], d[4:6], d[6:]),
                    's': it.get('strategy_profit'),
                    'b': it.get('csi_stock')})
    pts.sort(key=lambda x: x['d'])
    return pts


def raw_backtest_id(run_id):
    """Read stored raw result and return the inner TQX backtest_id (needed for profit paging)."""
    p = os.path.join(DIR, '%s.json' % run_id)
    if not os.path.exists(p):
        return None
    try:
        with open(p, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except Exception:
        return None
    res = raw.get('results') or {}
    bid = res.get('backtest_id')
    if bid:
        return bid
    bt = res.get('backtest') or {}
    return bt.get('backtest_id')
