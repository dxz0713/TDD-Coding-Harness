# PLAN · 实现计划

> **项目名称：** TDD Coding Harness
>
> **对应 SPEC：** `docs/SPEC.md` v1.0
>
> **总任务数：** 21
>
> **Story Point 说明：** SP1=简单（~15min），SP2=中等（~30min），SP3=较复杂（~1h）

---

## 系统架构图

```
┌───────────────────────────────────────────────────────────────┐
│                         CLI (typer)                            │
│  tdd-harness run "task" --provider mock --model gpt-4o        │
└─────────────────────────┬─────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────┐
│                         Config                                 │
│  CLI 参数 > config.yaml > 默认值                               │
│  ProviderFactory.create(config) → Provider 实例                │
└─────────────────────────┬─────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────┐
│                      Harness Main Loop                         │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  Build   │  │  Call    │  │  Decision    │  │Guardrail │  │
│  │ Context  │→│ Provider │→│  Layer ①     │→│  Check   │  │
│  └──────────┘  └──────────┘  └──────────────┘  └─────┬────┘  │
│                                                       │       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │       │
│  │  Stop    │←│  Feedback│←│  Collect │←────────────┘       │
│  │ Decision │  │  Engine  │  │  Result  │   ┌──────────┐    │
│  └──────────┘  └──────────┘  └──────────┘   │ Dispatch │    │
│       │                                      │  Tool    │    │
│       ▼                                      └──────────┘    │
│  ┌──────────┐                                                │
│  │  Memory  │  (Context 持久化)                               │
│  └──────────┘                                                │
└───────────────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌──────────────────────────────────────────────────┐
    │         Feedback Engine · Adaptive Repair          │
    │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
    │  │Collector │→│ Analyzer │→│ Adaptive       │  │
    │  │(原始输出)  │  │(失败分类)  │  │ Repair Strategy│  │
    │  └──────────┘  └──────────┘  └────────────────┘  │
    └──────────────────────────────────────────────────┘

① Decision Layer: 重复 Tool 去重、重复错误检测、Retry Policy、Stop Policy
   （Harness 自主决策，不依赖 LLM 判断）
```
```

---

## 目录规划

```
src/
├── harness/
│   ├── __init__.py
│   ├── cli.py         # CLI 入口（T3）— 放在 harness/ 下避免全局命名冲突
│   ├── models.py       # 数据模型（T2）
│   ├── config.py       # 配置加载（T2）
│   ├── loop.py         # 主循环（T11）
│   ├── context.py      # 上下文管理（T12）
│   ├── stop_condition.py # 停机条件（T13）
│   ├── guardrail.py    # 治理护栏（T10）
│   └── memory.py       # 记忆（T14）
├── providers/
│   ├── __init__.py
│   ├── base.py         # LLMProvider 抽象基类（T4）
│   ├── factory.py      # ProviderFactory（T4）
│   ├── mock.py         # MockProvider（T4）
│   └── openai_compat.py # OpenAICompatibleProvider（T5）
├── tools/
│   ├── __init__.py
│   ├── base.py         # BaseTool 抽象类（T6）
│   ├── dispatcher.py   # ToolDispatcher（T6）
│   ├── read_file.py    # ReadFile（T7）
│   ├── write_file.py   # WriteFile（T8）
│   └── run_shell.py    # RunShell（T9）
├── feedback/
│   ├── __init__.py
│   ├── models.py       # 反馈数据模型（T15）
│   ├── analyzer.py     # Collector + FailureAnalyzer（T16）
│   └── engine.py       # 反馈引擎 + 策略（T17）
├── tests/
│   ├── __init__.py, conftest.py
│   ├── test_models.py, test_config.py
│   ├── test_providers.py, test_tools.py, test_dispatcher.py
│   ├── test_guardrail.py, test_memory.py, test_context.py
│   ├── test_stop_condition.py, test_loop.py
│   ├── test_feedback_models.py, test_analyzer.py, test_feedback_engine.py
│   ├── test_cli.py, test_loop_integration.py
│   └── ...
└── examples/
    ├── demo_guardrail.py           # Guardrail 机制演示（T19）
    ├── demo_feedback.py            # Feedback 机制演示（T19）
    └── demo_autonomous_repair.py   # 自适应修复完整周期演示（T19）
```

---

## 依赖关系图

```
Phase 1: Foundation
  T1 ──→ T2
         │
Phase 2: CLI + Provider         │
  T3 (CLI)    T4 (LLM 抽象 + Mock + Factory)
         │      │
         └──────┘──→ T5 (OpenAICompatible)
                    │
Phase 3: Tools      │
  T6 (BaseTool + Dispatcher) ──→ T7 (ReadFile)
         │                        ├──→ T8 (WriteFile)
         │                        └──→ T9 (RunShell)
         │
