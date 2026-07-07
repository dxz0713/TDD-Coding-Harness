"""ReadFile tool (T7).

Reads a file from disk with path-traversal protection.
"""

from __future__ import annotations

from pathlib import Path

from harness.models import ToolResult

from .base import BaseTool

# Project root — used as the allowed base for path resolution.
# This is two levels up from tools/read_file.py → src/tools/read_file.py.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ReadFile(BaseTool):
    """Tool that reads a file from disk.

    By default, access is restricted to files inside the project
    directory.  Pass an explicit *allowed_root* to override this
    (useful for testing with ``tmp_path``).
    """

    name: str = "read_file"
    description: str = "Read a file from disk"
    input_schema: dict = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
        },
        "required": ["path"],
    }

    def __init__(self, allowed_root: Path | None = None) -> None:
        """Initialise the tool.

        Args:
            allowed_root: Directory that path traversal checks compare
                against.  Defaults to the project root.
        """
        self._allowed_root: Path = (allowed_root or _PROJECT_ROOT).resolve()

    def execute(self, path: str = "") -> ToolResult:
        """Read the file at *path* and return its contents.

        Args:
            path: Filesystem path to the file (relative or absolute).

        Returns:
            ``ToolResult(success=True, output=content)`` on success, or
            ``ToolResult(success=False, error=...)`` on failure.
        """
        if not path:
            return ToolResult(success=False, error="path is required", exit_code=1)

        # Resolve the target path and check for traversal
        target = Path(path).resolve()

        try:
            target.relative_to(self._allowed_root)
        except ValueError:
            return ToolResult(
                success=False,
                error=f"Path traversal denied: {path} is outside the allowed directory",
                exit_code=1,
            )

        if not target.exists():
            return ToolResult(
                success=False,
                error=f"File not found: {target}",
                exit_code=1,
            )

        if not target.is_file():
            return ToolResult(
                success=False,
                error=f"Path is not a file: {target}",
                exit_code=1,
            )

        try:
            content = target.read_text(encoding="utf-8")
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to read file: {exc}",
                exit_code=1,
            )

        return ToolResult(success=True, output=content)