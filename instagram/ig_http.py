"""Small stdlib HTTP helper.

The skill is loaded in many environments, so it deliberately avoids a hard
``requests`` dependency. Gateway calls MUST bypass proxies (flycast is internal);
Graph calls honor the normal environment proxy settings.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from ig_errors import ProviderError, redact


def request_json(
    url: str,
    *,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    no_proxy: bool = False,
    form: bool = False,
) -> Any:
    """Perform one HTTP request and return decoded JSON (or raw text)."""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(clean, doseq=True)}"

    hdrs = {"Accept": "application/json", **(headers or {})}
    data: Optional[bytes] = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body, doseq=True).encode()
            hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body, separators=(",", ":")).encode()
            hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({}))
        if no_proxy
        else urllib.request.build_opener()
    )

    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        text = raw.decode("utf-8", "replace")
        parsed: Any = None
        try:
            parsed = json.loads(text)
        except Exception:
            pass
        raise ProviderError(
            f"HTTP {exc.code} from {urllib.parse.urlsplit(url).netloc}: {redact(text)}",
            code="http_error",
            details={"status": exc.code, "body": parsed or redact(text)},
            retryable=exc.code >= 500 or exc.code == 429,
        )
    except urllib.error.URLError as exc:
        raise ProviderError(
            f"Network error reaching {urllib.parse.urlsplit(url).netloc}: {exc.reason}",
            code="network_error",
            retryable=True,
        )

    if not raw:
        return {}
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
