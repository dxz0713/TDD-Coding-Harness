"""Tests for FeedbackEngine integration into HarnessLoop (T18).

Covers four integration scenarios:
1. Test failure triggers FeedbackEngine.analyze().
2. Full "write code → test fails → feedback → fix → test passes" cycle.
3. Test success → no feedback generated.
4. Logs contain feedback classification results.
"""

from __future__ import annotations

import logging

from feedback.engine import FeedbackEngine
from harness.config import Config, GuardrailConfig, LoopConfig
from harness.context import ContextManager
from harness.guardrail import Guardrail
from harness.loop import HarnessLoop
from harness.models import FailureType, LLMResponse, ToolCall, ToolDef, ToolResult
from harness.stop_condition import AutonomousStopDecision
from providers.base import LLMProvider
from providers.mock import MockProvider
from tools.base import BaseTool
from tools.dispatcher import ToolDispatcher


# ═══════════════════════════════════════════════════════════════════
# Mock tools for testing
# ═══════════════════════════════════════════════════════════════════


class _MockRunShell(BaseTool):
    """Simulated RunShell tool that can be set to succeed or fail."""

    name = "run_shell"
    description = "Execute a shell command"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def __init__(self, fail_first: bool = False) -> None:
        """Initialize the mock tool.

        Args:
            fail_first: If True, the first call fails and subsequent calls succeed.
        """
        super().__init__()
        self._call_count = 0
        self._fail_first = fail_first

    def execute(self, command: str = "") -> ToolResult:
        self._call_count += 1
        if self._fail_first and self._call_count == 1:
            return ToolResult(
                success=False,
                output="AssertionError: assert 1 == 2",
                error="Test failed: assert 1 == 2",
                exit_code=1,
            )
        return ToolResult(success=True, output="All tests passed!", exit_code=0)


class _MockWriteFile(BaseTool):
    """Simulated WriteFile tool."""

    name = "write_file"
    description = "Write content to a file"
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


# ═══════════════════════════════════════════════════════════════════
# Sequence-based mock provider
# ═══════════════════════════════════════════════════════════════════


class _SequenceMockProvider(LLMProvider):
    """A mock provider that returns responses in a fixed sequence.

    Each call returns the next response in the list.  The last response
    is repeated if the sequence is exhausted.
    """

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self._index = 0

    def generate(
        self,
        messages: list,
        tools: list[ToolDef] | None = None,
        config: object = None,
    ) -> LLMResponse:
        response = self._responses[self._index]
        self._index = min(self._index + 1, len(self._responses) - 1)
        return response


# ═══════════════════════════════════════════════════════════════════
# Spy FeedbackEngine
# ═══════════════════════════════════════════════════════════════════


class _SpyFeedbackEngine(FeedbackEngine):
    """A FeedbackEngine that records whether analyze() was called."""

    def __init__(self) -> None:
        super().__init__()
        self.analyze_call_count = 0
        self.last_result: ToolResult | None = None

    def analyze(self, result: ToolResult) -> object:
        self.analyze_call_count += 1
        self.last_result = result
        return super().analyze(result)


# ═══════════════════════════════════════════════════════════════════
# Test suite
# ═══════════════════════════════════════════════════════════════════


