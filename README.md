# TDD Coding Harness

A teaching-oriented **Coding Agent Harness** that wraps an LLM into a programmable code-execution unit, with a focus on **test-driven feedback cycles**.

> **Course:** AI4SE Final Project — Category A (Coding Agent Harness)
>
> **Primary Contribution:** Feedback Engine (extensible feedback-loop engine)

## Quick Start

### Prerequisites

- Python 3.12+
- pip

### Install

```bash
pip install -e ".[dev]"
```

### Run

```bash
tdd-harness run "编写一个计算斐波那契数列的函数"
```

### Run Tests

```bash
pytest tests/ -v
```

### Docker

```bash
docker build -t tdd-harness .
docker run --rm tdd-harness --help
```

## Architecture

The system follows a linear pipeline architecture with a feedback loop:

```
CLI (typer) → Config (YAML + overrides) → Provider Factory → Main Loop → Tools / Feedback
```

1. **CLI Layer** — `harness/cli.py` uses `typer` to parse user commands (`run`, `demo`). CLI arguments override config-file values.

2. **Configuration Layer** — `harness/config.py` loads `config.yaml` using Pydantic models. Supports deep-merge overrides from CLI flags (`--provider`, `--model`). Priority: CLI arguments > config file > built-in defaults.

3. **Provider Factory** — `providers/factory.py` implements a registry pattern. Providers register themselves by name; the factory creates the correct provider from a config string. Built-in: `MockProvider` (offline testing) and `OpenAICompatibleProvider` (OpenAI / DeepSeek / Qwen compatible APIs).

4. **Main Loop** — `harness/loop.py` (`HarnessLoop`) orchestrates the TDD cycle:
   - Build context → LLM generate → Parse tool calls → Guardrail check → Dispatch tool → Analyze feedback → Update context → Repeat or stop
   - The loop delegates every concern to injected dependencies (provider, dispatcher, guardrail, context manager, stop decision, feedback engine).

5. **Tool Dispatcher** — `tools/dispatcher.py` routes LLM-requested tool calls to registered `BaseTool` implementations. Built-in tools: `ReadFile`, `WriteFile`, `RunShell`. A virtual `finish` tool signals completion.

6. **Guardrail** — `harness/guardrail.py` intercepts dangerous shell commands (`rm -rf /`, fork bombs, etc.) before execution. Supports allowlists, blocklists, and regex-based danger patterns.

7. **Feedback Engine** — `feedback/` package that implements the core contribution:
   - `Collector` — normalises raw test output (strips ANSI, extracts test names)
   - `FailureAnalyzer` — classifies failures into 7 types (SyntaxError, AssertionError, ImportError, RuntimeError, Timeout, TestFailure, Unknown)
   - `RepairStrategy` — per-failure-type repair prompt generation
   - `FeedbackEngine` — connects Collector → Analyzer → Strategy into one pipeline

8. **Context & Memory** — `harness/context.py` builds and tracks conversation context; `harness/memory.py` provides cross-session persistent memory.

## Configuration

The system uses a YAML configuration file (`config.yaml` by default) with Pydantic-based validation.

```yaml
# config.yaml — Default configuration
version: 1

provider:
  name: mock          # mock | openai
  model: gpt-4o
  base_url: https://api.openai.com/v1
  temperature: 0.0
  max_tokens: 4096
  timeout: 30

loop:
  max_iterations: 5
  workspace: .

guardrail:
  enabled: true
  block_list: []

memory:
  enabled: true
  path: output/memory.json
```

**Configuration priority** (high → low):
1. CLI arguments (`--provider`, `--model`)
2. Config file (`config.yaml`)
3. Built-in defaults (hardcoded in `Config` Pydantic model)

## Provider Switching

Switch between LLM providers by changing the configuration — no code changes needed.

```bash
# Use Mock provider (offline testing, no API key needed)
tdd-harness run "task description" --provider mock

# Use OpenAI-compatible API (OpenAI, DeepSeek, Qwen, etc.)
tdd-harness run "task description" --provider openai --model deepseek-v4-pro

# Use a config file with custom provider settings
tdd-harness run "task description" --config my-config.yaml
```

When using the `openai` provider, set your API key via the `OPENAI_API_KEY` environment variable (or a `.env` file).

## Demo

Three demonstration scripts are included in the `examples/` directory:

```bash
# Guardrail demonstration — shows dangerous command interception
python examples/demo_guardrail.py

# Feedback classification demonstration — shows 7 failure-type classifications
python examples/demo_feedback.py

# Full TDD autonomous repair cycle — MockProvider-based end-to-end demo
python examples/demo_autonomous_repair.py
```

