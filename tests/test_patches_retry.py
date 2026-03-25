"""
Suite C: Retry Logic Patch Validation
Tests shared/retry.py — HTTP retry middleware for skills
"""
import sys, os, asyncio, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'patches'))

from shared.retry import RetryConfig, with_retry, retry_api_call, RETRYABLE_CODES, _calc_delay

PASSED = 0
FAILED = 0

def test(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")

def atest(name, coro):
    global PASSED, FAILED
    try:
        asyncio.get_event_loop().run_until_complete(coro)
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")

print("\n🧪 Suite C: Retry Logic Patch\n")

# C1: RetryConfig defaults
def t_config_defaults():
    c = RetryConfig()
    assert c.max_attempts == 3
    assert c.base_delay == 1.0
    assert c.max_delay == 30.0
    assert c.backoff_factor == 2.0
    assert c.jitter is True
    assert 429 in c.retry_on_status
    assert 502 in c.retry_on_status
    assert 503 in c.retry_on_status
test("RetryConfig defaults are sensible", t_config_defaults)

# C2: RetryConfig custom
def t_config_custom():
    c = RetryConfig(max_attempts=5, base_delay=0.5, max_delay=10.0)
    assert c.max_attempts == 5
    assert c.base_delay == 0.5
    assert c.max_delay == 10.0
test("RetryConfig accepts custom parameters", t_config_custom)

# C3: RETRYABLE_CODES set
def t_retryable_codes():
    for code in [429, 500, 502, 503, 504]:
        assert code in RETRYABLE_CODES, f"{code} should be retryable"
    assert 200 not in RETRYABLE_CODES
    assert 404 not in RETRYABLE_CODES
test("RETRYABLE_CODES includes expected HTTP codes", t_retryable_codes)

# C4: Delay calculation — exponential backoff
def t_delay_calc():
    cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=30.0, jitter=False)
    d1 = _calc_delay(1, cfg)
    d2 = _calc_delay(2, cfg)
    d3 = _calc_delay(3, cfg)
    assert d1 == 1.0, f"Attempt 1 delay should be 1.0, got {d1}"
    assert d2 == 2.0, f"Attempt 2 delay should be 2.0, got {d2}"
    assert d3 == 4.0, f"Attempt 3 delay should be 4.0, got {d3}"
test("Delay uses exponential backoff", t_delay_calc)

# C5: Delay capped at max_delay
def t_delay_cap():
    cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=5.0, jitter=False)
    d10 = _calc_delay(10, cfg)  # 1 * 2^9 = 512, but capped at 5
    assert d10 == 5.0, f"Delay should be capped at 5.0, got {d10}"
test("Delay capped at max_delay", t_delay_cap)

# C6: Jitter adds randomness
def t_delay_jitter():
    cfg = RetryConfig(base_delay=1.0, backoff_factor=2.0, max_delay=30.0, jitter=True)
    delays = [_calc_delay(1, cfg) for _ in range(20)]
    unique = len(set(delays))
    assert unique > 1, "Jitter should produce varied delays"
    assert all(0.5 <= d <= 1.5 for d in delays), f"Jitter range should be 50%-150%, got {min(delays)}-{max(delays)}"
test("Jitter produces varied delay values in 50%-150% range", t_delay_jitter)

# C7: with_retry decorator — success on first try
async def t_retry_success():
    call_count = 0
    @with_retry(max_attempts=3, retry_on=[429, 502])
    async def good_fn():
        nonlocal call_count
        call_count += 1
        return "ok"
    result = await good_fn()
    assert result == "ok"
    assert call_count == 1, "Should only call once on success"
atest("with_retry: success on first try, calls once", t_retry_success())

# C8: with_retry — retries on exception then succeeds
async def t_retry_exception_then_ok():
    call_count = 0
    @with_retry(config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False))
    async def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("network blip")
        return "recovered"
    result = await flaky_fn()
    assert result == "recovered"
    assert call_count == 3
atest("with_retry: retries ConnectionError, succeeds on 3rd", t_retry_exception_then_ok())

# C9: with_retry — exhausts all retries, raises
async def t_retry_exhausted():
    @with_retry(config=RetryConfig(max_attempts=2, base_delay=0.01, jitter=False))
    async def always_fail():
        raise ConnectionError("persistent failure")
    try:
        await always_fail()
        assert False, "Should have raised"
    except ConnectionError:
        pass  # Correct — re-raises original error
atest("with_retry: exhausts attempts, raises original error", t_retry_exhausted())

# C10: with_retry — retries on HTTP status
async def t_retry_http_status():
    call_count = 0
    class FakeResponse:
        def __init__(self, status):
            self.status = status
    
    @with_retry(config=RetryConfig(max_attempts=3, base_delay=0.01, jitter=False))
    async def api_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return FakeResponse(429)
        return FakeResponse(200)
    
    result = await api_call()
    assert result.status == 200
    assert call_count == 3
atest("with_retry: retries on 429 status, returns 200", t_retry_http_status())

# C11: retry_api_call functional style
async def t_retry_functional():
    call_count = 0
    async def flaky(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("blip")
        return "data"
    result = await retry_api_call(flaky, tool_name="test/tool", max_attempts=3)
    assert result == "data"
    assert call_count == 2
atest("retry_api_call functional style works", t_retry_functional())

# C12: retry_api_call — exhausted raises RuntimeError with context
async def t_retry_functional_fail():
    async def always_fail():
        raise ConnectionError("down")
    try:
        await retry_api_call(always_fail, tool_name="coinglass/funding", max_attempts=2)
        assert False, "Should raise"
    except RuntimeError as e:
        s = str(e)
        assert "coinglass/funding" in s, f"Should include tool_name, got: {s}"
        assert "2 attempts" in s, f"Should include attempt count, got: {s}"
atest("retry_api_call: failure includes tool_name + attempt count", t_retry_functional_fail())

print(f"\n{'='*50}")
print(f"Results: {PASSED}/{PASSED+FAILED} passed")
print(f"{'='*50}")
