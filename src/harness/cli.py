"""CLI entry point for TDD Coding Harness (T3).

Supports ``run`` (the main coding-task command) and ``demo`` (placeholder
for mechanism demonstrations).
"""

from __future__ import annotations

from pathlib import Path

import typer

from harness.config import Config

app = typer.Typer(help="TDD Coding Harness — CLI")

DEFAULT_CONFIG = "config.yaml"


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """TDD Coding Harness — AI-Enabled Software Engineer Bootcamp Final Project."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description for the coding agent"),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        "-c",
        help="Path to YAML configuration file",
        exists=False,
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Override provider name (mock | openai)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override provider model name",
    ),
) -> None:
    """Run a coding task with the TDD Harness."""
    # Load configuration
    cfg = Config.from_yaml(config)
    cfg = cfg.with_overrides(provider_name=provider, provider_model=model)

    typer.echo(f"TDD Harness: run not yet implemented (task: {task})")
    typer.echo(f"  Provider: {cfg.provider.name}")
    typer.echo(f"  Model:    {cfg.provider.model}")
    typer.echo(f"  Config:   {config}")


@app.command()
def demo(
    feature: str = typer.Argument(
        "all", help="Feature to demo: guardrail, feedback, memory"
    ),
) -> None:
    """Run a mechanism demo."""
    typer.echo(f"TDD Harness: demo not yet implemented (feature: {feature})")


if __name__ == "__main__":
    app()