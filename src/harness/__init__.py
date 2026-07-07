"""TDD Coding Harness — top-level package.

Registers built-in providers and tools so they are available
when the harness runs.
"""

from __future__ import annotations

from providers.factory import ProviderFactory
from providers.mock import MockProvider
from tools.dispatcher import ToolDispatcher
from tools.read_file import ReadFile
from tools.run_shell import RunShell
from tools.write_file import WriteFile

# ── Register providers ────────────────────────────────────────────

ProviderFactory.register("mock", MockProvider)

try:
    from providers.openai_compat import OpenAICompatibleProvider  # noqa: F811

    ProviderFactory.register("openai", OpenAICompatibleProvider)
except ImportError:
    pass  # openai package not installed — skip registration

# ── Default tool dispatcher ───────────────────────────────────────

_default_dispatcher: ToolDispatcher | None = None


def get_default_dispatcher() -> ToolDispatcher:
    """Return (or create) the singleton default dispatcher with built-in tools."""
    global _default_dispatcher
    if _default_dispatcher is None:
        _default_dispatcher = ToolDispatcher()
        _default_dispatcher.register(ReadFile())
        _default_dispatcher.register(WriteFile())
        _default_dispatcher.register(RunShell())
    return _default_dispatcher