#!/bin/bash
# x402 gateway keepalive — one watchdog for ALL registered x402 services.
# Modeled on the cloudflare-tunnel-publish keepalive: idempotent, state-change
# reporting only, safe to run from both setup.sh (boot) and a scheduled task.
#
# Registry: /data/workspace/.x402/services.json  (written by monetize.py)
# For each service: if gateway /x402/health fails -> restart gateway from its
# config. Upstream being down is reported but NOT restarted here (the upstream
# has its own supervisor — preview/previews.json — do not fight it).

REG="/data/workspace/.x402/services.json"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="/data/workspace/.x402/.keepalive_state"
mkdir -p "$(dirname "$STATE")"; touch "$STATE"

[ -f "$REG" ] || exit 0

python3 - "$REG" "$SKILL_DIR" "$STATE" <<'PYEOF'
import json, os, subprocess, sys, time
import urllib.request

reg_path, skill_dir, state_path = sys.argv[1], sys.argv[2], sys.argv[3]
reg = json.load(open(reg_path))
state = {}
if os.path.getsize(state_path) > 0:
    try:
        state = json.load(open(state_path))
    except Exception:
        state = {}

changed = []
for name, svc in reg.get("services", {}).items():
    port, cfg = svc["port"], svc["config"]
    ok = False
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/x402/health", timeout=5) as r:
            body = json.load(r)
            ok = body.get("gateway") == "ok"
            upstream = body.get("upstream")
    except Exception:
        ok, upstream = False, "unknown"

    prev = state.get(name, {}).get("ok")
    if not ok:
        # restart gateway
        log = svc.get("log", f"/data/workspace/.x402/{name}/gateway.log")
        with open(log, "a") as lf:
            lf.write(f"\n[keepalive {time.strftime('%F %T')}] gateway down, restarting\n")
            p = subprocess.Popen(
                [sys.executable, os.path.join(skill_dir, "gateway", "app.py"), cfg],
                stdout=lf, stderr=subprocess.STDOUT, cwd="/data/workspace",
                start_new_session=True)
        svc["pid"] = p.pid
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/x402/health", timeout=5) as r:
                ok = json.load(r).get("gateway") == "ok"
        except Exception:
            ok = False
        changed.append(f"{name}: restarted -> {'recovered' if ok else 'STILL DOWN'}")
    elif prev is False:
        changed.append(f"{name}: recovered")
    if ok and upstream == "down" and state.get(name, {}).get("upstream") != "down":
        changed.append(f"{name}: gateway ok but UPSTREAM DOWN (port {svc.get('upstream_port')})")

    state[name] = {"ok": ok, "upstream": upstream, "ts": time.time()}

json.dump(reg, open(reg_path + ".tmp", "w"), indent=2)
os.replace(reg_path + ".tmp", reg_path)
json.dump(state, open(state_path, "w"))

# print ONLY on state change -> scheduled task stays silent when healthy
if changed:
    print("x402 keepalive: " + "; ".join(changed))
PYEOF
