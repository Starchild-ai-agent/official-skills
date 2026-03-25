"""
Unit tests for patches/aave/lending_safety.py

The patch module defines logic as code-string templates.
We compile and test the core functions directly.
"""
import importlib.util
import os
import pytest

# Load the module
_spec = importlib.util.spec_from_file_location(
    "lending_safety",
    os.path.join(
        os.path.dirname(__file__), "..", "patches", "aave", "lending_safety.py"
    ),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def _make_helper():
    """Compile all patches into a single helper class instance."""
    lines = ["class H:"]
    for attr in ["HEALTH_FACTOR_CHECK", "ERROR_ENRICHMENT", "POSITION_SUMMARY"]:
        code = getattr(_mod, attr)
        # The code strings are indented for class body — keep that
        lines.append(code)
    lines.append("helper = H()")
    ns = {"float": float, "int": int}
    exec("\n".join(lines), ns)
    return ns["helper"]


@pytest.fixture(scope="module")
def helper():
    return _make_helper()


class TestPatchModuleStructure:
    def test_has_health_factor_check(self):
        assert hasattr(_mod, "HEALTH_FACTOR_CHECK")
        assert "_check_health_factor" in _mod.HEALTH_FACTOR_CHECK

    def test_has_error_enrichment(self):
        assert hasattr(_mod, "ERROR_ENRICHMENT")
        assert "_classify_aave_error" in _mod.ERROR_ENRICHMENT

    def test_has_position_summary(self):
        assert hasattr(_mod, "POSITION_SUMMARY")
        assert "_format_position_summary" in _mod.POSITION_SUMMARY


# ── Health factor classification ──

class TestHealthFactorCheck:
    @pytest.mark.parametrize("hf,expected_level", [
        (3.0, "safe"),
        (2.5, "safe"),
        (1.7, "moderate"),
        (1.3, "risky"),
        (1.1, "danger"),
        (1.0, "liquidatable"),
        (0.5, "liquidatable"),
    ])
    def test_risk_levels(self, helper, hf, expected_level):
        result = helper._check_health_factor(hf)
        assert result["level"] == expected_level
        assert result["health_factor"] == hf

    def test_safe_no_warn(self, helper):
        result = helper._check_health_factor(3.0)
        assert result["should_warn"] is False
        assert result["should_block"] is False

    def test_risky_warns(self, helper):
        result = helper._check_health_factor(1.3)
        assert result["should_warn"] is True
        assert result["should_block"] is False

    def test_danger_warns(self, helper):
        result = helper._check_health_factor(1.1)
        assert result["should_warn"] is True
        assert result["should_block"] is False

    def test_liquidatable_blocks(self, helper):
        result = helper._check_health_factor(0.9)
        assert result["should_block"] is True

    def test_message_has_emoji(self, helper):
        for hf in [3.0, 1.7, 1.3, 1.1, 0.9]:
            result = helper._check_health_factor(hf)
            assert any(
                c in result["message"]
                for c in "🟢🟡🟠🔴💀⚠️"
            )

    def test_boundary_2_0_is_safe(self, helper):
        result = helper._check_health_factor(2.0)
        assert result["level"] == "safe"

    def test_boundary_1_5_is_moderate(self, helper):
        result = helper._check_health_factor(1.5)
        assert result["level"] == "moderate"

    def test_boundary_1_2_is_risky(self, helper):
        result = helper._check_health_factor(1.2)
        assert result["level"] == "risky"

    def test_boundary_1_05_is_danger(self, helper):
        result = helper._check_health_factor(1.05)
        assert result["level"] == "danger"


# ── Pre-borrow warning ──

class TestPreBorrowWarning:
    def test_safe_borrow(self, helper):
        msg = helper._pre_borrow_warning(
            current_hf=3.0, projected_hf=2.5,
            borrow_amount=1000, borrow_asset="USDC"
        )
        assert "1000" in msg
        assert "USDC" in msg
        assert "3.00" in msg
        assert "2.50" in msg
        # Safe borrow — no blocking message
        assert "liquidation zone" not in msg.lower()

    def test_risky_borrow_warns(self, helper):
        msg = helper._pre_borrow_warning(
            current_hf=2.0, projected_hf=1.3,
            borrow_amount=5000, borrow_asset="ETH"
        )
        assert "⚠️" in msg
        assert "1.30" in msg

    def test_liquidation_zone_blocks(self, helper):
        msg = helper._pre_borrow_warning(
            current_hf=1.5, projected_hf=1.0,
            borrow_amount=10000, borrow_asset="DAI"
        )
        assert "❌" in msg
        assert "liquidation zone" in msg.lower()


# ── Error enrichment ──

class TestErrorEnrichment:
    def test_health_factor_error(self, helper):
        msg = helper._classify_aave_error(
            "health factor below threshold", "borrow"
        )
        assert "❌" in msg
        assert "collateral" in msg.lower()

    def test_insufficient_liquidity(self, helper):
        msg = helper._classify_aave_error(
            "insufficient liquidity available", "borrow"
        )
        assert "liquidity" in msg.lower()

    def test_not_collateral(self, helper):
        msg = helper._classify_aave_error(
            "asset not enabled as collateral", "borrow"
        )
        assert "enable" in msg.lower()

    def test_allowance_error(self, helper):
        msg = helper._classify_aave_error(
            "ERC20: insufficient allowance", "deposit"
        )
        assert "approv" in msg.lower()

    def test_unknown_error_passthrough(self, helper):
        msg = helper._classify_aave_error(
            "some random error 0x1234", "withdraw"
        )
        assert "some random error" in msg
        assert "withdraw" in msg

    def test_operation_name_in_output(self, helper):
        msg = helper._classify_aave_error("health factor low", "repay")
        assert "repay" in msg


# ── Position summary ──

class TestPositionSummary:
    def test_basic_summary(self, helper):
        positions = {
            "health_factor": 2.5,
            "total_collateral_usd": 10000,
            "total_borrowed_usd": 3000,
            "available_borrow_usd": 4000,
            "net_worth_usd": 7000,
        }
        msg = helper._format_position_summary(positions)
        assert "2.50" in msg
        assert "Aave" in msg
        assert "Collateral" in msg
        assert "Borrowed" in msg

    def test_risky_position_shows_warning(self, helper):
        positions = {
            "health_factor": 1.25,
            "total_collateral_usd": 5000,
            "total_borrowed_usd": 3800,
            "available_borrow_usd": 200,
            "net_worth_usd": 1200,
        }
        msg = helper._format_position_summary(positions)
        assert "🟠" in msg or "risk" in msg.lower()

    def test_safe_position_no_extra_warning(self, helper):
        positions = {
            "health_factor": 5.0,
            "total_collateral_usd": 50000,
            "total_borrowed_usd": 5000,
            "available_borrow_usd": 30000,
            "net_worth_usd": 45000,
        }
        msg = helper._format_position_summary(positions)
        assert "🟢" in msg

    def test_missing_fields_default_to_zero(self, helper):
        positions = {"health_factor": 2.0}
        msg = helper._format_position_summary(positions)
        # Should not crash; uses .get(key, 0) defaults
        assert "2.00" in msg
