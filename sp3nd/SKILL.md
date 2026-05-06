---
name: sp3nd
version: 1.0.0
description: Autonomously buy Amazon/eBay products with USDC on Solana via SP3ND x402 payments. Covers registration, cart creation, order placement, transaction construction, payment, and order confirmation.
tags: [solana, usdc, amazon, shopping, x402, payments]
metadata:
  starchild:
    emoji: "🛒"
    skillKey: sp3nd
user-invocable: false
disable-model-invocation: false
---

# SP3ND — Autonomous Amazon/eBay Shopping with USDC on Solana

SP3ND lets an AI agent buy real products from Amazon and eBay using USDC on Solana. No KYC, no accounts, 0% platform fee, free Prime shipping on eligible Amazon items.

**Full API docs:** https://sp3nd.shop/partner-api/docs
**SKILL.md:** https://sp3nd.shop/skill.md
**Base URL:** `https://us-central1-sp3nddotshop-prod.cloudfunctions.net`

---

## Prerequisites

- Solana wallet with USDC balance (mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`)
- `solders` and `solana` Python packages (`pip install solders solana`)
- SP3ND API credentials in `.env` (obtained via Step 1 below)

---

## Step 1: Register Agent (one-time)

Self-registration — no approval queue. Credentials are shown once; save immediately.

```python
import urllib.request, json

BASE_URL = "https://us-central1-sp3nddotshop-prod.cloudfunctions.net"
wallet_pubkey = "<your Solana wallet pubkey>"

payload = json.dumps({
    "agent_name": "My Agent",
    "solana_public_key": wallet_pubkey,
    "contact_email": "you@example.com",
    "description": "Autonomous shopping agent"
}).encode()

req = urllib.request.Request(
    f"{BASE_URL}/registerAgent",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req, timeout=15) as r:
    d = json.loads(r.read())
    print(d["api_key"], d["api_secret"])  # save both to .env
```

Save to `.env`:
```
SP3ND_API_KEY=sp3nd_...
SP3ND_API_SECRET=sp3nd_sec_...
```

---

## Step 2: Pick the Correct Amazon/eBay TLD

**Critical:** Use the marketplace TLD that matches the shipping country. Wrong TLD = failed order or wrong pricing.

### Amazon TLD by Region

| TLD | Countries covered |
|-----|------------------|
| `amazon.com` | US, and default fallback |
| `amazon.co.uk` | GB, IE |
| `amazon.de` | DE, AT, CH, and much of Europe |
| `amazon.fr` | FR |
| `amazon.it` | IT |
| `amazon.es` | ES |
| `amazon.nl` | NL, BE |
| `amazon.pl` | PL |
| `amazon.se` | SE |
| `amazon.com.tr` | TR |
| `amazon.co.jp` | JP |
| `amazon.com.au` | AU, NZ |
| `amazon.in` | IN |
| `amazon.sg` | SG, MY, TH, VN, ID, PH, MM, BN, KH, LA |
| `amazon.ae` | AE, OM, BH, KW, QA, JO, IQ, LB |
| `amazon.sa` | SA, YE |
| `amazon.eg` | EG |
| `amazon.com.br` | BR |
| `amazon.com.mx` | MX |
| `amazon.ca` | CA |

### eBay TLD by Region

| TLD | Countries |
|-----|-----------|
| `ebay.com` | US (default) |
| `ebay.co.uk` | GB |
| `ebay.de` | DE, AT, CH |
| `ebay.fr` | FR |
| `ebay.it` | IT |
| `ebay.es` | ES |
| `ebay.com.au` | AU |
| `ebay.ca` | CA |

---

## Step 3: Create Cart

```python
API_KEY    = os.environ["SP3ND_API_KEY"]
API_SECRET = os.environ["SP3ND_API_SECRET"]
HEADERS    = {"Content-Type": "application/json", "X-API-Key": API_KEY, "X-API-Secret": API_SECRET}

payload = json.dumps({
    "items": [{"product_url": "https://www.amazon.sg/dp/ASIN", "quantity": 1}]
}).encode()

req = urllib.request.Request(f"{BASE_URL}/createPartnerCart", data=payload, headers=HEADERS, method="POST")
with urllib.request.urlopen(req, timeout=20) as r:
    cart = json.loads(r.read())
    cart_id = cart["cart"]["cart_id"]
    total   = cart["cart"]["total_amount"]  # in USD = USDC amount needed
```

---

## Step 4: Create Order

```python
payload = json.dumps({
    "cart_id": cart_id,
    "customer_email": "you@example.com",   # required
    "shipping_address": {
        "name":          "Full Name",
        "address_line1": "Street address",
        "address_line2": "Unit/suburb",    # optional
        "city":          "City",
        "state":         "State/province",
        "zip":           "Postal code",
        "country":       "ISO 2-letter code (e.g. MY, US, GB)",
        "phone":         "+1234567890"
    }
}).encode()

req = urllib.request.Request(f"{BASE_URL}/createPartnerOrder", data=payload, headers=HEADERS, method="POST")
with urllib.request.urlopen(req, timeout=20) as r:
    order = json.loads(r.read())
    order_id     = order["order"]["order_id"]
    order_number = order["order"]["order_number"]
    total_amount = order["order"]["total_amount"]
```

---

## Step 5: Build & Sign the Payment Transaction

**This is the tricky part.** SP3ND uses x402 v2 protocol. When you call `payAgentOrder` it returns HTTP 402 with payment requirements. You must:

1. Find the treasury's **actual USDC token account** (ATA) on-chain — do NOT derive it, fetch it
2. Build a transaction with **two instructions**: USDC `transferChecked` + a **Memo** with `SP3ND Order: <order_number>`
3. The Memo is mandatory — without it SP3ND's webhook cannot match the payment to your order
4. Sign and broadcast directly via Solana RPC

```python
import base64, struct, urllib.request, json
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.message import Message
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta
from solana.rpc.api import Client

USDC_MINT   = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
TOKEN_PROG  = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
MEMO_PROG   = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
TREASURY    = "2nkTRv3qxk7n2eYYjFAndReVXaV7sTF3Z9pNimvp5jcp"
RPC_URL     = "https://api.mainnet-beta.solana.com"

def get_treasury_ata():
    """Fetch SP3ND treasury's actual USDC ATA on-chain. Do NOT derive — fetch."""
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [TREASURY, {"mint": USDC_MINT}, {"encoding": "jsonParsed"}]
    }).encode()
    req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read())
        return d["result"]["value"][0]["pubkey"]

