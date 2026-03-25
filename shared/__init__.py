"""Shared patches for Starchild official-skills improvement."""
from .errors import (
    SkillError,
    TransientError, RateLimitError, ServiceUnavailableError, TimeoutError,
    UserInputError, InvalidParameterError, UnsupportedAssetError,
    InsufficientBalanceError, InsufficientGasError,
    ChainError, TransactionRevertedError, SlippageExceededError, NonceError,
    safe_call,
)
from .response import ok, fail, fmt_price, fmt_balance, fmt_table
from .retry import with_retry, RetryConfig, retry_api_call
from .crypto_safety import (
    get_finality_info, format_finality_message,
    estimate_gas_needed, suggest_slippage, verification_checklist,
)
