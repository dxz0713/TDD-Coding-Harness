# workspace

`workspace/` 用于保存本地 CLI 真实 API 运行产生的代码、测试和日志。

当前 CLI 已改为自动在 `loop.workspace` 下创建独立任务目录；不再需要先在项目根目录运行后手动移动文件。

## 生成规则

默认配置 `config.yaml` 中：

```yaml
loop:
  workspace: ./workspace
```

因此运行：

```bash
tdd-harness run "编写一个计算斐波那契数列的函数" --provider openai --model deepseek-v4-pro
```

会直接在 `workspace/` 下生成任务目录，例如：

```text
workspace/fib/
├── fib.py
├── test_fib.py
└── log.txt
```

如果同名目录已存在，会自动加时间戳，例如：

```text
workspace/fib-20260709-190946/
```

## 当前证据目录

- `fib/`：真实 API 生成 Fibonacci 函数任务的产物。
- `gcd/`：真实 API 生成最大公因数函数任务的产物。

每个任务目录中：

- `*.py`：LLM 通过 harness 工具生成的源码和测试。
- `log.txt`：本次 CLI 输出与 harness 迭代日志。

`log.txt` 已检查，不包含真实 API Key。
