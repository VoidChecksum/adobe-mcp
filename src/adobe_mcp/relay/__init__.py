"""WebSocket relay package — persistent connection bridge to Adobe CEP panels.

Provides the relay server, protocol definitions, operation cache, and shared
startup helper. The relay is entirely optional: if websockets is not installed
or no panel connects, all tool calls fall back to the osascript/PowerShell path.
"""

from adobe_mcp.relay.protocol import MessageType, validate_message
from adobe_mcp.relay.server import RelayServer
from adobe_mcp.relay.cache import OperationCache
from adobe_mcp.relay.startup import run_with_relay

__all__ = [
    "MessageType",
    "RelayServer",
    "OperationCache",
    "run_with_relay",
    "validate_message",
]
