"""Tests for Config loading (SPEC §3.8)."""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from harness.config import Config, LLMConfig, LoopConfig, GuardrailConfig, MemoryConfig


# ---------- Fixtures ----------

@pytest.fixture
def minimal_config_dict() -> dict[str, Any]:
    """Minimal valid config (all defaults should fill missing fields)."""
    return {
        "version": 1,
        "provider": {
            "name": "mock",
        },
    }


@pytest.fixture
def full_config_dict() -> dict[str, Any]:
    """Full config with all fields specified."""
    return {
        "version": 1,
        "provider": {
            "name": "openai",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
            "timeout": 60,
        },
        "loop": {
            "max_iterations": 10,
            "workspace": "/my/project",
        },
        "guardrail": {
            "enabled": True,
            "block_list": ["rm -rf", "dd if="],
        },
        "memory": {
            "enabled": True,
            "path": "output/custom_memory.json",
        },
    }


# ---------- Tests ----------

class TestConfigLoadDefaults:
    """Empty/missing fields should fall back to defaults."""

    def test_config_load_defaults(self, minimal_config_dict: dict[str, Any]) -> None:
        config = Config.model_validate(minimal_config_dict)
        assert config.version == 1
        assert config.provider.name == "mock"
        # Check defaults
        assert config.provider.model == "gpt-4o"
        assert config.provider.temperature == 0.0
        assert isinstance(config.provider.max_tokens, int)
        assert config.provider.timeout == 30
        assert config.loop.max_iterations == 5
        assert config.loop.workspace == "."
        assert config.guardrail.enabled is True
        assert config.memory.enabled is True
        assert config.memory.path == "output/memory.json"

    def test_provider_defaults(self) -> None:
        """LLMConfig with only name should fill reasonable defaults."""
        llm = LLMConfig(name="mock")
        assert llm.model == "gpt-4o"
        assert llm.temperature == 0.0
        assert llm.timeout == 30


class TestConfigLoadFromFile:
    """Load YAML file and verify field values."""

    def test_load_from_yaml(self, full_config_dict: dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(full_config_dict, f)
            config_path = f.name

        try:
            config = Config.from_yaml(config_path)
            assert config.provider.name == "openai"
            assert config.provider.model == "gpt-4o"
            assert config.provider.temperature == 0.7
            assert config.provider.max_tokens == 4096
            assert config.provider.timeout == 60
            assert config.loop.max_iterations == 10
            assert config.loop.workspace == "/my/project"
            assert config.guardrail.enabled is True
            assert "rm -rf" in config.guardrail.block_list
            assert config.memory.path == "output/custom_memory.json"
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_load_from_yaml_missing_file(self) -> None:
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("/nonexistent/config.yaml")


class TestConfigCLIOverride:
    """CLI arguments can override config fields."""

    def test_override_provider_name(self, full_config_dict: dict[str, Any]) -> None:
        config = Config.model_validate(full_config_dict)
        overridden = config.with_overrides(provider_name="mock")
        assert overridden.provider.name == "mock"
        # Unchanged fields should stay
        assert overridden.provider.model == "gpt-4o"

    def test_override_provider_model(self, full_config_dict: dict[str, Any]) -> None:
        config = Config.model_validate(full_config_dict)
        overridden = config.with_overrides(provider_model="claude-sonnet-4")
        assert overridden.provider.model == "claude-sonnet-4"
        assert overridden.provider.name == "openai"  # unchanged

    def test_override_both(self, full_config_dict: dict[str, Any]) -> None:
        config = Config.model_validate(full_config_dict)
        overridden = config.with_overrides(
            provider_name="mock",
            provider_model="gpt-4o-mini",
        )
        assert overridden.provider.name == "mock"
        assert overridden.provider.model == "gpt-4o-mini"

    def test_override_no_changes(self, full_config_dict: dict[str, Any]) -> None:
        """with_overrides with no args returns the same config."""
        config = Config.model_validate(full_config_dict)
        overridden = config.with_overrides()
        assert overridden.provider.name == config.provider.name
        assert overridden.provider.model == config.provider.model


class TestConfigSerialization:
    def test_roundtrip(self, full_config_dict: dict[str, Any]) -> None:
        config = Config.model_validate(full_config_dict)
        data = json.loads(config.model_dump_json())
        restored = Config.model_validate(data)
        assert restored.provider.name == config.provider.name
        assert restored.loop.max_iterations == config.loop.max_iterations
        assert restored.guardrail.block_list == config.guardrail.block_list