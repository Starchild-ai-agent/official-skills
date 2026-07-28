"""Fire-and-forget trade event reporting to the Starchild trade analytics API.

Posts executed orders/swaps to POST {AI_AGENT_API_URL}/v1/trade-events using
the machine's CONTAINER_JWT. Reporting must NEVER affect trading:
- runs in a background thread by default
- swallows all exceptions
- no-ops silently when env vars are missing (e.g. local dev)

Batch/script callers (e.g. trade_sync.py) MUST pass blocking=True, or use the
returned thread handle — a daemon thread is killed when the process exits and
the POST would never leave the machine.

Event dict fields (all optional except source/venue/event_type/dedupe_key):
    source, venue, event_type ('order'|'fill'|'swap'|'cancel'),
    dedupe_key, wallet_address, account_id, symbol, side ('buy'|'sell'),
    price, size, notional_usd, fee, fee_currency, order_id, tx_hash,
    raw (dict), occurred_at (ISO8601 str)
"""

import json
import logging
import os
import threading
import urllib.request

logger = logging.getLogger(__name__)

_TIMEOUT = 10
BATCH_MAX = 500


def _post_batches(base, token, events):
    """POST events in batches. Returns number of successfully sent events."""
    sent = 0
    for i in range(0, len(events), BATCH_MAX):
        chunk = events[i : i + BATCH_MAX]
        try:
            req = urllib.request.Request(
                f"{base}/v1/trade-events",
                data=json.dumps({"events": chunk}).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                resp.read()
            sent += len(chunk)
        except Exception as e:  # noqa: BLE001 — reporting must never break trading
            logger.debug(f"trade report batch failed (ignored): {e}")
    return sent


def report_trade_events(events, blocking=False):
    """Report a list of trade event dicts. Never raises.

    blocking=False (default): send in a background daemon thread; returns the
        thread handle (or None if nothing to send). Use from long-lived agent
        processes where the trade call must not wait on reporting.
    blocking=True: send synchronously and return the number of events sent.
        REQUIRED for short-lived scripts — a daemon thread dies with the
        process and the report would be silently lost.
    """
    try:
        if not events:
            return 0 if blocking else None
        base = os.environ.get("AI_AGENT_API_URL", "").rstrip("/")
        token = os.environ.get("CONTAINER_JWT", "")
        if not base or not token:
            logger.debug("trade report skipped: AI_AGENT_API_URL/CONTAINER_JWT unset")
            return 0 if blocking else None

        if blocking:
            return _post_batches(base, token, events)

        t = threading.Thread(
            target=_post_batches, args=(base, token, events), daemon=True
        )
        t.start()
        return t
    except Exception:  # noqa: BLE001
        return 0 if blocking else None
