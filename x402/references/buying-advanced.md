# x402 Buying Reference — signer details & funding the session EOA

Read this BEFORE paying, funding the buyer wallet, or paying outside the
supported buyer rails (EVM mainnet USDC/USDG exact).

## Signer internals

**Buyer signer = the session EOA** (`.x402/buyer.key`, created on first
use, mode 600). `signer_mode` `"auto"` and `"eoa"` both select it; every
result includes `signer_type: "session_eoa"`. It is a plain EOA (no code),
so it signs pure ECDSA that USDC's `transferWithAuthorization` accepts. It
cannot sign Solana — Solana accepts are never paid.
Fund it with a small USDC budget (ERC20 transfer from any wallet the user
controls); the budget IS the hard spend cap.

**Funding the session EOA (when target-chain balance is 0):** signature
verification passes with an empty wallet — settlement then fails with
`invalid_exact_evm_insufficient_balance`. Check before paying, and bridge if
the user's funds sit on a different chain:

Supported buyer stablecoin rails (EIP-3009 exact, settle by service facilitator) —
source of truth: `bazaar.PAYABLE_USDC` /
`bazaar.NETWORK_PREFERENCE` (prefer Base when multi-accept):
- Base `8453` USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- Polygon `137` USDC `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- Arbitrum `42161` USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- World Chain `480` USDC `0x79A02482A880bCE3F13e09Da970dC34db4CD24d1`
- Monad `143` USDC `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- Robinhood `4663` USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` (Global Dollar, Diamond proxy — non-standard EIP-712 domain)
- Avalanche `43114` USDC `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- Ethereum `1` USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- Optimism `10` USDC `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- Linea `59144` USDC `0x176211869cA2b568f2A7D4EE941E073a821EE1ff`
- Celo `42220` USDC `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- Unichain `130` USDC `0x078D782b760474a361dDA0AF3839290b0EF57AD6`
- X Layer `196` USDC `0x74b7f16337b8972027f6196a17a631ac6de26d22`
Not yet: Solana, EURC / other non-USDC stables, testnets.

1. Get the EOA address and live balances: `python3 skills/x402/scripts/preflight.py`
   (`payer.evm` + `balances` per rail).
2. Ask the user to send USDC to that address on the service's network (an
   ERC20 transfer of the token above — not a native-currency send). If their
   USDC sits on another chain, they bridge it first.
3. Re-check with `preflight.py`, then `paid_request(...)`.
4. No USDC anywhere → stop and tell the user to acquire some (on-ramp /
   exchange withdrawal). Never fabricate funds or skip the payment.

Verify chain/token combos other than Base USDC with a minimal purchase
first. Paid response bodies are returned in FULL; unpaid/error bodies are
capped at 2000 chars (override: env `X402_BODY_MAX`, 0 = unlimited). **Spend guard**: additionally refuses to sign above
`X402_MAX_ATOMIC` (default 1_000_000 = 1 USDC). ⚠️ Signing = spending real
money once settled — confirm with the user before paying unfamiliar services
or raising the cap. Result includes `settlement.transaction` (on-chain tx hash)
— report it and verify per transaction-verification rules.