Phase 4: Core
  T10 (Guardrail) ──→ T11 (Loop Framework)
         │              │
         │              ├──→ T12 (Context)
         │              │
         │              ├──→ T13 (Stop Conditions)
         │              │
         │              └──→ T14 (Memory)
         │
Phase 5: Feedback ⭐
  T15 (Models) ──→ T16 (Collector + Analyzer) ──→ T17 (Engine + Strategies)
         │
Phase 6: Integration
  T18 (Feedback → Loop) ──→ T19 (Demo Scripts)
         │
Phase 7: Delivery
  T20 (README Final) ──→ T21 (AGENT_LOG + Final Verify)
```

---

## 开发规则（Development Rules）

每个 Task 严格遵循以下流程：

```
① 创建 Worktree: git worktree add ../tdd-harness-<task-name>
② 编写失败测试: pytest 运行 → RED
③ 编写最少实现: 使测试通过 → GREEN
④ 重构: 优化代码质量
⑤ 提交 PR: git commit + PR（含 subagent 标注）
⑥ 代码审查: 检查 SPEC 合规 + 代码质量
⑦ Merge: 合并到主分支
⑧ 更新 docs/AGENT_LOG.md: 记录关键节点与教训
```

**通用 DoD（Definition of Done）：**

```
□ pytest 测试通过（全部）
□ 测试覆盖核心逻辑（边界条件 + 错误路径）
□ 类型提示完整（Python type hints）
□ SPEC 合规检查通过
□ 更新 docs/AGENT_LOG.md
```

---

## 项目边界（Out of Scope）

以下功能明确不包含在 MVP 中：

| 功能 | 理由 |
|------|------|
| 多 Agent 协作 | A 类要求的是单 Agent Harness |
| GUI / Web UI | 项目定位为 CLI 工具 |
| IDE 插件（VS Code 等） | 超过课程项目范围 |
| RAG / 向量数据库 | Memory 最小实现无需检索增强 |
| LangGraph / CrewAI / AutoGen | A 类要求自行实现 Harness 内核 |
| 远程 Sandbox | 单机工具无需远程执行 |
| 流式 Tool Calling | 增加复杂度，MVP 不做 |
| 并行任务执行 | 单线程主循环，MVP 不做 |

---

## Phase 1：Foundation（2 个 Task）

**Milestone：** 项目可安装、可导入、配置可加载、Docker 可构建、CI 自动运行测试

### T1：项目脚手架（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 建立项目基础结构，确保可安装、可构建 |
| **涉及文件** | `pyproject.toml`, `.gitignore`, `Dockerfile`, `.dockerignore`, `.gitlab-ci.yml`（或 `.github/workflows/ci.yml`）, `src/__init__.py`, `src/harness/__init__.py`, `src/tools/__init__.py`, `src/providers/__init__.py`, `src/feedback/__init__.py`, `src/tests/__init__.py`, `README.md`（初版） |
| **实现要点** | ① pyproject.toml 定义项目元数据、依赖（pydantic, typer, pyyaml, openai, python-dotenv）、`[project.scripts]` 入口 ② 创建所有 `__init__.py` ③ Dockerfile 基于 `python:3.12-slim` ④ CI 配置：按实际平台选择 `.gitlab-ci.yml` 或 `.github/workflows/ci.yml`，必须包含 `unit-test` job（pytest 一键运行）⑤ README 初版写项目简介和快速开始 |

**DoD：**
- `pytest --version` 可运行
- `docker build -t tdd-harness .` 成功
- `docker run --rm tdd-harness --help` 显示帮助
- CI 配置语法正确

**完成状态：** ✅ `d687c24`

---

### T2：数据模型 + Config 加载（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §6 的所有核心实体和 §3.8 的 Config 加载 |
| **涉及文件** | `src/harness/models.py`, `src/harness/config.py`, `src/tests/test_models.py`, `src/tests/test_config.py`, `config.yaml` |
| **实现要点** | ① 所有 pydantic 模型（Message, ToolDef, ToolCall, LLMResponse, FailureType, AnalysisResult, Feedback, GuardrailResult, StopDecision, Decision, Memory, Context, RunResult）② **`ToolResult` 统一数据结构**：所有工具返回相同格式 `ToolResult(success, output, error, exit_code, artifact=None, metadata={})`，Dispatcher 和 Feedback Engine 无需针对不同工具写特殊处理 ③ Config 从 YAML 加载，支持默认值 ④ 支持 CLI 参数覆盖（预留 merge 方法）⑤ `config.yaml` 作为默认配置文件 |

**ToolResult 统一结构：**
```python
class ToolResult(BaseModel):
    success: bool
    output: str = ""          # stdout 内容
    error: str | None = None  # stderr 或错误信息
    exit_code: int | None = None
    artifact: str | None = None   # 可选产物（如读到的文件内容）
    metadata: dict = {}            # 可选元数据
