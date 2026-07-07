"""Tests for FeedbackEngine and RepairStrategies (T17).

Covers:
- All 7 concrete RepairStrategy classes.
- FeedbackEngine: success → None, failure → Feedback with correct type.
"""

from __future__ import annotations

from feedback.engine import FeedbackEngine
from feedback.strategies import (
    AssertionStrategy,
    ImportStrategy,
    RepairStrategy,
    RuntimeErrorStrategy,
    SyntaxStrategy,
    TestFailureStrategy,
    TimeoutStrategy,
    UnknownStrategy,
)
from harness.models import AnalysisResult, FailureType, ToolResult


# ═══════════════════════════════════════════════════════════════════
# RepairStrategies
# ═══════════════════════════════════════════════════════════════════


class TestRepairStrategies:
    """Each concrete RepairStrategy produces a correct prompt."""

    def test_syntax_strategy(self) -> None:
        """SyntaxStrategy 生成的 prompt 包含 'SyntaxError' 和错误位置。"""
        analysis = AnalysisResult(
            failure_type=FailureType.SYNTAX_ERROR,
            location="test.py:1",
            error_message="invalid syntax",
        )
        strategy: RepairStrategy = SyntaxStrategy()
        prompt = strategy.generate(analysis)
        assert "SyntaxError" in prompt
        assert "test.py:1" in prompt

    def test_import_strategy(self) -> None:
        """ImportStrategy 生成的 prompt 包含 'ImportError'。"""
        analysis = AnalysisResult(
            failure_type=FailureType.IMPORT_ERROR,
            error_message="No module named 'foo'",
        )
        strategy: RepairStrategy = ImportStrategy()
        prompt = strategy.generate(analysis)
        assert "ImportError" in prompt
        assert "foo" in prompt

    def test_assertion_strategy_contains_values(self) -> None:
        """AssertionStrategy 生成的 prompt 包含预期值和实际值。"""
        analysis = AnalysisResult(
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="AssertionError",
            assertion_expected="42",
            assertion_actual="0",
        )
        strategy: RepairStrategy = AssertionStrategy()
        prompt = strategy.generate(analysis)
        assert "expected 42" in prompt
        assert "got 0" in prompt

    def test_assertion_strategy_missing_values(self) -> None:
        """AssertionStrategy 在缺少预期/实际值时代替为 '?'。"""
        analysis = AnalysisResult(
            failure_type=FailureType.ASSERTION_ERROR,
            error_message="AssertionError",
        )
        strategy: RepairStrategy = AssertionStrategy()
        prompt = strategy.generate(analysis)
        assert "expected ?" in prompt
        assert "got ?" in prompt

    def test_timeout_strategy(self) -> None:
        """TimeoutStrategy 生成的 prompt 包含 'Timeout'。"""
        analysis = AnalysisResult(
            failure_type=FailureType.TIMEOUT,
            error_message="command exceeded 30 seconds",
        )
        strategy: RepairStrategy = TimeoutStrategy()
        prompt = strategy.generate(analysis)
        assert "Timeout" in prompt

    def test_runtime_error_strategy(self) -> None:
        """RuntimeErrorStrategy 生成的 prompt 包含 'RuntimeError' 和位置。"""
        analysis = AnalysisResult(
            failure_type=FailureType.RUNTIME_ERROR,
            location="my_func:5",
            error_message="division by zero",
        )
        strategy: RepairStrategy = RuntimeErrorStrategy()
        prompt = strategy.generate(analysis)
        assert "RuntimeError" in prompt
        assert "my_func:5" in prompt

    def test_test_failure_strategy(self) -> None:
        """TestFailureStrategy 生成的 prompt 包含 'Test failure'。"""
        analysis = AnalysisResult(
            failure_type=FailureType.TEST_FAILURE,
            location="test_foo",
            error_message="Test(s) failed: test_foo",
        )
        strategy: RepairStrategy = TestFailureStrategy()
        prompt = strategy.generate(analysis)
        assert "Test failure" in prompt
        assert "test_foo" in prompt

    def test_unknown_strategy(self) -> None:
        """UnknownStrategy 生成通用修复提示。"""
        analysis = AnalysisResult(failure_type=FailureType.UNKNOWN)
        strategy: RepairStrategy = UnknownStrategy()
        prompt = strategy.generate(analysis)
        assert "Unknown failure" in prompt

    def test_all_strategies_produce_different_prompts(self) -> None:
        """不同 FailureType 产生不同的 repair_prompt。"""
        strategies: list[tuple[FailureType, RepairStrategy, AnalysisResult]] = [
            (
                FailureType.SYNTAX_ERROR,
                SyntaxStrategy(),
                AnalysisResult(
                    failure_type=FailureType.SYNTAX_ERROR,
                    error_message="err",
                ),
            ),
            (
                FailureType.IMPORT_ERROR,
                ImportStrategy(),
                AnalysisResult(
                    failure_type=FailureType.IMPORT_ERROR,
                    error_message="err",
                ),
            ),
            (
                FailureType.ASSERTION_ERROR,
                AssertionStrategy(),
                AnalysisResult(
                    failure_type=FailureType.ASSERTION_ERROR,
                    error_message="err",
                    assertion_expected="1",
                    assertion_actual="2",
                ),
            ),
            (
                FailureType.TIMEOUT,
                TimeoutStrategy(),
                AnalysisResult(
                    failure_type=FailureType.TIMEOUT,
                    error_message="err",
                ),
            ),
            (
                FailureType.RUNTIME_ERROR,
                RuntimeErrorStrategy(),
                AnalysisResult(
                    failure_type=FailureType.RUNTIME_ERROR,
                    error_message="err",
                ),
            ),
            (
                FailureType.TEST_FAILURE,
                TestFailureStrategy(),
                AnalysisResult(
                    failure_type=FailureType.TEST_FAILURE,
                    error_message="err",
                ),
            ),
            (
                FailureType.UNKNOWN,
                UnknownStrategy(),
                AnalysisResult(failure_type=FailureType.UNKNOWN),
            ),
        ]

        prompts = [s.generate(a) for _, s, a in strategies]
        # All prompts should be unique
        assert len(prompts) == len(set(prompts)), (
            f"Expected 7 unique prompts, got {len(set(prompts))}"
        )


