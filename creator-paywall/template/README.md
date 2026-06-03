# Creator Paywall

A **minimal** crypto subscription paywall. Users log in with an EVM wallet (SIWE),
pay a subscription by transferring tokens to your wallet, and get access — verified on-chain.
No payment processor, no third-party account, no recurring on-chain approvals.

Built to be **dropped into your own product**. It does two things and nothing more:
**wallet auth** + **subscription verification**.

## How it works

```
User connects wallet ──► signs SIWE message ──► session (wallet = identity)
        │
        ├─ picks plan (chain + token + monthly/yearly)
        ├─ transfers tokens to YOUR wallet
        └─ frontend submits txHash ──► backend verifies on-chain ──► subscription active
```

The key trick: **the payer's address must equal the logged-in wallet.** That's how a
plain transfer is matched to a user with zero memos or order IDs.

Supported chains: **Ethereum, Base, BSC**. Tokens: any ERC20 (incl. your own custom token)
or the native coin. All configured in one file.

## Quick start

```bash
npm install
cp .env.example .env      # set CREATOR_WALLET (your Starchild agent wallet) + JWT_SECRET
npm start                 # http://localhost:3000
```

Edit **`config.js`** — the only file you normally touch:
- `CREATOR_WALLET` — where payments land (your agent's EVM address)
- `PLANS` — which (chain, token, price) combos you sell, monthly/yearly
- `CHAINS` — swap public RPCs for your own (Alchemy/QuickNode) in production

## Payment confirmation

No background polling (keeps RPC usage tiny). Confirmation happens on-demand:
1. **After paying in the UI** — frontend submits the txHash, backend verifies (poll a few times).
2. **"Check payment" button** — scans recent token transfers from the user to your wallet
   (single bounded `getLogs` call, anchored at the block the payment started).
3. **"Verify hash"** — user pastes a txHash manually. Required for native ETH/BNB
   (native transfers can't be log-scanned).

## API

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| GET  | `/api/config` | — | chains, plans, creator wallet |
| GET  | `/api/nonce?address=&chainId=&uri=` | — | get SIWE message to sign |
| POST | `/api/login` `{message,signature,chainId}` | — | verify signature → session cookie + token |
| POST | `/api/logout` | — | clear session |
| GET  | `/api/me` | session | wallet + subscription status |
| POST | `/api/subscribe/intent` `{chainId,token,period}` | session | start payment, returns amount + payTo |
| POST | `/api/subscribe/verify` `{intentId,txHash}` | session | confirm a specific tx (native + ERC20) |
| POST | `/api/subscribe/check` `{intentId?}` | session | scan for payment (ERC20) |
| GET  | `/api/protected` | session + subscription | example gated resource |

Session works via **httpOnly cookie** or **`Authorization: Bearer <token>`** — use whichever fits your app.

## Integrating into your product

The whole thing is two middlewares:

```js
import { requireAuth, requireSubscription } from "./src/auth.js";

// gate any route behind a paid subscription
app.get("/my/premium/route", requireAuth, requireSubscription, (req, res) => {
  // req.wallet  = the user's address
  // req.subscription.expires_at = unix expiry
  res.json({ ... });
});
```

Bring your own DB by replacing `src/db.js` (it's ~120 lines of SQLite). Everything else
(`chains.js`, `payments.js`, `auth.js`) is storage-agnostic.

## Verification rules (what counts as a valid payment)

1. Tx is confirmed (chain-specific confirmations) and succeeded
2. Recipient == `CREATOR_WALLET`
3. Sender == the logged-in wallet
4. Token matches the selected plan
5. Amount transferred ≥ the plan price (`>=`, not `==` — safe for fee-on-transfer tokens)
6. txHash hasn't been used before (idempotent)

## Notes & limits (by design)

- **Stablecoins recommended.** Pricing native/volatile tokens at a fixed amount means the
  fiat value drifts. USDC/USDT keep prices stable.
- **No auto-renew.** On-chain subscriptions renew by the user sending another payment
  (which extends `expires_at`). No allowance/delegation — safer, simpler.
- **Custom tokens:** set the correct `decimals`. Fee-on-transfer tokens work because matching
  uses the actual received amount.
- **Not a payment processor.** No refunds, disputes, or fiat. This is wallet-to-wallet.
- This template stays intentionally small. Add notifications, creator dashboards, multi-creator
  routing, etc. on top — the core won't fight you.