```

**测试（先红后绿）：**
- `test_config_load_defaults`：空配置 → 返回默认值
- `test_config_load_from_file`：加载 YAML → 验证字段值
- `test_config_cli_override`：CLI 参数覆盖配置文件
- `test_model_serialization`：创建 Message → 序列化 JSON → 反序列化

**DoD：**
- ✅ 测试通过
- ✅ 类型提示完整

**完成状态：** ✅ `d687c24`

---

## Phase 2：CLI + Provider（3 个 Task）

**Milestone：** 可通过 CLI 运行 Harness（Mock 模式），可在不同 Provider/模型间切换

### T3：CLI 入口（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.9，基于 typer 的命令行接口 |
| **涉及文件** | `src/harness/cli.py`, `src/tests/test_cli.py` |
| **实现要点** | ① `tdd-harness run` 命令：接受 task 参数 + `--config`/`--provider`/`--model` 选项 ② `tdd-harness demo` 命令框架（子命令占位）③ 配置优先级：CLI 参数 > 配置文件 > 默认值 ④ 入口注册在 `pyproject.toml` 的 `[project.scripts]`（`tdd-harness = "harness.cli:app"`）⑤ CLI 模块放在 `harness/` 下而非 `src/` 根目录，避免与同环境其他项目的 `tdd-harness` 入口产生命名冲突 |

**测试（先红后绿）：**
- `test_cli_run_help`：`tdd-harness run --help` → 显示帮助
- `test_cli_run_with_provider_override`：`--provider mock` → Config 被覆盖

**DoD：**
- ✅ 测试通过
- ✅ `tdd-harness` 命令可运行

**完成状态：** ✅ `0f7247c`

---

### T4：LLMProvider 抽象基类 + MockProvider + ProviderFactory（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.1.1 + §3.1.2，建立 LLM 抽象层和工厂 |
| **涉及文件** | `src/providers/base.py`, `src/providers/mock.py`, `src/providers/factory.py`, `src/tests/test_providers.py` |
| **实现要点** | ① `LLMProvider` 抽象基类（ABC），定义 `generate(messages, tools, config) → LLMResponse` ② `MockProvider` 持有 `preset_responses: Dict[str, LLMResponse]`，按输入消息匹配 ③ 不匹配时返回默认响应 ④ **`ProviderFactory` 使用注册机制**：`ProviderFactory.register("mock", MockProvider)`、`ProviderFactory.register("openai", OpenAICompatibleProvider)`，创建时 `ProviderFactory.create(config)` 自动根据 `config.provider.name` 查找注册的类并实例化 ⑤ 新增 Provider 只需注册一行，不修改 Factory 源码 ⑥ 错误边界：超时、认证异常 |

**测试（先红后绿）：**
- `test_mock_provider_returns_preset`：输入特定消息 → 返回预设响应
- `test_mock_provider_default`：未预设消息 → 返回默认响应
- `test_mock_provider_tool_call`：Mock 返回包含 ToolCall 的响应
- `test_factory_creates_mock`：`name=mock` → 返回 MockProvider 实例
- `test_factory_creates_openai`：`name=openai` → 返回 OpenAICompatibleProvider 实例

**DoD：**
- ✅ 测试通过
- ✅ Factory 可创建全部 Provider 类型

**完成状态：** ✅ `0f7247c`

---

### T5：OpenAICompatibleProvider（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现兼容 OpenAI API 格式的 Provider（可对接 OpenAI、DeepSeek、Qwen 等） |
| **涉及文件** | `src/providers/openai_compat.py`, `src/tests/test_providers.py` |
| **实现要点** | ① 调用 OpenAI Chat Completions API（兼容接口）② 支持 tool calling（function calling）③ 配置从 `LLMConfig` 读取 ④ `base_url` 可配置，支持第三方 API ⑤ 错误处理：超时、认证失败、速率限制 |

**配置示例（三个模型通过同一 Provider 切换）：**

```yaml
# config.yaml
provider:
  name: openai
  base_url: https://api.example.com/v1
  api_key_env: LLM_API_KEY
  model: deepseek-v4-pro         # 切换为此行即可换模型
  # model: deepseek-v4-flash
  # model: qwen3.7-max
  # model: Qwen2.5-14B-Instruct
