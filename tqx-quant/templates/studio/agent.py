# -*- coding: utf-8 -*-
"""TQX Agent core: LLM tool-calling loop that designs factors, runs backtests,
and executes paper trades via the TQX CLI. Standalone module used by server.py."""
import os
import json
import time
import subprocess

from core.http_client import proxied_post

AGENT_MODEL = os.environ.get("TQX_AGENT_MODEL", "openai/gpt-4o-mini")
LLM_URL = "https://openrouter.ai/api/v1/chat/completions"
CALLER_ID = "preview:tqx-quant-strategy-studio"


# --------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------
def _sync_tqx_config():
    import shutil
    pd, rd = '/data/workspace/.tqx', '/root/.tqx'
    os.makedirs(pd, exist_ok=True); os.makedirs(rd, exist_ok=True)
    p, r = os.path.join(pd, 'config.yaml'), os.path.join(rd, 'config.yaml')
    if os.path.exists(p) and not os.path.exists(r):
        shutil.copy(p, r)
    elif os.path.exists(r):
        shutil.copy(r, p)


def _login(force=False):
    email = os.environ.get("TQX_EMAIL", "")
    pw = os.environ.get("TQX_PASSWORD", "")
    if not email or not pw:
        return
    if not force and os.path.exists("/root/.tqx/config.yaml"):
        return
    subprocess.run(["tqx-cli", "--json", "login", "--email", email, "--password", pw],
                   capture_output=True, env=os.environ.copy(), timeout=60)
    _sync_tqx_config()


def _run_cmd(cmd, timeout=120):
    _sync_tqx_config()
    env = os.environ.copy()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        out = p.stdout.strip()
        if not out:
            return {"error": p.stderr.strip() or "empty output", "exit_code": p.returncode}
        try:
            res = json.loads(out)
        except Exception:
            return {"raw_output": out, "exit_code": p.returncode}
        # auto re-login on token expiry
        _txt = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
        needs = ('LOGIN_REQUIRED' in _txt or '均已失效' in _txt or
                 'Please log in to continue' in _txt)
        if needs:
            _login(force=True)
            p2 = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
            if p2.stdout.strip():
                try:
                    return json.loads(p2.stdout.strip())
                except Exception:
                    return {"raw_output": p2.stdout.strip()}
        return res
    except Exception as e:
        return {"error": str(e)}


# --------------------------------------------------------------------------
# Tool implementations
# --------------------------------------------------------------------------
def t_run_factor_backtest(market="us", formula="close/ref(close,5)-1", name=None,
                          start_date="20260601", end_date="20260701", group_number=2,
                          adjustment_cycle=None, factor_direction=1, **_):
    _login()
    name = name or f"AgentFactor_{int(time.time())}"
    cmd = ["tqx-cli", "--json", "factor_create",
           "--market", market, "--formula", formula, "--name", name,
           "--start-date", str(start_date), "--end-date", str(end_date),
           "--group-number", str(group_number), "--factor-direction", str(factor_direction)]
    if adjustment_cycle:
        cmd += ["--adjustment-cycle", str(adjustment_cycle)]
    create = _run_cmd(cmd)
    if not create.get("success"):
        return {"ok": False, "stage": "create", "error": create.get("error") or create}
    fid = create.get("factor_id")
    run = _run_cmd(["tqx-cli", "--json", "factor_run", fid, "--no-wait"])
    if not run.get("success"):
        return {"ok": False, "stage": "run", "factor_id": fid, "error": run.get("error") or run}
    rid = run.get("run_id")
    try:
        import backtests
        backtests.record_run(rid, {"market": market, "formula": formula, "name": name,
                                   "start_date": start_date, "end_date": end_date,
                                   "group_number": group_number,
                                   "adjustment_cycle": adjustment_cycle,
                                   "factor_direction": factor_direction}, source='agent')
    except Exception:
        pass
    # poll result
    result = None
    for _i in range(30):
        res = _run_cmd(["tqx-cli", "--json", "factor_result", rid])
        status = str(res.get("status", "")).lower()
        if res.get("success") and (res.get("metrics") or status in ("finished", "success", "completed", "done")):
            result = res
            break
        if status in ("failed", "error"):
            return {"ok": False, "stage": "result", "factor_id": fid, "run_id": rid, "error": res}
        time.sleep(4)
    if result is None:
        return {"ok": False, "stage": "timeout", "factor_id": fid, "run_id": rid,
                "note": "Backtest still running; check the run_id later."}
    try:
        import backtests
        backtests.record_result(rid, result)
    except Exception:
        pass
    metrics, group_returns = _parse_factor_metrics(result)
    return {"ok": True, "factor_id": fid, "run_id": rid, "formula": formula,
            "market": market, "metrics": metrics, "group_returns": group_returns}


