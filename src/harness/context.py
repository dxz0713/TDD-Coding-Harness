"""Context manager — build and update context for the main loop (T12).

The ContextManager is responsible for constructing the initial system
prompt (with task description and tool definitions), appending tool
execution results, and appending feedback back into the message
history.
"""

from __future__ import annotations

from harness.models import Context, Feedback, Memory, Message, ToolCall, ToolDef, ToolResult


class ContextManager:
    """Builds and updates the conversation context for the harness loop.

    Each method returns a new Context (or modifies in place) so the
    caller always has the latest state.
    """

    def __init__(self, memory: Memory | None = None) -> None:
        """Initialize the context manager.

        Args:
            memory: Optional project memory to include in the system prompt.
        """
        self._memory = memory

    # ── Public API ──────────────────────────────────────────────────

    def build(self, task: str, tool_defs: list[ToolDef]) -> Context:
        """Build the initial context with a system prompt.

        The system prompt includes the task description, tool definitions,
        and optional project memory context.

        Args:
            task: The high-level task description for the LLM.
            tool_defs: List of tool definitions available to the LLM.

        Returns:
            A new Context with the system message and task set.
        """
        lines: list[str] = ["You are a TDD coding assistant. Your task is to complete the following objective by writing code and running tests.", ""]

        lines.append(f"Task: {task}")
        lines.append("")

        # Tool definitions
        lines.append("Available tools:")
        for td in tool_defs:
            lines.append(f"  - {td.name}: {td.description}")
            params = td.parameters.get("properties", {})
            if params:
                lines.append(f"    Parameters: {', '.join(params.keys())}")
        lines.append("")

        # Memory context
        if self._memory is not None:
            lines.append("Project context:")
            if self._memory.project_name:
                lines.append(f"  Project: {self._memory.project_name}")
            if self._memory.project_description:
                lines.append(f"  Description: {self._memory.project_description}")
            if self._memory.tech_stack:
                lines.append(f"  Tech stack: {', '.join(self._memory.tech_stack)}")
            if self._memory.conventions:
                lines.append("  Conventions:")
                for c in self._memory.conventions:
                    lines.append(f"    - {c}")
            if self._memory.decisions:
                lines.append("  Previous decisions:")
                for d in self._memory.decisions[-5:]:  # last 5 decisions
                    lines.append(f"    - [{d.timestamp}] {d.description}")
            lines.append("")

        system_content = "\n".join(lines)

        return Context(
            messages=[Message(role="system", content=system_content)],
            memory=self._memory,
            iteration=0,
            task=task,
        )

    def append_tool_result(
        self,
        ctx: Context,
        tool_call: ToolCall,
        result: ToolResult,
    ) -> Context:
        """Append a tool execution result to the message history.

        Args:
            ctx: The current context.
            tool_call: The tool call that was executed.
            result: The result returned by the tool.

        Returns:
            Updated Context with the tool result appended and iteration incremented.
        """
        ctx.messages.append(
            Message(
                role="tool",
                content=result.output or result.error or "",
                tool_call_id=tool_call.id,
            ),
        )
        ctx.iteration += 1
        return ctx

    def append_feedback(self, ctx: Context, feedback: Feedback) -> Context:
        """Append feedback information to the message history.

        Args:
            ctx: The current context.
            feedback: The feedback package to append.

        Returns:
            Updated Context with the feedback message appended and iteration incremented.
        """
        content = (
            f"Feedback ({feedback.failure_type.value}): {feedback.summary}\n\n"
            f"Details: {feedback.details.error_message}\n\n"
            f"Repair prompt: {feedback.repair_prompt}"
        )
        ctx.messages.append(
            Message(role="user", content=content),
        )
        ctx.iteration += 1
        return ctx