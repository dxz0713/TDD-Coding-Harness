"""Tool dispatcher (T6).

Routes incoming :class:`ToolCall`\\ s to the registered :class:`BaseTool`
that matches the call's *name*, and returns a structured :class:`ToolResult`.
"""

from __future__ import annotations

from typing import Any

from harness.models import ToolCall, ToolResult

from .base import BaseTool


class ToolDispatcher:
    """Holds a registry of tools and dispatches calls to them.

    Usage::

        dispatcher = ToolDispatcher()
        dispatcher.register(ReadFile())
        result = dispatcher.dispatch(ToolCall(id="1", name="read_file", ...))
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ── Registration ────────────────────────────────────────────────

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance, keyed by ``tool.name``.

        Args:
            tool: An instantiated tool.
        """
        self._tools[tool.name] = tool

    def registered_tools(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools.keys())

    # ── Dispatch ────────────────────────────────────────────────────

    def dispatch(self, call: ToolCall) -> ToolResult:
        """Dispatch a ``ToolCall`` to the matching tool.

        Args:
            call: The tool invocation from the LLM.

        Returns:
            The result returned by the tool, or an error ``ToolResult``
            if no tool is registered for ``call.name``.
        """
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {call.name!r}. "
                f"Registered tools: {self.registered_tools()}",
                exit_code=1,
            )
        try:
            return tool.execute(**call.arguments)
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Tool {call.name!r} raised {type(exc).__name__}: {exc}",
                exit_code=1,
            )