def _num(v):
    """Coerce a metric string like '-0.0134' or '35.00%' to float."""
    try:
        s = str(v).strip().replace("%", "")
        return float(s)  # "280.94%" -> 280.94 (percent-value convention)
    except Exception:
        return None


def _parse_factor_metrics(result):
    """TQX nests analysis inside results.nodes[<id>].result_json (a JSON string).
    Extract clean IC/IR/t-value metrics + per-group returns."""
    metrics, group_returns = {}, []
    res = result.get("results") or {}
    nodes = res.get("nodes") or {}
    payload = None
    for nd in nodes.values():
        rj = nd.get("result_json") if isinstance(nd, dict) else None
        if rj:
            try:
                payload = json.loads(rj)
                break
            except Exception:
                pass
    if not payload:
        # newer TQX shape: results.factor_analysis.query_* sections
        fa = res.get("factor_analysis") or {}
        if fa:
            payload = {
                "factor_data_analysis": (fa.get("query_factor_analysis_data") or {}).get("factor_data_analysis"),
                "group_return_analysis": (fa.get("query_group_return_analysis") or {}).get("group_return_analysis"),
                "last_date_top_factor": (fa.get("query_last_date_top_factor") or {}).get("last_date_top_factor"),
            }
    if not payload:
        return metrics, group_returns
    imap = {
        "IC_mean": "ic", "Rank_IC": "rank_ic", "IC_std": "ic_std",
        "IC_IR": "ic_ir", "IR": "ir", "t统计量": "t_value",
        "t-value": "t_value", "p-value": "p_value", "单调性": "monotonicity",
    }
    for row in payload.get("factor_data_analysis") or []:
        ind = row.get("indicator")
        key = imap.get(ind)
        if key:
            metrics[key] = _num(row.get("factor1"))
    for g in payload.get("group_return_analysis") or []:
        group_returns.append({
            "group": g.get("group"),
            "annual_return": _num(g.get("annualizedReturn")),
            "sharpe": _num(g.get("sharpeRatio")),
            "max_drawdown": _num(g.get("maxDrawdown")),
            "win_rate": _num(g.get("monthlyWinRate")),
        })
    # surface the strongest group's return/sharpe as reference
    if group_returns:
        best = max(group_returns, key=lambda x: (x.get("annual_return") or -9e9))
        metrics["annual_return"] = best.get("annual_return")
        metrics["sharpe"] = best.get("sharpe")
    return metrics, group_returns


