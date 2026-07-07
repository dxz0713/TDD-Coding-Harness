"""Main loop framework for TDD Coding Harness (T11).

HarnessLoop is the central orchestrator.  It owns the run loop but
delegates every concrete concern (LLM calls, tool execution, guardrail
checks, context management, stop decisions) to injected dependencies.
"""

from __future__ import annotations

from harness.config import Config
from harness.context import ContextManager
from harness.guardrail import Guardrail
from harness.memory import MemoryStore
from harness.models import Context, LLMResponse, RunResult, ToolCall, ToolDef
from harness.stop_condition import AutonomousStopDecision
from providers.base import LLMProvider
from tools.dispatcher import ToolDispatcher


class HarnessLoop:
    """Main TDD loop — owns the run loop, delegates everything else.

    Design principles:

    1. **Dependency injection** — all dependencies are received through
       the constructor.  HarnessLoop never instantiates anything itself.
    2. **Orchestration only** — the loop controls *when* things happen,
       not *how*.  Context assembly, stop evaluation, feedback analysis,
       etc. are all delegated.
    3. **Finish is a virtual tool** — ``ToolCall(name="finish")`` is
       intercepted before dispatch and routed to
       ``stop_decision.on_finish()``.
    """

    def __init__(
        self,
        provider: LLMProvider,
        dispatcher: ToolDispatcher,
        guardrail: Guardrail,
        context_manager: ContextManager,
        stop_decision: AutonomousStopDecision,
        memory_store: MemoryStore | None = None,
        config: Config | None = None,
    ) -> None:
        """Initialise the harness loop with injected dependencies.

        Args:
            provider: LLM provider used to generate responses.
            dispatcher: Dispatches ``ToolCall``\\ s to registered tools.
            guardrail: Checks tool calls for dangerous commands.
            context_manager: Builds and updates the conversation context.
            stop_decision: Evaluates whether the loop should stop.
            memory_store: Optional cross-session memory store.
            config: Optional harness configuration.
        """
        self._provider = provider
        self._dispatcher = dispatcher
        self._guardrail = guardrail
        self._context_manager = context_manager
        self._stop_decision = stop_decision
        self._memory_store = memory_store
        self._config = config

    # ── Public API ──────────────────────────────────────────────────

    def run(self, task: str, tool_defs: list[ToolDef]) -> RunResult:
        """Execute the main TDD loop for the given *task*.

        Args:
            task: The high-level task description for the LLM.
            tool_defs: Tool definitions available to the LLM.

        Returns:
            A ``RunResult`` summarising the outcome.
        """
        ctx: Context = self._context_manager.build(task, tool_defs)

        while True:
            response: LLMResponse = self._provider.generate(
                ctx.messages,
                tool_defs,
                self._config.provider if self._config else None,
            )

            for tool_call in response.tool_calls:
                # ── Virtual "finish" tool ──────────────────────────
                if tool_call.name == "finish":
                    decision = self._stop_decision.on_finish(tool_call)
                    return RunResult(
                        success=decision.success,
                        iterations=ctx.iteration,
                        artifacts=[],
                        error=None if decision.success else decision.reason,
                    )

                # ── Guardrail check ────────────────────────────────
                guard = self._guardrail.check_tool_call(tool_call)
                if not guard.allowed:
                    return RunResult(
                        success=False,
                        iterations=ctx.iteration,
                        artifacts=[],
                        error=guard.reason,
                    )

                # ── Dispatch & append result ───────────────────────
                result = self._dispatcher.dispatch(tool_call)
                ctx = self._context_manager.append_tool_result(ctx, tool_call, result)

                # ── Feedback (test-command output) ─────────────────
                if result.exit_code is not None:
                    # TODO(T18): Integrate FeedbackEngine.analyze()
                    # feedback = self.feedback_engine.analyze(result, ctx)
                    # if feedback:
                    #     ctx = self._context_manager.append_feedback(ctx, feedback)
                    pass

            # ── Stop check after processing all tool calls ─────────
            decision = self._stop_decision.should_stop(ctx)
            if decision.should_stop:
                return RunResult(
                    success=decision.success,
                    iterations=ctx.iteration,
                    artifacts=[],
                    error=None if decision.success else decision.reason,
                )