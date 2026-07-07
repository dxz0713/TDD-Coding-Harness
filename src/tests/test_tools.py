"""Tests for tool layer (T6).

Covers BaseTool abstract class, concrete tool implementations, and
ToolDispatcher registration/dispatch.
"""

from __future__ import annotations

from pathlib import Path
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


# ═══════════════════════════════════════════════════════════════════
# ReadFile (T7)
# ═══════════════════════════════════════════════════════════════════


class TestReadFile:
    """ReadFile reads a file from disk with path-traversal protection."""

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        """Reading an existing file returns its content."""
        from tools.read_file import ReadFile

        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!", encoding="utf-8")

        tool = ReadFile(allowed_root=tmp_path)
        result = tool.execute(path=str(f))
        assert result.success is True
        assert result.output == "Hello, world!"

    def test_file_not_found(self) -> None:
        """Reading a non-existent file returns an error."""
        from tools.read_file import ReadFile

        tool = ReadFile()
        result = tool.execute(path="/nonexistent_file_xyz.txt")
        assert result.success is False
        assert result.error is not None

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal (../) is blocked when it escapes the allowed root."""
        from tools.read_file import ReadFile

        tool = ReadFile(allowed_root=tmp_path)
        result = tool.execute(path=str(tmp_path / ".." / "escape.txt"))
        assert result.success is False
        assert result.error is not None
        assert "traversal" in result.error.lower() or "outside" in result.error.lower()

    def test_path_is_required(self) -> None:
        """Empty path returns an error."""
        from tools.read_file import ReadFile

        tool = ReadFile()
        result = tool.execute(path="")
        assert result.success is False
        assert result.exit_code == 1
        assert "required" in result.error


# ═══════════════════════════════════════════════════════════════════
# WriteFile (T8)
# ═══════════════════════════════════════════════════════════════════


class TestWriteFile:
    """WriteFile writes content to disk with path-traversal protection."""

    def test_writes_file(self, tmp_path: Path) -> None:
        """Writing a file produces correct content on disk."""
        from tools.write_file import WriteFile

        target = tmp_path / "out.txt"
        tool = WriteFile(allowed_root=tmp_path)
        result = tool.execute(path=str(target), content="file content")
        assert result.success is True
        assert target.read_text(encoding="utf-8") == "file content"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Writing to a deep path auto-creates parent directories."""
        from tools.write_file import WriteFile

        target = tmp_path / "a" / "b" / "c" / "deep.txt"
        tool = WriteFile(allowed_root=tmp_path)
        result = tool.execute(path=str(target), content="deep")
        assert result.success is True
        assert target.exists()
        assert target.read_text(encoding="utf-8") == "deep"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal (../) is blocked when it escapes the allowed root."""
        from tools.write_file import WriteFile

        tool = WriteFile(allowed_root=tmp_path)
        result = tool.execute(path=str(tmp_path / ".." / "escape.txt"), content="x")
        assert result.success is False
        assert result.error is not None
        assert "traversal" in result.error.lower() or "outside" in result.error.lower()

    def test_path_is_required(self) -> None:
        """Empty path returns an error."""
        from tools.write_file import WriteFile

        tool = WriteFile()
        result = tool.execute(path="", content="data")
        assert result.success is False
        assert result.exit_code == 1
        assert "required" in result.error


# ═══════════════════════════════════════════════════════════════════
# RunShell (T9)
# ═══════════════════════════════════════════════════════════════════


class TestRunShell:
    """RunShell executes shell commands with timeout and cwd support."""

    def test_echo_command(self) -> None:
        """Echo command returns the echoed text."""
        from tools.run_shell import RunShell

        tool = RunShell()
        result = tool.execute(command="echo hello")
        assert result.success is True
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_failure_exit_code(self) -> None:
        """A command that exits with non-zero returns success=False."""
        from tools.run_shell import RunShell

        tool = RunShell()
        result = tool.execute(command="python -c \"import sys; sys.exit(1)\"")
        assert result.success is False
        assert result.exit_code == 1

    def test_timeout(self) -> None:
        """A command that exceeds the timeout returns an error."""
        from tools.run_shell import RunShell

        tool = RunShell()
        result = tool.execute(
            command="python -c \"import time; time.sleep(100)\"",
            timeout=1,
        )
        assert result.success is False
        assert result.error is not None
        assert "timed out" in result.error.lower()

    def test_with_cwd(self, tmp_path: Path) -> None:
        """The cwd parameter changes the working directory."""
        from tools.run_shell import RunShell

        tool = RunShell()
        # Create a file in tmp_path, then verify it's visible from that cwd
        marker = tmp_path / "marker.txt"
        marker.write_text("present", encoding="utf-8")

        result = tool.execute(
            command="python -c \"import os; print(os.getcwd())\"",
            cwd=str(tmp_path),
        )
        assert result.success is True
        # The output should contain the tmp_path (or something close to it)
        assert str(tmp_path) in result.output

    def test_command_is_required(self) -> None:
        """Empty command returns an error."""
        from tools.run_shell import RunShell

        tool = RunShell()
        result = tool.execute(command="")
        assert result.success is False
        assert result.exit_code == 1
        assert "required" in result.error