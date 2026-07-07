"""Provider factory (T4).

Registry-based creation of LLM providers so the rest of the harness
never needs to import concrete provider classes directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.config import LLMConfig

    from .base import LLMProvider


class ProviderFactory:
    """Registry and factory for LLM providers.

    Usage::

        ProviderFactory.register("mock", MockProvider)
        provider = ProviderFactory.create(config)
    """

    _registry: dict[str, type[LLMProvider]] = {}

    # ── Registry management ─────────────────────────────────────────

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a provider class under *name*.

        Args:
            name: Short identifier (e.g. ``"mock"``, ``"openai"``).
            provider_cls: The class to register (must subclass ``LLMProvider``).
        """
        cls._registry[name] = provider_cls

    @classmethod
    def registered_names(cls) -> list[str]:
        """Return a sorted list of all registered provider names."""
        return sorted(cls._registry.keys())

    # ── Construction ────────────────────────────────────────────────

    @classmethod
    def create(cls, config: LLMConfig) -> LLMProvider:
        """Create a provider instance from an *LLMConfig*.

        Args:
            config: Provider configuration (at minimum ``config.name``).

        Returns:
            An instantiated ``LLMProvider``.

        Raises:
            ValueError: If *config.name* is not in the registry.
        """
        provider_cls = cls._registry.get(config.name)
        if provider_cls is None:
            registered = ", ".join(cls.registered_names())
            raise ValueError(
                f"Unknown provider {config.name!r}. "
                f"Registered providers: [{registered}]"
            )
        return provider_cls()