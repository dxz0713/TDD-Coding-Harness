# PLAN · 实现计划

> **项目名称：** TDD Coding Harness
>
> **对应 SPEC：** `docs/SPEC.md` v1.0
>
> **总任务数：** 22
>
> **Story Point 说明：** SP1=简单（~15min），SP2=中等（~30min），SP3=较复杂（~1h），SP5=复杂（~2h）

---

## 目录规划

```
src/
├── cli.py              # CLI 入口（T3）
├── harness/
│   ├── __init__.py
│   ├── models.py       # 数据模型（T2）
│   ├── config.py       # 配置加载（T2）
│   ├── loop.py         # 主循环（T11, T12, T13, T18）
│   ├── guardrail.py    # 治理护栏（T10）
│   └── memory.py       # 记忆（T19）
├── providers/
│   ├── __init__.py
│   ├── base.py         # LLMProvider 抽象基类（T4）
│   ├── mock.py         # MockProvider（T4）
│   └── openai_compat.py # OpenAICompatibleProvider（T5）
├── tools/
│   ├── __init__.py
│   ├── base.py         # BaseTool + Dispatcher（T6）
│   ├── read_file.py    # ReadFile（T7）
│   ├── write_file.py   # WriteFile（T8）
│   └── run_shell.py    # RunShell（T9）
├── feedback/
│   ├── __init__.py
│   ├── models.py       # 反馈数据模型（T14）
│   ├── collector.py    # 原始输出收集（T15）
│   ├── analyzer.py     # 失败分类（T16）
│   └── engine.py       # 反馈引擎 + 策略（T17）
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_providers.py
    ├── test_tools.py
    ├── test_dispatcher.py
    ├── test_guardrail.py
    ├── test_memory.py
    ├── test_loop.py
    ├── test_feedback_models.py
    ├── test_collector.py
    ├── test_analyzer.py
    ├── test_feedback_engine.py
    ├── test_cli.py
    └── test_loop_integration.py
```

---

## 依赖关系图

```
Phase 1: Foundation
  T1 ──→ T2
         │
Phase 2: CLI + Provider
         │
  T3 (CLI)    T4 (LLM 抽象 + Mock)
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
         │              ├──→ T12 (Context Management)
         │              │
         │              └──→ T13 (Stop Conditions)
         │
Phase 5: Feedback ⭐
  T14 (Models) ──→ T15 (Collector) ──→ T16 (Analyzer) ──→ T17 (Engine + Strategies)
         │
Phase 6: Integration
  T18 (Feedback → Loop) ──→ T19 (Memory) ──→ T20 (Demo)
         │
Phase 7: Delivery
  T21 (README) ──→ T22 (AGENT_LOG + Final)
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
⑧ 更新 AGENT_LOG: 记录关键节点与教训
```

**通用 DoD（Definition of Done）：**

```
□ pytest 测试通过（全部）
□ 测试覆盖核心逻辑（边界条件 + 错误路径）
□ 类型提示完整（Python type hints）
□ SPEC 合规检查通过
□ 更新 AGENT_LOG.md
```

---

## Phase 1：Foundation（2 个 Task）

**Milestone：** 项目可安装、可导入、配置可加载、Docker 可构建、CI 自动运行测试

### T1：项目脚手架（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 建立项目基础结构，确保可安装、可构建 |
| **涉及文件** | `pyproject.toml`, `.gitignore`, `Dockerfile`, `.dockerignore`, `.gitlab-ci.yml`, `src/__init__.py`, `src/harness/__init__.py`, `src/tools/__init__.py`, `src/providers/__init__.py`, `src/feedback/__init__.py`, `src/tests/__init__.py`, `README.md`（初版） |
| **实现要点** | ① pyproject.toml 定义项目元数据、依赖（pydantic, typer, pyyaml, openai, python-dotenv）、`[project.scripts]` 入口 ② 创建所有 `__init__.py` ③ Dockerfile 基于 `python:3.12-slim`，安装依赖 + 复制源码 ④ `.gitlab-ci.yml` 包含 `unit-test` job（pytest 一键运行）⑤ README 初版写项目简介和快速开始 |

