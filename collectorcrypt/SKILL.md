---
name: collectorcrypt
version: 1.3.0
description: >-
  CollectorCrypt: physical trading card NFTs on Solana — marketplace, gacha packs, vault redemption, P2P swaps.
  Use when buying/selling/trading collectible card NFTs, opening mystery packs, redeeming NFTs for physical cards, or swapping assets on Solana (e.g. list Pokemon card for 50 USDC, open gacha pack, ship card to address, swap NFTs peer-to-peer).
allowed-tools: Bash, Read, Write, WebFetch
homepage: https://collectorcrypt.com
metadata:
    emoji: "🃏"
    homepage: https://collectorcrypt.com
    # No env requirement and no primaryEnv: there is NO API key for this service
    # (confirmed by the CollectorCrypt team). Do not set CC_API_KEY. See "No API Key" below.
    tags:
      - nft
      - trading-cards
      - pokemon
      - solana
      - marketplace
      - gacha
      - mystery-packs
      - rwa
      - physical-redemption
      - vault
      - swap
      - usdc
      - collectibles
      - ebay
      - vrf

---

# CollectorCrypt API

Bridge physical trading cards and blockchain — buy, sell, and trade collectible card NFTs on Solana, open mystery gacha packs, redeem NFTs for real cards, and swap assets peer-to-peer.

**Marketplace Base URL:** `https://api.collectorcrypt.com`
**Marketplace Devnet URL:** `https://dev-api.collectorcrypt.com`
**Gacha Base URL:** `https://gacha.collectorcrypt.com`
**Gacha Devnet URL:** `https://dev-gacha.collectorcrypt.com`

## Key Concepts

### Product Suite

- **Marketplace** — buy/sell/trade collectible card NFTs using USDC on Solana
- **Gacha Machine** — mystery pack system; spend USDC for randomized Pokemon card NFTs with VRF-verified fairness
- **Vault** — bridge NFTs ↔ physical cards; deposit real cards to mint NFTs, burn NFTs to ship physical cards
- **Swap** — peer-to-peer on-chain asset swaps via escrow (NFTs, pNFTs, cNFTs, SPL tokens)
- **Launchpads** — drop pages for minting new collectible releases
- **Bidder** — eBay bid automation; deposit funds, service bids and tokenizes won cards

### Solana Programs

| Program | ID |
|---------|-----|
| Marketplace | `CcmRKTuZCGJBWQwMHvDYApBRvSZNHqGJXkznqpDTSQUr` |
| Swap | `CCSwaptcDXtfjyRMYBqavqBwiW162yXFAJrXN53UuENC` |

### NFT Types Supported

- **Programmable NFTs (pNFTs)** — Metaplex standard with enforced royalties; use `tokenStandard: "Pnft"`
- **Compressed NFTs (cNFTs)** — Metaplex Bubblegum merkle-tree structure; use `tokenStandard: "Cnft"`
- **Metaplex Core (`nftStandard: "core"`)** — single-account standard; **many live listings are Core** (browse responses return `"nftStandard": "core"`). For Core listings, **omit `tokenStandard`** from buy/list/offer bodies — do NOT pass `"Pnft"`/`"Cnft"`. Only send `tokenStandard` when the asset is actually pNFT or cNFT.

### Currency

All marketplace and gacha transactions use **USDC** (SPL Token) on Solana. Shipping fees accept USDC or USDT. Gas fees paid in SOL.

**Marketplace prices are in whole USDC** (e.g., `"price": 25` means $25.00 USDC).

### Transaction Pattern (Marketplace & Shipping)

Three-step flow:
1. **Build** — POST to API endpoint, receive base64-encoded unsigned transaction(s)
2. **Sign** — Sign with the Solana wallet (Phantom/Solflare, or the Starchild wallet helper — see below)
3. **Broadcast** — POST signed transaction to `/marketplace/broadcast`

**HTTP status — accept BOTH `200` and `201` as success.** Verified live: `/marketplace/buy` and `/marketplace/broadcast` return **`201`**, not `200`. Treat any 2xx as success; do not hard-check `== 200`.

**Response body may be raw base64 text, NOT JSON.** `/marketplace/buy` with `fundingSource: "wallet"` can return the unsigned transaction as a plain-text body. Parse defensively:
```python
text = response.text
try:
    data = response.json()
    tx = data.get("transaction") or data.get("serializedTransaction")
except Exception:
    tx = text  # body was the raw base64 transaction
```

**Starchild wallet signing returns snake_case `signed_transaction`.** When signing with the platform wallet:
```python
from core.skill_tools import wallet
signed = wallet.wallet_sol_sign_transaction(unsigned_tx)
# → {"signed_transaction": "<base64>", "encoding": "base64"}
signed_tx = signed.get("signed_transaction") or signed.get("signedTransaction")
```
Look for `signed_transaction` first, then the camelCase variant. Feed `signed_tx` into `/marketplace/broadcast` as the `signedTransaction` field.

