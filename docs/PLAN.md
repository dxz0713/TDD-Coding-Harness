# PLAN · 实现计划

> **项目名称：** TDD Coding Harness
>
> **对应 SPEC：** `docs/SPEC.md` v1.0
>
> **总任务数：** 20
>
> **预计并行度：** Phase 1→2→3 串行；Phase 4 起部分任务可并行

---

## 依赖关系图

```
Phase 1: Foundation
  T1 ──→ T2 ──→ T3
         │
         └──→ T4
                │
Phase 2: LLM    │
  T5 (基类) ──→ T6 (Mock) ──→ T7 (OpenAI)
                │
Phase 3: Tools  │
  T8 (BaseTool+Dispatcher) ──→ T9 (ReadFile)
                │                 ├──→ T10 (WriteFile)
                │                 └──→ T11 (RunShell)
                │
Phase 4: Core   │
  T12 (Guardrail) ──→ T13 (Memory) ──→ T14 (Main Loop, basic)
                │
Phase 5: Feedback (主要贡献)
  T15 (Models) ──→ T16 (Analyzer) ──→ T17 (Engine + Strategies)
                │
Phase 6: Integration
  T18 (CLI) ──→ T19 (Integrate Feedback → Loop)
                │
Phase 7: Polish
  T20 (Demo + Docker + CI)
```

---

## Phase 1：Foundation（4 个 Task）

### T1：项目脚手架

| 字段 | 内容 |
|------|------|
| **目标** | 建立项目基础结构，确保可安装、可运行 |
| **涉及文件** | `pyproject.toml`, `config.yaml`, `config.yaml.example`, `src/__init__.py`, `src/harness/__init__.py`, `src/tools/__init__.py`, `src/providers/__init__.py`, `src/feedback/__init__.py`, `src/tests/__init__.py`, `src/tests/conftest.py` |
| **实现要点** | ① pyproject.toml 定义项目元数据、依赖（pydantic, typer, pyyaml, openai）、[project.scripts] 入口 ② 创建所有 `__init__.py` ③ 准备 `config.yaml.example` ④ pytest 配置写在 pyproject.toml 的 `[tool.pytest.ini_options]` |

**测试：**
- `pytest --version` 可运行（环境验证）
- `python -c "from src import harness, tools, providers, feedback"` 无报错（模块可导入）

---

### T2：数据模型 + Config 加载

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §6 的所有核心实体和 §3.8 的 Config 加载 |
| **涉及文件** | `src/harness/models.py`, `src/harness/config.py`, `src/tests/test_models.py`, `src/tests/test_config.py` |
| **实现要点** | ① 所有 pydantic 模型（Message, ToolDef, ToolCall, LLMResponse, ToolResult, FailureType, AnalysisResult, Feedback, GuardrailResult, Decision, Memory, Context, RunResult）② Config 从 YAML 加载，支持默认值 ③ 支持 CLI 参数覆盖（预留 merge 方法） |

**测试（先红后绿）：**
- `test_config_load_defaults`：加载空配置 → 返回默认值
- `test_config_load_from_file`：加载 YAML → 验证字段值
- `test_config_cli_override`：CLI 参数覆盖配置文件
- `test_model_serialization`：创建 Message 对象 → 序列化 JSON → 反序列化

---

### T3：LLMProvider 抽象基类 + MockProvider

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.1.1 + §3.1.2，建立 LLM 抽象层 |
| **涉及文件** | `src/providers/base.py`, `src/providers/mock.py`, `src/tests/test_providers.py` |
| **实现要点** | ① `LLMProvider` 抽象基类（ABC），定义 `generate(messages, tools, config) → LLMResponse` ② `MockProvider` 持有 `preset_responses: Dict[str, LLMResponse]`，按输入消息匹配 ③ 不匹配时返回默认响应 ④ 错误边界：超时异常、认证异常 |

**测试（先红后绿）：**
- `test_mock_provider_returns_preset`：输入特定消息 → 返回预设响应
- `test_mock_provider_default_response`：输入未预设消息 → 返回默认响应
- `test_mock_provider_tool_call`：Mock 返回包含 ToolCall 的响应

