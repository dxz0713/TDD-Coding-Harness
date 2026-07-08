"""Tests for CLI entry point (T3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from harness.cli import app

runner = CliRunner()


class TestRunCommand:
    """Tests for the ``run`` subcommand."""

    def test_run_help(self) -> None:
        """--help should display usage information."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout
        assert "TASK" in result.stdout  # positional argument placeholder

    def test_run_with_provider_override(self) -> None:
        """--provider should be reflected in the output."""
        result = runner.invoke(
            app,
            ["run", "write a test", "--provider", "mock"],
        )
        # Mock provider returns empty response → harness exits with 1
        assert "Provider: mock" in result.stdout

    def test_run_with_model_override(self) -> None:
        """--model should be reflected in the output."""
        result = runner.invoke(
            app,
            ["run", "write a test", "--model", "gpt-4o-mini"],
        )
        # Provider reads from config.yaml (openai) + model override
        assert "gpt-4o-mini" in result.stdout

    def test_run_with_provider_and_model(self) -> None:
        """Both --provider and --model can be used together."""
        result = runner.invoke(
            app,
            [
                "run",
                "refactor this",
                "--provider",
                "openai",
                "--model",
                "gpt-4o",
            ],
        )
        assert "Provider: openai" in result.stdout
        assert "gpt-4o" in result.stdout

    def test_run_with_config(self) -> None:
        """--config loads a YAML file and displays its path."""
        config_data = {
            "version": 1,
            "provider": {"name": "openai", "model": "gpt-4-turbo"},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                ["run", "test task", "--config", config_path],
            )
            assert f"Config:   {config_path}" in result.stdout
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_run_with_config_and_override(self) -> None:
        """CLI overrides take priority over YAML values."""
        config_data = {
            "version": 1,
            "provider": {"name": "openai", "model": "gpt-4-turbo"},
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            result = runner.invoke(
                app,
                [
                    "run",
                    "test task",
                    "--config",
                    config_path,
                    "--provider",
                    "mock",
                ],
            )
            # Override takes precedence
            assert "Provider: mock" in result.stdout
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_run_config_file_not_found(self) -> None:
        """A missing config file should raise FileNotFoundError."""
        result = runner.invoke(
            app,
            ["run", "test task", "--config", "/nonexistent/config.yaml"],
        )
        assert result.exit_code != 0

    def test_run_defaults_to_config_yaml(self) -> None:
        """Without --config, the CLI defaults to 'config.yaml'."""
        # Run from the working directory; if config.yaml exists, it loads.
        result = runner.invoke(app, ["run", "hello"])
        assert "Provider:" in result.stdout


class TestDemoCommand:
    """Tests for the ``demo`` subcommand."""

    def test_demo_help(self) -> None:
        """--help should display usage information."""
        result = runner.invoke(app, ["demo", "--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout

    def test_demo_default(self) -> None:
        """Calling demo without arguments uses 'all' as the default feature."""
        result = runner.invoke(app, ["demo"])
        assert result.exit_code == 0
        assert "feature: all" in result.stdout

    def test_demo_with_feature(self) -> None:
        """Calling demo with a specific feature name."""
        result = runner.invoke(app, ["demo", "guardrail"])
        assert result.exit_code == 0
        assert "feature: guardrail" in result.stdout


class TestMainCallback:
    """Tests for the app callback (no subcommand)."""

    def test_no_subcommand_shows_help(self) -> None:
        """Running ``tdd-harness`` without a subcommand displays the help text."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage" in result.stdout
        # Should list available commands
        assert "run" in result.stdout.lower()
        assert "demo" in result.stdout.lower()