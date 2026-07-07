"""TDD Coding Harness — top-level package.

Registers built-in providers and tools so they are available
when the harness runs.
"""

from __future__ import annotations

from providers.factory import ProviderFactory
from providers.mock import MockProvider

# ── Register providers ────────────────────────────────────────────

ProviderFactory.register("mock", MockProvider)

try:
    from providers.openai_compat import OpenAICompatibleProvider  # noqa: F811

    ProviderFactory.register("openai", OpenAICompatibleProvider)
except ImportError:
    pass  # openai package not installed — skip registration