**DoD：**
- `pytest --version` 可运行
- `docker build -t tdd-harness .` 成功
- `docker run --rm tdd-harness --help` 显示帮助
- CI 配置语法正确

---

### T2：数据模型 + Config 加载（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §6 的所有核心实体和 §3.8 的 Config 加载 |
| **涉及文件** | `src/harness/models.py`, `src/harness/config.py`, `src/tests/test_models.py`, `src/tests/test_config.py`, `config.yaml` |
| **实现要点** | ① 所有 pydantic 模型（Message, ToolDef, ToolCall, LLMResponse, ToolResult, FailureType, AnalysisResult, Feedback, GuardrailResult, Decision, Memory, Context, RunResult）② Config 从 YAML 加载，支持默认值 ③ 支持 CLI 参数覆盖（预留 merge 方法）④ `config.yaml` 作为默认配置文件 |

**测试（先红后绿）：**
- `test_config_load_defaults`：空配置 → 返回默认值
- `test_config_load_from_file`：加载 YAML → 验证字段值
- `test_config_cli_override`：CLI 参数覆盖配置文件
- `test_model_serialization`：创建 Message → 序列化 JSON → 反序列化

**DoD：**
- ✅ 测试通过
- ✅ 类型提示完整

---

## Phase 2：CLI + Provider（3 个 Task）

**Milestone：** 可通过 CLI 运行 Harness（Mock 模式），可在不同 Provider 间切换

### T3：CLI 入口（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.9，基于 typer 的命令行接口 |
| **涉及文件** | `src/cli.py`, `src/tests/test_cli.py` |
| **实现要点** | ① `tdd-harness run` 命令：接受 task 参数 + `--config`/`--provider`/`--model` 选项 ② `tdd-harness demo` 命令框架（子命令占位）③ 配置优先级：CLI 参数 > 配置文件 > 默认值 ④ 入口注册在 `pyproject.toml` 的 `[project.scripts]` |

**测试（先红后绿）：**
- `test_cli_run_help`：`tdd-harness run --help` → 显示帮助
- `test_cli_run_with_provider_override`：`--provider mock` → Config 被覆盖

**DoD：**
- ✅ 测试通过
- ✅ `tdd-harness` 命令可运行

---

### T4：LLMProvider 抽象基类 + MockProvider（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.1.1 + §3.1.2，建立 LLM 抽象层 |
| **涉及文件** | `src/providers/base.py`, `src/providers/mock.py`, `src/tests/test_providers.py` |
| **实现要点** | ① `LLMProvider` 抽象基类（ABC），定义 `generate(messages, tools, config) → LLMResponse` ② `MockProvider` 持有 `preset_responses: Dict[str, LLMResponse]`，按输入消息匹配 ③ 不匹配时返回默认响应 ④ 错误边界：超时、认证异常 |

**测试（先红后绿）：**
- `test_mock_provider_returns_preset`：输入特定消息 → 返回预设响应
- `test_mock_provider_default`：未预设消息 → 返回默认响应
- `test_mock_provider_tool_call`：Mock 返回包含 ToolCall 的响应

**DoD：**
- ✅ 测试通过
- ✅ 可通过 `--provider mock` 调用

---

### T5：OpenAICompatibleProvider（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现兼容 OpenAI API 格式的 Provider（可对接 OpenAI、DeepSeek、Qwen 等） |
| **涉及文件** | `src/providers/openai_compat.py`, `src/tests/test_providers.py` |
| **实现要点** | ① 调用 OpenAI Chat Completions API（兼容接口）② 支持 tool calling（function calling）③ 配置从 `LLMConfig` 读取 ④ `base_url` 可配置，支持第三方 API ⑤ 错误处理：超时、认证失败、速率限制 |