```

**测试（先红后绿）：**
- `test_openai_compat_requires_api_key`：无 API Key → `LLMAuthError`
- `test_openai_compat_tool_def_format`：ToolDef 转换为 OpenAI tool format 正确

**DoD：**
- ✅ 测试通过
- ✅ 支持 `base_url` 配置
- ✅ 切换模型仅需修改 `model` 字段，无需改代码

**完成状态：** ✅ `c639657`

---

## Phase 3：Tools（4 个 Task）

**Milestone：** 工具可独立工作，Agent 能读写文件和执行命令

### T6：BaseTool 抽象类 + ToolDispatcher（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.3 + §3.4.0，建立工具分发机制 |
| **涉及文件** | `src/tools/base.py`, `src/tools/dispatcher.py`, `src/tests/test_dispatcher.py` |
| **实现要点** | ① `BaseTool(ABC)` 定义 `name: str`, `description: str`, `input_schema: dict` 类属性 + `execute(arguments: dict) → ToolResult` 抽象方法 ② Tool 自带元数据，Dispatcher 注册时自动读取 `tool.name`，避免 `register("read_file", WriteFile())` 这类人为错误 ③ `ToolDispatcher` 维护 `name→tool` 映射，`register(tool: BaseTool)` 和 `dispatch(tool_call) → ToolResult` 方法 ④ 未注册的工具返回错误结果 |

**Tool 注册示例：**
```python
dispatcher.register(ReadFile())     # 自动读取 ReadFile.name = "read_file"
dispatcher.register(WriteFile())    # 自动读取 WriteFile.name = "write_file"
dispatcher.register(RunShell())     # 自动读取 RunShell.name = "run_shell"
```

**测试（先红后绿）：**
- `test_dispatcher_register_and_dispatch`：注册 → 分发 → 验证调用
- `test_dispatcher_unknown_tool`：未注册工具 → 返回错误
- `test_dispatcher_routes_by_name`：多个工具 → 按名称路由正确

**DoD：**
- ✅ 测试通过
- ✅ 类型提示完整

**完成状态：** ✅ `0f7247c`

---

### T7：ReadFile 工具（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.1，读取文件内容 |
| **涉及文件** | `src/tools/read_file.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② 路径越界检查（不允许访问项目目录外）③ 文件不存在返回错误 ④ 使用 `pathlib` 处理路径 |

**测试（先红后绿）：**
- `test_read_file_success`：创建临时文件 → 读取 → 验证内容
- `test_read_file_not_found`：不存在文件 → 返回错误
- `test_read_file_path_traversal`：`../` 越界 → PathViolationError

**DoD：**
- ✅ 测试通过（含边界条件）

**完成状态：** ✅ `c639657`

---

### T8：WriteFile 工具（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.2，写入文件内容 |
| **涉及文件** | `src/tools/write_file.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② 路径越界检查 ③ 自动创建父目录 |

**测试（先红后绿）：**
- `test_write_file_success`：写入 → 验证内容和路径
- `test_write_file_path_traversal`：越界 → PathViolationError
- `test_write_file_creates_parent_dirs`：深层路径 → 自动创建目录

**DoD：**
- ✅ 测试通过（含边界条件）

**完成状态：** ✅ `c639657`

---

### T9：RunShell 工具（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.3，执行 Shell 命令 |
| **涉及文件** | `src/tools/run_shell.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② `subprocess.run()` 执行 ③ 超时控制（默认 30s）④ 捕获 stdout/stderr/exit_code ⑤ **支持 `cwd` 参数**：指定命令工作目录，后续 `pytest tests/`、`python main.py` 无需 Loop 切换目录 |

**输入结构：**
```python
class RunShellInput(BaseModel):
    command: str
    timeout: int = 30
    cwd: str | None = None  # 工作目录，None 表示当前目录
```

**风险：** Windows 与 Linux 的 Shell 命令差异（如 `echo` 行为），测试时注意跨平台兼容

**测试（先红后绿）：**
- `test_run_shell_echo`：`echo hello` → stdout 包含 "hello"
- `test_run_shell_failure`：`exit 1` → exit_code=1, success=False
- `test_run_shell_timeout`：`sleep 100` 超时 1s → TimeoutError

**DoD：**
- ✅ 测试通过（含超时边界）

**完成状态：** ✅ `c639657`

---

## Phase 4：Core（5 个 Task）

**Milestone：** Harness 可运行完整的主循环（Mock 模式），能拦截危险命令，支持记忆持久化

### T10：Guardrail（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.6，治理护栏 |
| **涉及文件** | `src/harness/guardrail.py`, `src/tests/test_guardrail.py` |
| **实现要点** | ① `check_tool_call(tool_call: ToolCall) → GuardrailResult` ② 提取命令参数（RunShell 的 command 字段）与危险模式匹配 ③ 模式可配置（`block_list`）④ 安全命令直接放行 ⑤ HITL 确认预留接口（Mock 模式自动拒绝） |

**测试（先红后绿）：**
- `test_guardrail_blocks_rm_rf`：`rm -rf /` → 拦截
- `test_guardrail_blocks_drop_table`：`DROP TABLE users` → 拦截
- `test_guardrail_blocks_fork_bomb`：`:(){ :|:& };:` → 拦截
- `test_guardrail_allows_safe_command`：`pytest tests/` → 放行
- `test_guardrail_configurable_block_list`：自定义 block_list → 新增模式生效

