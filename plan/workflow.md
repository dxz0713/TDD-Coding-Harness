我认为你现在已经完成了**第一步：选题**。

> **项目名称（暂定）**
>
> **TDD Coding Harness —— 一个具有测试反馈闭环的 Coding Agent Harness**

接下来就不要直接写代码了，而是严格按照老师要求的流程走，这样最后所有交付物都会自然产生，而不是后面补文档。

---

# 整体流程（推荐）

```text
① 选题（完成）
        │
        ▼
② Brainstorming（需求设计）
        │
        ▼
③ SPEC.md
        │
        ▼
④ PLAN.md
        │
        ▼
⑤ 冷启动验证（另一个 Agent）
        │
        ▼
⑥ 修改 SPEC / PLAN
        │
        ▼
⑦ 建立 Git Worktree
        │
        ▼
⑧ TDD 开发（一个 Task 一个 PR）
        │
        ▼
⑨ CI / Docker
        │
        ▼
⑩ README
        │
        ▼
⑪ REFLECTION
```

这几乎就是老师要求的 Superpowers 七步工作流。

---

# 第一阶段：设计（现在）

这是最重要的阶段。

## Step 1 Brainstorming

不要马上写代码。

而是回答一系列问题。

例如：

> Harness解决什么问题？

> 谁会使用？

> 为什么不用Codex？

> 最小可运行版本有哪些功能？

> MVP是什么？

> 哪个机制作为主要贡献？

最后得到：

```
Project Vision
```

这个阶段对应：

```
brainstorming skill
```

老师明确要求先完成 brainstorming，再生成 SPEC。

---

## Step 2 写 SPEC.md

不是写代码。

而是把所有设计固定下来。

包括：

```
Problem

Architecture

Workflow

Modules

Data Model

Security

Acceptance
```

老师要求的 10 个章节都在这里。

对于 A 类，还要增加：

```
领域与机制设计
```

说明：

* Feedback

* Guardrail

* Tool

* Memory

准备怎么编码实现。

---

## Step 3 写 PLAN.md

把开发拆成：

例如：

```
Task 1

LLM Interface

---------

Task 2

Main Loop

---------

Task 3

Tool Dispatcher

---------

Task 4

RunTests Tool

---------
```

每个 Task：

都有：

* 文件

* 测试

* 验证

老师要求每个 Task 都能由一个 Subagent 独立完成。

---

## Step 4 冷启动验证

这是很多人会忘记的一步。

老师要求：

找一个**不同于主开发 Agent** 的智能体，仅凭 `SPEC.md` 和 `PLAN.md` 尝试实现 1–2 个 Task，记录它遇到的问题，并据此修改规约。

如果你主要用 Codex CLI，可以考虑用 ChatGPT（网页）或其他不同类型的智能体来完成这一步。

---

# 第二阶段：开发

现在才开始写代码。

## 建议的模块

```
src/

harness/

tools/

tests/
```

例如：

```
src/
│
├── harness/
│     loop.py
│
│     dispatcher.py
│
│     feedback.py
│
│     guardrail.py
│
│     memory.py
│
│     llm.py
│
├── tools/
│
├── tests/
│
└── config/
```

---

## 一个 Task 一个 PR

例如：

```
Task1

↓

Worktree1

↓

PR1

---------

Task2

↓

Worktree2

↓

PR2
```

符合老师要求。

---

## TDD

每一个 Task：

```
写失败测试

↓

FAIL

↓

实现

↓

PASS

↓

Refactor
```

不要反过来。老师把这一点列为硬性要求。

---

# 第三阶段：完善

包括：

* Docker 或二进制分发
* CI（至少包含 `unit-test`）
* README
* AGENT_LOG
* REFLECTION
* （如果有服务端）部署并提供可访问 URL。

---

# 我建议我们的合作方式

如果按这个项目推进，我建议不要一上来就写代码，而是按照课程节奏逐步完成：

1. **第 1 天：Brainstorming**（把项目需求问清楚、定下来）
2. **第 2 天：完成 `SPEC.md`**
3. **第 3 天：完成 `PLAN.md`，拆成 15–25 个可独立完成的 Task**
4. **第 4 天：进行冷启动验证，修订 SPEC/PLAN**
5. **之后：按 TDD 一个 Task 一个 PR 开发，直到全部完成**

这样做的好处是，你整个开发过程都会与老师要求一一对应，最终交付物（`SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md` 等）都是开发过程中自然产生的，而不是最后临时补写。
