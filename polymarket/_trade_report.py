"""Fire-and-forget trade event reporting to the Starchild trade analytics API.

Posts executed orders/swaps to POST {AI_AGENT_API_URL}/v1/trade-events using
the machine's CONTAINER_JWT. Reporting must NEVER affect trading:
- runs in a daemon thread
- swallows all exceptions
- no-ops silently when env vars are missing (e.g. local dev)

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


def report_trade_events(events):
    """Report a list of trade event dicts. Fire-and-forget, never raises."""
    try:
        if not events:
            return
        base = os.environ.get("AI_AGENT_API_URL", "").rstrip("/")
        token = os.environ.get("CONTAINER_JWT", "")
        if not base or not token:
            return

        def _send():
            try:
                req = urllib.request.Request(
                    f"{base}/v1/trade-events",
                    data=json.dumps({"events": events}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                    resp.read()
            except Exception as e:  # noqa: BLE001 — reporting must never break trading
                logger.debug(f"trade report failed (ignored): {e}")

        threading.Thread(target=_send, daemon=True).start()
    except Exception:  # noqa: BLE001
        pass
