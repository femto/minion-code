"""Tests for minion-code tool contracts."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

import minion_code.agents.code_agent as code_agent_module
import minion_code.tools.glob_tool as glob_tool_module
import minion_code.tools.grep_tool as grep_tool_module
from minion_code.tools import (
    BashTool,
    FileReadTool,
    FileWriteTool,
    GlobTool,
    GrepTool,
    LsTool,
    TaskCreateTool,
    TaskGetTool,
    TaskListTool,
    TaskOutputTool,
    TaskStopTool,
    UserInputTool,
    TOOL_MAPPING,
)
from minion_code.utils.step_status import humanize_step_status


def test_tool_mapping_contains_background_task_tools():
    """Background task tools should be registered."""
    assert "bash" in TOOL_MAPPING
    assert "TaskCreate" in TOOL_MAPPING
    assert "TaskGet" in TOOL_MAPPING
    assert "TaskOutput" in TOOL_MAPPING
    assert "TaskList" in TOOL_MAPPING
    assert "TaskStop" in TOOL_MAPPING


def test_step_status_hides_fractional_counter():
    """Internal step counters should not leak to user-facing status text."""
    assert humanize_step_status("Step 1/5") == "Working"
    assert humanize_step_status("Step 2/5 indexing files") == "indexing files"
    assert humanize_step_status("Scanning repository") == "Scanning repository"


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


def test_ls_tool_skips_hidden_entries_and_supports_files(tmp_path: Path):
    """ls should avoid noisy hidden paths and return file metadata for files."""
    tool = LsTool(workdir=str(tmp_path))
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")

    dir_result = tool.forward(".", recursive=True)
    assert "src/" in dir_result
    assert ".git" not in dir_result

    file_result = tool.forward("src/app.py")
    assert "File: app.py" in file_result
    assert "Absolute path:" in file_result


def test_glob_tool_uses_rg_ignore_patterns(tmp_path: Path, monkeypatch):
    """glob should pass default and caller-provided ignore patterns to rg."""
    tool = GlobTool(workdir=str(tmp_path))
    captured = {}

    def _fake_find_rg():
        return "/usr/bin/rg"

    def _fake_collect_rg_lines(args, cwd, max_results):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["max_results"] = max_results
        return ["src/app.py"], False

    monkeypatch.setattr(glob_tool_module, "find_rg", _fake_find_rg)
    monkeypatch.setattr(glob_tool_module, "collect_rg_lines", _fake_collect_rg_lines)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")

    result = tool.forward("**/*.py", path=".", ignore=["**/generated/**"])

    assert "src/app.py" in result
    assert "-g" in captured["args"]
    assert "!**/generated/**" in captured["args"]
    assert "!**/.git/**" in captured["args"]


def test_grep_tool_uses_rg_backend(tmp_path: Path, monkeypatch):
    """grep should prefer rg when available."""
    tool = GrepTool(workdir=str(tmp_path))
    captured = {}

    def _fake_find_rg():
        return "/usr/bin/rg"

    def _fake_collect_rg_lines(args, cwd, max_results):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["max_results"] = max_results
        return ["src/app.py:1:TODO"], False

    monkeypatch.setattr(grep_tool_module, "find_rg", _fake_find_rg)
    monkeypatch.setattr(grep_tool_module, "collect_rg_lines", _fake_collect_rg_lines)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("TODO\n", encoding="utf-8")

    result = tool.forward("TODO", path=".", include="*.py", output_mode="content")

    assert "Search results for pattern 'TODO':" in result
    assert "--regexp" in captured["args"]
    assert "TODO" in captured["args"]
    assert "!**/.git/**" in captured["args"]


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
    status_tool = TaskGetTool(workdir=str(tmp_path))
    output_tool = TaskOutputTool(workdir=str(tmp_path))
    list_tool = TaskListTool(workdir=str(tmp_path))
    stop_tool = TaskStopTool(workdir=str(tmp_path))

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

    cancelled = await stop_tool.forward(task_id)
    assert cancelled["cancelled"] is False
    assert cancelled["status"] in {"completed", "failed", "cancelled"}


@pytest.mark.asyncio
async def test_task_create_tool_foreground_contract(tmp_path: Path, monkeypatch):
    """TaskCreate should return structured foreground results for short subagent runs."""

    create_calls = []

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
            create_calls.append(kwargs)
            return FakeAgent()

    monkeypatch.setattr(code_agent_module, "MinionCodeAgent", FakeMinionCodeAgent)

    tool = TaskCreateTool(workdir=str(tmp_path))
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
    assert create_calls[0]["allowed_tool_names"] is None
    assert create_calls[0]["readonly_only"] is False


@pytest.mark.asyncio
async def test_task_create_tool_passes_readonly_subagent_constraints(
    tmp_path: Path, monkeypatch
):
    """TaskCreate should pass readonly and tool allowlist constraints to subagents."""

    create_calls = []

    class FakeRegistry:
        def __init__(self):
            self._config = SimpleNamespace(
                system_prompt=None,
                model_name="inherit",
                tools=["file_read", "grep", "web_search"],
                readonly=True,
                description="fake",
                when_to_use="fake",
            )

        def get(self, name):
            return self._config if name == "Explore" else None

        def exists(self, name):
            return name == "Explore"

        def list_names(self):
            return ["Explore"]

        def list_all(self):
            return [self._config]

        def generate_tool_description_lines(self):
            return "- Explore: fake"

    class FakeChunk:
        def __init__(self, chunk_type, content="", answer=None, metadata=None):
            self.chunk_type = chunk_type
            self.content = content
            self.answer = answer
            self.metadata = metadata or {}

    class FakeAgent:
        async def run_async(self, prompt, stream=False):
            async def generator():
                yield FakeChunk("final_answer", "done", answer="done")

            return generator()

    class FakeMinionCodeAgent:
        @classmethod
        async def create(cls, **kwargs):
            create_calls.append(kwargs)
            return FakeAgent()

    monkeypatch.setattr(code_agent_module, "MinionCodeAgent", FakeMinionCodeAgent)

    tool = TaskCreateTool(workdir=str(tmp_path))
    tool._registry = FakeRegistry()

    result = await tool.forward(
        description="Explore task",
        prompt="Inspect this codebase",
        subagent_type="Explore",
        auto_background_after=5,
        state=SimpleNamespace(metadata={}),
    )

    assert result["mode"] == "foreground"
    assert result["status"] == "completed"
    assert create_calls[0]["allowed_tool_names"] == [
        "file_read",
        "grep",
        "web_search",
    ]
    assert create_calls[0]["readonly_only"] is True


@pytest.mark.asyncio
async def test_minion_code_agent_create_filters_allowed_tools(monkeypatch):
    """MinionCodeAgent.create should apply allowlist before readonly filtering."""

    create_calls = []

    class DummyAgent:
        def __init__(self):
            self.llm = "fake-llm"
            self.state = SimpleNamespace(history=[], metadata={})

    async def _fake_super_create(cls, **kwargs):
        create_calls.append(kwargs)
        return DummyAgent()

    monkeypatch.setattr(
        code_agent_module.CodeAgent,
        "create",
        classmethod(_fake_super_create),
    )

    await code_agent_module.MinionCodeAgent.create(
        name="Readonly Explore",
        llm="sonnet",
        allowed_tool_names=["file_read", "file_write", "web_fetch"],
        readonly_only=True,
    )

    assert [tool.name for tool in create_calls[0]["tools"]] == [
        "file_read",
        "web_fetch",
    ]


@pytest.mark.asyncio
async def test_user_input_tool_multi_question_form_uses_value_payload():
    """user_input should preserve choice values, not display labels."""

    class FakeAdapter:
        async def form(self, message, fields, title, submit_text):
            assert title == "Project Setup"
            assert message == "Fill in the values."
            assert submit_text == "Submit"
            assert fields[1]["options"][0]["label"] == "Python"
            assert fields[1]["options"][0]["value"] == "python"
            return {"name": "demo", "lang": "python"}

    tool = UserInputTool()
    state = SimpleNamespace(metadata={"output_adapter": FakeAdapter()})

    result = await tool.forward(
        questions_json='{"title":"Project Setup","message":"Fill in the values.","fields":[{"id":"name","label":"Project name","type":"text"},{"id":"lang","label":"Language","type":"choice","options":[{"label":"Python","value":"python"},{"label":"Go","value":"go"}],"default":"python"}]}',
        state=state,
    )

    assert '"lang": "python"' in result