**测试（先红后绿）：**
- `test_openai_compat_requires_api_key`：无 API Key → `LLMAuthError`
- `test_openai_compat_tool_def_format`：ToolDef 转换为 OpenAI tool format 正确

**DoD：**
- ✅ 测试通过
- ✅ 支持 `base_url` 配置

---

## Phase 3：Tools（4 个 Task）

**Milestone：** 工具可独立工作，Agent 能读写文件和执行命令

### T6：BaseTool 抽象类 + ToolDispatcher（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.3 + §3.4.0，建立工具分发机制 |
| **涉及文件** | `src/tools/base.py`, `src/harness/dispatcher.py`, `src/tests/test_dispatcher.py` |
| **实现要点** | ① `BaseTool(ABC)` 定义 `execute(arguments: dict) → ToolResult` ② `ToolDispatcher` 维护 `name→tool` 映射 ③ `register(name, tool)` 和 `dispatch(tool_call)` 方法 ④ 未注册的工具返回错误结果 |

**测试（先红后绿）：**
- `test_dispatcher_register_and_dispatch`：注册 → 分发 → 验证调用
- `test_dispatcher_unknown_tool`：未注册工具 → 返回错误
- `test_dispatcher_routes_by_name`：多个工具 → 按名称路由正确

**DoD：**
- ✅ 测试通过
- ✅ 类型提示完整

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

---

