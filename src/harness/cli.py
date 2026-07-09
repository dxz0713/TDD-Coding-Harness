"""CLI entry point for TDD Coding Harness (T3).

Supports ``run`` (the main coding-task command) and ``demo`` (placeholder
for mechanism demonstrations).
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import datetime
import logging
from pathlib import Path
from typing import Iterator

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
LOG_FORMAT = "  [%(levelname)s] %(message)s"

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


def _slugify_task(task: str) -> str:
    """Create a readable filesystem name from a task description."""
    lowered = task.lower()
    if "斐波那契" in task or "fibonacci" in lowered or "fib" in lowered:
        return "fib"
    if any(term in task for term in ("最大公约数", "最大公因数", "最大公因子")):
        return "gcd"
    if "gcd" in lowered:
        return "gcd"

    words = re.findall(r"[a-zA-Z0-9]+", lowered)
    slug = "-".join(words[:6])
    return (slug[:48].strip("-_") or "run")


def _create_run_directory(workspace: Path, task: str) -> Path:
    """Create a unique per-run directory inside the configured workspace."""
    workspace.mkdir(parents=True, exist_ok=True)
    slug = _slugify_task(task)
    candidate = workspace / slug
    if not candidate.exists():
        candidate.mkdir()
        return candidate

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for index in range(1, 100):
        suffix = timestamp if index == 1 else f"{timestamp}-{index}"
        candidate = workspace / f"{slug}-{suffix}"
        if not candidate.exists():
            candidate.mkdir()
            return candidate

    raise RuntimeError(f"Unable to create unique run directory in {workspace}")


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    """Temporarily execute relative file and shell operations from *path*."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _append_log(log_path: Path, message: str = "") -> None:
    """Append a console line to the run log."""
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _echo_and_log(log_path: Path, message: str = "", err: bool = False) -> None:
    """Echo a CLI line and persist it in log.txt."""
    typer.echo(message, err=err)
    _append_log(log_path, message)


def _add_file_log_handler(log_path: Path) -> logging.Handler:
    """Attach a file handler so harness iteration logs go into log.txt."""
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(handler)
    return handler


def _remove_file_log_handler(handler: logging.Handler) -> None:
    """Detach and close a temporary file log handler."""
    root_logger = logging.getLogger()
    root_logger.removeHandler(handler)
    handler.close()


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

    workspace_root = Path(cfg.loop.workspace).expanduser()
    run_dir = _create_run_directory(workspace_root, task)
    log_path = run_dir / "log.txt"
    file_log_handler = _add_file_log_handler(log_path)
    cfg.loop.workspace = str(run_dir)

    config_path = Path(config)
    memory_path = Path(cfg.memory.path)
    if not memory_path.is_absolute():
        memory_path = Path.cwd() / memory_path

    _echo_and_log(log_path, f"  Provider: {cfg.provider.name}")
    _echo_and_log(log_path, f"  Model:    {cfg.provider.model}")
    _echo_and_log(log_path, f"  Config:   {config_path}")
    _echo_and_log(log_path, f"  Workspace: {run_dir}")

    # ── 2. Create provider ─────────────────────────────────────────────
    try:
        provider_instance = ProviderFactory.create(cfg.provider)
    except Exception as exc:
        _echo_and_log(log_path, f"Error: {exc}", err=True)
        _remove_file_log_handler(file_log_handler)
        raise typer.Exit(code=1) from exc

    # ── 3. Build harness dependencies ──────────────────────────────────
    dispatcher = _build_workspace_dispatcher(run_dir)
    guardrail = Guardrail(cfg.guardrail)
    context_manager = ContextManager()
    stop_decision = AutonomousStopDecision(guardrail, cfg.loop)
    feedback_engine = FeedbackEngine()
    memory_store = MemoryStore(str(memory_path)) if cfg.memory.enabled else None

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

    try:
        with _working_directory(run_dir):
            result = loop.run(task, _BUILTIN_TOOL_DEFS)
    finally:
        _remove_file_log_handler(file_log_handler)

    # ── 5. Print result ────────────────────────────────────────────────
    _echo_and_log(log_path)
    _echo_and_log(log_path, "=" * 60)
    if result.success:
        _echo_and_log(log_path, "  SUCCESS - All tests passed")
    else:
        _echo_and_log(log_path, f"  FAILURE - {result.error or 'Unknown error'}")
    _echo_and_log(log_path, f"  Iterations: {result.iterations}")
    _echo_and_log(log_path, f"  Workspace: {run_dir}")
    _echo_and_log(log_path, f"  Log:        {log_path}")
    _echo_and_log(log_path, "=" * 60)

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
