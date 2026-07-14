---
name: bnbagent
version: 1.1.0
description: Build and operate on-chain AI agents on BNB Chain using the bnbagent Python SDK — register agent identities (ERC-8004), and transact through escrowed agentic commerce (ERC-8183) as a provider (accept jobs, deliver work, get paid) or client (create, fund, dispute, refund jobs). Also covers x402 micropayment signing. Use for anything involving BNB Chain agent identity, agent-to-agent paid jobs, BSC escrow jobs, or ERC-8004/ERC-8183/x402.
metadata: {"starchild":{"emoji":"🟨","requires":{"pips":["bnbagent"]},"install":[{"kind":"pip","package":"bnbagent==0.4.0"}]}}
---

# BNBAgent SDK

Python SDK (`pip install bnbagent`, Python 3.10+) for on-chain AI agents on BNB Chain. Two independent capabilities:

- **ERC-8004 (identity)** — register an agent on-chain as an ERC-721 identity token with a discoverable profile URI. Gas-free on BSC Testnet via MegaFuel paymaster.
- **ERC-8183 (agentic commerce)** — trustless job escrow between a **client** (pays) and a **provider** (delivers). Optimistic settlement: silence past the dispute window = approval; a client dispute triggers a whitelisted-voter quorum reject.

They are independent: you can run ERC-8183 jobs without ERC-8004 registration (registration is only recommended for discovery).

> Active development — breaking changes possible. Tested with `bnbagent==0.4.0`; verify install with `python -c "import bnbagent; print(bnbagent.__version__)"`. Optional extra: `pip install "bnbagent[ipfs]"` for IPFS/Pinata deliverable storage.

## ⚠️ Mainnet economics — read BEFORE any mainnet commerce

- **The payment token is U (United Stables)** `0xcE24439F2D9C6a2289F741120FE202248B666666` — not BNB, not USDT/USDC. There is no faucet for it: acquire U on PancakeSwap (a WBNB–U pair exists). The client must hold U **before** calling `fund()`. Fetch decimals at runtime via `erc8183.token_decimals()` — don't assume.
- **ERC-8183 writes on mainnet are never gas-sponsored.** Client and provider both need BNB for gas (only ERC-8004 identity registration is sponsored on mainnet).
- **The mainnet dispute window is 604800s (7 days).** A happy path cannot reach `COMPLETED` in one session — silence-approval only kicks in after the window. Plan a **partial E2E** (through `SUBMITTED`) and settle later via a cron/operator script (`examples/auto_settle.py`). `settle` reverting with `policy pending` during this week is expected, not an error.

### Preflight balance checklist (mainnet)

| Party | Needs | Why |
|-------|-------|-----|
| Client | BNB | gas for `createJob`/`registerJob`/`setBudget`/`approve`/`fund` (+ optional swap gas) |
| Client | U | the job budget escrowed by `fund` (+ small residual for retries) |
| Provider | BNB | gas for `submit` — not sponsored on mainnet |
| Settler (anyone) | BNB | gas for `settle` after the window |

## Decide what you're doing

| Goal | Use | Reference |
|------|-----|-----------|
| Register agent identity on-chain | `ERC8004Agent` | quick start below |
| Earn: accept + deliver funded jobs | `ERC8183JobOps` + `funded_job_watcher` | quick start below, `examples/agent-server/`, `examples/a2a-agent/` |
| Pay: create/fund/settle jobs | `ERC8183Client` | quick start below, `examples/client/` |
| Vote on disputes (whitelisted voter) | `PolicyClient.vote_reject` | `examples/voter/` |
| Pay HTTP 402 challenges (x402) | `X402Signer` / twak delegated payer | `examples/x402/`, `references/twak.md` |
| Understand internals / extend | — | `references/architecture.md` |
| Wallet backends (EVM keystore vs twak) | `EVMWalletProvider` / `TWAKProvider` | `references/wallets.md`, `references/twak.md` |

## Quick start: register an agent (ERC-8004)

One-time setup. Needs a private key (auto-generated if omitted) and `WALLET_PASSWORD`.

```python
import os
from bnbagent import ERC8004Agent, AgentEndpoint, EVMWalletProvider

wallet = EVMWalletProvider(
    password=os.getenv("WALLET_PASSWORD"),
    private_key=os.getenv("PRIVATE_KEY"),  # only needed on first run; keystore persists to ~/.bnbagent/wallets/
)
sdk = ERC8004Agent(network="bsc-testnet", wallet_provider=wallet)

agent_uri = sdk.generate_agent_uri(
    name="my-ai-agent",
    description="AI agent for document processing",
    endpoints=[
        AgentEndpoint.a2a("https://my-agent.example.com"),                      # A2A first (discovery doc URL)
        AgentEndpoint.mcp("https://my-agent.example.com/mcp", version="2025-06-18"),  # MCP second, if served
    ],
)
result = sdk.register_agent(agent_uri=agent_uri)
# result["agentId"], result["transactionHash"]
```