### Gacha Rarity Tiers

| Rarity | Probability |
|--------|------------|
| Epic | 1% |
| Rare (High) | 4% |
| Uncommon (Mid) | 15% |
| Common (Low) | 80% |

### VRF (Verifiable Random Function)

Gacha rolls use a Verifiable Random Function for tamper-proof, provably-fair results. Selection is **two-stage**:
1. **Roll → tier:** a uniform integer **roll in the range 1–100,000,000**, seeded by the player's own wallet signature on the open transaction, maps to a rarity tier via the machine's configured weights (see `tierRanges` in `/api/machines`).
2. **Card → within tier:** a provable selection picks the specific NFT inside that tier.

The seed (wallet signature) and result are committed to Solana in the award transaction's on-chain memo, preventing prediction or manipulation. Verify independently:
- `GET /api/vrf/verify?memo=YOUR_MEMO` — returns the proof, public key, transaction signature, and whether the stored roll matches the recomputed roll.
- `/verify-selection/YOUR_MEMO` — browser-side replay of the card selection against the on-chain memo.

The docs do **not** name a specific VRF algorithm; don't assert one.

## How to Call

### Gacha API — No API Key (the key does not exist)

**There is no API key. Do not set `CC_API_KEY`, do not send an `x-api-key` header, and do not try to obtain a key — the CollectorCrypt team has confirmed no key system exists.** Every gacha endpoint, reads and writes alike, is called with no authentication.

```bash
# Reads AND writes — no auth header of any kind
curl -s "https://gacha.collectorcrypt.com/api/machines"
curl -s -X POST "https://gacha.collectorcrypt.com/api/generatePack" \
  -H "Content-Type: application/json" \
  -d '{"playerAddress":"WALLET_PUBKEY"}'
```

> **Ignore the docs' authentication section.** The public docs say *"Each request must include a valid `x-api-key` header"* and reference a partner "slug." That does not reflect reality — confirmed both by the team (no key system exists) and by live testing (`/api/generatePack` returns `200` with no header). There is nothing to request and no header to add.

Without a key, generated transactions carry a `cc-<uuid>` memo. Security comes from the **wallet signature**, not from any API credential — nothing executes until the user signs the transaction this API hands back.

Reference implementation: **Gacha Starter Demo** — https://github.com/daxherrera/gacha-starter (full pack → sign → submit → open flow). Try every call live on devnet at `https://dev-gacha.collectorcrypt.com` (fund a devnet wallet via the USDC faucet: https://spl-token-faucet.com/?token-name=USDC-Dev).

### Marketplace API — No Auth for Reads

Public GET endpoints (browse listings) need no authentication. Write endpoints return unsigned transactions for wallet signing — no API key involved.

```bash
# Browse listings — no auth, 5s cache for unauthenticated requests
curl -s "https://api.collectorcrypt.com/marketplace?page=1&step=20&categories=Pokemon"

# Create listing — returns base64 unsigned transaction
curl -s -X POST "https://api.collectorcrypt.com/marketplace/list" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet": "YOUR_SOLANA_ADDRESS",
    "cardId": "CC_CARD_DB_ID",
    "nftAddress": "NFT_MINT_ADDRESS",
    "currency": "USDC",
    "price": 50
  }'
```

### Shipping API — Two Auth Tracks

**Track A — Privy Identity Token:**
```
Authorization: Bearer <privy-identity-token>
```

**Track B — Sign-In With Solana (SIWS):**
1. `POST /auth/wallet/nonce` — get nonce + message to sign
2. Sign message with wallet (ed25519, base58)
3. `POST /auth/wallet/verify` — exchange signature for access/refresh tokens

```bash
# Step 1: Get nonce
curl -s -X POST "https://api.collectorcrypt.com/auth/wallet/nonce" \
  -H "Content-Type: application/json" \
  -d '{"wallet": "YOUR_PUBKEY", "partnerAppId": "your-slug", "domain": "your-app.com", "uri": "https://your-app.com"}'

# Step 3: Verify and get tokens
curl -s -X POST "https://api.collectorcrypt.com/auth/wallet/verify" \
  -H "Content-Type: application/json" \
  -d '{"message": "<message-from-nonce>", "signature": "<base58-ed25519-signature>"}'
# Returns: {"accessToken": "cca_...", "refreshToken": "ccr_...", "expiresAt": ...}
```

