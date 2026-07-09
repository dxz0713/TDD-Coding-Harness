# AGENT_LOG

> **Project:** TDD Coding Harness — AI4SE Final Project Category A
> **Date:** 2026-07-07 to 2026-07-09
> **Planned Tasks:** T1–T21
> **Implementation Log:** T1–T19 plus T20/T21 final hardening/verification

---

## Task T1 — 初始项目脚手架

- **Date:** 2026-07-07 12:30
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `.gitignore`, `docs/SPEC.md`, `docs/SPEC_PROCESS.md`, `plan/AI4SE_Final_Project_A_Coding_Agent_Harness.md`, `plan/workflow.md`, `plan/通用要求.md`
- **Key decisions:** 采用 SPEC.md + SPEC_PROCESS.md 双文档体系，分别描述系统规格和开发流程；中文需求文档保留在 `plan/` 目录。
- **Result:** 7 files created, 1730 lines added
- **Reflection:** 初始项目结构奠定了整个项目的文档规范，后续所有任务都基于 SPEC 中的定义展开。

---

## Task T2 — SPEC + PLAN 文档完善

- **Date:** 2026-07-07 12:45–14:25
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `docs/SPEC.md`, `docs/SPEC_PROCESS.md`, `docs/PLAN.md`
- **Key decisions:**
  - 增加 CLI 参数覆盖 provider/model 的规格 (SPEC §3.8)
  - PLAN.md 采用 21-task 分解，标注每个 Task 的 SP 和依赖关系
  - 经过 8 轮 review 和 4 轮 refinement 迭代
- **Result:** 6 commits, ~1000 lines refined across SPEC and PLAN
- **Reflection:** 文档先行（documentation-driven）的策略有效减少了后期实现中的歧义。PLAN.md 的迭代次数（8 轮 review 建议）说明前期设计需要充分讨论。

---

## Task T3 — CLI 入口

- **Date:** 2026-07-07 14:47
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/cli.py`
- **Key decisions:** 使用 `typer` 而非 `argparse`，减少样板代码；支持 `run` 和 `demo` 两个子命令；`--provider` / `--model` 参数可选覆盖默认配置。
- **Result:** 50 lines; 测试文件 `test_cli.py` (162 lines) 覆盖 CLI 参数解析
- **Reflection:** typer 的类型注解自动生成 help 文档，大幅减少了 CLI 维护成本。

---

## Task T4 — Provider 抽象 + Factory

- **Date:** 2026-07-07 14:47
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/providers/base.py`, `src/providers/factory.py`, `src/providers/mock.py`
- **Key decisions:** 采用注册表模式（Registry Pattern）而非硬编码条件分支；`MockProvider` 支持可编程的 mock 响应，便于离线测试。
- **Result:** 213 lines; 测试文件 `test_providers.py` 覆盖 Provider 创建和 Mock 调用
- **Reflection:** 注册表模式使新增 provider 只需 `register()` 一行，符合开闭原则。

---

## Task T5 — OpenAI 兼容 Provider

- **Date:** 2026-07-07 15:13
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/providers/openai_compat.py`
- **Key decisions:** 支持 OpenAI API 兼容接口（OpenAI、DeepSeek、Qwen 等）；`base_url` 可配置以指向不同 API 端点；`python-dotenv` 支持 `.env` 文件加载 API Key。
- **Result:** 150 lines; 测试覆盖 API 调用和错误处理
- **Reflection:** 虽然最初预留了 `claude` provider 接口，但基于 OpenAI 兼容 API 的生态更广，故优先实现。

---

## Task T6 — Tool Dispatcher

- **Date:** 2026-07-07 14:47
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/tools/base.py`, `src/tools/dispatcher.py`
- **Key decisions:** `BaseTool` 抽象类定义 `execute()` 接口；`ToolDispatcher` 用字典注册工具，支持 `dispatch()` 路由；未注册的工具返回错误 ToolResult 而非抛异常。
- **Result:** 126 lines; 测试文件 `test_tools.py` 覆盖调度和错误路径
- **Reflection:** 将工具注册为单例模式（`get_default_dispatcher()`），避免重复初始化。

---

## Task T7 — ReadFile 工具

- **Date:** 2026-07-07 15:13
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/tools/read_file.py`
- **Key decisions:** 支持文件不存在时的友好错误信息；路径限制在工作目录内（安全考量）。
- **Result:** 94 lines
- **Reflection:** 与 T8/T9 共享 `BaseTool` 同一接口，三个工具的实现模式高度一致。

---

## Task T8 — WriteFile 工具

- **Date:** 2026-07-07 15:13
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/tools/write_file.py`
- **Key decisions:** 自动创建父目录；支持覆盖写和追加写两种模式。
- **Result:** 96 lines
- **Reflection:** 文件写入是 TDD 循环中"生成代码"的关键步骤，需要确保目录存在性。

---

## Task T9 — RunShell 工具

