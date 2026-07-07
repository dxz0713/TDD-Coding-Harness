"""Tests for tool layer (T6).

Covers BaseTool abstract class, concrete tool implementations, and
ToolDispatcher registration/dispatch.
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.models import ToolCall, ToolResult
from tools.base import BaseTool
from tools.dispatcher import ToolDispatcher


# ═══════════════════════════════════════════════════════════════════
# Concrete tools for testing
# ═══════════════════════════════════════════════════════════════════


class _ReadFile(BaseTool):
    """Tool that reads a file (simulated)."""

    name = "read_file"
    description = "Read a file from disk"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
        "required": ["path"],
    }

    def execute(self, path: str = "") -> ToolResult:
        if not path:
            return ToolResult(success=False, error="path is required", exit_code=1)
        if path == "/error":
            msg = "mock permission denied"
            return ToolResult(success=False, error=msg, exit_code=1)
        return ToolResult(success=True, output=f"Content of {path}")


class _WriteFile(BaseTool):
    """Tool that writes a file (simulated)."""

    name = "write_file"
    description = "Write a file to disk"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    def execute(self, path: str = "", content: str = "") -> ToolResult:
        if not path:
            return ToolResult(success=False, error="path is required", exit_code=1)
        return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")


class _FailingTool(BaseTool):
    """Tool whose execute() raises an unexpected exception."""

    name = "crash"
    description = "This tool crashes"
    input_schema = {"type": "object", "properties": {}}

    def execute(self) -> ToolResult:
        msg = "internal failure"
        raise RuntimeError(msg)


# ═══════════════════════════════════════════════════════════════════
# BaseTool
# ═══════════════════════════════════════════════════════════════════


class TestBaseTool:
    """BaseTool cannot be instantiated directly; subclasses must define metadata."""

    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore[abstract]

    def test_concrete_tool_has_metadata(self) -> None:
        tool = _ReadFile()
        assert tool.name == "read_file"
        assert tool.description == "Read a file from disk"
        assert "path" in tool.input_schema["properties"]

    def test_execute_returns_tool_result(self) -> None:
        tool = _ReadFile()
        result = tool.execute(path="test.txt")
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "Content of test.txt" in result.output

    def test_execute_failure_result(self) -> None:
        tool = _ReadFile()
        result = tool.execute()
        assert result.success is False
        assert result.exit_code == 1

    def test_multiple_tools_have_distinct_names(self) -> None:
        assert _ReadFile.name != _WriteFile.name


# ═══════════════════════════════════════════════════════════════════
# ToolDispatcher
# ═══════════════════════════════════════════════════════════════════


class TestToolDispatcherRegistration:
    """Tools can be registered and listed."""

    def test_register_single_tool(self) -> None:
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        assert dispatcher.registered_tools() == ["read_file"]

    def test_register_multiple_tools(self) -> None:
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        dispatcher.register(_WriteFile())
        assert dispatcher.registered_tools() == ["read_file", "write_file"]

    def test_empty_dispatcher(self) -> None:
        dispatcher = ToolDispatcher()
        assert dispatcher.registered_tools() == []

    def test_register_overwrites_existing(self) -> None:
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        dispatcher.register(_ReadFile())  # re-register same name
        assert dispatcher.registered_tools() == ["read_file"]


class TestToolDispatcherDispatch:
    """Dispatch routes ToolCalls to the correct tool."""

    def test_dispatch_to_registered_tool(self) -> None:
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        call = ToolCall(
            id="call_1",
            name="read_file",
            arguments={"path": "hello.txt"},
        )
        result = dispatcher.dispatch(call)
        assert result.success is True
        assert "hello.txt" in result.output

    def test_dispatch_routes_by_name(self) -> None:
        """Dispatch selects the correct tool among many by call.name."""
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        dispatcher.register(_WriteFile())
        call = ToolCall(
            id="call_2",
            name="write_file",
            arguments={"path": "out.txt", "content": "data"},
        )
        result = dispatcher.dispatch(call)
        assert result.success is True
        assert "Written" in result.output
        assert "out.txt" in result.output

    def test_dispatch_unknown_tool_returns_error(self) -> None:
        dispatcher = ToolDispatcher()
        call = ToolCall(
            id="call_3",
            name="nonexistent",
            arguments={},
        )
        result = dispatcher.dispatch(call)
        assert result.success is False
        assert result.exit_code == 1
        assert "Unknown tool" in result.error
        assert "nonexistent" in result.error

    def test_dispatch_empty_registry_returns_error(self) -> None:
        dispatcher = ToolDispatcher()
        call = ToolCall(
            id="call_4",
            name="anything",
            arguments={},
        )
        result = dispatcher.dispatch(call)
        assert result.success is False
        assert result.error is not None

    def test_dispatch_tool_that_raises_exception(self) -> None:
        """If a tool's execute() raises, the dispatcher catches it and returns an error ToolResult."""
        dispatcher = ToolDispatcher()
        dispatcher.register(_FailingTool())
        call = ToolCall(id="call_5", name="crash", arguments={})
        result = dispatcher.dispatch(call)
        assert result.success is False
        assert result.exit_code == 1
        assert "RuntimeError" in result.error

    def test_dispatch_without_required_args(self) -> None:
        """Tools should handle missing arguments gracefully via defaults (if designed to)."""
        dispatcher = ToolDispatcher()
        dispatcher.register(_ReadFile())
        call = ToolCall(
            id="call_6",
            name="read_file",
            arguments={},  # path is missing
        )
        result = dispatcher.dispatch(call)
        assert result.success is False
        assert result.exit_code == 1