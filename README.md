# TDD Coding Harness

一个教学导向的 Coding Agent Harness。项目自己实现了 agent 主循环、LLM Provider 抽象、工具分发、Guardrail、Context、Memory，以及主要贡献 Feedback Engine。它可以在本地 CLI 中运行，也部署了一个可访问的 FastAPI WebUI。

项目仓库：

- GitHub: <https://github.com/dxz0713/TDD-Coding-Harness>
- WebUI: <https://tdd-coding-harness.vercel.app/>

## 快速检查顺序

1. 阅读 `docs/README.md`、`docs/SPEC.md`、`docs/PLAN.md`、`docs/SPEC_PROCESS.md`。
2. 打开 WebUI，先运行 Mock demo。
3. 在 WebUI 中填写真实 API Key，运行 Real API 任务。
4. 如需本地复现，clone GitHub 仓库后按本文命令运行。

## 测试助教提示

- 本地 Real API 测试可用 PowerShell 临时环境变量传入 Key：`$env:OPENAI_API_KEY = "your-api-key"`，不要写入源码、配置文件或日志。
- WebUI Real API 测试时，API Key 仅用于本次后端调用，不写入仓库、不写入服务端文件、不在响应 HTML 中回显；如果兼容 API 的错误文本包含 Key，WebUI 会在展示 Output 和写入前端缓存前脱敏。浏览器端仅在当前标签页的 `sessionStorage` 中保留并保持输入框可见，关闭标签页后失效。
- 如果测试助教不希望使用自己的 Key，可联系作者获取仅适用于 `https://njusehub.info/v1` 的限时、限额临时 API Key；该 Key 不随提交文档公开。

## 从源码本地运行

### 1. 获取源码

public仓库

```bash
git clone https://github.com/dxz0713/TDD-Coding-Harness.git
cd TDD-Coding-Harness
```

### 2. 安装依赖

建议使用 Python 3.12+。

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Linux / macOS:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### 3. 一键测试

```bash
pytest tests/ -v
```

最后一次本地验证结果：

```text
213 passed, 1 skipped
```

其中唯一 skipped 测试是 `test_openai_provider_can_be_created_via_factory`。它只在本机未设置 `OPENAI_API_KEY` 时跳过，目的是让默认单元测试不依赖真实凭据；OpenAI-compatible Provider 的格式转换、工厂注册、Mock LLM 与 Harness 机制均由确定性测试覆盖，真实 API 行为通过本地 Real API 与 WebUI 验证。

## 本地 Mock 运行

Mock 模式用于离线、确定性地检查 harness 机制，不需要 API Key，也不调用真实 LLM。

推荐运行三个机制演示：

```bash
python examples/demo_guardrail.py
python examples/demo_feedback.py
python examples/demo_autonomous_repair.py
```

含义：

- `demo_guardrail.py`：演示危险 shell 命令被 Guardrail 拦截。
- `demo_feedback.py`：演示 Feedback Engine 对失败类型进行分类并生成修复提示。
- `demo_autonomous_repair.py`：演示 MockProvider 下的完整 TDD 闭环，包含写代码、测试失败、反馈修复、测试通过。

也可以运行 CLI 的 mock provider：

```bash
tdd-harness run "检查 mock provider" --provider mock
```

说明：CLI 的 `--provider mock` 是底层测试替身，默认不生成真实代码任务；完整 mock 检查应使用 `examples/` 或 WebUI 的 Mock demo。

## 本地 Real API 运行

真实 API 模式使用 OpenAI-compatible API。不要把 API Key 写入源码、配置文件或日志。

PowerShell 临时环境变量：

```powershell
$env:OPENAI_API_KEY = "your-api-key"
tdd-harness run "编写一个计算斐波那契数列的函数" --provider openai --model deepseek-v4-pro
```

Linux / macOS:

```bash
export OPENAI_API_KEY="your-api-key"
tdd-harness run "编写一个计算斐波那契数列的函数" --provider openai --model deepseek-v4-pro
```

课程 endpoint 可用本地配置文件指定：

```powershell
@"
version: 1

provider:
  name: openai
  model: deepseek-v4-pro
  base_url: https://njusehub.info/v1
  temperature: 0.0
  max_tokens: 4096
  timeout: 60

loop:
  max_iterations: 15
  workspace: ./workspace

guardrail:
  enabled: true
  block_list: []

memory:
  enabled: true
  path: output/memory.json
"@ | Set-Content -Encoding UTF8 config.local.yaml

$env:OPENAI_API_KEY = "your-api-key"
tdd-harness run "编写一个计算斐波那契数列的函数" --config config.local.yaml
```

`config.local.yaml` 已被 `.gitignore` 排除，不应提交。

## 本地产物位置

CLI 每次运行都会在配置的 `loop.workspace` 下创建一个独立任务目录，默认是 `./workspace`。

示例：

```text
workspace/
├── fib/
│   ├── fib.py
│   ├── test_fib.py
│   └── log.txt
└── gcd/
    ├── gcd.py
    ├── test_gcd.py
    └── log.txt
```

规则：

- 斐波那契 / fibonacci / fib 任务默认进入 `workspace/fib`。
- 最大公约数 / 最大公因数 / gcd 任务默认进入 `workspace/gcd`。
- 其他英文任务会生成 slug，例如 `workspace/write-a-test`。
- 如果目录已存在，会自动加时间戳，例如 `workspace/fib-20260709-190946`。
- `log.txt` 保存本次 CLI 输出和 harness 迭代日志。

已有真实 API 证据：

