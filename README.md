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

## Design Decisions

### Why not LangGraph / CrewAI / AutoGen?

This project intentionally implements its own Harness Loop, Provider abstraction, Tool Dispatcher, Feedback Engine, and Guardrail — instead of using existing orchestration frameworks. This is a **course requirement** (AI4SE Category A): the harness kernel must be self-implemented code, not a configuration layer on top of an existing agent framework. The goal is to demonstrate understanding of the engineering underneath these tools, not to build on top of them.

### Why not a GUI?

The project is scoped as a CLI tool for developers. A GUI or IDE plugin is explicitly out of scope for the MVP.

```
├── src/
│   ├── cli.py              # CLI entry point
│   ├── harness/            # Core harness (loop, guardrail, memory, config)
│   ├── tools/              # Tool implementations (ReadFile, WriteFile, RunShell)
│   ├── providers/          # LLM provider abstraction (Mock, OpenAI, Claude)
│   ├── feedback/           # Feedback Engine (collector, analyzer, strategies)
│   └── tests/              # Unit tests
├── docs/                   # SPEC, PLAN, process documents
├── output/                 # Run artifacts and logs
├── Dockerfile
└── pyproject.toml
```