**DoD：**
- ✅ 测试通过（含全部危险模式）

**完成状态：** ✅ `95e3918`

---

### T11：Main Loop 框架（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.2 的主循环骨架 |
| **涉及文件** | `src/harness/loop.py`, `src/harness/context.py`, `src/harness/stop_condition.py`, `src/tests/test_loop.py` |
| **设计原则：** 依赖注入。Loop 不负责创建 Provider、Dispatcher、Guardrail、Memory、FeedbackEngine、StopCondition，全部由外部注入 |
| **职责边界：** Loop **只负责流程控制**，不实现任何具体逻辑。Context 拼接委托给 `ContextManager`，停机判断委托给 `StopCondition`，反馈分析委托给 `FeedbackEngine`，记忆读写委托给 `Memory` |
| **Harness Superpowers（自主决策职责）：** Loop 在执行工具调用前插入 Decision Layer，负责以下自主决策（不依赖 LLM 判断）：① 重复 Tool 去重 — 相同参数的同名工具不重复执行 ② 重复错误检测 — 同一错误连续出现 N 次走止损策略 ③ Retry Policy — 失败工具按策略重试（而非每次都问 LLM）④ Tool Cache — 幂等的读取操作结果缓存 ⑤ Short-circuit — 无用调用（如空参数）直接跳过 |
| **实现要点** | ① `run(task, config) → RunResult` ② 主循环流程：`ContextManager.build()` → `Provider.generate()` → **Decision Layer（去重/缓存/策略）** → `Guardrail.check_tool_call()` → `Dispatcher.dispatch()` → `FeedbackEngine.analyze()` → `AutonomousStopDecision.should_stop()` → 循环/终止 ③ 构造注入所有依赖 ④ **`Finish` 是内置虚拟工具（Virtual Tool）**：不对应实际 Dispatcher（不进入 `dispatch()`），由 Loop 直接识别并交由 `AutonomousStopDecision.on_finish()` 处理。协议格式：`ToolCall(name="finish", arguments={"reason": "tests passed"})`，`reason` 字段记录结束原因 |

**伪代码：**
```python
def run(self, task, config):
    ctx = self.context_manager.build(task)
    while True:
        response = self.provider.generate(ctx.messages, self.tool_defs, config)
        for tool_call in response.tool_calls:
            if tool_call.name == "finish":
                return self.stop_condition.on_finish(tool_call)
            guard = self.guardrail.check_tool_call(tool_call)
            if not guard.allowed:
                return RunResult(success=False, error=guard.reason)
            result = self.dispatcher.dispatch(tool_call)
            ctx = self.context_manager.append_tool_result(ctx, tool_call, result)
            if result.exit_code is not None:  # 测试命令
                feedback = self.feedback_engine.analyze(result, ctx)
                if feedback:
                    ctx = self.context_manager.append_feedback(ctx, feedback)
            decision = self.stop_condition.should_stop(ctx)
            if decision.should_stop:
                return RunResult(success=decision.success, ...)
```

**测试（先红后绿）：**
- `test_loop_with_mock_finish`：MockProvider 返回 Finish → 成功停机
- `test_loop_read_write_cycle`：MockProvider 返回 ReadFile→WriteFile→Finish → 完整周期

**DoD：**
- ✅ 测试通过
- ✅ 依赖注入正确

**完成状态：** ✅ `009cb4a`

---

### T12：Context 管理（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 Context 的构建、更新、回灌逻辑，独立为 `ContextManager` 类 |
| **涉及文件** | `src/harness/context.py`, `src/tests/test_context.py` |
| **实现要点** | ① `ContextManager` 类负责系统提示词构建（含任务描述、工具定义）② 每次 LLM 响应后追加到 messages ③ 工具执行结果回灌（tool result → message）④ Feedback 回灌（追加到下一轮 LLM 调用）⑤ Loop 调用 `context_manager.build()` 和 `context_manager.append()` 而非自行管理 |

**测试（先红后绿）：**
- `test_context_build_system_prompt`：包含任务描述 + 工具定义
- `test_context_append_tool_result`：工具结果追加后 messages 长度增加

**DoD：**
- ✅ 测试通过
- ✅ messages 结构正确

**完成状态：** ✅ `95e3918`

---

