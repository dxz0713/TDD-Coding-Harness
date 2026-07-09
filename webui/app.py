"""TDD Coding Harness - WebUI (FastAPI)

Provides a browser interface for running harness tasks and viewing
results. Designed to be deployed on Vercel's Python runtime.
"""

from __future__ import annotations

import base64
import html
import io
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from textwrap import dedent

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI(title="TDD Coding Harness WebUI")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_ARTIFACT_FILES = 20
MAX_ARTIFACT_PREVIEW_BYTES = 64 * 1024
EXCLUDED_ARTIFACT_NAMES = {"config.webui.yaml"}
EXCLUDED_ARTIFACT_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
TEXT_ARTIFACT_EXTENSIONS = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Render the main page."""
    return HTMLResponse(_render_page())


@app.post("/run", response_class=HTMLResponse)
async def run_task(
    task: str = Form(...),
    provider: str = Form("mock"),
    base_url: str = Form("https://njusehub.info/v1"),
    model: str = Form("deepseek-v4-pro"),
    api_key: str = Form(""),
) -> HTMLResponse:
    """Execute a harness task and show the output."""
    artifacts: list[dict[str, object]] = []
    artifact_zip_b64 = ""
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

            if provider == "mock":
                command = [
                    sys.executable,
                    str(PROJECT_ROOT / "examples" / "demo_autonomous_repair.py"),
                ]
                output_prefix = (
                    "Mock mode selected: running deterministic offline TDD "
                    "repair demo.\n"
                    f"Submitted task: {task}\n\n"
                )
            else:
                if api_key.strip():
                    env["OPENAI_API_KEY"] = api_key.strip()

                runtime_config = Path(tmp) / "config.webui.yaml"
                runtime_config.write_text(
                    dedent(
                        f"""\
                        version: 1

                        provider:
                          name: {provider}
                          model: {model.strip() or "deepseek-v4-pro"}
                          base_url: {base_url.strip() or "https://njusehub.info/v1"}
                          temperature: 0.0
                          max_tokens: 4096
                          timeout: 60

                        loop:
                          max_iterations: 15
                          workspace: {tmp}

                        guardrail:
                          enabled: true
                          block_list: []

                        memory:
                          enabled: false
                          path: output/memory.json
                        """
                    ),
                    encoding="utf-8",
                )
                command = [
                    sys.executable,
                    "-m",
                    "harness.cli",
                    "run",
                    task,
                    "--provider",
                    provider,
                    "--model",
                    model.strip() or "deepseek-v4-pro",
                    "--config",
                    str(runtime_config),
                ]
                output_prefix = (
                    "Real API mode selected.\n"
                    f"Base URL: {base_url.strip() or 'https://njusehub.info/v1'}\n"
                    f"Model: {model.strip() or 'deepseek-v4-pro'}\n"
                    f"API key provided: {'yes' if api_key.strip() else 'no'}\n\n"
                )

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=tmp,
                env=env,
                timeout=60,
            )
            output = output_prefix + result.stdout + "\n" + result.stderr
            artifacts, artifact_zip_b64 = _collect_artifacts(Path(tmp))
    except Exception as exc:
        output = f"WebUI execution error: {exc}"

    return HTMLResponse(
        _render_page(
            output=output,
            task=task,
            provider=provider,
            base_url=base_url,
            model=model,
            artifacts=artifacts,
            artifact_zip_b64=artifact_zip_b64,
        )
    )


def _collect_artifacts(workspace: Path) -> tuple[list[dict[str, object]], str]:
    """Collect generated workspace files before Vercel removes the temp dir."""
    artifacts: list[dict[str, object]] = []
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if len(artifacts) >= MAX_ARTIFACT_FILES:
                break
            if not path.is_file():
                continue

            rel_path = path.relative_to(workspace)
            rel_parts = rel_path.parts
            rel_name = rel_path.as_posix()
            if path.name in EXCLUDED_ARTIFACT_NAMES:
                continue
            if any(part in EXCLUDED_ARTIFACT_DIRS for part in rel_parts):
                continue

            try:
                data = path.read_bytes()
            except OSError:
                continue

            archive.writestr(rel_name, data)
            artifact: dict[str, object] = {
                "path": rel_name,
                "size": len(data),
                "binary": not _looks_like_text(path, data),
                "truncated": len(data) > MAX_ARTIFACT_PREVIEW_BYTES,
            }
            if artifact["binary"]:
                artifact["content"] = ""
            else:
                artifact["content"] = data[:MAX_ARTIFACT_PREVIEW_BYTES].decode(
                    "utf-8",
                    errors="replace",
                )
            artifacts.append(artifact)

    if not artifacts:
        return [], ""

    return artifacts, base64.b64encode(zip_buffer.getvalue()).decode("ascii")


def _looks_like_text(path: Path, data: bytes) -> bool:
    """Return True for source-like files that can be previewed inline."""
    if path.suffix.lower() in TEXT_ARTIFACT_EXTENSIONS:
        return True
    if b"\x00" in data[:1024]:
        return False
    try:
        data[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _render_page(
    output: str | None = None,
    task: str = "",
    provider: str = "mock",
    base_url: str = "https://njusehub.info/v1",
    model: str = "deepseek-v4-pro",
    artifacts: list[dict[str, object]] | None = None,
    artifact_zip_b64: str = "",
) -> str:
    """Render a small self-contained HTML page.

    Keeping the HTML inline avoids template-file bundling ambiguity in Vercel's
    Python function packaging.
    """
    escaped_task = html.escape(task)
    escaped_base_url = html.escape(base_url)
    escaped_model = html.escape(model)
    escaped_output = html.escape(output) if output else ""
    mock_selected = "selected" if provider == "mock" else ""
    openai_selected = "selected" if provider == "openai" else ""
    output_block = (
        f"<h2>Output</h2><pre>{escaped_output}</pre>" if output else ""
    )
    artifacts_block = _render_artifacts(artifacts or [], artifact_zip_b64)

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
        input, select {{ width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }}
        label {{ display: block; margin-top: 1rem; font-weight: 600; }}
        button {{ padding: 0.5rem 2rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #0055aa; }}
        a.download {{ display: inline-block; margin: 0.5rem 0 1rem; color: #0066cc; font-weight: 600; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
        .artifact {{ margin: 1rem 0; }}
        .artifact-name {{ font-weight: 700; }}
        .artifact-meta {{ color: #666; font-size: 0.85rem; }}
        .info {{ color: #666; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>TDD Coding Harness</h1>
    <p class="info">Enter a coding task below and let the harness generate, test, and fix code automatically.</p>
    <form method="post" action="/run">
        <label>Task:
        <textarea name="task" placeholder="e.g., 编写一个计算斐波那契数列的函数">{escaped_task}</textarea>
        </label>
        <label>Provider:
            <select name="provider">
                <option value="mock" {mock_selected}>Mock (offline)</option>
                <option value="openai" {openai_selected}>OpenAI-compatible</option>
            </select>
        </label>
        <label>Base URL:
            <input name="base_url" type="url" value="{escaped_base_url}" placeholder="https://njusehub.info/v1">
        </label>
        <label>Model:
            <input name="model" type="text" value="{escaped_model}" placeholder="deepseek-v4-pro">
        </label>
        <label>API Key (real API mode only, not stored):
            <input name="api_key" type="password" placeholder="Enter API key for this request only" autocomplete="off">
        </label>
        <br>
        <button type="submit">Run</button>
    </form>
    {output_block}
    {artifacts_block}
</body>
</html>"""


def _render_artifacts(
    artifacts: list[dict[str, object]],
    artifact_zip_b64: str,
) -> str:
    """Render collected generated files."""
    if not artifacts:
        return ""

    download_link = (
        '<a class="download" download="tdd-harness-artifacts.zip" '
        f'href="data:application/zip;base64,{artifact_zip_b64}">'
        "Download artifacts.zip</a>"
        if artifact_zip_b64
        else ""
    )
    blocks = []
    for artifact in artifacts:
        path = html.escape(str(artifact["path"]))
        size = int(artifact["size"])
        truncated = " preview truncated" if artifact["truncated"] else ""
        if artifact["binary"]:
            body = "<pre>Binary file included in zip download.</pre>"
        else:
            content = html.escape(str(artifact.get("content", "")))
            body = f"<pre>{content}</pre>"
        blocks.append(
            '<div class="artifact">'
            f'<div class="artifact-name">{path}</div>'
            f'<div class="artifact-meta">{size} bytes{truncated}</div>'
            f"{body}"
            "</div>"
        )

    return f"<h2>Artifacts</h2>{download_link}{''.join(blocks)}"
