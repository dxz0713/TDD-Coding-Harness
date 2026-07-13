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

## 测试助教提示

- 本地 Real API 测试建议使用 PowerShell 临时环境变量传入 Key：`$env:OPENAI_API_KEY = "your-api-key"`，不要写入源码、配置文件或日志。
- WebUI Real API 测试时，API Key 仅用于本次后端调用，不写入仓库、不写入服务端文件、不在响应 HTML 中回显；如果兼容 API 的错误文本包含 Key，WebUI 会在展示 Output 和写入前端缓存前脱敏。浏览器端仅在当前标签页的 `sessionStorage` 中保留并保持输入框可见，便于连续验证，关闭标签页后失效。
- WebUI 点击 `Run` 后按钮会变为 `Running` 并禁用，Real API 任务完成后页面展示 `Output` 和 `Artifacts`。
- 如果测试助教不希望使用自己的 Key，可联系作者获取仅适用于 `https://njusehub.info/v1` 的限时、限额的临时 API Key；该 Key 不随提交文档公开。

## 交付物对照

| 要求 | 位置 |
| ------ | ------ |
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

访问 <https://tdd-coding-harness.vercel.app/>。（需要魔法）

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
- 填写 API Key 后运行；同一浏览器标签页会话内会保留 Key 并保持输入框可见，便于连续验证。
- 点击 `Run` 后按钮会切换为 `Running` 并禁用，避免重复提交。
- 运行结束后按钮旁状态会根据 Harness 结果显示 `Complete` 或 `Run failed`；API Key 错误、鉴权失败、测试失败等不会被标成完成。
- WebUI 使用前端提交并只更新结果区，刷新页面会保留当前标签页中的表单状态和最近一次 Output / Artifacts，但不会重复运行上一次任务；只有再次点击 `Run` 才会发起新任务。
- 如果在 `Running` 状态刷新页面，浏览器会中断当前前端请求；页面会提示 previous run was interrupted，并允许重新点击 `Run`。
- 产物会在当次页面的 `Artifacts` 区域展示，并可下载 zip。

## 最终验证摘要

- `pytest tests/ -v`：`213 passed, 1 skipped`
- 唯一 skipped 测试是 `test_openai_provider_can_be_created_via_factory`；该测试在未设置 `OPENAI_API_KEY` 时跳过，用于保证默认单元测试不依赖真实凭据。OpenAI-compatible Provider 的格式转换、工厂注册、Mock LLM 与完整 Harness 机制仍由确定性测试覆盖，真实 API 行为通过本地 Real API 与 WebUI 手动验证覆盖。
- Mock 机制演示：`demo_guardrail.py`、`demo_feedback.py`、`demo_autonomous_repair.py` 均通过
- 本地 Real API：LCM 任务通过，`SUCCESS - All tests passed`，作为最终手动验证记录；长期提交的真实 API 证据仍以 `workspace/fib/` 与 `workspace/gcd/` 为准
- `workspace/fib/` 与 `workspace/gcd/` 真实 API 证据目录测试通过，日志无异常
- `docker build -t tdd-harness .`：success
- `docker run --rm tdd-harness --help`：success
- WebUI 首页：200
- WebUI Mock demo：可运行，输出和 artifacts 区域可见
- WebUI Real API：支持 Base URL、Model、API Key 和自定义 Task；运行中按钮显示 `Running` 并禁用；结果页展示 artifacts

## 安全说明

- 仓库不提交真实 API Key。
- API Key 通过环境变量或 WebUI 表单传入；WebUI 后端只在单次请求中使用 Key 调用模型，不写入服务端文件或响应 HTML；浏览器端仅在当前标签页会话内保留，不写入仓库或服务器持久存储。
- `.env`、`.env.local`、`config.local.yaml`、`*.key` 已被 `.gitignore` 排除。
- `workspace/fib/log.txt` 与 `workspace/gcd/log.txt` 已检查，不包含真实 API Key。
