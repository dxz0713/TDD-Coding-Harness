# PR: pr-feedback

## 对应 Task
- T15: Feedback 数据模型（FailureType 枚举、AnalysisResult、Feedback）
- T16: Collector + FailureAnalyzer（7 种失败类型分类）
- T17: FeedbackEngine + 自适应修复策略

## 关联 Commit
- `009cb4a` — feat: implement T11 (Loop), T16 (Analyzer)
- `3a2b89c` — feat: implement T17 (FeedbackEngine + Strategies)

## Sub-agent 任务描述
参见 `.claude/T11T16.md`、`.claude/T17.md`

## 人工修改记录
- 无（全部由 sub-agent 自动完成）

## 验证
- [x] `pytest src/tests/ -v` 全部通过
- [x] 7 种 FailureType 全部覆盖
- [x] AssertionError 提取预期/实际值
- [x] 不同 FailureType 生成不同的 repair_prompt
- [x] 成功结果不产生 Feedback