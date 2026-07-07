"""FeedbackEngine — complete feedback loop (T17).

Connects Collector → FailureAnalyzer → RepairStrategy to produce
structured ``Feedback`` for failed test results.
"""

from __future__ import annotations

from feedback.analyzer import Collector, FailureAnalyzer
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
from harness.models import AnalysisResult, FailureType, Feedback, ToolResult


class FeedbackEngine:
    """Complete feedback engine connecting Collector → Analyzer → Strategy.

    Usage::

        engine = FeedbackEngine()
        feedback = engine.analyze(tool_result)   # Feedback | None
    """

    def __init__(self, analyzer: FailureAnalyzer | None = None) -> None:
        """Initialize with default strategies mapped to all FailureTypes.

        Args:
            analyzer: Optional ``FailureAnalyzer`` instance. Defaults to a
                      fresh ``FailureAnalyzer()``.
        """
        self._analyzer = analyzer or FailureAnalyzer()
        self._strategies: dict[FailureType, RepairStrategy] = {
            FailureType.SYNTAX_ERROR: SyntaxStrategy(),
            FailureType.IMPORT_ERROR: ImportStrategy(),
            FailureType.ASSERTION_ERROR: AssertionStrategy(),
            FailureType.TIMEOUT: TimeoutStrategy(),
            FailureType.RUNTIME_ERROR: RuntimeErrorStrategy(),
            FailureType.TEST_FAILURE: TestFailureStrategy(),
            FailureType.UNKNOWN: UnknownStrategy(),
        }

    def analyze(self, result: ToolResult) -> Feedback | None:
        """Analyze a tool result and produce feedback if there was a failure.

        Args:
            result: The ``ToolResult`` from a test execution.

        Returns:
            ``Feedback`` if a failure was detected, ``None`` if the result
            was successful (exit_code == 0).
        """
        collected = Collector.collect(result)
        analysis = self._analyzer.analyze(collected)

        # Successful run → no feedback needed
        if analysis.failure_type == FailureType.UNKNOWN and result.success:
            return None

        strategy = self._strategies[analysis.failure_type]
        prompt = strategy.generate(analysis)

        return Feedback(
            failure_type=analysis.failure_type,
            summary=f"{analysis.failure_type.value}: {analysis.error_message}",
            details=analysis,
            repair_prompt=prompt,
        )