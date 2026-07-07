"""Abstract LLM provider interface (T4).

Defines the contract every LLM provider must satisfy, along with
domain-specific exceptions for common failure modes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness.models import LLMResponse, Message


# ═══════════════════════════════════════════════════════════════════
# Custom exceptions
# ═══════════════════════════════════════════════════════════════════


class LLMTimeoutError(Exception):
    """Raised when the LLM provider fails to respond within the configured timeout."""


class LLMAuthError(Exception):
    """Raised when authentication with the LLM provider fails (invalid key, etc.)."""


class LLMRateLimitError(Exception):
    """Raised when the LLM provider returns a rate-limit / 429 response."""


# ═══════════════════════════════════════════════════════════════════
# Abstract provider
# ═══════════════════════════════════════════════════════════════════


class LLMProvider(ABC):
    """Abstract base for all LLM providers.

    Subclasses must implement :meth:`generate`, which takes a conversation
    history and returns a structured :class:`LLMResponse`.
    """

    @abstractmethod
    def generate(self, messages: list[Message]) -> LLMResponse:
        """Send a conversation to the LLM and return its response.

        Args:
            messages: The conversation history so far.

        Returns:
            A structured response containing text content and/or tool calls.

        Raises:
            LLMTimeoutError: Request timed out.
            LLMAuthError: Authentication failed.
            LLMRateLimitError: Rate-limited by the provider.
        """
        ...