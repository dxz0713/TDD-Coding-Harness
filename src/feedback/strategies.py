"""Repair strategies for each FailureType (T17).

Each concrete ``RepairStrategy`` produces a targeted repair prompt based
on the structured ``AnalysisResult`` from the ``FailureAnalyzer``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness.models import AnalysisResult


# ═══════════════════════════════════════════════════════════════════
# Abstract base
# ═══════════════════════════════════════════════════════════════════


class RepairStrategy(ABC):
    """Base class for all repair strategies."""

    @abstractmethod
    def generate(self, analysis: AnalysisResult) -> str:
        """Generate a repair prompt for the given analysis.

        Args:
            analysis: Structured analysis from the ``FailureAnalyzer``.

        Returns:
            A repair prompt string that will be fed back to the LLM.
        """
        ...


# ═══════════════════════════════════════════════════════════════════
# Concrete strategies (one per FailureType)
# ═══════════════════════════════════════════════════════════════════


class SyntaxStrategy(RepairStrategy):
    """Repair strategy for ``SYNTAX_ERROR`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        location = analysis.location or "unknown"
        return (
            f"SyntaxError at {location}: {analysis.error_message}. "
            f"Fix the syntax."
        )


class ImportStrategy(RepairStrategy):
    """Repair strategy for ``IMPORT_ERROR`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        return (
            f"ImportError: {analysis.error_message}. "
            f"Install missing module or fix import path."
        )


class AssertionStrategy(RepairStrategy):
    """Repair strategy for ``ASSERTION_ERROR`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        expected = analysis.assertion_expected or "?"
        actual = analysis.assertion_actual or "?"
        return (
            f"AssertionError: expected {expected} but got {actual}. "
            f"Fix the logic."
        )


class TimeoutStrategy(RepairStrategy):
    """Repair strategy for ``TIMEOUT`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        return (
            f"Timeout: {analysis.error_message}. "
            f"Optimize algorithm or increase timeout."
        )


class RuntimeErrorStrategy(RepairStrategy):
    """Repair strategy for ``RUNTIME_ERROR`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        location = analysis.location or "unknown"
        return (
            f"RuntimeError at {location}: {analysis.error_message}. "
            f"Fix the error."
        )


class TestFailureStrategy(RepairStrategy):
    """Repair strategy for ``TEST_FAILURE`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        return (
            f"Test failure: {analysis.error_message}. "
            f"Review and fix the test or implementation."
        )


class UnknownStrategy(RepairStrategy):
    """Repair strategy for ``UNKNOWN`` failures."""

    def generate(self, analysis: AnalysisResult) -> str:
        return (
            "Unknown failure. Review the output and improve the code."
        )