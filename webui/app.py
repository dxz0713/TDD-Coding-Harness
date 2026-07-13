"""TDD Coding Harness - WebUI (FastAPI)

Provides a browser interface for running harness tasks and viewing
results. Designed to be deployed on Vercel's Python runtime.
"""

from __future__ import annotations

import base64
import html
import io
import os
import re
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
DEMO_OPTIONS = {
    "autonomous_repair": {
        "label": "Autonomous repair TDD demo",
        "script": "demo_autonomous_repair.py",
        "task": "Implement a Fibonacci function",
        "success": "SUCCESS - All tests passed",
        "iterations": "7",
    },
    "feedback": {
        "label": "Feedback engine demo",
        "script": "demo_feedback.py",
        "task": "Classify test failures and produce repair feedback",
        "success": "SUCCESS - Feedback demo completed",
        "iterations": "1",
    },
    "guardrail": {
        "label": "Guardrail safety demo",
        "script": "demo_guardrail.py",
        "task": "Block dangerous shell commands and allow safe ones",
        "success": "SUCCESS - Guardrail demo completed",
        "iterations": "1",
    },
}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Render the main page."""
    return HTMLResponse(_render_page())


@app.post("/run", response_class=HTMLResponse)
async def run_task(
    task: str = Form(""),
    provider: str = Form("mock"),
    demo: str = Form("autonomous_repair"),
    base_url: str = Form("https://njusehub.info/v1"),
    model: str = Form("deepseek-v4-pro"),
    api_key: str = Form(""),
) -> HTMLResponse:
    """Execute a harness task and show the output."""
    selected_demo = demo if demo in DEMO_OPTIONS else "autonomous_repair"
    artifacts: list[dict[str, object]] = []
    artifact_zip_b64 = ""
    run_status = "idle"

    if provider != "mock" and not task.strip():
        return HTMLResponse(
            _render_page(
                output="Real API mode requires a task description.",
                task=task,
                provider=provider,
                demo=selected_demo,
                base_url=base_url,
                model=model,
                run_status="failure",
            )
        )

    try:
        with tempfile.TemporaryDirectory() as tmp:
            output_suffix = ""
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
                demo_config = DEMO_OPTIONS[selected_demo]
                command = [
                    sys.executable,
                    str(PROJECT_ROOT / "examples" / str(demo_config["script"])),
                ]
                output_prefix = (
                    "Provider: mock\n"
                    "Model:    deterministic-demo\n"
                    "Config:   fixed offline demo\n"
                    f"Demo:     {demo_config['label']}\n"
                    f"Task:     {demo_config['task']}\n\n"
                )
            else:
                effective_task = task.strip()
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
                    effective_task,
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
            if provider == "mock":
                output_suffix = _render_mock_summary(
                    result.returncode,
                    DEMO_OPTIONS[selected_demo],
                )
            output = output_prefix + result.stdout + "\n" + result.stderr + output_suffix
            output = _redact_sensitive_output(output, api_key)
            run_status = _classify_run_status(result.returncode, output)
            artifacts, artifact_zip_b64 = _collect_artifacts(Path(tmp))
    except Exception as exc:
        output = _redact_sensitive_output(f"WebUI execution error: {exc}", api_key)
        run_status = "failure"

    return HTMLResponse(
        _render_page(
            output=output,
            task="" if provider == "mock" else task,
            provider=provider,
            demo=selected_demo,
            base_url=base_url,
            model=model,
            artifacts=artifacts,
            artifact_zip_b64=artifact_zip_b64,
            show_artifacts=True,
            run_status=run_status,
        )
    )


def _render_mock_summary(
    returncode: int,
    demo_config: dict[str, str],
) -> str:
    """Render a CLI-like summary for deterministic mock demos."""
    if returncode == 0:
        status = demo_config["success"]
        iterations = demo_config["iterations"]
    else:
        status = "FAILURE - Demo failed"
        iterations = "n/a"

    return (
        "\n"
        + "=" * 60
        + "\n"
        + f"  {status}\n"
        + f"  Iterations: {iterations}\n"
        + "=" * 60
        + "\n"
    )


def _classify_run_status(returncode: int, output: str) -> str:
    """Classify the harness result separately from the HTTP request status."""
    failure_markers = (
        "FAILURE -",
        "WebUI execution error",
        "Traceback",
        "LLMAuthError",
        "LLMRateLimitError",
        "LLMTimeoutError",
        "AuthenticationError",
        "Authentication failed",
        "Invalid API key",
        "invalid_api_key",
        "Incorrect API key",
        "Rate limited",
        "Error code:",
        "HTTP 401",
        "401 Unauthorized",
    )
    if returncode != 0:
        return "failure"
    if any(marker in output for marker in failure_markers):
        return "failure"
    if "SUCCESS -" in output:
        return "success"
    if "Demo complete" in output and "[PASS]" in output:
        return "success"
    if output.strip():
        return "success"
    return "idle"


def _redact_sensitive_output(output: str, api_key: str = "") -> str:
    """Remove API key values from text before rendering or storing it."""
    redacted = output
    secret = api_key.strip()

    if secret:
        replacement = "[redacted-api-key]"
        if len(secret) >= 8:
            redacted = redacted.replace(secret, replacement)
        else:
            redacted = re.sub(
                rf"(?<![A-Za-z0-9_-]){re.escape(secret)}(?![A-Za-z0-9_-])",
                replacement,
                redacted,
            )

    return re.sub(r"\bsk-[A-Za-z0-9_-]{6,}\b", "[redacted-api-key]", redacted)


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
    demo: str = "autonomous_repair",
    base_url: str = "https://njusehub.info/v1",
    model: str = "deepseek-v4-pro",
    artifacts: list[dict[str, object]] | None = None,
    artifact_zip_b64: str = "",
    show_artifacts: bool = False,
    run_status: str = "idle",
) -> str:
    """Render a small self-contained HTML page.

    Keeping the HTML inline avoids template-file bundling ambiguity in Vercel's
    Python function packaging.
    """
    escaped_task = html.escape(task)
    escaped_base_url = html.escape(base_url)
    escaped_model = html.escape(model)
    escaped_output = html.escape(output) if output else ""
    escaped_run_status = html.escape(run_status)
    mock_selected = "selected" if provider == "mock" else ""
    openai_selected = "selected" if provider == "openai" else ""
    demo_options = _render_demo_options(demo)
    output_block = (
        f"<h2>Output</h2><pre>{escaped_output}</pre>" if output else ""
    )
    artifacts_block = _render_artifacts(
        artifacts or [],
        artifact_zip_b64,
        show_empty=show_artifacts,
    )
    result_panel = (
        f'<div id="result-panel" data-run-status="{escaped_run_status}">'
        f"{output_block}{artifacts_block}</div>"
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
        input, select {{ width: 100%; padding: 0.5rem; margin-top: 0.25rem; box-sizing: border-box; }}
        label {{ display: block; margin-top: 1rem; font-weight: 600; }}
        .section {{ margin-top: 1rem; }}
        button {{ padding: 0.5rem 2rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; min-width: 7rem; }}
        button:hover {{ background: #0055aa; }}
        button:disabled {{ background: #777; cursor: not-allowed; }}
        .run-row {{ display: flex; align-items: center; gap: 0.75rem; margin-top: 1rem; }}
        .run-status {{ color: #444; font-size: 0.95rem; min-height: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }}
        .spinner {{ display: inline-block; width: 1rem; height: 1rem; border: 2px solid #cfd8dc; border-top-color: #0066cc; border-radius: 50%; animation: spin 0.8s linear infinite; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        a.download {{ display: inline-block; margin: 0.5rem 0 1rem; color: #0066cc; font-weight: 600; }}
        pre {{ background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 4px; overflow-x: auto; }}
        .artifact {{ margin: 1rem 0; }}
        .artifact-name {{ font-weight: 700; }}
        .artifact-meta {{ color: #666; font-size: 0.85rem; }}
        .info {{ color: #666; font-size: 0.9rem; }}
        .key-hint {{ color: #666; font-size: 0.85rem; margin: 0.35rem 0 0; font-weight: 400; }}
    </style>
</head>
<body>
    <h1>TDD Coding Harness</h1>
    <p class="info">Mock mode runs fixed offline demos. Real API mode accepts custom coding tasks and shows generated artifacts.</p>
    <form id="run-form" method="post" action="/run">
        <label>Provider:
            <select id="provider" name="provider" onchange="updateMode()">
                <option value="mock" {mock_selected}>Mock (offline)</option>
                <option value="openai" {openai_selected}>OpenAI-compatible</option>
            </select>
        </label>
        <div id="mock-section" class="section">
            <label>Demo:
                <select name="demo">{demo_options}</select>
            </label>
            <p class="info">Mock mode is deterministic and does not use a custom task or API key.</p>
        </div>
        <div id="real-section" class="section">
            <label>Task:
            <textarea name="task" placeholder="e.g., 编写一个计算斐波那契数列的函数">{escaped_task}</textarea>
            </label>
            <label>Base URL:
                <input name="base_url" type="url" value="{escaped_base_url}" placeholder="https://njusehub.info/v1">
            </label>
            <label>Model:
                <input name="model" type="text" value="{escaped_model}" placeholder="deepseek-v4-pro">
            </label>
            <label>API Key (real API mode only; kept in this browser tab, not stored on server):
                <input id="api-key" name="api_key" type="password" placeholder="Enter API key for this request" autocomplete="off">
                <p id="api-key-hint" class="key-hint"></p>
            </label>
        </div>
        <div class="run-row">
            <button id="run-button" type="submit">Run</button>
            <div id="run-status" class="run-status" aria-live="polite"></div>
        </div>
    </form>
    {result_panel}
    <script>
        const apiKeyStorageKey = "tdd-harness-openai-api-key";
        const formStateStorageKey = "tdd-harness-form-state";
        const resultStorageKey = "tdd-harness-last-result-html";
        const runStateStorageKey = "tdd-harness-run-state";

        function readFormState() {{
            try {{
                return JSON.parse(window.sessionStorage.getItem(formStateStorageKey) || "{{}}");
            }} catch {{
                return {{}};
            }}
        }}

        function saveFormState() {{
            const form = document.getElementById("run-form");
            const state = {{
                provider: document.getElementById("provider").value,
                demo: form.elements.demo.value,
                task: form.elements.task.value,
                base_url: form.elements.base_url.value,
                model: form.elements.model.value,
            }};
            window.sessionStorage.setItem(formStateStorageKey, JSON.stringify(state));
        }}

        function restoreFormState() {{
            const form = document.getElementById("run-form");
            const state = readFormState();
            if (state.provider) {{
                document.getElementById("provider").value = state.provider;
            }}
            if (state.demo) {{
                form.elements.demo.value = state.demo;
            }}
            if (state.task) {{
                form.elements.task.value = state.task;
            }}
            if (state.base_url) {{
                form.elements.base_url.value = state.base_url;
            }}
            if (state.model) {{
                form.elements.model.value = state.model;
            }}
        }}

        function restoreResultPanel() {{
            const resultPanel = document.getElementById("result-panel");
            const savedResult = window.sessionStorage.getItem(resultStorageKey);
            if (savedResult) {{
                resultPanel.innerHTML = savedResult;
            }}
        }}

        function restoreRunState() {{
            const status = document.getElementById("run-status");
            const runState = window.sessionStorage.getItem(runStateStorageKey);
            if (runState === "running") {{
                window.sessionStorage.setItem(runStateStorageKey, "interrupted");
                status.textContent = "Previous run was interrupted by page refresh. Click Run to start again.";
            }} else if (runState === "failed") {{
                status.textContent = "Previous run failed. Check output.";
            }} else if (runState === "complete") {{
                status.textContent = "Previous run complete.";
            }}
        }}

        function escapeHtml(value) {{
            return value
                .replaceAll("&", "&amp;")
                .replaceAll("<", "&lt;")
                .replaceAll(">", "&gt;")
                .replaceAll('"', "&quot;")
                .replaceAll("'", "&#039;");
        }}

        function updateApiKeyHint() {{
            const provider = document.getElementById("provider").value;
            const hint = document.getElementById("api-key-hint");
            const hasStoredKey = Boolean(window.sessionStorage.getItem(apiKeyStorageKey));
            if (provider === "mock") {{
                hint.textContent = "";
            }} else if (hasStoredKey) {{
                hint.textContent = "API key is saved for this browser tab and will be reused for Real API runs.";
            }} else {{
                hint.textContent = "API key is sent only for Real API runs and is not stored on the server.";
            }}
        }}

        function updateMode() {{
            const provider = document.getElementById("provider").value;
            const apiInput = document.getElementById("api-key");
            document.getElementById("mock-section").style.display =
                provider === "mock" ? "block" : "none";
            document.getElementById("real-section").style.display =
                provider === "mock" ? "none" : "block";
            if (provider === "mock") {{
                apiInput.value = "";
            }} else if (!apiInput.value) {{
                apiInput.value = window.sessionStorage.getItem(apiKeyStorageKey) || "";
            }}
            saveFormState();
            updateApiKeyHint();
        }}

        document.getElementById("run-form").addEventListener("input", saveFormState);
        document.getElementById("run-form").addEventListener("change", saveFormState);

        document.getElementById("api-key").addEventListener("input", function () {{
            const provider = document.getElementById("provider").value;
            const apiInput = document.getElementById("api-key");
            if (provider !== "openai") {{
                return;
            }}
            if (apiInput.value.trim()) {{
                window.sessionStorage.setItem(apiKeyStorageKey, apiInput.value.trim());
            }} else {{
                window.sessionStorage.removeItem(apiKeyStorageKey);
            }}
            updateApiKeyHint();
        }});

        document.getElementById("run-form").addEventListener("submit", async function (event) {{
            event.preventDefault();

            const form = event.currentTarget;
            const provider = document.getElementById("provider").value;
            const apiInput = document.getElementById("api-key");
            const button = document.getElementById("run-button");
            const status = document.getElementById("run-status");
            const resultPanel = document.getElementById("result-panel");
            const formData = new FormData(form);

            if (provider === "mock") {{
                apiInput.value = "";
                formData.set("api_key", "");
            }} else {{
                const storedKey = window.sessionStorage.getItem(apiKeyStorageKey) || "";
                const effectiveKey = apiInput.value.trim() || storedKey;
                if (effectiveKey) {{
                    apiInput.value = effectiveKey;
                    window.sessionStorage.setItem(apiKeyStorageKey, effectiveKey);
                    formData.set("api_key", effectiveKey);
                }}
            }}
            saveFormState();
            window.sessionStorage.setItem(runStateStorageKey, "running");

            button.disabled = true;
            button.textContent = "Running";
            status.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>Running... Real API tasks can take up to a minute.</span>';

            try {{
                const response = await fetch(form.action, {{
                    method: "POST",
                    body: formData,
                }});
                const responseText = await response.text();
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}} ${{response.statusText}}`);
                }}
                const doc = new DOMParser().parseFromString(responseText, "text/html");
                const nextResult = doc.getElementById("result-panel");
                const nextRunStatus = nextResult ? nextResult.dataset.runStatus : "";
                resultPanel.innerHTML = nextResult
                    ? nextResult.innerHTML
                    : `<h2>Output</h2><pre>${{escapeHtml(responseText)}}</pre>`;
                if (nextRunStatus) {{
                    resultPanel.dataset.runStatus = nextRunStatus;
                }}
                window.sessionStorage.setItem(resultStorageKey, resultPanel.innerHTML);
                if (nextRunStatus === "success") {{
                    window.sessionStorage.setItem(runStateStorageKey, "complete");
                    status.textContent = "Complete.";
                }} else {{
                    window.sessionStorage.setItem(runStateStorageKey, "failed");
                    status.textContent = "Run failed. Check output.";
                }}
            }} catch (error) {{
                if (error.name === "AbortError") {{
                    window.sessionStorage.setItem(runStateStorageKey, "interrupted");
                    status.textContent = "Run interrupted by page navigation.";
                }} else {{
                    resultPanel.innerHTML = `<h2>Output</h2><pre>WebUI request failed: ${{escapeHtml(String(error))}}</pre>`;
                    window.sessionStorage.setItem(resultStorageKey, resultPanel.innerHTML);
                    window.sessionStorage.setItem(runStateStorageKey, "failed");
                    status.textContent = "Run failed.";
                }}
            }} finally {{
                button.disabled = false;
                button.textContent = "Run";
                updateMode();
            }}
        }});

        restoreFormState();
        restoreResultPanel();
        updateMode();
        restoreRunState();
    </script>
</body>
</html>"""


def _render_demo_options(selected_demo: str) -> str:
    """Render mock demo choices."""
    options = []
    for demo_id, demo_config in DEMO_OPTIONS.items():
        selected = "selected" if demo_id == selected_demo else ""
        value = html.escape(demo_id)
        label = html.escape(str(demo_config["label"]))
        options.append(f'<option value="{value}" {selected}>{label}</option>')
    return "".join(options)


def _render_artifacts(
    artifacts: list[dict[str, object]],
    artifact_zip_b64: str,
    show_empty: bool = False,
) -> str:
    """Render collected generated files."""
    if not artifacts:
        if show_empty:
            return (
                "<h2>Artifacts</h2>"
                '<p class="info">No generated files were produced by this run.</p>'
            )
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
