# SPEC_PROCESS · 过程文档

> **项目名称：** TDD Coding Harness
>
> **对应阶段：** Brainstorming → SPEC.md
>
> **记录时间：** 2026-07-07

---

## 一、Brainstorming 概述

本次 Brainstorming 使用课程推荐的 Superpowers 方法论，通过"智能体追问 → 学生决策"的方式逐步确定项目设计。整个过程覆盖了选题确认、MVP 范围、技术选型、主要贡献、模块划分等关键决策。

---

## 二、Timeline

```
2026-07-07 09:30    开始 Brainstorming
        │
        ▼
2026-07-07 09:45    确定项目定位与目标用户
        │
        ▼
2026-07-07 10:00    确定 MVP 范围（A~G 全部保留，F/G 最小实现）
        │
        ▼
2026-07-07 10:15    确定主要贡献为 Feedback Engine
        │
        ▼
2026-07-07 10:30    确定技术栈（Python 3.12 + pytest + pydantic + typer）
        │
        ▼
2026-07-07 10:45    确定 LLM Provider 抽象层设计（Mock/OpenAI/Claude）
        │
        ▼
2026-07-07 11:00    确定模块目录结构
        │
        ▼
2026-07-07 11:30    完成 SPEC.md v1 初稿
        │
        ▼
2026-07-07 11:45    审查发现 SPEC 混入 Brainstorming 内容，决定拆分
        │
        ▼
2026-07-07 12:00    完成 SPEC.md 正式版 + SPEC_PROCESS.md
        │
        ▼
2026-07-07 12:30    完成 Git 初始化 + 文档优化
        │
        ▼
2026-07-07 12:40    确定 CLI 参数覆盖配置方案（拒绝 `/model`）
        │
        ▼
2026-07-07 12:45    进入 PLAN.md
```

---

## 三、关键节点记录

### 节点 1：项目定位确认

**智能体追问：**
> "TDD Coding Harness 解决什么问题？谁会使用它？为什么不用现成的 Claude Code / Codex CLI？"

**学生决策：**
- 这是一个教学性质的 Harness，不追求与商业工具竞争
- 核心等式：Agent = LLM + Harness
- 目标用户是课程评分者与有好奇心的开发者

**处理方式：** 直接采纳，写入 SPEC §1。

---

### 节点 2：MVP 范围讨论

**智能体建议：**
> 将 A~G 七个功能列为候选，询问哪些是 MVP 必须的。

**各功能定义：**

| 编号 | 功能 | 说明 |
|------|------|------|
| A | 调用 LLM API | 通过抽象接口调用 LLM 生成代码 |
| B | 读写文件 | 创建/修改代码文件（ReadFile, WriteFile） |
| C | 执行 Shell 命令 | 运行测试、编译等（RunShell） |
| D | 反馈闭环 | 测试结果 → 分析 → 回灌给 LLM 修正 |
| E | 危险动作护栏 | 拦截危险命令，要求人工确认 |
| F | 跨会话记忆 | 保持项目上下文与历史决策 |
| G | 配置文件 | 通过 config 控制 Harness 行为 |

**学生决策（修正）：**
> "A~G 全部保留，但 F(Memory) 和 G(Config) 做最小实现。"

**决策理由：** A 类项目要求六个维度都有最低实现，不允许砍掉任何维度。但可以控制实现深度。

**对 SPEC 的影响：** §3 中 Memory 只做 JSON 文件存储（不做向量检索/RAG），Config 只做 YAML 加载。

---

### 节点 3：主要贡献选择

**智能体建议：**
> 列出四个候选维度（治理/反馈/工具/记忆），建议选反馈闭环。

**学生决策（采纳 + 深化）：**
> "选 Feedback Loop，但不要只是简单的 '把测试结果发给 LLM'。"
> 学生提出了**可扩展的反馈引擎（Feedback Engine）**的概念：
> - Collector 收集原始输出
> - Failure Analyzer 分类失败类型（SyntaxError / ImportError / AssertionError / Timeout 等）
> - 每种类型生成不同的修复 Prompt
> - 未来可扩展支持 ruff、mypy 等额外反馈来源

**处理方式：** 采纳并深化。这是项目中最重要的设计决策。

**对 SPEC 的影响：** §3.5 和 §12 详细描述了 Feedback Engine 的设计。

---

### 节点 4：技术栈选型

**智能体建议：**
> Python 3.12 / TypeScript / Go 三个选项。

**学生决策：**
> "Python 3.12"
> 具体选型：pytest, pydantic, typer, pyyaml, openai

**决策理由：** pytest 最成熟，subprocess 调 Shell 方便，LLM SDK 齐全，mock 测试简单，Docker 打包容易，课程示例接近 Python。

