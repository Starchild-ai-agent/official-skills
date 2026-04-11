"""
Wallet Skill — Multi-chain wallet (EVM + Solana)
Balances, transfers, signing, policy management.
Delegates to /app/tools/wallet for core functions.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """Register all wallet tools with the Agent framework."""
    registered = []

    try:
        from .wallet import (
            WalletInfoTool,
            WalletBalanceTool,
            WalletSolBalanceTool,
            WalletGetAllBalancesTool,
            WalletTransferTool,
            WalletSignTransactionTool,
            WalletSignTool,
            WalletSignTypedDataTool,
            WalletTransactionsTool,
            WalletSolTransferTool,
            WalletSolSignTransactionTool,
            WalletSolSignTool,
            WalletSolTransactionsTool,
            WalletGetPolicyTool,
            WalletProposePolicyTool,
        )

        tools = [
            WalletInfoTool(),
            WalletBalanceTool(),
            WalletSolBalanceTool(),
            WalletGetAllBalancesTool(),
            WalletTransferTool(),
            WalletSignTransactionTool(),
            WalletSignTool(),
            WalletSignTypedDataTool(),
            WalletTransactionsTool(),
            WalletSolTransferTool(),
            WalletSolSignTransactionTool(),
            WalletSolSignTool(),
            WalletSolTransactionsTool(),
            WalletGetPolicyTool(),
            WalletProposePolicyTool(),
        ]

        for tool in tools:
            api.register_tool(tool)
            registered.append(tool.name)

    except Exception as e:
        logger.error(f"Failed to register wallet tools: {e}", exc_info=True)

    return registered
