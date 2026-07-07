"""Tests for AutonomousStopDecision (T13).

Covers all four stop conditions: max iterations, Finish tool call
(success/failure), guardrail blocked, and not stopping when no
condition is met.
"""

from __future__ import annotations

from harness.config import GuardrailConfig, LoopConfig
from harness.guardrail import Guardrail
from harness.models import Context, Message, ToolCall
from harness.stop_condition import AutonomousStopDecision


class TestAutonomousStopDecision:
    """AutonomousStopDecision evaluates four stop conditions."""

    # ── Fixtures ────────────────────────────────────────────────────

    @staticmethod
    def _make_decision(
        max_iterations: int = 5,
        guardrail_enabled: bool = True,
    ) -> AutonomousStopDecision:
        config = LoopConfig(max_iterations=max_iterations)
        guardrail = Guardrail(GuardrailConfig(enabled=guardrail_enabled))
        return AutonomousStopDecision(guardrail=guardrail, config=config)

    # ── Max iterations ──────────────────────────────────────────────

    def test_max_iterations(self) -> None:
        """iteration >= max_iterations → should_stop=True."""
        decision = self._make_decision(max_iterations=3)
        ctx = Context(
            messages=[Message(role="system", content="test")],
            iteration=3,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is True
        assert result.success is False
        assert "Max iterations" in result.reason

    def test_max_iterations_exceeded(self) -> None:
        """iteration > max_iterations → should_stop=True."""
        decision = self._make_decision(max_iterations=3)
        ctx = Context(
            messages=[Message(role="system", content="test")],
            iteration=5,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is True

    def test_below_max_iterations(self) -> None:
        """iteration < max_iterations → 不因此停机。"""
        decision = self._make_decision(max_iterations=5)
        ctx = Context(
            messages=[Message(role="system", content="test")],
            iteration=2,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is False

    # ── Finish success ──────────────────────────────────────────────

    def test_finish_success(self) -> None:
        """Finish reason="tests passed" → should_stop=True, success=True."""
        decision = self._make_decision()
        call = ToolCall(
            id="finish_1",
            name="Finish",
            arguments={"reason": "All tests passed successfully"},
        )
        result = decision.on_finish(call)
        assert result.should_stop is True
        assert result.success is True

    def test_finish_success_complete(self) -> None:
        """Finish reason="implementation complete" → success=True."""
        decision = self._make_decision()
        call = ToolCall(
            id="finish_2",
            name="Finish",
            arguments={"reason": "Implementation complete"},
        )
        result = decision.on_finish(call)
        assert result.should_stop is True
        assert result.success is True

    # ── Finish failure ──────────────────────────────────────────────

    def test_finish_failure(self) -> None:
        """Finish reason="unable to complete" → should_stop=True, success=False."""
        decision = self._make_decision()
        call = ToolCall(
            id="finish_3",
            name="Finish",
            arguments={"reason": "unable to complete due to dependency issues"},
        )
        result = decision.on_finish(call)
        assert result.should_stop is True
        assert result.success is False

    def test_finish_empty_reason(self) -> None:
        """Finish 无 reason → should_stop=True, success=False."""
        decision = self._make_decision()
        call = ToolCall(
            id="finish_4",
            name="Finish",
            arguments={},
        )
        result = decision.on_finish(call)
        assert result.should_stop is True
        assert result.success is False
        assert "LLM returned Finish" in result.reason

    # ── Not stopping ────────────────────────────────────────────────

    def test_not_stopping(self) -> None:
        """未达到任何停机条件 → should_stop=False."""
        decision = self._make_decision(max_iterations=10)
        ctx = Context(
            messages=[Message(role="system", content="test")],
            iteration=1,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is False

    # ── Guardrail blocked ───────────────────────────────────────────

    def test_with_guardrail_blocked(self) -> None:
        """Guardrail 已拦截 → should_stop=True."""
        decision = self._make_decision()
        call = ToolCall(
            id="call_1",
            name="run_shell",
            arguments={"command": "rm -rf /"},
        )
        result = decision.check_guardrail(call)
        assert result is not None
        assert result.should_stop is True
        assert result.success is False
        assert "Guardrail blocked" in result.reason

    def test_guardrail_allows_safe(self) -> None:
        """Guardrail 放行 → check_guardrail 返回 None。"""
        decision = self._make_decision()
        call = ToolCall(
            id="call_2",
            name="run_shell",
            arguments={"command": "pytest tests/"},
        )
        result = decision.check_guardrail(call)
        assert result is None

    def test_guardrail_non_shell(self) -> None:
        """非 shell 工具 → check_guardrail 返回 None。"""
        decision = self._make_decision()
        call = ToolCall(
            id="call_3",
            name="read_file",
            arguments={"path": "test.txt"},
        )
        result = decision.check_guardrail(call)
        assert result is None

    # ── All tests passed (via tool result) ─────────────────────────

    def test_stop_on_all_tests_passed(self) -> None:
        """工具结果含 'all tests passed' → should_stop=True, success=True."""
        decision = self._make_decision(max_iterations=10)
        ctx = Context(
            messages=[
                Message(role="system", content="test"),
                Message(role="tool", content="All tests passed! 100% coverage", tool_call_id="c1"),
            ],
            iteration=1,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is True
        assert result.success is True
        assert "All tests passed" in result.reason

    def test_stop_on_passed_with_all(self) -> None:
        """工具结果含 'all' 和 'passed' → should_stop=True."""
        decision = self._make_decision(max_iterations=10)
        ctx = Context(
            messages=[
                Message(role="system", content="test"),
                Message(role="tool", content="all 10 tests passed", tool_call_id="c1"),
            ],
            iteration=1,
            task="test",
        )
        result = decision.should_stop(ctx)
        assert result.should_stop is True
        assert result.success is True