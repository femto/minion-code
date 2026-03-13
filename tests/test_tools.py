"""Tests for minion-code tool contracts."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import minion_code.agents.code_agent as code_agent_module
from minion_code.tools import (
    BashTool,
    FileReadTool,
    FileWriteTool,
    TaskCancelTool,
    TaskListTool,
    TaskOutputTool,
    TaskStatusTool,
    TaskTool,
    TOOL_MAPPING,
)


def test_tool_mapping_contains_background_task_tools():
    """Background task tools should be registered."""
    assert "bash" in TOOL_MAPPING
    assert "TaskStatus" in TOOL_MAPPING
    assert "TaskOutput" in TOOL_MAPPING
    assert "TaskList" in TOOL_MAPPING
    assert "TaskCancel" in TOOL_MAPPING


def test_file_read_tool(tmp_path: Path):
    """File read should return file content."""
    tool = FileReadTool(workdir=str(tmp_path))
    target = tmp_path / "sample.txt"
    target.write_text("Hello\nWorld\nTest", encoding="utf-8")

    result = tool.forward(str(target))

    assert "Hello" in result
    assert "World" in result
    assert "Test" in result


def test_file_write_tool(tmp_path: Path):
    """File write should create the target file."""
    tool = FileWriteTool(workdir=str(tmp_path))
    target = tmp_path / "test.txt"

    result = tool.forward(str(target), "Hello, World!")

    assert "wrote" in result.lower()
    assert target.read_text(encoding="utf-8") == "Hello, World!"


@pytest.mark.asyncio
async def test_bash_tool_foreground(tmp_path: Path):
    """Short bash commands should complete in the foreground."""
    tool = BashTool(workdir=str(tmp_path))

    result = await tool.forward("echo 'Hello World'", auto_background_after=5)

    assert result["mode"] == "foreground"
    assert result["status"] == "completed"
    assert "Hello World" in result["output"]


@pytest.mark.asyncio
async def test_bash_tool_background_and_task_tools(tmp_path: Path):
    """Longer bash commands should expose task status and output via task tools."""
    bash = BashTool(workdir=str(tmp_path))
    status_tool = TaskStatusTool(workdir=str(tmp_path))
    output_tool = TaskOutputTool(workdir=str(tmp_path))
    list_tool = TaskListTool(workdir=str(tmp_path))
    cancel_tool = TaskCancelTool(workdir=str(tmp_path))

    result = await bash.forward(
        "python -c \"import time; print('start'); time.sleep(2); print('done')\"",
        auto_background_after=1,
    )

    assert result["mode"] == "background"
    task_id = result["task_id"]

    status = status_tool.forward(task_id)
    assert status["task_id"] == task_id
    assert status["status"] in {"running", "completed"}

    await asyncio.sleep(2.5)

    output = output_tool.forward(task_id)
    assert "start" in output["content"]
    assert "done" in output["content"]

    listed = list_tool.forward()
    assert any(task["task_id"] == task_id for task in listed["tasks"])

    cancelled = await cancel_tool.forward(task_id)
    assert cancelled["cancelled"] is False
    assert cancelled["status"] in {"completed", "failed", "cancelled"}


@pytest.mark.asyncio
async def test_task_tool_foreground_contract(tmp_path: Path, monkeypatch):
    """Task should return structured foreground results for short subagent runs."""

    class FakeRegistry:
        def __init__(self):
            self._config = SimpleNamespace(
                system_prompt=None,
                model_name="inherit",
                tools="*",
                readonly=False,
                description="fake",
                when_to_use="fake",
            )

        def get(self, name):
            return self._config if name == "general-purpose" else None

        def exists(self, name):
            return name == "general-purpose"

        def list_names(self):
            return ["general-purpose"]

        def list_all(self):
            return [self._config]

        def generate_tool_description_lines(self):
            return "- general-purpose: fake"

    class FakeChunk:
        def __init__(self, chunk_type, content="", answer=None, metadata=None):
            self.chunk_type = chunk_type
            self.content = content
            self.answer = answer
            self.metadata = metadata or {}

    class FakeAgent:
        async def run_async(self, prompt, stream=False):
            assert prompt == "Do the thing"
            assert stream is True

            async def generator():
                yield FakeChunk("thinking", "working...")
                yield FakeChunk("final_answer", "done", answer="done")

            return generator()

    class FakeMinionCodeAgent:
        @classmethod
        async def create(cls, **kwargs):
            return FakeAgent()

    monkeypatch.setattr(code_agent_module, "MinionCodeAgent", FakeMinionCodeAgent)

    tool = TaskTool(workdir=str(tmp_path))
    tool._registry = FakeRegistry()

    result = await tool.forward(
        description="Fake task",
        prompt="Do the thing",
        auto_background_after=5,
        state=SimpleNamespace(metadata={}),
    )

    assert result["mode"] == "foreground"
    assert result["status"] == "completed"
    assert result["result"] == "done"
