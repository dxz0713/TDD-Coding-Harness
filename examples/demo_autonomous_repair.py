"""Demonstrate: Full TDD cycle with autonomous repair using MockProvider.

Shows the complete "write code → test fails → feedback → fix → test passes"
cycle powered by the real HarnessLoop + FeedbackEngine, driven by a
sequence-based MockProvider (no real LLM needed).

Usage:
    python examples/demo_autonomous_repair.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.config import Config, GuardrailConfig, LoopConfig
from harness.context import ContextManager
from harness.guardrail import Guardrail
from harness.loop import HarnessLoop
from harness.models import LLMResponse, ToolCall, ToolDef, ToolResult
from harness.stop_condition import AutonomousStopDecision
from providers.mock import MockProvider
from feedback.engine import FeedbackEngine
from tools.dispatcher import ToolDispatcher
from tools.read_file import ReadFile
from tools.write_file import WriteFile
from tools.run_shell import RunShell


# ═══════════════════════════════════════════════════════════════════
# Custom mock tools for deterministic demo behaviour
# ═══════════════════════════════════════════════════════════════════


class _MockRunShell(RunShell):
    """RunShell that fails on first call, passes on subsequent calls.

    This simulates a real test-driven cycle without needing an actual
    Python project to test.
    """

    def __init__(self) -> None:
        super().__init__()
        self._call_count = 0

    def execute(self, command: str = "", timeout: int = 30, cwd: str | None = None) -> ToolResult:
        self._call_count += 1
        if self._call_count == 1:
            return ToolResult(
                success=False,
                output="""_____________________________ test_fib _____________________________
    def test_fib_basic():
>       assert fib(5) == 5, f"Expected 5, got {fib(5)}"
E       AssertionError: Expected 5, got 0
E       assert 0 == 5

test_fib.py:2: AssertionError
_____________________________ test_fib_edge _____________________________
    def test_fib_edge():
>       assert fib(0) == 0
E       assert fib(0) == 0

test_fib.py:6: AssertionError
========================= short test summary info ==========================
FAILED test_fib.py::test_fib_basic - AssertionError: Expected 5, got 0
FAILED test_fib.py::test_fib_edge - AssertionError: assert fib(0) == 0
""",
                error="2 failed, 0 passed",
                exit_code=1,
            )
        return ToolResult(
            success=True,
            output="""_____________________________ test_fib _____________________________
    def test_fib_basic():
>       assert fib(5) == 5, f"Expected 5, got {fib(5)}"
E       assert 5 == 5

test_fib.py:2: AssertionError: Expected 5, got 5
_____________________________ test_fib_edge _____________________________
    def test_fib_edge():
>       assert fib(0) == 0
E       assert 0 == 0

