# TDD Coding Harness 交付入口

本目录是课程平台提交用的文档入口。完整源码、提交历史、CI 和线上部署不直接打包在本目录内，请通过下面的链接检查。

## 项目信息

- 项目名称：TDD Coding Harness
- 项目类型：AI4SE 期末项目 A 类 · Coding Agent Harness
- 代码仓库：<https://github.com/dxz0713/TDD-Coding-Harness>
- 线上 WebUI：<https://tdd-coding-harness.vercel.app/>
- CI：<https://github.com/dxz0713/TDD-Coding-Harness/actions>
- 默认分支：`master`

## 建议检查顺序

1. 阅读本文，确认仓库与线上入口。
2. 阅读 `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`。
3. 在 GitHub 仓库中查看源码、commit history、CI 配置和 workspace 证据目录。
4. 打开线上 WebUI，先运行 Mock demo。
5. 在 WebUI 中选择 Real API，填写 API Key、Base URL、Model 和 Task，运行真实任务。
6. 如需本地复现，按仓库根目录 `README.md` 的命令 clone 后运行。

## 交付物对照

| 要求 | 位置 |
|------|------|
| SPEC 设计文档 | `docs/SPEC.md` |
| PLAN 实现计划 | `docs/PLAN.md` |
| SPEC_PROCESS 过程文档 | `docs/SPEC_PROCESS.md` |
| README 运行说明 | 仓库根目录 `README.md`，本文也列出入口 |
| AGENT_LOG 开发日志 | `docs/AGENT_LOG.md` |
| REFLECTION 反思报告 | `docs/REFLECTION.md` |
| 源代码 | GitHub 仓库 `src/`, `examples/`, `webui/` |
| Mock LLM 单元测试 | GitHub 仓库 `src/tests/` 与 `tests/` |
| 机制演示 | GitHub 仓库 `examples/demo_guardrail.py`, `examples/demo_feedback.py`, `examples/demo_autonomous_repair.py`；WebUI Mock demo |
| Docker 分发 | GitHub 仓库 `Dockerfile` |
| CI 配置 | `.github/workflows/ci.yml` 与 `.gitlab-ci.yml` |
| CI/CD 执行记录 | GitHub Actions 页面 |
| 线上部署 URL | <https://tdd-coding-harness.vercel.app/> |
| 真实 API 运行证据 | GitHub 仓库 `workspace/fib/`, `workspace/gcd/` |

## 本地运行摘要

```bash
git clone https://github.com/dxz0713/TDD-Coding-Harness.git
cd TDD-Coding-Harness
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest tests/ -v
```

Mock 机制演示：

```bash
python examples/demo_guardrail.py
python examples/demo_feedback.py
python examples/demo_autonomous_repair.py
```

Real API 本地运行：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
tdd-harness run "编写一个计算斐波那契数列的函数" --provider openai --model deepseek-v4-pro
```

本地 CLI 会在 `workspace/` 下为每次运行创建独立目录，并写入 `log.txt`。

## WebUI 运行摘要

访问 <https://tdd-coding-harness.vercel.app/>。

Mock 模式：

- Provider 选择 `Mock (offline)`。
- 从 Demo 下拉框选择固定 demo。
- Mock 不允许自定义 task，不需要 API Key。
- 运行后查看 `Output` 和 `Artifacts`。

Real API 模式：

- Provider 选择 `OpenAI-compatible`。
- 填写 Task。
- Base URL 填 `https://njusehub.info/v1`。
- Model 填 `deepseek-v4-pro`。
- 填写 API Key 后运行。
- 产物会在当次页面的 `Artifacts` 区域展示，并可下载 zip。

## 最终验证摘要

- `pytest tests/ -v`：`213 passed, 1 skipped`
- `docker build -t tdd-harness .`：success
- `docker run --rm tdd-harness --help`：success
- WebUI 首页：200
- WebUI Mock demo：可运行，输出和 artifacts 区域可见
- WebUI Real API：支持 Base URL、Model、API Key 和自定义 Task

## 安全说明

- 仓库不提交真实 API Key。
- API Key 通过环境变量或 WebUI 表单临时传入。
- `.env`、`.env.local`、`config.local.yaml`、`*.key` 已被 `.gitignore` 排除。
- `workspace/fib/log.txt` 与 `workspace/gcd/log.txt` 已检查，不包含真实 API Key。
