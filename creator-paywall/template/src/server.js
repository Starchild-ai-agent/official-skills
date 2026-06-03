// server.js — minimal REST API for the paywall. Mount these routes in your own app,
// or run standalone for the demo. All money/identity logic lives in the imported modules.
import "dotenv/config";
import express from "express";
import cookieParser from "cookie-parser";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { randomUUID } from "crypto";

import { CREATOR_WALLET, CHAINS, SESSION_TTL_HOURS } from "../config.js";
import { publicPlans, findPlan, expectedAmountWei, periodSeconds, client } from "./chains.js";
import { buildLoginMessage, login, requireAuth, requireSubscription } from "./auth.js";
import { verifyTxHash, scanForPayment } from "./payments.js";
import {
  createIntent, getIntent, getLatestPendingIntent, markIntentPaid,
  paymentExists, recordPayment, extendSubscription, getSubscription, now,
} from "./db.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());
app.use(cookieParser());
app.use(express.static(join(__dirname, "..", "public")));

const cookieOpts = { httpOnly: true, sameSite: "lax", maxAge: SESSION_TTL_HOURS * 3600 * 1000 };

// ---- config / plans (public) -------------------------------------------------
app.get("/api/config", (req, res) => {
  res.json({ creatorWallet: CREATOR_WALLET, chains: CHAINS, plans: publicPlans() });
});

// ---- auth (SIWE) -------------------------------------------------------------
app.get("/api/nonce", (req, res) => {
  const { address, chainId, uri } = req.query;
  if (!address) return res.status(400).json({ error: "address required" });
  res.json({ message: buildLoginMessage({ address, chainId, uri }) });
});

app.post("/api/login", async (req, res) => {
  try {
    const { token, address } = await login(req.body);
    res.cookie("session", token, cookieOpts);
    res.json({ ok: true, address, token });
  } catch (e) {
    res.status(401).json({ error: e.message });
  }
});

app.post("/api/logout", (req, res) => {
  res.clearCookie("session");
  res.json({ ok: true });
});

// ---- current user + subscription status -------------------------------------
app.get("/api/me", requireAuth, (req, res) => {
  const sub = getSubscription(req.wallet);
  const active = sub && sub.expires_at > now();
  res.json({
    wallet: req.wallet,
    subscribed: !!active,
    expiresAt: active ? sub.expires_at : null,
  });
});

// ---- subscribe step 1: create intent (anchors the scan start block) ----------
app.post("/api/subscribe/intent", requireAuth, async (req, res) => {
  try {
    const { chainId, token, period } = req.body;
    const plan = findPlan(chainId, token);
    if (!plan) return res.status(400).json({ error: "no such plan" });
    if (!["monthly", "yearly"].includes(period))
      return res.status(400).json({ error: "period must be monthly|yearly" });

    const amount_wei = expectedAmountWei(plan, period);
    const from_block = Number(await client(Number(chainId)).getBlockNumber());
    const id = randomUUID();
    createIntent({
      id, wallet: req.wallet, chain_id: Number(chainId), token: String(token),
      period, amount_wei, from_block, created_at: now(),
    });
    res.json({
      intentId: id,
      payTo: CREATOR_WALLET,
      chainId: Number(chainId),
      token: String(token),
      symbol: plan.symbol,
      decimals: plan.decimals,
      amount: amount_wei, // base units to send (>=)
    });
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

// ---- subscribe step 2a: confirm via txHash (works for native + ERC20) --------
app.post("/api/subscribe/verify", requireAuth, async (req, res) => {
  try {
    const { intentId, txHash } = req.body;
    const intent = await loadOwnedIntent(intentId, req.wallet, res);
    if (!intent) return;
    if (!txHash || !/^0x[0-9a-fA-F]{64}$/.test(txHash))
      return res.status(400).json({ error: "valid txHash required" });
    if (paymentExists(txHash)) return res.status(409).json({ error: "tx already used" });

    const r = await verifyTxHash({
      chainId: intent.chain_id, token: intent.token,
      expectedWei: intent.amount_wei, wallet: req.wallet, txHash,
    });
    if (!r.ok) return res.status(400).json({ error: r.reason });
    return res.json(activate(intent, txHash, r.amount));
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ---- subscribe step 2b: "Check payment" button (ERC20 log scan) --------------
app.post("/api/subscribe/check", requireAuth, async (req, res) => {
  try {
    const intent = req.body.intentId
      ? await loadOwnedIntent(req.body.intentId, req.wallet, res)
      : getLatestPendingIntent(req.wallet);
    if (!intent) return res.json({ found: false, reason: "no pending payment" });

    const r = await scanForPayment({
      chainId: intent.chain_id, token: intent.token,
      expectedWei: intent.amount_wei, wallet: req.wallet, fromBlock: intent.from_block,
    });
    if (!r.found) return res.json({ found: false, reason: r.reason });
    if (paymentExists(r.txHash)) return res.json({ found: false, reason: "tx already used" });
    return res.json({ found: true, ...activate(intent, r.txHash, r.amount) });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ---- example protected resource ---------------------------------------------
app.get("/api/protected", requireAuth, requireSubscription, (req, res) => {
  res.json({ ok: true, secret: "🎉 premium content for " + req.wallet });
});

// ---- helpers ----------------------------------------------------------------
async function loadOwnedIntent(intentId, wallet, res) {
  if (!intentId) { res.status(400).json({ error: "intentId required" }); return null; }
  const intent = getIntent(intentId);
  if (!intent || intent.wallet !== wallet) { res.status(404).json({ error: "intent not found" }); return null; }
  return intent;
}

function activate(intent, txHash, amount) {
  recordPayment({
    tx_hash: txHash.toLowerCase(), wallet: intent.wallet, chain_id: intent.chain_id,
    token: intent.token, amount_wei: amount, period: intent.period, created_at: now(),
  });
  markIntentPaid(intent.id, txHash.toLowerCase());
  const expiresAt = extendSubscription(intent.wallet, periodSeconds(intent.period));
  return { ok: true, subscribed: true, expiresAt, txHash };
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Creator paywall running on http://localhost:${PORT}`));
