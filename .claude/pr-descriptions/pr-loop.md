# PR: pr-loop

## 对应 Task
- T11: Main Loop 框架（依赖注入 HarnessLoop）
- T18: 集成 Feedback Engine 到 Main Loop

## 关联 Commit
- `009cb4a` — feat: implement T11 (Loop), T16 (Analyzer)
- `d4643d4` — feat: implement T18 (Feedback->Loop integration), T19 (Demo scripts)

## Sub-agent 任务描述
参见 `.claude/T11T16.md`、`.claude/T18T19.md`

## 人工修改记录
- 无（全部由 sub-agent 自动完成）

## 验证
- [x] `pytest src/tests/ -v` 全部通过
- [x] 完整 TDD 闭环可运行（MockProvider 模式）
- [x] Feedback 反馈回灌到 LLM 上下文
- [x] 止损策略：连续同一错误达到迭代上限后停机
- [x] 日志记录完整的 Feedback 分类结果