# ═══════════════════════════════════════════════════════════════════
# FeedbackEngine
# ═══════════════════════════════════════════════════════════════════


class TestFeedbackEngine:
    """FeedbackEngine connects Collector → Analyzer → Strategy."""

    def test_success_result_returns_none(self) -> None:
        """exit_code=0 的 ToolResult → analyze() 返回 None。"""
        result = ToolResult(success=True, output="All tests passed!", exit_code=0)
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is None

    def test_failure_result_returns_feedback(self) -> None:
        """失败结果 → 返回 Feedback 对象。"""
        result = ToolResult(
            success=False,
            output="AssertionError: assert 1 == 2",
            exit_code=1,
        )
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is not None
        assert isinstance(feedback.failure_type, FailureType)

    def test_feedback_contains_repair_prompt(self) -> None:
        """Feedback 对象的 repair_prompt 字段非空。"""
        result = ToolResult(
            success=False,
            output="SyntaxError: invalid syntax",
            exit_code=1,
        )
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is not None
        assert feedback.repair_prompt != ""
        assert isinstance(feedback.repair_prompt, str)

    def test_feedback_type_matches_analysis(self) -> None:
        """Feedback 的 failure_type 与分析结果一致。"""
        result = ToolResult(
            success=False,
            output="Timeout: command exceeded 30 seconds",
            exit_code=1,
        )
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is not None
        assert feedback.failure_type == FailureType.TIMEOUT

    def test_feedback_has_summary(self) -> None:
        """Feedback 的 summary 字段包含 failure_type 和错误信息。"""
        result = ToolResult(
            success=False,
            output="ImportError: no module named 'xyz'",
            exit_code=1,
        )
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is not None
        assert "import_error" in feedback.summary

    def test_feedback_details_is_analysis_result(self) -> None:
        """Feedback 的 details 字段是 AnalysisResult 实例。"""
        result = ToolResult(
            success=False,
            output="RuntimeError: something broke",
            exit_code=1,
        )
        engine = FeedbackEngine()
        feedback = engine.analyze(result)
        assert feedback is not None
        assert isinstance(feedback.details, AnalysisResult)