"""SQLite credits ledger for x402 gateway (subscription / metered modes).

Accounts are keyed by payer wallet address. Each payer gets a stable API key.
Idempotency: settlement tx hash is UNIQUE — replayed credits are rejected.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import time

_LOCK = threading.Lock()


class Ledger:
    def __init__(self, db_path: str, key_salt: str | None = None):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self._salt = key_salt or self._load_or_create_salt(db_path + ".salt")
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts(
                    payer TEXT PRIMARY KEY,
                    api_key TEXT UNIQUE NOT NULL,
                    credits INTEGER NOT NULL DEFAULT 0,
                    pass_expires_at REAL NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS payments(
                    tx_hash TEXT PRIMARY KEY,
                    payer TEXT NOT NULL,
                    amount_atomic TEXT NOT NULL,
                    credits INTEGER NOT NULL,
                    network TEXT,
                    ts REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS usage(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT NOT NULL,
                    route TEXT,
                    units INTEGER NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_usage_key ON usage(api_key, ts);
                """
            )
            # migration for DBs created before timepass support
            try:
                c.execute("ALTER TABLE accounts ADD COLUMN pass_expires_at REAL NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass

    @staticmethod
    def _load_or_create_salt(path: str) -> str:
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
        salt = secrets.token_hex(16)
        with open(path, "w") as f:
            f.write(salt)
        os.chmod(path, 0o600)
        return salt

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _derive_key(self, payer: str) -> str:
        digest = hmac.new(self._salt.encode(), payer.lower().encode(), hashlib.sha256).hexdigest()
        return "x4k_" + digest[:40]

    # ------------------------------------------------------------------
    def get_or_create_account(self, payer: str) -> dict:
        payer = payer.lower()
        with _LOCK, self._conn() as c:
            row = c.execute("SELECT * FROM accounts WHERE payer=?", (payer,)).fetchone()
            if row:
                return dict(row)
            key = self._derive_key(payer)
            c.execute(
                "INSERT INTO accounts(payer, api_key, credits, created_at) VALUES(?,?,0,?)",
                (payer, key, time.time()),
            )
            return {"payer": payer, "api_key": key, "credits": 0, "revoked": 0}

    def credit_payment(self, tx_hash: str, payer: str, amount_atomic: str,
                       credits: int, network: str = "", pass_days: float = 0) -> dict:
        """Idempotent credit: same tx_hash never credits twice.

        credits > 0  -> add usage credits (subscription/metered)
        pass_days > 0 -> extend time pass from max(now, current expiry)
        """
        payer = payer.lower()
        acct = self.get_or_create_account(payer)
        with _LOCK, self._conn() as c:
            try:
                c.execute(
                    "INSERT INTO payments(tx_hash, payer, amount_atomic, credits, network, ts)"
                    " VALUES(?,?,?,?,?,?)",
                    (tx_hash, payer, amount_atomic, credits, network, time.time()),
                )
            except sqlite3.IntegrityError:
                return {"ok": False, "error": "duplicate_tx", "api_key": acct["api_key"]}
            if credits:
                c.execute("UPDATE accounts SET credits = credits + ? WHERE payer=?", (credits, payer))
            expires = None
            if pass_days > 0:
                row = c.execute("SELECT pass_expires_at FROM accounts WHERE payer=?", (payer,)).fetchone()
                base = max(time.time(), row["pass_expires_at"] or 0)
                expires = base + pass_days * 86400
                c.execute("UPDATE accounts SET pass_expires_at=? WHERE payer=?", (expires, payer))
            row = c.execute("SELECT credits, pass_expires_at FROM accounts WHERE payer=?", (payer,)).fetchone()
        out = {"ok": True, "api_key": acct["api_key"], "credits": row["credits"],
               "credited": credits, "tx_hash": tx_hash}
        if pass_days > 0:
            out["pass_expires_at"] = row["pass_expires_at"]
        return out

    def check_pass(self, api_key: str) -> dict:
        """Timepass validity check (no deduction)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT pass_expires_at FROM accounts WHERE api_key=? AND revoked=0", (api_key,)
            ).fetchone()
        if row is None:
            return {"ok": False, "error": "invalid_key"}
        if (row["pass_expires_at"] or 0) < time.time():
            return {"ok": False, "error": "pass_expired",
                    "pass_expires_at": row["pass_expires_at"]}
        return {"ok": True, "pass_expires_at": row["pass_expires_at"]}

    def lookup_key(self, api_key: str) -> dict | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM accounts WHERE api_key=? AND revoked=0", (api_key,)
            ).fetchone()
            return dict(row) if row else None

    def deduct(self, api_key: str, units: int, route: str = "") -> dict:
        """Atomically deduct usage units. Fails if balance insufficient."""
        with _LOCK, self._conn() as c:
            row = c.execute(
                "SELECT credits FROM accounts WHERE api_key=? AND revoked=0", (api_key,)
            ).fetchone()
            if row is None:
                return {"ok": False, "error": "invalid_key"}
            if row["credits"] < units:
                return {"ok": False, "error": "insufficient_credits", "credits": row["credits"]}
            c.execute("UPDATE accounts SET credits = credits - ? WHERE api_key=?", (units, api_key))
            c.execute("INSERT INTO usage(api_key, route, units, ts) VALUES(?,?,?,?)",
                      (api_key, route, units, time.time()))
            left = c.execute("SELECT credits FROM accounts WHERE api_key=?", (api_key,)).fetchone()
        return {"ok": True, "credits": left["credits"], "deducted": units}

    def refund(self, api_key: str, units: int, route: str = "") -> None:
        """Refund units (e.g. upstream 5xx after deduction)."""
        with _LOCK, self._conn() as c:
            c.execute("UPDATE accounts SET credits = credits + ? WHERE api_key=?", (units, api_key))
            c.execute("INSERT INTO usage(api_key, route, units, ts) VALUES(?,?,?,?)",
                      (api_key, route, -units, time.time()))

    def revoke(self, api_key: str) -> bool:
        with _LOCK, self._conn() as c:
            cur = c.execute("UPDATE accounts SET revoked=1 WHERE api_key=?", (api_key,))
            return cur.rowcount > 0

    def stats(self) -> dict:
        with self._conn() as c:
            accounts = c.execute("SELECT COUNT(*) n, COALESCE(SUM(credits),0) s FROM accounts").fetchone()
            pays = c.execute("SELECT COUNT(*) n FROM payments").fetchone()
            usage = c.execute("SELECT COALESCE(SUM(units),0) s FROM usage WHERE units>0").fetchone()
        return {"accounts": accounts["n"], "outstanding_credits": accounts["s"],
                "payments": pays["n"], "units_consumed": usage["s"]}