---

### T4：OpenAIProvider

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.1.3，支持真实 OpenAI API 调用 |
| **涉及文件** | `src/providers/openai.py`, `src/tests/test_providers.py` |
| **实现要点** | ① 调用 OpenAI Chat Completions API ② 支持 tool calling（function calling）③ 配置从 `LLMConfig` 读取 ④ 错误处理：超时、认证失败、速率限制 |

**测试（先红后绿）：**
- `test_openai_provider_requires_api_key`：无 API Key 抛出 `LLMAuthError`
- `test_openai_provider_tool_def_format`：ToolDef 转换为 OpenAI tool format 格式正确

---

## Phase 2：Tools（4 个 Task）

### T5：BaseTool 抽象类 + ToolDispatcher

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.3 + §3.4.0，建立工具分发机制 |
| **涉及文件** | `src/tools/base.py`, `src/harness/dispatcher.py`, `src/tests/test_dispatcher.py` |
| **实现要点** | ① `BaseTool(ABC)` 定义 `execute(arguments: dict) → ToolResult` 接口 ② `ToolDispatcher` 维护 `name→tool` 映射，`register(name, tool)` 和 `dispatch(tool_call)` 方法 ③ 统一错误处理：未注册的工具返回错误 ToolResult |

**测试（先红后绿）：**
- `test_dispatcher_register_and_dispatch`：注册工具 → 分发 → 验证调用
- `test_dispatcher_unknown_tool`：分发未注册工具 → 返回错误
- `test_dispatcher_routes_by_name`：注册多个工具 → 按名称路由正确

---

### T6：ReadFile 工具

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.1，读取文件内容 |
| **涉及文件** | `src/tools/read_file.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② 路径越界检查（不允许访问项目目录外的文件）③ 文件不存在返回错误 ④ 使用 `pathlib` 处理路径 |

**测试（先红后绿）：**
- `test_read_file_success`：创建临时文件 → 读取 → 验证内容
- `test_read_file_not_found`：读取不存在文件 → 返回错误
- `test_read_file_path_traversal`：路径越界（`../`）→ 返回 PathViolationError

---

### T7：WriteFile 工具

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.2，写入文件内容 |
| **涉及文件** | `src/tools/write_file.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② 路径越界检查 ③ 自动创建父目录 ④ 写入成功返回内容 |

**测试（先红后绿）：**
- `test_write_file_success`：写入文件 → 验证内容和路径
- `test_write_file_path_traversal`：路径越界 → 返回 PathViolationError
- `test_write_file_creates_parent_dirs`：写入深层路径 → 自动创建目录

---

### T8：RunShell 工具

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.4.3，执行 Shell 命令 |
| **涉及文件** | `src/tools/run_shell.py`, `src/tests/test_tools.py` |
| **实现要点** | ① 继承 BaseTool ② 使用 `subprocess.run()` 执行命令 ③ 超时控制（默认 30s）④ 捕获 stdout、stderr、exit_code ⑤ 非阻塞回调（预留） |

**测试（先红后绿）：**
- `test_run_shell_echo`：执行 `echo hello` → stdout 包含 "hello"
- `test_run_shell_failure`：执行 `exit 1` → exit_code=1, success=False
- `test_run_shell_timeout`：执行 `sleep 100`（超时 1s）→ 抛出 TimeoutError

---

## Phase 3：Harness Core（3 个 Task）

### T9：Guardrail

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.6，治理护栏 |
| **涉及文件** | `src/harness/guardrail.py`, `src/tests/test_guardrail.py` |
| **实现要点** | ① `check(action) → GuardrailResult` ② 危险命令模式匹配（SPEC 列出的所有模式）③ 模式可配置（`block_list`）④ 安全命令直接放行 ⑤ HITL 确认机制（预留接口，Mock 模式自动拒绝） |

