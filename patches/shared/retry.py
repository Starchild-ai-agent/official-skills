"""
Unified Retry Module for Crypto Skills
========================================
解决: 93个.py文件中仅2个实现了重试逻辑。

设计原则:
1. 区分可重试(429/5xx) vs 不可重试(400/401/403) 错误
2. 指数退避 + 抖动 防止 thundering herd
3. 小模型友好的日志：每次重试都说明原因和下次等待时间
4. 同步/异步双版本，覆盖所有 skill 代码风格

用法:
    # 异步 (coinglass, 1inch, hyperliquid)
    result = await async_retry(api_call, args, tool_name="hl_order")

    # 同步 (twitter, debank, charting scripts)
    result = sync_retry(api_call, args, tool_name="coin_price")

    # 装饰器
    @with_retry(max_attempts=3)
    async def my_api_call(): ...

    # 函数式 — 传入 callable
    result = await retry_api_call(fn, tool_name="coinglass/funding", max_attempts=3)
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Awaitable, Callable, Optional, Set, TypeVar

logger = logging.getLogger("skills.retry")

T = TypeVar("T")


# ─── Retryable HTTP status codes ─────────────────────────────────
RETRYABLE_CODES: Set[int] = {429, 500, 502, 503, 504}
NON_RETRYABLE_CODES: Set[int] = {400, 401, 403, 404, 422}


# ─── Configuration ───────────────────────────────────────────────

class RetryConfig:
    """Tunable retry parameters per skill/tool.

    Accepts both naming conventions:
      - max_attempts / max_retries  (both → max_attempts internally)
      - retry_on_status / retryable_status_codes
      - backoff_factor (alias for exponential multiplier)
      - jitter: bool (True/False) or float (backward compat, >0 = True)
    """
    def __init__(
        self,
        max_attempts: int = 3,
        max_retries: Optional[int] = None,  # alias
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: Any = True,
        retry_on_status: Optional[Set[int]] = None,
        retryable_status_codes: Optional[Set[int]] = None,  # alias
        non_retryable_status_codes: Optional[Set[int]] = None,
        retryable_exceptions: Optional[tuple] = None,
    ):
        # max_retries is an alias for max_attempts
        self.max_attempts = max_retries if max_retries is not None else max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        # jitter: accept bool or float (float > 0 → True for backward compat)
        if isinstance(jitter, (int, float)) and not isinstance(jitter, bool):
            self.jitter = jitter > 0
        else:
            self.jitter = bool(jitter)
        self.retry_on_status = (
            retryable_status_codes or retry_on_status or {429, 500, 502, 503, 504}
        )
        self.non_retryable_status_codes = (
            non_retryable_status_codes or {400, 401, 403, 404, 422}
        )
        self.retryable_exceptions = (
            retryable_exceptions or (ConnectionError, TimeoutError, OSError)
        )

    @property
    def max_retries(self) -> int:
        return self.max_attempts

    @property
    def retryable_status_codes(self) -> Set[int]:
        return self.retry_on_status


# Presets for common APIs
PRESETS = {
    "coingecko": RetryConfig(
        max_attempts=3, base_delay=2.0, max_delay=30.0,
    ),
    "coinglass": RetryConfig(
        max_attempts=3, base_delay=1.5, max_delay=20.0,
    ),
    "hyperliquid": RetryConfig(
        max_attempts=2, base_delay=0.5, max_delay=10.0,
    ),
    "1inch": RetryConfig(
        max_attempts=3, base_delay=2.0, max_delay=30.0,
    ),
    "twitter": RetryConfig(
        max_attempts=2, base_delay=3.0, max_delay=30.0,
    ),
    "default": RetryConfig(),
}


# ─── Core Retry Logic ────────────────────────────────────────────

def _calc_delay(attempt: int, config: RetryConfig) -> float:
    """Exponential backoff with optional jitter.

    attempt is 1-indexed: attempt=1 → base_delay * backoff^0 = base_delay.
    """
    raw = config.base_delay * (config.backoff_factor ** (attempt - 1))
    delay = min(raw, config.max_delay)
    if config.jitter:
        # ±50% jitter
        delay = delay * random.uniform(0.5, 1.5)
    return max(0.01, delay)


def _is_retryable(exc: Exception, config: RetryConfig) -> bool:
    """Determine if an exception is retryable."""
    if isinstance(exc, config.retryable_exceptions):
        return True

    status = getattr(exc, 'status_code', None) or getattr(exc, 'status', None)
    if status:
        if status in config.non_retryable_status_codes:
            return False
        if status in config.retry_on_status:
            return True

    msg = str(exc).lower()
    retryable_patterns = [
        "429", "rate limit", "too many requests", "timeout",
        "502", "503", "504", "bad gateway", "service unavailable",
        "connection reset", "connection refused",
    ]
    return any(p in msg for p in retryable_patterns)


def _format_retry_log(tool_name: str, attempt: int, max_attempts: int,
                      delay: float, error: str) -> str:
    """Format retry message for small model consumption."""
    return (
        f"⏳ [{tool_name}] Retry {attempt}/{max_attempts} "
        f"in {delay:.1f}s — {error}"
    )


def _should_retry_response(result: Any, config: RetryConfig) -> bool:
    """Check if a successful return value is actually a retryable HTTP response."""
    status = getattr(result, 'status', None) or getattr(result, 'status_code', None)
    if status and status in config.retry_on_status:
        return True
    return False


# ─── Async Retry ─────────────────────────────────────────────────

async def async_retry(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    config: Optional[RetryConfig] = None,
    tool_name: str = "",
    **kwargs: Any,
) -> T:
    """Async retry wrapper with exponential backoff."""
    config = config or RetryConfig()
    last_exc = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await fn(*args, **kwargs)
            # Check if result is a retryable HTTP response object
            if _should_retry_response(result, config) and attempt < config.max_attempts:
                delay = _calc_delay(attempt, config)
                status = getattr(result, 'status', None) or getattr(result, 'status_code', None)
                logger.info(_format_retry_log(
                    tool_name, attempt, config.max_attempts, delay,
                    f"HTTP {status}"
                ))
                await asyncio.sleep(delay)
                continue
            return result
        except Exception as exc:
            last_exc = exc
            if attempt >= config.max_attempts:
                break
            if not _is_retryable(exc, config):
                logger.warning(f"[{tool_name}] Non-retryable error: {exc}")
                raise
            delay = _calc_delay(attempt, config)
            logger.info(_format_retry_log(
                tool_name, attempt, config.max_attempts, delay, str(exc)[:100]
            ))
            await asyncio.sleep(delay)

    raise last_exc


# ─── Sync Retry ──────────────────────────────────────────────────

def sync_retry(
    fn: Callable[..., T],
    *args: Any,
    config: Optional[RetryConfig] = None,
    tool_name: str = "",
    **kwargs: Any,
) -> T:
    """Synchronous retry wrapper."""
    config = config or RetryConfig()
    last_exc = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = fn(*args, **kwargs)
            if _should_retry_response(result, config) and attempt < config.max_attempts:
                delay = _calc_delay(attempt, config)
                status = getattr(result, 'status', None) or getattr(result, 'status_code', None)
                logger.info(_format_retry_log(
                    tool_name, attempt, config.max_attempts, delay,
                    f"HTTP {status}"
                ))
                time.sleep(delay)
                continue
            return result
        except Exception as exc:
            last_exc = exc
            if attempt >= config.max_attempts:
                break
            if not _is_retryable(exc, config):
                logger.warning(f"[{tool_name}] Non-retryable error: {exc}")
                raise
            delay = _calc_delay(attempt, config)
            logger.info(_format_retry_log(
                tool_name, attempt, config.max_attempts, delay, str(exc)[:100]
            ))
            time.sleep(delay)

    raise last_exc


# ─── Decorator ───────────────────────────────────────────────────

def with_retry(
    config: Optional[RetryConfig] = None,
    tool_name: str = "",
    preset: str = "",
    # Convenience kwargs → forwarded to RetryConfig
    max_attempts: Optional[int] = None,
    retry_on: Optional[list] = None,
    **extra_config,
):
    """Decorator for automatic retry.

    @with_retry(preset="coinglass")
    async def get_funding_rate(symbol): ...

    @with_retry(max_attempts=3, retry_on=[429, 502])
    async def my_call(): ...

    @with_retry(config=RetryConfig(max_attempts=5))
    def sync_api_call(): ...
    """
    if preset and preset in PRESETS:
        config = PRESETS[preset]

    # Allow shorthand kwargs
    if config is None:
        cfg_kwargs = {}
        if max_attempts is not None:
            cfg_kwargs["max_attempts"] = max_attempts
        if retry_on is not None:
            cfg_kwargs["retry_on_status"] = set(retry_on)
        cfg_kwargs.update(extra_config)
        config = RetryConfig(**cfg_kwargs) if cfg_kwargs else RetryConfig()

    def decorator(fn):
        name = tool_name or fn.__qualname__

        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                return await async_retry(fn, *args, config=config, tool_name=name, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                return sync_retry(fn, *args, config=config, tool_name=name, **kwargs)
            return sync_wrapper

    return decorator


# ─── Functional API ──────────────────────────────────────────────

async def retry_api_call(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    tool_name: str = "",
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> T:
    """Functional-style async retry — pass a callable, get retried result.

    Raises RuntimeError with tool_name + attempt count on exhaustion.

    Example:
        data = await retry_api_call(
            client.get_funding, "BTC",
            tool_name="coinglass/funding",
            max_attempts=3
        )
    """
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay, jitter=False)
    last_exc = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts:
                break
            if not _is_retryable(exc, config):
                raise
            delay = _calc_delay(attempt, config)
            logger.info(_format_retry_log(
                tool_name, attempt, max_attempts, delay, str(exc)[:100]
            ))
            await asyncio.sleep(delay)

    raise RuntimeError(
        f"[{tool_name}] Failed after {max_attempts} attempts. "
        f"Last error: {last_exc}"
    )
