"""Data models for TDD Coding Harness (SPEC §6).

All core entities are defined as Pydantic v2 models for type safety,
serialization, and validation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════════
# LLM Layer
# ═══════════════════════════════════════════════════════════════════

class Message(BaseModel):
    """A single message in the LLM conversation history."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None


class ToolDef(BaseModel):
    """Definition of a tool that the LLM can call."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class ToolCall(BaseModel):
    """A tool invocation request from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    """Structured response from an LLM provider."""

    content: str
    tool_calls: list[ToolCall] = []
    finish_reason: str = "stop"  # "stop" | "tool_calls" | "error"


# ═══════════════════════════════════════════════════════════════════
# Tool Layer
# ═══════════════════════════════════════════════════════════════════

class ToolResult(BaseModel):
    """Unified result structure returned by every tool."""

    success: bool
    output: str = ""
    error: str | None = None
    exit_code: int | None = None
    artifact: str | None = None
    metadata: dict[str, Any] = {}


# ═══════════════════════════════════════════════════════════════════
# Feedback Layer
# ═══════════════════════════════════════════════════════════════════

class FailureType(str, Enum):
    """Categorised failure types detectable by the Feedback Engine."""

    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    ASSERTION_ERROR = "assertion_error"
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    UNKNOWN = "unknown"


class AnalysisResult(BaseModel):
    """Structured output from the FailureAnalyzer."""

    failure_type: FailureType
    location: str | None = None
    error_message: str = ""
    assertion_expected: str | None = None
    assertion_actual: str | None = None
    raw_snippet: str | None = None


class Feedback(BaseModel):
    """Complete feedback package produced by the Feedback Engine."""

    failure_type: FailureType
    summary: str
    details: AnalysisResult
    repair_prompt: str


# ═══════════════════════════════════════════════════════════════════
# Governance Layer
# ═══════════════════════════════════════════════════════════════════

class GuardrailResult(BaseModel):
    """Result of a guardrail check on a tool call."""

    allowed: bool
    reason: str | None = None


# ═══════════════════════════════════════════════════════════════════
# Memory Layer
# ═══════════════════════════════════════════════════════════════════

class Decision(BaseModel):
    """A historical decision recorded in project memory."""

    timestamp: str
    description: str
    reason: str


class Memory(BaseModel):
    """Cross-session project memory stored as JSON."""

    project_name: str = ""
    project_description: str = ""
    tech_stack: list[str] = []
    decisions: list[Decision] = []
    conventions: list[str] = []


# ═══════════════════════════════════════════════════════════════════
# Runtime Layer
# ═══════════════════════════════════════════════════════════════════

class Context(BaseModel):
    """Accumulated context for the current run."""

    messages: list[Message] = []
    memory: Memory | None = None
    iteration: int = 0
    task: str = ""


class StopDecision(BaseModel):
    """Decision about whether the main loop should stop."""

    should_stop: bool
    success: bool
    reason: str = ""


class RunResult(BaseModel):
    """Final result of a Harness run."""

    success: bool
    artifacts: list[str] = []
    iterations: int = 0
    error: str | None = None