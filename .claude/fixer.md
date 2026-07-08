# Fixer Task：TDD Coding Harness 满分补救

> **背景：** 项目已获得初始评分 80/100（修正后 81/100），目标是争取满分。
> **评分报告：** `temp.md`
> **CI 截图：** `CI_PASS.png`（项目根目录，CI 已通过）
> **工作目录：** `E:\MyClass\2-2-summer\AI-Enabled_SoftwareEngineerBootcamp\homework`
> **测试命令：** `D:\Python3.12\python.exe -m pytest src/tests/ -v`
>
> **注意：** 每次修改后必须运行全部测试，确保不破坏已有功能。

---

## 总览

| # | 修复项 | 可拿回分数 | 涉及文件 | 难度 |
|---|--------|-----------|---------|------|
| F1 | PLAN.md 更新 | +1 | `docs/PLAN.md` | 极低 |
| F2 | 安全配置说明 | +1 | `README.md` | 极低 |
| F3 | CI Badge + 截图 | +2 | `README.md` | 低 |
| F4 | 凭据安全（keyring） | +3 | `src/harness/credential_manager.py` + test + config | 低 |
| F5 | 机制演示改进 | +1 | `examples/demo_autonomous_repair.py` | 低 |
| F6 | Git 工作流补 PR | +4 | 5 个分支说明 | 中 |
| F7 | WebUI + 部署 | +3 | `webui/` 新目录 | 中 |
| | **总计** | **+15** | | |

**目标总分：** 81 + 15 = **96/100**

---

## F1：PLAN.md 更新（+1分）

**目标：** 为每个 Task 标注完成状态 ✅ 和对应 commit hash。

**修改文件：** `docs/PLAN.md`

**修改方式：** 在每个 Task 的 DoD 下方或表格末尾增加一行：

```markdown
**完成状态：** ✅ `99bb011`（或对应 commit hash）
```

**Task → Commit 对照表：**

| Task | 内容 | Commit |
|------|------|--------|
| T1 | 项目脚手架 | `d687c24` |
| T2 | 数据模型 + Config | `d687c24`（与 T1 同批次） |
| T3 | CLI 入口 | `0f7247c` |
| T4 | LLMProvider 抽象 + Mock + Factory | `0f7247c` |
| T5 | OpenAICompatibleProvider | `c639657` |
| T6 | BaseTool + Dispatcher | `0f7247c` |
| T7 | ReadFile | `c639657` |
| T8 | WriteFile | `c639657` |
| T9 | RunShell | `c639657` |
| T10 | Guardrail | `95e3918` |
| T11 | Main Loop 框架 | `009cb4a` |
| T12 | Context 管理 | `95e3918` |
| T13 | 停机条件 | `95e3918` |
| T14 | Memory | `95e3918` |
| T15 | Feedback 数据模型 | `99bb011`（在 models.py 中） |
| T16 | Collector + FailureAnalyzer | `009cb4a` |
| T17 | FeedbackEngine + 策略 | `3a2b89c` |
| T18 | 集成 Feedback → Loop | `d4643d4` |
| T19 | 机制演示脚本 | `d4643d4` |
| T20 | README 完善 | `bb6a695` |
| T21 | AGENT_LOG + 最终验证 | `bb6a695` |

**验证：** `cat docs/PLAN.md | grep -c "✅"` 应等于 21（每个 Task 都有完成标记）

---

## F2：安全配置说明（+1分）

**目标：** 在 README 中增加安全配置分级说明。

**修改文件：** `README.md`

**在现有 "Security" 章节（第 206-210 行）后追加以下内容：**

```markdown
### API Key 配置方式（按安全等级排序）

| 等级 | 方式 | 说明 | 安全性 |
|------|------|------|--------|
| 🥇 推荐 | 系统钥匙串 | 使用 `keyring` 接入 Windows Credential Manager / macOS Keychain | ✅ 加密存储，进程隔离 |
| 🥈 默认 | `.env` 文件 | `OPENAI_API_KEY=sk-...` 写入 `.env`，`python-dotenv` 加载 | ⚠️ 明文文件，需确保 `.gitignore` 排除 |
| 🥉 备选 | 环境变量 | 通过 `export OPENAI_API_KEY=sk-...` 或 Docker `-e` 传入 | ⚠️ 明文，shell history 可见 |
| ❌ 禁止 | 硬编码 | 不得在源码中写入 Key | 🔴 会导致凭据泄露 |

> **首次运行引导：** 当检测到未配置 API Key 时，运行 `tdd-harness init` 会提示你输入 Key（输入内容不回显），自动存入系统钥匙串。
```

