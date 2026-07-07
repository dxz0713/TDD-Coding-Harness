"""Tests for LLM provider layer (T4).

Covers the abstract base, custom exceptions, MockProvider, and
ProviderFactory.
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.models import LLMResponse, Message, ToolCall
from providers.base import LLMAuthError, LLMProvider, LLMRateLimitError, LLMTimeoutError
from providers.factory import ProviderFactory
from providers.mock import MockProvider


# ═══════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════


class TestLLMExceptions:
    """Custom exceptions should carry descriptive names and be catchable."""

    def test_llm_timeout_error(self) -> None:
        exc = LLMTimeoutError("Request timed out")
        assert isinstance(exc, Exception)
        assert "timed out" in str(exc)

    def test_llm_auth_error(self) -> None:
        exc = LLMAuthError("Invalid API key")
        assert isinstance(exc, Exception)
        assert "API" in str(exc)

    def test_llm_rate_limit_error(self) -> None:
        exc = LLMRateLimitError("Rate limited")
        assert isinstance(exc, Exception)
        assert "Rate" in str(exc)

    def test_exceptions_are_distinct(self) -> None:
        """Each exception type should be independently catchable."""
        errors = [LLMTimeoutError, LLMAuthError, LLMRateLimitError]
        assert len({type(e()) for e in errors}) == 3


# ═══════════════════════════════════════════════════════════════════
# Abstract base
# ═══════════════════════════════════════════════════════════════════


class TestLLMProviderABC:
    """LLMProvider cannot be instantiated directly."""

    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]


# ═══════════════════════════════════════════════════════════════════
# MockProvider
# ═══════════════════════════════════════════════════════════════════


class TestMockProvider:
    """MockProvider returns preset or default responses."""

    def test_default_response(self) -> None:
        """No presets → default response."""
        provider = MockProvider()
        messages = [Message(role="user", content="hello")]
        response = provider.generate(messages)
        assert response.content == "Mock default response"
        assert response.tool_calls == []
        assert response.finish_reason == "stop"

    def test_custom_default_response(self) -> None:
        """Custom default response is returned when no preset matches."""
        provider = MockProvider(
            default_response=LLMResponse(content="Custom default"),
        )
        response = provider.generate([Message(role="user", content="anything")])
        assert response.content == "Custom default"

    def test_preset_response(self) -> None:
        """Preset matching the last user message is returned."""
        provider = MockProvider(
            preset_responses={
                "hello": LLMResponse(content="Hi there!"),
            },
        )
        response = provider.generate([Message(role="user", content="hello")])
        assert response.content == "Hi there!"

    def test_preset_uses_last_user_message(self) -> None:
        """Only the *last* user message is used for lookup."""
        provider = MockProvider(
            preset_responses={
                "first": LLMResponse(content="FIRST"),
                "second": LLMResponse(content="SECOND"),
            },
        )
        messages = [
            Message(role="system", content="You are a bot"),
            Message(role="user", content="first"),
            Message(role="assistant", content="whatever"),
            Message(role="user", content="second"),
        ]
        response = provider.generate(messages)
        assert response.content == "SECOND"

    def test_no_user_message_falls_back_to_default(self) -> None:
        """No user messages in the conversation → default response."""
        provider = MockProvider(
            preset_responses={"hello": LLMResponse(content="Hi")},
        )
        messages = [Message(role="system", content="You are a bot")]
        response = provider.generate(messages)
        assert response.content == "Mock default response"

    def test_empty_messages_list(self) -> None:
        """Empty message list → default response."""
        provider = MockProvider()
        response = provider.generate([])
        assert response.content == "Mock default response"

    def test_tool_call_response(self) -> None:
        """Provider can return a response with tool calls."""
        tc = ToolCall(id="call_1", name="read_file", arguments={"path": "x.txt"})
        provider = MockProvider(
            default_response=LLMResponse(
                content="",
                tool_calls=[tc],
                finish_reason="tool_calls",
            ),
        )
        response = provider.generate([Message(role="user", content="read file")])
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "read_file"
        assert response.finish_reason == "tool_calls"


class TestMockProviderBuilders:
    """Convenience class methods for common scenarios."""

    def test_with_text_response(self) -> None:
        provider = MockProvider.with_text_response("Fixed response", finish_reason="stop")
        resp = provider.generate([Message(role="user", content="anything")])
        assert resp.content == "Fixed response"
        assert resp.finish_reason == "stop"

    def test_with_text_response_tool_calls_empty(self) -> None:
        provider = MockProvider.with_text_response("No tools")
        resp = provider.generate([Message(role="user", content="hi")])
        assert resp.tool_calls == []

    def test_with_tool_call(self) -> None:
        provider = MockProvider.with_tool_call(
            tool_name="write_file",
            arguments={"path": "out.txt", "content": "data"},
            response_text="Calling tool",
        )
        resp = provider.generate([Message(role="user", content="write")])
        assert resp.content == "Calling tool"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "write_file"
        assert resp.tool_calls[0].arguments == {"path": "out.txt", "content": "data"}
        assert resp.finish_reason == "tool_calls"

    def test_with_tool_call_default_args(self) -> None:
        provider = MockProvider.with_tool_call(tool_name="read_file")
        resp = provider.generate([Message(role="user", content="go")])
        assert resp.content == ""
        assert resp.tool_calls[0].arguments == {}
        assert resp.tool_calls[0].id == "mock_call_1"


# ═══════════════════════════════════════════════════════════════════
# ProviderFactory
# ═══════════════════════════════════════════════════════════════════


class _DummyProvider(LLMProvider):
    """Minimal concrete provider for factory tests."""

    def generate(self, messages: list[Message]) -> LLMResponse:
        return LLMResponse(content="dummy")


class TestProviderFactoryRegistration:
    """Providers can be registered and then created."""

    def setup_method(self) -> None:
        # Start with a clean registry for this test class
        ProviderFactory._registry = {}

    def test_register_and_create(self) -> None:
        ProviderFactory.register("dummy", _DummyProvider)
        from harness.config import LLMConfig

        config = LLMConfig(name="dummy")
        provider = ProviderFactory.create(config)
        assert isinstance(provider, _DummyProvider)
        resp = provider.generate([Message(role="user", content="test")])
        assert resp.content == "dummy"

    def test_register_mock(self) -> None:
        ProviderFactory.register("mock", MockProvider)
        from harness.config import LLMConfig

        config = LLMConfig(name="mock")
        provider = ProviderFactory.create(config)
        assert isinstance(provider, MockProvider)

    def test_unknown_provider_raises_value_error(self) -> None:
        from harness.config import LLMConfig

        config = LLMConfig(name="nonexistent")
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.create(config)

    def test_register_overwrites_existing(self) -> None:
        ProviderFactory.register("dummy", _DummyProvider)
        ProviderFactory.register("dummy", MockProvider)
        from harness.config import LLMConfig

        config = LLMConfig(name="dummy")
        provider = ProviderFactory.create(config)
        assert isinstance(provider, MockProvider)

    def test_registered_names(self) -> None:
        ProviderFactory.register("aaa", _DummyProvider)
        ProviderFactory.register("zzz", _DummyProvider)
        ProviderFactory.register("mock", MockProvider)
        names = ProviderFactory.registered_names()
        assert names == ["aaa", "mock", "zzz"]

    def test_empty_registry(self) -> None:
        ProviderFactory._registry = {}
        assert ProviderFactory.registered_names() == []

    def test_create_raises_on_empty_registry(self) -> None:
        from harness.config import LLMConfig

        ProviderFactory._registry = {}
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.create(LLMConfig(name="mock"))


class TestProviderFactoryIntegration:
    """End-to-end: factory creates a working MockProvider."""

    def setup_method(self) -> None:
        ProviderFactory._registry = {}

    def test_factory_creates_working_mock(self) -> None:
        ProviderFactory.register("mock", MockProvider)
        from harness.config import LLMConfig

        config = LLMConfig(name="mock")
        provider = ProviderFactory.create(config)
        resp = provider.generate([Message(role="user", content="hello")])
        assert resp.content == "Mock default response"

    def test_factory_with_preset_via_registration(self) -> None:
        """Factory creates a default MockProvider; presets are set after creation."""
        ProviderFactory.register("mock", MockProvider)
        from harness.config import LLMConfig

        config = LLMConfig(name="mock")
        provider = ProviderFactory.create(config)
        # Add presets after creation
        provider.preset_responses["hello"] = LLMResponse(content="world")
        resp = provider.generate([Message(role="user", content="hello")])
        assert resp.content == "world"