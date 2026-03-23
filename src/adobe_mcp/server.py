"""Adobe MCP Server — Full automation for all Adobe Creative Cloud apps.

Entry point for both pip (`adobe-mcp`) and direct execution (`python -m adobe_mcp`).
Starts the MCP stdio server and the WebSocket relay server concurrently.
If the relay cannot start (port occupied, websockets not installed), the
MCP server continues alone — all tools fall back to osascript/PowerShell.
"""

from mcp.server.fastmcp import FastMCP

from adobe_mcp.apps import register_all_tools

mcp = FastMCP("adobe_mcp")
register_all_tools(mcp)


def main():
    """Run the MCP server with concurrent WebSocket relay."""
    try:
        from adobe_mcp.relay.startup import run_with_relay
        run_with_relay(mcp)
    except ImportError:
        # Relay module not available (shouldn't happen in normal install,
        # but gracefully degrade to MCP-only)
        mcp.run()


if __name__ == "__main__":
    main()
