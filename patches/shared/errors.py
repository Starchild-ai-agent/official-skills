"""
Structured Error Taxonomy for Crypto Skills
============================================
解决问题: except: pass / except Exception: return None 让小模型收到空结果无法自诊断。
方案: 分层异常 + 自动分类 + 小模型友好的错误消息。

关键设计:
1. 每个异常自带 `user_message` — 小模型直接转述给用户
2. 每个异常自带 `suggestion` — 小模型知道该建议什么
3. 异常层级按可恢复性分类 — 小模型知道是该 retry 还是该放弃

用法:
    from shared.errors import (
        InsufficientBalanceError, RateLimitError,
        ChainError, safe_call
    )

    # 方法1: 直接抛出
    raise InsufficientBalanceError(
        available=100, required=500, asset="USDC",
        suggestion="Deposit more USDC or reduce position size"
    )

    # 方法2: safe_call 包装现有函数
    result = await safe_call(
        risky_api_function, args,
        tool_name="hyperliquid/hl_order",
        fallback_msg="Failed to place order"
    )
"""


class SkillError(Exception):
    """Base error for all skill failures. Structured for LLM consumption."""

    code: str = "SKILL_ERROR"
    retryable: bool = False

    def __init__(self, message: str, suggestion: str = "",
                 tool_name: str = "", **context):
        self.message = message
        self.suggestion = suggestion
        self.tool_name = tool_name
        self.context = context
        super().__init__(self.format())

    def format(self) -> str:
        """Format for small model consumption"""
        parts = [f"❌ [{self.code}]"]
        if self.tool_name:
            parts[0] += f" {self.tool_name}:"
        parts[0] += f" {self.message}"

        if self.context:
            for k, v in self.context.items():
                parts.append(f"  {k}: {v}")

        if self.suggestion:
            parts.append(f"  → Suggestion: {self.suggestion}")
        if self.retryable:
            parts.append("  ℹ️ This error is transient — retry may succeed")
        return '\n'.join(parts)


# ── Transient Errors (retryable) ──────────────────────────

class TransientError(SkillError):
    retryable = True


class RateLimitError(TransientError):
    code = "RATE_LIMITED"

    def __init__(self, service: str, retry_after: int = None, **kw):
        suggestion = f"Wait {retry_after}s before retrying" if retry_after else "Wait and retry"
        super().__init__(
            f"{service} rate limit reached",
            suggestion=suggestion,
            retry_after=retry_after,
            **kw
        )


class ServiceUnavailableError(TransientError):
    code = "SERVICE_DOWN"

    def __init__(self, service: str, status: int = None, **kw):
        super().__init__(
            f"{service} is temporarily unavailable (HTTP {status or '?'})",
            suggestion="Try again in 30-60 seconds",
            **kw
        )


class TimeoutError(TransientError):
    code = "TIMEOUT"

    def __init__(self, service: str, timeout_seconds: float = None, **kw):
        super().__init__(
            f"{service} request timed out after {timeout_seconds}s",
            suggestion="Retry with a simpler query or increase timeout",
            **kw
        )


# ── User Errors (not retryable, user must fix input) ──────

class UserInputError(SkillError):
    code = "BAD_INPUT"


class InvalidParameterError(UserInputError):
    code = "INVALID_PARAM"

    def __init__(self, param: str, got, expected: str = "", **kw):
        msg = f"Invalid parameter '{param}': got {repr(got)}"
        if expected:
            msg += f", expected {expected}"
        super().__init__(msg, **kw)


class UnsupportedAssetError(UserInputError):
    code = "UNSUPPORTED_ASSET"

    def __init__(self, asset: str, supported: list = None, **kw):
        suggestion = ""
        if supported:
            suggestion = f"Supported assets include: {', '.join(supported[:10])}"
        super().__init__(
            f"Asset '{asset}' is not supported on this service",
            suggestion=suggestion,
            **kw
        )


# ── Balance & Margin Errors ──────────────────────────────

