"""Shared utilities for Starchild official-skills."""
from .errors import (  # noqa: F401
    SkillError,
    TransientError, RateLimitError, ServiceUnavailableError, TimeoutError,
    UserInputError, InvalidParameterError, UnsupportedAssetError,
    InsufficientBalanceError, InsufficientGasError,
    ChainError, TransactionRevertedError, SlippageExceededError, NonceError,
    safe_call, safe_call_sync,
)
from .response import ok, fail, fmt_price, fmt_balance, fmt_table  # noqa: F401
from .retry import with_retry, RetryConfig, async_retry, sync_retry, PRESETS  # noqa: F401
from .crypto_safety import (  # noqa: F401
    get_finality_info, format_finality_message,
    estimate_gas_needed, suggest_slippage, verification_checklist,
)
