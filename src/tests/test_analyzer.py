"""Tests for Collector and FailureAnalyzer (T16).

Covers:
- Collector: stdout extraction, ANSI stripping, failed test name extraction.
- FailureAnalyzer: all 7 FailureType classifications.
"""

from __future__ import annotations

from harness.models import FailureType, ToolResult
from feedback.analyzer import CollectedOutput, Collector, FailureAnalyzer


# ═══════════════════════════════════════════════════════════════════
# Collector
# ═══════════════════════════════════════════════════════════════════


class TestCollector:
    """Collector extracts and normalises raw output from a ToolResult."""

    def test_extracts_stdout(self) -> None:
        """从 ToolResult 提取 stdout。"""
        result = ToolResult(success=True, output="hello world", exit_code=0)
        collected = Collector.collect(result)
        assert collected.stdout == "hello world"
        assert collected.stderr == ""
        assert collected.exit_code == 0

    def test_strips_ansi(self) -> None:
        """含 ANSI 转义的输出 → 去除转义。"""
        ansi_text = "\x1B[32mPASSED\x1B[0m \x1B[31mFAILED\x1B[0m"
        result = ToolResult(success=False, output=ansi_text, exit_code=1)
        collected = Collector.collect(result)
        assert "\x1B[" not in collected.stdout
        assert "PASSED" in collected.stdout
        assert "FAILED" in collected.stdout

    def test_extracts_failed_tests(self) -> None:
        """pytest 输出 → 提取 FAILED 测试名称。"""
        output = (
            "tests/test_demo.py::test_hello PASSED\n"
            "tests/test_demo.py::test_fibonacci FAILED\n"
            "tests/test_demo.py::test_parse FAILED\n"
        )
        result = ToolResult(success=False, output=output, exit_code=1)
        collected = Collector.collect(result)
        assert "test_fibonacci" in collected.failed_tests
        assert "test_parse" in collected.failed_tests
        assert "test_hello" not in collected.failed_tests

    def test_empty_result(self) -> None:
        """空 ToolResult → 空 CollectedOutput。"""
        result = ToolResult(success=True)
        collected = Collector.collect(result)
        assert collected.stdout == ""
        assert collected.stderr == ""
        assert collected.exit_code is None
        assert collected.failed_tests == []

    def test_stderr_extraction(self) -> None:
        """从 ToolResult 的 error 字段提取 stderr。"""
        result = ToolResult(success=False, output="", error="runtime error", exit_code=1)
        collected = Collector.collect(result)
        assert collected.stderr == "runtime error"

    def test_ansi_in_stderr(self) -> None:
        """stderr 中的 ANSI 也被去除。"""
        result = ToolResult(success=False, output="", error="\x1B[31mERROR\x1B[0m", exit_code=1)
        collected = Collector.collect(result)
        assert "\x1B[" not in collected.stderr
        assert "ERROR" in collected.stderr


# ═══════════════════════════════════════════════════════════════════
# FailureAnalyzer
# ═══════════════════════════════════════════════════════════════════


