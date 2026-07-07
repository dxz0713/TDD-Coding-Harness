"""Tests for MemoryStore (T14).

Covers save/load round-trip, loading non-existent files, adding
decisions, formatting context, and auto-truncation.
"""

from __future__ import annotations

from pathlib import Path

from harness.memory import MemoryStore
from harness.models import Decision, Memory


class TestMemoryStore:
    """MemoryStore persists project memory as a JSON file."""

    # ── save and load ───────────────────────────────────────────────

    def test_save_and_load(self, tmp_path: Path) -> None:
        """写入 → 读取 → 内容一致。"""
        store = MemoryStore(path=str(tmp_path / "memory.json"))
        memory = Memory(
            project_name="TestProject",
            project_description="A test project",
            tech_stack=["python", "pytest"],
            conventions=["Use type hints"],
        )
        store.save(memory)
        loaded = store.load()
        assert loaded.project_name == "TestProject"
        assert loaded.project_description == "A test project"
        assert loaded.tech_stack == ["python", "pytest"]
        assert loaded.conventions == ["Use type hints"]

    def test_save_and_load_with_decisions(self, tmp_path: Path) -> None:
        """含决策的完整写入/读取。"""
        store = MemoryStore(path=str(tmp_path / "memory.json"))
        memory = Memory(
            project_name="MyApp",
            decisions=[
                Decision(timestamp="2024-01-01", description="Initial decision", reason="Reason A"),
            ],
        )
        store.save(memory)
        loaded = store.load()
        assert loaded.project_name == "MyApp"
        assert len(loaded.decisions) == 1
        assert loaded.decisions[0].description == "Initial decision"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """父目录不存在时自动创建。"""
        nested = tmp_path / "nested" / "dir" / "memory.json"
        store = MemoryStore(path=str(nested))
        memory = Memory(project_name="Nested")
        store.save(memory)
        assert nested.exists()
        loaded = store.load()
        assert loaded.project_name == "Nested"

    # ── load non-existent ───────────────────────────────────────────

    def test_load_non_existent(self) -> None:
        """文件不存在 → 返回空 Memory。"""
        store = MemoryStore(path="/tmp/nonexistent_memory_file_xyz.json")
        memory = store.load()
        assert isinstance(memory, Memory)
        assert memory.project_name == ""
        assert memory.decisions == []

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        """无效 JSON → 返回空 Memory。"""
        f = tmp_path / "invalid.json"
        f.write_text("not json", encoding="utf-8")
        store = MemoryStore(path=str(f))
        memory = store.load()
        assert isinstance(memory, Memory)
        assert memory.project_name == ""

    # ── add_decision ────────────────────────────────────────────────

    def test_add_decision(self) -> None:
        """追加决策 → decisions 列表长度增加。"""
        store = MemoryStore()
        memory = Memory()
        assert len(memory.decisions) == 0
        decision = Decision(
            timestamp="2024-06-01T12:00:00",
            description="Switch to pytest",
            reason="Better assertions",
        )
        memory = store.add_decision(memory, decision)
        assert len(memory.decisions) == 1
        assert memory.decisions[0].description == "Switch to pytest"

    def test_add_multiple_decisions(self) -> None:
        """多次追加决策。"""
        store = MemoryStore()
        memory = Memory()
        for i in range(3):
            memory = store.add_decision(
                memory,
                Decision(
                    timestamp=f"2024-06-0{i + 1}",
                    description=f"Decision {i}",
                    reason=f"Reason {i}",
                ),
            )
        assert len(memory.decisions) == 3

    # ── get_context ─────────────────────────────────────────────────

    def test_get_context(self) -> None:
        """get_context() 返回格式化的字符串。"""
        store = MemoryStore()
        memory = Memory(
            project_name="MyProject",
            tech_stack=["python"],
            conventions=["Use type hints"],
            decisions=[
                Decision(timestamp="2024-01-01", description="Chose pytest", reason="Better"),
            ],
        )
        ctx = store.get_context(memory)
        assert "MyProject" in ctx
        assert "python" in ctx
        assert "Use type hints" in ctx
        assert "Chose pytest" in ctx

    def test_get_context_empty(self) -> None:
        """空 memory → 返回默认消息。"""
        store = MemoryStore()
        ctx = store.get_context(Memory())
        assert "No project context available" in ctx

    def test_get_context_partial(self) -> None:
        """部分填充的 memory。"""
        store = MemoryStore()
        memory = Memory(project_name="OnlyName")
        ctx = store.get_context(memory)
        assert "OnlyName" in ctx
        assert "No project context" not in ctx

    # ── auto_truncate ───────────────────────────────────────────────

    def test_auto_truncate(self, tmp_path: Path) -> None:
        """超过限制 → 截断保留最近 N 条。"""
        # Create a memory file larger than 1MB
        f = tmp_path / "large_memory.json"
        # Pre-populate with a large file — 150 decisions with 10k char reasons each
        large_data = {
            "project_name": "Large",
            "decisions": [
                {
                    "timestamp": f"2024-01-{i:02d}",
                    "description": f"Decision {i}",
                    "reason": "x" * 10_000,  # Big reason to make the file large
                }
                for i in range(150)
            ],
        }
        import json
        f.write_text(json.dumps(large_data), encoding="utf-8")

        # Verify the file is indeed larger than 1MB
        file_size = f.stat().st_size
        assert file_size > 1_048_576, f"Test file too small: {file_size} bytes"

        store = MemoryStore(path=str(f))
        memory = store.load()
        assert len(memory.decisions) == 150
        # Save should trigger truncation since file > 1MB
        store.save(memory)
        # Re-load and verify
        reloaded = store.load()
        assert len(reloaded.decisions) <= 100

    def test_no_truncate_small_file(self, tmp_path: Path) -> None:
        """小文件不截断。"""
        store = MemoryStore(path=str(tmp_path / "small.json"))
        memory = Memory(
            project_name="Small",
            decisions=[
                Decision(timestamp="2024-01-01", description="D1", reason="R1"),
                Decision(timestamp="2024-01-02", description="D2", reason="R2"),
            ],
        )
        store.save(memory)
        loaded = store.load()
        assert len(loaded.decisions) == 2