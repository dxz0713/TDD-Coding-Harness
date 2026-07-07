# REFLECTION

> **Project:** TDD Coding Harness — AI4SE Final Project Category A
> **Date:** 2026-07-07

## 总体回顾

本项目从零开始实现了一个完整的 TDD Coding Agent Harness，涵盖 CLI、Provider 抽象、Tool 调度、Guardrail、Main Loop、Feedback Engine 等核心模块。以下是对整个开发过程的反思。

## 做得好的

### 1. 文档先行（Documentation-Driven）

在写任何代码之前，先完成了 SPEC.md、SPEC_PROCESS.md、PLAN.md 三份文档。这确保了：
- 所有设计决策有据可查
- 任务分解清晰，依赖关系明确
- 后期实现时减少了"回头改设计"的成本

### 2. 模块化设计

系统被拆分为 6 个独立包（harness、providers、tools、feedback、tests、examples），每个包有清晰的职责边界。特别是：
- 依赖注入使 `HarnessLoop` 不需要知道任何具体实现的细节
- 注册表模式使新增 Provider 或 Tool 变得简单
- 策略模式使新增 Feedback 失败类型只需添加 Strategy 类

### 3. 测试驱动

210+ 个测试覆盖了所有模块的核心路径和边界情况。测试文件与源文件一一对应，保持了良好的可维护性。

### 4. 子代理协作模式

通过 `.claude/T*.md` 任务描述文件 + 子代理的方式，实现了：
- 任务并行执行（如 T3/T4/T6 在一个子代理中完成）
- 每个子代理有明确的任务边界
- 主代理负责协调和集成

## 可以改进的

### 1. 任务粒度不均衡

部分 Task 过于细小（如 T7/T8/T9 三个工具分别占一个 Task），导致 commit 数量多但每个 commit 的变更量小。可以合并为"工具实现"一个 Task。

### 2. 测试覆盖率

虽然总量 210+，但缺少对以下场景的测试：
- 网络超时和重试逻辑
- 大文件读写边界情况
- 并发安全（当前为单线程，但 MCP 工具可能异步调用）

### 3. 错误处理一致性

部分模块的异常直接抛出（如 Config 的 `FileNotFoundError`），而其他模块返回 `ToolResult` 包装错误。统一的错误处理策略可以减少调用方的防御性代码。

### 4. 子代理上下文管理

子代理完成任务后，主代理需要手动阅读其输出并整合。如果子代理数量增多（如 10+），这种模式会变得难以管理。可以考虑引入更结构化的输出格式（如 JSON Schema）。

## 关键技术决策复盘

| 决策 | 选择 | 替代方案 | 评价 |
|------|------|----------|------|
| CLI 框架 | typer | argparse, click | 正确，类型注解自动生成 help |
| Provider 注册 | 注册表模式 | 条件分支 | 正确，扩展性好 |
| 反馈引擎架构 | Collector→Analyzer→Strategy | 单一函数 | 正确，策略模式便于扩展 |
| 测试框架 | pytest | unittest | 正确，fixture 和参数化更灵活 |
| 配置优先级 | CLI > 文件 > 默认值 | 仅文件配置 | 正确，灵活性高 |
| 跨会话存储 | JSON 文件 | SQLite, Redis | 原型阶段正确，生产需升级 |

## 总结

本项目成功实现了一个教学导向的 TDD Coding Agent Harness，核心贡献（Feedback Engine）展示了如何将测试反馈闭环集成到 LLM agent 的工作流中。19 个 Task 按计划顺利完成，210+ 测试通过，3 个 Demo 可运行。最重要的是，**整个开发过程本身就是 AI 辅助软件工程的实践**——从需求分析到设计、编码、测试，每一步都由 AI Agent 辅助完成。