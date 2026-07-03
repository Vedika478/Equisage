"""
Shared helper to construct MCPToolset instances pointing at the
EquiSage Market Data MCP server (run via stdio).

Each agent imports from this module so the server path is maintained
in one place.
"""

import os
import sys

from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

# Absolute path to the market data MCP server script
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER_SCRIPT = os.path.join(_HERE, "mcp_servers", "market_data_server.py")


def make_mcp_toolset(tool_filter: list[str] | None = None) -> MCPToolset:
    """
    Create an MCPToolset that launches market_data_server.py via stdio.

    Args:
        tool_filter: Optional list of tool names to expose to the agent.
                     If None, all tools are exposed.

    Returns:
        Configured MCPToolset instance.
    """
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,  # use same Python interpreter
                args=[_SERVER_SCRIPT],
                cwd=_HERE,
            ),
            timeout=30.0,
        ),
        tool_filter=tool_filter,
    )
