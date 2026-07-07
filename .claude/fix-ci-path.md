# Task 描述：Fix — CI 测试路径

## 问题

`.github/workflows/ci.yml` 中 `pytest tests/ -v` 路径错误。测试代码在 `src/tests/` 目录下，而不是 `tests/`。

## 修复

将 `.github/workflows/ci.yml` 第 23 行从：

```yaml
        run: pytest tests/ -v
```

改为：

```yaml
        run: pytest src/tests/ -v
```

## 涉及文件

- `.github/workflows/ci.yml`

## 验证

确保 CI 中的 `pytest` 命令能找到所有 210 个测试用例，而不是报 `no tests ran`。

## DoD

- [x] CI 命令路径改为 `src/tests/`
- [x] 推送后 CI 运行通过（209 passed / 1 failed — 唯一的失败 `test_openai_provider_can_be_created_via_factory` 是预先存在的环境问题，需要 OpenAI API key，与本次修改无关）