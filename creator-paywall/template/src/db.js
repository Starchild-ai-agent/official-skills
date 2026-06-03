// db.js — tiny SQLite store. Swap for Postgres/your ORM when integrating.
import Database from "better-sqlite3";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const db = new Database(join(__dirname, "..", "paywall.db"));
db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS nonces (
    address TEXT PRIMARY KEY,
    nonce   TEXT NOT NULL,
    expires_at INTEGER NOT NULL
  );

  -- A subscription = one row per (user wallet). expires_at drives access.
  CREATE TABLE IF NOT EXISTS subscriptions (
    wallet     TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
  );

  -- Pending payment intents. Anchors the on-chain scan to a start block.
  CREATE TABLE IF NOT EXISTS intents (
    id         TEXT PRIMARY KEY,
    wallet     TEXT NOT NULL,
    chain_id   INTEGER NOT NULL,
    token      TEXT NOT NULL,
    period     TEXT NOT NULL,           -- 'monthly' | 'yearly'
    amount_wei TEXT NOT NULL,           -- expected min amount, base units
    from_block INTEGER NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending', -- pending | paid
    tx_hash    TEXT,
    created_at INTEGER NOT NULL
  );

  -- Ledger of accepted payments (idempotency + creator accounting).
  CREATE TABLE IF NOT EXISTS payments (
    tx_hash    TEXT PRIMARY KEY,
    wallet     TEXT NOT NULL,
    chain_id   INTEGER NOT NULL,
    token      TEXT NOT NULL,
    amount_wei TEXT NOT NULL,
    period     TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );
`);

export const now = () => Math.floor(Date.now() / 1000);

// --- nonces ---
export function saveNonce(address, nonce, ttlSec = 600) {
  db.prepare(
    `INSERT INTO nonces(address,nonce,expires_at) VALUES(?,?,?)
     ON CONFLICT(address) DO UPDATE SET nonce=excluded.nonce, expires_at=excluded.expires_at`
  ).run(address.toLowerCase(), nonce, now() + ttlSec);
}
export function takeNonce(address) {
  const row = db.prepare(`SELECT nonce,expires_at FROM nonces WHERE address=?`).get(address.toLowerCase());
  db.prepare(`DELETE FROM nonces WHERE address=?`).run(address.toLowerCase());
  if (!row || row.expires_at < now()) return null;
  return row.nonce;
}

// --- subscriptions ---
export function getSubscription(wallet) {
  return db.prepare(`SELECT * FROM subscriptions WHERE wallet=?`).get(wallet.toLowerCase()) || null;
}
export function extendSubscription(wallet, addSeconds) {
  const w = wallet.toLowerCase();
  const cur = getSubscription(w);
  const base = cur && cur.expires_at > now() ? cur.expires_at : now();
  const expires = base + addSeconds;
  db.prepare(
    `INSERT INTO subscriptions(wallet,expires_at,updated_at) VALUES(?,?,?)
     ON CONFLICT(wallet) DO UPDATE SET expires_at=excluded.expires_at, updated_at=excluded.updated_at`
  ).run(w, expires, now());
  return expires;
}

// --- intents ---
export function createIntent(i) {
  db.prepare(
    `INSERT INTO intents(id,wallet,chain_id,token,period,amount_wei,from_block,status,created_at)
     VALUES(@id,@wallet,@chain_id,@token,@period,@amount_wei,@from_block,'pending',@created_at)`
  ).run(i);
}
export function getIntent(id) {
  return db.prepare(`SELECT * FROM intents WHERE id=?`).get(id) || null;
}
export function getLatestPendingIntent(wallet) {
  return db.prepare(
    `SELECT * FROM intents WHERE wallet=? AND status='pending' ORDER BY created_at DESC LIMIT 1`
  ).get(wallet.toLowerCase()) || null;
}
export function markIntentPaid(id, txHash) {
  db.prepare(`UPDATE intents SET status='paid', tx_hash=? WHERE id=?`).run(txHash, id);
}

// --- payments (idempotency) ---
export function paymentExists(txHash) {
  return !!db.prepare(`SELECT 1 FROM payments WHERE tx_hash=?`).get(txHash.toLowerCase());
}
export function recordPayment(p) {
  db.prepare(
    `INSERT OR IGNORE INTO payments(tx_hash,wallet,chain_id,token,amount_wei,period,created_at)
     VALUES(@tx_hash,@wallet,@chain_id,@token,@amount_wei,@period,@created_at)`
  ).run(p);
}

export default db;
