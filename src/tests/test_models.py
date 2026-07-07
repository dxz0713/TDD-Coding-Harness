"""Tests for data models (SPEC §6)."""

import json
from enum import Enum
from typing import Any

import pytest
from pydantic import BaseModel

from harness.models import (
    AnalysisResult,
    Context,
    Decision,
    FailureType,
    Feedback,
    GuardrailResult,
    LLMResponse,
    Memory,
    Message,
    RunResult,
    StopDecision,
    ToolCall,
    ToolDef,
    ToolResult,
)


class TestMessage:
    """Message is the basic unit of LLM conversation history."""

    def test_create_system_message(self) -> None:
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant."
        assert msg.tool_call_id is None

    def test_create_tool_message(self) -> None:
        msg = Message(role="tool", content="Command output", tool_call_id="call_123")
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_123"

    def test_serialization_roundtrip(self) -> None:
        """Verify JSON serialization → deserialization preserves all fields."""
        original = Message(role="user", content="Write a function")
        data = json.loads(original.model_dump_json())
        restored = Message.model_validate(data)
        assert restored.role == original.role
        assert restored.content == original.content


class TestToolDef:
    def test_create_tool_def(self) -> None:
        tool = ToolDef(
            name="read_file",
            description="Read a file from disk",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert tool.name == "read_file"
        assert isinstance(tool.parameters, dict)

    def test_serialization_roundtrip(self) -> None:
        original = ToolDef(name="write_file", description="Write a file", parameters={})
        data = json.loads(original.model_dump_json())
        restored = ToolDef.model_validate(data)
        assert restored.name == original.name


class TestToolCall:
    def test_create_tool_call(self) -> None:
        call = ToolCall(id="call_1", name="read_file", arguments={"path": "test.txt"})
        assert call.id == "call_1"
        assert call.arguments["path"] == "test.txt"

    def test_serialization_roundtrip(self) -> None:
        original = ToolCall(id="call_1", name="read_file", arguments={"path": "x.txt"})
        data = json.loads(original.model_dump_json())
        restored = ToolCall.model_validate(data)
        assert restored.id == original.id


class TestLLMResponse:
    def test_create_with_text_only(self) -> None:
        resp = LLMResponse(content="Hello")
        assert resp.content == "Hello"
        assert resp.tool_calls == []
        assert resp.finish_reason == "stop"

    def test_create_with_tool_calls(self) -> None:
        tc = ToolCall(id="call_1", name="read_file", arguments={"path": "x.txt"})
        resp = LLMResponse(content="", tool_calls=[tc], finish_reason="tool_calls")
        assert len(resp.tool_calls) == 1
        assert resp.finish_reason == "tool_calls"


class TestToolResult:
    def test_create_success_result(self) -> None:
        result = ToolResult(success=True, output="file content")
        assert result.success is True
        assert result.output == "file content"
        assert result.error is None
        assert result.exit_code is None
        assert result.metadata == {}

    def test_create_error_result(self) -> None:
        result = ToolResult(success=False, error="File not found", exit_code=1)
        assert result.success is False
        assert result.exit_code == 1

    def test_serialization_roundtrip(self) -> None:
        original = ToolResult(success=True, output="hello", metadata={"key": "val"})
        data = json.loads(original.model_dump_json())
        restored = ToolResult.model_validate(data)
        assert restored.metadata == {"key": "val"}


class TestFailureType:
    def test_enum_values(self) -> None:
        assert FailureType.SYNTAX_ERROR.value == "syntax_error"
        assert FailureType.IMPORT_ERROR.value == "import_error"
        assert FailureType.ASSERTION_ERROR.value == "assertion_error"
        assert FailureType.TIMEOUT.value == "timeout"
        assert FailureType.RUNTIME_ERROR.value == "runtime_error"
        assert FailureType.TEST_FAILURE.value == "test_failure"
        assert FailureType.UNKNOWN.value == "unknown"

    def test_is_str_enum(self) -> None:
        """FailureType is a str enum so it serializes as plain string."""
        assert isinstance(FailureType.SYNTAX_ERROR, str)


class TestAnalysisResult:
    def test_basic_analysis(self) -> None:
        result = AnalysisResult(
            failure_type=FailureType.SYNTAX_ERROR,
            error_message="invalid syntax",
            location="test.py:10",
        )
        assert result.failure_type == FailureType.SYNTAX_ERROR
        assert result.error_message == "invalid syntax"
        assert result.location == "test.py:10"

    def test_assertion_fields(self) -> None:
        result = AnalysisResult(
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="assert 1 == 2",
            assertion_expected="2",
            assertion_actual="1",
        )
        assert result.assertion_expected == "2"
        assert result.assertion_actual == "1"

    def test_serialization_roundtrip(self) -> None:
        original = AnalysisResult(
            failure_type=FailureType.TIMEOUT,
            error_message="timed out",
        )
        data = json.loads(original.model_dump_json())
        restored = AnalysisResult.model_validate(data)
        assert restored.failure_type == FailureType.TIMEOUT


class TestFeedback:
    def test_contains_repair_prompt(self) -> None:
        analysis = AnalysisResult(
            failure_type=FailureType.SYNTAX_ERROR,
            error_message="invalid syntax",
        )
        feedback = Feedback(
            failure_type=FailureType.SYNTAX_ERROR,
            summary="Syntax error detected",
            details=analysis,
            repair_prompt="Fix the syntax error at line 10",
        )
        assert feedback.repair_prompt == "Fix the syntax error at line 10"
        assert feedback.details is analysis


class TestGuardrailResult:
    def test_allowed(self) -> None:
        result = GuardrailResult(allowed=True)
        assert result.allowed is True
        assert result.reason is None

    def test_blocked(self) -> None:
        result = GuardrailResult(allowed=False, reason="Dangerous command")
        assert result.allowed is False
        assert result.reason == "Dangerous command"


class TestDecision:
    def test_decision_fields(self) -> None:
        d = Decision(timestamp="2026-07-07T12:00:00", description="Use Python", reason="Ecosystem")
        assert d.timestamp == "2026-07-07T12:00:00"
        assert d.description == "Use Python"


class TestMemory:
    def test_empty_memory(self) -> None:
        m = Memory()
        assert m.project_name == ""
        assert m.decisions == []
        assert m.conventions == []

    def test_memory_with_data(self) -> None:
        d = Decision(timestamp="now", description="decision", reason="reason")
        m = Memory(
            project_name="Test",
            tech_stack=["Python"],
            decisions=[d],
            conventions=["Use type hints"],
        )
        assert m.project_name == "Test"
        assert len(m.decisions) == 1


class TestContext:
    def test_empty_context(self) -> None:
        ctx = Context()
        assert ctx.messages == []
        assert ctx.iteration == 0
        assert ctx.task == ""

    def test_context_with_messages(self) -> None:
        msg = Message(role="user", content="hello")
        ctx = Context(messages=[msg], iteration=1, task="test")
        assert len(ctx.messages) == 1
        assert ctx.iteration == 1


class TestStopDecision:
    def test_stop_true_success(self) -> None:
        d = StopDecision(should_stop=True, success=True, reason="Tests passed")
        assert d.should_stop is True
        assert d.success is True

    def test_stop_true_failure(self) -> None:
        d = StopDecision(should_stop=True, success=False, reason="Max iterations")
        assert d.should_stop is True
        assert d.success is False


class TestRunResult:
    def test_success_result(self) -> None:
        r = RunResult(success=True, artifacts=["output.txt"], iterations=3)
        assert r.success is True
        assert r.iterations == 3

    def test_failure_result(self) -> None:
        r = RunResult(success=False, error="Something went wrong")
        assert r.success is False
        assert r.error == "Something went wrong"

    def test_serialization_roundtrip(self) -> None:
        original = RunResult(success=True, iterations=2)
        data = json.loads(original.model_dump_json())
        restored = RunResult.model_validate(data)
        assert restored.success == original.success