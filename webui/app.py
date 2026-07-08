"""TDD Coding Harness — WebUI (FastAPI)

Provides a browser interface for running harness tasks and viewing
results.  Designed to be deployed on Render / Railway / Fly.io.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="TDD Coding Harness WebUI")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the main page."""
    return templates.TemplateResponse("index.html", {"request": request, "output": None})


@app.post("/run", response_class=HTMLResponse)
async def run_task(
    request: Request,
    task: str = Form(...),
    provider: str = Form("mock"),
) -> HTMLResponse:
    """Execute a harness task and show the output."""
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            ["tdd-harness", "run", task, "--provider", provider],
            capture_output=True,
            text=True,
            cwd=tmp,
            timeout=60,
        )
        output = result.stdout + "\n" + result.stderr
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "output": output, "task": task, "provider": provider},
    )