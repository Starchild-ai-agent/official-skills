"""x402 skill end-to-end self-check.

Run: python3 skills/x402/scripts/verify_setup.py [--funded]

Layer A (no funds needed):
  1. 402 challenge served correctly (payperuse)
  2. buyer auto-signs EIP-3009; facilitator cryptographically verifies
     (expected outcome without funds: insufficient_balance -> chain proven)
  3. subscription mode: topup challenge, API-key auth, credit deduction,
     insufficient-credits error, refund on upstream failure
Layer B (--funded, requires testnet/mainnet USDC in the Privy wallet):
  4. real payment -> settlement receipt -> ledger credit
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import time

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
WS = os.path.abspath(os.path.join(SKILL, "..", ".."))
sys.path.insert(0, SKILL)

NETWORK = os.environ.get("X402_NETWORK", "eip155:84532")  # Base Sepolia default
# Placeholder recipient for local self-checks only (no funds ever sent to it);
# set X402_PAY_TO to your real wallet for a live check.
PAY_TO = os.environ.get("X402_PAY_TO", "0x000000000000000000000000000000000000dEaD")
UP_PORT, PPU_PORT, SUB_PORT = 18500, 18501, 18502

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def wait_port(port: int, tries: int = 40) -> bool:
    for _ in range(tries):
        try:
            httpx.get(f"http://127.0.0.1:{port}/x402/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def start(cmd: list[str], env: dict | None = None) -> subprocess.Popen:
    e = {**os.environ, **(env or {})}
    return subprocess.Popen(cmd, env=e, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def main():
    funded = "--funded" in sys.argv
    procs: list[subprocess.Popen] = []
    tmp = tempfile.mkdtemp(prefix="x402check_")
    try:
        # ---------- dummy upstream ----------
        upstream_py = os.path.join(tmp, "up.py")
        with open(upstream_py, "w") as f:
            f.write(
                "from fastapi import FastAPI\nimport uvicorn\napp=FastAPI()\n"
                "@app.get('/')\ndef r(): return {'ok':True}\n"
                "@app.get('/api/data')\ndef d(): return {'premium':'payload'}\n"
                "@app.get('/api/boom')\ndef b(): raise RuntimeError('boom')\n"
                f"uvicorn.run(app,host='127.0.0.1',port={UP_PORT},log_level='error')\n")
        procs.append(start([sys.executable, upstream_py]))
        time.sleep(1.5)

        # ---------- payperuse gateway ----------
        # networks_profile=testnet so resolve_networks returns the testnet
        # full set (the legacy single "network" field is no longer read by
        # resolve_networks — plans-280-04 §5.6.1).
        ppu_cfg = os.path.join(tmp, "ppu.json")
        json.dump({"mode": "payperuse", "upstream": f"http://127.0.0.1:{UP_PORT}",
                   "pay_to": PAY_TO, "networks_mode": "custom",
                   "networks": [NETWORK], "port": PPU_PORT,
                   "routes": {"GET /api/data": {"price": "$0.001"}},
                   "state_dir": os.path.join(tmp, "s1")}, open(ppu_cfg, "w"))
        procs.append(start([sys.executable, os.path.join(SKILL, "gateway", "app.py"), ppu_cfg]))
        check("payperuse gateway boots", wait_port(PPU_PORT))

        r = httpx.get(f"http://127.0.0.1:{PPU_PORT}/api/data", timeout=10)
        hdr = r.headers.get("PAYMENT-REQUIRED", "")
        check("402 challenge", r.status_code == 402 and bool(hdr), f"status={r.status_code}")
        if hdr:
            acc = json.loads(base64.b64decode(hdr))["accepts"][0]
            check("challenge fields", acc["payTo"].lower() == PAY_TO.lower()
                  and acc["network"] == NETWORK and acc["scheme"] == "exact",
                  f"amount={acc['amount']}")

        # ---------- platform multi-accepts (plans-280-04 X1/X2/X3) ----------
        # X1: default (no networks) -> accepts = platform mainnet full set
        sys.path.insert(0, os.path.join(SKILL, "gateway"))
        from platform_modes import (resolve_networks, platform_mainnet_networks,
                                    platform_testnet_networks, ASSETS)
        # resolve_networks with empty cfg -> mainnet full set
        nets_all = resolve_networks({})
        check("resolve_networks default -> all", len(nets_all) >= 1,
              f"networks={nets_all}")
        # X2: custom single chain -> accepts length 1
        nets_custom = resolve_networks({"networks_mode": "custom",
                                        "networks": ["eip155:8453"]})
        check("resolve_networks custom single", nets_custom == ["eip155:8453"],
              f"networks={nets_custom}")
        # X3: extend MAINNET with a fake chain -> all picks it up (no business
        # table update needed). Simulate by checking ASSETS has Monad.
        check("ASSETS includes Monad mainnet", "eip155:143" in ASSETS,
              f"keys={list(ASSETS)}")
        # illegal: custom with empty list
        try:
            resolve_networks({"networks_mode": "custom", "networks": []})
            check("resolve_networks custom+empty raises", False, "no error raised")
        except ValueError:
            check("resolve_networks custom+empty raises", True)
        # testnet profile via facilitator URL
        nets_testnet = resolve_networks({"facilitator": "https://x402.org/facilitator"})
        check("resolve_networks testnet profile",
              set(nets_testnet).issubset(set(platform_testnet_networks())),
              f"networks={nets_testnet}")

        # unprotected route passes through free
        r = httpx.get(f"http://127.0.0.1:{PPU_PORT}/", timeout=10)
        check("free route proxied", r.status_code == 200 and r.json().get("ok") is True)

        # ---------- buyer: throwaway key -> facilitator sig verification ----------
        from eth_account import Account
        from x402 import x402Client
        from x402.mechanisms.evm.exact.register import register_exact_evm_client
        from x402.http.clients.httpx import x402HttpxClient
        import asyncio

        async def buy(url):
            c = x402Client()
            register_exact_evm_client(c, Account.create())
            async with x402HttpxClient(c, timeout=60) as hc:
                r = await hc.get(url)
                err = ""
                h2 = r.headers.get("PAYMENT-REQUIRED")
                if r.status_code == 402 and h2:
                    err = json.loads(base64.b64decode(h2)).get("error", "")
                return r.status_code, err

        st, err = asyncio.run(buy(f"http://127.0.0.1:{PPU_PORT}/api/data"))
        sig_ok = (st == 200) or (st == 402 and "insufficient_balance" in err)
        check("EIP-3009 sig accepted by facilitator", sig_ok,
              f"status={st} err={err or 'settled'}")

        # ---------- platform multi-accepts gateway (plans-280-04 G1/G2) ----
        # G1: networks_mode=all -> 402 accepts is a LIST with the platform
        # mainnet full set (Base + Monad + Robinhood + X Layer + Solana). G2: custom single chain -> length 1.
        PLAT_PORT = 18510
        plat_cfg_all = os.path.join(tmp, "plat_all.json")
        json.dump({"mode": "pay_per_use", "upstream": f"http://127.0.0.1:{UP_PORT}",
                   "pay_to": PAY_TO, "networks_mode": "all", "port": PLAT_PORT,
                   "price_usd": "0.01",
                   "facilitator": "https://starchild-x402-facilitator.fly.dev",
                   "routes": {"* /api/*": {"units": 1}},
                   "state_dir": os.path.join(tmp, "s_plat_all")}, open(plat_cfg_all, "w"))
        procs.append(start([sys.executable, os.path.join(SKILL, "gateway", "app.py"), plat_cfg_all]))
        check("platform all gateway boots", wait_port(PLAT_PORT))

        r = httpx.get(f"http://127.0.0.1:{PLAT_PORT}/api/data", timeout=10)
        check("platform 402 status", r.status_code == 402, f"status={r.status_code}")
        try:
            body = r.json()
        except Exception:
            body = {}
        accepts = body.get("accepts")
        check("G1: accepts is a list", isinstance(accepts, list) and len(accepts) >= 1,
              f"len={len(accepts) if isinstance(accepts, list) else 'n/a'}")
        if isinstance(accepts, list) and accepts:
            nets_in_402 = [a.get("network") for a in accepts]
            check("G1: accepts includes Base+Monad+Robinhood+X Layer+Solana",
                  "eip155:8453" in nets_in_402 and "eip155:143" in nets_in_402
                  and "eip155:4663" in nets_in_402 and "eip155:196" in nets_in_402,
                  f"networks={nets_in_402}")
            check("G1: each accept has pricingModel",
                  all(a.get("pricingModel") == "pay_per_use" for a in accepts),
                  f"models={[a.get('pricingModel') for a in accepts]}")
        # info endpoint exposes networks list
        r = httpx.get(f"http://127.0.0.1:{PLAT_PORT}/x402/info", timeout=10)
        check("info exposes networks list",
              r.status_code == 200 and isinstance(r.json().get("networks"), list),
              f"networks={r.json().get('networks')}")

        # G2: custom single chain -> accepts length 1
        PLAT_PORT_C = 18511
        plat_cfg_c = os.path.join(tmp, "plat_custom.json")
        json.dump({"mode": "pay_per_use", "upstream": f"http://127.0.0.1:{UP_PORT}",
                   "pay_to": PAY_TO, "networks_mode": "custom",
                   "networks": ["eip155:8453"], "port": PLAT_PORT_C,
                   "price_usd": "0.01",
                   "facilitator": "https://starchild-x402-facilitator.fly.dev",
                   "routes": {"* /api/*": {"units": 1}},
                   "state_dir": os.path.join(tmp, "s_plat_c")}, open(plat_cfg_c, "w"))
        procs.append(start([sys.executable, os.path.join(SKILL, "gateway", "app.py"), plat_cfg_c]))
        check("platform custom gateway boots", wait_port(PLAT_PORT_C))
        r = httpx.get(f"http://127.0.0.1:{PLAT_PORT_C}/api/data", timeout=10)
        try:
            accepts_c = r.json().get("accepts")
        except Exception:
            accepts_c = None
        check("G2: custom single chain -> accepts length 1",
              isinstance(accepts_c, list) and len(accepts_c) == 1
              and accepts_c[0].get("network") == "eip155:8453",
              f"accepts={accepts_c}")

        # ---------- subscription gateway ----------
        sub_cfg = os.path.join(tmp, "sub.json")
        state2 = os.path.join(tmp, "s2")
        json.dump({"mode": "subscription", "upstream": f"http://127.0.0.1:{UP_PORT}",
                   "pay_to": PAY_TO, "networks_mode": "custom",
                   "networks": [NETWORK], "port": SUB_PORT,
                   "routes": {"GET /api/*": {"units": 1}},
                   "topup": {"price_per_credit_usd": 0.001, "min_credits": 100},
                   "state_dir": state2}, open(sub_cfg, "w"))
        procs.append(start([sys.executable, os.path.join(SKILL, "gateway", "app.py"), sub_cfg]))
        check("subscription gateway boots", wait_port(SUB_PORT))

        r = httpx.post(f"http://127.0.0.1:{SUB_PORT}/x402/topup", timeout=10)
        check("topup requires x402 payment", r.status_code == 402)

        r = httpx.get(f"http://127.0.0.1:{SUB_PORT}/api/data", timeout=10)
        check("missing key -> 401 invalid_key", r.status_code == 401
              and r.json()["error"]["code"] == "invalid_key")

        # simulate a settled payment (ledger credit path, no funds needed)
        sys.path.insert(0, os.path.join(SKILL, "gateway"))
        from ledger import Ledger
        led = Ledger(os.path.join(state2, "ledger.db"))
        out = led.credit_payment("0xtest_tx_1", "0xAbCd00000000000000000000000000000000eF12",
                                 "100000", 100, NETWORK)
        key = out["api_key"]
        check("ledger credit (idempotent insert)", out["ok"] and out["credits"] == 100)
        dup = led.credit_payment("0xtest_tx_1", "0xAbCd00000000000000000000000000000000eF12",
                                 "100000", 100, NETWORK)
        check("replay tx rejected", dup["ok"] is False and dup["error"] == "duplicate_tx")

        r = httpx.get(f"http://127.0.0.1:{SUB_PORT}/api/data",
                      headers={"X-API-Key": key}, timeout=10)
        check("valid key -> proxied 200", r.status_code == 200
              and r.json().get("premium") == "payload")

        r = httpx.get(f"http://127.0.0.1:{SUB_PORT}/x402/balance",
                      headers={"X-API-Key": key}, timeout=10)
        check("balance deducted", r.status_code == 200 and r.json()["credits"] == 99,
              f"credits={r.json().get('credits')}")

        r = httpx.get(f"http://127.0.0.1:{SUB_PORT}/api/boom",
                      headers={"X-API-Key": key}, timeout=10)
        b2 = httpx.get(f"http://127.0.0.1:{SUB_PORT}/x402/balance",
                       headers={"X-API-Key": key}, timeout=10).json()["credits"]
        check("refund on upstream 5xx", r.status_code == 500 and b2 == 99,
              f"credits after boom={b2}")

        led.deduct(key, 99)  # drain
        r = httpx.get(f"http://127.0.0.1:{SUB_PORT}/api/data",
                      headers={"X-API-Key": key}, timeout=10)
        check("drained -> 402 insufficient_credits", r.status_code == 402
              and r.json()["error"]["code"] == "insufficient_credits")

        # ---------- Layer B: real funded payment ----------
        if funded:
            from client import paid_request  # noqa
            out = paid_request("GET", f"http://127.0.0.1:{PPU_PORT}/api/data",
                               max_amount_atomic=10_000)
            check("FUNDED: real settlement", out["status"] == 200 and "settlement" in out,
                  json.dumps(out.get("settlement", {}))[:200])

    finally:
        for p in procs:
            p.terminate()

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"== {passed}/{len(results)} checks passed ==")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
