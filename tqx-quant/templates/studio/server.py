import http.server
import socketserver
import json
import subprocess
import urllib.parse
import os
import time
from concurrent.futures import ThreadPoolExecutor

PORT = 8090

def load_env():
    env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip("'\"")

def sync_tqx_config():
    persistent_dir = '/data/workspace/.tqx'
    root_dir = '/root/.tqx'
    os.makedirs(persistent_dir, exist_ok=True)
    os.makedirs(root_dir, exist_ok=True)
    
    p_cfg = os.path.join(persistent_dir, 'config.yaml')
    r_cfg = os.path.join(root_dir, 'config.yaml')

    if os.path.exists(p_cfg) and not os.path.exists(r_cfg):
        import shutil
        shutil.copy(p_cfg, r_cfg)
    elif os.path.exists(r_cfg):
        import shutil
        shutil.copy(r_cfg, p_cfg)

class TQXHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        path_str = parsed.path
        if path_str == '/' or path_str == '/index.html':
            return os.path.join(os.path.dirname(__file__), 'index.html')
        return os.path.join(os.path.dirname(__file__), path_str.lstrip('/'))

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/api/status':
            load_env()
            sync_tqx_config()
            login_res = self._ensure_research_login()
            # Run all read-only CLI queries in parallel to avoid slow page load
            with ThreadPoolExecutor(max_workers=5) as ex:
                f_bal = ex.submit(self._run_cmd, ["tqx-cli", "--json", "balance"])
                f_acc = ex.submit(self._run_cmd, ["tqx", "--json", "trading", "account"])
                f_pos = ex.submit(self._run_cmd, ["tqx", "--json", "trading", "positions"])
                f_ord = ex.submit(self._run_cmd, ["tqx", "--json", "trading", "orders", "list"])
                f_trd = ex.submit(self._run_cmd, ["tqx", "--json", "trading", "trades", "--limit=20"])
                balance_res = f_bal.result()
                account_res = f_acc.result()
                positions_res = f_pos.result()
                orders_res = f_ord.result()
                trades_res = f_trd.result()

            try:
                import journal
                journal.snapshot_nav(account_res if isinstance(account_res, dict) else {})
            except Exception:
                pass
            
            self._send_json({
                "status": "ok",
                "auth": {
                    "research_login": login_res.get("success", False),
                    "email": os.environ.get("TQX_EMAIL", ""),
                    "has_trading_key": bool(os.environ.get("TQX_API_KEY", ""))
                },
                "balance": balance_res.get("balance", {}),
                "account": account_res if "error" not in account_res else None,
                "positions": positions_res.get("items", []) if isinstance(positions_res, dict) else [],
                "orders": orders_res.get("items", []) if isinstance(orders_res, dict) else [],
                "trades": trades_res.get("items", []) if isinstance(trades_res, dict) else []
            })
            return

        if parsed.path == '/api/decisions':
            import journal
            limit = int(query.get('limit', ['100'])[0])
            self._send_json({"items": journal.read_decisions(limit)})
            return

        if parsed.path == '/api/nav':
            import journal
            self._send_json({"points": journal.read_nav(), "stats": journal.nav_stats()})
            return

        if parsed.path == '/api/strategies':
            import strategies
            self._send_json({"items": strategies.list_all()})
            return

        if parsed.path == '/api/accounts':
            self._send_json({"items": [
                {"id": "paper", "label": "仿真盘 PAPER · account 517", "active": True},
                {"id": "live", "label": "真实盘（未接入）", "active": False, "disabled": True},
            ]})
            return

        if parsed.path == '/api/workflow/pending':
            load_env(); sync_tqx_config(); self._ensure_research_login()
            res = self._run_cmd(["tqx-cli", "--json", "workflow_pending_list"])
            self._send_json(res)
            return

        if parsed.path == '/api/strategy/list':
            load_env(); sync_tqx_config(); self._ensure_research_login()
            market = query.get('market', ['us'])[0]
            res = self._run_cmd(["tqx-cli", "--json", "strategy_list", "--market", market])
            self._send_json(res)
            return

        if parsed.path == '/api/factor/result':
            run_id = query.get('run_id', [''])[0]
            if not run_id:
                self._send_json({"error": "missing run_id"}, 400)
                return
            res = self._run_cmd(["tqx-cli", "--json", "factor_result", run_id])
            try:
                import backtests
                backtests.record_result(run_id, res)
            except Exception:
                pass
            self._send_json(res)
            return

        if parsed.path == '/api/backtests':
            import backtests
            self._send_json({"items": backtests.list_all(int(query.get('limit', ['100'])[0]))})
            return

        if parsed.path == '/api/backtests/get':
            import backtests
            rid = query.get('run_id', [''])[0]
            full = backtests.get(rid)
            if full is None:
                self._send_json({"error": "not found"}, 404)
            else:
                self._send_json(full)
            return

        super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8')
        data = json.loads(body) if body else {}

        if self.path == '/api/factor/run':
            load_env()
            sync_tqx_config()
            self._ensure_research_login()

            market = data.get('market', 'us')
            formula = data.get('formula', 'close/ref(close,5)-1')
            name = data.get('name', 'Custom_Factor')
            start_date = data.get('start_date', '20260601')
            end_date = data.get('end_date', '20260701')
            group_number = str(data.get('group_number', 2))
            adjustment_cycle = str(data.get('adjustment_cycle', '') or '').strip()
            factor_direction = str(data.get('factor_direction', 1))

            create_cmd = [
                "tqx-cli", "--json", "factor_create",
                "--market", market,
                "--formula", formula,
                "--name", name,
                "--start-date", start_date,
                "--end-date", end_date,
                "--group-number", group_number,
                "--factor-direction", factor_direction
            ]
            if adjustment_cycle:
                create_cmd += ["--adjustment-cycle", adjustment_cycle]
            c_res = self._run_cmd(create_cmd)
            
            # Check if login is required or token expired
            if not c_res.get('success') and any(k in str(c_res) for k in ["LOGIN_REQUIRED", "Please log in", "CONFIG_ERROR", "accessToken"]):
                self._ensure_research_login(force=True)
                c_res = self._run_cmd(create_cmd)

            if not c_res.get('success'):
                err_val = c_res.get('error')
                if isinstance(err_val, dict):
                    err_msg = err_val.get('message') or err_val.get('detail') or str(err_val)
                elif isinstance(err_val, str):
                    err_msg = err_val
                else:
                    err_msg = c_res.get('detail') or "因子创建失败"
                self._send_json({"error": err_msg, "details": c_res}, 400)
                return

            factor_id = c_res.get('factor_id')
            r_res = self._run_cmd(["tqx-cli", "--json", "factor_run", factor_id, "--no-wait"])
            if not r_res.get('success') and any(k in str(c_res) for k in ["LOGIN_REQUIRED", "Please log in", "CONFIG_ERROR", "accessToken"]):
                self._ensure_research_login(force=True)
                r_res = self._run_cmd(["tqx-cli", "--json", "factor_run", factor_id, "--no-wait"])
            if not r_res.get('success'):
                err_val = r_res.get('error')
                if isinstance(err_val, dict):
                    err_msg = err_val.get('message') or err_val.get('detail') or str(err_val)
                elif isinstance(err_val, str):
                    err_msg = err_val
                else:
                    err_msg = r_res.get('detail') or "因子运行失败"
                self._send_json({"error": err_msg, "details": r_res}, 400)
                return

            run_id = r_res.get('run_id')
            try:
                import backtests
                backtests.record_run(run_id, {
                    "market": market, "formula": formula, "name": name,
                    "start_date": start_date, "end_date": end_date,
                    "group_number": group_number,
                    "adjustment_cycle": adjustment_cycle,
                    "factor_direction": factor_direction}, source='ui')
            except Exception:
                pass
            self._send_json({
                "success": True,
                "factor_id": factor_id,
                "run_id": run_id
            })
            return

        if self.path == '/api/trading/order':
            symbol = data.get('symbol', 'AAPL.US')
            side = data.get('side', 'BUY')
            order_type = data.get('order_type', 'MARKET')
            quantity = str(data.get('quantity', 1))
            price = data.get('price')

            key = f"order-{int(time.time()*1000)}"
            cmd = [
                "tqx", "--json", "trading", "orders", "place",
                f"--symbol={symbol}",
                f"--side={side}",
                f"--orderType={order_type}",
                f"--quantity={quantity}",
                f"--idempotencyKey={key}"
            ]
            if order_type == 'LIMIT' and price:
                cmd.append(f"--price={price}")
            reason = data.get('reason')
            if reason:
                cmd.append(f"--reason={reason}")

            res = self._run_cmd(cmd)
            try:
                import journal
                ok = isinstance(res, dict) and not res.get("error")
                journal.log_decision("manual", f"手动下单 {side} {quantity} {symbol}",
                    reason or "", [{"tool": "place_order",
                    "args": {"symbol": symbol, "side": side, "order_type": order_type,
                             "quantity": quantity, "price": price},
                    "ok": ok, "order_id": (res or {}).get("order_id"),
                    "summary": json.dumps(res, ensure_ascii=False)[:300]}])
            except Exception:
                pass
            self._send_json(res)
            return

        if self.path == '/api/decisions/log':
            # external writers (e.g. thread-driven agent) append decisions here
            import journal
            rec = journal.log_decision(
                data.get('source', 'thread'), data.get('instruction', ''),
                data.get('reasoning', ''), data.get('actions', []))
            self._send_json({"success": True, "record": rec})
            return

        if self.path == '/api/agent/chat':
            load_env()
            sync_tqx_config()
            self._ensure_research_login()
            try:
                import agent as tqx_agent
                import importlib; importlib.reload(tqx_agent)
                history = data.get('history', [])
                if not isinstance(history, list) or not history:
                    self._send_json({"error": "empty history"}, 400)
                    return
                out = tqx_agent.run_agent_turn(history)
                self._send_json({
                    "reply": out.get("reply", ""),
                    "actions": out.get("actions", []),
                    "cost": out.get("cost", 0),
                    "messages": out.get("messages", [])
                })
            except Exception as e:
                import traceback
                self._send_json({"error": str(e), "trace": traceback.format_exc()[-1500:]}, 500)
            return

        if self.path == '/api/strategies/save':
            import strategies
            rec = strategies.create(data)
            import journal
            journal.log_decision('backtest', f"应用策略到自动交易: {rec['name']}",
                                 f"公式 {rec['formula']} | 市场 {rec['market']} | 指标 {json.dumps(rec['metrics'], ensure_ascii=False)}",
                                 [])
            self._send_json({"success": True, "strategy": rec})
            return

        if self.path == '/api/strategies/update':
            import strategies
            sid = data.get('id', '')
            if data.get('delete'):
                ok = strategies.delete(sid)
                self._send_json({"success": ok})
                return
            rec = strategies.update(sid, data)
            self._send_json({"success": rec is not None, "strategy": rec})
            return

        if self.path == '/api/strategies/execute':
            import strategies
            sid = data.get('id', '')
            rec = next((s for s in strategies.list_all() if s['id'] == sid), None)
            if not rec:
                self._send_json({"error": "strategy not found"}, 404)
                return
            load_env(); sync_tqx_config(); self._ensure_research_login()
            try:
                import agent as tqx_agent
                import importlib; importlib.reload(tqx_agent)
                instruction = (
                    f"【策略自动执行】策略「{rec['name']}」({rec['market'].upper()}市场)，"
                    f"因子公式: {rec['formula']}。"
                    f"请执行一次调仓检查：1) 用该公式跑最新因子回测，取 Top 选股；"
                    f"2) 对比当前仿真盘持仓；3) 若 Top1 未持有，用市价单在仿真盘买入 1 股作为信号验证，"
                    f"若已持有则回复无需操作。全程使用 PAPER 仿真盘，单笔不超过 1 股。"
                )
                out = tqx_agent.run_agent_turn([{"role": "user", "content": instruction}])
                import time as _t
                strategies.update(sid, {"last_run": _t.strftime('%Y-%m-%d %H:%M'), "_inc_run": True})
                self._send_json({"success": True, "reply": out.get("reply", ""),
                                 "actions": out.get("actions", []), "cost": out.get("cost", 0)})
            except Exception as e:
                import traceback
                self._send_json({"error": str(e), "trace": traceback.format_exc()[-1500:]}, 500)
            return

        if self.path == '/api/trading/cancel':
            order_id = data.get('order_id', '')
            if not order_id:
                self._send_json({"error": "missing order_id"}, 400)
                return
            res = self._run_cmd(["tqx", "--json", "trading", "orders", "cancel", str(order_id)])
            self._send_json(res)
            return

        self._send_json({"error": "not found"}, 404)

    def _ensure_research_login(self, force=False):
        load_env()
        sync_tqx_config()
        email = os.environ.get("TQX_EMAIL", "")
        password = os.environ.get("TQX_PASSWORD", "")
        if not email or not password:
            return {"success": False, "message": "未配置账号密码"}

        if not force and os.path.exists("/root/.tqx/config.yaml"):
            return {"success": True, "message": "配置正常"}

        cmd = ["tqx-cli", "--json", "login", "--email", email, "--password", password]
        res = self._run_cmd(cmd)
        sync_tqx_config()
        return res

    def _log_err(self, cmd, payload):
        try:
            import datetime
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log"), "a") as f:
                f.write("%s | %s | %s\n" % (datetime.datetime.now().isoformat(timespec='seconds'), " ".join(cmd[:6]), json.dumps(payload, ensure_ascii=False)[:800]))
        except Exception:
            pass

    def _run_cmd(self, cmd):
        env = os.environ.copy()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
            stdout = p.stdout.strip()
            if stdout:
                try:
                    res = json.loads(stdout)
                    # Handle automatic re-login on token expiration
                    if isinstance(res, dict) and res.get('error'):
                        self._log_err(cmd, res)
                    if isinstance(res, dict) and (
                        res.get('detail') == 'Please log in to continue.' or
                        (isinstance(res.get('error'), dict) and res.get('error', {}).get('type') == 'LOGIN_REQUIRED')
                    ):
                        email = os.environ.get("TQX_EMAIL", "")
                        password = os.environ.get("TQX_PASSWORD", "")
                        if email and password:
                            subprocess.run(["tqx-cli", "--json", "login", "--email", email, "--password", password], capture_output=True, env=env)
                            sync_tqx_config()
                            p2 = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
                            if p2.stdout.strip():
                                return json.loads(p2.stdout.strip())
                    return res
                except Exception:
                    self._log_err(cmd, {"raw_output": stdout[:400], "exit_code": p.returncode})
                    return {"raw_output": stdout, "exit_code": p.returncode}
            err = {"error": p.stderr.strip() or "empty output", "exit_code": p.returncode}
            self._log_err(cmd, err)
            return err
        except Exception as e:
            self._log_err(cmd, {"error": str(e)})
            return {"error": str(e)}