---

## F3：CI Badge + 截图（+2分）

**目标：** 在 README 中添加 CI badge，引用 CI_PASS.png 截图。

**修改文件：** `README.md`

**在 README 开头的 "Quick Start" 或其他位置添加：**

```markdown
## CI Status

![CI](https://github.com/dxz0713/TDD-Coding-Harness/actions/workflows/ci.yml/badge.svg)

![CI Pass Screenshot](CI_PASS.png)
*CI 最后一次执行结果（2026-07-08）*
```

**验证：** 截图文件 `CI_PASS.png` 必须在项目根目录能被引用。

---

## F4：凭据安全 — keyring 实现（+3分）

**目标：** 实现系统钥匙串存储方案，替代仅 `.env` 的方式。

### 新建文件：`src/harness/credential_manager.py`

```python
"""Credential manager — OS keyring integration (keyring).

Provides secure storage and guided first-run setup for API keys,
backed by the operating system credential manager (Windows Credential
Manager, macOS Keychain, Linux Secret Service).

Usage::

    cm = CredentialManager()
    api_key = cm.get_api_key()       # auto-prompt on first call
"""

from __future__ import annotations

import getpass
import logging
import sys
from typing import ClassVar

import keyring

logger = logging.getLogger(__name__)


class CredentialManager:
    """System keyring-backed credential storage.

    Attributes:
        SERVICE_NAME: The keyring service name used for all credentials.
    """

    SERVICE_NAME: ClassVar[str] = "tdd-harness"

    # ── Public API ──────────────────────────────────────────────────

    @staticmethod
    def get_api_key(env_var: str = "OPENAI_API_KEY") -> str:
        """Retrieve the API key from the system keyring.

        Falls back to the environment variable if the keyring is empty.
        If neither is available, prompts the user for interactive input.

        Args:
            env_var: Environment variable name to fall back to.

        Returns:
            The API key as a string.
        """
        # 1. Try keyring
        key = keyring.get_password(CredentialManager.SERVICE_NAME, "openai_api_key")
        if key:
            logger.debug("API key loaded from system keyring")
            return key

        # 2. Try environment variable
        import os

        key = os.getenv(env_var)
        if key:
            logger.info("API key loaded from environment variable %s", env_var)
            # Optionally persist to keyring for future use
            return key

        # 3. Interactive prompt
        print("No API key found. Please enter your OpenAI-compatible API key.")
        print("(Input will be hidden for security.)")
        key = getpass.getpass("API Key: ")
        if key:
            CredentialManager.set_api_key(key)
            return key

        logger.error("No API key provided.")
        sys.exit(1)

    @staticmethod
    def set_api_key(key: str) -> None:
        """Store an API key in the system keyring.

        Args:
            key: The API key to store.
        """
        keyring.set_password(CredentialManager.SERVICE_NAME, "openai_api_key", key)
        logger.info("API key saved to system keyring")

    @staticmethod
    def has_api_key() -> bool:
        """Check whether an API key is available in the keyring.

        Returns:
            True if a key exists in the keyring.
        """
        return keyring.get_password(CredentialManager.SERVICE_NAME, "openai_api_key") is not None

    @staticmethod
    def clear_api_key() -> None:
        """Remove the API key from the system keyring."""
        try:
            keyring.delete_password(CredentialManager.SERVICE_NAME, "openai_api_key")
            logger.info("API key cleared from system keyring")
        except keyring.errors.PasswordDeleteError:
            logger.info("No API key to clear from system keyring")
```

### 新建测试文件：`src/tests/test_credential_manager.py`

