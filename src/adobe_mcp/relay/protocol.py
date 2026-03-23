"""WebSocket relay protocol — message types and helpers.

Defines the message format for communication between the Python MCP server
and CEP panels running inside Adobe apps. All messages are JSON dicts with
at minimum a `type` field and an `id` field (UUID4 for correlation).
"""

import uuid
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Message types for the WebSocket relay protocol."""

    # Server -> Panel: execute this JSX code
    EXECUTE = "execute"

    # Panel -> Server: result of JSX execution
    RESULT = "result"

    # Panel -> Server: periodic heartbeat with app identification
    HEARTBEAT = "heartbeat"

    # Server -> Panel: sent after first heartbeat identifies the app
    WELCOME = "welcome"

    # Either direction: error report
    ERROR = "error"


def make_id() -> str:
    """Generate a new message correlation ID (UUID4 hex string)."""
    return uuid.uuid4().hex


def make_execute(jsx_code: str, msg_id: str | None = None) -> dict[str, Any]:
    """Create an EXECUTE message to send JSX code to a CEP panel.

    Args:
        jsx_code: The ExtendScript code to execute.
        msg_id: Optional correlation ID. Generated if not provided.

    Returns:
        Message dict ready for JSON serialization.
    """
    return {
        "type": MessageType.EXECUTE.value,
        "id": msg_id or make_id(),
        "jsx": jsx_code,
    }


def make_result(msg_id: str, success: bool, stdout: str = "", stderr: str = "") -> dict[str, Any]:
    """Create a RESULT message reporting JSX execution outcome.

    Args:
        msg_id: Correlation ID matching the original EXECUTE message.
        success: Whether execution completed without error.
        stdout: Captured output from the script.
        stderr: Error output, if any.

    Returns:
        Message dict ready for JSON serialization.
    """
    return {
        "type": MessageType.RESULT.value,
        "id": msg_id,
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
    }


def make_heartbeat(app: str, version: str = "") -> dict[str, Any]:
    """Create a HEARTBEAT message identifying a connected panel.

    Args:
        app: Adobe app name (e.g. "photoshop", "illustrator").
        version: Optional app version string.

    Returns:
        Message dict ready for JSON serialization.
    """
    return {
        "type": MessageType.HEARTBEAT.value,
        "id": make_id(),
        "app": app,
        "version": version,
    }


def make_welcome(app: str) -> dict[str, Any]:
    """Create a WELCOME message acknowledging a panel's first heartbeat.

    Args:
        app: The app name that was identified.

    Returns:
        Message dict ready for JSON serialization.
    """
    return {
        "type": MessageType.WELCOME.value,
        "id": make_id(),
        "app": app,
        "message": f"Connected as {app}",
    }


def make_error(msg_id: str, error: str) -> dict[str, Any]:
    """Create an ERROR message.

    Args:
        msg_id: Correlation ID of the message that caused the error.
        error: Human-readable error description.

    Returns:
        Message dict ready for JSON serialization.
    """
    return {
        "type": MessageType.ERROR.value,
        "id": msg_id,
        "error": error,
    }


def validate_message(msg: dict[str, Any]) -> bool:
    """Check that a message dict has the required fields.

    All messages must have 'type' and 'id'. HEARTBEAT messages also require 'app'.
    RESULT messages also require 'success'.

    Args:
        msg: Parsed message dict.

    Returns:
        True if the message has all required fields for its type.
    """
    if not isinstance(msg, dict):
        return False
    if "type" not in msg or "id" not in msg:
        return False

    msg_type = msg.get("type")

    if msg_type == MessageType.HEARTBEAT.value:
        return "app" in msg

    if msg_type == MessageType.RESULT.value:
        return "success" in msg

    if msg_type == MessageType.EXECUTE.value:
        return "jsx" in msg

    # WELCOME and ERROR are valid with just type + id
    return msg_type in {t.value for t in MessageType}
