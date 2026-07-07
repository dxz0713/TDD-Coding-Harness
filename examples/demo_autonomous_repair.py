"""Demonstrate: Full TDD cycle with autonomous repair using MockProvider.

Shows the complete "write code -> test fails -> feedback -> fix -> test passes"
cycle without a real LLM connection.

Usage:
    python examples/demo_autonomous_repair.py
"""

from __future__ import annotations

import sys
import os
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.config import Config, GuardrailConfig, LoopConfig
from harness.context import ContextManager
from harness.guardrail import Guardrail
from harness.loop import HarnessLoop
from harness.models import LLMResponse, ToolCall, ToolDef, ToolResult
from harness.stop_condition import AutonomousStopDecision
from providers.base import LLMProvider
from providers.mock import MockProvider
from feedback.engine import FeedbackEngine
from tools.base import BaseTool
from tools.dispatcher import ToolDispatcher


# ═══════════════════════════════════════════════════════════════════
# Mock tools
# ═══════════════════════════════════════════════════════════════════


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
        print(f"  [WRITE] {path} ({len(content)} bytes)")
        return ToolResult(success=True, output=f"Written {len(content)} bytes to {path}")


class _MockRunShell(BaseTool):
    """Simulated RunShell that fails on first call, passes on subsequent calls."""

    name = "run_shell"
    description = "Execute a shell command"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._call_count = 0

    def execute(self, command: str = "") -> ToolResult:
        self._call_count += 1
        if self._call_count == 1:
            print("  [TEST] Running tests... FAILED")
            return ToolResult(
                success=False,
                output="AssertionError: assert fib(5) == 5, got 0",
                error="Test failed: assert fib(5) == 5, got 0",
                exit_code=1,
            )
        print("  [TEST] Running tests... PASSED")
        return ToolResult(
            success=True,
            output="All tests passed! (3 passed)",
            exit_code=0,
        )


# ═══════════════════════════════════════════════════════════════════
# Sequence-based mock provider
# ═══════════════════════════════════════════════════════════════════


class _SequenceMockProvider(LLMProvider):
    """Returns responses in a fixed sequence, then repeats the last one."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self._index = 0

    def generate(
        self,
        messages: list,
        tools: list[ToolDef] | None = None,
        config: Any = None,
    ) -> LLMResponse:
        response = self._responses[self._index]
        self._index = min(self._index + 1, len(self._responses) - 1)
        return response


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════


def main() -> None:
    """Run the autonomous repair demonstration."""
    print("=" * 60)
    print("  TDD Coding Harness - Autonomous Repair Demo")
    print("=" * 60)
    print()

    # ── Register tools ───────────────────────────────────────────────
    dispatcher = ToolDispatcher()
    dispatcher.register(_MockWriteFile())
    dispatcher.register(_MockRunShell())

    # ── Sequence of LLM responses ────────────────────────────────────
    # 1. Write initial code
    # 2. Run tests → fails → FeedbackEngine generates repair prompt
    # 3. Fix code (prompted by feedback in context)
    # 4. Run tests → passes
    # 5. Finish
    provider = _SequenceMockProvider([
        LLMResponse(
            content="I'll write the Fibonacci function.",
            tool_calls=[
                ToolCall(
                    id="c1",
                    name="write_file",
                    arguments={
                        "path": "fib.py",
                        "content": "def fib(n):\n    return 0\n",
                    },
                ),
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            content="Now let me run the tests.",
            tool_calls=[
                ToolCall(
                    id="c2",
                    name="run_shell",
                    arguments={"command": "pytest test_fib.py"},
                ),
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            content="The test failed. Let me fix the implementation.",
            tool_calls=[
                ToolCall(
                    id="c3",
                    name="write_file",
                    arguments={
                        "path": "fib.py",
                        "content": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
                    },
                ),
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            content="Now let me verify the fix.",
            tool_calls=[
                ToolCall(
                    id="c4",
                    name="run_shell",
                    arguments={"command": "pytest test_fib.py"},
                ),
            ],
            finish_reason="tool_calls",
        ),
        LLMResponse(
            content="All tests passed!",
            tool_calls=[
                ToolCall(
                    id="c5",
                    name="finish",
                    arguments={"reason": "All tests passed"},
                ),
            ],
            finish_reason="tool_calls",
        ),
    ])

    # ── Build harness ────────────────────────────────────────────────
    config = Config(
        loop=LoopConfig(max_iterations=10),
        guardrail=GuardrailConfig(enabled=False),
    )
    guardrail = Guardrail(config.guardrail)
    cm = ContextManager()
    sd = AutonomousStopDecision(guardrail=guardrail, config=config.loop)
    feedback = FeedbackEngine()

    loop = HarnessLoop(
        provider=provider,
        dispatcher=dispatcher,
        guardrail=guardrail,
        context_manager=cm,
        stop_decision=sd,
        feedback_engine=feedback,
        config=config,
    )

    tool_defs = [
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
        ToolDef(
            name="run_shell",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        ),
    ]

    # ── Run ──────────────────────────────────────────────────────────
    print("  Starting TDD cycle...")
    print()
    result = loop.run("Implement a Fibonacci function", tool_defs)

    print()
    print(f"  Result: {'SUCCESS' if result.success else 'FAILURE'}")
    print(f"  Iterations: {result.iterations}")
    if result.error:
        print(f"  Error: {result.error}")
    print()
    print("=" * 60)
    print("  Demo complete - full TDD cycle demonstrated")
    print("=" * 60)


if __name__ == "__main__":
    main()