def build_unsigned_tx(wallet_pubkey, our_ata, treasury_ata, amount_usdc_units, order_number):
    """Build unsigned tx: transferChecked + memo. amount_usdc_units = USDC * 1_000_000."""
    client = Client(RPC_URL)
    bh = client.get_latest_blockhash().value.blockhash

    wallet_pk  = Pubkey.from_string(wallet_pubkey)
    src        = Pubkey.from_string(our_ata)
    dst        = Pubkey.from_string(treasury_ata)
    mint       = Pubkey.from_string(USDC_MINT)
    token_prog = Pubkey.from_string(TOKEN_PROG)
    memo_prog  = Pubkey.from_string(MEMO_PROG)

    # Instruction 1: transferChecked (discriminator=12, u64 amount, u8 decimals=6)
    ix_transfer = Instruction(
        program_id=token_prog,
        accounts=[
            AccountMeta(pubkey=src,       is_signer=False, is_writable=True),
            AccountMeta(pubkey=mint,      is_signer=False, is_writable=False),
            AccountMeta(pubkey=dst,       is_signer=False, is_writable=True),
            AccountMeta(pubkey=wallet_pk, is_signer=True,  is_writable=False),
        ],
        data=bytes([12]) + struct.pack("<Q", amount_usdc_units) + bytes([6])
    )

    # Instruction 2: Memo — required for SP3ND webhook to match payment to order
    ix_memo = Instruction(
        program_id=memo_prog,
        accounts=[AccountMeta(pubkey=wallet_pk, is_signer=True, is_writable=False)],
        data=f"SP3ND Order: {order_number}".encode("utf-8")
    )

    msg = Message.new_with_blockhash([ix_transfer, ix_memo], wallet_pk, Hash.from_string(str(bh)))
    tx  = Transaction.new_unsigned(msg)
    return base64.b64encode(bytes(tx)).decode()
