"""WriteFile tool (T8).

Writes content to a file on disk with path-traversal protection
and automatic parent-directory creation.
"""

from __future__ import annotations

from pathlib import Path

from harness.models import ToolResult

from .base import BaseTool

# Project root — used as the allowed base for path resolution.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WriteFile(BaseTool):
    """Tool that writes content to a file on disk.

    By default, access is restricted to files inside the project
    directory.  Pass an explicit *allowed_root* to override this
    (useful for testing with ``tmp_path``).
    """

    name: str = "write_file"
    description: str = "Write content to a file"
    input_schema: dict = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, allowed_root: Path | None = None) -> None:
        """Initialise the tool.

        Args:
            allowed_root: Directory that path traversal checks compare
                against.  Defaults to the project root.
        """
        self._allowed_root: Path = (allowed_root or _PROJECT_ROOT).resolve()

    def execute(self, path: str = "", content: str = "") -> ToolResult:
        """Write *content* to *path*.

        Args:
            path: Filesystem path of the file to write.
            content: Text content to write to the file.

        Returns:
            ``ToolResult(success=True, output=...)`` on success, or
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

        # Auto-create parent directories
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to create parent directories: {exc}",
                exit_code=1,
            )

        # Write the file
        try:
            target.write_text(content, encoding="utf-8")
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to write file: {exc}",
                exit_code=1,
            )

        return ToolResult(
            success=True,
            output=f"Written {len(content)} bytes to {target}",
        )