"""RunShell tool (T9).

Executes shell commands with timeout control, working-directory
support, and stdout/stderr capture.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from harness.models import ToolResult

from .base import BaseTool


class RunShell(BaseTool):
    """Tool that executes a shell command."""

    name: str = "run_shell"
    description: str = "Execute a shell command"
    input_schema: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30)",
                "default": 30,
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command (optional)",
                "default": None,
            },
        },
        "required": ["command"],
    }

    def execute(
        self,
        command: str = "",
        timeout: int = 30,
        cwd: str | None = None,
    ) -> ToolResult:
        """Execute *command* in a subprocess.

        Args:
            command: The shell command to run.
            timeout: Maximum execution time in seconds.
            cwd: Working directory (``None`` = current directory).

        Returns:
            ``ToolResult`` with ``output`` (stdout), ``error`` (stderr),
            and ``exit_code`` populated.
        """
        if not command:
            return ToolResult(success=False, error="command is required", exit_code=1)

        # Resolve cwd if provided
        resolved_cwd: str | None = None
        if cwd is not None:
            resolved_cwd = str(Path(cwd).resolve())

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=resolved_cwd,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout}s",
                exit_code=-1,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {exc}",
                exit_code=1,
            )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode

        # Build a combined output string
        output_parts: list[str] = []
        if stdout:
            output_parts.append(stdout)
        if stderr:
            output_parts.append(f"stderr: {stderr}")

        return ToolResult(
            success=exit_code == 0,
            output="\n".join(output_parts),
            error=stderr if exit_code != 0 else None,
            exit_code=exit_code,
        )