```

### Sign and broadcast (Starchild Privy wallet)

Starchild agents have a built-in Privy-managed Solana wallet. Use these two tools in sequence:

**Step 1 — Get the wallet address:**
```
wallet_info()  →  returns solana address (e.g. C4ffoATXA5j3UdyvP4UQ3vMuQ547G18bG2QqhSs5bDvb)
```

**Step 2 — Check USDC balance before building:**
```
wallet_sol_balance()  →  lists all SPL tokens including USDC
```

**Step 3 — Sign the unsigned tx:**
```
wallet_sol_sign_transaction(transaction=unsigned_b64)
→ returns { signed_transaction: "<base64>" }
```

**Step 4 — Broadcast via Solana RPC directly:**

⚠️ Do NOT use `wallet_sol_transfer` — it only handles native SOL, not SPL tokens. For USDC transfers you must broadcast the signed tx yourself via the Solana RPC.

```python
signed_b64 = "<signed_transaction from tool above>"

payload = json.dumps({
    "jsonrpc": "2.0", "id": 1,
    "method": "sendTransaction",
    "params": [signed_b64, {"encoding": "base64", "preflightCommitment": "confirmed"}]
}).encode()
req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    d = json.loads(r.read())
    tx_sig = d["result"]  # transaction signature
    print(f"https://solscan.io/tx/{tx_sig}")
```

**Finding your USDC token account (our_ata):**
```python
# Fetch your own USDC ATA on-chain — same pattern as treasury ATA lookup
payload = json.dumps({
    "jsonrpc": "2.0", "id": 1,
    "method": "getTokenAccountsByOwner",
    "params": [wallet_pubkey, {"mint": USDC_MINT}, {"encoding": "jsonParsed"}]
}).encode()
req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=10) as r:
    d = json.loads(r.read())
    our_ata = d["result"]["value"][0]["pubkey"]
    balance = d["result"]["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
```

---

## Step 6: Confirm Order Paid

Poll `getPartnerOrders` every ~5 seconds. SP3ND's Helius webhook detects the USDC + memo on-chain and marks the order Paid — typically within 60 seconds.

```python
import time

for _ in range(24):  # up to ~2 minutes
    req = urllib.request.Request(f"{BASE_URL}/getPartnerOrders", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        orders = json.loads(r.read())["orders"]
    order = next((o for o in orders if o["order_number"] == order_number), None)
    if order and order["status"] == "Paid":
        print("Order paid:", order["order_number"])
        break
    time.sleep(5)
```

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Wrong treasury ATA | Always fetch on-chain via `getTokenAccountsByOwner`, never derive |
| Missing memo instruction | Add `MemoSq4g...` instruction with `SP3ND Order: <order_number>` — without it USDC lands but order stays unpaid |
| `wallet_sol_transfer` for USDC | Won't work — build raw tx + `wallet_sol_sign_transaction` + broadcast via RPC |
| Wrong Amazon TLD for country | Use the TLD table in Step 2 — wrong TLD = failed order |
| Unsigned tx using derived ATA | Treasury's real ATA differs from derived ATA — fetch it |
| Missing `customer_email` in order | Required field — `createPartnerOrder` returns 400 without it |
| Cart expiry | Carts expire after 30 minutes — place order promptly |

---

## Fee Structure

- Platform fee: **0%** by default
- Payment: USDC on Solana (6 decimals, multiply USD amount by 1,000,000)
- Amazon: free Prime shipping on eligible items
- eBay: per-item shipping set by seller

## Key Addresses

| Item | Value |
|------|-------|
| SP3ND treasury | `2nkTRv3qxk7n2eYYjFAndReVXaV7sTF3Z9pNimvp5jcp` |
| USDC mint (Solana) | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` |
| x402 facilitator | `https://facilitator.payai.network` |
| Support | support@sp3nd.shop |
