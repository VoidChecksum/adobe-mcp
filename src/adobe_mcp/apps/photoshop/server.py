"""Standalone Photoshop MCP server — loads only common + Photoshop tools.

Entry point: `adobe-mcp-ps` (registered in pyproject.toml)

This starts a focused server with ~27 tools instead of the full 54,
saving context in dedicated Photoshop sessions.
"""

from mcp.server.fastmcp import FastMCP

from adobe_mcp.apps.common import register_common_tools
from adobe_mcp.apps.photoshop import register_photoshop_tools

mcp = FastMCP("adobe_photoshop")
register_common_tools(mcp)
register_photoshop_tools(mcp)


def main():
    """Run the Photoshop-only MCP server with concurrent WebSocket relay."""
    try:
        from adobe_mcp.relay.startup import run_with_relay
        run_with_relay(mcp)
    except ImportError:
        mcp.run()


if __name__ == "__main__":
    main()