**测试（先红后绿）：**
- `test_guardrail_blocks_rm_rf`：`rm -rf /` → 拦截
- `test_guardrail_blocks_drop_table`：`DROP TABLE users` → 拦截
- `test_guardrail_blocks_fork_bomb`：`:(){ :|:& };:` → 拦截
- `test_guardrail_allows_safe_command`：`pytest tests/` → 放行
- `test_guardrail_configurable_block_list`：自定义 block_list → 新增模式生效

---

### T10：Memory

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.7，JSON 文件记忆 |
| **涉及文件** | `src/harness/memory.py`, `src/tests/test_memory.py` |
| **实现要点** | ① `Memory` 类基于 JSON 文件存储 ② `load()`, `save()`, `add_decision()`, `get_context()` 方法 ③ 超过 1MB 自动截断（保留最近 100 条）④ 文件不存在时返回空 Memory |

**测试（先红后绿）：**
- `test_memory_save_and_load`：写入 → 读取 → 内容一致
- `test_memory_add_decision`：追加决策 → 验证列表长度和内容
- `test_memory_get_context`：返回格式化字符串
- `test_memory_auto_truncate`：超过限制 → 截断保留最近 N 条

---

### T11：Main Loop（基础版）

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.2，主循环（不含 Feedback Engine 集成） |
| **涉及文件** | `src/harness/loop.py`, `src/tests/test_loop.py` |
| **实现要点** | ① `run(task, config) → RunResult` ② 流程：初始化 Context → 调用 LLM → 解析 → Guardrail → 分发 → 回灌 → 停机判断 ③ 停机条件：测试通过 / 最大迭代 / Finish 调用 / Guardrail 拒绝 ④ 使用 MockProvider 可独立测试 |

**测试（先红后绿）：**
- `test_loop_with_mock_finish`：MockProvider 返回 Finish → 成功停机
- `test_loop_max_iterations`：MockProvider 持续返回工具调用 → 达到最大迭代后停机
- `test_loop_guardrail_blocks`：MockProvider 返回危险命令 → Guardrail 拦截 → 停机
- `test_loop_read_write_cycle`：MockProvider 返回 ReadFile → WriteFile → Finish → 完整周期

---

## Phase 4：Feedback Engine（3 个 Task）⭐ 主要贡献

### T12：Feedback 数据模型

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.1 + §3.5.2，反馈引擎的基础数据结构 |
| **涉及文件** | `src/feedback/models.py`（或复用 `src/harness/models.py`）, `src/feedback/__init__.py`, `src/tests/test_feedback_models.py` |
| **实现要点** | ① `FailureType` 枚举（7 种类型）② `AnalysisResult` 模型 ③ `Feedback` 模型（含 `repair_prompt`）④ 与 ToolResult 的数据转换 |

**测试（先红后绿）：**
- `test_failure_type_values`：7 种类型值正确
- `test_analysis_result_serialization`：序列化 → 反序列化 一致
- `test_feedback_contains_repair_prompt`：Feedback 对象包含 repair_prompt 字段

---

### T13：FailureAnalyzer

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.3，解析 pytest 输出，分类失败类型 |
| **涉及文件** | `src/feedback/analyzer.py`, `src/tests/test_analyzer.py` |
| **实现要点** | ① 正则/模式匹配解析 pytest stdout/stderr ② 区分 SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_ERROR / TIMEOUT / RUNTIME_ERROR / TEST_FAILURE / UNKNOWN ③ 对 AssertionError 提取预期值和实际值 ④ 提取失败位置（文件:行号） |

**测试（先红后绿）：**
- `test_analyzer_syntax_error`：注入 SyntaxError 输出 → 分类为 SYNTAX_ERROR
- `test_analyzer_import_error`：注入 ImportError 输出 → 分类为 IMPORT_ERROR
- `test_analyzer_assertion_error`：注入 AssertionError 输出 → 分类为 ASSERTION_ERROR + 提取预期/实际值
- `test_analyzer_timeout`：注入超时输出 → 分类为 TIMEOUT
- `test_analyzer_runtime_error`：注入运行时异常 → 分类为 RUNTIME_ERROR
- `test_analyzer_pytest_failure`：注入测试失败输出 → 分类为 TEST_FAILURE
- `test_analyzer_unknown`：注入无关输出 → 分类为 UNKNOWN

