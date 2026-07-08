"""OpenAI-compatible LLM provider (T5).

Works with any API that speaks the OpenAI Chat Completions format,
including OpenAI, DeepSeek, Qwen, and others.
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import APIStatusError, APITimeoutError, RateLimitError, OpenAI

from harness.config import LLMConfig
from harness.models import LLMResponse, Message, ToolCall, ToolDef

from .base import LLMAuthError, LLMProvider, LLMRateLimitError, LLMTimeoutError


class OpenAICompatibleProvider(LLMProvider):
    """Provider that calls an OpenAI-compatible Chat Completions API.

    Reads the API key from the ``OPENAI_API_KEY`` environment variable
    by default; a key can also be passed directly to the constructor.

    Attributes:
        client: The underlying ``openai.OpenAI`` client instance.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialise the provider.

        Args:
            api_key: API key.  If ``None`` (the default), the key is
                read from the ``OPENAI_API_KEY`` environment variable.
        """
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.client = OpenAI(api_key=resolved_key)

    # ── Provider interface ──────────────────────────────────────────

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        """Call the Chat Completions API and return a structured response.

        Args:
            messages: Conversation history.
            tools: Tool definitions the LLM may call (optional).
            config: Provider configuration overrides (optional).

        Returns:
            A structured response containing text content and/or tool calls.

        Raises:
            LLMTimeoutError: Request timed out.
            LLMAuthError: Authentication failed.
            LLMRateLimitError: Rate-limited by the provider.
        """
        # ── Build request parameters ──────────────────────────────
        kwargs: dict[str, Any] = {
            "messages": [_to_openai_msg(m) for m in messages],
            "model": config.model if config else "gpt-4o",
        }

        if config is not None:
            if config.base_url is not None and config.base_url.strip():
                self.client.base_url = config.base_url.rstrip("/") + "/"
            if config.temperature is not None:
                kwargs["temperature"] = config.temperature
            if config.max_tokens is not None:
                kwargs["max_tokens"] = config.max_tokens
            if config.timeout is not None:
                kwargs["timeout"] = config.timeout

        if tools:
            kwargs["tools"] = [_to_openai_tool(t) for t in tools]

        # ── Make the API call ─────────────────────────────────────
        try:
            response = self.client.chat.completions.create(**kwargs)
        except APITimeoutError as exc:
            raise LLMTimeoutError(f"Request timed out: {exc}") from exc
        except APIStatusError as exc:
            status_code = exc.response.status_code if exc.response else 0
            if status_code == 401:
                raise LLMAuthError(
                    f"Authentication failed (status {status_code}): {exc}"
                ) from exc
            if status_code == 429:
                raise LLMRateLimitError(
                    f"Rate limited (status {status_code}): {exc}"
                ) from exc
            raise
        except Exception as exc:
            raise LLMTimeoutError(f"Request failed: {exc}") from exc

        # ── Parse the response ────────────────────────────────────
        choice = response.choices[0]
        finish_reason: str = choice.finish_reason or "stop"

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),  # JSON string → dict
                    )
                )
            # Map finish_reason to standard values
            if finish_reason == "tool_calls":
                pass  # already correct
            elif finish_reason == "stop" and tool_calls:
                finish_reason = "tool_calls"

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )


# ═══════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════


def _to_openai_msg(msg: Message) -> dict[str, Any]:
    """Convert a ``Message`` to the OpenAI Chat Completions format."""
    d: dict[str, Any] = {"role": msg.role, "content": msg.content}
    if msg.tool_call_id:
        d["tool_call_id"] = msg.tool_call_id
    return d


def _to_openai_tool(tool: ToolDef) -> dict[str, Any]:
    """Convert a ``ToolDef`` to the OpenAI tool-calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }