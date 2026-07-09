"""TDD Coding Harness - WebUI (FastAPI)

Provides a browser interface for running harness tasks and viewing
results. Designed to be deployed on Vercel's Python runtime.
"""

from __future__ import annotations

import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI(title="TDD Coding Harness WebUI")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Render the main page."""
    return HTMLResponse(_render_page())


@app.post("/run", response_class=HTMLResponse)
async def run_task(
    task: str = Form(...),
    provider: str = Form("mock"),
) -> HTMLResponse:
    """Execute a harness task and show the output."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            pythonpath_parts = [str(PROJECT_ROOT / "src")]
            pythonpath_parts.extend(path for path in sys.path if path)
            existing_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                os.pathsep.join(pythonpath_parts)
                if not existing_pythonpath
                else os.pathsep.join([*pythonpath_parts, existing_pythonpath])
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "harness.cli",
                    "run",
                    task,
                    "--provider",
                    provider,
                    "--config",
                    str(PROJECT_ROOT / "config.yaml"),
                ],
                capture_output=True,
                text=True,
                cwd=tmp,
                env=env,
                timeout=60,
            )
            output = result.stdout + "\n" + result.stderr
    except Exception as exc:
        output = f"WebUI execution error: {exc}"

    return HTMLResponse(_render_page(output=output, task=task, provider=provider))


def _render_page(
    output: str | None = None,
    task: str = "",
    provider: str = "mock",
) -> str:
    """Render a small self-contained HTML page.

    Keeping the HTML inline avoids template-file bundling ambiguity in Vercel's
    Python function packaging.
    """
    escaped_task = html.escape(task)
    escaped_output = html.escape(output) if output else ""
    mock_selected = "selected" if provider == "mock" else ""
    openai_selected = "selected" if provider == "openai" else ""
    output_block = (
        f"<h2>Output</h2><pre>{escaped_output}</pre>" if output else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDD Coding Harness</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        textarea {{ width: 100%; min-height: 100px; padding: 0.5rem; font-family: monospace; }}
        button {{ padding: 0.5rem 2rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #0055aa; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
        .info {{ color: #666; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>TDD Coding Harness</h1>
    <p class="info">Enter a coding task below and let the harness generate, test, and fix code automatically.</p>
    <form method="post" action="/run">
        <textarea name="task" placeholder="e.g., 编写一个计算斐波那契数列的函数">{escaped_task}</textarea>
        <br><br>
        <label>Provider:
            <select name="provider">
                <option value="mock" {mock_selected}>Mock (offline)</option>
                <option value="openai" {openai_selected}>OpenAI-compatible</option>
            </select>
        </label>
        <br><br>
        <button type="submit">Run</button>
    </form>
    {output_block}
</body>
</html>"""
