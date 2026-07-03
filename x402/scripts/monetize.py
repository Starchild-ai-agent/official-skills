"""One-command monetization: wrap an existing local service with an x402 gateway.

Usage:
  python3 skills/x402/scripts/monetize.py \
      --name my-api --upstream-port 5173 --mode payperuse \
      --route "GET /api/*=\\$0.01" [--network eip155:8453] [--pay-to 0x..]

  # subscription / metered
  python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
      --mode subscription --price-per-credit 0.001 --min-credits 100 \
      --route "GET /api/*=1"        # =N means N credit units per call

Writes config + starts the gateway + registers it in the x402 registry
(/data/workspace/.x402/services.json) which keepalive.sh watches.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time

WS = "/data/workspace"
REG_DIR = os.path.join(WS, ".x402")
REG = os.path.join(REG_DIR, "services.json")
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port(start: int = 8402) -> int:
    for p in range(start, start + 200):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise RuntimeError("no free port")


def load_registry() -> dict:
    if os.path.exists(REG):
        with open(REG) as f:
            return json.load(f)
    return {"services": {}}


def save_registry(reg: dict):
    os.makedirs(REG_DIR, exist_ok=True)
    with open(REG + ".tmp", "w") as f:
        json.dump(reg, f, indent=2)
    os.replace(REG + ".tmp", REG)


def default_pay_to() -> str:
    from core.skill_tools import wallet
    info = wallet.wallet_info()
    return next(w["wallet_address"] for w in info["wallets"] if w["chain_type"] == "ethereum")


def start_gateway(cfg_path: str, log_path: str) -> int:
    with open(log_path, "w") as lf:
        p = subprocess.Popen([sys.executable, os.path.join(SKILL, "gateway", "app.py"), cfg_path],
                             stdout=lf, stderr=subprocess.STDOUT,
                             cwd=WS, start_new_session=True)
    return p.pid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--upstream-port", type=int, required=True)
    ap.add_argument("--mode", choices=["payperuse", "subscription", "metered", "timepass"], default="payperuse")
    ap.add_argument("--pass-days", type=float, default=30, help="timepass: pass validity in days")
    ap.add_argument("--pass-price", default="5", help="timepass: pass price in USD, e.g. 5 or $4.99")
    ap.add_argument("--route", action="append", default=[],
                    help='payperuse: "GET /api/*=$0.01"; sub/metered: "GET /api/*=UNITS"')
    ap.add_argument("--network", default=os.environ.get("X402_NETWORK", "eip155:84532"),
                    help="eip155:84532 = Base Sepolia (test), eip155:8453 = Base mainnet")
    ap.add_argument("--facilitator", default=os.environ.get("X402_FACILITATOR", ""),
                    help="empty = x402.org (testnet only). Mainnet needs CDP facilitator URL.")
    ap.add_argument("--pay-to", default="")
    ap.add_argument("--price-per-credit", type=float, default=0.01)
    ap.add_argument("--min-credits", type=int, default=100)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()

    if args.network == "eip155:8453" and not args.facilitator:
        # default to the self-hosted facilitator (local Phase-1, platform URL later)
        args.facilitator = os.environ.get(
            "X402_FACILITATOR_URL", "http://127.0.0.1:8410")

    routes = {}
    for spec in args.route:
        pattern, _, val = spec.rpartition("=")
        if not pattern:
            sys.exit(f"bad --route {spec!r}, expected 'METHOD /path=value'")
        if args.mode == "payperuse":
            routes[pattern] = {"price": val if val.startswith("$") else f"${val}"}
        else:
            routes[pattern] = {"units": int(val)}
    if not routes:
        sys.exit("at least one --route required")

    pay_to = args.pay_to or default_pay_to()
    port = args.port or free_port()

    svc_dir = os.path.join(REG_DIR, args.name)
    os.makedirs(svc_dir, exist_ok=True)
    cfg = {
        "mode": args.mode,
        "upstream": f"http://127.0.0.1:{args.upstream_port}",
        "pay_to": pay_to,
        "network": args.network,
        "port": port,
        "routes": routes,
        "state_dir": os.path.join(svc_dir, "state"),
    }
    if args.facilitator:
        cfg["facilitator"] = args.facilitator
    if args.mode in ("subscription", "metered"):
        cfg["topup"] = {"price_per_credit_usd": args.price_per_credit,
                        "min_credits": args.min_credits}
    elif args.mode == "timepass":
        cfg["topup"] = {"price_usd": str(args.pass_price),
                        "pass_days": args.pass_days}
    cfg_path = os.path.join(svc_dir, "x402.config.json")
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)

    log_path = os.path.join(svc_dir, "gateway.log")
    pid = start_gateway(cfg_path, log_path)

    reg = load_registry()
    reg["services"][args.name] = {
        "config": cfg_path, "port": port, "upstream_port": args.upstream_port,
        "pid": pid, "log": log_path, "created": time.time(),
    }
    save_registry(reg)

    # health check
    import httpx
    ok = False
    for _ in range(20):
        try:
            ok = httpx.get(f"http://127.0.0.1:{port}/x402/health", timeout=2).status_code == 200
            if ok:
                break
        except Exception:
            time.sleep(0.5)

    print(json.dumps({
        "ok": ok, "name": args.name, "gateway_port": port, "pid": pid,
        "mode": args.mode, "network": args.network, "pay_to": pay_to,
        "info_endpoint": f"http://127.0.0.1:{port}/x402/info",
        "config": cfg_path, "log": log_path,
        "next": "expose the GATEWAY port (not the upstream) via preview/community-publish; "
                "run keepalive registration (see SKILL.md §keepalive)",
    }, indent=2))


if __name__ == "__main__":
    main()