- **Date:** 2026-07-07 15:13
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/tools/run_shell.py`
- **Key decisions:** 捕获 stdout/stderr 和 exit_code；设置超时防止命令挂起；与 Guardrail 协同工作（Guardrail 先拦截再执行）。
- **Result:** 108 lines
- **Reflection:** Shell 命令执行是风险最高的工具，需要超时和 Guardrail 双层保护。

---

## Task T10 — Guardrail

- **Date:** 2026-07-07 15:31
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/guardrail.py`
- **Key decisions:** 使用正则表达式匹配危险命令模式（`rm -rf /`、fork bomb 等）；内置安全命令白名单优先于黑名单检查；支持用户通过 `config.yaml` 扩展 block list。
- **Result:** 136 lines; 测试文件 `test_guardrail.py` (260 lines) 覆盖全部 10+ 危险模式
- **Reflection:** 白名单 + 黑名单双机制有效降低了误杀率，同时保证了安全性。

---

## Task T11 — Main Loop

- **Date:** 2026-07-07 15:52
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/loop.py`
- **Key decisions:** 依赖注入设计——`HarnessLoop` 不实例化任何依赖，所有组件通过构造函数注入；`finish` 作为虚拟工具调用（intercept before dispatch）；循环中每轮 tool call 都执行 Guardrail 检查。
- **Result:** 126 lines; 测试文件 `test_loop.py` (245 lines) 覆盖循环路径和中断条件
- **Reflection:** 依赖注入使 Loop 的单元测试可以 mock 所有外部组件，隔离性极好。

---

## Task T12 — Context Manager

- **Date:** 2026-07-07 15:31
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/context.py`
- **Key decisions:** 维护消息列表（messages），支持追加 system/user/assistant 消息以及 tool result 和 feedback 消息；迭代次数跟踪。
- **Result:** 131 lines; 测试文件 `test_context.py` (176 lines)
- **Reflection:** Context 是 Loop 的"数据总线"，所有组件通过它交换信息。

---

## Task T13 — Memory Store

- **Date:** 2026-07-07 15:31
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/memory.py`
- **Key decisions:** 基于 JSON 文件的跨会话持久化存储；支持 key-value 存取；通过 `config.yaml` 控制启用/禁用和存储路径。
- **Result:** 135 lines; 测试文件 `test_memory.py` (190 lines)
- **Reflection:** JSON 文件存储适合原型阶段，生产环境可替换为数据库存储。

---

## Task T14 — Stop Condition

- **Date:** 2026-07-07 15:31
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/stop_condition.py`
- **Key decisions:** 支持两种停止信号：`finish` 虚拟工具调用（成功完成）和最大迭代次数超限（超时终止）；`AutonomousStopDecision` 提供 `should_stop()` 和 `on_finish()` 两个入口。
- **Result:** 134 lines; 测试文件 `test_stop_condition.py` (202 lines)
- **Reflection:** 将停止逻辑从 Loop 中抽离为独立组件，符合单一职责原则。

---

## Task T15 — Feedback 数据模型

- **Date:** 2026-07-07 14:21
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/models.py`
- **Key decisions:** 使用 Pydantic 定义 `FailureType`（7 种失败类型枚举）、`AnalysisResult`（分析结果）和 `Feedback`（可直接用于 LLM 的反馈结构）；`FailureType` 涵盖 SyntaxError、AssertionError、ImportError、RuntimeError、Timeout、TestFailure、Unknown。
- **Result:** 模型类定义在 `models.py` 中，与 T16/T17 共享
- **Reflection:** 数据模型先行（model-first）使 T16 的 Analyzer 和 T17 的 Engine 可以基于稳定的接口开发。

---

## Task T16 — Feedback Analyzer

- **Date:** 2026-07-07 15:52
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/feedback/analyzer.py`
- **Key decisions:** `Collector` 负责标准化原始输出（去除 ANSI 转义码、提取失败测试名）；`FailureAnalyzer` 使用正则/模式匹配对 pytest 输出进行分类；每种 `FailureType` 有对应的检测策略。
- **Result:** 266 lines; 测试文件 `test_analyzer.py` (246 lines)
- **Reflection:** 正则匹配方式对 pytest 输出格式依赖较强，更换测试框架需要调整匹配规则。

---

## Task T17 — FeedbackEngine + 自适应修复策略