---

### T14：FeedbackEngine + 修复策略

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.5.4，完整的反馈引擎，连接 Analyzer 和修复策略 |
| **涉及文件** | `src/feedback/engine.py`, `src/feedback/strategies.py`, `src/tests/test_feedback_engine.py` |
| **实现要点** | ① `FeedbackEngine.analyze(tool_result, context) → Feedback` ② 调用 Collector 收集原始输出 ③ 调用 Analyzer 分类 ④ 根据 FailureType 选择策略 ⑤ 每种策略生成差异化的 repair_prompt ⑥ 策略表：SYNTAX_ERROR→语法修复提示，ASSERTION_ERROR→预期/实际值提示，等 |

**测试（先红后绿）：**
- `test_feedback_engine_syntax_error`：注入 SyntaxError 结果 → 返回 SYNTAX_ERROR 类型的 Feedback
- `test_feedback_engine_assertion_error`：注入 AssertionError 结果 → Feedback 包含预期/实际值
- `test_feedback_engine_different_prompts`：不同 FailureType → repair_prompt 内容不同
- `test_feedback_engine_no_failure`：成功结果 → 返回 None（无需修复）

---

## Phase 5：Integration（2 个 Task）

### T15：CLI 入口

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §3.9，基于 typer 的命令行接口 |
| **涉及文件** | `src/cli.py`, `src/tests/test_cli.py` |
| **实现要点** | ① `tdd-harness run` 命令：接受 task 参数 + `--config`/`--provider`/`--model` 选项 ② `tdd-harness demo` 命令：guardrail / feedback / memory 子命令 ③ 配置优先级：CLI 参数 > 配置文件 > 默认值 ④ 错误处理：友好的报错信息 ⑤ 入口注册在 `pyproject.toml` 的 `[project.scripts]` |

**测试（先红后绿）：**
- `test_cli_run_help`：`tdd-harness run --help` → 显示帮助信息
- `test_cli_demo_help`：`tdd-harness demo --help` → 显示帮助信息
- `test_cli_run_with_provider_override`：传入 `--provider mock` → Config 中 provider 被覆盖

---

### T16：集成 Feedback Engine 到 Main Loop

| 字段 | 内容 |
|------|------|
| **目标** | 将 Feedback Engine 接入主循环，实现完整的 TDD 闭环 |
| **涉及文件** | `src/harness/loop.py`, `src/feedback/engine.py`, `src/tests/test_loop_integration.py` |
| **实现要点** | ① 在 Main Loop 中 RunShell 执行测试后 → 调用 FeedbackEngine.analyze() ② 分析结果回灌到 LLM 上下文（追加到 messages）③ 停机条件增强：Feedback 连续 N 次同一类型 → 走"止损"停机 ④ 日志记录 Feedback 分类结果 |

**测试（先红后绿）：**
- `test_loop_feedback_fix_cycle`：MockProvider 模拟"写代码→测试失败→收到反馈→修复→测试通过"完整周期
- `test_loop_feedback_max_retries`：MockProvider 持续返回同一错误 → 达到最大迭代后停机
- `test_loop_feedback_logs`：验证日志中包含 Feedback 分类结果

---

## Phase 6：Polish（4 个 Task）

### T17：机制演示脚本

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §9.3，三个可在 Mock LLM 下确定性复现的机制演示 |
| **涉及文件** | `output/demo/guardrail_demo.py`, `output/demo/feedback_demo.py`, `output/demo/full_cycle_demo.py` |
| **实现要点** | ① Guardrail 演示：构造危险命令 → Guardrail 拦截 → 输出拦截信息 ② Feedback 演示：注入构造的测试输出 → Analyzer 分类 → 生成修复 Prompt ③ 完整周期演示：Mock LLM 驱动完整"写代码→测试→修复→通过"流程 |

**测试（先红后绿）：**
- 三个演示脚本可独立运行且输出确定性结果

