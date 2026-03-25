#!/usr/bin/env python3
"""
Tests for M1-T1: shared/retry.py
Validates retry logic, backoff calculation, and error classification.
"""
import sys, os, time, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'patches'))

from shared.retry import (
    RetryConfig, async_retry, sync_retry, with_retry,
    _calc_delay, _is_retryable, PRESETS
)


def test_calc_delay_exponential():
    """Delay should double each attempt (1-indexed: attempt=1 → base_delay)."""
    cfg = RetryConfig(base_delay=1.0, max_delay=30.0, jitter=0.0)  # no jitter for determinism
    d1 = _calc_delay(1, cfg)
    d2 = _calc_delay(2, cfg)
    d3 = _calc_delay(3, cfg)
    assert abs(d1 - 1.0) < 0.01, f"Attempt 1: expected ~1.0, got {d1}"
    assert abs(d2 - 2.0) < 0.01, f"Attempt 2: expected ~2.0, got {d2}"
    assert abs(d3 - 4.0) < 0.01, f"Attempt 3: expected ~4.0, got {d3}"


def test_calc_delay_cap():
    """Delay should not exceed max_delay."""
    cfg = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=0.0)
    d10 = _calc_delay(10, cfg)  # 2^10 = 1024, should cap at 5
    assert d10 <= 5.0, f"Expected <= 5.0, got {d10}"


def test_calc_delay_jitter():
    """Jitter should add randomness."""
    cfg = RetryConfig(base_delay=2.0, max_delay=30.0, jitter=1.0)
    delays = [_calc_delay(1, cfg) for _ in range(20)]
    # With jitter=1.0, delays should vary around 4.0 ± 1.0
    unique = len(set(round(d, 4) for d in delays))
    assert unique > 1, f"Expected variation with jitter, got {unique} unique values"


def test_is_retryable_status_codes():
    """429 and 5xx should be retryable, 400/401 should not."""
    cfg = RetryConfig()
    
    class FakeExc429(Exception):
        status_code = 429
    class FakeExc400(Exception):
        status_code = 400
    class FakeExc503(Exception):
        status_code = 503
    
    assert _is_retryable(FakeExc429(), cfg) == True
    assert _is_retryable(FakeExc400(), cfg) == False
    assert _is_retryable(FakeExc503(), cfg) == True


def test_is_retryable_message_patterns():
    """Error messages containing 'rate limit' etc should be retryable."""
    cfg = RetryConfig()
    assert _is_retryable(Exception("429 Too Many Requests"), cfg) == True
    assert _is_retryable(Exception("rate limit exceeded"), cfg) == True
    assert _is_retryable(Exception("connection reset by peer"), cfg) == True
    assert _is_retryable(Exception("invalid parameter value"), cfg) == False


def test_is_retryable_exception_types():
    """ConnectionError and TimeoutError should be retryable."""
    cfg = RetryConfig()
    assert _is_retryable(ConnectionError("reset"), cfg) == True
    assert _is_retryable(TimeoutError("timed out"), cfg) == True
    assert _is_retryable(ValueError("bad value"), cfg) == False


def test_sync_retry_succeeds_after_failures():
    """Function should succeed if transient failure resolves within retries."""
    call_count = 0
    
    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("temporary")
        return "success"
    
    cfg = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)
    result = sync_retry(flaky_fn, config=cfg, tool_name="test")
    assert result == "success"
    assert call_count == 3


def test_sync_retry_exhausted():
    """Should raise after max_retries exhausted."""
    def always_fail():
        raise ConnectionError("permanent")
    
    cfg = RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0)
    try:
        sync_retry(always_fail, config=cfg, tool_name="test")
        assert False, "Should have raised"
    except ConnectionError as e:
        assert "permanent" in str(e)


def test_sync_retry_non_retryable_immediate():
    """Non-retryable errors should raise immediately (no retry)."""
    call_count = 0
    
    def auth_fail():
        nonlocal call_count
        call_count += 1
        raise ValueError("invalid API key")
    
    cfg = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)
    try:
        sync_retry(auth_fail, config=cfg, tool_name="test")
        assert False, "Should have raised"
    except ValueError:
        assert call_count == 1, f"Should not retry non-retryable, but called {call_count} times"


def test_async_retry_succeeds():
    """Async version should work like sync."""
    call_count = 0
    
    async def flaky_async():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError("timeout")
        return 42
    
    cfg = RetryConfig(max_retries=3, base_delay=0.01, jitter=0.0)
    result = asyncio.run(
        async_retry(flaky_async, config=cfg, tool_name="test_async")
    )
    assert result == 42
    assert call_count == 2


def test_decorator_sync():
    """@with_retry should work on sync functions."""
    call_count = 0
    
    @with_retry(config=RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0))
    def decorated():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("temp")
        return "ok"
    
    assert decorated() == "ok"
    assert call_count == 2


def test_decorator_async():
    """@with_retry should work on async functions."""
    call_count = 0
    
    @with_retry(config=RetryConfig(max_retries=2, base_delay=0.01, jitter=0.0))
    async def decorated_async():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError("temp")
        return "async_ok"
    
    result = asyncio.run(decorated_async())
    assert result == "async_ok"


def test_presets_exist():
    """All expected presets should be defined."""
    expected = ["coingecko", "coinglass", "hyperliquid", "1inch", "twitter", "default"]
    for name in expected:
        assert name in PRESETS, f"Missing preset: {name}"
        cfg = PRESETS[name]
        assert cfg.max_retries >= 1
        assert cfg.base_delay > 0


def test_retry_timing():
    """Verify actual sleep time is roughly correct."""
    call_count = 0
    start = time.monotonic()
    
    def fail_twice():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("temp")
        return "ok"
    
    cfg = RetryConfig(max_retries=3, base_delay=0.05, jitter=0.0)
    result = sync_retry(fail_twice, config=cfg, tool_name="timing")
    elapsed = time.monotonic() - start
    
    # 2 retries: ~0.05 + ~0.10 = 0.15s, allow generous margin
    assert elapsed < 1.0, f"Retry took too long: {elapsed:.2f}s"
    assert result == "ok"


# ─── Runner ──────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("calc_delay_exponential", test_calc_delay_exponential),
        ("calc_delay_cap", test_calc_delay_cap),
        ("calc_delay_jitter", test_calc_delay_jitter),
        ("is_retryable_status_codes", test_is_retryable_status_codes),
        ("is_retryable_message_patterns", test_is_retryable_message_patterns),
        ("is_retryable_exception_types", test_is_retryable_exception_types),
        ("sync_retry_succeeds_after_failures", test_sync_retry_succeeds_after_failures),
        ("sync_retry_exhausted", test_sync_retry_exhausted),
        ("sync_retry_non_retryable_immediate", test_sync_retry_non_retryable_immediate),
        ("async_retry_succeeds", test_async_retry_succeeds),
        ("decorator_sync", test_decorator_sync),
        ("decorator_async", test_decorator_async),
        ("presets_exist", test_presets_exist),
        ("retry_timing", test_retry_timing),
    ]
    
    passed = failed = 0
    print("=" * 60)
    print("  M1-T1: Retry Module Tests")
    print("=" * 60)
    
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    
    print(f"\n  TOTAL: {passed} passed, {failed} failed ({passed + failed} total)")
    print("=" * 60)
    sys.exit(1 if failed else 0)