class TestFailureAnalyzer:
    """FailureAnalyzer classifies test failures from collected output."""

    # ── Fixtures ────────────────────────────────────────────────────

    @staticmethod
    def _collect(text: str, exit_code: int = 1) -> CollectedOutput:
        return CollectedOutput(stdout=text, exit_code=exit_code)

    # ── SYNTAX_ERROR ────────────────────────────────────────────────

    def test_syntax_error(self) -> None:
        """注入 SyntaxError 输出 → FailureType.SYNTAX_ERROR。"""
        output = (
            '  File "test.py", line 1\n'
            "    x = 1 +\n"
            "           ^\n"
            "SyntaxError: invalid syntax\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.SYNTAX_ERROR
        assert "SyntaxError" in result.error_message

    def test_syntax_error_simple(self) -> None:
        """简单的 SyntaxError 文本 → SYNTAX_ERROR。"""
        collected = self._collect("SyntaxError: invalid syntax")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.SYNTAX_ERROR

    # ── IMPORT_ERROR ────────────────────────────────────────────────

    def test_import_error(self) -> None:
        """注入 ImportError 输出 → FailureType.IMPORT_ERROR。"""
        output = (
            "Traceback (most recent call last):\n"
            '  File "test.py", line 1, in <module>\n'
            "    import nonexistent_module\n"
            "ModuleNotFoundError: No module named 'nonexistent_module'\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.IMPORT_ERROR
        assert "Error" in result.error_message

    def test_import_error_direct(self) -> None:
        """ImportError 文本 → IMPORT_ERROR。"""
        collected = self._collect("ImportError: cannot import name 'X'")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.IMPORT_ERROR

    # ── ASSERTION_ERROR ─────────────────────────────────────────────

    def test_assertion_error(self) -> None:
        """注入 AssertionError → 分类正确 + 提取预期/实际值。"""
        output = (
            ">       assert result == 42\n"
            "E       AssertionError\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.ASSERTION_ERROR
        assert "AssertionError" in result.error_message

    def test_assertion_error_with_values(self) -> None:
        """断言错误含 expected/actual 提取。"""
        output = "assert 1 == 2\n"
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.ASSERTION_ERROR
        # Should have extracted expected/actual values
        assert result.assertion_expected is not None or result.assertion_actual is not None

    # ── TIMEOUT ─────────────────────────────────────────────────────

    def test_timeout(self) -> None:
        """注入超时输出 → FailureType.TIMEOUT。"""
        output = "Timeout: command exceeded 30 seconds"
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.TIMEOUT

    def test_timeout_lowercase(self) -> None:
        """小写 timeout 关键词 → TIMEOUT。"""
        collected = self._collect("timed out after 30s")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.TIMEOUT

    # ── RUNTIME_ERROR ───────────────────────────────────────────────

    def test_runtime_error(self) -> None:
        """注入运行时异常 → FailureType.RUNTIME_ERROR。"""
        output = (
            "Traceback (most recent call last):\n"
            '  File "test.py", line 5, in my_func\n'
            "    return 1 / 0\n"
            "ZeroDivisionError: division by zero\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.RUNTIME_ERROR

    def test_runtime_error_generic(self) -> None:
        """通用 Error: 前缀 → RUNTIME_ERROR。"""
        collected = self._collect("ValueError: invalid value")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.RUNTIME_ERROR

    # ── TEST_FAILURE ────────────────────────────────────────────────

    def test_test_failure(self) -> None:
        """注入测试失败 → FailureType.TEST_FAILURE。"""
        output = "FAILED tests/test_demo.py::test_fibonacci - AssertionError"
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.TEST_FAILURE

    # ── UNKNOWN ─────────────────────────────────────────────────────

    def test_unknown(self) -> None:
        """无关输出 → FailureType.UNKNOWN。"""
        collected = self._collect("Everything looks good!")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.UNKNOWN

    def test_unknown_empty_output(self) -> None:
        """空输出 → UNKNOWN。"""
        collected = self._collect("")
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.UNKNOWN

    # ── Priority order ──────────────────────────────────────────────

    def test_syntax_error_takes_priority(self) -> None:
        """SyntaxError 出现在其他 Error 前 → 优先识别为 SYNTAX_ERROR。"""
        output = (
            "SyntaxError: invalid syntax\n"
            "ImportError: cannot import\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.SYNTAX_ERROR

    def test_import_error_before_runtime(self) -> None:
        """ImportError 出现在 Traceback 前 → IMPORT_ERROR。"""
        output = (
            "ImportError: no module\n"
            "Traceback (most recent call last):\n"
        )
        collected = self._collect(output)
        analyzer = FailureAnalyzer()
        result = analyzer.analyze(collected)
        assert result.failure_type == FailureType.IMPORT_ERROR