### T9：RunShell 工具（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.3，执行 Shell 命令 |
| **涉及文件** | `src/tools/run_shell.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② `subprocess.run()` 执行 ③ 超时控制（默认 30s）④ 捕获 stdout/stderr/exit_code |

**风险：** Windows 与 Linux 的 Shell 命令差异（如 `echo` 行为），测试时注意跨平台兼容

**测试（先红后绿）：**
- `test_run_shell_echo`：`echo hello` → stdout 包含 "hello"
- `test_run_shell_failure`：`exit 1` → exit_code=1, success=False
- `test_run_shell_timeout`：`sleep 100` 超时 1s → TimeoutError

**DoD：**
- ✅ 测试通过（含超时边界）

---

## Phase 4：Core（4 个 Task）

**Milestone：** Harness 可运行完整的主循环（Mock 模式），能拦截危险命令

### T10：Guardrail（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.6，治理护栏 |
| **涉及文件** | `src/harness/guardrail.py`, `src/tests/test_guardrail.py` |
| **实现要点** | ① `check(action) → GuardrailResult` ② 危险命令模式匹配（SPEC 列出的所有模式）③ 模式可配置（`block_list`）④ 安全命令直接放行 ⑤ HITL 确认预留接口（Mock 模式自动拒绝） |

**测试（先红后绿）：**
- `test_guardrail_blocks_rm_rf`：`rm -rf /` → 拦截
- `test_guardrail_blocks_drop_table`：`DROP TABLE users` → 拦截
- `test_guardrail_blocks_fork_bomb`：`:(){ :|:& };:` → 拦截
- `test_guardrail_allows_safe_command`：`pytest tests/` → 放行
- `test_guardrail_configurable_block_list`：自定义 block_list → 新增模式生效

**DoD：**
- ✅ 测试通过（含全部危险模式）

---

### T11：Main Loop 框架（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.2 的主循环骨架：组织上下文 → 调用 LLM → 解析 → 分发 → 回灌 → 停机 |
| **涉及文件** | `src/harness/loop.py`, `src/tests/test_loop.py` |
| **实现要点** | ① `run(task, config) → RunResult` ② 主循环骨架：初始化 Context → 调用 LLM → 解析 ToolCall → Guardrail 检查 → 分发工具 → 收集结果 → 回灌 → 循环 ③ 依赖注入：接收 LLMProvider, ToolDispatcher, Guardrail 等实例 |

**测试（先红后绿）：**
- `test_loop_with_mock_finish`：MockProvider 返回 Finish → 成功停机
- `test_loop_read_write_cycle`：MockProvider 返回 ReadFile→WriteFile→Finish → 完整周期

**DoD：**
- ✅ 测试通过
- ✅ 依赖注入正确

---

### T12：Context 管理（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 Context 的构建、更新、回灌逻辑 |
| **涉及文件** | `src/harness/loop.py`（Context 方法）, `src/tests/test_loop.py` |
| **实现要点** | ① 系统提示词构建（含任务描述、工具定义）② 每次 LLM 响应后追加到 messages ③ 工具执行结果回灌（tool result → message）④ Feedback 回灌（追加到下一轮 LLM 调用） |

**测试（先红后绿）：**
- `test_context_build_system_prompt`：包含任务描述 + 工具定义
- `test_context_append_tool_result`：工具结果追加后 messages 长度增加

**DoD：**
- ✅ 测试通过
- ✅ messages 结构正确

---

### T13：停机条件（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.2 中定义的四种停机条件 |
| **涉及文件** | `src/harness/loop.py`, `src/tests/test_loop.py` |
| **实现要点** | ① 测试全部通过 → 成功 ② 达到最大迭代次数（默认 5）→ 失败 ③ LLM 返回 Finish 工具调用 → 按结果判定 ④ Guardrail 拦截致命动作且用户拒绝 → 失败 |

**测试（先红后绿）：**
- `test_loop_max_iterations`：持续返回工具调用 → 达到上限后停机
- `test_loop_guardrail_blocks`：MockProvider 返回危险命令 → Guardrail 拦截 → 停机
- `test_loop_finish_success`：Finish 且测试通过 → 成功
- `test_loop_finish_failure`：Finish 但测试失败 → 失败

**DoD：**
- ✅ 四种停机条件全部覆盖

---

## Phase 5：Feedback Engine（4 个 Task）⭐ 主要贡献

**Milestone：** Feedback Engine 可对 pytest 输出进行分类，生成差异化的修复 Prompt

### T14：Feedback 数据模型（SP1）

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

---

### T15：Collector（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.1 中的 Collector，收集原始输出 |
| **涉及文件** | `src/feedback/collector.py`, `src/tests/test_collector.py` |
| **实现要点** | ① 从 ToolResult 提取 stdout, stderr, exit_code ② 标准化输出格式（去除 ANSI 转义序列）③ 提取关键行（错误行、失败测试名称） |

**测试（先红后绿）：**
- `test_collector_extracts_stdout`：从 ToolResult 提取 stdout
- `test_collector_strips_ansi`：含 ANSI 转义的输出 → 去除转义
- `test_collector_extracts_failed_tests`：pytest 输出 → 提取 FAILED 测试名称

**DoD：**
- ✅ 测试通过
- ✅ 输出已标准化（无 ANSI 转义）

---

### T16：FailureAnalyzer（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.3，解析 pytest 输出，分类失败类型 |
| **涉及文件** | `src/feedback/analyzer.py`, `src/tests/test_analyzer.py` |
| **实现要点** | ① 正则/模式匹配解析 pytest stdout/stderr ② 区分 SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_ERROR / TIMEOUT / RUNTIME_ERROR / TEST_FAILURE / UNKNOWN ③ AssertionError 提取预期值和实际值 ④ 提取失败位置（文件:行号） |

**风险：** Windows 与 Linux 的 pytest 输出格式可能略有差异，测试时需覆盖两种格式

**测试（先红后绿）：**
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

---

### T17：FeedbackEngine + 修复策略（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.4，完整的反馈引擎，连接 Collector + Analyzer + 策略 |
| **涉及文件** | `src/feedback/engine.py`, `src/feedback/strategies.py`, `src/tests/test_feedback_engine.py` |
| **实现要点** | ① `FeedbackEngine.analyze(tool_result, context) → Feedback | None` ② 调用 Collector → Analyzer → 策略选择 ③ 每种 FailureType 生成差异化 repair_prompt ④ 成功结果返回 None |

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

---

## Phase 6：Integration（3 个 Task）

**Milestone：** 完整 TDD 闭环可运行，记忆持久化，机制可演示

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

---

### T19：Memory（SP1）

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

---

### T20：机制演示脚本（SP2）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §9.3，三个可在 Mock LLM 下确定性复现的机制演示 |
| **涉及文件** | `output/demo/guardrail_demo.py`, `output/demo/feedback_demo.py`, `output/demo/full_cycle_demo.py` |
| **实现要点** | ① Guardrail 演示：构造危险命令 → 拦截 → 输出结果 ② Feedback 演示：注入测试输出 → Analyzer 分类 → 生成修复 Prompt ③ 完整周期：Mock 驱动"写代码→测试→修复→通过"流程 |

**DoD：**
- ✅ 三个脚本可独立运行
- ✅ 输出确定性结果（不依赖网络）

---

## Phase 7：Delivery（2 个 Task）

**Milestone：** 项目可交付、可运行、文档完整

### T21：README 完善（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 完成 README，包含所有必需章节 |
| **涉及文件** | `README.md` |
| **实现要点** | ① 项目简介 ② 安装步骤（pip install / docker）③ 运行命令 ④ 分发命令 ⑤ 目录结构 ⑥ 安全边界说明（Key 配置方式）⑦ 已知限制 |

**DoD：**
- ✅ 包含全部必需章节
- ✅ Key 安全配置方式写清

### T22：AGENT_LOG + 最终验证（SP1）

| 字段 | 内容 |
|------|------|
| **目标** | 完成 AGENT_LOG.md，做最终验证 |
| **涉及文件** | `AGENT_LOG.md`, `REFLECTION.md` |
| **实现要点** | ① AGENT_LOG.md：按时间记录关键节点、subagent 输出、人工干预 ② 验证所有机制演示可运行 ③ 验证 `pytest tests/` 全部通过 |

**DoD：**
- ✅ `pytest tests/` 全部通过
- ✅ 三个机制演示可运行
- ✅ AGENT_LOG 完整

---

## Story Point 汇总

| Task | 名称 | SP | 阶段 |
|------|------|----|------|
| T1 | 项目脚手架 | 1 | Phase 1 |
| T2 | 数据模型 + Config | 1 | Phase 1 |
| T3 | CLI 入口 | 2 | Phase 2 |
| T4 | LLMProvider 抽象 + Mock | 2 | Phase 2 |
| T5 | OpenAICompatibleProvider | 1 | Phase 2 |
| T6 | BaseTool + Dispatcher | 1 | Phase 3 |
| T7 | ReadFile | 1 | Phase 3 |
| T8 | WriteFile | 1 | Phase 3 |
| T9 | RunShell | 1 | Phase 3 |
| T10 | Guardrail | 1 | Phase 4 |
| T11 | Main Loop 框架 | 2 | Phase 4 |
| T12 | Context 管理 | 1 | Phase 4 |
| T13 | 停机条件 | 1 | Phase 4 |
| T14 | Feedback 数据模型 | 1 | Phase 5 ⭐ |
| T15 | Collector | 1 | Phase 5 ⭐ |
| T16 | FailureAnalyzer | 2 | Phase 5 ⭐ |
| T17 | FeedbackEngine + 策略 | 2 | Phase 5 ⭐ |
| T18 | 集成 Feedback → Loop | 3 | Phase 6 |
| T19 | Memory | 1 | Phase 6 |
| T20 | 机制演示脚本 | 2 | Phase 6 |
| T21 | README | 1 | Phase 7 |
| T22 | AGENT_LOG + 最终验证 | 1 | Phase 7 |
| | **合计** | **30 SP** | |

---

## 并行建议

| 并行组 | 包含 Task | 说明 |
|--------|----------|------|
| **Group A** | T7, T8, T9 | 三个工具互不依赖，可并行 |
| **Group B** | T12, T13 | Context 和停机条件互不依赖，可并行 |
| **Group C** | T21, T22 | 文档收尾可并行 |

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