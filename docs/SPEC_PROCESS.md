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

## 二、关键节点记录

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

**对 SPEC 的影响：** §3.5 和 §11 详细描述了 Feedback Engine 的设计。

---

### 节点 4：技术栈选型

**智能体建议：**
> Python 3.12 / TypeScript / Go 三个选项。

**学生决策：**
> "Python 3.12"
> 具体选型：pytest, pydantic, typer, pyyaml, openai

**决策理由：** pytest 最成熟，subprocess 调 Shell 方便，LLM SDK 齐全，mock 测试简单，Docker 打包容易，课程示例接近 Python。

**对 SPEC 的影响：** §8 技术选型表。

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

## 三、关键迭代摘要

### 第 1 轮：从模糊到清晰

**初始状态：** 只有"做一个 TDD Coding Harness"的想法。

**Brainstorming 产出：** 明确了项目定位、MVP 范围、技术栈、主要贡献。

**关键转折：** 学生提出 Feedback Engine 的详细设计，将项目从"普通 Harness"提升为"具有可扩展反馈引擎的 Harness"。

### 第 2 轮：从讨论到规约

**初始状态：** SPEC.md 包含 Brainstorming 的问答形式。

**问题发现：** SPEC 中出现"我建议……""你觉得呢？""是否采用？"等讨论性内容，不符合软件规格说明书的规范。

**修正：** 将 SPEC.md 改为纯规格说明（全部是"已决定"的陈述），所有讨论过程迁移到 SPEC_PROCESS.md。

---

## 四、AI 建议 vs 学生决策 对照表

| 议题 | AI 建议 | 学生决策 | 采纳/修正/推翻 |
|------|---------|---------|--------------|
| MVP 范围 | 建议选出核心功能 | 全部保留（A~G），F/G 最小实现 | **修正**（更完整） |
| 主要贡献 | 选 Feedback Loop | 选 Feedback Engine（深化） | **采纳并深化** |
| 技术栈 | 列出三个选项 | Python 3.12 | **采纳** |
| LLM 抽象 | 做抽象层 | 做抽象层 + 强调 Mock 可测试性 | **采纳并深化** |
| 目录结构 | 建议标准模块结构 | 提出 docs/ 分离、src/providers/ 分离 | **采纳** |
| SPEC 风格 | 按规范格式写 | 指出问答形式不符合规范，要求拆分 | **学生主导修正** |

---

## 五、反思

### Brainstorming 做得好的地方

1. **追问质量高**：智能体在 MVP 范围、技术选型等关键节点都提出了有区分度的选项，帮助学生做决策。
2. **及时纠正**：学生发现 SPEC 中混入了 Brainstorming 内容并主动要求拆分，这是对文档质量的重要把控。

### 不足之处

1. **SPEC 初稿风格偏差**：第一版 SPEC 混入了问答形式的讨论内容，说明在设计阶段就应明确区分"过程文档"与"规格文档"。
2. **验收标准可量化性**：部分验收标准仍偏笼统（如"可运行""语法正确"），后续 PLAN.md 中需要进一步细化。

### 学到的教训

- 软件规格说明书（SPEC）应该只包含"已决定"的事实陈述，所有"为什么这样选"的记录应归入 SPEC_PROCESS.md
- 在 Brainstorming 阶段就应将两个文档的边界划清楚，避免后续重写工作

---

> **本文件对应课程要求：** AI4SE 期末项目 · 通用要求 §4.4 — SPEC_PROCESS.md（过程文档）