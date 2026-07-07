"""Guardrail — dangerous command interception (T10).

Intercepts RunShell tool calls before execution and blocks commands
that match dangerous patterns (rm -rf /, fork bombs, etc.) or
user-configured block-list entries.
"""

from __future__ import annotations

import re

from harness.config import GuardrailConfig
from harness.models import GuardrailResult, ToolCall

# ═══════════════════════════════════════════════════════════════════
# Built-in dangerous patterns
# ═══════════════════════════════════════════════════════════════════

# Commands that are always safe to run — checked first, before any
# dangerous-pattern matching.
_SAFE_COMMANDS: set[str] = {
    "pytest",
    "echo",
    "python",
    "python3",
    "pip",
    "pip3",
    "ls",
    "cat",
    "cd",
    "mkdir",
    "touch",
    "cp",
    "mv",
    "which",
    "head",
    "tail",
    "wc",
    "sort",
    "grep",
    "find",
    "diff",
    "git",
    "make",
    "npm",
    "node",
    "cargo",
    "go",
    "rustc",
}

# Patterns that are always dangerous, regardless of context.
_DANGEROUS_PATTERNS: list[re.Pattern] = [
    # Recursive root deletion
    re.compile(r"\brm\s+(-rf|--recursive)\s+/\s*(\s|$|#)"),
    re.compile(r"\brm\s+(-rf|--recursive)\s+/\*\s*(\s|$|#)"),
    # Direct disk write
    re.compile(r"\bdd\s+if="),
    # Destructive SQL
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+DATABASE\b", re.IGNORECASE),
    # Fork bomb
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}"),
    # Block device write
    re.compile(r">\s*/dev/sda"),
    # Network download and execute
    re.compile(r"\bcurl\b.*\|\s*(bash|sh)\b"),
    re.compile(r"\bwget\b.*\|\s*(bash|sh)\b"),
    # Sensitive directory writes
    re.compile(r"~[/\\]\.ssh[/\\]"),
    re.compile(r"~[/\\]\.config[/\\]"),
]


class Guardrail:
    """Governance guardrail that intercepts dangerous tool calls.

    The guardrail only inspects ``RunShell`` (``tool_call.name == "run_shell"``)
    calls. All other tool types are allowed through unconditionally.
    """

    def __init__(self, config: GuardrailConfig) -> None:
        """Initialize the guardrail with the given configuration.

        Args:
            config: Guardrail configuration (enabled flag and custom block-list).
        """
        self._config = config

    # ── Public API ──────────────────────────────────────────────────

    def check_tool_call(self, tool_call: ToolCall) -> GuardrailResult:
        """Check whether a tool call should be allowed.

        Args:
            tool_call: The tool call from the LLM.

        Returns:
            GuardrailResult with ``allowed=True`` if the call is safe,
            ``allowed=False`` with a reason if it is blocked.
        """
        # Guardrail disabled — everything passes
        if not self._config.enabled:
            return GuardrailResult(allowed=True)

        # Only intercept RunShell calls
        if tool_call.name != "run_shell":
            return GuardrailResult(allowed=True)

        command: str = tool_call.arguments.get("command", "")

        if not command:
            return GuardrailResult(allowed=True)

        # Check user-configured block-list FIRST (before safe-command bypass)
        for pattern in self._config.block_list:
            if pattern in command:
                return GuardrailResult(
                    allowed=False,
                    reason=f"Command matches config block-list pattern: {pattern}",
                )

        # Check built-in dangerous patterns (before safe-command bypass)
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                return GuardrailResult(
                    allowed=False,
                    reason=f"Command matches dangerous pattern: {pattern.pattern}",
                )

        # Safe commands bypass remaining checks
        first_word = command.strip().split(maxsplit=1)[0] if command.strip() else ""
        if first_word in _SAFE_COMMANDS:
            return GuardrailResult(allowed=True)

        return GuardrailResult(allowed=True)