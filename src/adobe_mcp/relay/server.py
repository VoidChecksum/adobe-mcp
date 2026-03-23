"""WebSocket relay server — persistent connection bridge to CEP panels.

Provides the RelayServer class that maintains WebSocket connections to
Adobe CEP panels. Each panel identifies itself via HEARTBEAT messages,
and the server can dispatch EXECUTE messages to run JSX code through
the panel's CSInterface.evalScript() instead of the osascript subprocess path.

The relay is entirely optional: if no panel is connected for an app,
the engine falls back to the original osascript/PowerShell execution path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from adobe_mcp.config import RELAY_HOST, RELAY_PORT, RELAY_STALE_THRESHOLD
from adobe_mcp.relay.protocol import (
    MessageType,
    make_error,
    make_execute,
    make_id,
    make_welcome,
    validate_message,
)

logger = logging.getLogger("adobe_mcp.relay")

# Guard the websockets import — relay is disabled if the library is missing
try:
    import websockets
    from websockets.server import WebSocketServerProtocol

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    WebSocketServerProtocol = Any  # type: ignore[assignment,misc]


class RelayServer:
    """Async WebSocket server that bridges MCP tool calls to CEP panels.

    Lifecycle:
        relay = RelayServer()
        await relay.start()     # begins accepting connections
        ...
        await relay.stop()      # graceful shutdown

    Connection flow:
        1. CEP panel connects via WebSocket.
        2. Panel sends a HEARTBEAT with its app name.
        3. Server sends WELCOME, registers the connection.
        4. Panel continues sending HEARTBEATs every 5 seconds.
        5. Server can send EXECUTE messages; panel replies with RESULT.
    """

    def __init__(self, host: str = RELAY_HOST, port: int = RELAY_PORT) -> None:
        self.host = host
        self.port = port

        # Connection registry: app name -> active WebSocket
        self._connections: dict[str, WebSocketServerProtocol] = {}

        # Pending JSX execution requests: message_id -> Future
        self._pending: dict[str, asyncio.Future] = {}

        # Heartbeat tracking: app name -> last heartbeat timestamp
        self._last_heartbeat: dict[str, float] = {}

        # Operation recording buffer (populated by cache integration)
        self._recording: list[dict] = []

        # Server handle for shutdown
        self._server: Any = None
        self._started = False

    # ── Public API ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the WebSocket server. Non-blocking — returns after binding."""
        if not HAS_WEBSOCKETS:
            logger.warning(
                "websockets library not installed — relay server disabled. "
                "Install with: pip install 'websockets>=12.0'"
            )
            return

        try:
            self._server = await websockets.serve(
                self._handler,
                self.host,
                self.port,
            )
            self._started = True
            logger.info("Relay server listening on ws://%s:%d", self.host, self.port)
        except OSError as exc:
            # Port already in use — warn and continue without relay
            logger.warning(
                "Relay server could not bind to %s:%d (%s) — relay disabled",
                self.host,
                self.port,
                exc,
            )

    async def stop(self) -> None:
        """Gracefully shut down the relay server and cancel pending requests."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            self._started = False
            logger.info("Relay server stopped")

        # Cancel any pending futures so callers don't hang
        for msg_id, future in self._pending.items():
            if not future.done():
                future.cancel()
        self._pending.clear()
        self._connections.clear()
        self._last_heartbeat.clear()

    def is_connected(self, app: str) -> bool:
        """Check if an app has a fresh WebSocket connection.

        A connection is considered fresh if a heartbeat was received within
        RELAY_STALE_THRESHOLD seconds (default 15s, i.e. 3 missed beats).

        Args:
            app: Adobe app name (e.g. "photoshop").

        Returns:
            True if the app has a live, non-stale connection.
        """
        if app not in self._connections:
            return False
        last_beat = self._last_heartbeat.get(app, 0)
        return (time.time() - last_beat) < RELAY_STALE_THRESHOLD

    @property
    def connected_apps(self) -> list[str]:
        """List of currently connected app names with fresh heartbeats."""
        return [app for app in self._connections if self.is_connected(app)]

    async def execute_jsx(self, app: str, jsx_code: str, timeout: float = 120) -> dict[str, Any]:
        """Send JSX code to a connected CEP panel and await the result.

        Creates an EXECUTE message, sends it over the WebSocket, and waits
        for the panel to reply with a RESULT message bearing the same ID.

        Args:
            app: Target Adobe app name.
            jsx_code: ExtendScript code to execute.
            timeout: Maximum seconds to wait for a result.

        Returns:
            Dict matching the engine result format:
            {"success": bool, "stdout": str, "stderr": str, "returncode": int}

        Raises:
            ConnectionError: If no live connection exists for the app.
            TimeoutError: If the panel doesn't respond within timeout.
        """
        if not self.is_connected(app):
            raise ConnectionError(f"No live relay connection for {app}")

        ws = self._connections[app]
        msg_id = make_id()
        msg = make_execute(jsx_code, msg_id)

        # Create a future for the response
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[msg_id] = future

        try:
            await ws.send(json.dumps(msg))
            result = await asyncio.wait_for(future, timeout=timeout)

            # Normalize to engine result format
            return {
                "success": result.get("success", False),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "returncode": 0 if result.get("success") else 1,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Relay timeout after {timeout}s waiting for {app}",
                "returncode": -1,
            }
        except websockets.exceptions.ConnectionClosed:
            # Connection dropped mid-request — caller should fall back
            self._unregister_app(app)
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Relay connection to {app} closed during execution",
                "returncode": -1,
            }
        finally:
            self._pending.pop(msg_id, None)

    # ── WebSocket Handler ────────────────────────────────────────────

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """Handle an incoming WebSocket connection from a CEP panel.

        The first HEARTBEAT message identifies the app. Subsequent messages
        are dispatched by type: HEARTBEAT updates freshness, RESULT resolves
        pending futures, ERROR logs and resolves with failure.
        """
        app_name: str | None = None

        try:
            async for raw_message in websocket:
                try:
                    msg = json.loads(raw_message)
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Relay received non-JSON message, ignoring")
                    continue

                if not validate_message(msg):
                    logger.warning("Relay received invalid message: %s", msg.get("type", "?"))
                    continue

                msg_type = msg["type"]

                if msg_type == MessageType.HEARTBEAT.value:
                    incoming_app = msg["app"].lower()

                    if app_name is None:
                        # First heartbeat — register this connection
                        app_name = incoming_app
                        self._register_app(app_name, websocket)
                        logger.info("Panel connected: %s", app_name)

                        # Send WELCOME
                        welcome = make_welcome(app_name)
                        await websocket.send(json.dumps(welcome))

                    # Update heartbeat timestamp
                    self._last_heartbeat[app_name] = time.time()

                elif msg_type == MessageType.RESULT.value:
                    msg_id = msg["id"]
                    future = self._pending.get(msg_id)
                    if future and not future.done():
                        future.set_result(msg)
                    else:
                        logger.warning("Received RESULT for unknown/completed request: %s", msg_id)

                elif msg_type == MessageType.ERROR.value:
                    msg_id = msg["id"]
                    future = self._pending.get(msg_id)
                    if future and not future.done():
                        # Resolve the future with an error result
                        future.set_result({
                            "success": False,
                            "stdout": "",
                            "stderr": msg.get("error", "Unknown panel error"),
                        })
                    else:
                        logger.warning("Relay ERROR from panel: %s", msg.get("error", "?"))

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception:
            logger.exception("Unexpected error in relay handler")
        finally:
            if app_name:
                self._unregister_app(app_name)
                logger.info("Panel disconnected: %s", app_name)

    # ── Internal Helpers ─────────────────────────────────────────────

    def _register_app(self, app: str, websocket: WebSocketServerProtocol) -> None:
        """Register a WebSocket connection for an app, replacing any stale one."""
        old_ws = self._connections.get(app)
        if old_ws is not None and old_ws != websocket:
            # Close stale connection silently — panel probably reconnected
            asyncio.ensure_future(old_ws.close())
        self._connections[app] = websocket
        self._last_heartbeat[app] = time.time()

    def _unregister_app(self, app: str) -> None:
        """Remove an app's connection and heartbeat tracking."""
        self._connections.pop(app, None)
        self._last_heartbeat.pop(app, None)
