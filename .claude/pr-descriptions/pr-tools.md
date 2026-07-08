# PR: pr-tools

## 对应 Task
- T6: BaseTool 抽象 + ToolDispatcher
- T7: ReadFile 工具
- T8: WriteFile 工具
- T9: RunShell 工具

## 关联 Commit
- `c639657` — feat: implement T5 (OpenAIProvider), T7-T9 (Tools)

## Sub-agent 任务描述
参见 `.claude/T5T7T8T9.md`

## 人工修改记录
- 无（全部由 sub-agent 自动完成）

## 验证
- [x] `pytest src/tests/ -v` 全部通过
- [x] 路径越界检查（`../`）正常工作
- [x] RunShell 超时控制正常工作
- [x] 自动创建父目录功能正常