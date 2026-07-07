"""Autonomous stop decision — determines when the main loop should stop (T13).

Evaluates four stop conditions:
1. All tests passed (detected via tool result content).
2. Maximum iterations reached.
3. LLM returned a Finish tool call.
4. Guardrail blocked a dangerous command.
"""

from __future__ import annotations

from harness.config import LoopConfig
from harness.guardrail import Guardrail
from harness.models import Context, GuardrailResult, StopDecision, ToolCall


class AutonomousStopDecision:
    """Evaluates whether the main loop should stop and why.

    The class combines guardrail results with loop configuration and
    context state to make a stop decision.
    """

    def __init__(self, guardrail: Guardrail, config: LoopConfig) -> None:
        """Initialize the stop decision engine.

        Args:
            guardrail: The guardrail instance (used to check for blocked tool calls).
            config: Loop configuration (max_iterations, etc.).
        """
        self._guardrail = guardrail
        self._config = config

    # ── Public API ──────────────────────────────────────────────────

    def should_stop(self, context: Context) -> StopDecision:
        """Check whether the main loop should stop.

        Evaluates stop conditions in order:
        1. Maximum iterations reached.
        2. Guardrail blocked a tool call (in the last message).
        3. All tests passed.

        Args:
            context: The current run context.

        Returns:
            StopDecision with should_stop=True if any condition is met.
        """
        # Condition 1: Max iterations
        if context.iteration >= self._config.max_iterations:
            return StopDecision(
                should_stop=True,
                success=False,
                reason="Max iterations reached",
            )

        # Condition 2: All tests passed (check last tool message)
        for msg in reversed(context.messages):
            if msg.role == "tool" and "passed" in msg.content.lower():
                # Check if "all tests passed" or similar
                if "all" in msg.content.lower() or "100%" in msg.content:
                    return StopDecision(
                        should_stop=True,
                        success=True,
                        reason="All tests passed",
                    )
                # Single test passed — don't stop on that alone
            break  # Only check the last message

        # Condition 3: Guardrail check on the last tool call
        # (This is checked externally; the caller should pass guardrail-blocked
        #  cases via the guardrail_blocked parameter or the on_finish method.)

        return StopDecision(should_stop=False, success=False, reason="")

    def on_finish(self, tool_call: ToolCall) -> StopDecision:
        """Handle an LLM Finish tool call.

        Args:
            tool_call: The Finish tool call from the LLM.

        Returns:
            StopDecision based on the reason in the Finish call.
        """
        reason: str = tool_call.arguments.get("reason", "")

        # Check for explicit failure indicators first
        failure_prefixes = [
            "unable to", "failed to", "could not", "cannot", "can't",
            "unfinished", "incomplete", "error", "failure",
        ]
        reason_lower = reason.lower()
        is_failure = any(reason_lower.startswith(prefix) for prefix in failure_prefixes)

        if is_failure:
            return StopDecision(
                should_stop=True,
                success=False,
                reason=reason or "LLM returned Finish",
            )

        success_keywords = [
            "passed", "complete", "success", "done", "finished",
            "all tests", "tests passed", "implementation complete",
        ]
        is_success = any(kw in reason_lower for kw in success_keywords)

        return StopDecision(
            should_stop=True,
            success=is_success,
            reason=reason or "LLM returned Finish",
        )

    def check_guardrail(self, tool_call: ToolCall) -> StopDecision | None:
        """Check if a tool call is blocked by the guardrail.

        If the guardrail blocks the call, a StopDecision is returned.
        Otherwise returns None (caller should proceed with execution).

        Args:
            tool_call: The tool call to check.

        Returns:
            StopDecision if blocked, None otherwise.
        """
        result: GuardrailResult = self._guardrail.check_tool_call(tool_call)
        if not result.allowed:
            return StopDecision(
                should_stop=True,
                success=False,
                reason=f"Guardrail blocked: {result.reason}",
            )
        return None