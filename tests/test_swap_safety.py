"""
Unit tests for patches/1inch/swap_safety.py

The patch module defines logic as code-string templates.
We extract and test the core logic by reimplementing the functions
from the documented behavior, validating they match the patch specs.
"""
import importlib.util
import os
import pytest

# Load the module (can't use normal import — "1inch" starts with a digit)
_spec = importlib.util.spec_from_file_location(
    "swap_safety",
    os.path.join(os.path.dirname(__file__), "..", "patches", "1inch", "swap_safety.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


class TestPatchModuleStructure:
    """Verify the patch module exports the expected code strings."""

    def test_has_pre_swap_check(self):
        assert hasattr(_mod, "PRE_SWAP_CHECK")
        assert "_pre_swap_check" in _mod.PRE_SWAP_CHECK

    def test_has_slippage_default(self):
        assert hasattr(_mod, "SLIPPAGE_DEFAULT")
        assert "DEFAULT_SLIPPAGE" in _mod.SLIPPAGE_DEFAULT
        assert "_safe_slippage" in _mod.SLIPPAGE_DEFAULT

    def test_has_post_swap_verification(self):
        assert hasattr(_mod, "POST_SWAP_VERIFICATION")
        assert "_post_swap_message" in _mod.POST_SWAP_VERIFICATION

    def test_has_fusion_status_messages(self):
        assert hasattr(_mod, "FUSION_STATUS_MESSAGES")
        assert "FUSION_STATUS_MAP" in _mod.FUSION_STATUS_MESSAGES


# ── Extract and compile slippage logic for direct testing ──
# The slippage patch is pure sync, so we can exec it into a test class.

def _make_helper(code_string, extra_globals=None):
    """Exec a patch code string inside a throwaway class and return an instance.

    All patch code strings are 4-space indented (class-body level), so
    wrapping with ``class H:\\n`` + the raw string works directly.
    """
    globs = extra_globals or {}
    ns = {}
    exec("class H:\n" + code_string + "\nhelper = H()", globs, ns)
    return ns["helper"]


def _make_slippage_helper():
    return _make_helper(_mod.SLIPPAGE_DEFAULT, {"float": float})


def _make_post_swap_helper():
    return _make_helper(_mod.POST_SWAP_VERIFICATION)


def _make_fusion_helper():
    return _make_helper(_mod.FUSION_STATUS_MESSAGES)


@pytest.fixture(scope="module")
def slip():
    return _make_slippage_helper()


@pytest.fixture(scope="module")
def post():
    return _make_post_swap_helper()


@pytest.fixture(scope="module")
def fusion():
    return _make_fusion_helper()


# ── Pre-swap check logic (tested via patch code analysis) ──

class TestPreSwapCheckSpec:
    """Test the spec defined in PRE_SWAP_CHECK code string."""

    def test_rejects_non_positive(self):
        code = _mod.PRE_SWAP_CHECK
        assert "float(src_amount) <= 0" in code
        assert "must be positive" in code.lower()

    def test_warns_on_large_swaps(self):
        code = _mod.PRE_SWAP_CHECK
        assert "10000" in code  # $10k threshold
        assert "splitting" in code.lower() or "smaller orders" in code.lower()

    def test_is_async(self):
        assert "async def _pre_swap_check" in _mod.PRE_SWAP_CHECK


# ── Slippage validation ──

class TestSlippageDefault:
    def test_normal_slippage_passthrough(self, slip):
        val, warn = slip._safe_slippage(0.5, "ETH", "USDC")
        assert val == 0.5
        assert warn == ""

    def test_excessive_slippage_blocked(self, slip):
        val, warn = slip._safe_slippage(6.0, "ETH", "USDC")
        assert val is None
        assert "dangerously high" in warn.lower() or "max" in warn.lower()

    def test_max_boundary_allowed(self, slip):
        val, warn = slip._safe_slippage(5.0, "ETH", "USDC")
        assert val == 5.0

    def test_high_slippage_warned(self, slip):
        val, warn = slip._safe_slippage(3.5, "ETH", "USDC")
        assert val == 3.5
        assert "mev" in warn.lower() or "high" in warn.lower()

    def test_stablecoin_high_slippage_warned(self, slip):
        val, warn = slip._safe_slippage(1.0, "USDC", "USDT")
        assert val == 1.0
        assert "stablecoin" in warn.lower()

    def test_stablecoin_low_slippage_ok(self, slip):
        val, warn = slip._safe_slippage(0.1, "USDC", "DAI")
        assert val == 0.1
        assert warn == ""

    def test_stablecoin_case_insensitive(self, slip):
        val, warn = slip._safe_slippage(1.0, "usdc", "usdt")
        assert val == 1.0
        assert "stablecoin" in warn.lower()

    def test_default_slippage_constants(self, slip):
        assert slip.DEFAULT_SLIPPAGE["stablecoin"] == 0.1
        assert slip.DEFAULT_SLIPPAGE["major"] == 0.5
        assert slip.DEFAULT_SLIPPAGE["default"] == 1.0
        assert slip.DEFAULT_SLIPPAGE["max"] == 5.0


# ── Post-swap verification ──

class TestPostSwapVerification:
    def test_basic_message(self, post):
        msg = post._post_swap_message(
            "ethereum", "0xabc123", "ETH", "1.5", "USDC"
        )
        assert "1.5" in msg
        assert "ETH" in msg
        assert "USDC" in msg
        assert "0xabc123" in msg

    def test_includes_verification_steps(self, post):
        msg = post._post_swap_message(
            "ethereum", "0xabc", "ETH", "1.0", "USDC"
        )
        assert "wallet_balance" in msg
        assert "Verify" in msg

    def test_with_expected_dst(self, post):
        msg = post._post_swap_message(
            "ethereum", "0xdef", "ETH", "1.0", "USDC",
            expected_dst="3500"
        )
        assert "3500" in msg
        assert "Expected" in msg

    def test_without_expected_dst(self, post):
        msg = post._post_swap_message(
            "arbitrum", "0x999", "USDC", "1000", "ETH"
        )
        assert "Expected" not in msg


# ── Fusion status ──

class TestFusionStatus:
    def test_known_statuses(self, fusion):
        for status in [
            "pending", "order_accepted", "pre_swap_done",
            "swap_done", "executed", "expired", "cancelled", "failed",
        ]:
            msg = fusion._format_fusion_status(status)
            assert len(msg) > 0
            assert "unknown" not in msg.lower()

    def test_unknown_status(self, fusion):
        msg = fusion._format_fusion_status("weird_new_status")
        assert "unknown" in msg.lower()

    def test_partial_fill(self, fusion):
        msg = fusion._format_fusion_status(
            "order_accepted", {"fill_percentage": 60}
        )
        assert "60%" in msg

    def test_full_fill_no_percentage(self, fusion):
        msg = fusion._format_fusion_status(
            "executed", {"fill_percentage": 100}
        )
        assert "100%" not in msg

    def test_case_insensitive(self, fusion):
        msg = fusion._format_fusion_status("PENDING")
        assert "⏳" in msg or "pending" in msg.lower()

    def test_status_map_has_emojis(self, fusion):
        for status, msg in fusion.FUSION_STATUS_MAP.items():
            assert any(
                c in msg for c in "⏳📋🔄✅❌🔍"
            ), f"Status '{status}' missing emoji"
