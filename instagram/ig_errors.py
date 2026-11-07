"""Structured Instagram errors shared by every backend.

Every public function returns ``{"ok": False, "error": {...}}`` instead of
raising, so an agent can branch on ``error.code`` and follow ``hint`` without
parsing tracebacks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


_SECRET_KEYS = {
    "access_token",
    "page_token",
    "client_secret",
    "password",
    "sessionid",
    "fb_exchange_token",
    "authorization",
}

_TOKEN_RE = re.compile(
    r"(?i)(\"?)(access_token|page_token|client_secret|password|sessionid|"
    r"fb_exchange_token)(\"?\s*[:=]\s*\"?)([^\"\s,}]+)"
)
_BEARER_RE = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+/=-]{8,})")


def redact(value: Any) -> str:
    """Best-effort secret scrubber for errors and debug payloads."""
    text = value if isinstance(value, str) else str(value)
    text = _TOKEN_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}***", text)
    text = _BEARER_RE.sub(lambda m: f"{m.group(1)}***", text)
    if len(text) > 1200:
        text = text[:1200] + "...[truncated]"
    return text


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if str(key).lower() in _SECRET_KEYS else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


class InstagramError(Exception):
    code = "instagram_error"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        hint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        super().__init__(message)
        self.message = redact(message)
        if code:
            self.code = code
        self.hint = hint
        self.details = details or {}
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "hint": self.hint,
                "details": _redact_value(self.details),
                "retryable": self.retryable,
            },
        }


class ValidationError(InstagramError):
    code = "validation_error"


class CredentialRequired(InstagramError):
    code = "credential_required"


class AccountNotFound(InstagramError):
    code = "account_not_found"


class CapabilityUnavailable(InstagramError):
    code = "capability_not_available"


class AuthError(InstagramError):
    code = "auth_error"


class PermissionDenied(InstagramError):
    code = "permission_denied"


class RateLimitError(InstagramError):
    code = "rate_limited"
    retryable = True


class QuotaExceeded(InstagramError):
    code = "quota_exceeded"


class ProviderError(InstagramError):
    code = "provider_error"


class NotFound(InstagramError):
    code = "not_found"


class WriteBlocked(InstagramError):
    code = "write_blocked"


class ConfirmationRequired(InstagramError):
    code = "confirmation_required"


class MediaHostingRequired(InstagramError):
    code = "media_hosting_required"


class ToolNotFound(InstagramError):
    code = "composio_tool_not_found"
