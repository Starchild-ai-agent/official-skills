"""
Agent Builder — Create and manage focused micro-agents.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """Register agent builder tools."""
    registered = []

    try:
        from .tools import (
            AgentBuildTool,
            AgentTaskTool,
            AgentRunTool,
            AgentListTool,
            AgentTeamTool,
            AgentLoopTool,
            AgentMessageTool,
        )

        api.register_tool(AgentBuildTool())
        api.register_tool(AgentTaskTool())
        api.register_tool(AgentRunTool())
        api.register_tool(AgentListTool())
        api.register_tool(AgentTeamTool())
        api.register_tool(AgentLoopTool())
        api.register_tool(AgentMessageTool())

        registered = [
            "agent_build",
            "agent_task",
            "agent_run",
            "agent_list",
            "agent_team",
            "agent_loop",
            "agent_message",
        ]

        logger.info(f"Registered agent-builder tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load agent-builder tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "agent-builder",
    "version": "1.0.0",
    "description": "Create and manage focused micro-agents with tasks, schedules, and isolated memory",
    "tools": [
        "agent_build",
        "agent_task",
        "agent_run",
        "agent_list",
        "agent_team",
        "agent_loop",
    ],
}
