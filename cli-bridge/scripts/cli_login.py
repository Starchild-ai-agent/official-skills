#!/usr/bin/env python3
"""cli-login --label "<name>" [--ttl-days N]

Mint a fresh AKM key with `scope=chat:bridge:cli` on the local clawd, then
register it with sc-chatroom in exchange for a short opaque code
(``sc_<8>``). The bundle handed to the user contains only the short code
— never the AKM secret, never the Fly machine id.

Bundle layout (matches tools/starchild/internal/identity/identity.go):

    {
      "d":   <sc-chatroom public URL>,
      "c":   ""                          ← deprecated; resolved server-side
      "k":   "sc_xxxxxxxx",              ← short code, server-resolves to AKM
      "s":   "chat:bridge:cli",
      "exp": <unix expiry>,
      "l":   <user-supplied label>
    }

Revoking the bundle is now: ``cli-revoke <sc_…>`` (kills the short code,
AKM stays alive for direct use); or ``cli-revoke --akm <prefix>`` to also
nuke the underlying AKM on clawd.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys

import _common as C


DEFAULT_TTL_DAYS = 90
MAX_TTL_DAYS = 365
DEFAULT_RATE_LIMIT = {"per_minute": 30}


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cli-login",
        description="Mint a CLI bundle for the starchild binary.",
    )
    p.add_argument(
        "--label", required=True,
        help='Human reminder for this key (e.g. "my laptop", "codex-vm").',
    )
    p.add_argument(
        "--ttl-days", type=int, default=DEFAULT_TTL_DAYS,
        help=f"Days until the AKM key expires (default {DEFAULT_TTL_DAYS}, "
             f"max {MAX_TTL_DAYS}).",
    )
    return p.parse_args(argv[1:])


def _encode_bundle(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return "starchild_" + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def main(argv: list[str]) -> int:
    args = _parse(argv)
    label = args.label.strip()
    if not label:
        C.die("--label cannot be empty")
    ttl_days = args.ttl_days
    if ttl_days < 1:
        C.die("--ttl-days must be >= 1")
    if ttl_days > MAX_TTL_DAYS:
        C.die(f"--ttl-days exceeds max ({MAX_TTL_DAYS}); use a shorter TTL")
    C.require_env()
    ttl_seconds = ttl_days * 86400

    # 1. Mint the AKM key on local clawd
    akm_body = {
        "scope": C.CLI_BRIDGE_SCOPE,
        "ttl_seconds": ttl_seconds,
        "label": label,
        "rate_limit": DEFAULT_RATE_LIMIT,
    }
    r = C.clawd_call("POST", "/api/keys", json=akm_body)
    if r.status_code != 201:
        C.die(f"clawd POST /api/keys returned {r.status_code}: {r.text}")
    akm_resp = r.json()
    akm_secret = akm_resp["secret"]
    akm_prefix = akm_resp["key"]["prefix"]
    # clawd stores expires_at as REAL (services/akm.py); the Go CLI's
    # Bundle.ExpiresAt is int64 and rejects floats during JSON decode.
    expires_at = int(akm_resp["key"]["expires_at"])

    # 2. Register the AKM + container_id with sc-chatroom in exchange for
    # a short sc_… code. After this, the AKM secret never leaves the
    # Fly internal network in plaintext — bundle carries only the code.
    register_body = {
        "akm_key": akm_secret,
        "container_id": C.CONTAINER_ID,
        "label": label,
        "ttl_seconds": ttl_seconds,
    }
    rr = C.chatroom_call("POST", "/cli-keys", json=register_body)
    if rr.status_code != 201:
        # Roll back the AKM — don't leave a live secret nobody references.
        try:
            C.clawd_call("DELETE", f"/api/keys/{akm_prefix}")
        except Exception:
            pass
        C.die(
            f"sc-chatroom POST /cli-keys returned {rr.status_code}: {rr.text}"
            " (AKM rolled back)"
        )
    code = rr.json()["code"]

    # 3. Pack the bundle. No secret inside — only the short code, the
    # gateway URL, expiry, and label.
    bundle = _encode_bundle({
        "d": C.CHATROOM_PUBLIC_URL,
        "c": "",                      # routing target now resolved by the code
        "k": code,                    # bearer the CLI will send
        "s": C.CLI_BRIDGE_SCOPE,
        "exp": expires_at,
        "l": label,
    })

    C.info(f"  ✓ minted CLI key (akm_prefix {akm_prefix}, code {code}, "
           f"expires {expires_at})")
    C.info("")
    C.info("First time on this device? Grab the starchild binary "
           "(auto-detects your OS):")
    C.info(f"  {C.CHATROOM_PUBLIC_URL.rstrip('/')}/starchild")
    C.info("")
    C.info("Then pair the CLI by pasting this into your terminal:")
    C.info("")
    C.info(f"  starchild login {bundle}")
    C.info("")
    C.info(
        "The bundle no longer contains your AKM secret — sc-chatroom resolves "
        f"the short code ({code}) on each call. Revoke immediately if it leaks:"
    )
    C.info(f"  python3 skills/cli-bridge/scripts/cli_revoke.py {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