**Token management:**
- Access token lifetime: 15 minutes
- Refresh: `POST /auth/wallet/refresh` with `{"refreshToken": "..."}`
- Logout: `POST /auth/wallet/logout`
- Track B limitation: crypto payment only (no card payments), Solana signatures only

## Intent Routing

### Marketplace

Base: `https://api.collectorcrypt.com`

All POST endpoints return base64-encoded unsigned Solana transaction(s). Sign with wallet, then broadcast via `/marketplace/broadcast`.

#### List an NFT — `POST /marketplace/list`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Seller's Solana address |
| `cardId` | string | yes | CollectorCrypt card DB ID |
| `nftAddress` | string | yes | NFT mint address |
| `currency` | string | yes | `"USDC"` |
| `price` | number | yes | Listing price in USDC |
| `tokenStandard` | enum | no | `"Pnft"` or `"Cnft"` |
| `userHasSol` | boolean | no | If `false`, backend pays fees |

Errors: `400` (on-chain error), `409` (already listed)

#### Cancel a Listing — `POST /marketplace/cancel-listing`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Caller's wallet |
| `tokenMint` | string | yes | NFT mint address |
| `seller` | string | no | Defaults to `wallet` |

Errors: `400` (on-chain error), `404` (no listing found)

#### Update a Listing Price — `POST /marketplace/update-listing`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Seller's wallet |
| `tokenMint` | string | yes | NFT mint address |
| `newPrice` | number | yes | Updated price in USDC |
| `coin` | string | yes | `"USDC"` |

Errors: `400` (price unchanged or on-chain error), `404` (no listing found)

#### Buy an NFT — `POST /marketplace/buy`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Buyer's wallet |
| `nftAddress` | string | yes | NFT mint address |
| `price` | number | yes | Listed price in USDC |
| `currency` | string | yes | `"USDC"` |
| `tokenStandard` | enum | no | `"Pnft"` or `"Cnft"` — **omit for Metaplex Core listings** (`nftStandard: "core"`) |
| `sellerWallet` | string | no | Resolved from DB if omitted |
| `fundingSource` | enum | no | `"wallet"` (default) or `"escrow"` |

**Success status is `200` OR `201`** (live buys return `201`). **Response body may be raw base64 text rather than JSON** — parse defensively (see Transaction Pattern above).
- `fundingSource: "wallet"` → single base64 unsigned transaction (JSON `{"transaction": "..."}` **or** plain base64 text)
- `fundingSource: "escrow"` → `{"transactions": ["BASE64_WITHDRAW_TX", "BASE64_BUY_TX"], "fundingSource": "escrow"}`

Escrow requires minimum `price × 1.02` USDC balance.

Errors: `400` (on-chain error, insufficient escrow), `404` (card/listing not found), `409` (owner changed)

#### End-to-End Buy Recipe (tested live)

```python
import requests
from core.skill_tools import wallet

BASE = "https://api.collectorcrypt.com"
buyer = "YOUR_WALLET_PUBKEY"

# 1. Find a listed item, cheapest first
listings = requests.get(f"{BASE}/marketplace",
    params={"page": 1, "step": 1, "marketplaceStatus": "Buy now", "orderBy": "listedPriceAsc"}
).json()["filterNFtCard"]
item = listings[0]
mint   = item["nftAddress"]
price  = float(item["listing"]["price"])
seller = item["owner"]["wallet"]
std    = item.get("nftStandard")  # "core" | "Pnft" | "Cnft"

# 2. Build buy tx. Omit tokenStandard for Core listings.
body = {"wallet": buyer, "nftAddress": mint, "price": price,
        "currency": "USDC", "sellerWallet": seller}
if std in ("Pnft", "Cnft"):
    body["tokenStandard"] = std
r = requests.post(f"{BASE}/marketplace/buy", json=body)
assert r.status_code in (200, 201)              # buy returns 201
try:    unsigned = r.json().get("transaction") or r.json().get("serializedTransaction")
except Exception: unsigned = r.text             # may be raw base64

# 3. Sign with Starchild wallet (snake_case key)
signed = wallet.wallet_sol_sign_transaction(unsigned)
signed_tx = signed.get("signed_transaction") or signed.get("signedTransaction")

# 4. Broadcast
b = requests.post(f"{BASE}/marketplace/broadcast",
    json={"wallet": buyer, "signedTransaction": signed_tx, "nftAddress": mint})
assert b.status_code in (200, 201) and b.json().get("success")  # broadcast returns 201
sig = b.json()["signature"]

# 5. Verify on Solana RPC — the SOURCE OF TRUTH (see below)
status = requests.post("https://api.mainnet-beta.solana.com", json={
    "jsonrpc": "2.0", "id": 1, "method": "getSignatureStatuses",
    "params": [[sig], {"searchTransactionHistory": True}]}
).json()["result"]["value"][0]
assert status and status["err"] is None and status["confirmationStatus"] == "finalized"
```

