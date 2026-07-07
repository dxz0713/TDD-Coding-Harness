"""Tests for ContextManager (T12).

Covers building initial context, appending tool results, appending
feedback, and iteration counting.
"""

from __future__ import annotations

from harness.context import ContextManager
from harness.models import (
    AnalysisResult,
    Context,
    FailureType,
    Feedback,
    Memory,
    ToolCall,
    ToolDef,
    ToolResult,
)


class TestContextManager:
    """ContextManager builds and updates conversation context."""

    # ── build ───────────────────────────────────────────────────────

    def test_build_creates_system_prompt(self) -> None:
        """build() 返回的 Context 包含系统提示词。"""
        cm = ContextManager()
        ctx = cm.build(task="Fix the bug in main.py", tool_defs=[])
        assert isinstance(ctx, Context)
        assert len(ctx.messages) == 1
        assert ctx.messages[0].role == "system"
        assert "Fix the bug in main.py" in ctx.messages[0].content
        assert ctx.task == "Fix the bug in main.py"
        assert ctx.iteration == 0

    def test_build_includes_tool_defs(self) -> None:
        """系统提示词中包含工具定义。"""
        cm = ContextManager()
        tool_defs = [
            ToolDef(
                name="read_file",
                description="Read a file",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            ToolDef(
                name="write_file",
                description="Write a file",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            ),
        ]
        ctx = cm.build(task="Test task", tool_defs=tool_defs)
        content = ctx.messages[0].content
        assert "read_file" in content
        assert "write_file" in content
        assert "Read a file" in content
        assert "path" in content

    def test_build_with_memory(self) -> None:
        """build() 含 memory 时系统提示词包含项目信息。"""
        memory = Memory(
            project_name="MyProject",
            tech_stack=["python", "pytest"],
            conventions=["Use type hints"],
        )
        cm = ContextManager(memory=memory)
        ctx = cm.build(task="Implement feature", tool_defs=[])
        content = ctx.messages[0].content
        assert "MyProject" in content
        assert "python" in content
        assert "Use type hints" in content

    # ── append_tool_result ──────────────────────────────────────────

    def test_append_tool_result(self) -> None:
        """追加工具结果后 messages 长度增加，role 为 "tool"。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        tool_call = ToolCall(id="call_1", name="read_file", arguments={"path": "test.txt"})
        result = ToolResult(success=True, output="file content")
        ctx = cm.append_tool_result(ctx, tool_call, result)
        assert len(ctx.messages) == 2
        assert ctx.messages[1].role == "tool"
        assert ctx.messages[1].content == "file content"
        assert ctx.messages[1].tool_call_id == "call_1"

    def test_append_tool_result_with_error(self) -> None:
        """工具错误时 content 包含错误信息。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        tool_call = ToolCall(id="call_2", name="run_shell", arguments={"command": "false"})
        result = ToolResult(success=False, error="Command failed with exit code 1")
        ctx = cm.append_tool_result(ctx, tool_call, result)
        assert ctx.messages[1].content == "Command failed with exit code 1"

    # ── append_feedback ─────────────────────────────────────────────

    def test_append_feedback(self) -> None:
        """追加反馈后 messages 包含反馈内容。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        feedback = Feedback(
            failure_type=FailureType.SYNTAX_ERROR,
            summary="Syntax error in main.py",
            details=AnalysisResult(
                failure_type=FailureType.SYNTAX_ERROR,
                error_message="invalid syntax at line 10",
            ),
            repair_prompt="Fix the syntax error",
        )
        ctx = cm.append_feedback(ctx, feedback)
        assert len(ctx.messages) == 2
        assert ctx.messages[1].role == "user"
        assert "Syntax error in main.py" in ctx.messages[1].content
        assert "Fix the syntax error" in ctx.messages[1].content

    # ── iteration ───────────────────────────────────────────────────

    def test_iteration_increments(self) -> None:
        """每次追加后 iteration +1。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        tool_call = ToolCall(id="call_1", name="read_file", arguments={"path": "x.txt"})
        result = ToolResult(success=True, output="data")
        ctx = cm.append_tool_result(ctx, tool_call, result)
        assert ctx.iteration == 1
        ctx = cm.append_tool_result(ctx, tool_call, result)
        assert ctx.iteration == 2

    def test_iteration_increments_on_feedback(self) -> None:
        """feedback 追加也增加 iteration。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        feedback = Feedback(
            failure_type=FailureType.TEST_FAILURE,
            summary="Tests failed",
            details=AnalysisResult(
                failure_type=FailureType.TEST_FAILURE,
                error_message="assertion error",
            ),
            repair_prompt="Fix tests",
        )
        ctx = cm.append_feedback(ctx, feedback)
        assert ctx.iteration == 1

    # ── Mixed operations ────────────────────────────────────────────

    def test_multiple_appends(self) -> None:
        """多次追加后 messages 长度正确。"""
        cm = ContextManager()
        ctx = cm.build(task="Test", tool_defs=[])
        tc1 = ToolCall(id="c1", name="read_file", arguments={"path": "a.txt"})
        tc2 = ToolCall(id="c2", name="write_file", arguments={"path": "b.txt", "content": "x"})
        ctx = cm.append_tool_result(ctx, tc1, ToolResult(success=True, output="a"))
        ctx = cm.append_tool_result(ctx, tc2, ToolResult(success=True, output="b"))
        feedback = Feedback(
            failure_type=FailureType.RUNTIME_ERROR,
            summary="Error",
            details=AnalysisResult(
                failure_type=FailureType.RUNTIME_ERROR,
                error_message="runtime error",
            ),
            repair_prompt="Fix",
        )
        ctx = cm.append_feedback(ctx, feedback)
        assert len(ctx.messages) == 4  # system + 2 tool + 1 feedback
        assert ctx.iteration == 3