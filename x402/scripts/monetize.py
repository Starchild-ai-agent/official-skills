"""One-command monetization: wrap an existing local service with an x402 gateway.

Usage:
  python3 skills/x402/scripts/monetize.py \
      --name my-api --upstream-port 5173 --mode pay_per_use \
      --price 0.01 [--networks all] [--pay-to 0x..]

  # lock to a single chain (custom)
  python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
      --mode pay_per_use --price 0.01 --networks eip155:8453

  # subscription / metered (legacy/extended modes)
  python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
      --mode subscription --price-per-credit 0.001 --min-credits 100 \
      --route "GET /api/*=1"        # =N means N credit units per call

Networks (plans-280-04 §5.6.4):
  --networks all            follow the platform mainnet full set (default;
                            testnet full set when the facilitator is x402.org)
  --networks eip155:8453,eip155:143   custom lock to the given CAIP-2 list
  (omitted)                 same as "all" — config gets networks_mode=all

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


def _port_in_use(port: int) -> bool:
    """Check if a port is already in use (listening)."""
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


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


def _pids_for_config(cfg_path: str) -> list:
    """Find gateway processes serving this config (by /proc cmdline)."""
    pids = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == os.getpid():
            continue
        try:
            with open(f"/proc/{d}/cmdline", "rb") as f:
                cmd = f.read().decode(errors="replace").replace("\x00", " ")
        except OSError:
            continue
        if cfg_path in cmd and "gateway/app.py" in cmd:
            pids.append(int(d))
    return pids


def stop_service(name: str) -> dict:
    reg = load_registry()
    svc = reg["services"].get(name)
    if not svc:
        sys.exit(f"unknown service '{name}' — registered: {list(reg['services'])}")
    killed = []
    for pid in _pids_for_config(svc["config"]):
        try:
            os.kill(pid, 15)
            killed.append(pid)
        except ProcessLookupError:
            pass
    time.sleep(1.0)
    port = svc.get("port")
    with socket.socket() as s:
        port_free = (s.connect_ex(("127.0.0.1", port)) != 0) if port else True
    svc["pid"] = None
    save_registry(reg)
    return {"ok": port_free, "name": name, "killed_pids": killed,
            "port": port, "port_free": port_free,
            "note": "" if port_free else "port still held by a non-gateway "
            "process — inspect /proc/*/cmdline or move to a fresh port"}


def restart_service(name: str) -> dict:
    r = stop_service(name)
    reg = load_registry()
    svc = reg["services"][name]
    log_path = svc.get("log") or os.path.join(os.path.dirname(svc["config"]), "gateway.log")
    pid = start_gateway(svc["config"], log_path)
    svc["pid"] = pid
    save_registry(reg)
    import httpx
    ok = False
    for _ in range(20):
        try:
            ok = httpx.get(f"http://127.0.0.1:{svc['port']}/x402/health",
                           timeout=2).status_code == 200
            if ok:
                break
        except Exception:
            time.sleep(0.5)
    return {"ok": ok, "name": name, "pid": pid, "port": svc["port"],
            "stopped": r["killed_pids"], "log": log_path}


def main():
    # lifecycle subcommands: --stop NAME / --restart NAME (no other args)
    if len(sys.argv) >= 3 and sys.argv[1] in ("--stop", "--restart"):
        fn = stop_service if sys.argv[1] == "--stop" else restart_service
        print(json.dumps(fn(sys.argv[2]), indent=2))
        return

    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--no-start", action="store_true",
                    help="write config + register only; do NOT start the gateway "
                         "(use when preview(serve) will own the process)")
    ap.add_argument("--upstream-port", type=int, required=True)
    ap.add_argument("--mode", default="pay_per_use",
                    choices=["pay_per_use", "lifetime", "monthly", "weekly",
                             "quarterly", "yearly", "prepaid",  # platform (Starchild community-gateway contract)
                             "payperuse", "subscription", "metered", "timepass"])  # legacy/extended
    ap.add_argument("--price", default="0.01",
                    help="platform modes: service price in USD (pay_per_use/prepaid per call, lifetime one-time, monthly per month)")
    ap.add_argument("--facilitator-admin-token", default=os.environ.get("X402_FACILITATOR_ADMIN_TOKEN", ""),
                    help="platform modes lifetime/monthly: token for facilitator /access-status + /settlements")
    ap.add_argument("--deposit", default="",
                    help="prepaid: suggested deposit in USD (default: 100 calls worth, min $0.10)")
    ap.add_argument("--plan", action="append", default=[],
                    help='multi-plan: extra pricing option "MODE=PRICE_USD" '
                         '(e.g. --plan weekly=3 --plan yearly=90). --mode is the '
                         'default plan; buyers pick others via X-Pricing-Model. '
                         'pay_per_use cannot be combined.')
    ap.add_argument("--pass-days", type=float, default=30, help="timepass: pass validity in days")
    ap.add_argument("--pass-price", default="5", help="timepass: pass price in USD, e.g. 5 or $4.99")
    ap.add_argument("--route", action="append", default=[],
                    help='payperuse: "GET /api/*=$0.01"; sub/metered: "GET /api/*=UNITS"')
    ap.add_argument("--networks", default=os.environ.get("X402_NETWORKS", "all"),
                    help="'all' (default) = follow the platform mainnet full set "
                         "(Base+Monad+Robinhood+X Layer); testnet full set when the facilitator is "
                         "x402.org. Or a comma-separated CAIP-2 list to lock to "
                         "specific chains, e.g. 'eip155:8453,eip155:143,eip155:4663,eip155:196'.")
    ap.add_argument("--network", default="",
                    help="DEPRECATED: use --networks. If set, treated as a single-chain "
                         "custom lock (networks_mode=custom, networks=[<value>]).")
    ap.add_argument("--facilitator", default=os.environ.get("X402_FACILITATOR", ""),
                    help="empty = x402.org for testnet; mainnet defaults to the platform "
                         "facilitator (override via X402_FACILITATOR_URL). "
                         "x402.org is REJECTED for mainnet (testnet-only).")
    ap.add_argument("--facilitator-token", default=os.environ.get("X402_FACILITATOR_TOKEN", ""),
                    help="bearer token if the facilitator enforces caller auth (X402_GATEWAY_TOKENS)")
    ap.add_argument("--pay-to", default="")
    ap.add_argument("--price-per-credit", type=float, default=0.01)
    ap.add_argument("--min-credits", type=int, default=100)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()

    # --- networks resolution (plans-280-04 §5.6.4) -------------------------
    # --networks: "all" (default) or comma-separated CAIP-2 list (custom).
    # --network (deprecated): if set, overrides --networks as a single-chain
    # custom lock for backward compatibility.
    MAINNET_IDS = {"eip155:8453", "eip155:143"}
    # Mirror platform_modes.ASSETS — fail fast on unknown CAIP-2 ids (S-9).
    KNOWN_NETWORKS = {
        "eip155:8453", "eip155:84532", "eip155:143", "eip155:10143",
    }
    if args.network:
        # deprecated single-chain flag -> custom lock
        networks_list = [n.strip() for n in args.network.split(",") if n.strip()]
        networks_mode = "custom"
    elif args.networks.strip().lower() == "all":
        networks_list = []
        networks_mode = "all"
    else:
        networks_list = [n.strip() for n in args.networks.split(",") if n.strip()]
        networks_mode = "custom" if networks_list else "all"
    if networks_mode == "custom":
        if not networks_list:
            sys.exit("networks_mode=custom requires a non-empty --networks list")
        bad = [n for n in networks_list if n not in KNOWN_NETWORKS]
        if bad:
            sys.exit(f"unsupported network(s) {bad} (known: {sorted(KNOWN_NETWORKS)})")
    has_mainnet = any(n in MAINNET_IDS for n in networks_list) or networks_mode == "all"

    # mainnet default: platform facilitator (Starchild self-hosted, multi-chain)
    if has_mainnet and not args.facilitator:
        args.facilitator = os.environ.get(
            "X402_FACILITATOR_URL", "https://starchild-x402-facilitator.fly.dev")

    # Hard guard: x402.org facilitator supports TESTNETS ONLY (verified via
    # /supported — no mainnet chains). A mainnet service pointed at it looks
    # healthy (discovery + 402 work) but EVERY buyer settlement fails with
    # 402 unexpected_error. Seen live on a community machine.
    if has_mainnet and "x402.org" in (args.facilitator or ""):
        sys.exit("mainnet networks cannot use the x402.org facilitator "
                 "(testnet-only). Use a mainnet-capable facilitator, e.g. "
                 "--facilitator https://starchild-x402-facilitator.fly.dev")

    PLATFORM = ("pay_per_use", "lifetime", "monthly", "weekly",
                "quarterly", "yearly", "prepaid")
    SUBSCRIPTION = ("lifetime", "monthly", "weekly", "quarterly", "yearly")
    routes = {}
    for spec in args.route:
        pattern, _, val = spec.rpartition("=")
        if not pattern and args.mode in PLATFORM:
            # platform modes: bare pattern OK (single service price via --price)
            pattern, val = spec, "1"
        if not pattern:
            sys.exit(f"bad --route {spec!r}, expected 'METHOD /path=value'")
        if args.mode == "payperuse":
            routes[pattern] = {"price": val if val.startswith("$") else f"${val}"}
        else:
            routes[pattern] = {"units": int(val)}
    if not routes:
        if args.mode in PLATFORM:
            routes["* /api/*"] = {"units": 1}   # sensible default: protect /api/*
        else:
            sys.exit("at least one --route required")

    pay_to = args.pay_to or default_pay_to()
    port = args.port or free_port()

    # Upstream port conflict check: warn (not fail) if the upstream port is
    # already in use by a DIFFERENT registered service — the gateway will proxy
    # to the wrong upstream (root cause of blank pages in multi-service setups).
    if _port_in_use(args.upstream_port):
        reg_check = load_registry()
        conflict = [n for n, s in reg_check.get("services", {}).items()
                    if s.get("upstream_port") == args.upstream_port and n != args.name]
        if conflict:
            print(f"⚠️  WARNING: upstream port {args.upstream_port} is already in use "
                  f"by service(s): {conflict}. The gateway will proxy to the WRONG "
                  f"upstream. Either stop the conflicting service(s) or use a "
                  f"different --upstream-port.", file=sys.stderr)

    svc_dir = os.path.join(REG_DIR, args.name)
    os.makedirs(svc_dir, exist_ok=True)
    cfg = {
        "mode": args.mode,
        "upstream": f"http://127.0.0.1:{args.upstream_port}",
        "pay_to": pay_to,
        "port": port,
        "routes": routes,
        "state_dir": os.path.join(svc_dir, "state"),
    }
    # Multi-chain config (plans-280-04 §5.6.4):
    # - "all" (default): write networks_mode=all, no networks list. The
    #   gateway resolves to the platform mainnet full set at startup.
    # - custom: write networks_mode=custom + networks=[...]. The gateway
    #   locks to exactly those chains.
    # Legacy single "network" field is NOT written — resolve_networks does
    # not do "legacy Base -> all" guessing (§5.6.1).
    cfg["networks_mode"] = networks_mode
    if networks_mode == "custom":
        if not networks_list:
            sys.exit("networks_mode=custom requires a non-empty --networks list")
        cfg["networks"] = networks_list
    if args.facilitator:
        cfg["facilitator"] = args.facilitator
    if args.facilitator_token:
        cfg["facilitator_token"] = args.facilitator_token
    if args.mode in PLATFORM:
        cfg["price_usd"] = str(args.price).lstrip("$")
        if args.mode == "prepaid" and args.deposit:
            cfg["deposit_usd"] = str(args.deposit).lstrip("$")
        if args.plan:
            if args.mode == "pay_per_use":
                sys.exit("pay_per_use cannot be combined with other plans (--plan)")
            plans = {}
            for spec in args.plan:
                try:
                    m, p = spec.split("=", 1)
                except ValueError:
                    sys.exit(f"--plan must be MODE=PRICE_USD, got: {spec}")
                m = m.strip().lower()
                if m == "pay_per_use":
                    sys.exit("pay_per_use cannot be offered as an extra plan")
                if m not in PLATFORM:
                    sys.exit(f"unknown plan mode '{m}' (allowed: {PLATFORM})")
                plans[m] = {"price_usd": str(p).lstrip("$")}
            cfg["plans"] = plans
        if args.facilitator_admin_token:
            cfg["facilitator_admin_token"] = args.facilitator_admin_token
        elif args.mode in SUBSCRIPTION or any(
                m in SUBSCRIPTION for m in cfg.get("plans", {})):
            # No admin token — the gateway will fall back to the
            # community-gateway proxy for access-status checks (the proxy
            # holds the admin token server-side). This requires
            # COMMUNITY_GATEWAY_URL to be set in the environment.
            cg = os.environ.get("COMMUNITY_GATEWAY_URL", "")
            if not cg:
                print("[x402] WARNING: no --facilitator-admin-token and no "
                      "COMMUNITY_GATEWAY_URL — the gateway will fail at "
                      "startup unless one of them is available.", flush=True)
        if not args.facilitator:
            sys.exit("platform modes require --facilitator (e.g. https://starchild-x402-facilitator.fly.dev)")
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
    pid = None if args.no_start else start_gateway(cfg_path, log_path)

    reg = load_registry()
    reg["services"][args.name] = {
        "config": cfg_path, "port": port, "upstream_port": args.upstream_port,
        "pid": pid, "log": log_path, "created": time.time(),
    }
    save_registry(reg)

    if args.no_start:
        print(json.dumps({
            "ok": True, "name": args.name, "gateway_port": port, "started": False,
            "mode": args.mode, "networks_mode": networks_mode,
            "networks": (networks_list or "all (platform mainnet full set)"),
            "pay_to": pay_to, "config": cfg_path,
            "gateway_command": f"python3 {os.path.join(SKILL, 'gateway', 'app.py')} {cfg_path}",
            "next": "config written, gateway NOT started. Wrap your upstream + the "
                    "gateway_command in a start.py and run it under "
                    "preview(action='serve', port=<gateway_port>) so preview owns "
                    "the process lifecycle (auto-restart after reboots). ONE owner "
                    "per port — do not also start the gateway another way.",
        }, indent=2))
        return

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
        "mode": args.mode, "networks_mode": networks_mode,
        "networks": (networks_list or "all (platform mainnet full set)"),
        "pay_to": pay_to,
        "info_endpoint": f"http://127.0.0.1:{port}/x402/info",
        "config": cfg_path, "log": log_path,
        "manage": f"monetize.py --stop {args.name} | --restart {args.name} "
                  "(restart after editing x402.config.json, e.g. network switch)",
        "next": "this gateway runs as a monetize-managed background process "
                "(keepalive revives it). To publish via preview/community-publish "
                "do NOT start it again under preview(serve) — that collides on "
                "the port. Either keep it monetize-managed (publish only needs "
                "the port), or --stop it and re-run with --no-start so "
                "preview(serve) owns the process (SKILL.md §Gateway lifecycle).",
    }, indent=2))


if __name__ == "__main__":
    main()