def _parse_strategy_metrics(result):
    """Tolerant extraction of strategy backtest summary metrics from TQX result.
    Looks through results.nodes[*].result_json for common performance keys."""
    metrics = {}
    kmap = {
        "annualizedReturn": "annual_return", "annual_return": "annual_return",
        "年化收益率": "annual_return", "sharpeRatio": "sharpe", "sharpe": "sharpe",
        "夏普比率": "sharpe", "maxDrawdown": "max_drawdown", "max_drawdown": "max_drawdown",
        "最大回撤": "max_drawdown", "totalReturn": "total_return", "累计收益率": "total_return",
        "winRate": "win_rate", "胜率": "win_rate", "volatility": "volatility",
        "back_profit": "total_return", "back_profit_year": "annual_return",
        "max_drawdown_rate": "max_drawdown", "sharpe_ratio": "sharpe",
        "benchmark_profit": "benchmark_return", "information_ratio": "information_ratio",
    }

    def scan(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = kmap.get(k)
                if key and key not in metrics:
                    metrics[key] = _num(v)
                else:
                    scan(v)
        elif isinstance(obj, list):
            for it in obj:
                scan(it)

    nodes = (result.get("results") or {}).get("nodes") or {}
    for nd in nodes.values():
        rj = nd.get("result_json") if isinstance(nd, dict) else None
        if rj:
            try:
                scan(json.loads(rj))
            except Exception:
                pass
    scan(result.get("metrics") or {})
    if not metrics:  # new API format: summary fields at result root (e.g. backtest_info)
        scan(result)
    return metrics


def t_run_strategy_backtest(code=None, market="us", name=None,
                            start_date="20260601", end_date="20260701",
                            start_capital=None, commission_rate=None,
                            slippage=None, frequency=None, **_):
    """Full-control strategy backtest: custom Python code (own stock pool,
    buy/sell logic), capital, commission, slippage, rebalance frequency."""
    _login()
    if not code:
        return {"ok": False, "error": "code (Python strategy) required"}
    name = name or f"AgentStrategy_{int(time.time())}"
    cmd = ["tqx-cli", "--json", "strategy_create", "--market", market,
           "--code", code, "--name", name,
           "--start-date", str(start_date), "--end-date", str(end_date)]
    if start_capital is not None:
        cmd += ["--start-capital", str(start_capital)]
    if commission_rate is not None:
        cmd += ["--commission-rate", str(commission_rate)]
    if slippage is not None:
        cmd += ["--slippage", str(slippage)]
    if frequency:
        cmd += ["--frequency", str(frequency)]
    create = _run_cmd(cmd)
    if not create.get("success"):
        return {"ok": False, "stage": "create", "error": create.get("error") or create}
    sid = create.get("strategy_id") or create.get("workflow_id") or create.get("id")
    run = _run_cmd(["tqx-cli", "--json", "strategy_run", str(sid), "--no-wait"])
    if not run.get("success"):
        return {"ok": False, "stage": "run", "strategy_id": sid, "error": run.get("error") or run}
    rid = run.get("run_id")
    try:
        import backtests
        backtests.record_run(rid, {"market": market, "formula": code[:400], "code": code, "name": name,
                                   "start_date": start_date, "end_date": end_date,
                                   "start_capital": start_capital,
                                   "commission_rate": commission_rate,
                                   "slippage": slippage, "frequency": frequency},
                             source='agent', btype='strategy')
    except Exception:
        pass
    result = None
    for _i in range(45):  # strategy runs take longer
        res = _run_cmd(["tqx-cli", "--json", "strategy_result", str(rid)])
        status = str(res.get("status", "")).lower()
        if res.get("success") and ((res.get("results") or {}).get("nodes") or
                                   status in ("finished", "success", "completed", "done")):
            result = res
            break
        if status in ("failed", "error"):
            return {"ok": False, "stage": "result", "strategy_id": sid, "run_id": rid, "error": res}
        time.sleep(6)
    if result is None:
        return {"ok": False, "stage": "timeout", "strategy_id": sid, "run_id": rid,
                "note": "Strategy backtest still running; check run_id later via get_backtest_result."}
    try:
        import backtests
        backtests.record_result(rid, result)
    except Exception:
        pass
    metrics = _parse_strategy_metrics(result)
    return {"ok": True, "strategy_id": sid, "run_id": rid, "market": market,
            "name": name, "metrics": metrics}


def t_get_backtest_result(run_id=None, kind="factor", **_):
    _login()
    if not run_id:
        return {"ok": False, "error": "run_id required"}
    cmd = "strategy_result" if kind == "strategy" else "factor_result"
    res = _run_cmd(["tqx-cli", "--json", cmd, str(run_id)])
    try:
        import backtests
        backtests.record_result(run_id, res)
    except Exception:
        pass
    return res


def t_get_balance(**_):
    _login()
    return _run_cmd(["tqx-cli", "--json", "balance"])


def t_list_workflows(**_):
    _login()
    return _run_cmd(["tqx-cli", "--json", "workflow_list"])


def t_delete_workflow(workflow_id=None, **_):
    _login()
    if not workflow_id:
        return {"ok": False, "error": "workflow_id required"}
    return _run_cmd(["tqx-cli", "--json", "workflow_delete", str(workflow_id)])


def t_get_account(**_):
    _login()
    return _run_cmd(["tqx", "--json", "trading", "account"])


def t_get_positions(**_):
    _login()
    return _run_cmd(["tqx", "--json", "trading", "positions"])


def t_list_orders(**_):
    _login()
    return _run_cmd(["tqx", "--json", "trading", "orders", "list"])


def t_place_order(symbol=None, side="BUY", order_type="MARKET", quantity=1, price=None, reason=None, **_):
    _login()
    if not symbol:
        return {"ok": False, "error": "symbol required (e.g. AAPL.US)"}
    key = f"order-{int(time.time()*1000)}"
    cmd = ["tqx", "--json", "trading", "orders", "place",
           f"--symbol={symbol}", f"--side={side}", f"--orderType={order_type}",
           f"--quantity={quantity}", f"--idempotencyKey={key}"]
    if order_type == "LIMIT" and price:
        cmd.append(f"--price={price}")
    if reason:
        cmd.append(f"--reason={reason}")
    return _run_cmd(cmd)


def t_cancel_order(order_id=None, **_):
    _login()
    if not order_id:
        return {"ok": False, "error": "order_id required"}
    return _run_cmd(["tqx", "--json", "trading", "orders", "cancel", str(order_id)])


def t_list_strategies(market="us", **_):
    _login()
    return _run_cmd(["tqx-cli", "--json", "strategy_list", "--market", market])


TOOL_IMPL = {
    "run_factor_backtest": t_run_factor_backtest,
    "run_strategy_backtest": t_run_strategy_backtest,
    "get_backtest_result": t_get_backtest_result,
    "get_balance": t_get_balance,
    "list_workflows": t_list_workflows,
    "delete_workflow": t_delete_workflow,
    "get_account": t_get_account,
    "get_positions": t_get_positions,
    "list_orders": t_list_orders,
    "place_order": t_place_order,
    "cancel_order": t_cancel_order,
    "list_strategies": t_list_strategies,
}


# --------------------------------------------------------------------------
# Tool schemas (OpenAI function-calling format)
# --------------------------------------------------------------------------
TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "run_factor_backtest",
        "description": "Design-and-validate a quant factor: creates the factor from a TQX formula, runs the backtest, waits for completion, and returns IC/IR/t-value and other alpha metrics. Use this whenever the user wants to test, validate, or evaluate a factor idea.",
        "parameters": {"type": "object", "properties": {
            "formula": {"type": "string", "description": "TQX factor formula, e.g. 'close/ref(close,20)-1' for 20-day momentum. Supported ops: ref(x,n), mean(x,n), std(x,n), rank(x), correlation, etc."},
            "market": {"type": "string", "enum": ["us", "hk"], "description": "Market. Default us. TQX supports only US and HK."},
            "start_date": {"type": "string", "description": "YYYYMMDD backtest start"},
            "end_date": {"type": "string", "description": "YYYYMMDD backtest end"},
            "group_number": {"type": "integer", "description": "Number of quantile groups, default 2"},
            "adjustment_cycle": {"type": "integer", "description": "Position adjustment (rebalance) cycle in days, e.g. 1/5/20"},
            "factor_direction": {"type": "integer", "enum": [1, -1], "description": "1 = higher factor value is better; -1 = inverted"},
            "name": {"type": "string", "description": "Optional factor name"}
        }, "required": ["formula"]}}},
    {"type": "function", "function": {
        "name": "run_strategy_backtest",
        "description": "Full-control STRATEGY backtest with custom Python code: define your own stock pool (specific tickers), buy/sell logic, initial capital, commission, slippage, and rebalance frequency. Use this when the user wants to backtest specific stocks or custom trading logic that a factor formula cannot express. Write the TQX strategy Python code yourself.",
        "parameters": {"type": "object", "properties": {
            "code": {"type": "string", "description": "TQX panda_backtest strategy Python code. VERIFIED CONTRACT: (1) imports MUST be `from panda_backtest.api.api import *` AND `from panda_backtest.api.stock_us_api import *` (hk: stock_hk_api) AND `import tqx_data`; (2) define initialize(context) and handle_data(context, data); (3) US symbols use .NB suffix (AAPL.NB) — .US gives silent zero-trade runs; HK uses 00700.HK; (4) account id: context.account = list(context.stock_account_dict.keys())[0]; (5) trade via order_shares(context.account, symbol, qty, style=MarketOrderStyle), sell qty from position.sellable; (6) log with print() only — SRLog causes instant FAILED; (7) guard bar None: bar = data.get(symbol); skip if bar is None or bar.close <= 0."},
            "market": {"type": "string", "enum": ["us", "hk"]},
            "start_date": {"type": "string", "description": "YYYYMMDD"},
            "end_date": {"type": "string", "description": "YYYYMMDD"},
            "start_capital": {"type": "number", "description": "Initial capital, e.g. 1000000"},
            "commission_rate": {"type": "number", "description": "e.g. 0.0003 for 万三"},
            "slippage": {"type": "number", "description": "e.g. 0.001"},
            "frequency": {"type": "string", "enum": ["1d", "1M"], "description": "Rebalance frequency: daily or monthly"},
            "name": {"type": "string"}
        }, "required": ["code"]}}},
    {"type": "function", "function": {
        "name": "get_backtest_result",
        "description": "Fetch the result of a previously submitted backtest by run_id (factor or strategy). Also refreshes the persisted history record.",
        "parameters": {"type": "object", "properties": {
            "run_id": {"type": "string"},
            "kind": {"type": "string", "enum": ["factor", "strategy"]}
        }, "required": ["run_id"]}}},
    {"type": "function", "function": {
        "name": "get_balance",
        "description": "Check TQX computing-power (algo credits) balance. Check before launching heavy backtests.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "list_workflows",
        "description": "List all TQX factor & strategy workflows (research assets) under this account.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "delete_workflow",
        "description": "Delete a TQX workflow (factor or strategy) by id. Only when the user asks to clean up.",
        "parameters": {"type": "object", "properties": {
            "workflow_id": {"type": "string"}}, "required": ["workflow_id"]}}},
    {"type": "function", "function": {
        "name": "get_account",
        "description": "Get the paper trading account: cash, buying power, net liquidation, currency.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_positions",
        "description": "Get current open positions in the paper trading account.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "list_orders",
        "description": "List current/recent orders in the paper trading account.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "place_order",
        "description": "Place a PAPER (simulated) trade order. Only use after the user has agreed to trade, or when the user explicitly asks to buy/sell. Always explain the rationale.",
        "parameters": {"type": "object", "properties": {
            "symbol": {"type": "string", "description": "e.g. AAPL.US, 0700.HK"},
            "side": {"type": "string", "enum": ["BUY", "SELL"]},
            "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"]},
            "quantity": {"type": "integer"},
            "price": {"type": "number", "description": "Required only for LIMIT orders"},
            "reason": {"type": "string", "description": "Short rationale for the trade"}
        }, "required": ["symbol", "side", "order_type", "quantity"]}}},
    {"type": "function", "function": {
        "name": "cancel_order",
        "description": "Cancel an open paper order by its order_id.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "list_strategies",
        "description": "List available saved strategies for a market.",
        "parameters": {"type": "object", "properties": {
            "market": {"type": "string", "enum": ["us", "hk"]}}}}},
]

