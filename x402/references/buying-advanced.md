# x402 Buying Reference — signer details & funding the session EOA

Read this BEFORE using the session EOA signer, funding a buyer wallet, or
paying on a chain/token other than Base mainnet USDC.

## Signer internals

**Buyer signer = Privy wallet by default** (`signer_mode="auto"`).
The Privy wallet may be a smart account (delegated code at the address):
the client detects this and signs through an ERC-1271-compatible path
automatically — no configuration needed. It requires a facilitator with
ERC-1271 verify support (the platform facilitator has it). Do NOT revoke
the wallet's delegation: it is installed by the gas-sponsorship flow and
revoking it breaks sponsored transactions. Exact wrapping details live in
`client.py` (PrivySigner) comments.
Fallback signer = session EOA (`.x402/buyer.key`). `auto` is FAIL-CLOSED:
if the Privy signer cannot be initialized, `paid_request` raises instead of
paying from a different identity. Allow the EOA fallback only explicitly —
`allow_fallback_eoa=True`, env `X402_FALLBACK_EOA=1`, or pin
`signer_mode="eoa"` / env `X402_SIGNER=eoa`. Every result includes
`signer_type` (`"privy"` | `"session_eoa"`); an opted-in fallback also sets
`signer_warning`.
⚠️ The two signers are DIFFERENT payer identities: subscriptions / prepaid
balances bought under one do NOT carry over — pin `signer_mode` explicitly
for subscription/prepaid services.
If using the session EOA, fund it with a small USDC budget from the Privy
wallet (ERC20 transfer); the budget IS the hard spend cap.

**Funding the session EOA (when target-chain balance is 0):** signature
verification passes with an empty wallet — settlement then fails with
`invalid_exact_evm_insufficient_balance`. Check before paying, and bridge if
the user's funds sit on a different chain:

1. Snapshot all chains: `wallet_get_all_balances()` (wallet skill).
2. USDC on the wrong chain → move it to the service's network first
   (cross-chain: okx / bridge skills; same-chain swap: 1inch / openocean).
3. Privy → session EOA on the target chain via `wallet_transfer` — an ERC20
   transfer is a CONTRACT call, not a native send: `to` = the token contract
   (Base USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`), `amount` = 0,
   `data` = transfer calldata `0xa9059cbb` + recipient (the session EOA,
   zero-padded to 32 bytes) + atomic amount (32 bytes). Build it:
   `"0xa9059cbb" + eoa[2:].lower().zfill(64) + hex(atomic)[2:].zfill(64)`.
   Setting `to` = the EOA directly sends NATIVE currency instead — wrong tx.
   (The EOA address is printed by client.py on first run.)
4. Re-check the EOA balance, then `paid_request(...)`.
5. No USDC anywhere → stop and tell the user to acquire some (on-ramp /
   exchange withdrawal). Never fabricate funds or skip the payment.

**Signer selection:** `auto` FAILS CLOSED on any PrivySigner init failure —
most commonly `ImportError: core.skill_tools` when PYTHONPATH lacks `/app`
(script run outside the agent runtime), or wallet-service signing errors
(e.g. 401) — raising before anything is signed. Fix the cause, or explicitly
allow the session-EOA fallback via `allow_fallback_eoa=True` /
env `X402_FALLBACK_EOA=1`; an opted-in fallback logs a `[x402] auto: ...`
stderr warning and sets `signer_type`/`signer_warning` in the result —
check them to confirm which identity actually paid. Base mainnet USDC works
with both signers; verify other chain/token combos with a minimal purchase
first. Paid response bodies are returned in FULL; unpaid/error bodies are
capped at 2000 chars (override: env `X402_BODY_MAX`, 0 = unlimited). **Spend guard**: additionally refuses to sign above
`X402_MAX_ATOMIC` (default 1_000_000 = 1 USDC). ⚠️ Signing = spending real
money once settled — confirm with the user before paying unfamiliar services
or raising the cap. Result includes `settlement.transaction` (on-chain tx hash)
— report it and verify per transaction-verification rules.
