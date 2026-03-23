"""Local operation cache — append-only log of JSX executions.

Records every JSX execution through the relay (and optionally osascript)
for replay capability, state recovery, and workflow extraction.

Storage layout:
    .cache/relay/
        operations.jsonl      — append-only log of all executions
        snapshots/
            {app}_latest.json — periodic per-app state snapshots
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("adobe_mcp.relay.cache")

# Default cache root relative to the project working directory
_DEFAULT_CACHE_DIR = Path(".cache") / "relay"


class OperationCache:
    """Append-only operation log and snapshot store for relay executions.

    Usage:
        cache = OperationCache()                    # uses .cache/relay/
        cache = OperationCache("/tmp/my-cache")     # custom location

        cache.record("illustrator", "adobe_ai_shapes", "abc123", {...}, "Rect created", True)
        history = cache.get_history(app="illustrator", limit=10)
    """

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        self._ops_file = self.cache_dir / "operations.jsonl"
        self._snapshots_dir = self.cache_dir / "snapshots"

        # Ensure directories exist on first use
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        app: str,
        tool_name: str,
        jsx_hash: str,
        params: dict[str, Any],
        result_summary: str,
        success: bool,
    ) -> None:
        """Append an operation record to the JSONL log.

        Args:
            app: Adobe app name (e.g. "illustrator").
            tool_name: MCP tool that triggered this execution.
            jsx_hash: Hash of the JSX code for deduplication/replay.
            params: Tool parameters (sanitized for logging).
            result_summary: Brief human-readable result description.
            success: Whether the execution succeeded.
        """
        entry = {
            "ts": time.time(),
            "app": app,
            "tool": tool_name,
            "jsx_hash": jsx_hash,
            "params": params,
            "result_summary": result_summary,
            "success": success,
        }
        try:
            with open(self._ops_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as exc:
            logger.warning("Failed to write operation cache: %s", exc)

    def get_history(self, app: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Read recent operations from the JSONL log.

        Args:
            app: If provided, filter to only this app's operations.
            limit: Maximum number of records to return (most recent first).

        Returns:
            List of operation dicts, newest first.
        """
        if not self._ops_file.exists():
            return []

        entries: list[dict[str, Any]] = []
        try:
            with open(self._ops_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if app is None or entry.get("app") == app:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:
            logger.warning("Failed to read operation cache: %s", exc)
            return []

        # Return most recent first, limited
        return entries[-limit:][::-1]

    def save_snapshot(self, app: str, state_dict: dict[str, Any]) -> None:
        """Save a state snapshot for an app.

        Overwrites the previous snapshot for this app. Snapshots capture
        the last known document state so sessions can recover after crashes.

        Args:
            app: Adobe app name.
            state_dict: Arbitrary state dict to persist.
        """
        snapshot_path = self._snapshots_dir / f"{app}_latest.json"
        try:
            snapshot = {
                "ts": time.time(),
                "app": app,
                "state": state_dict,
            }
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, default=str)
        except OSError as exc:
            logger.warning("Failed to save snapshot for %s: %s", app, exc)

    def load_snapshot(self, app: str) -> dict[str, Any] | None:
        """Load the latest state snapshot for an app.

        Args:
            app: Adobe app name.

        Returns:
            The snapshot dict if one exists, otherwise None.
        """
        snapshot_path = self._snapshots_dir / f"{app}_latest.json"
        if not snapshot_path.exists():
            return None
        try:
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load snapshot for %s: %s", app, exc)
            return None


def jsx_hash(jsx_code: str) -> str:
    """Compute a short hash of JSX code for cache deduplication.

    Args:
        jsx_code: The ExtendScript source code.

    Returns:
        First 12 hex characters of the SHA-256 hash.
    """
    return hashlib.sha256(jsx_code.encode("utf-8")).hexdigest()[:12]
