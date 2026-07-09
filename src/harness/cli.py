"""CLI entry point for TDD Coding Harness (T3).

Supports ``run`` (the main coding-task command) and ``demo`` (placeholder
for mechanism demonstrations).
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from harness.config import Config
from harness.context import ContextManager
from harness.guardrail import Guardrail
from harness.loop import HarnessLoop
from harness.memory import MemoryStore
from harness.models import ToolDef
from harness.stop_condition import AutonomousStopDecision
from feedback.engine import FeedbackEngine
from providers.factory import ProviderFactory
from tools.read_file import ReadFile
from tools.dispatcher import ToolDispatcher
from tools.run_shell import RunShell
from tools.write_file import WriteFile

# Import harness package to trigger built-in provider registration
import harness  # noqa: F401

app = typer.Typer(help="TDD Coding Harness - CLI")

# Enable harness logging so iteration progress is visible.
logging.basicConfig(
    level=logging.INFO,
    format="  [%(levelname)s] %(message)s",
    force=True,
)

DEFAULT_CONFIG = "config.yaml"

# Built-in tool definitions exposed to the LLM.
_BUILTIN_TOOL_DEFS: list[ToolDef] = [
    ToolDef(
        name=ReadFile.name,
        description=ReadFile.description,
        parameters=ReadFile.input_schema,
    ),
    ToolDef(
        name=WriteFile.name,
        description=WriteFile.description,
        parameters=WriteFile.input_schema,
    ),
    ToolDef(
        name=RunShell.name,
        description=RunShell.description,
        parameters=RunShell.input_schema,
    ),
]


def _build_workspace_dispatcher(workspace: Path) -> ToolDispatcher:
    """Create tools scoped to the configured workspace."""
    allowed_root = workspace.resolve()
    dispatcher = ToolDispatcher()
    dispatcher.register(ReadFile(allowed_root=allowed_root))
    dispatcher.register(WriteFile(allowed_root=allowed_root))
    dispatcher.register(RunShell())
    return dispatcher


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """TDD Coding Harness - AI-Enabled Software Engineer Bootcamp Final Project."""
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
    """Run a coding task with the TDD Harness.

    The harness orchestrates an LLM-powered TDD loop:

        task -> LLM writes code -> run tests -> analyse feedback
                                                 |
                    LLM fixes code <-- repair prompt

    Examples::

        # Use the mock provider (no real LLM):
        tdd-harness run "Implement a Fibonacci function" --provider mock

        # Use OpenAI with the model from config.yaml:
        tdd-harness run "Write a sorting algorithm" --provider openai

        # Override both provider and model:
        tdd-harness run "Add input validation" -p openai -m gpt-4o
    """
    # ── 1. Load configuration ──────────────────────────────────────────
    try:
        cfg = Config.from_yaml(config)
    except FileNotFoundError:
        typer.echo(f"Error: config file not found: {config}", err=True)
        raise typer.Exit(code=1)

    cfg = cfg.with_overrides(provider_name=provider, provider_model=model)

    typer.echo(f"  Provider: {cfg.provider.name}")
    typer.echo(f"  Model:    {cfg.provider.model}")
    typer.echo(f"  Config:   {config}")

    # ── 2. Create provider ─────────────────────────────────────────────
    try:
        provider_instance = ProviderFactory.create(cfg.provider)
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # ── 3. Build harness dependencies ──────────────────────────────────
    dispatcher = _build_workspace_dispatcher(Path(cfg.loop.workspace))
    guardrail = Guardrail(cfg.guardrail)
    context_manager = ContextManager()
    stop_decision = AutonomousStopDecision(guardrail, cfg.loop)
    feedback_engine = FeedbackEngine()
    memory_store = MemoryStore(cfg.memory.path) if cfg.memory.enabled else None

    # ── 4. Run the TDD loop ────────────────────────────────────────────
    loop = HarnessLoop(
        provider=provider_instance,
        dispatcher=dispatcher,
        guardrail=guardrail,
        context_manager=context_manager,
        stop_decision=stop_decision,
        feedback_engine=feedback_engine,
        memory_store=memory_store,
        config=cfg,
    )

    result = loop.run(task, _BUILTIN_TOOL_DEFS)

    # ── 5. Print result ────────────────────────────────────────────────
    typer.echo()
    typer.echo("=" * 60)
    if result.success:
        typer.echo("  SUCCESS - All tests passed")
    else:
        typer.echo(f"  FAILURE - {result.error or 'Unknown error'}")
    typer.echo(f"  Iterations: {result.iterations}")
    typer.echo("=" * 60)

    if not result.success:
        raise typer.Exit(code=1)


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