- `workspace/fib/`：Fibonacci 任务产物和日志。
- `workspace/gcd/`：GCD 任务产物和日志。

## WebUI 运行

访问：

<https://tdd-coding-harness.vercel.app/>

### WebUI Mock 模式

1. Provider 选择 `Mock (offline)`。
2. 在 Demo 下拉框选择一个固定 demo：
   - `Autonomous repair TDD demo`
   - `Feedback engine demo`
   - `Guardrail safety demo`
3. 点击 `Run`。

说明：

- Mock 模式不能自定义 task。
- Mock 模式不需要 Base URL、Model 或 API Key。
- 输出格式会显示 `Provider: mock`、固定 demo task、迭代摘要。
- 页面下方会显示 `Artifacts`。如果该 demo 不生成文件，会显示空状态；如果生成文件，会展示文件内容并提供 zip 下载。

### WebUI Real API 模式

1. Provider 选择 `OpenAI-compatible`。
2. 填写 Task，例如：

```text
编写一个计算斐波那契数列的函数
```

3. 填写 Base URL：

```text
https://njusehub.info/v1
```

4. 填写 Model：

```text
deepseek-v4-pro
```

5. 填写 API Key。输入框默认隐藏，浏览器自带眼睛图标可临时显示。
6. 点击 `Run`。

说明：

- 点击 `Run` 后按钮会切换为 `Running` 并禁用，避免重复提交。
- 运行结束后按钮旁状态会根据 Harness 结果显示 `Complete` 或 `Run failed`；API Key 错误、鉴权失败、测试失败等不会被标成完成。
- WebUI 使用前端提交并只更新结果区，刷新页面会保留当前标签页中的表单状态和最近一次 Output / Artifacts，但不会重复运行上一次任务；只有再次点击 `Run` 才会发起新任务。
- 如果在 `Running` 状态刷新页面，浏览器会中断当前前端请求；页面会提示 previous run was interrupted，并允许重新点击 `Run`。
- API Key 不写入仓库文件，也不在服务端持久化或回显到响应 HTML；如果兼容 API 的错误文本包含 Key，WebUI 会在展示 Output 和写入前端缓存前脱敏。WebUI 会在当前浏览器标签页的 `sessionStorage` 中保留并保持输入框可见，方便同一标签页连续运行 Real API 任务，关闭标签页后失效。
- WebUI 会把本次运行放入服务器临时目录。
- 请求结束前，WebUI 会收集临时目录中的产物，直接展示在页面的 `Artifacts` 区域，并提供 `artifacts.zip` 下载。
- Vercel 临时目录不会长期保存，因此老师应在当次结果页查看或下载产物。

## Docker 运行

```bash
docker build -t tdd-harness .
docker run --rm tdd-harness --help
```

本地最终验证结果：

```text
docker build -t tdd-harness .        -> success
docker run --rm tdd-harness --help   -> success
```

## CI/CD

- GitHub Actions: <https://github.com/dxz0713/TDD-Coding-Harness/actions>
- Vercel 部署绑定 GitHub `master` 分支，push 后自动重构。
- 课程要求的 `.gitlab-ci.yml` 也保留在仓库中，包含 `unit-test` job。

## 架构说明

```text
CLI / WebUI
    -> Config
    -> ProviderFactory
    -> HarnessLoop
    -> ToolDispatcher / Guardrail / FeedbackEngine / Memory
```

核心模块：

- `src/harness/loop.py`：agent 主循环。
- `src/providers/`：MockProvider 与 OpenAI-compatible Provider。
- `src/tools/`：`read_file`、`write_file`、`run_shell`。
- `src/feedback/`：Collector、FailureAnalyzer、RepairStrategy、FeedbackEngine。
- `src/harness/guardrail.py`：危险动作拦截。
- `webui/app.py`：Vercel 上的 FastAPI WebUI。

## 项目结构

```text
├── src/                         # harness 源码
├── examples/                    # mock 机制演示脚本
├── tests/                       # 顶层 pytest tests/ 入口
├── docs/                        # 设计、计划、过程与提交索引
├── plan/                        # 课程原始要求
├── workspace/                   # 本地真实 API 运行产物
├── webui/                       # FastAPI WebUI
├── .github/workflows/ci.yml     # GitHub Actions CI
├── .gitlab-ci.yml               # 课程要求的 GitLab CI job
├── Dockerfile
├── config.yaml
├── pyproject.toml
├── docs/AGENT_LOG.md
├── docs/REFLECTION.md
└── README.md
```

## 安全说明

- API Key 通过环境变量或 WebUI 表单传入；WebUI 后端只在单次请求中使用 Key 调用模型，不写入服务端文件或响应 HTML；浏览器端仅在当前标签页会话内保留，不写入仓库或服务器持久存储。
- `.env`、`.env.local`、`config.local.yaml`、`*.key` 已在 `.gitignore` 中排除。
- 不要将真实 API Key 写入 README、日志、截图、配置或 commit history。
- `workspace/fib/log.txt` 与 `workspace/gcd/log.txt` 已检查，不包含真实 API Key。
- Guardrail 会在 shell 执行前拦截危险命令，如 `rm -rf /`、fork bomb、破坏性数据库命令等。

## 已知限制

- 当前只实现 OpenAI-compatible Provider，未实现 Anthropic Claude Provider。
- Feedback Analyzer 主要针对 pytest 输出。
- WebUI 是演示层，不提供用户登录、任务持久化或多用户隔离。
- Vercel 临时目录只在单次请求内可靠，长期产物请使用本地 CLI 的 `workspace/`。
