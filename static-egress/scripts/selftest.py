#!/usr/bin/env python3
"""Prove the egress path without a database.

Everything the RDS recipe depends on except the database engine itself can be
tested against public endpoints:

  1. the relay reaches a real TCP target, and the target sees the allowlisted IP
  2. TLS with hostname verification works through the relay while the socket goes
     to loopback — the exact `host` + `hostaddr` semantics libpq needs

What it cannot prove: that *your* firewall allowlists the right address, or that
your endpoint is reachable at all. Only a real target can. Run `verify.py`
against the real endpoint for that.

The allocation is saved and restored, so running this does not disturb a real
one (the egress IPs are stable either way).

    python3 selftest.py
"""
from __future__ import annotations

import argparse
import os
import socket
import ssl
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, fail  # noqa: E402
from tunnel import open_via_relay  # noqa: E402  (reuse the SOCKS5 client)

HTTP_HOST = "ifconfig.co"
TLS_HOST = "example.com"


class _Creds:
    """What open_via_relay() needs; built from the control plane's response."""

    def __init__(self, payload: dict):
        host, _, port = payload["relay"].rpartition(":")
        self.username = payload["username"]
        self.token = payload["token"]
        self.relay_host, self.relay_port = host, int(port)


def _read_all(sock: socket.socket) -> bytes:
    data = b""
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            return data
        data += chunk


def _restore(prior: dict | None) -> None:
    """Put the user's own allocation back exactly as it was."""
    if prior is None:
        call("DELETE", "/v1/allocations/current")
        return
    body = {"targets": [":".join(str(x) for x in t) for t in prior["targets"]]}
    if prior.get("region"):
        body["region"] = prior["region"]
    call("POST", "/v1/allocations", body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove the egress path without a database.")
    parser.add_argument("--http-host", default=HTTP_HOST)
    parser.add_argument("--tls-host", default=TLS_HOST)
    args = parser.parse_args()

    try:
        try:
            prior = call("GET", "/v1/allocations/current")
        except ServiceError as exc:
            if exc.code != "not_found":
                raise
            prior = None

        payload = call("POST", "/v1/allocations", {
            "targets": [f"{args.http_host}:80", f"{args.tls_host}:443"],
        })
        allowlist = payload["allowlist"]
        creds = _Creds(payload)
        results = []

        # 1. TCP through the relay, and the far end's view of our source address.
        try:
            sock = open_via_relay(creds, args.http_host, 80)
            try:
                sock.sendall(f"GET /ip HTTP/1.1\r\nHost: {args.http_host}\r\n"
                             f"User-Agent: sc-static-egress-selftest/1\r\n"
                             f"Connection: close\r\n\r\n".encode())
                raw = _read_all(sock)
            finally:
                sock.close()
            head, _, body = raw.decode(errors="replace").partition("\r\n\r\n")
            seen = body.strip().splitlines()[-1].strip() if body.strip() else ""
            # A mismatch is the RDS-breaking condition: the far end would
            # see a different address than the one you allowlisted.
            ok = head.startswith("HTTP/1.1 200") and seen in allowlist
            results.append(("tcp + source address", ok,
                            f"{head.splitlines()[0] if head else 'no response'}; "
                            f"far end sees {seen or '(nothing)'}; "
                            f"allowlisted {', '.join(allowlist)}; "
                            f"{'match' if seen in allowlist else 'MISMATCH'}"))
        except Exception as exc:  # noqa: BLE001
            results.append(("tcp + source address", False, f"{type(exc).__name__}: {exc}"))

        # 2. TLS with hostname verification over a loopback socket — what
        #    libpq does with host=<real name> hostaddr=127.0.0.1.
        try:
            context = ssl.create_default_context()
            raw_sock = open_via_relay(creds, args.tls_host, 443)
            try:
                tls = context.wrap_socket(raw_sock, server_hostname=args.tls_host)
                try:
                    subject = dict(x[0] for x in tls.getpeercert().get("subject", ()))
                    results.append(("tls verify-full via relay", True,
                                    f"{tls.version()} to {args.tls_host}, "
                                    f"cert CN={subject.get('commonName', '?')}"))
                finally:
                    tls.close()
            finally:
                raw_sock.close()
        except Exception as exc:  # noqa: BLE001
            results.append(("tls verify-full via relay", False, f"{type(exc).__name__}: {exc}"))

        _restore(prior)

    except ServiceError as exc:
        return fail(exc.message, exc.code)

    width = max(len(name) for name, _, _ in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:{width}}  {detail}")
    print()
    print("This proves the mechanism. It does NOT prove your firewall allows the "
          "address above, nor that your endpoint is reachable — run verify.py "
          "against the real endpoint for that.")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())