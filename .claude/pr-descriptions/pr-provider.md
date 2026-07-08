# PR: pr-provider-layer

## 对应 Task
- T3: CLI 入口（typer 框架，`--provider`/`--model` 参数）
- T4: LLMProvider 抽象 + MockProvider + ProviderFactory
- T5: OpenAICompatibleProvider

## 关联 Commit
- `0f7247c` — feat: implement T3 (CLI), T4 (Providers), T6 (Tool Dispatcher)
- `c639657` — feat: implement T5 (OpenAIProvider), T7-T9 (Tools)

## Sub-agent 任务描述
参见 `.claude/T3T4T6.md`、`.claude/T5T7T8T9.md`

## 人工修改记录
- 无（全部由 sub-agent 自动完成）

## 验证
- [x] `pytest src/tests/ -v` 全部通过
- [x] `tdd-harness run --help` 可运行
- [x] `tdd-harness run "test task" --provider mock` 可在 Mock 模式下运行