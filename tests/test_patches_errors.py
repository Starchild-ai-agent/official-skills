"""
Suite A: Error Handling Patch Validation
Tests shared/errors.py — structured error taxonomy for crypto skills
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'patches'))

from shared.errors import (
    SkillError, TransientError, RateLimitError, ServiceUnavailableError,
    TimeoutError, UserInputError, InvalidParameterError, UnsupportedAssetError,
    InsufficientBalanceError, InsufficientGasError, ChainError,
    TransactionRevertedError, SlippageExceededError, NonceError, safe_call
)

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
    """Async test helper"""
    global PASSED, FAILED
    try:
        asyncio.get_event_loop().run_until_complete(coro)
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")

print("\n🧪 Suite A: Error Handling Patch\n")

# A1: SkillError base class
def t_skill_error_format():
    e = SkillError("test error", suggestion="try again", tool_name="test/tool")
    s = e.format()
    assert "❌" in s, "Should have error emoji"
    assert "SKILL_ERROR" in s, f"Should have code, got: {s}"
    assert "test/tool" in s, "Should include tool name"
    assert "try again" in s, "Should include suggestion"
test("SkillError formats with code + tool + suggestion", t_skill_error_format)

# A2: SkillError context kwargs
def t_skill_error_context():
    e = SkillError("oops", balance="100", required="500")
    s = e.format()
    assert "balance: 100" in s
    assert "required: 500" in s
test("SkillError includes context kwargs in format", t_skill_error_context)

# A3: Transient errors are retryable
def t_transient_retryable():
    assert TransientError.retryable is True
    assert RateLimitError.retryable is True
    assert ServiceUnavailableError.retryable is True
    assert TimeoutError.retryable is True
test("Transient errors have retryable=True", t_transient_retryable)

# A4: User errors are NOT retryable
def t_user_not_retryable():
    assert UserInputError.retryable is False
    assert InvalidParameterError.retryable is False
    assert UnsupportedAssetError.retryable is False
test("User input errors have retryable=False", t_user_not_retryable)

# A5: RateLimitError includes retry_after
def t_rate_limit_retry_after():
    e = RateLimitError(service="coinglass", retry_after=30)
    s = str(e)
    assert "RATE_LIMITED" in s
    assert "30" in s
    assert "coinglass" in s
test("RateLimitError includes service name + retry_after", t_rate_limit_retry_after)

# A6: InsufficientBalanceError shows shortfall
def t_insufficient_balance():
    e = InsufficientBalanceError(available=100, required=500, asset="USDC")
    s = str(e)
    assert "INSUFFICIENT_BALANCE" in s
    assert "400" in s, f"Should show shortfall of 400, got: {s}"
    assert "USDC" in s
test("InsufficientBalanceError calculates and shows shortfall", t_insufficient_balance)

# A7: InsufficientGasError derives from InsufficientBalanceError
def t_gas_error():
    e = InsufficientGasError(chain="arbitrum", available=0.001, estimated_gas=0.01)
    s = str(e)
    assert "INSUFFICIENT_GAS" in s
    assert "ETH" in s, f"Should mention native token ETH for arbitrum, got: {s}"
test("InsufficientGasError maps chain to native token", t_gas_error)

# A8: SlippageExceededError calculates actual slippage
def t_slippage_error():
    e = SlippageExceededError(expected_price=100.0, actual_price=95.0, max_slippage=3.0)
    s = str(e)
    assert "5.00%" in s, f"Should calculate 5% slippage, got: {s}"
    assert "SLIPPAGE_EXCEEDED" in s
test("SlippageExceededError calculates actual slippage %", t_slippage_error)

# A9: TransactionRevertedError
def t_tx_reverted():
    e = TransactionRevertedError(tx_hash="0xabc123", revert_reason="ERC20: transfer amount exceeds balance")
    s = str(e)
    assert "TX_REVERTED" in s
    assert "0xabc123" in s
    assert "transfer amount exceeds balance" in s
test("TransactionRevertedError includes tx hash + reason", t_tx_reverted)

# A10: safe_call wraps normal exception into SkillError
async def t_safe_call_wraps():
    async def bad_fn():
        raise ValueError("something broke")
    try:
        await safe_call(bad_fn, tool_name="test/tool", fallback_msg="Failed")
        assert False, "Should have raised"
    except SkillError as e:
        s = str(e)
        assert "SKILL_ERROR" in s
        assert "something broke" in s
atest("safe_call wraps ValueError into SkillError", t_safe_call_wraps())

# A11: safe_call classifies 429 as RateLimitError
async def t_safe_call_429():
    async def rate_limited():
        raise Exception("HTTP 429 rate limit exceeded")
    try:
        await safe_call(rate_limited, tool_name="api/test")
        assert False, "Should have raised"
    except RateLimitError:
        pass  # Correct classification
atest("safe_call classifies '429' in error msg as RateLimitError", t_safe_call_429())

# A12: safe_call rejects None results
async def t_safe_call_none():
    async def returns_none():
        return None
    try:
        await safe_call(returns_none, tool_name="api/test")
        assert False, "Should have raised"
    except SkillError as e:
        assert "None" in str(e) or "empty" in str(e).lower()
atest("safe_call raises SkillError when function returns None", t_safe_call_none())

# A13: safe_call passes through already-structured SkillError
async def t_safe_call_passthrough():
    async def already_errored():
        raise InsufficientBalanceError(available=10, required=100, asset="ETH")
    try:
        await safe_call(already_errored, tool_name="test")
        assert False, "Should have raised"
    except InsufficientBalanceError:
        pass  # Correct — passed through, not re-wrapped
atest("safe_call passes through SkillError subclasses", t_safe_call_passthrough())

# A14: Error hierarchy
def t_hierarchy():
    assert issubclass(RateLimitError, TransientError)
    assert issubclass(TransientError, SkillError)
    assert issubclass(InsufficientGasError, InsufficientBalanceError)
    assert issubclass(SlippageExceededError, ChainError)
    assert issubclass(InvalidParameterError, UserInputError)
test("Error hierarchy is correct", t_hierarchy)

print(f"\n{'='*50}")
print(f"Results: {PASSED}/{PASSED+FAILED} passed")
print(f"{'='*50}")