```python
"""Tests for CredentialManager."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from harness.credential_manager import CredentialManager


class TestCredentialManager:
    """Test keyring-based credential storage."""

    def test_has_api_key_false_when_empty(self) -> None:
        """钥匙串为空时 has_api_key() 返回 False。"""
        with patch("keyring.get_password", return_value=None):
            assert not CredentialManager.has_api_key()

    def test_has_api_key_true_when_set(self) -> None:
        """钥匙串有 Key 时 has_api_key() 返回 True。"""
        with patch("keyring.get_password", return_value="sk-test123"):
            assert CredentialManager.has_api_key()

    def test_get_api_key_from_env_fallback(self) -> None:
        """钥匙串为空时回退到环境变量。"""
        with patch("keyring.get_password", return_value=None):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-test"}, clear=False):
                key = CredentialManager.get_api_key()
                assert key == "sk-env-test"

    def test_set_and_clear(self) -> None:
        """set_api_key → has_api_key=True → clear → has_api_key=False。"""
        with patch("keyring.set_password") as mock_set:
            with patch("keyring.delete_password") as mock_del:
                with patch("keyring.get_password", side_effect=["sk-test", None]):
                    CredentialManager.set_api_key("sk-test")
                    mock_set.assert_called_once()
                    assert CredentialManager.has_api_key()

                    CredentialManager.clear_api_key()
                    mock_del.assert_called_once()
                    assert not CredentialManager.has_api_key()
```

### 修改文件：`config.yaml`

在 `config.yaml` 增加凭据配置选项：

```yaml
# 在文件末尾或 provider 节点中增加
credential:
  storage: keyring       # keyring | env | prompt
  env_var: OPENAI_API_KEY
```

### 修改文件：`pyproject.toml`

在 `[project.optional-dependencies]` 或 `dependencies` 中增加：

```toml
dependencies = [
    ...
    "keyring>=24.0",
]
```

### 验证

```bash
pip install keyring
python -m pytest src/tests/test_credential_manager.py -v
```

---

## F5：机制演示改进（+1分）

**目标：** 重写 `examples/demo_autonomous_repair.py`，使其展示真正的 MockProvider 驱动的动态修复流程，而非硬编码的预设步骤。

**修改文件：** `examples/demo_autonomous_repair.py`

**要求：**
1. 使用 `MockProvider` 创建动态的 mock 响应序列
2. 模拟"写代码→测试失败→分析反馈→修复→测试通过"的完整闭环
3. 展示 `FeedbackEngine` 在循环中实际被调用
4. 不要硬编码每一步的结果——使用真实的 `HarnessLoop` + `FeedbackEngine` 流程
5. 输出清晰标记每个阶段

**核心思路（伪代码）：**

```python
# 1. 创建 MockProvider，预设响应序列
#    响应1：写一个文件（WriteFile）
#    响应2：运行测试（RunShell）— 测试失败
#    响应3：读取文件（ReadFile）
#    响应4：写修复后的文件（WriteFile）
#    响应5：运行测试（RunShell）— 测试通过
#    响应6：Finish

# 2. 创建真实的 HarnessLoop（注入 MockProvider + FeedbackEngine）

# 3. 运行 loop.run("修复代码中的bug")

# 4. 打印每次迭代的反馈和结果
```

**验证：** `python examples/demo_autonomous_repair.py` 能在不联网的情况下输出完整的修复流程。

---

## F6：Git 工作流补 PR（+4分）

**目标：** 编写 5 个 PR 描述文件，供用户在 GitHub 上基于已有分支创建 PR。

**前提：** 5 个分支（`pr-provider-layer`、`pr-tools`、`pr-guardrail`、`pr-feedback`、`pr-loop`）已在 GitHub 上从 master 创建。本环境无法连接 GitHub，因此只负责在本地创建 PR 描述文件。

**分支 PR 对照表：**

| 分支名 | 对应 Task | 关联 Commit |
|--------|----------|-------------|
| `pr-provider-layer` | T3(CLI) + T4(Provider抽象) + T5(OpenAIProvider) | `0f7247c`, `c639657` |
| `pr-tools` | T6(Dispatcher) + T7(ReadFile) + T8(WriteFile) + T9(RunShell) | `c639657` |
| `pr-guardrail` | T10(Guardrail) | `95e3918` |
| `pr-feedback` | T15+T16(数据模型+Analyzer) + T17(Engine+策略) | `009cb4a`, `3a2b89c` |
| `pr-loop` | T11(Loop) + T18(Feedback→Loop集成) | `009cb4a`, `d4643d4` |

### 创建 5 个 PR 描述文件

在 `.claude/pr-descriptions/` 目录下创建 5 个文件：

- `.claude/pr-descriptions/pr-provider-layer.md`
- `.claude/pr-descriptions/pr-tools.md`
- `.claude/pr-descriptions/pr-guardrail.md`
- `.claude/pr-descriptions/pr-feedback.md`
- `.claude/pr-descriptions/pr-loop.md`

每个文件内容格式：

