#!/usr/bin/env python3
"""Local TCP -> SOCKS5 forwarder, so any client can use the static egress.

Database drivers do not speak SOCKS5, so the standard pattern is: run this in
the container, then point the application at ``127.0.0.1:<port>``. Keep TLS
end-to-end by telling libpq both names:

    host=<real db hostname>   hostaddr=127.0.0.1   port=5432   sslmode=verify-full

Usage:
    python3 tunnel.py --target db-prod.xxx.rds.amazonaws.com:5432
                      [--listen 127.0.0.1:5432] [--region sjc]

Credentials come from the control plane and are refreshed automatically when
the relay rejects a stale one. Nothing is written to disk.
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ServiceError, call, fail  # noqa: E402

BUFFER = 65536


class Credentials:
    """Rotating egress credential, refreshed on demand."""

    def __init__(self, target: str, region: str | None):
        self.target = target
        self.region = region
        self.lock = threading.Lock()
        self.username = ""
        self.token = ""
        self.relay_host = ""
        self.relay_port = 0
        self.refresh()

    def refresh(self) -> None:
        """Re-mint the token for the same allocation (idempotent: same egress IPs)."""
        body: dict = {"targets": [self.target]}
        if self.region:
            body["region"] = self.region
        payload = call("POST", "/v1/allocations", body)
        with self.lock:
            self.username = payload["username"]
            self.token = payload["token"]
            host, _, port = payload["relay"].rpartition(":")
            if not host or not port:
                raise ServiceError(502, "bad_relay", f"unusable relay address {payload['relay']!r}")
            self.relay_host, self.relay_port = host, int(port)


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    buf = b""
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise ConnectionResetError("relay closed the connection")
        buf += chunk
    return buf


def open_via_relay(creds: Credentials, target_host: str, target_port: int,
                   timeout: float = 15.0) -> socket.socket:
    sock = socket.create_connection((creds.relay_host, creds.relay_port), timeout=timeout)
    try:
        sock.sendall(bytes([0x05, 0x01, 0x02]))          # offer username/password only
        method = _recv_exact(sock, 2)
        if method[1] != 0x02:
            raise PermissionError("relay did not accept username/password auth")
        user, pwd = creds.username.encode(), creds.token.encode()
        sock.sendall(bytes([0x01, len(user)]) + user + bytes([len(pwd)]) + pwd)
        if _recv_exact(sock, 2)[1] != 0x00:
            raise PermissionError("relay rejected the credential")
        host = target_host.encode()
        sock.sendall(bytes([0x05, 0x01, 0x00, 0x03, len(host)]) + host
                     + target_port.to_bytes(2, "big"))
        reply = _recv_exact(sock, 4)
        if reply[1] != 0x00:
            raise PermissionError(f"relay refused CONNECT to {target_host}:{target_port} "
                                  f"(code {reply[1]})")
        if reply[3] == 0x01:
            _recv_exact(sock, 6)
        elif reply[3] == 0x04:
            _recv_exact(sock, 18)
        elif reply[3] == 0x03:
            _recv_exact(sock, _recv_exact(sock, 1)[0] + 2)
        return sock
    except Exception:
        sock.close()
        raise


def _pump(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            chunk = src.recv(BUFFER)
            if not chunk:
                break
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        for sock in (src, dst):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def serve(creds: Credentials, listen_host: str, listen_port: int,
          target_host: str, target_port: int) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((listen_host, listen_port))
    except OSError as exc:
        raise ServiceError(
            502, "bind_failed",
            f"cannot listen on {listen_host}:{listen_port} ({exc.strerror}). "
            f"Pick another --listen port, or stop whatever already holds it.",
        ) from exc
    server.listen(64)
    print(f"tunnel: 127.0.0.1:{listen_port} -> {target_host}:{target_port} "
          f"via {creds.relay_host}:{creds.relay_port}", flush=True)
    print("tunnel: point the client at it with BOTH names — the real hostname for "
          "SNI/certificate checks, the loopback address for the socket:", flush=True)
    print(f"tunnel:   host={target_host}  hostaddr=127.0.0.1  port={listen_port}", flush=True)
    print(f"tunnel:   psql \"host={target_host} hostaddr=127.0.0.1 port={listen_port} "
          f"dbname=<db> user=<user> sslmode=verify-full\"", flush=True)

    def handle(client: socket.socket) -> None:
        upstream = None
        try:
            try:
                upstream = open_via_relay(creds, target_host, target_port)
            except PermissionError:
                creds.refresh()          # token likely expired; rotate once and retry
                upstream = open_via_relay(creds, target_host, target_port)
            threading.Thread(target=_pump, args=(client, upstream), daemon=True).start()
            _pump(upstream, client)
        except Exception as exc:  # noqa: BLE001 - one bad connection must not stop the tunnel
            print(f"tunnel: connection failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr, flush=True)
            try:
                client.close()
            except OSError:
                pass

    while True:
        client, _ = server.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward a local TCP port through the static egress.")
    parser.add_argument("--target", required=True, help="real target, host:port")
    parser.add_argument("--listen", default="127.0.0.1:5432", help="local host:port to listen on")
    parser.add_argument("--region", default=None, help="relay region")
    args = parser.parse_args()

    target_host, _, target_port = args.target.rpartition(":")
    listen_host, _, listen_port = args.listen.rpartition(":")
    if not target_host or not target_port or not listen_host or not listen_port:
        return fail("--target and --listen must both be host:port", "bad_args")

    try:
        creds = Credentials(args.target, args.region)
        serve(creds, listen_host, int(listen_port), target_host, int(target_port))
    except ServiceError as exc:
        return fail(exc.message, exc.code)
    return 0


if __name__ == "__main__":
    sys.exit(main())