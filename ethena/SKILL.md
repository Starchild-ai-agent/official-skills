---
name: ethena
version: 1.2.0
description: "Ethena protocol integration — stake USDe for sUSDe yield, unstake with cooldown, check staking rates. Use when user mentions Ethena, USDe, sUSDe, or wants stablecoin yield."

metadata:
  starchild:
    emoji: "🟣"
    skillKey: ethena

user-invocable: true
---

## ⛔ HARD RULES (read first, always)

- **ALWAYS** call `ethena_rate` before any on-chain operation — cooldown duration is live from chain, not a constant
- **NEVER** call `wallet_transfer` directly — use `ethena_*` native tools only (wallet_transfer triggers UI block in deny-all policy)
- **NEVER** hardcode cooldown as "7 days" — actual value is fetched per request (currently ~24h)
- **NEVER** guess or assume the sUSDe/USDe exchange rate — call `ethena_rate`
- **HARD LIMIT**: max 5 tool calls per user request
- **ON-CHAIN EXECUTION**: after `ethena_*` returns calldata, sign and broadcast via `wallet_sign_transaction` — NEVER skip or simulate

---

# Ethena — USDe Staking

Ethena lets users stake USDe to receive sUSDe, an ERC4626 yield-bearing token. Rewards accrue from ETH staking + funding rate delta-hedging. sUSDe value only increases or stays flat — never decreases.

## Key Contracts (Ethereum Mainnet)

| Contract | Address |
|----------|---------|
| USDe | `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3` |
| sUSDe (StakedUSDe) | `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497` |
| USDeSilo (cooldown) | `0x7FC7c91D556B400AFa565013E3F32055a0713425` |

## Native Tools

| Tool | When to use | Returns |
|------|-------------|---------|
| `ethena_rate()` | Rate query, before any tx, cooldown check | rate, totalAssets, totalSupply, cooldown_seconds |
| `ethena_apy()` | APY / yield / return question | apy_current, apy_7d, apy_30d, tvl_usd |
| `ethena_balance(wallet)` | Balance check | usde_balance, susde_balance, cooldown_end_ts |
| `ethena_stake(amount, receiver)` | Stake USDe | 2 tx calldata (approve + deposit) |
| `ethena_cooldown_start(amount)` | Start unstake | cooldown tx calldata + live cooldown_hours |
| `ethena_unstake(receiver)` | Claim after cooldown | unstake tx calldata |

## End-to-End Execution — Sign & Broadcast

`ethena_*` tools return **unsigned calldata**. To actually execute on-chain:

```
ethena_stake / ethena_cooldown_start / ethena_unstake
        ↓  returns tx dict  {to, data, value, chain_id}
wallet_sign_transaction(tx)          ← wallet skill
        ↓  returns signed_tx hex
wallet_sign_transaction broadcast    ← same call, auto-broadcasts
```

### Standard Flow (stake example)

```
Step 1  ethena_rate()                    # confirm rate + cooldown before tx
Step 2  ethena_stake("100", receiver)    # returns [approve_tx, deposit_tx]
Step 3  wallet_sign_transaction(approve_tx, broadcast=True)
Step 4  wallet_sign_transaction(deposit_tx, broadcast=True)
```

### Standard Flow (unstake)

```
Step 1  ethena_rate()                    # get live cooldown duration
Step 2  ethena_cooldown_start("100")     # returns cooldown_tx
Step 3  wallet_sign_transaction(cooldown_tx, broadcast=True)
Step 4  [wait cooldown_hours]
Step 5  ethena_unstake(receiver)         # returns unstake_tx
Step 6  wallet_sign_transaction(unstake_tx, broadcast=True)
```

### Cross-skill dependency

Load **wallet-policy** skill first to confirm wildcard policy is active. `wallet_sign_transaction` is part of the **wallet** skill — it is available natively; no extra install needed.

### Error handling

| Error | Cause | Fix |
|-------|-------|-----|
| 403 on sign | Privy policy deny-all | Approve wildcard policy in Web UI |
| nonce conflict | Two txs broadcast too fast | Wait for Step 3 receipt before Step 4 |
| gas estimate fail | Approve not mined yet | Add 5s delay between approve and deposit |

## Tool Routing — IF/THEN