## Project Structure

```
├── src/
│   ├── cli.py                    # CLI entry point (typer)
│   ├── feedback/                 # Feedback Engine ★ core contribution
│   │   ├── analyzer.py           #   Collector + FailureAnalyzer
│   │   ├── engine.py             #   FeedbackEngine pipeline
│   │   └── strategies.py         #   Per-failure-type repair strategies
│   ├── harness/                  # Core harness runtime
│   │   ├── cli.py                #   CLI commands (run, demo)
│   │   ├── config.py             #   YAML config + Pydantic models
│   │   ├── context.py            #   Conversation context manager
│   │   ├── guardrail.py          #   Dangerous command interception
│   │   ├── loop.py               #   Main TDD orchestration loop
│   │   ├── memory.py             #   Cross-session memory store
│   │   ├── models.py             #   Shared Pydantic data models
│   │   └── stop_condition.py     #   Autonomous stop decision logic
│   ├── providers/                # LLM provider abstraction
│   │   ├── base.py               #   Abstract LLMProvider base class
│   │   ├── factory.py            #   Registry-based provider factory
│   │   ├── mock.py               #   Mock provider (offline testing)
│   │   └── openai_compat.py      #   OpenAI-compatible API provider
│   ├── tests/                    # Unit tests (210+ tests)
│   │   ├── test_analyzer.py
│   │   ├── test_cli.py
│   │   ├── test_config.py
│   │   ├── test_context.py
│   │   ├── test_feedback_engine.py
│   │   ├── test_guardrail.py
│   │   ├── test_loop.py
│   │   ├── test_loop_integration.py
│   │   ├── test_memory.py
│   │   ├── test_models.py
│   │   ├── test_providers.py
│   │   ├── test_stop_condition.py
│   │   └── test_tools.py
│   └── tools/                    # Tool implementations
│       ├── base.py               #   BaseTool abstract class
│       ├── dispatcher.py         #   Tool call dispatcher
│       ├── read_file.py          #   Read file tool
│       ├── run_shell.py          #   Shell command tool
│       └── write_file.py         #   Write file tool
├── examples/                     # Demo scripts
│   ├── demo_guardrail.py
│   ├── demo_feedback.py
│   └── demo_autonomous_repair.py
├── docs/                         # Specification and planning
│   ├── SPEC.md
│   ├── SPEC_PROCESS.md
│   └── PLAN.md
├── config.yaml                   # Default configuration
├── Dockerfile                    # Container build
├── pyproject.toml                # Project metadata and dependencies
└── README.md                     # This file
```

## Design Decisions

### Why not LangGraph / CrewAI / AutoGen?

This project intentionally implements its own Harness Loop, Provider abstraction, Tool Dispatcher, Feedback Engine, and Guardrail — instead of using existing orchestration frameworks. This is a **course requirement** (AI4SE Category A): the harness kernel must be self-implemented code, not a configuration layer on top of an existing agent framework. The goal is to demonstrate understanding of the engineering underneath these tools, not to build on top of them.

### Why not a GUI?

The project is scoped as a CLI tool for developers. A GUI or IDE plugin is explicitly out of scope for the MVP.

## Security

- **API Keys** are configured via the `OPENAI_API_KEY` environment variable (or `.env` file). They are **never hardcoded** in source code.
- The `.env` file is excluded by `.gitignore` to prevent accidental credential leaks.
- The **Guardrail** module (`harness/guardrail.py`) intercepts dangerous shell commands (`rm -rf /`, fork bombs, etc.) before execution. Users can extend the blocklist via `config.yaml`.
- Built-in safe command allowlist ensures common development commands (`pytest`, `python`, `pip`, `ls`, `git`, etc.) are always permitted.

## Known Issues / Limitations

- **Provider support** — Currently supports only OpenAI-compatible APIs (OpenAI, DeepSeek, Qwen, etc.). Anthropic Claude provider is reserved for future implementation.
- **Test framework** — The default test framework is pytest. Other frameworks (unittest, doctest) are not explicitly handled by the FailureAnalyzer.
- **Cross-platform** — Windows and Linux shell command differences may affect the `RunShell` tool (e.g., path separators, environment variables).
- **No GUI / IDE plugin** — The harness is CLI-only. No VS Code extension, JetBrains plugin, or web UI is provided.
- **Memory persistence** — Cross-session memory is file-based (JSON). For production use, a database-backed store would be more appropriate.