SYSTEM_PROMPT = """You are the TQX Quant Agent, an autonomous quantitative research and paper-trading assistant.

Your job: turn the user's natural-language intent into concrete quant actions using your tools.
- When the user describes a factor idea, TRANSLATE it into a valid TQX formula yourself, then call run_factor_backtest to validate it. Do not ask the user to write formulas.
- When the user wants SPECIFIC stocks (a custom pool like "only AAPL and NVDA"), custom buy/sell logic, capital/commission/slippage settings — use run_strategy_backtest and write the Python strategy code yourself. Factor analysis is always whole-market; strategy backtest is for custom pools.
- Markets: TQX supports only US (us) and HK (hk). A-shares are NOT available — say so if asked.
- Before launching heavy/long backtests, you may check get_balance for remaining algo credits.
- After a backtest, INTERPRET the metrics plainly: IC (predictive power, want |IC|>0.03), IR (stability, want >0.3), t-value (significance, want |t|>2), annualized return, Sharpe. State whether the factor looks promising and why.
- For trading, this is a PAPER (simulated) account, so you may place/cancel orders directly when the user asks to trade or approves a trade. Always check account/positions first when sizing a trade, and always give a one-line rationale.
- Be decisive and act with the tools instead of describing what could be done. Chain multiple tools in one turn when it moves the task forward (e.g. backtest -> check account -> place order).
- Keep replies concise and in the user's language. Report concrete numbers from tool results, never invent them.

Common formula patterns: momentum = close/ref(close,N)-1 ; reversal = -1*(close/ref(close,N)-1) ; volatility = std(close/ref(close,1)-1, N) ; volume factor = volume/mean(volume,N).
"""


