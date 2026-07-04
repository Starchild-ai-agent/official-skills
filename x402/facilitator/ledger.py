"""Settlement ledger for the self-hosted x402 facilitator.

Every verify/settle that passes through the facilitator is recorded here —
this is the platform-wide monitoring ledger (Q2: full transaction visibility).
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time

_LOCK = threading.Lock()


class FacilitatorLedger:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        with self._conn() as c:
            # migrate legacy schema (auth_nonce globally UNIQUE) -> composite key;
            # EIP-3009 nonces are only unique PER PAYER on-chain.
            row = c.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='settlements'"
            ).fetchone()
            legacy = bool(row and "auth_nonce TEXT UNIQUE" in (row["sql"] or ""))
            if legacy:
                c.execute("ALTER TABLE settlements RENAME TO settlements_legacy")
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS settlements(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auth_nonce TEXT NOT NULL,          -- EIP-3009 nonce (unique per payer only)
                    payer TEXT NOT NULL,
                    pay_to TEXT NOT NULL,
                    amount_atomic TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    network TEXT NOT NULL,
                    resource TEXT,
                    status TEXT NOT NULL,              -- pending|submitted|confirmed|failed
                    tx_hash TEXT,
                    error TEXT,
                    gas_used INTEGER,
                    created_at REAL NOT NULL,
                    confirmed_at REAL,
                    UNIQUE(payer, auth_nonce, asset, network)
                );
                CREATE INDEX IF NOT EXISTS idx_settle_payer ON settlements(payer, created_at);
                CREATE TABLE IF NOT EXISTS verifications(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payer TEXT, pay_to TEXT, amount_atomic TEXT,
                    network TEXT, valid INTEGER NOT NULL, reason TEXT,
                    ts REAL NOT NULL
                );
                """
            )
            if legacy:
                c.execute(
                    "INSERT OR IGNORE INTO settlements(auth_nonce,payer,pay_to,amount_atomic,"
                    "asset,network,resource,status,tx_hash,error,gas_used,created_at,confirmed_at)"
                    " SELECT auth_nonce,payer,pay_to,amount_atomic,asset,network,resource,"
                    "status,tx_hash,error,gas_used,created_at,confirmed_at FROM settlements_legacy")
                c.execute("DROP TABLE settlements_legacy")

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def record_verify(self, payer, pay_to, amount, network, valid, reason=""):
        with _LOCK, self._conn() as c:
            c.execute(
                "INSERT INTO verifications(payer,pay_to,amount_atomic,network,valid,reason,ts)"
                " VALUES(?,?,?,?,?,?,?)",
                (payer, pay_to, amount, network, 1 if valid else 0, reason, time.time()))

    def begin_settlement(self, auth_nonce, payer, pay_to, amount, asset, network, resource="") -> bool:
        """Idempotency on (payer, nonce, asset, network). False if already processed."""
        with _LOCK, self._conn() as c:
            try:
                c.execute(
                    "INSERT INTO settlements(auth_nonce,payer,pay_to,amount_atomic,asset,"
                    "network,resource,status,created_at) VALUES(?,?,?,?,?,?,?,'pending',?)",
                    (auth_nonce, payer.lower(), pay_to, amount, asset, network,
                     resource, time.time()))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_settlement(self, payer, auth_nonce, asset, network) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM settlements WHERE payer=? AND auth_nonce=? AND asset=? AND network=?",
                (payer.lower(), auth_nonce, asset, network)).fetchone()
            return dict(row) if row else None

    def update_settlement(self, payer, auth_nonce, asset, network, **fields):
        cols = ", ".join(f"{k}=?" for k in fields)
        with _LOCK, self._conn() as c:
            c.execute(
                f"UPDATE settlements SET {cols} WHERE payer=? AND auth_nonce=? AND asset=? AND network=?",
                (*fields.values(), payer.lower(), auth_nonce, asset, network))

    def payer_recent_count(self, payer: str, window_sec: int = 60) -> int:
        with self._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) n FROM settlements WHERE payer=? AND created_at>?",
                (payer.lower(), time.time() - window_sec)).fetchone()
            return row["n"]

    def stats(self) -> dict:
        with self._conn() as c:
            s = c.execute(
                "SELECT status, COUNT(*) n FROM settlements GROUP BY status").fetchall()
            v = c.execute(
                "SELECT valid, COUNT(*) n FROM verifications GROUP BY valid").fetchall()
            vol = c.execute(
                "SELECT COALESCE(SUM(CAST(amount_atomic AS INTEGER)),0) s FROM settlements"
                " WHERE status='confirmed'").fetchone()
            gas = c.execute(
                "SELECT COALESCE(SUM(gas_used),0) g FROM settlements WHERE gas_used IS NOT NULL"
            ).fetchone()
        return {
            "settlements": {r["status"]: r["n"] for r in s},
            "verifications": {("valid" if r["valid"] else "invalid"): r["n"] for r in v},
            "confirmed_volume_atomic": vol["s"],
            "total_gas_used": gas["g"],
        }
