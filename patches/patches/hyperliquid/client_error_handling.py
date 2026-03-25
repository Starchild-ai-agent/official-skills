"""
Hyperliquid client.py — Critical Error Handling Patches
=======================================================
Patches for 3 CRITICAL silent exception locations.

How to apply:
  Each function below replaces the corresponding code block.
  Search for the original code (shown in OLD/NEW comments), then replace.
"""

# ─────────────────────────────────────────────────────
# PATCH 1: Line ~160 — spot_meta loading failure
# ─────────────────────────────────────────────────────
# PROBLEM: If spot metadata fails to load, the client silently sets
# self._spot_meta = {} — then later, any spot operation returns
# "asset not found" instead of "metadata unavailable".
# Small models get confused by "asset not found" when the asset exists.

"""
OLD (line ~160-165):
            except Exception:
                self._spot_meta = {}

NEW:
"""
PATCH_1_SPOT_META = '''
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to load spot metadata: {e}")
                self._spot_meta = {}
                self._spot_meta_error = str(e)  # Track degraded state
'''

# Then in _resolve_any_asset, add degraded-state warning:
PATCH_1_RESOLVE_ASSET_ADDITION = '''
    async def _resolve_any_asset(self, coin: str) -> int:
        """Resolve coin name to asset index — tries perps, builder perps, then spot."""
        await self._ensure_meta()
        try:
            return await self._resolve_asset(coin)
        except ValueError:
            pass
        # Check if spot metadata failed to load
        if hasattr(self, '_spot_meta_error') and self._spot_meta_error:
            raise ValueError(
                f"Cannot resolve spot asset '{coin}': spot metadata failed to load "
                f"({self._spot_meta_error}). Retry or check Hyperliquid API status."
            )
        # Try spot (exact then case-insensitive) — original logic continues...
'''


# ─────────────────────────────────────────────────────
# PATCH 2: Line ~331 and ~596 — abstraction_state fallback
# ─────────────────────────────────────────────────────
# PROBLEM: If abstraction state query fails, the client assumes "default" mode.
# But if the user IS on unified account, this leads to wrong balance reporting
# ($0 perp balance when funds are actually in spot).
# This is DANGEROUS for trading — small model could report "no funds" and
# refuse to place orders.

"""
OLD (line ~331):
            except Exception:
                current_mode = "default"

NEW:
"""
PATCH_2_ABSTRACTION_STATE = '''
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Could not detect account abstraction mode: {e}. "
                    f"Defaulting to 'default' — balance may be inaccurate if "
                    f"account is in unified mode."
                )
                current_mode = "default"
                _abstraction_degraded = True  # Flag for downstream logic
'''

# Add balance cross-check after getting balances:
PATCH_2_BALANCE_CROSSCHECK = '''
            # PATCH: Cross-check for degraded abstraction state
            # If we couldn't detect mode and both perp+spot balances are near zero,
            # add a warning — the user might have funds in the other mode.
            if _abstraction_degraded and total_balance < 1.0:
                result["_warning"] = (
                    "⚠️ Account abstraction mode could not be detected. "
                    "If you have deposited funds, they may be in unified/spot mode. "
                    "Check both `hl_account` and `hl_balances` to confirm."
                )
'''


# ─────────────────────────────────────────────────────
# PATCH 3: Line ~666 — order validation non-blocking catch
# ─────────────────────────────────────────────────────
# PROBLEM: If order validation fails (e.g., can't fetch market data to
# check margin), it logs a warning and continues to submit the order.
# This is correct for resilience, but the warning is INVISIBLE to the LLM.
# The order might then fail on the exchange side with a cryptic error.

"""
OLD (line ~665-668):
            except ValueError:
                # Re-raise validation errors
                raise
            except Exception as e:
                # Don't block order on validation errors
                logger.warning(f"Order validation error (non-blocking): {e}")

NEW:
"""
PATCH_3_ORDER_VALIDATION = '''
            except ValueError:
                # Re-raise validation errors (these are definitive failures)
                raise
            except Exception as e:
                # Don't block order, but surface warning in response
                logger.warning(f"Order validation error (non-blocking): {e}")
                _validation_warning = (
                    f"⚠️ Pre-order validation could not complete: {e}. "
                    f"Order will be submitted anyway — monitor for exchange-side rejection."
                )
'''

# Then in the order response, include the warning:
PATCH_3_ORDER_RESPONSE = '''
        # Include validation warning in successful response
        if _validation_warning:
            result["validation_warning"] = _validation_warning
'''