def run_agent_turn(history, max_steps=8):
    """history: list of {role, content} (and tool messages). Returns dict with
    reply text, the full updated message list, and a log of tool actions taken."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    actions = []
    total_cost = 0.0
    for _step in range(max_steps):
        r = proxied_post(LLM_URL, json={
            "model": AGENT_MODEL, "messages": messages,
            "tools": TOOLS_SCHEMA, "temperature": 0.2, "max_tokens": 1200,
        }, headers={"SC-CALLER-ID": CALLER_ID}, timeout=90)
        if r.status_code != 200:
            return {"reply": f"LLM error {r.status_code}: {r.text[:300]}",
                    "messages": messages, "actions": actions, "cost": total_cost}
        data = r.json()
        total_cost += float(data.get("usage", {}).get("cost") or 0)
        msg = data["choices"][0]["message"]
        tool_calls = msg.get("tool_calls")
        # append assistant message (must include tool_calls if present)
        assistant_msg = {"role": "assistant", "content": msg.get("content") or ""}
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        if not tool_calls:
            return {"reply": msg.get("content") or "", "messages": messages,
                    "actions": actions, "cost": round(total_cost, 6)}
        for tc in tool_calls:
            fn = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except Exception:
                args = {}
            impl = TOOL_IMPL.get(fn)
            result = impl(**args) if impl else {"error": f"unknown tool {fn}"}
            actions.append({"tool": fn, "args": args, "result": result})
            # journal: record decisive actions (orders / backtests) with reasoning
            if fn in ("place_order", "cancel_order", "run_factor_backtest"):
                try:
                    import journal
                    user_msgs = [m.get("content", "") for m in history
                                 if isinstance(m, dict) and m.get("role") == "user"]
                    ok = isinstance(result, dict) and not result.get("error")
                    journal.log_decision("agent", user_msgs[-1] if user_msgs else "",
                        (msg.get("content") or args.get("reason") or ""),
                        [{"tool": fn, "args": args, "ok": ok,
                          "order_id": (result or {}).get("order_id"),
                          "summary": json.dumps(result, ensure_ascii=False)[:300]}])
                except Exception:
                    pass
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "name": fn, "content": json.dumps(result, ensure_ascii=False)[:6000]})
    return {"reply": "(Reached step limit — partial result above.)",
            "messages": messages, "actions": actions, "cost": round(total_cost, 6)}