**Verify via Solana RPC signature status, not a marketplace refetch.** Marketplace metadata refresh lags after a buy, and there is no `nftAddress` lookup filter (`search=<mint>` is fuzzy and may not reflect the new owner immediately). The authoritative post-broadcast check is `getSignatureStatuses` on the broadcast `signature`:
```json
{"confirmationStatus": "finalized", "err": null, "status": {"Ok": null}}
```
`err == null` (and `confirmationStatus` of `confirmed`/`finalized`) means the buy settled on-chain. Only fall back to a marketplace refetch for display, never as the success gate.

**Regression fixture — a real buy that succeeded (use to smoke-test the flow):**

| Field | Value |
|-------|-------|
| Item | 2017 #024 POKE BALL PSA 9 — Pokémon Japanese Sun & Moon, Ash vs. Team Rocket Deck Kit |
| Price | 19 USDC |
| NFT mint | `4AWreh7pqVb4jhANAXFz2fwSPKqWr5ZAFMgaAFWZS9nk` |
| Seller | `FfveJgtFmGPCSazkjicf21WLk9rdUaMsownVVA8LRhwf` |
| Broadcast signature | `5SwxeuWGjWbiAFq8YVN3Qsw1PXnKXBakKA2ykgccc78gg6JkGnyi48StezcijXmgWHyGWvojq8TYmTXJoC9XnbjH` |
| Solana status | `finalized`, `err: null` |

#### Make an Offer — `POST /marketplace/make-offer`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Buyer's wallet |
| `cardId` | string | yes | CollectorCrypt card DB ID |
| `nftAddress` | string | yes | NFT mint address |
| `price` | number | yes | Offer price in USDC |
| `currency` | string | yes | `"USDC"` |
| `tokenStandard` | enum | no | `"Pnft"` or `"Cnft"` |
| `userHasSol` | boolean | no | Backend fee payer if `false` |
| `ownerWallet` | string | no | Current NFT owner |
| `collectionHash` | string | no | cNFT collection hash |