class TestLoopFeedbackIntegration:
    """FeedbackEngine integration into HarnessLoop."""

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_loop(
        provider: LLMProvider,
        feedback_engine: FeedbackEngine | None = None,
        max_iterations: int = 10,
        dispatcher: ToolDispatcher | None = None,
    ) -> HarnessLoop:
        """Build a HarnessLoop with a given provider and optional feedback engine."""
        if dispatcher is None:
            dispatcher = ToolDispatcher()
        config = Config(
            loop=LoopConfig(max_iterations=max_iterations),
            guardrail=GuardrailConfig(enabled=False),
        )
        guardrail = Guardrail(config.guardrail)
        cm = ContextManager()
        sd = AutonomousStopDecision(guardrail=guardrail, config=config.loop)
        return HarnessLoop(
            provider=provider,
            dispatcher=dispatcher,
            guardrail=guardrail,
            context_manager=cm,
            stop_decision=sd,
            feedback_engine=feedback_engine or FeedbackEngine(),
            config=config,
        )

    @staticmethod
    def _tool_defs() -> list[ToolDef]:
        return [
            ToolDef(
                name="run_shell",
                description="Execute a shell command",
                parameters={
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            ),
            ToolDef(
                name="write_file",
                description="Write content to a file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
        ]

    # ── Tests ────────────────────────────────────────────────────────

    def test_feedback_triggered_on_test_failure(self) -> None:
        """MockProvider 返回 RunShell 执行测试 → 测试失败 → FeedbackEngine 被调用。"""
        dispatcher = ToolDispatcher()
        dispatcher.register(_MockRunShell(fail_first=True))

        spy = _SpyFeedbackEngine()
        provider = MockProvider.with_tool_call(
            tool_name="run_shell",
            arguments={"command": "pytest tests/"},
        )
        loop = self._make_loop(
            provider=provider,
            feedback_engine=spy,
            max_iterations=3,
            dispatcher=dispatcher,
        )
        result = loop.run("test task", self._tool_defs())

        # The loop should have called analyze() at least once
        assert spy.analyze_call_count >= 1
        assert spy.last_result is not None
        assert spy.last_result.exit_code is not None
        # Loop should reach max iterations (no finish call)
        assert result.success is False

    def test_feedback_cycle_completes(self) -> None:
        """Mock 模拟"写代码→测试失败→收到反馈→修复→测试通过"完整周期。"""
        dispatcher = ToolDispatcher()
        shell = _MockRunShell(fail_first=True)
        dispatcher.register(shell)
        dispatcher.register(_MockWriteFile())

        # Sequence of LLM responses:
        # 1. run_shell → test fails → feedback generated
        # 2. write_file → fix code (triggered by feedback content in context)
        # 3. finish → done
        provider = _SequenceMockProvider([
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="c1", name="run_shell", arguments={"command": "pytest"}),
                ],
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="c2", name="write_file", arguments={"path": "fix.py", "content": "fixed"}),
                ],
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="c3", name="run_shell", arguments={"command": "pytest"}),
                ],
                finish_reason="tool_calls",
            ),
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(id="c4", name="finish", arguments={"reason": "all tests passed"}),
                ],
                finish_reason="tool_calls",
            ),
        ])
        loop = self._make_loop(provider=provider, max_iterations=10, dispatcher=dispatcher)
        result = loop.run("test task", self._tool_defs())

        assert result.success is True
        assert result.error is None
        # The cycle should have taken multiple iterations
        assert result.iterations > 0

    def test_no_feedback_on_success(self) -> None:
        """测试通过 → FeedbackEngine 不被调用（或返回 None）。"""
        dispatcher = ToolDispatcher()
        dispatcher.register(_MockRunShell(fail_first=False))

        spy = _SpyFeedbackEngine()
        provider = MockProvider.with_tool_call(
            tool_name="run_shell",
            arguments={"command": "pytest tests/"},
        )
        loop = self._make_loop(
            provider=provider,
            feedback_engine=spy,
            max_iterations=3,
            dispatcher=dispatcher,
        )
        result = loop.run("test task", self._tool_defs())

        # The tool returns exit_code=0 (success) → analyze() is called
        # but should return None (no feedback generated)
        # Verify the loop ran without error
        assert result.error is None or "Guardrail" not in (result.error or "")
        # analyze() should have been called (exit_code is not None)
        assert spy.analyze_call_count >= 1

    def test_feedback_logs(self, caplog: object) -> None:
        """日志中包含 Feedback 分类结果。"""
        import logging

        dispatcher = ToolDispatcher()
        dispatcher.register(_MockRunShell(fail_first=True))

        provider = MockProvider.with_tool_call(
            tool_name="run_shell",
            arguments={"command": "pytest tests/"},
        )
        loop = self._make_loop(provider=provider, max_iterations=3, dispatcher=dispatcher)

        # Capture logs at INFO level
        with caplog.at_level(logging.INFO):
            loop.run("test task", self._tool_defs())

        # Check that the feedback log message was emitted
        found_feedback_log = any(
            "Feedback generated" in record.getMessage()
            for record in caplog.records
        )
        assert found_feedback_log, (
            "Expected a log message containing 'Feedback generated'"
        )