## Quick start: provider (earn loop, headless)

No server needed. Watch for funded jobs, do the work, submit:

```python
import asyncio
from bnbagent import EVMWalletProvider
from bnbagent.erc8183 import ERC8183JobOps, funded_job_watcher
from bnbagent.storage import LocalStorageProvider

wallet = EVMWalletProvider(password="...", private_key="0x...")
ops = ERC8183JobOps(
    wallet,
    network="bsc-testnet",
    storage_provider=LocalStorageProvider(),
    service_price=1_000_000_000_000_000_000,      # min acceptable budget, raw units (18 decimals here)
    agent_url="http://localhost:8003/erc8183",    # public URL; required for file:// deliverable rewriting
)

async def on_funded(job: dict) -> None:
    deliverable = f"Processed: {job['description']}"   # your business logic
    await ops.submit_result(job["jobId"], deliverable)

asyncio.run(funded_job_watcher(ops, on_funded, interval=30))
```

- `submit_result` handles verification (FUNDED status, assignment, expiry, budget ≥ service_price), deliverable upload, manifest hashing, and the `submit` tx.
- The watcher never submits or settles by itself. **Settlement is a separate step** — run an operator script calling `ERC8183Client.settle(job_id)` after the dispute window elapses (`examples/auto_settle.py`, `examples/agent-server/scripts/settle.py`).
- `job` dict fields: `jobId`, `description`, `budget`, `client`, `provider`, `evaluator`, `status` (always `FUNDED`), `expiredAt`, `hook`.
- Serving surface (A2A/MCP/HTTP) is your choice — copy-and-own references in `examples/a2a-agent/` (recommended) and `examples/agent-server/` (FastAPI).
- Deliverable storage: placeholder URLs like `https://example.invalid/manifest.json` (as in `examples/client/happy.py`) are **chain-only demos — voters cannot verify the deliverable**. For anything a client might dispute, use real storage (`LocalStorageProvider` behind a public `ERC8183_AGENT_URL`, or `IPFSStorageProvider`).

## Quick start: client (create and pay for a job)

```python
import time
from bnbagent.erc8183 import ERC8183Client, JobStatus
from bnbagent.wallets import EVMWalletProvider

wallet = EVMWalletProvider(password="...", private_key="0x...")
erc8183 = ERC8183Client(wallet, network="bsc-testnet")

budget = 1 * (10 ** erc8183.token_decimals())   # DEMO-SCALE (1 full token). On MAINNET use tiny
                                                # budgets, e.g. (10 ** dec) // 100 for 0.01 U.
expired_at = int(time.time()) + 65 * 60

job_id = erc8183.create_job(provider=provider_addr, expired_at=expired_at, description="task")["jobId"]
erc8183.register_job(job_id)          # bind default policy (OptimisticPolicy)
erc8183.set_budget(job_id, budget)
erc8183.fund(job_id, budget)          # escrows; auto-approves payment token with 100-token floor

# ... provider submits ... dispute window elapses ...
erc8183.settle(job_id)                # permissionless — anyone can call
assert erc8183.get_job_status(job_id) == JobStatus.COMPLETED
```

Disputes and escape hatch:

```python
erc8183.dispute(job_id)        # client only, within dispute window after submit
erc8183.vote_reject(job_id)    # whitelisted voters only, after dispute; quorum flips verdict to REJECT
erc8183.claim_refund(job_id)   # anyone, after expiredAt if never settled — non-pausable escape hatch
```

`fund(job_id, amount, approve_floor=None)`: default approves `max(amount, 100 * 10**decimals)` to avoid re-approving across job streams; `approve_floor=0` approves exactly `amount`; no approve is sent if allowance already covers it.

## Job lifecycle

```
OPEN ──► FUNDED ──► SUBMITTED ──┬─ silence past window ──► COMPLETED (provider paid, minus platform fee)
  │         │                   ├─ dispute + quorum reject ──► REJECTED (client refunded)
  │         │                   └─ no verdict + past expiredAt ──► EXPIRED (client claimRefund)
  │         └─ past expiredAt ──► EXPIRED (claimRefund)
  └─ client reject() before funding ──► REJECTED
```

## Gas sponsorship matrix

