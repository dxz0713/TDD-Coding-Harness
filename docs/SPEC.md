# SPEC · TDD Coding Harness

> **项目名称：** TDD Coding Harness
>
> **主要贡献：** Feedback Engine（可扩展的反馈闭环引擎）
>
> **版本：** v1.0
>
> **对应课程要求：** AI4SE 期末项目 · A · Coding Agent Harness

---

## 目录

1. [问题陈述](#1-问题陈述)
2. [用户故事](#2-用户故事)
3. [功能规约](#3-功能规约)
4. [非功能性需求](#4-非功能性需求)
5. [系统架构](#5-系统架构)
6. [数据模型](#6-数据模型)
7. [凭据与分发设计](#7-凭据与分发设计)
8. [技术选型与理由](#8-技术选型与理由)
9. [验收标准](#9-验收标准)
10. [风险与未决问题](#10-风险与未决问题)
11. [领域与机制设计](#11-领域与机制设计)

---

## 1. 问题陈述

### 1.1 要解决什么问题

当前 LLM（如 GPT-4o、Claude Sonnet）具备强大的代码生成能力，但 LLM 本身只是一个"思考引擎"——它只能决定下一步做什么，无法直接作用于外部世界。要让 LLM 真正完成一个编码任务，需要一个工程层（Harness）来完成以下工作：

- 将 LLM 的"决策"转化为对文件系统的操作（读/写文件）
- 将 LLM 的"决策"转化为对 Shell 的调用（运行测试、构建）
- 将外部结果（测试失败、编译错误）回灌给 LLM，驱动其自我修正
- 在危险操作（如删除文件、执行破坏性命令）前拦截并请求人工确认
- 跨会话保持项目上下文与历史决策

### 1.2 目标用户

本项目的目标用户是**课程评分者**与**有好奇心的开发者**。它是一个教学性质的 Harness，不追求与商业工具（Claude Code、Codex CLI）竞争，但要求完整体现课程所学的工程方法论。

### 1.3 为什么值得做

TDD Coding Harness 的价值不在于"另一个编码 Agent"，而在于：

1. **工程深度**：将 LLM 从"对话式助手"封装为"可编程的编码执行单元"，这是 AI4SE 课程核心命题的具体实践。
2. **可测试性**：通过 Mock LLM 设计，使 Harness 的每个核心机制都可以用确定性单元测试验证——这是课程 A 类项目的硬性要求，也是区分"工程实现"与"提示词堆砌"的关键标准。
3. **反馈闭环的显式建模**：将"测试结果→分析→修正"这一循环从隐式提示词提升为可编码、可扩展的反馈引擎，是项目的主要贡献。

---

## 2. 用户故事

以下用户故事遵循 INVEST 原则（Independent, Negotiable, Valuable, Estimable, Small, Testable）。

### US-01：运行代码生成任务

> 作为一名开发者，我希望通过命令行启动 Harness，传入一个编码任务描述，让 Harness 自动完成代码编写，以便节省手动编码时间。

**验收标准：**
- 执行 `tdd-harness run "编写一个计算斐波那契数列的函数"` 后，Harness 生成对应的代码文件
- 生成的代码语法正确、可运行

### US-02：自动修复测试失败

> 作为一名开发者，我希望 Harness 在运行测试后发现失败时，能自动分析失败原因并尝试修复代码，而不是在第一次失败后就停止。

**验收标准：**
- 给定一个有 bug 的代码 + 对应的测试文件，Harness 运行测试 → 检测失败 → 分析失败类型 → 生成修复 → 重新测试
- 修复过程最多重试 N 次（可配置），达到上限后停止并报告

### US-03：拦截危险命令

> 作为一名开发者，我希望 Harness 在执行危险 Shell 命令（如 `rm -rf /`、`DROP TABLE`）前暂停并请求我确认，以避免意外破坏。

**验收标准：**
- Guardrail 模块识别到危险命令模式时，拦截执行并输出提示信息
- 在 Mock LLM 模式下，可通过确定性测试验证拦截行为

### US-04：查看 Harness 运行日志

> 作为一名开发者，我希望 Harness 记录每次运行的完整日志（LLM 调用、工具执行、反馈结果），以便在出错时回溯排查。

**验收标准：**
- 每次运行在 `output/logs/` 下生成时间戳命名的日志文件
- 日志包含：LLM 请求/响应、工具调用与结果、Guardrail 拦截记录、Feedback 分类结果

### US-05：切换 LLM 供应商

> 作为一名开发者，我希望通过修改配置文件切换 LLM 供应商（如从 OpenAI 切换到 Mock），而不需要修改代码。

**验收标准：**
- `config.yaml` 中修改 `provider` 字段即可切换
- Mock Provider 在无网络环境下返回预设响应，用于测试

### US-06：使用反馈引擎调试 AssertionError

> 作为一名开发者，我希望 Harness 遇到 AssertionError 时能提取具体的断言表达式和预期/实际值，生成有针对性的修复提示，而不是泛泛地重试。

**验收标准：**
- Feedback Engine 能区分 AssertionError、SyntaxError、ImportError、Timeout 等失败类型
- 每种类型生成不同的修复 Prompt

---

## 3. 功能规约

### 3.1 LLM 抽象层（`src/providers/`）

#### 3.1.1 `LLMProvider` 抽象基类

```
输入：
  - messages: List[Message]  # 对话历史
  - tools: List[ToolDef]     # 可用工具定义
  - config: LLMConfig        # 模型参数（temperature, max_tokens 等）

输出：
  - LLMResponse
    - content: str           # 文本回复
    - tool_calls: List[ToolCall]  # 工具调用请求

行为：
  - 同步/异步调用底层 LLM API
  - 返回结构化响应（文本 + 工具调用）
```

**边界条件：**
- 网络超时：默认 30s，可配置；超时后抛出 `LLMTimeoutError`
- API Key 无效：抛出 `LLMAuthError`
- 速率限制：抛出 `LLMRateLimitError`

#### 3.1.2 `MockProvider`

```
输入：
  - preset_responses: Dict[str, LLMResponse]  # 预设响应表

行为：
  - 根据输入消息匹配预设响应
  - 不匹配时返回默认响应
  - 不依赖网络，用于单元测试
```

#### 3.1.3 `OpenAIProvider`

```
配置：
  - api_key: str（从环境变量或密钥管理加载）
  - model: str（默认 gpt-4o）
  - base_url: str（可选，用于兼容接口）

行为：
  - 调用 OpenAI Chat Completions API
  - 支持工具调用（function calling）
```

#### 3.1.4 `ClaudeProvider`（预留）

```
行为：
  - 调用 Anthropic Messages API
  - 支持工具调用（tool use）
  - 本次 MVP 不实现，仅预留接口
```

### 3.2 主循环（`src/harness/loop.py`）

```
输入：
  - task: str           # 任务描述
  - config: Config      # 配置

流程：
  1. 初始化 Context（系统提示 + 记忆）
  2. 调用 LLM → 获取响应
  3. 解析响应中的工具调用
  4. Guardrail 检查
  5. 分发工具执行
  6. 收集执行结果
  7. 若为测试命令 → Feedback Engine 分析
  8. 将结果回灌给 LLM
  9. 判断停机条件 → 未满足则回到步骤 2

输出：
  - RunResult
    - success: bool
    - artifacts: List[FilePath]
    - logs: List[LogEntry]
    - iterations: int
```

**停机条件：**
- 测试全部通过 → 成功
- 达到最大迭代次数（默认 5）→ 失败
- LLM 返回 `Finish` 工具调用 → 按结果判定
- Guardrail 拦截致命动作且用户拒绝 → 失败

### 3.3 工具分发器（`src/harness/dispatcher.py`）

```
输入：
  - tool_call: ToolCall  # LLM 请求的工具调用

行为：
  - 根据工具名称路由到对应工具实现
  - 统一错误处理
  - 返回 ToolResult

输出：
  - ToolResult
    - success: bool
    - output: str
    - error: str | None
```

**注册机制：**
```python
class ToolDispatcher:
    def register(self, name: str, tool: BaseTool): ...
    def dispatch(self, call: ToolCall) -> ToolResult: ...
```

### 3.4 工具定义（`src/tools/`）

#### 3.4.1 `ReadFile`

```
输入：
  - path: str

输出：
  - success: bool
  - content: str

错误：
  - 文件不存在 → FileNotFoundError
  - 路径越界（超出项目目录）→ PathViolationError
```

#### 3.4.2 `WriteFile`

```
输入：
  - path: str
  - content: str

输出：
  - success: bool

错误：
  - 路径越界 → PathViolationError
  - 磁盘空间不足 → IOError
```

#### 3.4.3 `RunShell`

```
输入：
  - command: str
  - timeout: int（默认 30s）

输出：
  - success: bool
  - stdout: str
  - stderr: str
  - exit_code: int

错误：
  - 超时 → TimeoutError
  - 命令被 Guardrail 拦截 → GuardrailInterceptedError
```

### 3.5 反馈引擎（`src/feedback/`）—— 主要贡献

#### 3.5.1 `FeedbackEngine`

```
输入：
  - tool_result: ToolResult（RunShell 执行结果）
  - context: Context（当前任务上下文）

流程：
  1. Collector 收集原始输出（stdout, stderr, exit_code）
  2. Analyzer 分析失败类型
  3. 根据类型选择对应的修复策略
  4. 生成结构化的反馈信息

输出：
  - Feedback
    - failure_type: FailureType
    - summary: str
    - details: dict
    - repair_prompt: str  # 用于 LLM 下次迭代的增强提示
```

#### 3.5.2 `FailureType` 分类

```python
class FailureType(Enum):
    SYNTAX_ERROR     = "syntax_error"      # Python 语法错误
    IMPORT_ERROR     = "import_error"      # 导入错误
    ASSERTION_ERROR  = "assertion_error"   # 断言失败（含预期/实际值）
    TIMEOUT          = "timeout"           # 执行超时
    RUNTIME_ERROR    = "runtime_error"     # 其他运行时异常
    TEST_FAILURE     = "test_failure"      # 测试失败（未分类）
    UNKNOWN          = "unknown"           # 无法分类
```

#### 3.5.3 `FailureAnalyzer`

```
输入：
  - stdout: str
  - stderr: str
  - exit_code: int

行为：
  - 正则/模式匹配解析 pytest 输出
  - 提取失败类型、失败位置、错误信息
  - 对 AssertionError 提取断言表达式和预期/实际值

输出：
  - AnalysisResult
    - failure_type: FailureType
    - location: str | None        # 文件:行号
    - error_message: str
    - assertion_expected: str | None  # AssertionError 专用
    - assertion_actual: str | None    # AssertionError 专用
    - raw_snippet: str | None     # 相关代码片段
```

#### 3.5.4 修复策略与差异化 Prompt

| FailureType | 策略 |
|---|---|
| SYNTAX_ERROR | 提取语法错误位置 + 期望的语法结构，生成精确修复提示 |
| IMPORT_ERROR | 提取缺失的模块名，建议安装或修正导入路径 |
| ASSERTION_ERROR | 提取预期值 vs 实际值，生成针对性修复提示 |
| TIMEOUT | 建议优化算法复杂度或增加超时时间 |
| RUNTIME_ERROR | 提取异常类型 + 堆栈，生成通用修复提示 |
| TEST_FAILURE | 提取失败测试名称 + 输出，生成通用修复提示 |

### 3.6 治理护栏（`src/harness/guardrail.py`）

```
输入：
  - action: Action（待执行的工具调用）

行为：
  - 匹配危险命令模式列表
  - 命中则拦截，记录日志，请求人工确认
  - 用户确认后放行，拒绝则终止

输出：
  - GuardrailResult
    - allowed: bool
    - reason: str | None
```

**危险命令模式（基础版）：**
- `rm -rf /`、`rm -rf /*` 等递归删除根目录
- `dd if=` 直接磁盘写入
- `DROP TABLE`、`DROP DATABASE` 等破坏性 SQL
- `:(){ :|:& };:`（fork 炸弹）
- `> /dev/sda` 等直接写入块设备
- 写入 `~/.ssh/` 或 `~/.config/` 等敏感目录
- 网络下载并执行（`curl ... | bash`、`wget ... -O- | sh`）

### 3.7 记忆（`src/harness/memory.py`）

```
存储：
  - 文件：output/memory.json

内容：
  - project_name: str
  - project_description: str
  - tech_stack: List[str]
  - decisions: List[Decision]  # 历史决策记录
  - conventions: List[str]     # 项目约定

行为：
  - load(): 从 JSON 文件加载
  - save(): 写入 JSON 文件
  - add_decision(decision): 追加决策
  - get_context(): 返回格式化的上下文摘要

约束：
  - 不做向量检索
  - 不做 RAG
  - 文件大小超过 1MB 时自动截断（保留最近 100 条）
```

### 3.8 配置（`src/harness/config.py`）

```
加载方式：
  - 默认路径：config.yaml（项目根目录）
  - 可通过 CLI 参数 --config 覆盖

内容：
  provider:
    name: mock | openai | claude
    model: str
    temperature: float
    max_tokens: int
    timeout: int

  loop:
    max_iterations: int (默认 5)
    workspace: str (默认 .)

  guardrail:
    enabled: bool (默认 true)
    block_list: List[str]

  memory:
    enabled: bool (默认 true)
    path: str (默认 output/memory.json)
```

### 3.9 CLI（`src/cli.py`）

基于 typer 的命令行入口：

```
tdd-harness run "任务描述"     # 执行编码任务
tdd-harness run --config custom.yaml "任务描述"
tdd-harness demo guardrail      # 运行 Guardrail 机制演示
tdd-harness demo feedback       # 运行 Feedback 机制演示
tdd-harness demo memory         # 运行 Memory 机制演示
```

---

## 4. 非功能性需求

### 4.1 性能

- 工具执行时间：读/写文件 < 100ms，Shell 命令受限于命令本身（默认超时 30s）
- LLM 调用时间受限于供应商 API 响应速度（通常 1-10s）
- 日志文件单个不超过 10MB，自动轮转

### 4.2 安全（含凭据威胁模型）

**凭据存储：**
- API Key 绝不硬编码进源码，绝不提交到 Git
- 支持从环境变量 `OPENAI_API_KEY` 加载
- 支持通过 `.env` 文件加载（须在 `.gitignore` 中排除 `.env`）
- 首次运行检测到无 Key 时，提示用户输入（隐藏输入，不回显）

**威胁模型：**
| 威胁 | 缓解措施 |
|------|---------|
| API Key 泄露至 Git | `.gitignore` 排除 `.env`，代码审查时检查 |
| 进程环境被读取 | 使用环境变量而非命令行参数传递 Key |
| 日志泄露 Key | 日志输出前过滤 `sk-...` 模式 |
| 危险 Shell 命令 | Guardrail 拦截 + HITL 确认 |

### 4.3 可用性

- CLI 提供清晰的错误信息和帮助文档
- 首次运行有引导提示（配置 Key 等）
- 日志文件可读性强，时间戳 + 级别 + 内容

### 4.4 可观测性

- 结构化日志（JSON 格式可选）
- 每次运行生成独立日志文件（`output/logs/run_YYYYMMDD_HHmmss.jsonl`）
- 关键事件记录：LLM 调用、工具执行、Guardrail 拦截、Feedback 分析

---

## 5. 系统架构

### 5.1 组件图

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (typer)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Main Loop                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  LLM     │  │  Tool    │  │Guardrail │  │  Memory        │  │
│  │ Provider │→│Dispatcher│→│  Check   │→│  (Context)      │  │
│  │(抽象接口) │  │          │  │          │  │                │  │
│  └────┬─────┘  └──────────┘  └──────────┘  └────────────────┘  │
│       │                                                          │
└───────┼──────────────────────────────────────────────────────────┘
        │
   ┌────┴────┬─────────┬──────────┐
   │         │         │          │
   ▼         ▼         ▼          ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│ Mock │ │OpenAI│ │Claude  │ │ (Future) │
│ LLM  │ │LLM   │ │LLM     │ │          │
└──────┘ └──────┘ └────────┘ └──────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Feedback Engine                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐   │
│  │Collector │→│ Analyzer │→│ Repair Strategy Selector       │   │
│  │(原始输出) │  │(失败分类)  │  │(差异化 Prompt 生成)          │   │
│  └──────────┘  └──────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 数据流（一次迭代）

```
User → CLI → Main Loop
  → LLM.generate(prompt + context) → Text + ToolCall
  → Guardrail.check(ToolCall) → allowed/blocked
  → ToolDispatcher.dispatch(ToolCall) → ToolResult
  → [if test command]
    → FeedbackEngine.analyze(ToolResult) → Feedback
    → 回灌 Feedback 到 LLM 上下文
  → [停机判断] → 继续/终止
```

### 5.3 外部依赖

| 依赖 | 用途 | 必要性 |
|------|------|--------|
| OpenAI SDK | 调用 GPT-4o | 可选（Mock 模式不需要） |
| Anthropic SDK | 调用 Claude | 可选（预留，暂不实现） |
| pytest | 作为外部工具被调用 | 用户项目依赖 |
| ruff / mypy | 作为反馈源扩展 | 可选（扩展范围） |

---

## 6. 数据模型

### 6.1 核心实体

```python
# === LLM 层 ===
class Message(BaseModel):
    role: str           # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None

class ToolDef(BaseModel):
    name: str
    description: str
    parameters: dict     # JSON Schema

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict

class LLMResponse(BaseModel):
    content: str
    tool_calls: List[ToolCall] = []
    finish_reason: str = "stop"   # "stop" | "tool_calls" | "error"

# === 工具层 ===
class ToolResult(BaseModel):
    success: bool
    output: str = ""
    error: str | None = None
    exit_code: int | None = None

# === 反馈层 ===
class FailureType(str, Enum):
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    ASSERTION_ERROR = "assertion_error"
    TIMEOUT = "timeout"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    UNKNOWN = "unknown"

class AnalysisResult(BaseModel):
    failure_type: FailureType
    location: str | None = None
    error_message: str = ""
    assertion_expected: str | None = None
    assertion_actual: str | None = None
    raw_snippet: str | None = None

class Feedback(BaseModel):
    failure_type: FailureType
    summary: str
    details: AnalysisResult
    repair_prompt: str

# === 治理层 ===
class GuardrailResult(BaseModel):
    allowed: bool
    reason: str | None = None

# === 记忆层 ===
class Decision(BaseModel):
    timestamp: str
    description: str
    reason: str

class Memory(BaseModel):
    project_name: str = ""
    project_description: str = ""
    tech_stack: List[str] = []
    decisions: List[Decision] = []
    conventions: List[str] = []

# === 运行层 ===
class RunResult(BaseModel):
    success: bool
    artifacts: List[str] = []
    iterations: int = 0
    error: str | None = None
```

### 6.2 实体关系

```
Main Loop (1) ── uses ──▶ (1) LLMProvider
Main Loop (1) ── uses ──▶ (1) ToolDispatcher
ToolDispatcher (1) ── routes ──▶ (N) BaseTool
Main Loop (1) ── uses ──▶ (1) Guardrail
Main Loop (1) ── uses ──▶ (1) Memory
Main Loop (1) ── uses ──▶ (1) FeedbackEngine
FeedbackEngine (1) ── has ──▶ (1) FailureAnalyzer
```

---

## 7. 凭据与分发设计

### 7.1 凭据存储方案

| 方式 | 说明 | 安全等级 |
|------|------|---------|
| 环境变量 | `OPENAI_API_KEY=sk-...` 通过 `.env` 加载 | ⚠️ 明文，进程环境可见 |
| 隐藏输入 | 首次运行 `tdd-harness init` 引导用户输入，不回显 | ✅ 避免 shell history |

**实现：**
- 使用 `python-dotenv` 加载 `.env` 文件
- `.env` 列入 `.gitignore`
- 日志输出前过滤 `sk-...` 模式，防止 Key 泄露到日志

### 7.2 分发形态

**容器镜像（Docker）：**
- `docker build -t tdd-harness .`
- `docker run --rm -v $(pwd):/workspace -e OPENAI_API_KEY=sk-... tdd-harness run "任务"`

**本地运行：**
- Python 3.12+，pip install -r requirements.txt
- `tdd-harness run "任务"`

### 7.3 Key 在目标机的安全配置方式

1. 在项目目录创建 `.env` 文件，写入 `OPENAI_API_KEY=sk-...`
2. 运行 `tdd-harness run "任务"`（自动从 `.env` 加载）
3. 或者通过 `docker run -e OPENAI_API_KEY=sk-...` 传入

---

## 8. 技术选型与理由

| 选型 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.12 | 测试框架成熟（pytest），LLM SDK 齐全，课程熟悉 |
| LLM 接口 | 抽象接口 + OpenAI SDK | 灵活性 + 可测试性（Mock Provider） |
| 数据校验 | pydantic v2 | 类型安全，自动序列化/反序列化 |
| CLI 框架 | typer | 零配置，自动生成帮助文档 |
| 配置格式 | YAML（pyyaml） | 可读性强，课程常用 |
| 测试框架 | pytest | 最成熟的 Python 测试框架 |
| 测试隔离 | pytest-mock | Mock LLM 调用 |
| 容器 | Docker | 分发简单，跨平台 |

---

## 9. 验收标准

### 9.1 功能验收

| 功能 | 验收标准 |
|------|---------|
| LLM 抽象层 | MockProvider 可返回预设响应；OpenAIProvider 可真实调用 API；切换 provider 配置即可切换 |
| 主循环 | 给定任务描述，Harness 能完成多轮工具调用并最终停机 |
| ReadFile | 读取存在文件返回内容；读取不存在文件返回错误；路径越界返回错误 |
| WriteFile | 写入文件成功；路径越界返回错误 |
| RunShell | 执行成功命令返回 stdout；执行失败命令返回 stderr 和 exit_code；超时抛出异常 |
| Guardrail | 危险命令被拦截并返回提示；安全命令正常放行 |
| Feedback Engine | 正确分类 SYNTAX_ERROR / IMPORT_ERROR / ASSERTION_ERROR / TIMEOUT / RUNTIME_ERROR；每种类型生成不同修复 Prompt |
| Memory | 保存和加载 JSON 文件；跨会话保持数据；超过 1MB 自动截断 |
| Config | 加载 YAML 配置；缺失字段使用默认值；CLI 参数可覆盖配置文件 |
| CLI | `tdd-harness run` 可执行任务；`tdd-harness demo` 可运行机制演示 |

### 9.2 测试验收

- 所有核心机制有 Mock LLM 驱动的确定性单元测试
- 测试不依赖网络和真实 LLM
- `pytest tests/` 一键运行全部通过

### 9.3 机制演示验收

以下三个场景可在 Mock LLM 下确定性复现：

1. **Guardrail 演示**：构建一个 `rm -rf /` 命令 → Guardrail 拦截 → 输出拦截信息
2. **Feedback 演示**：注入一个 SyntaxError 测试结果 → Feedback Engine 分析并分类 → 生成修复 Prompt → 下一轮 LLM 调用包含修复上下文
3. **主要贡献演示**：展示 Feedback Engine 对多种失败类型（至少 3 种）产生不同的修复策略

---

## 10. 风险与未决问题

### 10.1 已识别的风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM API 调用成本 | 运行测试产生费用 | Mock Provider 覆盖单元测试；真实调用仅用于集成验证 |
| 项目范围膨胀 | 超出个人项目合理工作量 | 明确 MVP 边界；F(G) 做最小实现；先完成核心再扩展 |
| 反馈分类不够准确 | 依赖正则匹配，可能漏分类 | 兜底 UNKNOWN 类型；预留扩展点 |
| Guardrail 误拦 | 正常命令被拦截 | 提供放行机制（HITL 确认）；`block_list` 可配置 |

### 10.2 未决问题

- 是否需要支持 `mypy` / `ruff` 作为额外的反馈来源？→ 列为扩展项，MVP 不做
- 是否支持多文件项目？→ MVP 支持，LLM 决定多文件操作
- 是否支持非 Python 项目？→ RunShell 工具可执行任意命令，pytest 作为默认测试命令，其他语言依赖用户配置

---

## 11. 领域与机制设计

### 11.1 领域分析：Coding Agent 的四个核心机制

#### 11.1.1 动作/工具

**领域需求：** 编码 Agent 需要能够读写代码文件、执行构建与测试命令。

**编码实现方案：**
- `BaseTool` 抽象基类，定义 `execute(params) -> ToolResult` 接口
- `ToolDispatcher` 维护名称到工具实例的映射，负责路由
- 每个工具（ReadFile, WriteFile, RunShell）是独立类，可单独单元测试
- 工具注册通过 `dispatcher.register("read_file", ReadFile())` 完成

#### 11.1.2 客观反馈信号

**领域需求：** 编码 Agent 需要知道代码是否正确。最客观的信号是运行测试/检查工具的输出。

**编码实现方案（⭐ 主要贡献）：**
- `FeedbackEngine` 是确定性代码模块，不依赖 LLM 判断
- `Collector` 将原始 stdout/stderr 解析为结构化数据
- `FailureAnalyzer` 通过正则/模式匹配对失败类型进行分类（不依赖 LLM）
- 不同类型触发不同的修复策略，生成不同的 repair_prompt
- 移除 LLM 后，FeedbackEngine 的所有分类逻辑仍可独立测试

#### 11.1.3 危险动作

**领域需求：** 编码 Agent 可能执行破坏性命令（删除文件、格式化磁盘、修改系统配置）。

**编码实现方案：**
- `Guardrail` 函数/类，在工具执行前拦截
- 危险命令通过模式匹配识别（字符串匹配 + 正则）
- 拦截后返回 `GuardrailResult(allowed=False, reason=...)`
- 可配置 `block_list` 扩展危险模式
- 移除 LLM 后，传入构造的 Action 即可测试拦截逻辑

#### 11.1.4 记忆

**领域需求：** 跨会话保持项目上下文、历史决策、技术栈约定。

**编码实现方案：**
- `Memory` 类基于 JSON 文件存储
- 加载时反序列化为结构化对象，保存时序列化
- 只做精确匹配检索，不做语义搜索
- 大小超限时自动截断（保留最近 N 条）
- 移除 LLM 后，读写 JSON 文件的逻辑可独立测试

### 11.2 重点维度论证：反馈引擎

选择 Feedback Engine 作为主要贡献，理由如下：

1. **项目名即承诺**：TDD Coding Harness 的核心是"测试驱动"，反馈闭环是 TDD 的工程化实现。
2. **天然由代码构成**：Collector 的日志解析、Analyzer 的失败分类、Strategy Selector 的策略分发，全部是确定性代码，不依赖 LLM 智能。
3. **可测试性强**：每种失败类型都可以构造对应的测试输入，验证分类是否正确、修复策略是否匹配。
4. **可扩展性**：新的失败类型只需添加新的分类规则和修复策略，符合开闭原则。
5. **工程深度足够**：从简单的"把测试结果发给 LLM"提升为"结构化分析 + 差异化的修复策略"，体现了工程思维。

### 11.3 机制可测试性对照表

| 机制 | 测试方式 | 需要 LLM？ |
|------|---------|-----------|
| ToolDispatcher 路由 | 注册 mock 工具 → 分发 → 验证调用 | ❌ |
| Guardrail 拦截 | 传入危险 Action → 验证拦截 | ❌ |
| FeedbackEngine 分类 | 注入构造的 stdout/stderr → 验证分类结果 | ❌ |
| Memory 读写 | 写入 → 读取 → 验证内容一致 | ❌ |
| Config 加载 | 加载 YAML → 验证字段值 | ❌ |
| Main Loop 流程 | 使用 MockProvider → 验证迭代次数和停机条件 | ❌（Mock） |
| ReadFile/WriteFile | 创建临时文件 → 读写 → 验证内容 | ❌ |

---

> **本 SPEC 对应课程要求：** AI4SE 期末项目 · A · Coding Agent Harness
>
> **下一份文档：** PLAN.md（实现计划）