**对 SPEC 的影响：** §9 技术选型表。

---

### 节点 5：LLM 供应商设计

**智能体建议：**
> 先做抽象层，后期随意切换。

**学生决策（采纳 + 深化）：**
> 设计 LLM Provider 抽象接口：
> - `LLMProvider` 抽象基类
> - `OpenAIProvider` 实现
> - `ClaudeProvider` 预留（MVP 不实现）
> - `MockProvider` 用于单元测试
>
> 特别指出："Mock Provider 就是老师要求的 Mock LLM —— 所有机制测试都不需要联网。"

**处理方式：** 采纳，这是满足 A 类"移除 LLM 后可测试"要求的关键设计。

**对 SPEC 的影响：** §3.1 完整描述了 LLM 抽象层设计。

---

### 节点 5b：Provider 切换方式 — CLI 参数 vs `/model`

**智能体追问：**
> 商业 Agent 支持 `/model` 命令切换模型，是否要在 Harness 中实现类似功能？

**学生决策（拒绝 + 替代方案）：**
> "一次性 CLI 工具不需要交互式 REPL 的 `/model`。"
> 学生提出**三级配置优先级**替代方案：
> - CLI 参数 `--provider`、`--model` 可覆盖配置文件
> - 优先级：CLI 参数 > 配置文件 > 默认值
> - 不做 `/model` 运行时切换

**决策理由：**
- `/model` 需要命令解析器 + 会话状态 + 热切换 Provider，复杂度高但课程收益低
- `--provider`、`--model` 实现成本低，typer 原生支持
- 课程评分关注的是 Provider 抽象和配置驱动，而非复刻商业产品交互

**对 SPEC 的影响：** US-05 增加 CLI 参数覆盖描述；CLI 章节增加 `--provider`、`--model` 参数；Config 章节增加优先级规则。

---

### 节点 6：模块目录结构

**学生提出：**
```
homework/
├── docs/          # 项目文档（SPEC, PLAN, 等）
├── src/           # 源代码
│   ├── harness/   # 主循环、分发器、护栏、记忆
│   ├── tools/     # 工具实现
│   ├── providers/ # LLM Provider
│   ├── feedback/  # 反馈引擎
│   └── tests/     # 测试
├── output/        # 运行产物
├── plan/          # 课程原始文件（只读）
└── config.yaml    # 配置
```

**处理方式：** 采纳，按此结构创建目录。

**对 SPEC 的影响：** 项目目录结构在 SPEC 中通过模块路径体现。

---

## 四、关键迭代摘要

### 第 1 轮：从模糊到清晰

**初始状态：** 只有"做一个 TDD Coding Harness"的想法。

**Brainstorming 产出：** 明确了项目定位、MVP 范围、技术栈、主要贡献。

**关键转折：** 学生提出 Feedback Engine 的详细设计，将项目从"普通 Harness"提升为"具有可扩展反馈引擎的 Harness"。

### 第 2 轮：从讨论到规约

**初始状态：** SPEC.md 包含 Brainstorming 的问答形式。

**问题发现：** SPEC 中出现"我建议……""你觉得呢？""是否采用？"等讨论性内容，不符合软件规格说明书的规范。

**修正：** 将 SPEC.md 改为纯规格说明（全部是"已决定"的陈述），所有讨论过程迁移到 SPEC_PROCESS.md。

---

## 五、AI 建议 vs 最终决策 对照表

| 议题 | AI 建议 | 最终决策 | 采纳/修正/推翻 | 理由 |
|------|---------|---------|--------------|------|
| MVP 范围 | 建议选出核心功能 | 全部保留（A~G），F/G 最小实现 | **修正**（更完整） | A 类要求六个维度都有最低实现 |
| 主要贡献 | 选 Feedback Loop | 选 Feedback Engine（深化） | **采纳并深化** | 项目名即承诺，TDD 核心是反馈闭环 |
| 技术栈 | 列出三个选项 | Python 3.12 | **采纳** | 生态成熟，课程熟悉，Mock 测试容易 |
| LLM 抽象 + 切换方式 | 做抽象层 + `/model` 命令 | 做抽象层 + CLI 参数覆盖（`--provider`/`--model`） | **采纳并深化** | Provider 抽象采纳；`/model` 拒绝，改为 CLI 参数覆盖 |
| 目录结构 | 建议标准模块结构 | 提出 docs/ 分离、src/providers/ 分离 | **采纳** | 关注点分离，文档与代码各归其位 |
| SPEC 风格 | 按规范格式写 | 指出问答形式不符合规范，要求拆分 | **学生主导修正** | SPEC 应只含已决定陈述，讨论归入 SPEC_PROCESS |

---

## 六、Decision Log

