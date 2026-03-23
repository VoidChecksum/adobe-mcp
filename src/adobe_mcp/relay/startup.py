"""Shared startup helper — runs MCP server and WebSocket relay concurrently.

All per-app servers and the main server use this to start both the MCP
stdio transport and the relay WebSocket server in the same event loop.

If the relay fails to start (port occupied, websockets not installed),
the MCP server continues normally — relay is always optional.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import anyio

from adobe_mcp.config import RELAY_PORT
from adobe_mcp.relay.server import RelayServer

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("adobe_mcp.relay.startup")


def run_with_relay(mcp_instance: FastMCP, port: int | None = None) -> None:
    """Start MCP stdio server and WebSocket relay concurrently.

    This replaces the simple `mcp.run()` call. Both services run in the
    same anyio event loop. If the relay cannot start, MCP continues alone.

    Args:
        mcp_instance: The FastMCP server instance to run.
        port: WebSocket port override. Defaults to RELAY_PORT from config.
    """
    relay_port = port if port is not None else RELAY_PORT

    async def _run_both() -> None:
        relay = RelayServer(port=relay_port)

        # Register the relay with the engine so _async_run_jsx can use it
        try:
            from adobe_mcp.engine import set_relay
            set_relay(relay)
        except ImportError:
            logger.warning("Could not register relay with engine")

        async with anyio.create_task_group() as tg:
            # Start relay in background — non-fatal if it fails
            async def _start_relay() -> None:
                try:
                    await relay.start()
                except Exception as exc:
                    logger.warning("Relay startup failed: %s — continuing without relay", exc)

            tg.start_soon(_start_relay)

            # Run MCP stdio — this blocks until the MCP session ends
            try:
                await mcp_instance.run_stdio_async()
            finally:
                # When MCP exits, shut down relay too
                await relay.stop()
                # Cancel the task group so we don't hang
                tg.cancel_scope.cancel()

    anyio.run(_run_both)
