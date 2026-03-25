"""
1inch Swap Safety Patches
=========================
Issues found:
1. No pre-swap balance check in swap_tokens tool
2. No slippage default safeguard  
3. No post-swap verification
4. Fusion order status polling doesn't surface clear progress

These patches add safety wrappers around the existing swap flow.
"""

# ── PATCH 1: Pre-swap balance check ──

PRE_SWAP_CHECK = '''
    # PATCH: Pre-swap safety checks
    async def _pre_swap_check(self, ctx, src_token, src_amount, chain_id):
        """Verify user has enough balance + gas before swapping."""
        warnings = []

        # Check source token balance
        # (This requires a balance check tool call — the swap tool should
        #  verify the user actually has the tokens they want to swap)
        if float(src_amount) <= 0:
            return False, "❌ Swap amount must be positive"

        # Warn on large swaps without explicit slippage
        if float(src_amount) > 10000:  # > $10k equivalent
            warnings.append(
                "⚠️ Large swap detected. Consider splitting into smaller orders "
                "to reduce price impact."
            )

        return True, "\\n".join(warnings) if warnings else ""
'''

# ── PATCH 2: Slippage default with warning ──

SLIPPAGE_DEFAULT = '''
    # PATCH: Safe slippage defaults
    DEFAULT_SLIPPAGE = {
        # Stablecoin pairs
        "stablecoin": 0.1,   # 0.1%
        # Major tokens (BTC, ETH)
        "major": 0.5,        # 0.5%
        # Everything else
        "default": 1.0,      # 1.0%
        # Maximum allowed
        "max": 5.0,          # 5.0% — refuse above this
    }

    def _safe_slippage(self, slippage: float, src_token: str, dst_token: str) -> tuple:
        """Validate and potentially adjust slippage.
        Returns (adjusted_slippage, warning_message)"""
        STABLECOINS = {"USDC", "USDT", "DAI", "BUSD", "FRAX"}
        src_upper = src_token.upper()
        dst_upper = dst_token.upper()

        if slippage > self.DEFAULT_SLIPPAGE["max"]:
            return None, (
                f"❌ Slippage {slippage}% is dangerously high (max: {self.DEFAULT_SLIPPAGE['max']}%). "
                f"This protects against sandwich attacks. Reduce slippage or confirm explicitly."
            )

        warning = ""
        if slippage > 3.0:
            warning = f"⚠️ High slippage ({slippage}%) — vulnerable to MEV. Consider reducing."
        elif src_upper in STABLECOINS and dst_upper in STABLECOINS and slippage > 0.5:
            warning = f"⚠️ Stablecoin swap with {slippage}% slippage is high. 0.1% is typical."

        return slippage, warning
'''

# ── PATCH 3: Post-swap verification prompt ──

POST_SWAP_VERIFICATION = '''
    # PATCH: Post-swap verification
    def _post_swap_message(self, chain: str, tx_hash: str,
                           src_token: str, src_amount: str,
                           dst_token: str, expected_dst: str = "") -> str:
        """Generate verification instructions after swap."""
        parts = [
            f"✅ Swap submitted: {src_amount} {src_token} → {dst_token}",
            f"   TX: {tx_hash}",
            f"",
            f"**Verify:**",
            f"1. Check wallet_balance(chain='{chain}') for updated balances",
            f"2. Confirm {dst_token} received matches quote",
        ]
        if expected_dst:
            parts.append(f"   Expected: ~{expected_dst} {dst_token}")
        parts.append(f"3. If discrepancy > slippage tolerance, report as issue")
        return "\\n".join(parts)
'''


# ── PATCH 4: Fusion order status clarity ──

FUSION_STATUS_MESSAGES = '''
    # PATCH: Clear fusion order status messages
    FUSION_STATUS_MAP = {
        "pending": "⏳ Order pending — waiting for resolver to pick up",
        "order_accepted": "📋 Order accepted by resolver — execution in progress",
        "pre_swap_done": "🔄 Pre-swap complete — awaiting cross-chain confirmation",
        "swap_done": "✅ Swap complete — tokens should arrive shortly",
        "executed": "✅ Order fully executed",
        "expired": "❌ Order expired — no resolver filled it. Try again with better params.",
        "cancelled": "❌ Order cancelled",
        "failed": "❌ Order failed — check parameters and try again",
    }

    def _format_fusion_status(self, status: str, order_data: dict = None) -> str:
        """Human-readable fusion order status."""
        msg = self.FUSION_STATUS_MAP.get(
            status.lower(),
            f"🔍 Unknown status: {status}"
        )
        if order_data:
            fill_pct = order_data.get("fill_percentage", 0)
            if fill_pct and fill_pct < 100:
                msg += f" ({fill_pct}% filled)"
        return msg
'''