```
IF "APY" OR "yield" OR "return" OR "收益率" OR "年化"
  → ethena_apy()

IF "rate" OR "price" OR "how much USDe per sUSDe" OR "汇率" OR "多少USDe"
  → ethena_rate()

IF "balance" OR "how much do I have" OR "余额"
  → ethena_balance(wallet_address)

IF "stake" OR "deposit" OR "质押" AND amount given
  → ethena_stake(amount, receiver)

IF "unstake" OR "redeem" OR "cooldown" OR "withdraw" OR "赎回" — starting flow
  → ethena_cooldown_start(amount)

IF "claim" OR "unstake" OR "withdraw" AND cooldown already done
  → ethena_unstake(receiver)

IF "how long" OR "cooldown duration" OR "等多久"
  → ethena_rate()  ← returns cooldown_seconds live from chain
```

## Few-Shot Examples

**ETH-01 — APY query**
> "sUSDe 现在的 APY 是多少？"
```
ethena_apy()
→ "当前 APY 3.72%，7日均值 3.68%"
```

**ETH-02 — Rate query**
> "1 sUSDe 能换多少 USDe？"
```
ethena_rate()
→ "1 sUSDe = 1.227675 USDe（totalAssets/totalSupply 实时计算）"
```

**ETH-03 — Balance**
> "我有多少 USDe 和 sUSDe？"
```
ethena_balance("0x...")
→ {usde_balance: 500.0, susde_balance: 81.46, susde_in_usde: 100.0}
```

**ETH-04 — Stake**
> "帮我质押 100 USDe"
```
ethena_rate()          # get live rate for estimate
ethena_stake("100", receiver="0x...")
→ [{approve tx}, {deposit tx}]  # execute in order
```

**ETH-04b — Stake end-to-end (sign & broadcast)**
> "帮我质押 100 USDe，直接执行到链上"
```
ethena_rate()                                   # Step 1: confirm rate
ethena_stake("100", receiver="0x...")           # Step 2: get calldata
→ [approve_tx, deposit_tx]
wallet_sign_transaction(approve_tx, broadcast=True)   # Step 3
wallet_sign_transaction(deposit_tx, broadcast=True)   # Step 4
→ tx_hash confirmed
```

**ETH-06b — Unstake end-to-end (sign & broadcast)**
> "帮我开始赎回 50 sUSDe，直接发链上"
```
ethena_rate()                                         # Step 1: get cooldown
ethena_cooldown_start("50")                           # Step 2: get calldata
→ {cooldown_tx, cooldown_hours: 24.0}
wallet_sign_transaction(cooldown_tx, broadcast=True)  # Step 3
→ tx_hash confirmed, 等待 24h 后再调 ethena_unstake
```

**ETH-05 — Cooldown duration**
> "赎回要等多久？"
```
ethena_rate()
→ "cooldown_seconds: 86400 → 当前需等待 24 小时"
```

**ETH-06 — Start cooldown**
> "开始赎回 50 USDe 的 sUSDe"
```
ethena_cooldown_start("50")
→ {transaction: {...}, cooldown_hours: 24.0}
```

**ETH-07 — Claim after cooldown**
> "cooldown 到了，帮我提款"
```
ethena_unstake("0x...")
→ {transaction: {...}}
```

**ETH-08 — English yield query**
> "What's the current yield for staking USDe?"
```
ethena_apy()
→ "Current APY: 3.72%"
```

## How Staking Works

1. **Stake**: `ethena_stake` → approve USDe + deposit → receive sUSDe (ERC4626)
2. **Yield**: Protocol transfers USDe rewards every 8h, linearly vested over 8h (anti-sandwich)
3. **Unstake**: `ethena_cooldown_start` → wait cooldown (query live, currently ~24h) → `ethena_unstake`

sUSDe/USDe rate only goes up. Cooldown duration may change — always query `ethena_rate`.

After generating calldata via any `ethena_*` tool, **always follow up with `wallet_sign_transaction(tx, broadcast=True)`** to actually submit on-chain. Never stop at calldata generation.

## Prerequisites — Wallet Policy

Before any on-chain operation, ensure a wildcard wallet policy is active (deny key export + allow `*`). Load the **wallet-policy** skill if needed.

## Gotchas

- **Cooldown is ~24h** (not 7 days) — but always verify with `ethena_rate()` as it can change via governance
- **No negative rewards** — sUSDe value can only go up or stay flat
- **Rewards every 8h** — linearly vested, no sandwich opportunities
- sUSDe can be sold on DEXes without cooldown if liquidity exists
- **EU/EEA restriction** — sUSDe acquisition not offered in EU/EEA