### T13：停机条件 — Autonomous Stop Decision（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.2 中定义的四种停机条件，独立为 `AutonomousStopDecision` 类。强调停机是 **Harness 自主决定**，而非 LLM 决定 |
| **涉及文件** | `src/harness/stop_condition.py`, `src/tests/test_stop_condition.py` |
| **实现要点** | ① `AutonomousStopDecision` 类判断四种停机条件：测试全部通过 / 达到最大迭代次数 / LLM 返回 Finish / Guardrail 拦截致命动作 ② `should_stop(context) → StopDecision` ③ **`StopDecision` 对象**包含 `should_stop: bool`, `success: bool`, `reason: str`，避免元组无法区分"成功结束"与"失败结束" ④ 由外部注入到 Loop ⑤ `Finish` 是内置虚拟工具（Virtual Tool），不对应实际 Dispatcher，仅作为 Agent 主动结束任务的协议信号 |

**StopDecision 结构：**
```python
class StopDecision(BaseModel):
    should_stop: bool
    success: bool
    reason: str = ""
```

**测试（先红后绿）：**
- `test_stop_condition_max_iterations`：持续返回工具调用 → 达到上限后停机
- `test_stop_condition_guardrail_blocks`：Guardrail 拦截 → 停机
- `test_stop_condition_finish_success`：Finish 且测试通过 → 成功
- `test_stop_condition_finish_failure`：Finish 但测试失败 → 失败

**DoD：**
- ✅ 四种停机条件全部覆盖

**完成状态：** ✅ `95e3918`

---

### T14：Memory（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.7，JSON 文件记忆 |
| **涉及文件** | `src/harness/memory.py`, `src/tests/test_memory.py` |
| **实现要点** | ① `load()` / `save()` / `add_decision()` / `get_context()` ② 超过 1MB 自动截断（保留最近 100 条）③ 文件不存在时返回空 Memory |

**测试（先红后绿）：**
- `test_memory_save_and_load`：写入→读取→一致
- `test_memory_add_decision`：追加决策→验证内容
- `test_memory_get_context`：返回格式化字符串
- `test_memory_auto_truncate`：超限→截断保留最近 N 条

**DoD：**
- ✅ 测试通过
- ✅ 截断策略正确

**完成状态：** ✅ `95e3918`

---

## Phase 5：Feedback Engine（3 个 Task）⭐ 主要贡献

**Milestone：** 自适应修复引擎可对 pytest 输出进行分类，生成差异化的修复 Prompt

### T15：Feedback 数据模型（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.1 + §3.5.2，反馈引擎的基础数据结构 |
| **涉及文件** | `src/feedback/models.py`, `src/tests/test_feedback_models.py` |
| **实现要点** | ① `FailureType` 枚举（7 种类型）② `AnalysisResult` 模型（含 location, error_message, assertion_expected/actual, raw_snippet）③ `Feedback` 模型（含 failure_type, summary, details, repair_prompt） |

**测试（先红后绿）：**
- `test_failure_type_values`：7 种类型值正确
- `test_analysis_result_serialization`：序列化→反序列化一致
- `test_feedback_contains_repair_prompt`：Feedback 包含 repair_prompt

**DoD：**
- ✅ 测试通过
- ✅ 类型提示完整

**完成状态：** ✅ `99bb011`

---

### T16：Collector + FailureAnalyzer（SP3）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.1（Collector）+ §3.5.3（Analyzer），收集原始输出并分类失败类型 |
| **涉及文件** | `src/feedback/analyzer.py`, `src/tests/test_analyzer.py` |
| **实现要点** | ① **`Collector` 类**：从 ToolResult 提取 stdout/stderr/exit_code，去除 ANSI 转义序列，提取关键行（失败测试名称、错误行号）② **`FailureAnalyzer` 类**：接收 Collector 处理后的输出，通过正则/模式匹配解析 pytest 输出 ③ 区分 SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_ERROR / TIMEOUT / RUNTIME_ERROR / TEST_FAILURE / UNKNOWN ④ AssertionError 提取预期值和实际值 ⑤ 提取失败位置（文件:行号）|

**代码结构：** `Collector` 和 `FailureAnalyzer` 是独立的两个类，职责分离。即使它们在一个 Task 中实现，代码不合并。

**风险：** Windows 与 Linux 的 pytest 输出格式可能略有差异，测试时需覆盖两种格式

**测试（先红后绿）：**
- `test_analyzer_strips_ansi`：含 ANSI 转义 → 去除转义
- `test_analyzer_syntax_error`：注入 SyntaxError → 分类 SYNTAX_ERROR
- `test_analyzer_import_error`：注入 ImportError → 分类 IMPORT_ERROR
- `test_analyzer_assertion_error`：注入 AssertionError → ASSERTION_ERROR + 提取预期/实际值
- `test_analyzer_timeout`：注入超时 → 分类 TIMEOUT
- `test_analyzer_runtime_error`：注入运行时异常 → RUNTIME_ERROR
- `test_analyzer_pytest_failure`：注入测试失败 → TEST_FAILURE
- `test_analyzer_unknown`：无关输出 → UNKNOWN

