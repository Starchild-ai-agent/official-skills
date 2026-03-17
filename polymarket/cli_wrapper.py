"""
Polymarket CLI Wrapper — Subprocess interface to official Rust CLI.

Executes `polymarket -o json` commands and parses JSON output.
Handles errors, validates binary installation, and provides type-safe result parsing.
"""

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class PolymarketCLIError(Exception):
    """Raised when Polymarket CLI command fails."""
    pass


class PolymarketCLI:
    """
    Wrapper for the official Polymarket Rust CLI.

    Executes commands via subprocess and parses JSON output.
    """

    def __init__(self, binary_path: str = "polymarket"):
        """
        Initialize CLI wrapper.

        Args:
            binary_path: Path to polymarket binary (default: "polymarket")
        """
        self.binary_path = binary_path
        self._check_binary()

    def _check_binary(self) -> None:
        """
        Verify that polymarket CLI is installed and accessible.

        Raises:
            PolymarketCLIError: If binary is not found
        """
        try:
            result = subprocess.run(
                [self.binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise PolymarketCLIError(
                    f"Polymarket CLI check failed: {result.stderr}"
                )
            logger.debug(f"Polymarket CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise PolymarketCLIError(
                "Polymarket CLI not found. Install via: "
                "curl -sSL https://raw.githubusercontent.com/Polymarket/polymarket-cli/main/install.sh | sh"
            )
        except subprocess.TimeoutExpired:
            raise PolymarketCLIError("Polymarket CLI check timed out")

    def _execute(
        self,
        args: List[str],
        json_output: bool = True,
        timeout: int = 30
    ) -> Union[Dict, List, str]:
        """
        Execute a polymarket CLI command.

        Args:
            args: Command arguments (e.g., ["markets", "list", "--limit", "10"])
            json_output: Whether to expect JSON output (adds -o json flag)
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON output (dict/list) if json_output=True, else raw stdout string

        Raises:
            PolymarketCLIError: If command fails or JSON parsing fails
        """
        cmd = [self.binary_path]

        # Add -o json for JSON output
        if json_output:
            cmd.extend(["-o", "json"])

        cmd.extend(args)

        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()

                # Try to parse JSON error response
                if json_output and error_msg:
                    try:
                        error_data = json.loads(error_msg)
                        if isinstance(error_data, dict) and "error" in error_data:
                            raise PolymarketCLIError(error_data["error"])
                    except json.JSONDecodeError:
                        pass

                raise PolymarketCLIError(f"Command failed: {error_msg}")

            # Parse JSON output
            if json_output:
                stdout = result.stdout.strip()
                if not stdout:
                    return {}
                try:
                    return json.loads(stdout)
                except json.JSONDecodeError as e:
                    raise PolymarketCLIError(f"Failed to parse JSON output: {e}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise PolymarketCLIError(f"Command timed out after {timeout}s")
        except FileNotFoundError:
            raise PolymarketCLIError("Polymarket CLI not found")

    # ── Market Discovery ─────────────────────────────────────────────────────

    def markets_list(
        self,
        limit: int = 10,
        offset: int = 0,
        order: Optional[str] = None,
        active: Optional[bool] = None,
        closed: Optional[bool] = None
    ) -> List[Dict]:
        """
        List markets.

        Args:
            limit: Number of results (default 10)
            offset: Pagination offset
            order: Sort field (volume, liquidity, created_at)
            active: Filter by active status
            closed: Filter by closed status

        Returns:
            List of market dicts
        """
        args = ["markets", "list", "--limit", str(limit)]

        if offset:
            args.extend(["--offset", str(offset)])
        if order:
            args.extend(["--order", order])
        if active is not None:
            args.extend(["--active", str(active).lower()])
        if closed is not None:
            args.extend(["--closed", str(closed).lower()])

        result = self._execute(args)
        return result if isinstance(result, list) else []

    def markets_get(self, market_id: str) -> Dict:
        """
        Get a single market by ID or slug.

        Args:
            market_id: Market slug or condition ID

        Returns:
            Market dict
        """
        result = self._execute(["markets", "get", market_id])
        return result if isinstance(result, dict) else {}

    def markets_search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search markets by keyword.

        Args:
            query: Search query
            limit: Number of results

        Returns:
            List of market dicts
        """
        args = ["markets", "search", query, "--limit", str(limit)]
        result = self._execute(args)
        return result if isinstance(result, list) else []

    def events_list(
        self,
        limit: int = 10,
        tag: Optional[str] = None,
        active: Optional[bool] = None
    ) -> List[Dict]:
        """
        List events.

        Args:
            limit: Number of results
            tag: Filter by tag slug
            active: Filter by active status

        Returns:
            List of event dicts
        """
        args = ["events", "list", "--limit", str(limit)]

        if tag:
            args.extend(["--tag", tag])
        if active is not None:
            args.extend(["--active", str(active).lower()])

        result = self._execute(args)
        return result if isinstance(result, list) else []

    def events_get(self, event_id: str) -> Dict:
        """
        Get an event by ID.

        Args:
            event_id: Event ID

        Returns:
            Event dict with child markets
        """
        result = self._execute(["events", "get", event_id])
        return result if isinstance(result, dict) else {}

    def tags_list(self) -> List[Dict]:
        """
        List all market tags/categories.

        Returns:
            List of tag dicts
        """
        result = self._execute(["tags", "list"])
        return result if isinstance(result, list) else []

    # ── Series, Comments, Sports (Enhanced Market Discovery) ────────────────

    def series_list(self, limit: int = 10) -> List[Dict]:
        """List market series (recurring events)."""
        args = ["series", "list", "--limit", str(limit)]
        result = self._execute(args)
        return result if isinstance(result, list) else []

    def series_get(self, series_id: str) -> Dict:
        """Get a series by ID."""
        result = self._execute(["series", "get", series_id])
        return result if isinstance(result, dict) else {}

    def comments_list(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        List comments on an entity.

        Args:
            entity_type: Entity type (event, market, etc)
            entity_id: Entity ID
            limit: Number of results
        """
        args = [
            "comments", "list",
            "--entity-type", entity_type,
            "--entity-id", entity_id,
            "--limit", str(limit)
        ]
        result = self._execute(args)
        return result if isinstance(result, list) else []

    def sports_list(self) -> List[Dict]:
        """List available sports."""
        result = self._execute(["sports", "list"])
        return result if isinstance(result, list) else []

    def sports_teams(self, league: str, limit: int = 50) -> List[Dict]:
        """
        List teams for a league.

        Args:
            league: League name (NFL, NBA, etc)
            limit: Number of results
        """
        args = ["sports", "teams", "--league", league, "--limit", str(limit)]
        result = self._execute(args)
        return result if isinstance(result, list) else []

    # ── Prices & Order Book (CLOB API) ──────────────────────────────────────

    def clob_price(self, token_id: str, side: str) -> Dict:
        """
        Get best price for a token.

        Args:
            token_id: CLOB token ID
            side: "buy" or "sell"

        Returns:
            Price dict
        """
        args = ["clob", "price", token_id, "--side", side]
        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    def clob_midpoint(self, token_id: str) -> Dict:
        """Get midpoint price for a token."""
        result = self._execute(["clob", "midpoint", token_id])
        return result if isinstance(result, dict) else {}

    def clob_spread(self, token_id: str) -> Dict:
        """Get bid-ask spread for a token."""
        result = self._execute(["clob", "spread", token_id])
        return result if isinstance(result, dict) else {}

    def clob_book(self, token_id: str) -> Dict:
        """
        Get order book for a token.

        Args:
            token_id: CLOB token ID

        Returns:
            Order book with bids/asks
        """
        result = self._execute(["clob", "book", token_id])
        return result if isinstance(result, dict) else {}

    # ── Trading (CLOB API, requires auth) ───────────────────────────────────

    def clob_create_order(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        post_only: bool = False
    ) -> Dict:
        """
        Place a limit order.

        Args:
            token_id: CLOB token ID
            side: "buy" or "sell"
            price: Limit price (0.01-0.99)
            size: Order size in shares
            post_only: Maker-only mode

        Returns:
            Order response with order_id
        """
        args = [
            "clob", "create-order",
            "--token", token_id,
            "--side", side,
            "--price", str(price),
            "--size", str(size)
        ]

        if post_only:
            args.append("--post-only")

        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    def clob_market_order(
        self,
        token_id: str,
        side: str,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        Place a market order (FOK).

        Args:
            token_id: CLOB token ID
            side: "buy" or "sell"
            amount: Amount ($ for buy, shares for sell)
            price: Worst acceptable price (slippage protection)

        Returns:
            Order response
        """
        args = [
            "clob", "market-order",
            "--token", token_id,
            "--side", side,
            "--amount", str(amount)
        ]

        if price is not None:
            args.extend(["--price", str(price)])

        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    def clob_cancel(self, order_id: str) -> Dict:
        """Cancel a single order."""
        result = self._execute(["clob", "cancel", order_id])
        return result if isinstance(result, dict) else {}

    def clob_cancel_all(self, market: Optional[str] = None) -> Dict:
        """
        Cancel all open orders.

        Args:
            market: Optional market condition ID to filter
        """
        args = ["clob", "cancel-all"]
        if market:
            args.extend(["--market", market])

        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    def clob_orders(self, market: Optional[str] = None) -> List[Dict]:
        """
        Get open orders.

        Args:
            market: Optional market condition ID to filter

        Returns:
            List of open orders
        """
        args = ["clob", "orders"]
        if market:
            args.extend(["--market", market])

        result = self._execute(args)
        return result if isinstance(result, list) else []

    def clob_trades(self, market: Optional[str] = None, asset: Optional[str] = None) -> List[Dict]:
        """
        Get trade history.

        Args:
            market: Optional market condition ID to filter
            asset: Optional asset/token ID to filter

        Returns:
            List of trades
        """
        args = ["clob", "trades"]
        if market:
            args.extend(["--market", market])
        if asset:
            args.extend(["--asset", asset])

        result = self._execute(args)
        return result if isinstance(result, list) else []

    def clob_balance(self, asset_type: str = "collateral") -> Dict:
        """
        Get account balance.

        Args:
            asset_type: "collateral" or "conditional"

        Returns:
            Balance dict
        """
        args = ["clob", "balance", "--asset-type", asset_type]
        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    # ── Portfolio & Analytics (Data API) ────────────────────────────────────

    def data_positions(self, address: str) -> List[Dict]:
        """
        Get positions for an address.

        Args:
            address: Wallet address

        Returns:
            List of positions
        """
        result = self._execute(["data", "positions", address])
        return result if isinstance(result, list) else []

    def data_leaderboard(
        self,
        period: str = "month",
        order_by: str = "pnl",
        limit: int = 10
    ) -> List[Dict]:
        """
        Get leaderboard.

        Args:
            period: Time period (week, month, year, all)
            order_by: Sort field (pnl, volume, trades)
            limit: Number of results

        Returns:
            List of traders
        """
        args = [
            "data", "leaderboard",
            "--period", period,
            "--order-by", order_by,
            "--limit", str(limit)
        ]
        result = self._execute(args)
        return result if isinstance(result, list) else []

    # ── Contract Approvals ──────────────────────────────────────────────────

    def approve_check(self, address: Optional[str] = None) -> Dict:
        """
        Check contract approvals.

        Args:
            address: Optional address to check (defaults to wallet)

        Returns:
            Approval status for each contract
        """
        args = ["approve", "check"]
        if address:
            args.append(address)

        result = self._execute(args)
        return result if isinstance(result, dict) else {}

    def approve_set(self) -> str:
        """
        Set all contract approvals (sends on-chain transactions).

        Returns:
            Raw stdout (transaction hashes and status messages)

        Note: This requires MATIC for gas and returns non-JSON output
        """
        # approve set returns transaction output, not JSON
        return self._execute(["approve", "set"], json_output=False, timeout=120)

    # ── CTF Token Operations ────────────────────────────────────────────────

    def ctf_split(self, condition_id: str, amount: float) -> str:
        """
        Split collateral into conditional tokens.

        Args:
            condition_id: Condition ID (0x...)
            amount: Amount in USDC to split

        Returns:
            Transaction output

        Note: Requires MATIC for gas
        """
        args = [
            "ctf", "split",
            "--condition", condition_id,
            "--amount", str(amount)
        ]
        return self._execute(args, json_output=False, timeout=120)

    def ctf_merge(self, condition_id: str, amount: float) -> str:
        """
        Merge conditional tokens back to collateral.

        Args:
            condition_id: Condition ID (0x...)
            amount: Amount to merge

        Returns:
            Transaction output
        """
        args = [
            "ctf", "merge",
            "--condition", condition_id,
            "--amount", str(amount)
        ]
        return self._execute(args, json_output=False, timeout=120)

    def ctf_redeem(self, condition_id: str) -> str:
        """
        Redeem winning tokens after market resolution.

        Args:
            condition_id: Condition ID (0x...)

        Returns:
            Transaction output
        """
        args = ["ctf", "redeem", "--condition", condition_id]
        return self._execute(args, json_output=False, timeout=120)

    # ── Bridge Operations ───────────────────────────────────────────────────

    def bridge_deposit(self, address: str) -> Dict:
        """
        Get deposit addresses for bridging from other chains.

        Args:
            address: Destination Polygon address

        Returns:
            Dict with deposit addresses for each supported chain
        """
        result = self._execute(["bridge", "deposit", address])
        return result if isinstance(result, dict) else {}

    def bridge_status(self, deposit_address: str) -> Dict:
        """
        Check deposit status.

        Args:
            deposit_address: Deposit address to check

        Returns:
            Status dict with pending/completed deposits
        """
        result = self._execute(["bridge", "status", deposit_address])
        return result if isinstance(result, dict) else {}

    def bridge_supported_assets(self) -> List[Dict]:
        """
        List supported chains and tokens for bridging.

        Returns:
            List of supported assets
        """
        result = self._execute(["bridge", "supported-assets"])
        return result if isinstance(result, list) else []