Errors: `400` (can't determine owner or on-chain error)

#### Cancel an Offer — `POST /marketplace/cancel-offer`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Buyer's wallet |
| `nftAddress` | string | yes | NFT mint address |
| `keepInEscrow` | boolean | no | If `true`, USDC stays in escrow; default `false` |

Backend auto-sets `keepInEscrow: true` if wallet has insufficient SOL for rent.

Errors: `404` (no active offer found)

#### Update an Offer — `POST /marketplace/update-offer`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Buyer's wallet (signer) |
| `nftAddress` | string | yes | NFT mint address |
| `currency` | string | yes | `"USDC"` |
| `buyer` | string | yes | Buyer's wallet (typically = `wallet`) |
| `price` | number | yes | New offer price in USDC |

**Important:** Escrow must already contain the full new amount — this instruction does NOT transfer additional USDC.

Errors: `400` (price unchanged, no escrow, insufficient balance, on-chain error), `404` (offer not found)

#### Accept an Offer — `POST /marketplace/accept-offer`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Seller's wallet (NFT owner) |
| `nftAddress` | string | yes | NFT mint address |
| `buyer` | string | yes | Buyer's wallet |
| `currency` | string | yes | `"USDC"` |
| `price` | number | yes | Offer price in USDC |
| `tokenStandard` | enum | no | `"Pnft"` or `"Cnft"` |
| `userHasSol` | boolean | no | Backend fee payer if `false` |

**cNFT edge case:** If the cNFT is currently listed, returns:
```json
{
  "requiresCancelListing": true,
  "cancelListingTx": "BASE64_CANCEL_LISTING_TX",
  "message": "This cNFT is currently listed. Please sign..."
}
```
Sign the cancel-listing tx first, then re-call accept-offer.

Errors: `400` (price drift, on-chain error), `404` (offer not found)

#### Browse Listings — `GET /marketplace`

Public, no auth required. 5-second cache for unauthenticated requests.

**Pagination:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | 1-indexed page |
| `step` | integer | 100 | Page size (max 100) |

**Filters (all optional):**

| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Substring match against itemName, nftAddress, gemrateCardName, gradingID. **This is the only way to look up by mint** — there is NO `nftAddress` query param (`GET /marketplace?nftAddress=<mint>` returns `400`). Use `search=<mint>` instead. |
| `ownerAddress` | string | Filter by owner wallet |
| `hideOwned` | boolean | Hide caller's own cards (requires auth) |
| `favoritesOnly` | boolean | Only favorited cards (requires auth) |
| `followingOnly` | boolean | Only from followed users (requires auth) |
| `followingOf` | string | Cards owned by users that this wallet follows |
| `marketplaceStatus` | CSV | `Buy now`, `Has offers` |
| `marketplaceSource` | CSV | `CC`, `ME` |
| `marketplaceTags` | CSV | Global tag names (e.g., `Hot`, `Featured`) |
| `listPriceMin` / `listPriceMax` | number | USDC price range |
| `insuredValueMin` / `insuredValueMax` | number | Insured value range |
| `yearMin` / `yearMax` | integer | Card year range |
| `categories` | CSV | `Pokemon`, `Baseball`, `Basketball`, `Football`, `Magic The Gathering`, `Yu-Gi-Oh!`, `Lorcana`, `One Piece`, `Non-Sport`, etc. |
| `cardType` | CSV | `Card`, `Comic`, `ComicRaw`, `Game`, `Merch`, `Raw`, `Sealed` |
| `blockchain` | CSV | `Solana`, others |
| `authenticated` | boolean | Only authenticated cards |
| `autographed` | boolean | Only autographed cards |
| `burnt` | boolean | Include burned cards (default excludes) |
| `grade` | string | Substring match |
| `genericGradeMin` / `genericGradeMax` | number | Numeric grade range |
| `gradingCompany` | CSV | `PSA`, `Beckett`, `CGC`, `SGC`, `TAG`, `CSG`, `KSA`, `PSA/DNA`, `UDA`, `Steiner`, `BBCE`, `Rare Edition`, `Not graded` |
| `set` / `format` / `language` / `productCode` | string | Substring match for sealed/comic metadata |
| `pokemon` | string | Word-boundary match against gemrateCardName |
| `ccBuyback` | boolean | Only cards with active CC buyback |
| `gemrateSet` / `gemrateGrade` / `gemrateCardName` / `gemrateSpecId` / `gemrateParallel` | string | Gemrate-specific filters |

**Sort — `orderBy` values:**
`dateAsc`, `dateDesc`, `nameAsc`, `nameDesc`, `priceAsc`, `priceDesc` (insured value), `yearAsc`, `yearDesc`, `listedDateAsc`, `listedDateDesc`, `listedPriceAsc`, `listedPriceDesc`
Default: `listedDateDesc`

**Response:**
```json
{
  "filterNFtCard": [
    {
      "id": "card_db_id",
      "itemName": "...",
      "nftAddress": "NFT_MINT_ADDRESS",
      "nftStandard": "Pnft",
      "blockchain": "Solana",
      "category": "Pokemon",
      "type": "Card",
      "year": 1999,
      "grade": "10",
      "gradeNum": 10,
      "gradingCompany": "PSA",
      "gradingID": "...",
      "insuredValue": "...",
      "listing": {
        "price": "25",
        "currency": "USDC",
        "marketplace": "CC",
        "sellerId": "...",
        "createdAt": "ISO_DATE"
      },
      "offers": [{"id": "offer_id"}],
      "owner": {
        "id": "user_id",
        "name": "...",
        "wallet": "OWNER_WALLET_ADDRESS"
      },
      "images": {
        "front": "URL",
        "frontM": "URL",
        "frontS": "URL",
        "back": "URL",
        "backM": "URL",
        "backS": "URL"
      }
    }
  ],
  "findTotal": 1234,
  "total": 50000,
  "totalPages": 25,
  "cardsQtyByCategory": {"Pokemon": 800, "Baseball": 200}
}
```

- `listing` is `null` when unlisted
- `offers` is array of active offer IDs
- `findTotal` = total matching filter; `total` = total marketplace cards overall
- `cardsQtyByCategory` = per-category count (excludes `categories` filter)

#### Broadcast a Transaction — `POST /marketplace/broadcast`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `wallet` | string | yes | Signer wallet address |
| `signedTransaction` | string | yes | Base64-encoded signed transaction |
| `nftAddress` | string | no | Triggers metadata refresh after 5s |

**Success status is `200` OR `201`** (live broadcasts return `201`). **Response:**
```json
{
  "success": true,
  "signature": "SOLANA_TRANSACTION_SIGNATURE",
  "message": "Transaction broadcast successfully"
}
```
Don't treat the `201` as a failure — check `success === true` / presence of `signature`, not the status code.

**Insufficient funds recovery:** If broadcast returns `400` with `"code": "INSUFFICIENT_FUNDS_RETRYABLE"`, rebuild the original transaction with `userHasSol: false` so the backend pays fees, then re-sign and re-broadcast.

**Validation:** Transaction is validated against an allow-list of program IDs before submission.

Errors: `400` (invalid transaction, insufficient funds retryable, submission failure), `403` (program ID not on allow-list)

### Gacha Machine

Base: `https://gacha.collectorcrypt.com`

| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/api/status` | — | Machine operational status (open/closed) |
| GET | `/api/stock` | — | NFT inventory counts by rarity per machine |
| GET | `/api/machines` | — | Full config for all machines: pricing, `odds`, `tierRanges` (roll→tier bounds), live `stock`, `instantBuyback` %, and `ev` (rarity-weighted expected insured value) |
| GET | `/api/getNfts` | `code`, `rarity`, `page`, `limit` | Available NFTs with filtering |
| POST | `/api/generatePack` | Body: `playerAddress`, `packType`, `turbo`, `altPlayerAddress` | Create purchase transaction for one pack |
| POST | `/api/generateYoloPacks` | Body: `count` (1-100), `packType`, `playerAddress`, `turbo`, `altPlayerAddress` | Batch purchase multiple packs |
| POST | `/api/openPack` | Body: `memo` | Open purchased pack, receive NFT |
| POST | `/api/buyback` | Body: `playerAddress`, `nftAddress`, `altRecipient` | Sell NFT back for USDC (within 72 hours) |
| GET | `/api/buyback/check` | `memo` | Check buyback completion status |
| GET | `/api/buyback/available` | `wallet`, `nft` | Pre-check NFT buyback eligibility + refund `amount` (before building a tx) |
| GET | `/api/pack/status` | `memo` | Full pack lifecycle: purchase, NFT send (incl. `prize_tier`, `insured_value`, `vrf_proof`), and buyback history |
| POST | `/api/submitTransaction` | Body: `signedTransaction` (base64) | Submit signed transaction to Solana |
| POST | `/api/generateGift` | Body: `sender`, `receiver`, `packType`, `count` | Gift packs to another wallet |
| GET | `/api/getGifted` | `wallet` | Gift history (sent/received) |
| GET | `/api/purchasedPacks` | `wallet` | Pack counts by type (purchased vs gifted, used vs unused) |
| POST | `/api/generatePurchasedPack` | Body: `publicKey`, `packType`, `ledger` | Create sign challenge for opening gifted/purchased packs |
| POST | `/api/usePurchasedPack` | Body: `nonce`, `packType`, `publicKey`, `signature`/`transactionSignature`, `ledger` | Consume purchased pack after signing, returns memo |
| GET | `/api/getAllWinners` | `timestamp`, `slug`, `epic`, `packType`, `count` | Recent winners with optional filtering |
| GET | `/api/vrf/verify` | `memo` | Verify VRF proof for a roll |

#### Gacha Response Shapes

**generatePack response:**
```json
{"memo": "slug-uuid", "transaction": "base64_encoded_transaction"}
```
The `memo` is `cc-<uuid>` (there is no API key, so no partner slug prefix applies). Body is `{playerAddress, packType?, turbo?, altPlayerAddress?}` — `packType` defaults to `pokemon_50` (use `pokemon_250` for legendary).

**openPack response (normal win):**
```json
{
  "success": true,
  "transactionSignature": "...",
  "nft_address": "...",
  "nftWon": {
    "content": {
      "metadata": {"name": "...", "description": "...", "attributes": []}
    }
  },
  "points": 0,
  "roll": 12345678,
  "rarity": "Epic|Rare|Uncommon|Common"
}
```
`roll` is an integer in the range 1–100,000,000 (NOT a fraction). `nftWon` is nested under `content.metadata` — there is no top-level `name`/`image`.

**openPack response (turbo-mode buyback, Common roll):** adds `"code": "TURBO_MODE_BUYBACK"` and `"buybackAmount": 42500000` (USDC base units) — the Common NFT is auto-sold instead of delivered.

**openPack response (payment not yet confirmed):**
```json
{"success": true, "code": "WAITING_FOR_WEBHOOK", "memo": "slug-uuid-string"}
```
Do NOT assume an NFT was delivered on this response — poll `GET /api/pack/status?memo=...` (or retry `openPack`) until the win resolves.

**openPack is idempotent:** calling it again on an already-opened pack returns the original result (same `transactionSignature`, `nftWon`, `points`, `rarity`) — safe to retry.

**Prize tier mapping** (`pack/status` and `getAllWinners` return numeric `prize_tier`; `openPack` returns human-readable `rarity`): `1` = Epic, `2` = Rare, `3` = Uncommon, `4` = Common.

**buyback response:**
```json
{
  "serializedTransaction": "base64",
  "refundAmount": 42500000,
  "memo": "..."
}
```

### Shipping / Vault Redemption

Base: `https://api.collectorcrypt.com`

| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| POST | `/redeem/estimate` | Body: `nftAddresses`, `shippingAddressId` | Fee estimate without creating shipment; returns `price`, `insurancePrice`, `feesPrice`, `shippingPrice`, `total`, `numberOfCards`, `breakdown` |
| POST | `/redeem/prepare` | Body: `nftAddresses`, `shippingAddressId`, `coin` (`USDC`\|`USDT`), `deliveryCompany`, `comment`, `insurance` | Create pending shipment, returns unsigned transactions |
| POST | `/blockchain/:outboundShipmentId/burn` | Body: `transactions` (base64 signed), `evmTransactions` | Broadcast signed burn transactions; returns `id`, `status`, `transactionUrls` |
| GET | `/outbound-shipment` | — | List user shipments |
| GET | `/outbound-shipment/:id` | `id` | Get specific shipment status |

#### Shipping Address Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/shipping-address` | List saved addresses |
| GET | `/shipping-address/:id` | Get specific address |
| POST | `/shipping-address/create` | Create new address |
| PATCH | `/shipping-address/update/:id` | Update address |
| DELETE | `/shipping-address/:id` | Delete address |

#### Shipping Rates

| Region | Base | Each Additional | Signature | Pack Surcharge |
|--------|------|-----------------|-----------|----------------|
| USA | $5.99 | $3.00 | +$3.00 (value >= $500) | $0.18/pack |
| Canada | $20.99 | $3.00 | Included | $0.25/pack |
| Europe | $29.99 | $3.00 | Included | $0.25/pack |
| Australia/NZ | $34.99 | $3.00 | Included | $0.25/pack |
| Rest of World | $34.99 | $3.00 | Included | $0.25/pack |

Insurance auto-applies at 0.5% of declared value when package exceeds $5,000.

#### Redeem/Prepare Response Shape

```json
{
  "outboundShipmentId": "shipment_...",
  "transactions": ["<base64-unsigned-tx>"],
  "evmTransactions": [],
  "totalCost": 14.99,
  "submitUrl": "/blockchain/shipment_.../burn",
  "breakdown": {
    "region": "USA",
    "declaredValue": 700,
    "numberOfCards": 10,
    "lines": [
      {"code": "shipping_base", "label": "Base shipping (USA, first card)", "amount": 5.99, "unitPrice": 5.99}
    ]
  }
}
```

### Auth (SIWS — Sign-In With Solana)

Base: `https://api.collectorcrypt.com`

| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| POST | `/auth/wallet/nonce` | Body: `wallet`, `partnerAppId`, `domain`, `uri` | Get nonce + EIP-4361 signing message |
| POST | `/auth/wallet/verify` | Body: `message`, `signature` (base58 ed25519) | Exchange signature for access + refresh tokens |
| POST | `/auth/wallet/refresh` | Body: `refreshToken` | Refresh expired access token |
| POST | `/auth/wallet/logout` | Body: `refreshToken` (+ access token in `Authorization` header) | Invalidate tokens |

### Swap Program (On-Chain)

Program ID: `CCSwaptcDXtfjyRMYBqavqBwiW162yXFAJrXN53UuENC`

The swap program is an Anchor-based Solana smart contract. Trades follow this lifecycle:

```
Open → Approved → Executed → Settled → (Closed)
         ↑            ↑
    cancel_trade  cancel_trade
```

**Instructions:**

| Instruction | Description |
|-------------|-------------|
| `create_trade` | Initialize trade between two wallets |
| `approve_trade` | Signal readiness (both parties must approve) |
| `execute_trade` | Commit to execution (both parties must execute) |
| `cancel_trade` | Abort open or approved trades |
| `execute_nft_batch` | Transfer standard NFTs into/out of escrow |
| `execute_pnft_batch` | Transfer programmable NFTs |
| `execute_cnft_batch` | Transfer compressed NFTs |
| `execute_token_batch` | Transfer SPL tokens |
| `mark_trade_settled` | Backend confirmation of completion |
| `close_trade` | Final cleanup and rent refund |

## Marketplace On-Chain Details

### Account Structure

| Account | Purpose |
|---------|---------|
| **Market** | Singleton PDA — config (admin keys, fees, treasury, paused status) |
| **Listing** | Sale info indexed by asset ID + seller, with delegation authority |
| **Offer** | Buyer offer details with independent escrow backing |
| **UserEscrow** | Per-user USDC deposit tracking for offer collateral |

### Fee Structure

Platform fee: **200 basis points (2%)**. Configurable 0–200 bps.
```
fee = floor(price * platform_fee_bps / 10000)
```
Uses u128 intermediate precision to prevent overflow.

### Security Properties

- **Non-custodial listings** — NFTs remain in seller wallets using delegation, not escrow transfers
- **Frontrun prevention** — `expected_price` parameters validate on-chain prices match expectations
- **Self-trade blocking** — enforced `seller != buyer` validation
- **PDA determinism** — fixed seed schemes prevent unauthorized account substitution
- **Broadcast allow-list** — transactions validated against approved program IDs before submission

## Error Handling

**Success is any 2xx — accept `200` AND `201`.** Several marketplace write endpoints (`/marketplace/buy`, `/marketplace/broadcast`) return `201` on success. Never gate on `status == 200`; check for a 2xx status plus `success: true` / a `signature` / a transaction body.

All APIs return errors in a standard shape:

```json
{"statusCode": 400, "message": "human-readable error", "error": "Bad Request"}
```

| Status | Meaning |
|--------|---------|
| `400` | Invalid input, on-chain failure, price mismatch, insufficient escrow, signing failure |
| `401` | Invalid or expired token |
| `403` | Access denied, program ID outside broadcast allow-list |
| `404` | Card, NFT, listing, offer, or address not found |
| `409` | Conflict (already listed, owner changed, wallet linked to Privy account) |
| `429` | Rate limit exceeded |
| `500` | Machine empty, too many packs open, or processing error |

## Safety Notes

- **Marketplace prices are in whole USDC.** `"price": 25` means $25.00 USDC.
- **Buy/broadcast succeed with HTTP `201`** — accept any 2xx, parse the body which may be raw base64 (not JSON), and verify the result on Solana RPC (`getSignatureStatuses`), not via a marketplace refetch. See the End-to-End Buy Recipe.
- **Metaplex Core (`nftStandard: "core"`) is common** — omit `tokenStandard` for those; only send `"Pnft"`/`"Cnft"` when the asset really is one.
- **Starchild wallet signing returns `signed_transaction`** (snake_case) — read that (or the camelCase fallback) before broadcasting.
- **Gacha `refundAmount` is in USDC lamports.** 42,500,000 = $42.50 USDC (1 USDC = 1,000,000 lamports).
- **Gacha buyback window is 72 hours.** After that, the NFT cannot be sold back to the machine.
- **Buyback refund is a per-machine percentage of insured/market value** (not the purchase price). The rate is exposed as `instantBuyback` in `GET /api/machines` (e.g. `85` = 85%); don't assume a fixed global rate. Use `GET /api/buyback/available?wallet=…&nft=…` to get the exact refund `amount` before building a buyback tx (USDC base units, already adjusted for the machine's buyback % and **capped at 40,000 USDC**).
- **Non-custodial listings** — NFTs stay in seller wallets via delegation. If a seller transfers an NFT without canceling the listing, the listing becomes invalid. Backend auto-cancellation is not guaranteed.
- **Escrow must be pre-funded for offer updates** — `update-offer` does NOT transfer additional USDC; the escrow must already contain the full new amount.
- **cNFT accept-offer may require two transactions** — if the cNFT is currently listed, the API returns a cancel-listing tx that must be signed first.
- **Shipping creates real physical shipments.** Always confirm address and NFT selection with the user before calling `/redeem/prepare`.
- **Signed transactions are irreversible.** Verify NFT address, price, and wallet before broadcasting.
- **VRF rolls are final.** Once a pack is opened, the result cannot be changed or re-rolled.
- **Track B (SIWS) is crypto-only.** No card payment support. Wallets already linked to Privy accounts will get `409 Conflict`.
- **`userHasSol: false`** — use this flag when the user's wallet lacks SOL for transaction fees; the backend will pay gas. Also use it to recover from `INSUFFICIENT_FUNDS_RETRYABLE` broadcast errors.

## Known Limitations

- **Marketplace uses delegation, not escrow** — if a seller transfers their NFT elsewhere without canceling, the listing breaks silently. Always check listing validity before buying.
- **Field names differ across endpoints** — listing uses `nftAddress`, cancel-listing uses `tokenMint`, update-listing uses `tokenMint` + `newPrice` + `coin`. Always check the exact field names per endpoint above.
- **Gacha `packType` codes** are machine-specific (e.g., `pokemon_50`, `pokemon_250`). Use `GET /api/machines` to discover available pack types and current pricing.
- **No keyword search for gacha NFTs** — use `GET /api/getNfts` with `code` and `rarity` filters, or browse via `GET /api/machines`.
- **Swap is on-chain only** — no REST API wrapper; interact via Solana transactions against the Anchor program IDL.
- **Access tokens expire in 15 minutes** (Track B / SIWS) — implement refresh token rotation for long sessions.
- **eBay Bidder** has no public API documentation — it's a consumer-facing tool at `https://bid.collectorcrypt.com`.
- **Launchpads** are admin-managed drop pages — no public API for creating or configuring them.
- **Browse listings cache** — unauthenticated GET requests are cached for 5 seconds.