| Protocol / write | BSC Testnet | BSC Mainnet |
|------------------|-------------|-------------|
| ERC-8004 `register_agent` | ✅ sponsored (MegaFuel) | ✅ sponsored (MegaFuel) — works with a zero-BNB wallet |
| ERC-8183 create/fund/submit/settle | 🟡 per-call: MegaFuel decides (`fund`/`settle` sponsored today); declined calls self-pay | ❌ never sponsored — all writes self-pay BNB |
| ERC-20 `approve` of payment token (sent inside `fund` when allowance short) | ❌ always self-pays — fresh testnet buyer needs a little tBNB | ❌ self-pays |
| twak wallet ops | ❌ twak self-pays (twak-internal, SDK has no control) | ✅ twak auto-sponsors — see `references/twak.md` |

## Networks & contracts

**BSC Testnet (chain 97)** — faucets: [tBNB](https://www.bnbchain.org/en/testnet-faucet), [U tokens](https://united-coin-u.github.io/u-faucet/)

| Contract | Address |
|----------|---------|
| Identity Registry (ERC-8004) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| AgenticCommerce | `0xa206c0517b6371c6638cd9e4a42cc9f02a33b0de` |
| EvaluatorRouter | `0xd7d36d66d2f1b608a0f943f722d27e3744f66f25` |
| OptimisticPolicy | `0x4f4678d4439fec812ac7674bb3efb4c8f5fb78a6` |

**BSC Mainnet (chain 56)**

| Contract | Address |
|----------|---------|
| Identity Registry (ERC-8004) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| AgenticCommerce | `0xea4daa3100a767e86fded867729ae7446476eba6` |
| EvaluatorRouter | `0x51895229e12f9876011789b04f8698af06ccd6da` |
| OptimisticPolicy | `0x9c01845705b3078aa2e8cff7520a6376fd766de5` |

The payment token address is NOT configurable — it is read from the Commerce kernel at runtime (`ERC8183Client.payment_token`). On mainnet it resolves to **U (United Stables)** `0xcE24…6666` (see the mainnet economics section at the top).

Notes:
- The SDK constructor defaults to `network="bsc-testnet"` — always pass `network="bsc-mainnet"` explicitly (or `NETWORK=bsc-mainnet`) for mainnet work, and print `bscscan.com` (not `testnet.bscscan.com`) explorer links; some example scripts hardcode testnet URLs.
- Discovery/indexer lag: the registry index may show a generic name (e.g. `Agent #198565`) even when your URI carries the real name. The **on-chain URI is the source of truth**; indexer names can lag or stay generic.

## Environment variables

Full annotated reference: `references/env.example`. The essentials:

| Variable | Required | Notes |
|----------|----------|-------|
| `WALLET_PASSWORD` | Yes | Encrypts/decrypts the keystore at `~/.bnbagent/wallets/`. |
| `PRIVATE_KEY` | First run only | Imported and encrypted, then removable. Auto-generates a wallet if absent. |
| `WALLET_ADDRESS` | No | Pick a keystore when several exist. |
| `NETWORK` | No (`bsc-testnet`) | Or `bsc-mainnet`. |
| `RPC_URL` | No | Custom RPC endpoint. |
| `ERC8183_SERVICE_PRICE` | No (`1e18`) | Provider's minimum budget, raw units. |
| `ERC8183_AGENT_URL` | If LocalStorageProvider | Public base URL incl. `/erc8183`; `file://` deliverable URLs get rewritten to it. |
| `STORAGE_API_KEY` | If IPFSStorageProvider | Pinata-compatible JWT. |
| `STORAGE_LOCAL_PATH` | No (`.agent-data`) | Local deliverable dir. |

Storage backend is chosen **in code** (pass `storage_provider=`), not by env var.

## Security rules (important for agent flows)

- **EIP-712 signing is policy-gated by default.** `EVMWalletProvider.sign_typed_data` only accepts EIP-3009 `TransferWithAuthorization`/`ReceiveWithAuthorization` against U-token on BSC 56/97. EIP-2612 `Permit` and Permit2 `PermitSingle`/`PermitBatch` are **denylisted unconditionally** (they grant unbounded allowances — a malicious 402 server could drain the wallet). Never try to bypass this in agent-reachable code; `SigningPolicy.permissive()` and `_DANGEROUS_sign_typed_data_no_policy()` are tests-only.
- **Never hand tool functions a raw `WalletProvider`.** Give them a scoped `X402Signer(wallet, max_value_per_call={token: ...}, session_budget={token: ...})` and always pass `expected_to` from config/on-chain registry — never from the 402 challenge body.
- Custom tokens/types: `SigningPolicy.strict_default().extend(domain_allowlist={(chain_id, contract)}, primary_type_allowlist={"MyType"})` — the Permit denylist still wins.
- `claimRefund` is non-pausable and non-hookable: funds are always recoverable past `expiredAt`.
- **Throwaway/demo keys**: use `EVMWalletProvider(persist=False)` so one-off keys never touch disk, and never reuse demo keys in production. Never paste production private keys into chat/logs — prefer the keystore + `WALLET_PASSWORD` flow.

Full rationale, decision tree, and examples: `references/sdk-readme.md` (Security section) and `examples/security/e2e.py`.

## Wallet backends

- **`EVMWalletProvider`** (default) — Keystore V3 (MetaMask/Geth compatible), persistent at `~/.bnbagent/wallets/` or in-memory with `persist=False`.
- **`TWAKProvider`** (Trust Wallet Agent Kit) — self-custody, self-broadcasting; no raw-tx or generic EIP-712 signing; BSC only; x402 via delegated payer `make_x402_payer()`. **Read `references/twak.md` before using** — unsupported calls raise `UnsupportedWalletOperation`. Swap: `TWAKProvider(chain="bsc")` or `WALLET_KIND=twak`.
- Custom (HSM, MPC, KMS): subclass `WalletProvider`. Details: `references/wallets.md`.

### AA / self-broadcast wallets (Privy, ZeroDev, etc.) — known integration tax

Account-abstraction wallets that submit Intents/UserOperations instead of raw signed transactions are **not first-class** in the SDK yet (field-tested on BSC mainnet with a Privy AA client, `bnbagent==0.4.0`). What to expect and the workarounds that worked:

- **ERC-20 `approve` fails**: `approve_payment_token` goes through `_send_tx` → raw `sign_transaction`, which AA wallets don't implement (`sign.transaction: wallet does not implement raw-transaction signing`). Workaround: do the `approve(commerce, amount)` on the payment token manually through your AA stack, then call `fund` with `fund_bundles_approval=True`. `create_job`/`set_budget`/`fund` themselves work through a custom Intent executor (subclass the executor / `WalletProvider`).
- **`jobId` comes back `None` after `create_job`**: AA wallets return a `user_operation_hash`, not a tx hash, and `create_job` only parses `jobId` from receipt logs. Workaround: wait for inclusion, then scan `jobCounter` backwards (or index recent jobs by `client` + `provider` + `description`) to find your job.
- For a documented self-broadcasting wallet, use `TWAKProvider` (`references/twak.md`); Privy-style adapters are currently build-your-own.

## Troubleshooting

| Error | Cause → Fix |
|-------|-------------|
| `No PRIVATE_KEY and no keystore found` | New wallet auto-generated, or set `PRIVATE_KEY` to import. |
| `Multiple wallets found` | Set `WALLET_ADDRESS=0x...`. |
| `403 Provider mismatch` | Job assigned to a different provider — check `job.provider`. |
| `409 Not FUNDED` | Job already submitted/settled. |
| `408 Job expired` | Past `expiredAt`; client can `claimRefund`, create a new job. |
| `402 Budget below service price` | Client must fund ≥ `ERC8183_SERVICE_PRICE`. |
| `settle` reverts `policy pending` | Dispute window not elapsed and no dispute — wait, then retry. On mainnet the window is **7 days**. |
| `voteReject` reverts `not voter`/`not disputed` | Caller not whitelisted or no dispute — use `examples/voter/vote_reject.py`. |
| Revert selector `0xcdbc1d27` on `register_job` | Job already bound to a policy — re-registering reverts by design. Treat as success if `job_policy(job_id)` is already set. |
| `sign.transaction: wallet does not implement raw-transaction signing` | AA/self-broadcast wallet hit the raw-tx `approve` path — see AA wallet section above. |
| `jobId` is `None` after `create_job` | AA wallet returned a user-op hash, no receipt to parse — scan `jobCounter` backwards for your job. |
| Allowance stays 0 after `fund` attempt | The bundled `approve` never landed (wrong wallet path) — manually `approve(commerce, amount)`, then `fund`. |

## Files in this skill

- `references/sdk-readme.md` — full upstream SDK README (deep detail on everything above)
- `references/architecture.md` — code map, layering, invariants
- `references/twak.md` — TWAK wallet support matrix and boundaries
- `references/wallets.md` — wallet provider deep dive
- `references/env.example` — annotated env var reference
- `examples/` — copy-and-own scripts: `client/` (5 canonical job flows), `a2a-agent/`, `agent-server/`, `voter/`, `twak/`, `x402/`, `security/`, `auto_settle.py`
