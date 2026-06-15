---
name: creator-paywall
description: |
  Drop-in crypto subscription paywall for creator products (not fiat/Stripe). EVM wallet login (SIWE) + on-chain
  payment verification. Users sign in with their wallet, pay a monthly/yearly subscription by
  transferring tokens (ETH/Base/BSC, any ERC20 incl. custom tokens) to the creator's Starchild
  agent wallet, and get gated access — verified on-chain with no payment processor or third-party
  account.

  Use when a creator wants to add "sign up → pay → use" monetization to something they built
  (e.g. "add a paywall", "let users pay to subscribe", "gate my app behind a crypto payment",
  "收款", "订阅付费", "wallet login + subscription"). Not for fiat/Stripe, not for pay-per-use metering.
author: starchild
version: 1.0.1
tags: [paywall, subscription, crypto, evm, siwe, wallet, payments, monetization, creator]
---

# 💸 Creator Paywall

A **minimal, drop-in** crypto subscription paywall. Two jobs only: **wallet auth** + **subscription
verification**. Built to be embedded into a creator's existing product, not to be a platform.

```
Connect wallet → sign SIWE message → session (wallet = identity)
      │
      ├─ pick plan (chain + token + monthly/yearly)
      ├─ transfer tokens to the creator's wallet
      └─ submit txHash → backend verifies on-chain → subscription active
```

**The core trick:** the payer's address must equal the logged-in wallet. That's how a plain
transfer is matched to a user with **zero memos or order IDs**. Match rule is `from == logged-in wallet`.

## When to use this

- Creator built something (app, dashboard, content, API) and wants paid access.
- They want **crypto** payments straight to their **Starchild agent wallet** — no Stripe, no signup.
- Subscription model only (monthly / yearly). **Not** pay-per-use metering, **not** fiat.

If the creator needs fiat/cards or automatic recurring charges, this is the wrong tool — tell them so.

## What it is

A small Node/Express + viem app. ~900 LOC, SQLite store (swappable). Chains: **Ethereum, Base, BSC**.
Tokens: native coin or any ERC20 (including the creator's own custom token).

```
template/
  config.js          ← the ONLY file most creators edit (chains / tokens / prices / wallet)
  src/auth.js        ← SIWE login + requireAuth / requireSubscription middleware
  src/payments.js    ← on-chain verification (txHash receipt + bounded getLogs scan)
  src/chains.js      ← viem clients + plan/price helpers
  src/db.js          ← SQLite (replace with your DB when integrating)
  src/server.js      ← REST API wiring everything together
  public/index.html  ← demo frontend: 3 views (landing / paywall / member), token-based auth
  README.md          ← integration docs for the creator
  .env.example
```

## Quick start (scaffold a new instance)

**Step 1 — get the creator's receiving wallet.** Default = their Starchild agent EVM wallet.
Call the `wallet_info` tool and use the `ethereum` address.

**Step 2 — scaffold.** Run the init script (copies template, writes `.env`, npm installs):

```bash
bash skills/creator-paywall/scripts/init.sh <target_dir> <creator_wallet> [jwt_secret] [siwe_domain]
# example:
bash skills/creator-paywall/scripts/init.sh output/projects/my-paywall 0xYourAgentWallet
```

`jwt_secret` auto-generates if omitted. `siwe_domain` defaults to `localhost` (set the real domain in prod).

**Step 3 — set the plans.** Edit `config.js` → `PLANS`: each entry is one `(chain, token, monthly, yearly)`
the user can pick. Stablecoins recommended (stable fiat value). For custom tokens, set the correct `decimals`.

**Step 4 — run & preview.**

```bash
# foreground for a quick check, or use the preview tool:
```
Use the `preview` tool: `serve` with `dir=<target_dir>`, `command="node src/server.js"`, `port=3007`
(port must match `PORT` in `.env`). Then give the user `/preview/<id>/`.

## Critical gotchas (learned building this — don't skip)

1. **Preview runs in an iframe → cookies are blocked.** The frontend uses **token-based auth**
   (`localStorage` + `Authorization: Bearer`), NOT cookies. If you rewrite the frontend, keep this —
   cookie sessions silently fail inside the preview frame (login "does nothing").
2. **Preview is served under `/preview/<id>/`.** All frontend API calls MUST be **relative**
   (resolved against `document.baseURI`), never absolute `/api/...` — absolute paths hit the root
   domain and 404, leaving a blank page.
3. **Wallets are often blocked inside iframes.** UI/state works in the frame, but to actually
   trigger MetaMask signing/transfer the user should open the preview in a **new browser tab** or a
   **wallet in-app browser**, OR publish to a public URL. The frontend already warns about this.
4. **Native coin (ETH/BNB) can't be log-scanned.** The "Check payment" button uses `getLogs` which
   only catches ERC20 `Transfer` events. Native payments must be confirmed via **txHash submit**
   (the UI handles this automatically after sending; manual paste is the fallback).
5. **No background polling — by design.** Confirmation is on-demand only (post-payment txHash poll,
   "Check payment" button, manual hash). Keeps public-RPC usage tiny. Don't add a block-scanning loop.
6. **Amount match uses `>=`, not `==`.** Safe for fee-on-transfer / rounding. Keep it.

## Integrating into the creator's own product

The whole thing reduces to two middlewares:

```js
import { requireAuth, requireSubscription } from "./src/auth.js";

app.get("/my/premium", requireAuth, requireSubscription, (req, res) => {
  // req.wallet = user address;  req.subscription.expires_at = unix expiry
  res.json({ ... });
});
```

- Bring your own DB by replacing `src/db.js` (everything else is storage-agnostic).
- Session works via **Bearer token** (returned by `/api/login`) — works in SPAs and iframes.
- Subscriptions renew by the user paying again (`expires_at` rolls forward). No on-chain auto-debit.

## API surface

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| GET  | `/api/config` | — | chains, plans, creator wallet |
| GET  | `/api/nonce?address=&chainId=&uri=` | — | SIWE message to sign |
| POST | `/api/login` `{message,signature,chainId}` | — | verify → returns session token |
| POST | `/api/logout` | — | end session |
| GET  | `/api/me` | token | wallet + subscription status |
| POST | `/api/subscribe/intent` `{chainId,token,period}` | token | start payment → amount + payTo |
| POST | `/api/subscribe/verify` `{intentId,txHash}` | token | confirm a tx (native + ERC20) |
| POST | `/api/subscribe/check` `{intentId?}` | token | scan for ERC20 payment |
| GET  | `/api/protected` | token + subscription | example gated resource |

## Verification rules (what counts as paid)

1. Tx confirmed (chain-specific confirmations) and succeeded
2. Recipient == creator wallet
3. Sender == logged-in wallet
4. Token matches the selected plan
5. Amount ≥ plan price (`>=`)
6. txHash not already used (idempotent)

## Going to production

- Set a strong `JWT_SECRET` and the real `SIWE_DOMAIN` in `.env`.
- Swap public RPCs in `config.js` for your own (Alchemy/QuickNode) — set `RPC_ETHEREUM/RPC_BASE/RPC_BSC`.
- Replace SQLite (`src/db.js`) with your production DB.
- Publish via the `community-publish` skill for a public URL (also fixes the iframe-wallet limitation).
