"""
Hyperliquid API Client — wraps /info (read-only) and /exchange (signed) endpoints.

Uses the hyperliquid-python-sdk Info class for reads, and custom signing
(via wallet service) for exchange actions.
"""

import logging
import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional

import aiohttp

from .signing import sign_l1_action, sign_user_action, sign_user_set_abstraction

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.hyperliquid.xyz"
DEFAULT_SLIPPAGE = 0.03  # 3% for market orders


def float_to_wire(x: float) -> str:
    """Convert a float to a string matching Hyperliquid's server-side normalization.

    Matches the official Hyperliquid Python SDK: rounds to 8 decimal places,
    then strips trailing zeros via Decimal.normalize().
    """
    rounded = f"{x:.8f}"
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError(f"float_to_wire: rounding loses precision for {x}")
    if rounded == "-0.00000000":
        rounded = "0.00000000"
    normalized = Decimal(rounded).normalize()
    return f"{normalized:f}"

# Hyperliquid bridge contract (for USDC deposits)
BRIDGE_ADDRESS = "0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7"

# USDC on Arbitrum
USDC_ADDRESS = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
USDC_DECIMALS = 6
ARBITRUM_CHAIN_ID = 42161
MIN_DEPOSIT_USDC = 5


class HyperliquidClient:
    """
    Async Hyperliquid client.

    - Info methods: POST to /info (no auth)
    - Exchange methods: POST to /exchange (signed)
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get(
            "HYPERLIQUID_API_URL", DEFAULT_API_URL
        )
        # Cached metadata
        self._meta: Optional[dict] = None
        self._spot_meta: Optional[dict] = None
        self._name_to_index: Dict[str, int] = {}
        self._spot_name_to_index: Dict[str, int] = {}
        self._spot_mid_key: Dict[str, str] = {}  # user name → allMids key
        self._sz_decimals: Dict[str, int] = {}
        # Builder dex (HIP-3) metadata — lazy loaded
        self._perp_dexs: Optional[list] = None         # perpDexs API response
        self._dex_offsets: Dict[str, int] = {}          # dex_name -> asset index offset
        self._builder_meta: Dict[str, dict] = {}        # dex_name -> meta response

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _post(self, endpoint: str, payload: dict) -> Any:
        """POST to Hyperliquid API."""
        url = f"{self.api_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Hyperliquid API {resp.status}: {body}")
                data = await resp.json()
                # Hyperliquid returns HTTP 200 with {"status": "err", "response": "..."} for API-level errors
                if isinstance(data, dict) and data.get("status") == "err":
                    raise Exception(f"Hyperliquid error: {data.get('response', data)}")
                return data

    async def _info(self, req_type: str, **kwargs) -> Any:
        """Query the /info endpoint."""
        payload = {"type": req_type, **kwargs}
        return await self._post("/info", payload)

    async def _exchange(
        self,
        action: dict,
        nonce: Optional[int] = None,
        vault_address: Optional[str] = None,
    ) -> Any:
        """Submit a signed action to the /exchange endpoint.

        Matches SDK's Exchange._post_action() behavior.
        """
        if nonce is None:
            nonce = int(time.time() * 1000)

        action_type = action.get("type", "unknown")
        wallet_addr = self._cached_address or "unknown"
        logger.info(
            f"_exchange: action_type={action_type}, wallet={wallet_addr}, nonce={nonce}"
        )

        signature = await sign_l1_action(action, nonce, vault_address)

        # Match SDK payload structure exactly
        # vaultAddress: included for most actions, None for usdClassTransfer/sendAsset
        # expiresAfter: None by default (matches SDK's expires_after = None)
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": vault_address if action_type not in ["usdClassTransfer", "sendAsset"] else None,
            "expiresAfter": None,  # matches SDK default
        }

        try:
            return await self._post("/exchange", payload)
        except Exception as e:
            logger.error(
                f"_exchange FAILED: action_type={action_type}, wallet={wallet_addr}, "
                f"nonce={nonce}, error={e}"
            )
            raise

    async def _ensure_meta(self) -> None:
        """Fetch and cache perp + spot metadata for asset index resolution."""
        if self._meta is None:
            self._meta = await self._info("meta")
            for i, asset in enumerate(self._meta.get("universe", [])):
                name = asset["name"]
                self._name_to_index[name] = i
                self._sz_decimals[name] = asset.get("szDecimals", 0)

        if self._spot_meta is None:
            try:
                self._spot_meta = await self._info("spotMeta")
                for pair in self._spot_meta.get("universe", []):
                    # universe entries: {"tokens": [1,0], "name": "PURR/USDC", "index": 0}
                    # Non-canonical entries have names like "@1", "@2"
                    pair_name = pair.get("name", "")
                    idx = pair.get("index", 0)
                    if "/" in pair_name:
                        # Canonical pair like "PURR/USDC" — map base name
                        base = pair_name.split("/")[0]
                        self._spot_name_to_index[base] = idx
                        self._spot_mid_key[base] = pair_name  # allMids uses "PURR/USDC"
                    elif pair_name:
                        # Non-canonical like "@1" — map as-is
                        self._spot_name_to_index[pair_name] = idx
                        self._spot_mid_key[pair_name] = pair_name
            except Exception:
                self._spot_meta = {}

    async def _ensure_builder_dex(self, dex_name: str) -> None:
        """Lazy-load builder dex metadata (HIP-3 perps like xyz:NVDA).

        Called only when a coin with ':' prefix is encountered.
        Fetches perpDexs once to discover all builder dexes and compute offsets,
        then fetches meta for the specific builder dex.
        """
        # Already loaded this dex
        if dex_name in self._builder_meta:
            return

        # Fetch perpDexs list once to compute offsets
        if self._perp_dexs is None:
            raw = await self._info("perpDexs")
            # perpDexs returns [null, {"name": "xyz", ...}, {"name": "rage", ...}, ...]
            # First element is null (default dex), rest are builder dex objects.
            # Offset formula matches SDK: skip index 0, then 110000 + i * 10000
            self._perp_dexs = raw
            idx = 0
            for entry in raw:
                if entry is None:
                    continue
                name = entry if isinstance(entry, str) else entry.get("name", "")
                if name:
                    self._dex_offsets[name] = 110000 + idx * 10000
                    idx += 1

        if dex_name not in self._dex_offsets:
            raise ValueError(
                f"Unknown builder dex: {dex_name}. "
                f"Available: {list(self._dex_offsets.keys())}"
            )

        # Fetch meta for this specific builder dex
        meta = await self._info("meta", dex=dex_name)
        self._builder_meta[dex_name] = meta
        offset = self._dex_offsets[dex_name]

        for i, asset in enumerate(meta.get("universe", [])):
            asset_name = asset["name"]
            # meta(dex="xyz") returns names already prefixed: "xyz:NVDA"
            # Use the name as-is if it contains ':', otherwise prefix it
            full_name = asset_name if ":" in asset_name else f"{dex_name}:{asset_name}"
            self._name_to_index[full_name] = offset + i
            self._sz_decimals[full_name] = asset.get("szDecimals", 0)

    async def _resolve_asset(self, coin: str) -> int:
        """Resolve coin name to perp asset index.

        Supports builder perps via 'dex:COIN' format (e.g. 'xyz:NVDA').
        """
        # Try direct match first
        idx = self._name_to_index.get(coin)
        if idx is not None:
            return idx

        # Case-insensitive fallback (e.g. "ai16z" -> "AI16Z")
        coin_upper = coin.upper()
        for name, i in self._name_to_index.items():
            if name.upper() == coin_upper:
                return i

        # If coin contains ':', try loading the builder dex
        if ":" in coin:
            dex_name = coin.split(":")[0]
            await self._ensure_builder_dex(dex_name)
            idx = self._name_to_index.get(coin)
            if idx is not None:
                return idx

        raise ValueError(
            f"Unknown perp asset: {coin}. "
            f"Available: {list(self._name_to_index.keys())[:20]}..."
        )

    async def _resolve_any_asset(self, coin: str) -> int:
        """Resolve coin name to asset index — tries perps, builder perps, then spot."""
        await self._ensure_meta()
        try:
            return await self._resolve_asset(coin)
        except ValueError:
            pass
        # Try spot (exact then case-insensitive)
        idx = self._spot_name_to_index.get(coin)
        if idx is not None:
            return 10000 + idx
        coin_upper = coin.upper()
        for name, i in self._spot_name_to_index.items():
            if name.upper() == coin_upper:
                return 10000 + i
        raise ValueError(f"Unknown asset: {coin}")

    def _resolve_spot_asset(self, coin: str) -> int:
        """Resolve coin name to spot asset index (10000 + idx)."""
        idx = self._spot_name_to_index.get(coin)
        if idx is None:
            raise ValueError(
                f"Unknown spot asset: {coin}. "
                f"Available: {list(self._spot_name_to_index.keys())[:20]}..."
            )
        return 10000 + idx

    def _format_size(self, coin: str, size: float) -> str:
        """Format size using float_to_wire for exact Hyperliquid normalization."""
        return float_to_wire(size)

    def _format_price(self, price: float, coin: str = "", is_spot: bool = False) -> str:
        """Format price matching the official SDK's rounding rules.

        Prices can have up to 5 significant figures, but no more than
        (MAX_DECIMALS - szDecimals) decimal places where MAX_DECIMALS is 6
        for perps and 8 for spot. Integer prices are always allowed.
        """
        # Step 1: round to 5 significant figures
        rounded = float(f"{price:.5g}")
        # Step 2: constrain decimal places based on szDecimals
        sz_decimals = self._sz_decimals.get(coin, 0)
        max_decimals = 8 if is_spot else 6
        max_dp = max_decimals - sz_decimals
        if max_dp >= 0:
            rounded = round(rounded, max_dp)
        return float_to_wire(rounded)

    async def _validate_order_margin(
        self,
        coin: str,
        size: float,
        price: float,
        leverage: int = 1,
        is_spot: bool = False,
    ) -> tuple[bool, str]:
        """Validate if account has sufficient margin for an order.

        Returns: (is_valid, error_message)
        """
        try:
            # Spot orders don't use leverage/margin
            if is_spot:
                return (True, "")

            # Calculate order notional value
            order_value = size * price

            # Check minimum order value ($10)
            if order_value < 10:
                return (
                    False,
                    f"Order value ${order_value:.2f} is below minimum $10. "
                    f"Increase size to at least {10 / price:.4f} {coin}",
                )

            # Calculate required margin (notional / leverage)
            required_margin = order_value / max(leverage, 1)

            # CRITICAL: Check abstraction mode FIRST to determine which account to query
            # Unified account mode keeps funds in SPOT, not PERP
            address = await self._get_address()
            current_mode = "default"
            try:
                abstraction_state = await self.get_user_abstraction_state(address)
                if isinstance(abstraction_state, str):
                    current_mode = abstraction_state
                elif isinstance(abstraction_state, dict):
                    current_mode = abstraction_state.get("type", abstraction_state.get("state", "default"))
            except Exception:
                current_mode = "default"

            # Get account state based on abstraction mode
            if current_mode == "unifiedAccount":
                # Unified account: funds are in SPOT (shared collateral)
                spot_state = await self.get_spot_state(address)
                # Find USDC balance in spot
                usdc_balance = 0.0
                for bal in spot_state.get("balances", []):
                    if bal.get("coin") == "USDC":
                        usdc_balance = float(bal.get("total", 0))
                        break

                # Use SPOT balance as available margin
                account_value = usdc_balance
                total_margin_used = 0.0  # Unified account shares collateral
                available_margin = account_value

                logger.info(
                    f"Margin validation for {coin} (UNIFIED ACCOUNT): "
                    f"spot_usdc=${usdc_balance:.2f}, "
                    f"available=${available_margin:.2f}"
                )
            else:
                # Default/disabled mode: check PERP account
                state = await self.get_account_state(address)
                margin_summary = state.get("marginSummary", {})
                account_value = float(margin_summary.get("accountValue", 0))
                total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
                available_margin = account_value - total_margin_used

                logger.info(
                    f"Margin validation for {coin} (PERP ACCOUNT): "
                    f"accountValue=${account_value:.2f}, "
                    f"totalMarginUsed=${total_margin_used:.2f}, "
                    f"available=${available_margin:.2f}"
                )

            # Require a safety buffer (5%)
            safe_available = available_margin * 0.95

            if required_margin > safe_available:
                error_msg = (
                    f"Insufficient margin for {coin} order. "
                    f"Required: ${required_margin:.2f}, "
                    f"Available: ${safe_available:.2f} "
                    f"(Account value: ${account_value:.2f}, Used: ${total_margin_used:.2f}). "
                )

                # Add mode-specific guidance
                if current_mode == "unifiedAccount":
                    error_msg += (
                        f"\n\n⚠️ UNIFIED ACCOUNT MODE ACTIVE: Checked SPOT balance (${account_value:.2f}) where your collateral is. "
                        f"If you think you have more funds, use `hl_total_balance` tool to see the complete picture. "
                        f"DO NOT use `hl_account` or `hl_balances` alone - they only show partial balances!"
                    )
                elif account_value == 0:
                    error_msg += (
                        "\n\n💡 NOTE: Showing $0 balance in PERP account. If you have funds in SPOT, enable unified account mode "
                        "to share collateral across spot/perp, or manually transfer USDC to perp using `hl_transfer_usd`."
                    )

                if ":" in coin:
                    # Builder perp specific guidance
                    dex_name = coin.split(":")[0]
                    error_msg += (
                        f"\n\n🏗️  BUILDER PERP ({dex_name}): "
                        f"DEX abstraction auto-transfers funds from main account → {dex_name} dex when order is placed. "
                        f"Validation checks main account available margin (not {dex_name} dex balance)."
                    )

                error_msg += (
                    f"\n\n✅ SOLUTIONS:\n"
                    f"1) Use `hl_total_balance` to check actual available funds\n"
                    f"2) Reduce size to {safe_available * leverage / price:.4f} {coin} or less\n"
                    f"3) Increase leverage (if below max for this asset)\n"
                    f"4) Deposit more USDC to your Hyperliquid account\n"
                    f"5) Close other positions to free up margin"
                )

                return (False, error_msg)

            return (True, "")

        except Exception as e:
            logger.warning(f"Order validation failed: {e}")
            # Don't block order on validation errors - let exchange validate
            return (True, "")

    # ── Info Methods (read-only, no auth) ────────────────────────────────

    async def get_account_state(self, address: str, dex: Optional[str] = None) -> dict:
        """Get perp positions, margin, account value.

        Args:
            address: Wallet address
            dex: Builder dex name (e.g. 'xyz') for HIP-3 perp positions.
                 None for default perp positions.
        """
        if dex:
            return await self._info("clearinghouseState", user=address, dex=dex)
        return await self._info("clearinghouseState", user=address)

    async def get_spot_state(self, address: str) -> dict:
        """Get spot token balances."""
        return await self._info("spotClearinghouseState", user=address)

    async def get_open_orders(self, address: str) -> list:
        """Get all open orders."""
        return await self._info("openOrders", user=address)

    async def get_all_mids(self, dex: Optional[str] = None) -> dict:
        """Get current mid prices for all assets.

        Args:
            dex: Builder dex name (e.g. 'xyz') for builder perp mid prices.
                 None for default perp/spot mid prices.
        """
        if dex:
            return await self._info("allMids", dex=dex)
        return await self._info("allMids")

    async def get_l2_book(self, coin: str) -> dict:
        """Get L2 orderbook snapshot."""
        return await self._info("l2Book", coin=coin)

    async def get_meta(self) -> dict:
        """Get perp universe metadata."""
        await self._ensure_meta()
        return self._meta

    async def get_spot_meta(self) -> dict:
        """Get spot universe metadata."""
        await self._ensure_meta()
        return self._spot_meta

    async def get_candles(
        self, coin: str, interval: str, start: int, end: int
    ) -> list:
        """Get OHLCV candlestick data."""
        return await self._info(
            "candleSnapshot",
            req={"coin": coin, "interval": interval, "startTime": start, "endTime": end},
        )

    async def get_user_fills(self, address: str) -> list:
        """Get recent trade fills."""
        return await self._info("userFills", user=address)

    async def get_funding_history(
        self, coin: str, start: int
    ) -> list:
        """Get historical funding rates."""
        return await self._info(
            "fundingHistory", coin=coin, startTime=start
        )

    async def get_predicted_fundings(self) -> list:
        """Get predicted next funding rates for all assets."""
        return await self._info("predictedFundings")

    async def get_user_fees(self, address: str) -> dict:
        """Get user fee schedule."""
        return await self._info("userFees", user=address)

    async def get_user_abstraction_state(self, address: str) -> dict:
        """Query current abstraction state for a user.

        Returns abstraction mode: "default", "unifiedAccount", "portfolioMargin", or "disabled"
        """
        return await self._info("userAbstraction", user=address)

    async def get_order_status(self, address: str, oid: int) -> dict:
        """Look up a single order by oid."""
        return await self._info("orderStatus", user=address, oid=oid)

    # ── Exchange Methods (require signing) ───────────────────────────────

    async def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: Optional[float] = None,
        order_type: str = "limit",
        reduce_only: bool = False,
        cloid: Optional[str] = None,
        is_spot: bool = False,
        trigger_px: Optional[float] = None,
        tpsl: Optional[str] = None,
    ) -> dict:
        """
        Place a perp or spot order.

        Args:
            coin: Asset name (e.g. "BTC", "ETH")
            is_buy: True for buy, False for sell
            size: Order size in base asset
            price: Limit price. None = market order (IoC with slippage)
            order_type: "limit" (GTC), "ioc", "alo" (post-only)
            reduce_only: If True, only reduces position
            cloid: Optional client order ID
            is_spot: If True, use spot asset index
            trigger_px: Trigger price for stop loss / take profit orders
            tpsl: "tp" for take profit, "sl" for stop loss
        """
        await self._ensure_meta()

        # Builder perps (HIP-3) need DEX abstraction for collateral
        # Enable BEFORE validation so we can check actual available margin
        logger.info(f"place_order DEX check: coin={coin}, is_spot={is_spot}, has_colon={':' in coin}")
        if not is_spot and ":" in coin:
            logger.info(f"place_order: triggering DEX abstraction for builder perp {coin}")
            await self.ensure_dex_abstraction()
        else:
            logger.info(f"place_order: skipping DEX abstraction (is_spot={is_spot}, coin={coin})")

        asset_idx = (
            self._resolve_spot_asset(coin)
            if is_spot
            else await self._resolve_asset(coin)
        )

        # Market order: fetch mid price and apply slippage
        # IMPORTANT: Skip this for trigger orders - they use trigger_px, not current mid
        if price is None and trigger_px is None:
            # Regular market order (non-trigger)
            # Builder perps use dex-specific allMids
            if not is_spot and ":" in coin:
                dex_name = coin.split(":")[0]
                mids = await self.get_all_mids(dex=dex_name)
                # allMids(dex="xyz") returns keys like "xyz:NVDA", use full coin name
                mid_key = coin
            else:
                mids = await self.get_all_mids()
                # Spot uses pair name in allMids (e.g. "PURR/USDC" or "@1")
                if is_spot:
                    mid_key = self._spot_mid_key.get(coin, coin)
                else:
                    mid_key = coin
            mid_str = mids.get(mid_key)
            if not mid_str:
                raise ValueError(f"No mid price for {coin} (looked up '{mid_key}')")
            mid = float(mid_str)
            slippage = DEFAULT_SLIPPAGE
            price = mid * (1 + slippage) if is_buy else mid * (1 - slippage)
            order_type = "ioc"  # Force IoC for market orders

        # Pre-flight validation: check margin requirements
        # CRITICAL: When unified account is active, funds are shared across spot/perp/builder-dexes
        # Check SPOT balance instead of perp, since that's where the collateral actually is
        if not is_spot and not reduce_only:
            try:
                address = await self._get_address()

                # Check if unified account is active
                try:
                    abstraction_state = await self.get_user_abstraction_state(address)
                    if isinstance(abstraction_state, str):
                        current_abstraction = abstraction_state
                    elif isinstance(abstraction_state, dict):
                        current_abstraction = abstraction_state.get("type", abstraction_state.get("state", "default"))
                    else:
                        current_abstraction = "default"
                except Exception:
                    current_abstraction = "default"

                # Get margin state - check SPOT if unified, otherwise check perp
                if current_abstraction == "unifiedAccount":
                    # Unified account: check SPOT balance (where collateral actually is)
                    spot_state = await self.get_spot_state(address)
                    # Find USDC balance in spot
                    usdc_balance = 0.0
                    for bal in spot_state.get("balances", []):
                        if bal.get("coin") == "USDC":
                            usdc_balance = float(bal.get("total", 0))
                            break

                    # Create a synthetic margin summary from spot balance
                    state = {
                        "marginSummary": {
                            "accountValue": str(usdc_balance),
                            "totalMarginUsed": "0.0",  # Unified account shares collateral
                            "totalNtlPos": "0.0",
                            "totalRawUsd": str(usdc_balance),
                        },
                        "assetPositions": [],  # Will check metadata for leverage
                    }
                    logger.info(f"Unified account active: using SPOT balance ${usdc_balance:.2f} for margin validation")
                else:
                    # Default mode: check perp clearinghouse
                    state = await self.get_account_state(address)

                # Extract leverage from assetPositions or use default
                leverage = 1
                for pos in state.get("assetPositions", []):
                    position = pos.get("position", pos)
                    if position.get("coin") == coin:
                        lev_info = position.get("leverage", {})
                        leverage = lev_info.get("value", 1)
                        break

                # If no position, check metadata for default/max leverage
                if leverage == 1:
                    if ":" in coin:
                        dex_name = coin.split(":")[0]
                        meta = self._builder_meta.get(dex_name, {})
                        for asset in meta.get("universe", []):
                            if asset["name"] == coin or asset["name"] == coin.split(":", 1)[-1]:
                                # Use max leverage as estimate if no position exists
                                leverage = asset.get("maxLeverage", 1)
                                break
                    else:
                        if self._meta:
                            for asset in self._meta.get("universe", []):
                                if asset["name"] == coin:
                                    leverage = asset.get("maxLeverage", 1)
                                    break

                # Validate margin
                is_valid, error_msg = await self._validate_order_margin(
                    coin=coin,
                    size=size,
                    price=price,
                    leverage=leverage,
                    is_spot=is_spot,
                )

                if not is_valid:
                    raise ValueError(error_msg)

            except ValueError:
                # Re-raise validation errors
                raise
            except Exception as e:
                # Don't block order on validation errors
                logger.warning(f"Order validation error (non-blocking): {e}")

        # Build order type spec
        if trigger_px is not None:
            # Trigger order - use float_to_wire directly (matches SDK)
            # This ensures consistent serialization when price == trigger_px
            formatted_trigger = float_to_wire(trigger_px)
            formatted_price = float_to_wire(price)

            is_market_trigger = (price == trigger_px) if price is not None else True
            # CRITICAL: Field order must match SDK exactly for msgpack hash consistency
            # SDK uses: isMarket, triggerPx, tpsl (not triggerPx first!)
            trigger_spec = {
                "isMarket": is_market_trigger,
                "triggerPx": formatted_trigger,
                "tpsl": tpsl or "tp",
            }
            tif_spec = {"trigger": trigger_spec}
        elif order_type == "limit":
            # Regular orders - keep existing validation
            formatted_price = self._format_price(price, coin=coin, is_spot=is_spot)
            tif_spec = {"limit": {"tif": "Gtc"}}
        elif order_type == "ioc":
            formatted_price = self._format_price(price, coin=coin, is_spot=is_spot)
            tif_spec = {"limit": {"tif": "Ioc"}}
        elif order_type == "alo":
            formatted_price = self._format_price(price, coin=coin, is_spot=is_spot)
            tif_spec = {"limit": {"tif": "Alo"}}
        else:
            formatted_price = self._format_price(price, coin=coin, is_spot=is_spot)
            tif_spec = {"limit": {"tif": "Gtc"}}

        order = {
            "a": asset_idx,
            "b": is_buy,
            "p": formatted_price,
            "s": self._format_size(coin, size),
            "r": reduce_only,
            "t": tif_spec,
        }
        if cloid:
            order["c"] = cloid

        action = {
            "type": "order",
            "orders": [order],
            "grouping": "na",
        }

        logger.info(
            f"place_order: coin={coin}, is_buy={is_buy}, size={size}, "
            f"price={formatted_price}, order_type={order_type}, "
            f"asset_idx={asset_idx}"
        )

        # DEBUG: Log the full action structure for trigger orders
        if trigger_px is not None:
            import json
            logger.info(f"TRIGGER ORDER ACTION: {json.dumps(action, indent=2)}")

        result = await self._exchange(action)
        logger.info(f"place_order result: {result}")
        return result

    async def cancel_order(self, coin: str, oid: int) -> dict:
        """Cancel an order by oid."""
        await self._ensure_meta()
        asset_idx = await self._resolve_any_asset(coin)

        action = {
            "type": "cancel",
            "cancels": [{"a": asset_idx, "o": oid}],
        }
        return await self._exchange(action)

    async def cancel_by_cloid(self, coin: str, cloid: str) -> dict:
        """Cancel an order by client order ID."""
        await self._ensure_meta()
        asset_idx = await self._resolve_any_asset(coin)

        action = {
            "type": "cancelByCloid",
            "cancels": [{"asset": asset_idx, "cloid": cloid}],
        }
        return await self._exchange(action)

    async def cancel_all(self, coin: Optional[str] = None) -> list:
        """
        Cancel all open orders, optionally filtered by coin.
        Returns list of cancel results.
        """
        # No batch cancel action in HL — cancel individually
        address = await self._get_address()
        orders = await self.get_open_orders(address)

        if coin:
            orders = [o for o in orders if o.get("coin") == coin]

        results = []
        for order in orders:
            try:
                r = await self.cancel_order(
                    order["coin"], order["oid"]
                )
                results.append(r)
            except Exception as e:
                results.append({"error": str(e), "oid": order.get("oid")})

        return results

    async def modify_order(
        self,
        oid: int,
        coin: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: str = "limit",
    ) -> dict:
        """Modify an existing order."""
        await self._ensure_meta()
        asset_idx = await self._resolve_any_asset(coin)

        if order_type == "limit":
            tif_spec = {"limit": {"tif": "Gtc"}}
        elif order_type == "ioc":
            tif_spec = {"limit": {"tif": "Ioc"}}
        elif order_type == "alo":
            tif_spec = {"limit": {"tif": "Alo"}}
        else:
            tif_spec = {"limit": {"tif": "Gtc"}}

        action = {
            "type": "modify",
            "oid": oid,
            "order": {
                "a": asset_idx,
                "b": is_buy,
                "p": self._format_price(price, coin=coin),
                "s": self._format_size(coin, size),
                "r": False,
                "t": tif_spec,
            },
        }
        return await self._exchange(action)

    # ── DEX Abstraction (HIP-3 builder perps collateral) ─────────────────

    _dex_abstraction_enabled: bool = False

    async def ensure_dex_abstraction(self) -> dict:
        """Enable DEX abstraction so collateral auto-transfers to builder dexes.

        Required for trading HIP-3 builder perps (xyz:NVDA, xyz:TSLA, etc.).
        Without this, the wallet has no collateral in builder dex clearinghouses
        and all orders fail with "Insufficient margin".

        Checks current abstraction state first, then tries multiple methods:
        1. agentSetAbstraction("u") - modern agent-signed approach
        2. agentEnableDexAbstraction - legacy agent-signed approach
        3. userSetAbstraction("unifiedAccount") - user-signed fallback

        Safe to call multiple times — Hyperliquid handles idempotency.
        """
        address = await self._get_address()

        # ALWAYS check current state first - don't trust cache
        # The cache might be stale if the state was changed externally or if enable failed
        try:
            state_result = await self.get_user_abstraction_state(address)
            # API may return string ("default") or dict ({"type": "default"})
            if isinstance(state_result, str):
                current_state = state_result
            elif isinstance(state_result, dict):
                current_state = state_result.get("type", state_result.get("state", "unknown"))
            else:
                current_state = "unknown"

            logger.info(f"DEX abstraction: current state for {address} = {current_state}")

            # If already in unifiedAccount mode, we're done
            if current_state == "unifiedAccount":
                logger.info("DEX abstraction: already enabled (unifiedAccount mode)")
                self._dex_abstraction_enabled = True
                return {"status": "already_enabled", "state": current_state}

            # If cache says enabled but state check shows otherwise, reset cache
            if self._dex_abstraction_enabled and current_state != "unifiedAccount":
                logger.warning(
                    f"DEX abstraction: cache says enabled but state is '{current_state}'. "
                    f"Resetting cache and retrying enable."
                )
                self._dex_abstraction_enabled = False

            # SDK comment says: "the account must be in 'default' mode to succeed"
            if current_state not in ("default", "disabled"):
                logger.warning(
                    f"DEX abstraction: account in {current_state} mode. "
                    f"Transitions may fail if not in 'default' mode."
                )
        except Exception as e:
            logger.warning(f"DEX abstraction: failed to query current state: {e}")
            # Continue anyway, state check is informational

        # Try Method 1: agentSetAbstraction with "u" (unified account)
        logger.info(f"DEX abstraction: trying agentSetAbstraction(u) for {address}")
        action = {
            "type": "agentSetAbstraction",
            "abstraction": "u",  # "u" = unified account (DEX abstraction enabled)
        }

        try:
            result = await self._exchange(action, vault_address=None)
            logger.info(f"DEX abstraction: agentSetAbstraction result = {result}")
            self._dex_abstraction_enabled = True
            return result
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"DEX abstraction: agentSetAbstraction failed: {e}")

            # If it says "already" or "enabled", that's success
            if "already" in err_str or "enabled" in err_str:
                self._dex_abstraction_enabled = True
                return {"status": "ok", "detail": str(e)}

        # Try Method 2: agentEnableDexAbstraction (legacy)
        logger.info(f"DEX abstraction: trying agentEnableDexAbstraction for {address}")
        action = {
            "type": "agentEnableDexAbstraction",
        }

        try:
            result = await self._exchange(action, vault_address=None)
            logger.info(f"DEX abstraction: agentEnableDexAbstraction result = {result}")
            self._dex_abstraction_enabled = True
            return result
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"DEX abstraction: agentEnableDexAbstraction failed: {e}")

            if "already" in err_str or "enabled" in err_str:
                self._dex_abstraction_enabled = True
                return {"status": "ok", "detail": str(e)}

        # Try Method 3: userSetAbstraction (user-signed, not agent-signed)
        # This uses a different signing domain (HyperliquidSignTransaction vs Agent)
        # SDK example shows this works when account is in "default" mode
        logger.info(f"DEX abstraction: trying userSetAbstraction(unifiedAccount) for {address}")

        try:
            result = await self._user_set_abstraction(address, "unifiedAccount")
            logger.info(f"DEX abstraction: userSetAbstraction result = {result}")

            # Verify the state actually changed
            try:
                new_state_result = await self.get_user_abstraction_state(address)
                if isinstance(new_state_result, str):
                    new_state = new_state_result
                elif isinstance(new_state_result, dict):
                    new_state = new_state_result.get("type", new_state_result.get("state", "unknown"))
                else:
                    new_state = "unknown"
                logger.info(f"DEX abstraction: state AFTER userSetAbstraction = {new_state}")

                if new_state == "unifiedAccount":
                    logger.info("DEX abstraction: successfully enabled (verified)")
                    self._dex_abstraction_enabled = True
                    return result
                else:
                    logger.warning(
                        f"DEX abstraction: userSetAbstraction returned success but state is still '{new_state}', not 'unifiedAccount'. "
                        f"This may indicate the account has restrictions. Full result: {result}"
                    )
            except Exception as verify_err:
                logger.warning(f"DEX abstraction: failed to verify state after userSetAbstraction: {verify_err}")

            self._dex_abstraction_enabled = True
            return result
        except Exception as e:
            err_str = str(e).lower()
            logger.error(f"DEX abstraction: userSetAbstraction failed: {e}")

            if "already" in err_str or "enabled" in err_str:
                self._dex_abstraction_enabled = True
                return {"status": "ok", "detail": str(e)}

        # All methods failed
        raise RuntimeError(
            f"Failed to enable DEX abstraction for {address}. "
            f"Your account may have DEX abstraction manually disabled. "
            f"Please enable it at app.hyperliquid.xyz:\n"
            f"1. Go to Settings (top right)\n"
            f"2. Find 'Disable HIP-3 Dex Abstraction' checkbox\n"
            f"3. UNCHECK it to enable DEX abstraction\n"
            f"4. Then retry your order"
        )

    async def _user_set_abstraction(self, user: str, abstraction: str) -> dict:
        """Set abstraction mode for user (user-signed action).

        Matches SDK's user_set_abstraction exactly.

        Args:
            user: User wallet address
            abstraction: "unifiedAccount", "portfolioMargin", or "disabled"

        Returns: API response
        """
        nonce = int(time.time() * 1000)

        # Action payload must include signatureChainId and hyperliquidChain
        # These are required for all user-signed actions
        action = {
            "type": "userSetAbstraction",
            "user": user.lower(),
            "abstraction": abstraction,
            "nonce": nonce,
            "signatureChainId": "0xa4b1",  # 42161 in hex (Arbitrum mainnet)
            "hyperliquidChain": "Mainnet",
        }

        signature = await sign_user_set_abstraction(
            user=user,
            abstraction=abstraction,
            nonce=nonce,
        )

        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
        }
        return await self._post("/exchange", payload)

    async def update_leverage(
        self, coin: str, leverage: int, is_cross: bool = True
    ) -> dict:
        """Set leverage for a perp."""
        await self._ensure_meta()
        # Builder perps need DEX abstraction
        logger.info(f"update_leverage DEX check: coin={coin}, has_colon={':' in coin}")
        if ":" in coin:
            logger.info(f"update_leverage: triggering DEX abstraction for builder perp {coin}")
            await self.ensure_dex_abstraction()
        else:
            logger.info(f"update_leverage: skipping DEX abstraction for {coin}")
        asset_idx = await self._resolve_asset(coin)

        action = {
            "type": "updateLeverage",
            "asset": asset_idx,
            "isCross": is_cross,
            "leverage": leverage,
        }
        return await self._exchange(action)

    async def market_open(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        slippage: float = DEFAULT_SLIPPAGE,
        is_spot: bool = False,
    ) -> dict:
        """Convenience: open a position with an IoC market order."""
        return await self.place_order(
            coin=coin,
            is_buy=is_buy,
            size=size,
            price=None,  # triggers market order logic
            order_type="ioc",
            is_spot=is_spot,
        )

    async def market_close(
        self, coin: str, address: str, slippage: float = DEFAULT_SLIPPAGE
    ) -> dict:
        """Close entire perp position for a coin."""
        # Builder perps (HIP-3) have separate clearinghouse state per dex
        if ":" in coin:
            dex_name = coin.split(":")[0]
            state = await self._info("clearinghouseState", user=address, dex=dex_name)
        else:
            state = await self.get_account_state(address)
        positions = state.get("assetPositions", [])

        pos = None
        for p in positions:
            position = p.get("position", p)
            if position.get("coin") == coin:
                pos = position
                break

        if not pos:
            raise ValueError(f"No open position for {coin}")

        size = abs(float(pos["szi"]))
        is_buy = float(pos["szi"]) < 0  # Close short = buy, close long = sell

        return await self.place_order(
            coin=coin,
            is_buy=is_buy,
            size=size,
            price=None,
            order_type="ioc",
            reduce_only=True,
        )

    async def transfer_usd(
        self, amount: float, to_perp: bool = True
    ) -> dict:
        """
        Transfer USDC between spot and perp.
        Uses user-signed action (HyperliquidSignTransaction domain).
        """
        address = await self._get_address()

        # Query balances BEFORE transfer for verification
        try:
            perp_state_before = await self.get_account_state(address)
            spot_state_before = await self.get_spot_state(address)
            perp_value_before = float(perp_state_before.get("marginSummary", {}).get("accountValue", 0))
            spot_balances_before = spot_state_before.get("balances", [])
            logger.info(
                f"transfer_usd: BEFORE transfer - "
                f"perp_value=${perp_value_before:.2f}, "
                f"spot_balances={spot_balances_before}"
            )
        except Exception as e:
            logger.warning(f"transfer_usd: failed to query balances before transfer: {e}")

        nonce = int(time.time() * 1000)

        action = {
            "type": "usdClassTransfer",
            "amount": str(amount),
            "toPerp": to_perp,
            "nonce": nonce,
            "signatureChainId": "0xa4b1",  # 42161 in hex (Arbitrum mainnet)
            "hyperliquidChain": "Mainnet",
        }

        types = {
            "HyperliquidTransaction:UsdClassTransfer": [
                {"name": "hyperliquidChain", "type": "string"},
                {"name": "amount", "type": "string"},
                {"name": "toPerp", "type": "bool"},
                {"name": "nonce", "type": "uint64"},
            ]
        }

        signature = await sign_user_action(
            action={
                "hyperliquidChain": "Mainnet",
                "amount": str(amount),
                "toPerp": to_perp,
                "nonce": nonce,
            },
            types=types,
            primary_type="HyperliquidTransaction:UsdClassTransfer",
        )

        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
        }

        logger.info(f"transfer_usd: submitting ${amount} transfer ({'spot→perp' if to_perp else 'perp→spot'})")

        try:
            result = await self._post("/exchange", payload)
            logger.info(f"transfer_usd: API response SUCCESS = {result}")
        except Exception as api_error:
            logger.error(f"transfer_usd: API call FAILED: {api_error}", exc_info=True)
            # Re-raise so caller sees the error
            raise

        # Query balances AFTER transfer for verification
        try:
            perp_state_after = await self.get_account_state(address)
            spot_state_after = await self.get_spot_state(address)
            perp_value_after = float(perp_state_after.get("marginSummary", {}).get("accountValue", 0))
            spot_balances_after = spot_state_after.get("balances", [])
            logger.info(
                f"transfer_usd: AFTER transfer - "
                f"perp_value=${perp_value_after:.2f}, "
                f"spot_balances={spot_balances_after}"
            )
        except Exception as e:
            logger.warning(f"transfer_usd: failed to query balances after transfer: {e}")

        return result

    async def withdraw_from_bridge(
        self, amount: float, destination: Optional[str] = None
    ) -> dict:
        """
        Withdraw USDC from Hyperliquid to an Arbitrum wallet (L1 bridge withdrawal).

        Fee: 1 USDC (deducted by Hyperliquid). Processing: ~5 minutes.

        Args:
            amount: USDC amount to withdraw
            destination: Target wallet address (defaults to agent's own wallet)
        """
        if not destination:
            destination = await self._get_address()

        nonce = int(time.time() * 1000)

        action = {
            "type": "withdraw3",
            "hyperliquidChain": "Mainnet",
            "signatureChainId": "0xa4b1",  # 42161 in hex (Arbitrum mainnet)
            "destination": destination,
            "amount": str(amount),
            "time": nonce,
        }

        types = {
            "HyperliquidTransaction:Withdraw": [
                {"name": "hyperliquidChain", "type": "string"},
                {"name": "destination", "type": "string"},
                {"name": "amount", "type": "string"},
                {"name": "time", "type": "uint64"},
            ]
        }

        signature = await sign_user_action(
            action={
                "hyperliquidChain": "Mainnet",
                "destination": destination,
                "amount": str(amount),
                "time": nonce,
            },
            types=types,
            primary_type="HyperliquidTransaction:Withdraw",
        )

        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
        }
        return await self._post("/exchange", payload)

    async def deposit_usdc(self, amount: float) -> dict:
        """
        Deposit USDC from agent's Arbitrum wallet into Hyperliquid.

        Sends an ERC-20 transfer of USDC to the Hyperliquid bridge contract.
        Minimum deposit: 5 USDC.

        Args:
            amount: USDC amount to deposit (minimum 5)
        """
        from eth_utils import keccak
        from tools.wallet import _wallet_request, _is_fly_machine

        if not _is_fly_machine():
            raise RuntimeError("Not running on a Fly Machine — wallet unavailable")

        if amount < MIN_DEPOSIT_USDC:
            raise ValueError(f"Minimum deposit is {MIN_DEPOSIT_USDC} USDC")

        amount_base = int(amount * (10 ** USDC_DECIMALS))

        # Step 1: ERC-20 approve(bridge, amount)
        approve_selector = keccak(b"approve(address,uint256)")[:4]
        bridge_bytes = bytes.fromhex(BRIDGE_ADDRESS.replace("0x", "")).rjust(32, b"\x00")
        amount_bytes = amount_base.to_bytes(32, "big")
        approve_data = "0x" + (approve_selector + bridge_bytes + amount_bytes).hex()

        logger.info(f"HL deposit: approve TX (amount_base={amount_base})")
        approve_result = await _wallet_request("POST", "/agent/transfer", {
            "to": USDC_ADDRESS,
            "amount": "0",
            "data": approve_data,
            "chain_id": ARBITRUM_CHAIN_ID,
        })
        approve_tx = approve_result.get("tx_hash", approve_result.get("hash", "unknown"))
        logger.info(f"HL deposit: approve TX = {approve_tx}")

        # Step 2: ERC-20 transfer(bridge, amount)
        transfer_selector = keccak(b"transfer(address,uint256)")[:4]
        transfer_data = "0x" + (transfer_selector + bridge_bytes + amount_bytes).hex()

        logger.info(f"HL deposit: transfer TX to bridge {BRIDGE_ADDRESS}")
        transfer_result = await _wallet_request("POST", "/agent/transfer", {
            "to": USDC_ADDRESS,
            "amount": "0",
            "data": transfer_data,
            "chain_id": ARBITRUM_CHAIN_ID,
        })
        transfer_tx = transfer_result.get("tx_hash", transfer_result.get("hash", "unknown"))
        logger.info(f"HL deposit: transfer TX = {transfer_tx}")

        return {
            "approve_tx_hash": approve_tx,
            "transfer_tx_hash": transfer_tx,
            "amount_deposited": amount,
            "amount_base_units": amount_base,
            "bridge_contract": BRIDGE_ADDRESS,
            "chain_id": ARBITRUM_CHAIN_ID,
        }

    # ── Address helper ───────────────────────────────────────────────────

    _cached_address: Optional[str] = None

    async def _get_address(self) -> str:
        """Get the agent's EVM address from wallet service (cached)."""
        if self._cached_address:
            return self._cached_address

        from tools.wallet import _wallet_request, _is_fly_machine

        if not _is_fly_machine():
            raise RuntimeError("Not running on Fly — wallet unavailable")

        data = await _wallet_request("GET", "/agent/wallet")
        wallets = data if isinstance(data, list) else data.get("wallets", [])
        for w in wallets:
            if w.get("chain_type") == "ethereum":
                self._cached_address = w["wallet_address"]
                return self._cached_address

        raise RuntimeError("No ethereum wallet found")
