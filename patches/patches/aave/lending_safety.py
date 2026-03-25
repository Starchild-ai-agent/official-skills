"""
Aave Lending Safety Patches
============================
Issues:
1. No health factor warning before borrow
2. No liquidation threshold education in error messages  
3. Missing "are you sure?" for risky operations
"""

# ── PATCH 1: Health factor awareness ──

HEALTH_FACTOR_CHECK = '''
    # PATCH: Pre-borrow health factor check
    RISK_LEVELS = {
        "safe": (2.0, float("inf"), "🟢 Safe — health factor above 2.0"),
        "moderate": (1.5, 2.0, "🟡 Moderate risk — monitor regularly"),
        "risky": (1.2, 1.5, "🟠 High risk — consider reducing borrow"),
        "danger": (1.05, 1.2, "🔴 Danger — close to liquidation!"),
        "liquidatable": (0, 1.05, "💀 LIQUIDATION ZONE — immediate action needed"),
    }

    def _check_health_factor(self, health_factor: float) -> dict:
        """Classify health factor risk and generate warning."""
        for level, (low, high, msg) in self.RISK_LEVELS.items():
            if low <= health_factor < high:
                return {
                    "level": level,
                    "health_factor": health_factor,
                    "message": msg,
                    "should_warn": level in ("risky", "danger", "liquidatable"),
                    "should_block": level == "liquidatable",
                }
        return {"level": "unknown", "health_factor": health_factor, "message": "⚠️ Unknown state"}

    def _pre_borrow_warning(self, current_hf: float, projected_hf: float,
                            borrow_amount: float, borrow_asset: str) -> str:
        """Generate warning message before borrow."""
        current = self._check_health_factor(current_hf)
        projected = self._check_health_factor(projected_hf)

        parts = [
            f"**Borrow {borrow_amount} {borrow_asset} Risk Assessment:**",
            f"Current health factor: {current_hf:.2f} {current['message']}",
            f"After borrow: ~{projected_hf:.2f} {projected['message']}",
        ]

        if projected["should_block"]:
            parts.append(
                "\\n❌ This borrow would put you in the liquidation zone. "
                "Reduce borrow amount or add more collateral first."
            )
        elif projected["should_warn"]:
            parts.append(
                f"\\n⚠️ Health factor drops from {current_hf:.2f} → {projected_hf:.2f}. "
                "A 20% price drop in your collateral could trigger liquidation. "
                "Consider borrowing less or adding collateral."
            )

        return "\\n".join(parts)
'''


# ── PATCH 2: Error message enrichment ──

ERROR_ENRICHMENT = '''
    # PATCH: Aave-specific error classification
    def _classify_aave_error(self, error_str: str, operation: str) -> str:
        """Enrich Aave errors with actionable context."""
        err_lower = error_str.lower()

        if "health factor" in err_lower or "liquidation" in err_lower:
            return (
                f"❌ {operation}: Health factor too low.\\n"
                f"  → Your collateral doesn't support this borrow amount.\\n"
                f"  → Either deposit more collateral or reduce the borrow."
            )

        if "insufficient" in err_lower and "liquidity" in err_lower:
            return (
                f"❌ {operation}: Insufficient liquidity in the pool.\\n"
                f"  → The asset has high utilization — not enough available to borrow.\\n"
                f"  → Try a smaller amount or wait for liquidity to return."
            )

        if "not collateral" in err_lower or "not enabled" in err_lower:
            return (
                f"❌ {operation}: Asset not enabled as collateral.\\n"
                f"  → You need to enable this asset as collateral first.\\n"
                f"  → Use the Aave 'set collateral' function before borrowing."
            )

        if "allowance" in err_lower or "approve" in err_lower:
            return (
                f"❌ {operation}: Token approval needed.\\n"
                f"  → Approve the Aave contract to spend your tokens first.\\n"
                f"  → This requires a separate transaction before the deposit."
            )

        # Default
        return f"❌ {operation}: {error_str}"
'''


# ── PATCH 3: Position summary helper ──

POSITION_SUMMARY = '''
    def _format_position_summary(self, positions: dict) -> str:
        """Format Aave position for clear model consumption."""
        parts = ["**Aave Position Summary:**"]

        hf = positions.get("health_factor", 0)
        risk = self._check_health_factor(hf)

        parts.append(f"Health Factor: {hf:.2f} {risk['message']}")
        parts.append(f"Total Collateral: ${positions.get('total_collateral_usd', 0):,.2f}")
        parts.append(f"Total Borrowed: ${positions.get('total_borrowed_usd', 0):,.2f}")
        parts.append(f"Available to Borrow: ${positions.get('available_borrow_usd', 0):,.2f}")
        parts.append(f"Net Worth: ${positions.get('net_worth_usd', 0):,.2f}")

        if risk["should_warn"]:
            parts.append(f"\\n{risk['message']}")

        return "\\n".join(parts)
'''