---

### T18：Docker 分发

| 字段 | 内容 |
|------|------|
| **目标** | 实现 SPEC §7.2，容器分发 |
| **涉及文件** | `Dockerfile`, `.dockerignore` |
| **实现要点** | ① 基于 `python:3.12-slim` ② 安装依赖 → 复制源码 → 设置入口 ③ `.dockerignore` 排除 `output/`, `.env`, `.git/` ④ 支持 `docker run -e OPENAI_API_KEY=...` 传入 Key |

**验证：**
- `docker build -t tdd-harness .` 成功
- `docker run --rm tdd-harness --help` 显示帮助

---

### T19：CI 配置

| 字段 | 内容 |
|------|------|
| **目标** | 实现 CI，每次 push 自动运行测试 |
| **涉及文件** | `.gitlab-ci.yml` |
| **实现要点** | ① 定义 `unit-test` job（老师要求必须包含此名称）② 安装依赖 → 运行 `pytest tests/` ③ 仅 Mock 模式，不依赖网络 ④ 可选：构建 Docker 镜像 |

**验证：**
- CI 配置语法正确
- `unit-test` job 名称正确

---

### T20：README 收尾

| 字段 | 内容 |
|------|------|
| **目标** | 完成项目文档收尾 |
| **涉及文件** | `README.md`, `AGENT_LOG.md` |
| **实现要点** | ① README：项目简介、安装、运行、分发命令、目录结构、安全边界 ② AGENT_LOG.md：按时间记录关键节点 ③ 分发的 README 章节写清 Key 的安全配置方式 |

---

## Task 依赖关系汇总

| Task | 名称 | 依赖 | 预计工时 | 阶段 |
|------|------|------|---------|------|
| T1 | 项目脚手架 | — | 15min | Phase 1 |
| T2 | 数据模型 + Config | T1 | 20min | Phase 1 |
| T3 | LLMProvider 抽象 + Mock | T2 | 15min | Phase 1 |
| T4 | OpenAIProvider | T3 | 15min | Phase 1 |
| T5 | BaseTool + Dispatcher | T2 | 15min | Phase 2 |
| T6 | ReadFile | T5 | 10min | Phase 2 |
| T7 | WriteFile | T5 | 10min | Phase 2 |
| T8 | RunShell | T5 | 15min | Phase 2 |
| T9 | Guardrail | T2 | 15min | Phase 3 |
| T10 | Memory | T2 | 15min | Phase 3 |
| T11 | Main Loop（基础） | T3, T5, T9, T10 | 25min | Phase 3 |
| T12 | Feedback 数据模型 | T2 | 10min | Phase 4 ⭐ |
| T13 | FailureAnalyzer | T12 | 20min | Phase 4 ⭐ |
| T14 | FeedbackEngine + 策略 | T13 | 20min | Phase 4 ⭐ |
| T15 | CLI 入口 | T2, T11 | 15min | Phase 5 |
| T16 | 集成 Feedback → Loop | T11, T14 | 20min | Phase 5 |
| T17 | 机制演示脚本 | T9, T14, T16 | 15min | Phase 6 |
| T18 | Docker 分发 | T1 | 10min | Phase 6 |
| T19 | CI 配置 | T1 | 10min | Phase 6 |
| T20 | README + AGENT_LOG | T17, T18, T19 | 20min | Phase 6 |

---

## 并行建议

| 并行组 | 包含 Task | 说明 |
|--------|----------|------|
| **Group A** | T6, T7, T8 | 三个工具实现互不依赖，可并行 |
| **Group B** | T9, T10 | Guardrail 和 Memory 互不依赖，可并行 |
| **Group C** | T18, T19 | Docker 和 CI 配置互不依赖，可并行 |

---

> **对应 SPEC：** `docs/SPEC.md` v1.0
>
> **开发方式：** 每个 Task 一个 Worktree → TDD（先红后绿）→ PR → Merge
>
> **下一阶段：** 冷启动验证（使用另一个 Agent 尝试实现 T1~T2）