test_fib.py:6: AssertionError: assert 0 == 0
========================= 2 passed in 0.02s ==========================
""",
            error="",
            exit_code=0,
        )


# ═══════════════════════════════════════════════════════════════════
# Sequence-based MockProvider
# ═══════════════════════════════════════════════════════════════════


class _SequenceMockProvider(MockProvider):
    """MockProvider that returns responses in a fixed sequence.

    Extends the project's ``MockProvider`` so all MockProvider semantics
    are preserved (it IS a MockProvider, registered with the same type).
    After the sequence is exhausted, the last response is repeated.
    """

    def __init__(self, responses: list[LLMResponse]) -> None:
        super().__init__()
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
# Phase printers
# ═══════════════════════════════════════════════════════════════════

def _phase(title: str) -> None:
    print()
    print(f"  # {'=' * 50}")
    print(f"  # {title}")
    print(f"  # {'=' * 50}")
    print()


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════


def main() -> None:
    """Run the autonomous repair demonstration."""
    print("=" * 60)
    print("  TDD Coding Harness -- Autonomous Repair Demo")
    print("=" * 60)

    _phase("Phase 1: Register tools")

    dispatcher = ToolDispatcher()
    dispatcher.register(WriteFile())
    dispatcher.register(ReadFile())
    dispatcher.register(_MockRunShell())
    print("  Tools registered: write_file, read_file, run_shell")

    _phase("Phase 2: Configure MockProvider with response sequence")

    # ── Sequence of LLM responses ────────────────────────────────────
    # Each response simulates what a real LLM would decide to do at
    # that point in the TDD cycle.
    responses = [
        # Step 1: Write the initial (buggy) implementation
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
        # Step 2: Run the tests → they will fail
        LLMResponse(
            content="Now let me run the tests.",
            tool_calls=[
                ToolCall(
                    id="c2",
                    name="run_shell",
                    arguments={"command": "pytest test_fib.py -v"},
                ),
            ],
            finish_reason="tool_calls",
        ),
        # Step 3: Read the file to understand the code
        LLMResponse(
            content="The test failed. Let me read the current implementation.",
            tool_calls=[
                ToolCall(
                    id="c3",
                    name="read_file",
                    arguments={"path": "fib.py"},
                ),
            ],
            finish_reason="tool_calls",
        ),
        # Step 4: Write the fixed implementation
        LLMResponse(
            content="I see the issue. Let me fix the implementation.",
            tool_calls=[
                ToolCall(
                    id="c4",
                    name="write_file",
                    arguments={
                        "path": "fib.py",
                        "content": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
                    },
                ),
            ],
            finish_reason="tool_calls",
        ),
        # Step 5: Verify the fix
        LLMResponse(
            content="Now let me verify the fix.",
            tool_calls=[
                ToolCall(
                    id="c5",
                    name="run_shell",
                    arguments={"command": "pytest test_fib.py -v"},
                ),
            ],
            finish_reason="tool_calls",
        ),
        # Step 6: Finish
        LLMResponse(
            content="All tests passed!",
            tool_calls=[
                ToolCall(
                    id="c6",
                    name="finish",
                    arguments={"reason": "All tests passed"},
                ),
            ],
            finish_reason="tool_calls",
        ),
    ]

    provider = _SequenceMockProvider(responses)
    print(f"  MockProvider loaded with {len(responses)} response steps")
    print("  (no real LLM connection needed)")

    _phase("Phase 3: Build harness with real components")

    config = Config(
        loop=LoopConfig(max_iterations=20),
        guardrail=GuardrailConfig(enabled=False),
    )
    guardrail = Guardrail(config.guardrail)
    context_manager = ContextManager()
    stop_decision = AutonomousStopDecision(guardrail=guardrail, config=config.loop)
    feedback_engine = FeedbackEngine()

    loop = HarnessLoop(
        provider=provider,
        dispatcher=dispatcher,
        guardrail=guardrail,
        context_manager=context_manager,
        stop_decision=stop_decision,
        feedback_engine=feedback_engine,
        config=config,
    )

    print("  HarnessLoop        [OK]  (real — orchestrates the loop)")
    print("  FeedbackEngine     [OK]  (real — Collector -> Analyzer -> Strategy)")
    print("  Guardrail          [OK]  (real — dangerous command interception)")
    print("  ContextManager     [OK]  (real — system prompt + message history)")
    print("  AutonomousStopDecision  [OK]  (real — stop condition evaluation)")

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
            name="read_file",
            description="Read content from a file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        ),
        ToolDef(
            name="run_shell",
            description="Execute a shell command",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["command"],
            },
        ),
    ]

    _phase("Phase 4: Run TDD cycle")

    print("  Task: Implement a Fibonacci function")
    print()
    result = loop.run("Implement a Fibonacci function", tool_defs)

    _phase("Phase 5: Results")

    print(f"  Iterations: {result.iterations}")
    print(f"  Status:     {'[SUCCESS]' if result.success else '[FAILURE]'}")
    if result.error:
        print(f"  Error:      {result.error}")

    print()
    print("=" * 60)
    print("  Demo complete -- full TDD cycle demonstrated")
    print()
    print("  What happened:")
    print("    1. LLM wrote initial (buggy) Fibonacci implementation")
    print("    2. Tests ran and FAILED -- FeedbackEngine analyzed output")
    print("    3. LLM read the current code to understand the bug")
    print("    4. LLM wrote a fixed implementation")
    print("    5. Tests ran and PASSED")
    print("    6. LLM called finish() to signal completion")
    print()
    print("  Key takeaway: The FeedbackEngine classified the test")
    print("  failure (AssertionError), generated a repair prompt,")
    print("  and injected it back into the LLM context -- all without")
    print("  a real API call.")
    print("=" * 60)


if __name__ == "__main__":
    main()