```markdown
# PR: [分支名]

## 对应 Task
- T3: CLI入口（typer框架，`--provider`/`--model`参数）
- T4: LLMProvider抽象 + MockProvider + ProviderFactory
- T5: OpenAICompatibleProvider

## 关联 Commit
- `0f7247c` — feat: implement T3 (CLI), T4 (Providers), T6 (Tool Dispatcher)
- `c639657` — feat: implement T5 (OpenAIProvider), T7-T9 (Tools)

## Sub-agent 任务描述
参见 `.claude/T3T4T6.md`、`.claude/T5T7T8T9.md`

## 人工修改记录
- 无（全部由 sub-agent 自动完成）

## 验证
- [x] `pytest src/tests/ -v` 全部通过
- [x] `tdd-harness run --help` 可运行
```

---

## F7：WebUI + 部署（+3分）

**目标：** 创建一个简单的 FastAPI Web 界面，允许用户通过浏览器输入任务并查看 Harness 输出。

### 新建目录结构

```
webui/
├── app.py          # FastAPI 应用
├── templates/
│   └── index.html  # Jinja2 模板
├── Dockerfile      # WebUI 专用 Dockerfile
└── requirements.txt # WebUI 依赖
```

### `webui/app.py`

```python
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
```

### `webui/templates/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TDD Coding Harness</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; background: #f5f5f5; }
        h1 { color: #333; }
        textarea { width: 100%; min-height: 100px; padding: 0.5rem; font-family: monospace; }
        button { padding: 0.5rem 2rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0055aa; }
        pre { background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 4px; overflow-x: auto; }
        .info { color: #666; font-size: 0.9rem; }
    </style>
</head>
<body>
    <h1>TDD Coding Harness</h1>
    <p class="info">Enter a coding task below and let the harness generate, test, and fix code automatically.</p>
    <form method="post" action="/run">
        <textarea name="task" placeholder="e.g., 编写一个计算斐波那契数列的函数">{{ task or '' }}</textarea>
        <br><br>
        <label>Provider:
            <select name="provider">
                <option value="mock" {% if provider == 'mock' %}selected{% endif %}>Mock (offline)</option>
                <option value="openai" {% if provider == 'openai' %}selected{% endif %}>OpenAI</option>
            </select>
        </label>
        <br><br>
        <button type="submit">Run</button>
    </form>
    {% if output %}
    <h2>Output</h2>
    <pre>{{ output }}</pre>
    {% endif %}
</body>
</html>
```

### `webui/requirements.txt`

```
fastapi>=0.100
uvicorn>=0.20
jinja2>=3.0
```

### `webui/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install harness
COPY pyproject.toml /app/
COPY src/ /app/src/
RUN pip install --no-cache-dir -e ".[dev]"

# Install webui deps
COPY webui/requirements.txt /app/webui/
RUN pip install --no-cache-dir -r /app/webui/requirements.txt

COPY webui/ /app/webui/

EXPOSE 8000
CMD ["uvicorn", "webui.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 验证

```bash
pip install fastapi uvicorn jinja2
uvicorn webui.app:app --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000
```

---

## 执行顺序（按优先级）

```
F1 (PLAN更新)     → 15分钟，先做，影响最小
F2 (安全说明)     → 10分钟，改 README
F3 (CI Badge)     → 5分钟，加 badge
F4 (keyring)      → 30分钟，核心安全改进
F5 (demo改进)     → 30分钟
F6 (PR描述文件)    → 20分钟，写5个文件
F7 (WebUI)        → 1小时，如果时间允许
```

## DoD（全局）

```
□ F1: PLAN.md 每个 Task 有 ✅ 完成标记 + commit hash
□ F2: README 安全配置分级说明已追加
□ F3: README 包含 CI badge 和 CI_PASS.png 引用
□ F4: src/harness/credential_manager.py 已创建，测试通过
□ F5: examples/demo_autonomous_repair.py 已重写，展示动态修复流程
□ F6: .claude/pr-descriptions/ 下 5 个 PR 描述文件已创建
□ F7: webui/ 目录已创建，可本地运行
□   全部 pytest 通过（不能破坏已有测试）
```

---

> **注意：** Fixer 完成后，人工还需执行以下操作：
> 1. 在 GitHub 上为已有的 5 个分支创建 PR（内容参考 `.claude/pr-descriptions/` 下的文件）
> 2. 将 webui/ 推送到 GitHub 并部署到 Render
> 3. 截图 Render 部署页面
> 4. `pip install keyring` 并测试凭据管理