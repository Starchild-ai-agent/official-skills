# -*- coding: utf-8 -*-
"""Decision journal + NAV history for TQX Studio. Shared by server.py / agent.py."""
import json
import os
import time
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
os.makedirs(DATA, exist_ok=True)
DECISIONS_FILE = os.path.join(DATA, 'decisions.jsonl')
NAV_FILE = os.path.join(DATA, 'nav_history.jsonl')
_lock = threading.Lock()

NAV_MIN_INTERVAL = 300  # seconds between NAV snapshots


def _append(path, obj):
    with _lock:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def _read_jsonl(path, limit=200):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out[-limit:]


def _num(v):
    try:
        return float(str(v).replace(',', ''))
    except Exception:
        return None


def log_decision(source, instruction, reasoning, actions):
    """source: 'agent' | 'manual' | 'thread'. actions: list of
    {tool, args, ok, summary, order_id}."""
    rec = {
        'ts': int(time.time()),
        'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'source': source,
        'instruction': (instruction or '')[:500],
        'reasoning': (reasoning or '')[:1200],
        'actions': actions[:10],
    }
    _append(DECISIONS_FILE, rec)
    return rec


def read_decisions(limit=100):
    return list(reversed(_read_jsonl(DECISIONS_FILE, limit)))


def snapshot_nav(account):
    """Append a NAV point from a trading-account dict, throttled."""
    if not isinstance(account, dict):
        return False
    total = _num(account.get('total_assets'))
    if total is None:
        return False
    hist = _read_jsonl(NAV_FILE, 1)
    now = int(time.time())
    if hist and now - hist[-1].get('ts', 0) < NAV_MIN_INTERVAL:
        return False
    _append(NAV_FILE, {
        'ts': now,
        'time': time.strftime('%Y-%m-%d %H:%M', time.localtime()),
        'total_assets': total,
        'cash': _num(account.get('available_cash')),
        'market_value': _num(account.get('market_value')),
        'currency': account.get('currency') or 'HKD',
    })
    return True


def read_nav(limit=1000):
    return _read_jsonl(NAV_FILE, limit)


def nav_stats():
    """Cumulative return, max drawdown, latest value — computed from history."""
    pts = read_nav()
    if len(pts) < 1:
        return None
    vals = [p['total_assets'] for p in pts if p.get('total_assets')]
    if not vals:
        return None
    first, last = vals[0], vals[-1]
    peak, mdd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return {
        'start_value': first,
        'latest_value': last,
        'cum_return': (last / first - 1) if first else 0,
        'max_drawdown': mdd,
        'points': len(vals),
        'since': pts[0].get('time'),
    }
