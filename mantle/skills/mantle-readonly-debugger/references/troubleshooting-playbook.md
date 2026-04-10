# Troubleshooting Playbook

Follow this sequence to keep diagnostics structured and repeatable.

## Step 1: Reproduce and capture

- Re-run failing read with same parameters once.
- Record endpoint, method, params hash, timestamp (UTC), and exact error text.
- Record chain ID and block tag used.

## Step 2: Branch by issue type

### RPC exception branch

1. Check endpoint health and rate-limit signals.
2. Retry with bounded backoff.
3. Switch to fallback endpoint.
4. Compare outcomes across endpoints.

### Quote failure branch

1. Verify token addresses and decimals.
2. Verify input amount scaling.
3. Probe smaller notional size.
4. Try alternate liquidity source.

### Balance mismatch branch

1. Compare reads at `latest` and `pending`.
2. Check for unconfirmed tx and nonce conflicts.
3. Reconcile token decimals and symbol/address mapping.
4. Re-read at consistent block context.

## Step 3: Conclude with bounded claim

- State likely root cause as hypothesis plus confidence.
- Provide smallest next action.
- If unresolved after bounded retries, escalate with captured evidence.

## Escalation package

- Full raw error strings
- Endpoint list tested
- Request fingerprints (without private keys/secrets)
- Timestamped observations
- What was ruled out
