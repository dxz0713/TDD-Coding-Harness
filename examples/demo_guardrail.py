"""Demonstrate: Guardrail intercepts dangerous commands.

Usage:
    python examples/demo_guardrail.py
"""

import sys
import os

# Ensure the harness package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from harness.guardrail import Guardrail
from harness.config import GuardrailConfig
from harness.models import ToolCall


def main() -> None:
    """Run the guardrail demonstration."""
    guard = Guardrail(GuardrailConfig())

    # ── Should be blocked ────────────────────────────────────────────
    result = guard.check_tool_call(
        ToolCall(id="1", name="run_shell", arguments={"command": "rm -rf /"}),
    )
    assert not result.allowed, f"Expected blocked, got allowed: {result.reason}"
    print(f"[BLOCKED] {result.reason}")

    # ── Should be allowed ────────────────────────────────────────────
    result = guard.check_tool_call(
        ToolCall(id="2", name="run_shell", arguments={"command": "pytest tests/"}),
    )
    assert result.allowed, f"Expected allowed, got blocked: {result.reason}"
    print("[ALLOWED] Safe command passed")

    print()
    print("[PASS] Guardrail demo passed")


if __name__ == "__main__":
    main()