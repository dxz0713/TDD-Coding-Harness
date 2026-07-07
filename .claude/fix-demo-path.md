# Task 描述：Fix — Demo 脚本路径修复

## 问题

`examples/demo_guardrail.py`、`examples/demo_feedback.py`、`examples/demo_autonomous_repair.py` 三个文件的 Usage 注释中写死了路径 `D:\\Python3.12\\python.exe`，这是开发者本机的真实路径，对其他用户不可用。

## 修复要求

将三个文件中的：

```
Usage:
    D:\\Python3.12\\python.exe examples/demo_xxx.py
```

改为：

```
Usage:
    python examples/demo_xxx.py
```

**只改注释，不改代码逻辑，不改测试。**

## 涉及文件

- `examples/demo_guardrail.py`（第 3-4 行）
- `examples/demo_feedback.py`（第 3-4 行）
- `examples/demo_autonomous_repair.py`（第 6-7 行）

## 验证

```bash
D:\Python3.12\python.exe -m pytest src/tests/ -v
D:\Python3.12\python.exe examples/demo_guardrail.py
D:\Python3.12\python.exe examples/demo_feedback.py
D:\Python3.12\python.exe examples/demo_autonomous_repair.py
```

## DoD

- [x] 三个文件的 Usage 注释改为 `python` 而非本机路径
- [x] 210 个测试全部通过
- [x] 三个 demo 正常运行