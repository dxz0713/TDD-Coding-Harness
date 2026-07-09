"""Tests for CLI entry point (T3)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from harness.cli import app

runner = CliRunner()


def _write_cli_config(
    tmp_path: Path,
    provider: str = "mock",
    model: str = "mock-model",
) -> tuple[Path, Path]:
    """Write a minimal CLI config that uses a temporary workspace."""
    workspace = tmp_path / "workspace"
    config_path = tmp_path / "config.yaml"
    config_data = {
        "version": 1,
        "provider": {"name": provider, "model": model},
        "loop": {"workspace": str(workspace), "max_iterations": 1},
        "memory": {"enabled": False},
    }
    config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    return config_path, workspace


class TestRunCommand:
    """Tests for the ``run`` subcommand."""

    def test_run_help(self) -> None:
        """--help should display usage information."""
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Usage" in result.stdout
        assert "TASK" in result.stdout  # positional argument placeholder

    def test_run_with_provider_override(self, tmp_path: Path) -> None:
        """--provider should be reflected in the output."""
        config_path, _ = _write_cli_config(tmp_path)
        result = runner.invoke(
            app,
            ["run", "write a test", "--config", str(config_path), "--provider", "mock"],
        )
        # Mock provider returns empty response → harness exits with 1
        assert "Provider: mock" in result.stdout

    def test_run_with_model_override(self, tmp_path: Path) -> None:
        """--model should be reflected in the output."""
        config_path, _ = _write_cli_config(tmp_path)
        result = runner.invoke(
            app,
            ["run", "write a test", "--config", str(config_path), "--model", "gpt-4o-mini"],
        )
        # Provider reads from config.yaml (openai) + model override
        assert "gpt-4o-mini" in result.stdout

    def test_run_with_provider_and_model(self, tmp_path: Path) -> None:
        """Both --provider and --model can be used together."""
        config_path, _ = _write_cli_config(tmp_path)
        result = runner.invoke(
            app,
            [
                "run",
                "refactor this",
                "--config",
                str(config_path),
                "--provider",
                "openai",
                "--model",
                "gpt-4o",
            ],
        )
        assert "Provider: openai" in result.stdout
        assert "gpt-4o" in result.stdout

    def test_run_with_config(self, tmp_path: Path) -> None:
        """--config loads a YAML file and displays its path."""
        workspace = tmp_path / "workspace"
        config_path = tmp_path / "config.yaml"
        config_data = {
            "version": 1,
            "provider": {"name": "openai", "model": "gpt-4-turbo"},
            "loop": {"workspace": str(workspace), "max_iterations": 1},
            "memory": {"enabled": False},
        }
        config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app,
            ["run", "test task", "--config", str(config_path)],
        )
        assert f"Config:   {config_path}" in result.stdout

    def test_run_with_config_and_override(self, tmp_path: Path) -> None:
        """CLI overrides take priority over YAML values."""
        workspace = tmp_path / "workspace"
        config_path = tmp_path / "config.yaml"
        config_data = {
            "version": 1,
            "provider": {"name": "openai", "model": "gpt-4-turbo"},
            "loop": {"workspace": str(workspace), "max_iterations": 1},
            "memory": {"enabled": False},
        }
        config_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "run",
                "test task",
                "--config",
                str(config_path),
                "--provider",
                "mock",
            ],
        )
        # Override takes precedence
        assert "Provider: mock" in result.stdout

    def test_run_creates_workspace_run_directory_with_log(self, tmp_path: Path) -> None:
        """Each CLI run gets an isolated workspace folder with log.txt."""
        config_path, workspace = _write_cli_config(tmp_path)

        result = runner.invoke(
            app,
            ["run", "write fibonacci function", "--config", str(config_path)],
        )

        run_dirs = [path for path in workspace.iterdir() if path.is_dir()]
        assert len(run_dirs) == 1
        assert run_dirs[0].name == "fib"
        log_path = run_dirs[0] / "log.txt"
        assert log_path.exists()
        log_text = log_path.read_text(encoding="utf-8")
        assert "Provider: mock" in result.stdout
        assert "Workspace:" in result.stdout
        assert "Provider: mock" in log_text
        assert "Workspace:" in log_text

    def test_run_config_file_not_found(self) -> None:
        """A missing config file should raise FileNotFoundError."""
        result = runner.invoke(
            app,
            ["run", "test task", "--config", "/nonexistent/config.yaml"],
        )
        assert result.exit_code != 0

    def test_run_defaults_to_config_yaml(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without --config, the CLI defaults to 'config.yaml'."""
        _write_cli_config(tmp_path)
        monkeypatch.chdir(tmp_path)
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
