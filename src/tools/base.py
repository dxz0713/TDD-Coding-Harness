"""Abstract tool interface (T6).

Every tool that the LLM can invoke is a subclass of :class:`BaseTool`,
which declares its identity and schema at the class level.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from harness.models import ToolResult


class BaseTool(ABC):
    """Abstract base for all executable tools.

    Subclasses **must** set *name*, *description*, and *input_schema* as
    class-level attributes, and implement :meth:`execute`.

    Example::

        class ReadFile(BaseTool):
            name = "read_file"
            description = "Read a file from disk"
            input_schema = {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            }

            def execute(self, path: str) -> ToolResult:
                ...
    """

    # ── Class-level metadata (override in subclasses) ───────────────

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}

    # ── Execution ───────────────────────────────────────────────────

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Run the tool with the given keyword arguments.

        Args:
            **kwargs: Arguments matching *input_schema*.

        Returns:
            A ``ToolResult`` indicating success or failure.
        """
        ...