"""
HTTP Retry Middleware for Skills
================================
解决问题: 10/12 skill 无任何 retry 逻辑，瞬态 429/502/503 直接失败。
方案: 可复用 decorator + context manager，skill 代码改动最小。

用法:
    from shared.retry import with_retry, RetryConfig

    # 作为 decorator
    @with_retry(max_attempts=3, retry_on=[429, 502, 503])
    async def fetch_price(url, **kwargs):
        return await proxied_get(url, **kwargs)

    # 自定义配置
    config = RetryConfig(max_attempts=5, base_delay=0.5, max_delay=30)
    @with_retry(config=config)
    async def heavy_api_call(...):
        ...
"""

import asyncio
import functools
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Default retryable status codes
RETRYABLE_CODES = {429, 500, 502, 503, 504}


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0        # seconds
    max_delay: float = 30.0        # seconds  
    backoff_factor: float = 2.0    # exponential backoff multiplier
    retry_on_status: set = field(default_factory=lambda: RETRYABLE_CODES.copy())
    retry_on_exceptions: tuple = (ConnectionError, TimeoutError, asyncio.TimeoutError)
    jitter: bool = True            # add random jitter to prevent thundering herd


DEFAULT_CONFIG = RetryConfig()


def with_retry(
    func=None,
    *,
    max_attempts: int = None,
    retry_on: list[int] = None,
    config: RetryConfig = None
):
    """
    Decorator for async functions that make HTTP calls.
    Automatic retry with exponential backoff for transient failures.

    Returns the original response on success.
    Raises on persistent failure with context about all attempts.
    """
    cfg = config or RetryConfig(
        max_attempts=max_attempts or DEFAULT_CONFIG.max_attempts,
        retry_on_status=set(retry_on) if retry_on else DEFAULT_CONFIG.retry_on_status,
    )

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            last_error = None
            last_status = None

            for attempt in range(1, cfg.max_attempts + 1):
                try:
                    result = await fn(*args, **kwargs)

                    # Check HTTP status if result has one
                    status = getattr(result, 'status', None) or getattr(result, 'status_code', None)
                    if status and status in cfg.retry_on_status:
                        last_status = status
                        if attempt < cfg.max_attempts:
                            delay = _calc_delay(attempt, cfg)
                            logger.warning(
                                f"[retry] {fn.__name__} got {status}, "
                                f"attempt {attempt}/{cfg.max_attempts}, "
                                f"retrying in {delay:.1f}s"
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            # Final attempt also failed
                            logger.error(
                                f"[retry] {fn.__name__} failed after {cfg.max_attempts} attempts, "
                                f"last status: {status}"
                            )

                    return result

                except cfg.retry_on_exceptions as e:
                    last_error = e
                    if attempt < cfg.max_attempts:
                        delay = _calc_delay(attempt, cfg)
                        logger.warning(
                            f"[retry] {fn.__name__} raised {type(e).__name__}: {e}, "
                            f"attempt {attempt}/{cfg.max_attempts}, "
                            f"retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"[retry] {fn.__name__} failed after {cfg.max_attempts} attempts: {e}"
                        )
                        raise

            # Should not reach here, but safety
            if last_error:
                raise last_error
            return result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def _calc_delay(attempt: int, cfg: RetryConfig) -> float:
    """Calculate delay with exponential backoff + optional jitter"""
    import random
    delay = cfg.base_delay * (cfg.backoff_factor ** (attempt - 1))
    delay = min(delay, cfg.max_delay)
    if cfg.jitter:
        delay *= (0.5 + random.random())  # 50%-150% of calculated delay
    return delay


async def retry_api_call(
    call_fn,
    *args,
    tool_name: str = "unknown",
    max_attempts: int = 3,
    **kwargs
):
    """
    Functional style retry — for cases where decorator isn't convenient.

    Usage:
        response = await retry_api_call(
            proxied_get,
            url, params=params, headers=headers,
            tool_name="coinglass/funding_rate"
        )
    """
    cfg = RetryConfig(max_attempts=max_attempts)
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = await call_fn(*args, **kwargs)
            status = getattr(result, 'status', None)
            if status and status in cfg.retry_on_status and attempt < max_attempts:
                delay = _calc_delay(attempt, cfg)
                logger.warning(f"[retry] {tool_name} got {status}, retry in {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            return result
        except cfg.retry_on_exceptions as e:
            last_error = e
            if attempt < max_attempts:
                delay = _calc_delay(attempt, cfg)
                logger.warning(f"[retry] {tool_name} error: {e}, retry in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(
                    f"{tool_name}: failed after {max_attempts} attempts. "
                    f"Last error: {type(e).__name__}: {e}"
                ) from e

    raise RuntimeError(f"{tool_name}: exhausted all {max_attempts} retry attempts")
