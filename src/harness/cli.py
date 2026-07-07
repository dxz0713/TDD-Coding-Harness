"""Minimal CLI stub — placeholder for T3 implementation."""

import typer

app = typer.Typer(help="TDD Coding Harness — CLI")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
) -> None:
    """TDD Coding Harness — AI-Enabled Software Engineer Bootcamp Final Project."""
    if ctx.invoked_subcommand is None:
        typer.echo(app.get_help_text())


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description for the coding agent"),
) -> None:
    """Run a coding task with the TDD Harness."""
    typer.echo(f"TDD Harness: run not yet implemented (task: {task})")


@app.command()
def demo(
    feature: str = typer.Argument("all", help="Feature to demo: guardrail, feedback, memory"),
) -> None:
    """Run a mechanism demo."""
    typer.echo(f"TDD Harness: demo not yet implemented (feature: {feature})")


if __name__ == "__main__":
    app()