| 编号 | 决策 | 理由 | 影响 |
|------|------|------|------|
| D-01 | 采用 Python 3.12 | 生态成熟，pytest/pydantic/typer 支持完善，Mock 测试容易 | 所有模块统一使用 Python |
| D-02 | 采用 LLM Provider 抽象层 | 可切换供应商，Mock 支持离线测试 | 满足 A 类可测试性要求 |
| D-03 | 采用 MockProvider | 确定性返回预设响应，不依赖网络 | 核心机制全部可离线单元测试 |
| D-04 | 选择 Feedback Engine 作为主要贡献 | 项目名即承诺，TDD 核心是反馈闭环 | 深入实现 Collector + Analyzer + 差异化 Prompt |
| D-05 | Memory 做最小实现（JSON 文件） | 不做向量检索/RAG，控制项目范围 | 仅保存项目配置与决策历史 |
| D-06 | Guardrail 做基础版 | 模式匹配危险命令 + HITL 确认 | 满足 A 类治理维度最低要求 |
| D-07 | 配置使用 YAML | 可读性强，课程常用 | Config 独立于代码，修改配置不需要改代码 |
| D-08 | SPEC 与 SPEC_PROCESS 分离 | 规格说明与过程记录职责不同 | 文档清晰，各司其职 |
| D-09 | 使用 CLI 参数（`--provider`/`--model`）覆盖配置，不做 `/model` 命令 | CLI 工具无需交互式 REPL 的 `/model`，`--provider` 实现成本低 | Config 优先级：CLI 参数 > 配置文件 > 默认值 |

## 七、反思

### 7.1 Brainstorming 做得好的地方

1. **追问质量高**：智能体在 MVP 范围、技术选型等关键节点都提出了有区分度的选项，帮助学生做决策。
2. **及时纠正**：学生发现 SPEC 中混入了 Brainstorming 内容并主动要求拆分，这是对文档质量的重要把控。

### 7.2 不足之处

1. **SPEC 初稿风格偏差**：第一版 SPEC 混入了问答形式的讨论内容，说明在设计阶段就应明确区分"过程文档"与"规格文档"。
2. **验收标准可量化性**：部分验收标准仍偏笼统（如"可运行""语法正确"），后续 PLAN.md 中需要进一步细化。

### 7.3 Lessons Learned

| 教训 | 说明 |
|------|------|
| 不应过早引入复杂框架 | 初期考虑过 LangGraph / CrewAI，但 A 类要求自行实现 Harness 内核，这些框架反而违规 |
| Feedback 比 Memory 更适合做主要贡献 | Memory 的实现偏向存储，工程深度有限；Feedback Engine 有分类、策略、生成等多层逻辑 |
| Mock 是课程项目的关键 | "移除 LLM 后可测试"是 A 类评分硬标准，MockProvider 的设计直接影响通过率 |
| MVP 范围必须主动控制 | AI 倾向于建议更多功能，学生需要主动判断"哪些可以最小实现"来保持项目可控 |
| 文档应该从一开始就区分"规格"和"过程" | 混在一起导致后期重写，增加不必要的工作量 |

### 7.4 学到的教训

- 软件规格说明书（SPEC）应该只包含"已决定"的事实陈述，所有"为什么这样选"的记录应归入 SPEC_PROCESS.md
- 在 Brainstorming 阶段就应将两个文档的边界划清楚，避免后续重写工作

---

## 八、Brainstorming 产出总结

```
┌─────────────────────────────────────────────┐
│          Brainstorming 产出总结              │
├─────────────────────────────────────────────┤
│                                             │
│  项目名称     TDD Coding Harness            │
│                                             │
│  项目类型     CLI 工具                      │
│                                             │
│  实现语言     Python 3.12                   │
│                                             │
│  LLM 供应商   OpenAI + Mock                 │
│              (Claude 预留)                   │
│                                             │
│  主要贡献     Feedback Engine               │
│              (可扩展反馈闭环引擎)             │
│                                             │
│  MVP 范围     A~G 全部覆盖                  │
│              F(Memory) / G(Config) 最小实现  │
│                                             │
│  六个维度     ✅ 决策  ✅ 工具  ✅ 反馈       │
│              ✅ 治理  ✅ 记忆  ✅ 配置       │
│                                             │
│  测试策略     Mock LLM 确定性单元测试         │
│              不依赖网络，pytest 一键运行       │
│                                             │
│  分发形态     Docker + 本地 Python 运行       │
│                                             │
│  下一阶段     → PLAN.md (实现计划)           │
│               → 冷启动验证                   │
│               → TDD 开发                    │
└─────────────────────────────────────────────┘
```

---

> **本文件对应课程要求：** AI4SE 期末项目 · 通用要求 §4.4 — SPEC_PROCESS.md（过程文档）