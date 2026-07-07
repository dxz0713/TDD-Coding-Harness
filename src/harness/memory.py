"""Memory store — JSON file-based cross-session persistence (T14).

The MemoryStore loads and saves project memory (decisions, conventions,
tech stack) as a JSON file, with automatic truncation when the file
exceeds a size limit.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from harness.models import Decision, Memory

# Max file size before truncation (1 MB).
_MAX_FILE_SIZE: int = 1_048_576  # 1 MB in bytes

# Number of most-recent decisions to keep after truncation.
_KEEP_DECISIONS: int = 100


class MemoryStore:
    """Persistent project memory backed by a JSON file.

    The store is scoped to a single file path. All operations are
    read/write to that file.
    """

    def __init__(self, path: str = "output/memory.json") -> None:
        """Initialize the memory store.

        Args:
            path: Path to the JSON file used for persistence.
        """
        self._path = path

    # ── Public API ──────────────────────────────────────────────────

    def load(self) -> Memory:
        """Load memory from the JSON file.

        Returns:
            Memory instance populated from the file, or an empty Memory
            if the file does not exist or is invalid.
        """
        path = Path(self._path)
        if not path.exists():
            return Memory()

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return Memory.model_validate(data)
        except (json.JSONDecodeError, ValueError, OSError):
            return Memory()

    def save(self, memory: Memory) -> None:
        """Save memory to the JSON file.

        Creates parent directories if they do not exist. Automatically
        truncates the file if it exceeds the size limit.

        Args:
            memory: The Memory instance to persist.
        """
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Check size before writing
        if path.exists() and path.stat().st_size > _MAX_FILE_SIZE:
            self._truncate(memory)

        raw = memory.model_dump_json(indent=2, exclude_none=True)
        path.write_text(raw, encoding="utf-8")

    def add_decision(self, memory: Memory, decision: Decision) -> Memory:
        """Append a decision record to the memory.

        Args:
            memory: The current Memory instance.
            decision: The decision to append.

        Returns:
            A new Memory (or modified input) with the decision appended.
        """
        memory.decisions.append(decision)
        return memory

    def get_context(self, memory: Memory) -> str:
        """Return a formatted context summary string from memory.

        Args:
            memory: The Memory instance to format.

        Returns:
            A human-readable string summarising the project memory.
        """
        parts: list[str] = []

        if memory.project_name:
            parts.append(f"Project: {memory.project_name}")

        if memory.project_description:
            parts.append(f"Description: {memory.project_description}")

        if memory.tech_stack:
            parts.append(f"Tech stack: {', '.join(memory.tech_stack)}")

        if memory.conventions:
            parts.append("Conventions:")
            for c in memory.conventions:
                parts.append(f"  - {c}")

        if memory.decisions:
            parts.append(f"Decisions ({len(memory.decisions)} total):")
            for d in memory.decisions[-5:]:  # last 5
                parts.append(f"  - [{d.timestamp}] {d.description} ({d.reason})")

        return "\n".join(parts) if parts else "No project context available."

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _truncate(memory: Memory) -> None:
        """Truncate memory to keep only the most recent decisions.

        Mutates the memory in place.

        Args:
            memory: The Memory instance to truncate.
        """
        if len(memory.decisions) > _KEEP_DECISIONS:
            memory.decisions = memory.decisions[-_KEEP_DECISIONS:]