class InsufficientBalanceError(SkillError):
    code = "INSUFFICIENT_BALANCE"

    def __init__(self, available: float, required: float,
                 asset: str = "", **kw):
        suggestion = kw.pop('suggestion',
                            f"Need {required - available:.4f} more {asset}. "
                            f"Deposit funds or reduce the amount."
                            )
        super().__init__(
            f"Insufficient {asset} balance",
            suggestion=suggestion,
            available=f"{available:.4f} {asset}",
            required=f"{required:.4f} {asset}",
            shortfall=f"{required - available:.4f} {asset}",
            **kw
        )


class InsufficientGasError(InsufficientBalanceError):
    code = "INSUFFICIENT_GAS"

    def __init__(self, chain: str, available: float, estimated_gas: float, **kw):
        native = {"ethereum": "ETH", "arbitrum": "ETH", "base": "ETH",
                  "optimism": "ETH", "polygon": "MATIC", "solana": "SOL"}.get(chain, "native token")
        super().__init__(
            available=available, required=estimated_gas, asset=native,
            suggestion=f"Need {native} on {chain} for gas. Bridge or deposit {native} first.",
            **kw
        )


# ── Chain / Protocol Errors ──────────────────────────────

class ChainError(SkillError):
    code = "CHAIN_ERROR"


class TransactionRevertedError(ChainError):
    code = "TX_REVERTED"

    def __init__(self, tx_hash: str = "", revert_reason: str = "", **kw):
        suggestion = kw.pop('suggestion', "Check transaction on block explorer for details")
        super().__init__(
            f"Transaction reverted{f': {revert_reason}' if revert_reason else ''}",
            suggestion=suggestion,
            tx_hash=tx_hash or "unknown",
            **kw
        )


class SlippageExceededError(ChainError):
    code = "SLIPPAGE_EXCEEDED"

    def __init__(self, expected_price: float, actual_price: float,
                 max_slippage: float = None, **kw):
        actual_slippage = abs(actual_price - expected_price) / expected_price * 100
        super().__init__(
            f"Price slippage too high: {actual_slippage:.2f}%"
            f"{f' (max allowed: {max_slippage}%)' if max_slippage else ''}",
            suggestion="Increase slippage tolerance or reduce order size",
            expected_price=expected_price,
            actual_price=actual_price,
            slippage_pct=f"{actual_slippage:.2f}%",
            **kw
        )


class NonceError(ChainError):
    code = "NONCE_ERROR"

    def __init__(self, expected: int = None, got: int = None, **kw):
        super().__init__(
            "Transaction nonce conflict",
            suggestion="Wait for pending transactions to confirm, then retry",
            expected_nonce=expected,
            got_nonce=got,
            **kw
        )


# ── Safe Call Wrapper ────────────────────────────────────

async def safe_call(fn, *args, tool_name: str = "",
                    fallback_msg: str = "Operation failed", **kwargs):
    """
    Wrap any async function call with structured error handling.
    Never returns None silently — always returns result or raises SkillError.

    替代 try/except: pass 模式:
        # ❌ Before (小模型收到 None 无法诊断)
        try:
            result = await api_call()
        except:
            return None

        # ✅ After (小模型收到结构化错误)
        result = await safe_call(api_call, tool_name="skill/tool")
    """
    try:
        result = await fn(*args, **kwargs)
        if result is None:
            raise SkillError(
                f"{fallback_msg}: API returned None (empty response)",
                tool_name=tool_name,
                suggestion="The API may be down or the request parameters invalid"
            )
        return result
    except SkillError:
        raise  # Already structured, pass through
    except Exception as e:
        # Classify common exceptions
        err_str = str(e).lower()
        if '429' in err_str or 'rate limit' in err_str:
            raise RateLimitError(service=tool_name) from e
        if '503' in err_str or '502' in err_str:
            raise ServiceUnavailableError(service=tool_name) from e
        if 'timeout' in err_str:
            raise TimeoutError(service=tool_name) from e
        if 'insufficient' in err_str and ('balance' in err_str or 'fund' in err_str):
            raise InsufficientBalanceError(
                available=0, required=0, asset="unknown",
                suggestion="Check your balance and try again"
            ) from e

        # Generic fallback — still structured
        raise SkillError(
            f"{fallback_msg}: {type(e).__name__}: {e}",
            tool_name=tool_name,
            suggestion="Check parameters and retry. If persistent, report as bug."
        ) from e
