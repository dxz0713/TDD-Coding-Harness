"""Configuration loading for TDD Coding Harness (SPEC §3.8).

Supports YAML configuration files with CLI parameter overrides.
Priority: CLI arguments > config file > defaults.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import yaml
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# Sub-config models
# ═══════════════════════════════════════════════════════════════════

class LLMConfig(BaseModel):
    """Provider-specific configuration."""

    name: str = "mock"
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 30  # seconds


class LoopConfig(BaseModel):
    """Main loop configuration."""

    max_iterations: int = 5
    workspace: str = "."


class GuardrailConfig(BaseModel):
    """Guardrail (dangerous command interception) configuration."""

    enabled: bool = True
    block_list: list[str] = []


class MemoryConfig(BaseModel):
    """Cross-session memory configuration."""

    enabled: bool = True
    path: str = "output/memory.json"


# ═══════════════════════════════════════════════════════════════════
# Top-level Config
# ═══════════════════════════════════════════════════════════════════

class Config(BaseModel):
    """Top-level configuration combining all sub-configs."""

    version: int = 1
    provider: LLMConfig = Field(default_factory=LLMConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    guardrail: GuardrailConfig = Field(default_factory=GuardrailConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    # ── YAML loading ──────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Config instance with values from the file (defaults for missing fields).

        Raises:
            FileNotFoundError: If the YAML file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    # ── CLI overrides ─────────────────────────────────────────────

    def with_overrides(
        self,
        provider_name: str | None = None,
        provider_model: str | None = None,
    ) -> "Config":
        """Return a new Config with CLI-provided overrides applied.

        Args:
            provider_name: Override for provider.name (if not None).
            provider_model: Override for provider.model (if not None).

        Returns:
            A new Config instance with overrides merged in.
        """
        overrides: dict[str, Any] = {}
        provider_overrides: dict[str, Any] = {}

        if provider_name is not None:
            provider_overrides["name"] = provider_name
        if provider_model is not None:
            provider_overrides["model"] = provider_model

        if provider_overrides:
            overrides["provider"] = provider_overrides

        if overrides:
            base_data = self.model_dump()
            base_data = self._deep_merge(base_data, overrides)
            return Config.model_validate(base_data)
        return self.model_copy(deep=True)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep-merge override dict into base dict (mutates base)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value
        return base