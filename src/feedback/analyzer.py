"""Collector and FailureAnalyzer for test-output processing (T16).

Collector
    Extracts and normalises raw output from a ToolResult (strips ANSI,
    identifies failed test names).

FailureAnalyzer
    Classifies test-failure output into one of seven FailureType values
    using regex/pattern matching on pytest stdout/stderr.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from harness.models import AnalysisResult, FailureType, ToolResult


# ═══════════════════════════════════════════════════════════════════
# CollectedOutput
# ═══════════════════════════════════════════════════════════════════


class CollectedOutput(BaseModel):
    """Normalised output ready for analysis."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    failed_tests: list[str] = []  # e.g. ["test_fibonacci"]


# ═══════════════════════════════════════════════════════════════════
# Collector
# ═══════════════════════════════════════════════════════════════════

# ANSI escape sequence pattern
_ANSI_RE: re.Pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Pattern to extract FAILED test names from pytest output
# Matches lines like:
#   tests/test_demo.py::test_fibonacci FAILED
#   FAILED tests/test_demo.py::test_fibonacci - ...
_FAILED_TEST_RE: re.Pattern = re.compile(
    r"(?:\S+::(\w+)\s+FAILED|FAILED\s+\S+::(\w+))",
)


class Collector:
    """Collects and normalises raw output from a ToolResult."""

    @staticmethod
    def collect(result: ToolResult) -> CollectedOutput:
        """Extract and normalise stdout/stderr from a tool result.

        - Strips ANSI escape sequences
        - Extracts key lines (failed test names, error locations)

        Args:
            result: The raw ``ToolResult`` from a tool execution.

        Returns:
            A ``CollectedOutput`` with cleaned text and parsed metadata.
        """
        stdout: str = result.output or ""
        stderr: str = result.error or ""

        # Strip ANSI
        stdout = Collector._strip_ansi(stdout)
        stderr = Collector._strip_ansi(stderr)

        # Extract failed test names from combined output
        combined: str = stdout + "\n" + stderr
        matches: list[tuple[str, str]] = _FAILED_TEST_RE.findall(combined)
        failed_tests: list[str] = [g1 or g2 for g1, g2 in matches]

        return CollectedOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=result.exit_code,
            failed_tests=failed_tests,
        )

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape sequences from *text*."""
        return _ANSI_RE.sub("", text)


# ═══════════════════════════════════════════════════════════════════
# FailureAnalyzer
# ═══════════════════════════════════════════════════════════════════

# Regex patterns for each failure type (checked in priority order)
_SYNTAX_ERROR_RE: re.Pattern = re.compile(
    r"(?:SyntaxError|SyntaxError:\s+invalid\s+syntax)",
)
_IMPORT_ERROR_RE: re.Pattern = re.compile(
    r"(?:ModuleNotFoundError|ImportError)\s*:",
)
_ASSERTION_ERROR_RE: re.Pattern = re.compile(
    r"(?:AssertionError|assert\s.+?\s+failed|assert\s+.+?\s+==\s+.+)",
)
_TIMEOUT_RE: re.Pattern = re.compile(
    r"\b(?:Timeout|timed?\s*out|timeout)\b",
    re.IGNORECASE,
)
_RUNTIME_ERROR_RE: re.Pattern = re.compile(
    r"(?:Traceback|Error:|Exception:)",
)
_TEST_FAILURE_RE: re.Pattern = re.compile(
    r"\bFAILED\b|\bfailed\b",
)

# Pattern to extract assertion expected vs actual
# Matches pytest assertion rewriting output:
#   assert 1 == 2
#   +  where 1 = actual_value
#   -  where 2 = expected_value
_ASSERT_EXPECTED_RE: re.Pattern = re.compile(
    r"assert\s+(.+?)\s+==\s+(.+)",
)
_ASSERT_WHERE_RE: re.Pattern = re.compile(
    r"(?:\+|-) where (.+?) = (.+)",
)


class FailureAnalyzer:
    """Classifies test failures by parsing pytest output."""

    def analyze(self, collected: CollectedOutput) -> AnalysisResult:
        """Determine the failure type from collected output.

        Uses regex/pattern matching on pytest stdout/stderr to classify:

        - SYNTAX_ERROR: Python syntax errors
        - IMPORT_ERROR: Import errors
        - ASSERTION_ERROR: Assertion failures (extract expected/actual)
        - TIMEOUT: Execution timeout
        - RUNTIME_ERROR: Other runtime exceptions
        - TEST_FAILURE: General test failure (unclassified)
        - UNKNOWN: Cannot classify

        Args:
            collected: The normalised output from the ``Collector``.

        Returns:
            An ``AnalysisResult`` with the determined failure type and
            any extracted details.
        """
        combined: str = f"{collected.stdout}\n{collected.stderr}"

        # ── SYNTAX_ERROR ──────────────────────────────────────────
        if _SYNTAX_ERROR_RE.search(combined):
            return AnalysisResult(
                failure_type=FailureType.SYNTAX_ERROR,
                error_message=self._extract_snippet(combined, "SyntaxError"),
                raw_snippet=self._extract_snippet(combined, "SyntaxError"),
            )

        # ── IMPORT_ERROR ──────────────────────────────────────────
        if _IMPORT_ERROR_RE.search(combined):
            return AnalysisResult(
                failure_type=FailureType.IMPORT_ERROR,
                error_message=self._extract_snippet(combined, "Error"),
                raw_snippet=self._extract_snippet(combined, "Error"),
            )

        # ── TIMEOUT ───────────────────────────────────────────────
        if _TIMEOUT_RE.search(combined):
            return AnalysisResult(
                failure_type=FailureType.TIMEOUT,
                error_message=self._extract_snippet(combined, "timeout", max_len=120),
                raw_snippet=self._extract_snippet(combined, "timeout", max_len=120),
            )

        # ── TEST_FAILURE (pytest summary lines) ───────────────────
        # Check BEFORE AssertionError/RuntimeError because pytest
        # summary lines (e.g. "FAILED test.py::test_foo - AssertionError")
        # should be classified as TEST_FAILURE, not the underlying error.
        if _TEST_FAILURE_RE.search(combined):
            failed: str = ", ".join(collected.failed_tests) if collected.failed_tests else "unknown"
            return AnalysisResult(
                failure_type=FailureType.TEST_FAILURE,
                location=failed,
                error_message=f"Test(s) failed: {failed}",
                raw_snippet=self._extract_snippet(combined, "FAILED", max_len=200),
            )

        # ── ASSERTION_ERROR ───────────────────────────────────────
        assertion_match = _ASSERTION_ERROR_RE.search(combined)
        if assertion_match:
            expected, actual = self._extract_assert_values(combined)
            # Prefer "AssertionError" as the error message over
            # "assert X == Y" (both match the combined pattern).
            error_msg: str = assertion_match.group()
            if "AssertionError" in combined:
                error_msg = "AssertionError"
            return AnalysisResult(
                failure_type=FailureType.ASSERTION_ERROR,
                error_message=error_msg,
                assertion_expected=expected,
                assertion_actual=actual,
                raw_snippet=self._extract_snippet(combined, "assert"),
            )

        # ── RUNTIME_ERROR ─────────────────────────────────────────
        if _RUNTIME_ERROR_RE.search(combined):
            return AnalysisResult(
                failure_type=FailureType.RUNTIME_ERROR,
                error_message=self._extract_snippet(combined, "Error"),
                raw_snippet=self._extract_snippet(combined, "Traceback"),
            )

        # ── UNKNOWN ───────────────────────────────────────────────
        return AnalysisResult(
            failure_type=FailureType.UNKNOWN,
            error_message="",
        )

    # ── Internal helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_snippet(
        text: str,
        keyword: str,
        max_len: int = 200,
    ) -> str:
        """Extract a snippet of text around *keyword*."""
        idx = text.find(keyword)
        if idx == -1:
            return ""
        start = max(0, idx - 20)
        end = min(len(text), idx + max_len)
        snippet = text[start:end].strip()
        return snippet[:max_len]

    @staticmethod
    def _extract_assert_values(text: str) -> tuple[str | None, str | None]:
        """Extract expected and actual values from assertion output.

        Returns:
            A tuple ``(expected, actual)``.
        """
        expected: str | None = None
        actual: str | None = None

        # Try pytest assertion rewriting:  "assert actual == expected"
        match = _ASSERT_EXPECTED_RE.search(text)
        if match:
            actual = match.group(1).strip()
            expected = match.group(2).strip()

        # Try :"where" lines for more detail
        # "+ where 1 = actual_value"  (actual)
        # "- where 2 = expected_value" (expected)
        for where_match in _ASSERT_WHERE_RE.finditer(text):
            prefix: str = where_match.group(1).strip()
            value: str = where_match.group(2).strip()
            if prefix and value:
                expected = value  # last "where" value wins

        return expected, actual