**DoD：**
- ✅ 7 种失败类型全部覆盖
- ✅ AssertionError 提取预期/实际值

**完成状态：** ✅ `009cb4a`

---

### T17：FeedbackEngine + 自适应修复策略（Adaptive Repair）（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.4，完整的反馈引擎，连接 Collector + Analyzer + 自适应修复策略 |
| **涉及文件** | `src/feedback/engine.py`, `src/feedback/strategies.py`, `src/tests/test_feedback_engine.py` |
| **实现要点** | ① `FeedbackEngine.analyze(tool_result, context) → Feedback | None` ② 调用 Collector → Analyzer → 策略选择 ③ **使用策略映射**：`strategy_map[FailureType] → RepairStrategy`，每种 FailureType 对应一个策略类，新增类型只需添加策略不修改 Engine ④ 成功结果返回 None |

**策略映射示例：**
```python
class RepairStrategy(ABC):
    def generate(self, analysis: AnalysisResult) -> str: ...

class SyntaxStrategy(RepairStrategy): ...
class AssertionStrategy(RepairStrategy): ...

strategy_map = {
    FailureType.SYNTAX_ERROR: SyntaxStrategy(),
    FailureType.ASSERTION_ERROR: AssertionStrategy(),
    ...
}
# Engine 中：strategy = strategy_map[analysis.failure_type]
```

**策略表：**

| FailureType | 修复 Prompt 策略 |
|---|---|
| SYNTAX_ERROR | 提取错误位置 + 期望语法结构，生成精确修复提示 |
| IMPORT_ERROR | 提取缺失模块名，建议安装或修正导入路径 |
| ASSERTION_ERROR | 提取预期值 vs 实际值，生成针对性修复提示 |
| TIMEOUT | 建议优化算法复杂度或增加超时时间 |
| RUNTIME_ERROR | 提取异常类型 + 堆栈，生成通用修复提示 |
| TEST_FAILURE | 提取失败测试名称 + 输出，生成通用修复提示 |
| UNKNOWN | 返回原始输出，泛化重试提示 |

**测试（先红后绿）：**
- `test_feedback_engine_syntax_error`：注入 SyntaxError 结果 → SYNTAX_ERROR
- `test_feedback_engine_assertion_error`：注入 AssertionError → 含预期/实际值
- `test_feedback_engine_different_prompts`：不同 FailureType → repair_prompt 不同
- `test_feedback_engine_no_failure`：成功结果 → 返回 None

**DoD：**
- ✅ 7 种类型全部有对应策略
- ✅ 成功结果不产生 Feedback

**完成状态：** ✅ `3a2b89c`

---

## Phase 6：Integration（2 个 Task）

**Milestone：** 完整 TDD 闭环可运行，机制可演示

### T18：集成 Feedback Engine 到 Main Loop（SP3）

| 字段 | 内容 |
|------|------|
| **目标** | 将 Feedback Engine 接入主循环，实现完整的 TDD 闭环 |
| **涉及文件** | `src/harness/loop.py`, `src/feedback/engine.py`, `src/tests/test_loop_integration.py` |
| **实现要点** | ① RunShell 执行测试后 → 调用 FeedbackEngine.analyze() ② 分析结果回灌到 LLM 上下文 ③ 日志记录 Feedback 分类结果 ④ 止损策略：连续 N 次同一类型错误 → 停机 |

**测试（先红后绿）：**
- `test_loop_feedback_fix_cycle`：Mock 模拟"写代码→测试失败→修复→通过"完整周期
- `test_loop_feedback_max_retries`：持续同一错误 → 达到迭代上限后停机
- `test_loop_feedback_logs`：日志包含 Feedback 分类结果

**DoD：**
- ✅ 完整闭环可运行
- ✅ 日志记录完整

**完成状态：** ✅ `d4643d4`

---

### T19：机制演示脚本（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §9.3，三个可在 Mock LLM 下确定性复现的机制演示 |
| **涉及文件** | `examples/demo_guardrail.py`, `examples/demo_feedback.py`, `examples/demo_autonomous_repair.py` |
| **实现要点** | ① Guardrail 演示：构造危险命令 → 拦截 → 输出结果 ② Feedback 演示：注入测试输出 → Analyzer 分类 → 生成修复 Prompt ③ 完整周期：Mock 驱动"写代码→测试→修复→通过"流程 |

**DoD：**
- ✅ 三个脚本可独立运行
- ✅ 输出确定性结果（不依赖网络）

**完成状态：** ✅ `d4643d4`

---

## Phase 7：Delivery（2 个 Task）

**Milestone：** 项目可交付、可运行、文档完整

