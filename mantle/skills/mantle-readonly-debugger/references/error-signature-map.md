# Error Signature Map

Use this table to classify frequent read-path failures quickly.

## RPC transport/connectivity

- Symptoms:
  - timeout
  - connection reset
  - HTTP 429/503
- Likely causes:
  - provider saturation
  - rate limit
  - unstable endpoint
- First actions:
  - retry with backoff
  - switch to fallback RPC
  - reduce batch size/request rate

## Call/revert errors

- Symptoms:
  - `execution reverted`
  - `CALL_EXCEPTION`
  - empty return data where data expected
- Likely causes:
  - wrong contract address
  - wrong ABI/function selector
  - invalid params or state preconditions
- First actions:
  - verify target address/ABI
  - dry-run minimal input
  - decode revert data if available

## Quote failures

- Symptoms:
  - DEX aggregator quote returns null/error
  - path not found
  - amount out equals zero
- Likely causes:
  - insufficient liquidity
  - unsupported route/token pair
  - wrong decimals/input units
- First actions:
  - validate token decimals and amount scaling
  - try smaller size
  - try alternate route/source

## Balance inconsistencies

- Symptoms:
  - wallet balance differs across reads
  - expected post-action balance not visible
- Likely causes:
  - pending transactions
  - nonce contention
  - stale block tag/source lag
- First actions:
  - compare `latest` vs `pending`
  - inspect recent tx status
  - re-read after bounded delay