def _nav_poller():
    """Background NAV snapshot every 10 min so the equity curve accumulates
    even when the page is closed. Pure TQX API call — no LLM cost."""
    import journal
    while True:
        try:
            env = os.environ.copy()
            p = subprocess.run(["tqx", "--json", "trading", "account"],
                               capture_output=True, text=True, env=env, timeout=60)
            if p.stdout.strip():
                journal.snapshot_nav(json.loads(p.stdout.strip()))
        except Exception:
            pass
        time.sleep(600)


if __name__ == '__main__':
    load_env()
    sync_tqx_config()
    import threading
    threading.Thread(target=_nav_poller, daemon=True).start()
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    socketserver.ThreadingTCPServer.daemon_threads = True
    with socketserver.ThreadingTCPServer(("", PORT), TQXHandler) as httpd:
        print(f"TQX Studio Backend running at http://localhost:{PORT}")
        httpd.serve_forever()

@app.route('/api/backtest-demo', methods=['GET'])
def get_demo_backtest():
    """Demo backtest showing a successful MA strategy result on AAPL."""
    return jsonify({
        'ok': True,
        'backtest': {
            'name': '双均线策略 (AAPL.NB, 2025-01-01~2025-12-31)',
            'strategy': '5MA > 20MA 买入 90% 头寸 / 下穿全部卖出',
            'metrics': {
                'total_return': -0.131,
                'benchmark_return': 0.119,
                'trades': 18
            },
            'status': 'SUCCESS',
            'note': '已验证：美股标的必须用 .NB 后缀（AAPL.NB）。.US 后缀会导致行情为空、静默零成交。'
        }
    })