- **Date:** 2026-07-07 16:03
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/feedback/engine.py`, `src/feedback/strategies.py`
- **Key decisions:** `FeedbackEngine` 连接 Collector → Analyzer → Strategy 成完整流水线；每种 `FailureType` 有对应的 `RepairStrategy`（如 `SyntaxStrategy`、`AssertionStrategy`、`ImportStrategy` 等）；修复策略生成可被 LLM 理解的修复提示。
- **Result:** 185 lines; 测试文件 `test_feedback_engine.py` (261 lines)
- **Reflection:** 策略模式（Strategy Pattern）使新增失败类型只需添加新的 Strategy 类，无需修改 Engine。

---

## Task T18 — Feedback → Loop 集成

- **Date:** 2026-07-07 16:23
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `src/harness/loop.py`, `src/tests/test_loop_integration.py`
- **Key decisions:** 在 Loop 的 tool call 处理循环中，当 `result.exit_code` 非零时自动调用 `FeedbackEngine.analyze()`；生成的 Feedback 被追加到 Context 中供 LLM 下一轮使用；集成测试覆盖完整 TDD 闭环。
- **Result:** 修改 24 lines; 新增集成测试 319 lines
- **Reflection:** 集成测试是验证 TDD 闭环的关键，MockProvider 使测试不依赖真实 API。

---

## Task T19 — Demo 脚本

- **Date:** 2026-07-07 16:23
- **Sub-agent:** Claude Code (Sonnet)
- **Files:** `examples/demo_guardrail.py`, `examples/demo_feedback.py`, `examples/demo_autonomous_repair.py`
- **Key decisions:** 三个 Demo 分别演示：Guardrail 拦截、Feedback 分类、完整 TDD 闭环；`demo_autonomous_repair.py` 使用 MockProvider 实现无需 API Key 的可演示闭环。
- **Result:** 3 demo scripts, 357 lines total
- **Reflection:** Demo 脚本不仅用于展示，也可作为回归测试的一部分（每次提交时运行验证基础功能正常）。

---

## Final Hardening — 测试、真实 API、Vercel、Docker 收尾

- **Date:** 2026-07-09 02:19 +08:00
- **Agent:** Codex
- **Files:** `.gitignore`, `Dockerfile`, `README.md`, `docs/README.md`, `app.py`, `pyproject.toml`, `requirements.txt`, `src/harness/cli.py`, `src/harness/loop.py`, `tests/test_src_suite.py`, `webui/app.py`, `webui/requirements.txt`
- **Decision:** 修复最终交付前的运行路径问题，而不改变核心 harness 架构。
- **Reason:** `pytest tests/ -v` 需要在受限 Windows 环境稳定运行；CLI mock 路径存在无工具调用死循环；Vercel WebUI 500 需要定位；真实 API 和 Docker 需要交付前验证。
- **Result:**
  - `pytest tests/ -v` 通过：`213 passed, 1 skipped`
  - 唯一 skipped 测试为 `test_openai_provider_can_be_created_via_factory`，原因是本地未设置 `OPENAI_API_KEY` 时跳过真实 OpenAI-compatible Provider 实例化检查，以保证默认测试不依赖真实凭据
  - 修复 `HarnessLoop` 文本但无 tool call 时无限循环的问题，改为确定性失败退出
  - CLI 输出改为 ASCII，避免 Windows GBK 下 `UnicodeEncodeError`
  - 新增 `tests/test_src_suite.py`，兼容顶层 `pytest tests/ -v`
  - pytest 临时目录固定为 `.pytest_tmp`，并加入 `.gitignore`
  - WebUI 本地健康检查通过：`GET / -> 200`，`POST /run -> 200`
  - 补齐 Vercel/FastAPI 依赖：`fastapi`、`uvicorn`、`python-multipart`
  - 配置 Vercel 入口：根目录 `app.py` + `[tool.vercel] entrypoint = "app:app"`
  - 删除旧 `vercel.json` 的 `builds/routes` 配置，避免覆盖官方 Python runtime 入口
  - WebUI 改为内联 HTML，避免模板文件打包缺失导致首页 500
  - 真实 API Fibonacci 调用通过：`SUCCESS - All tests passed`，`Iterations: 9`
  - 真实 API GCD 调用通过：`SUCCESS - All tests passed`，`Iterations: 3`
  - 本地 Real API LCM 调用通过：`SUCCESS - All tests passed`，`Iterations: 10`，作为最终手动验证记录；长期提交的真实 API 证据仍以 `workspace/fib/` 与 `workspace/gcd/` 为准
  - 真实 API 证据目录：`workspace/fib/`、`workspace/gcd/`
  - WebUI Real API 与 Mock demo 均完成手动检查；`Run` 按钮在运行中显示 `Running` 并禁用，API Key 仅在当前浏览器标签页 `sessionStorage` 保留，不由服务端持久化或回显
  - Docker 验证通过：`docker build -t tdd-harness .` 成功，`docker run --rm tdd-harness --help` 成功
  - Dockerfile 补充复制 `config.yaml`，容器内默认 CLI 配置可解析
- **Reflection:** 最终问题集中在运行环境边界和交付命令一致性，而不是核心机制缺失。将测试入口、临时目录、WebUI 依赖和 CLI 输出做成确定性行为后，项目更适合在评分环境和不同机器上复现。

---

## 汇总统计

| 指标 | 数值 |
|------|------|
| 计划 Task 数 | 21 |
| 实际实现记录 | T1-T19 + T20/T21 final hardening |
| 总 Commits | 23 |
| 源文件数 | ~40 Python files |
| 测试文件数 | 13 source test files + 1 compatibility entry |
| 总测试数 | 214 collected (`213 passed, 1 skipped`; skipped 为未设置 `OPENAI_API_KEY` 时的 OpenAI provider 实例化检查) |
| Demo 脚本 | 3 |

---

*Last updated on 2026-07-09 by Codex*