### T20：README 完善（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 完成 README，包含所有必需章节（**初版已在 T1 创建**：Install + Quick Start；开发过程中持续更新；T20 补全其余章节） |
| **涉及文件** | `README.md` |
| **实现要点** | ① 项目简介 + 安装步骤（pip install / docker）② 运行命令 + 分发命令 ③ 完整目录结构 ④ **安全边界说明（Key 配置方式）** ⑤ Architecture + Configuration + Demo + Known Issues 章节 |

**两阶段策略：**
- T1：创建 `README.md` 初版（项目简介、Install、Quick Start、CI badge）
- 每完成一个 Phase，追加对应章节
- T20：补全 Architecture、Examples、Configuration、Demo、Known Issues、安全边界

**DoD：**
- ✅ 包含全部必需章节
- ✅ Key 安全配置方式写清

**完成状态：** ✅ `bb6a695`

---

### T21：AGENT_LOG + 最终验证（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 完成 docs/AGENT_LOG.md，做最终验证 |
| **涉及文件** | `docs/AGENT_LOG.md`, `docs/REFLECTION.md` |
| **实现要点** | ① docs/AGENT_LOG.md：按时间记录关键节点，每条记录包含 **Decision → Reason → Result → Reflection** 四段式格式 ② 验证所有机制演示可运行 ③ 验证 `pytest tests/` 全部通过 |

**AGENT_LOG 记录格式示例：**
```
## Iteration 4 — Feedback Engine

- Decision: Apply AssertionStrategy
- Reason: Expected 5 != Actual 3 (AssertionError)
- Result: Test passed after repair
- Reflection: Strategy works for simple arithmetic, needs refinement for edge cases
```

**DoD：**
- ✅ `pytest tests/` 全部通过
- ✅ 三个机制演示可运行
- ✅ AGENT_LOG 完整

**完成状态：** ✅ `bb6a695`

---

## Story Point 汇总

| Task | 名称 | SP | 阶段 |
|------|------|----|------|
| T1 | 项目脚手架（含 Docker + CI + README 初版） | 1 | Phase 1 |
| T2 | 数据模型 + Config | 1 | Phase 1 |
| T3 | CLI 入口 | 2 | Phase 2 |
| T4 | LLMProvider 抽象 + Mock + Factory | 2 | Phase 2 |
| T5 | OpenAICompatibleProvider | 1 | Phase 2 |
| T6 | BaseTool + Dispatcher | 1 | Phase 3 |
| T7 | ReadFile | 1 | Phase 3 |
| T8 | WriteFile | 1 | Phase 3 |
| T9 | RunShell | 1 | Phase 3 |
| T10 | Guardrail | 1 | Phase 4 |
| T11 | Main Loop 框架（依赖注入） | 2 | Phase 4 |
| T12 | Context 管理 | 2 | Phase 4 |
| T13 | 停机条件（StopCondition 独立类） | 2 | Phase 4 |
| T14 | Memory | 1 | Phase 4 |
| T15 | Feedback 数据模型 | 1 | Phase 5 ⭐ |
| T16 | Collector + FailureAnalyzer | 3 | Phase 5 ⭐ |
| T17 | FeedbackEngine + 策略 | 2 | Phase 5 ⭐ |
| T18 | 集成 Feedback → Loop | 3 | Phase 6 |
| T19 | 机制演示脚本（examples/） | 2 | Phase 6 |
| T20 | README 完善（两阶段策略） | 1 | Phase 7 |
| T21 | AGENT_LOG + 最终验证 | 1 | Phase 7 |
| | **合计** | **31 SP** | |

---

## 并行建议

| 并行组 | 包含 Task | 说明 |
|--------|----------|------|
| **Group A** | T7, T8, T9 | 三个工具互不依赖，可并行 |
| **Group B** | T12, T13, T14 | Context / 停机条件 / Memory 互不依赖，可并行 |
| **Group C** | T20, T21 | 文档收尾可并行 |

---

## 已识别的风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| OpenAI API 调用成本 | 集成测试产生费用 | MockProvider 覆盖单元测试；真实调用仅用于手动验证 |
| Windows/Linux Shell 差异 | RunShell 测试在 CI（Linux）可能行为不同 | 测试用例覆盖跨平台命令；CI 运行在 Linux 容器 |
| pytest 输出格式差异 | Analyzer 正则匹配可能因 pytest 版本不同而失效 | 测试用例覆盖多种 pytest 版本输出格式 |
| 项目范围膨胀 | 超出课程项目合理工作量 | 明确 MVP 边界；Memory 最小实现；先完成核心再扩展 |

---

> **对应 SPEC：** `docs/SPEC.md` v1.0
>
> **开发方式：** 每个 Task 一个 Worktree → TDD（先红后绿）→ PR → Merge → AGENT_LOG
>
> **下一阶段：** 冷启动验证（使用另一个 Agent 尝试实现 T1~T2）
