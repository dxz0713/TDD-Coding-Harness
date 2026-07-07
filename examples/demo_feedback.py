"""Demonstrate: Feedback Engine classifies failure types.

Usage:
    D:\\Python3.12\\python.exe examples/demo_feedback.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from feedback.engine import FeedbackEngine
from harness.models import FailureType, ToolResult


def main() -> None:
    """Run the feedback demonstration."""
    engine = FeedbackEngine()

    # ── SyntaxError ──────────────────────────────────────────────────
    result = ToolResult(
        success=False,
        exit_code=1,
        output="",
        error="SyntaxError: invalid syntax",
    )
    feedback = engine.analyze(result)
    assert feedback is not None
    assert feedback.failure_type == FailureType.SYNTAX_ERROR
    print(f"[{feedback.failure_type.value}] {feedback.repair_prompt}")

    # ── AssertionError ───────────────────────────────────────────────
    result = ToolResult(
        success=False,
        exit_code=1,
        output="AssertionError: assert 42 == 0",
        error="AssertionError: assert 42 == 0",
    )
    feedback = engine.analyze(result)
    assert feedback is not None
    assert feedback.failure_type == FailureType.ASSERTION_ERROR
    print(f"[{feedback.failure_type.value}] {feedback.repair_prompt}")

    # ── Successful run (no feedback) ─────────────────────────────────
    result = ToolResult(success=True, exit_code=0, output="All tests passed!")
    feedback = engine.analyze(result)
    assert feedback is None
    print("[SUCCESS] No feedback generated for passing tests")

    print()
    print("[PASS] Feedback demo passed")


if __name__ == "__main__":
    main()