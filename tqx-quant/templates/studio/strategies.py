# -*- coding: utf-8 -*-
"""Strategy registry for TQX Studio — backtest results applied to auto-trading."""
import json
import os
import time
import threading
import uuid

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
os.makedirs(DATA, exist_ok=True)
FILE = os.path.join(DATA, 'strategies.json')
_lock = threading.Lock()


def _load():
    if not os.path.exists(FILE):
        return []
    try:
        with open(FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save(items):
    tmp = FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FILE)


def list_all():
    with _lock:
        return _load()


def create(payload):
    """payload: name, market, formula, start_date, end_date, group_number,
    metrics{ic,ir,t,annualized,sharpe,max_drawdown}, top_picks[]"""
    with _lock:
        items = _load()
        sid = uuid.uuid4().hex[:8]
        rec = {
            'id': sid,
            'name': (payload.get('name') or '未命名策略')[:60],
            'market': payload.get('market', 'us'),
            'formula': (payload.get('formula') or '')[:300],
            'start_date': payload.get('start_date'),
            'end_date': payload.get('end_date'),
            'group_number': payload.get('group_number'),
            'metrics': payload.get('metrics') or {},
            'top_picks': (payload.get('top_picks') or [])[:10],
            'status': 'paused',           # paused | active
            'account': 'paper',           # 目前仅仿真盘
            'created': time.strftime('%Y-%m-%d %H:%M'),
            'last_run': None,
            'run_count': 0,
        }
        items.append(rec)
        _save(items)
        return rec


def update(sid, fields):
    with _lock:
        items = _load()
        for it in items:
            if it['id'] == sid:
                for k in ('status', 'name', 'last_run', 'top_picks'):
                    if k in fields:
                        it[k] = fields[k]
                if fields.get('_inc_run'):
                    it['run_count'] = it.get('run_count', 0) + 1
                _save(items)
                return it
        return None


def delete(sid):
    with _lock:
        items = _load()
        n = len(items)
        items = [it for it in items if it['id'] != sid]
        _save(items)
        return len(items) < n
