"""Mock LLM provider for testing (T4).

Returns canned responses so harness behaviour can be verified without
a real API connection.
"""

from __future__ import annotations

from typing import Any

from harness.config import LLMConfig
from harness.models import LLMResponse, Message, ToolCall, ToolDef

from .base import LLMProvider


class MockProvider(LLMProvider):
    """A provider that returns preset responses.

    Responses are looked up by the **last user message content** in the
    conversation.  If no preset matches, a default response is returned.

    Attributes:
        preset_responses: Maps ``str`` (user message content) → ``LLMResponse``.
        default_response: Fallback when no preset matches.
    """

    def __init__(
        self,
        preset_responses: dict[str, LLMResponse] | None = None,
        default_response: LLMResponse | None = None,
    ) -> None:
        self.preset_responses: dict[str, LLMResponse] = preset_responses or {}
        self.default_response: LLMResponse = default_response or LLMResponse(
            content="Mock default response",
        )

    # ── Provider interface ──────────────────────────────────────────

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Return a preset response keyed by the last user message.

        If no user message is found, or the message content is not in
        *preset_responses*, the *default_response* is returned.

        The *tools* and *config* parameters are accepted for interface
        compatibility but are not used by the mock.
        """
        # Find the last user message
        last_user_msg = next(
            (m for m in reversed(messages) if m.role == "user"),
            None,
        )

        if last_user_msg and last_user_msg.content in self.preset_responses:
            return self.preset_responses[last_user_msg.content]

        return self.default_response

    # ── Convenience builders ────────────────────────────────────────

    @classmethod
    def with_text_response(
        cls,
        text: str,
        finish_reason: str = "stop",
    ) -> MockProvider:
        """Create a ``MockProvider`` that always returns *text*."""
        return cls(
            default_response=LLMResponse(content=text, finish_reason=finish_reason),
        )

    @classmethod
    def with_tool_call(
        cls,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        response_text: str = "",
    ) -> MockProvider:
        """Create a ``MockProvider`` that always returns a single ``ToolCall``."""
        tc = ToolCall(
            id="mock_call_1",
            name=tool_name,
            arguments=arguments or {},
        )
        return cls(
            default_response=LLMResponse(
                content=response_text,
                tool_calls=[tc],
                finish_reason="tool_calls",
            ),
        )