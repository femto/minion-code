"""Tests for MCP config loading and large-output fallback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import minion_code.utils.mcp_loader as mcp_loader_module
from minion_code.utils.mcp_loader import CachedMCPTool, MCPToolsLoader, find_mcp_config
from minion_code.utils.output_truncator import MAX_TOKEN_LIMIT


def test_find_mcp_config_prefers_project_then_minion_user_config(
    tmp_path: Path, monkeypatch
):
    """Project-local config should win over user-scoped minion config."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))

    user_config = home / ".minion.json"
    user_config.write_text("{}", encoding="utf-8")

    project_config = project / ".mcp.json"
    project_config.write_text("{}", encoding="utf-8")

    assert find_mcp_config(project_dir=project) == project_config

    project_config.unlink()
    assert find_mcp_config(project_dir=project) == user_config


def test_loader_merges_global_and_project_servers_from_minion_json(tmp_path: Path):
    """~/.minion.json should merge global and closest project servers."""
    project_root = tmp_path / "project"
    nested_dir = project_root / "src"
    nested_dir.mkdir(parents=True)
    config_path = tmp_path / ".minion.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "global": {"command": "uvx", "args": ["global-server"]},
                    "override": {"command": "uvx", "args": ["global-override"]},
                },
                "projects": {
                    str(project_root): {
                        "mcpServers": {
                            "project": {
                                "command": "uvx",
                                "args": ["project-server"],
                            },
                            "override": {
                                "command": "uvx",
                                "args": ["project-override"],
                            },
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    loader = MCPToolsLoader(
        config_path=config_path,
        auto_discover=False,
        project_dir=nested_dir,
    )
    servers = loader.load_config()

    assert set(servers) == {"global", "project", "override"}
    assert servers["global"].args == ["global-server"]
    assert servers["project"].args == ["project-server"]
    assert servers["override"].args == ["project-override"]


def test_loader_parses_stdio_sse_and_http_servers(tmp_path: Path):
    """Loader should accept Claude-style stdio and remote transport entries."""
    config_path = tmp_path / ".mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "stdio-server": {
                        "command": "uvx",
                        "args": ["stdio-server"],
                        "env": {"TOKEN": 123},
                    },
                    "sse-server": {
                        "type": "http",
                        "url": "https://example.com/sse",
                    },
                    "http-server": {
                        "type": "http",
                        "url": "https://example.com/mcp",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    loader = MCPToolsLoader(config_path=config_path, auto_discover=False)
    servers = loader.load_config()

    assert servers["stdio-server"].transport == "stdio"
    assert servers["stdio-server"].env == {"TOKEN": "123"}
    assert servers["sse-server"].transport == "sse"
    assert servers["sse-server"].url == "https://example.com/sse"
    assert servers["http-server"].transport == "http"
    assert servers["http-server"].url == "https://example.com/mcp"


@pytest.mark.asyncio
async def test_loader_skips_cancelled_mcp_server(monkeypatch, tmp_path: Path):
    """A broken MCP server setup should be skipped instead of aborting all loading."""
    config_path = tmp_path / ".mcp.json"
    config_path.write_text(
        json.dumps(
            {"mcpServers": {"broken": {"type": "http", "url": "https://example.com/sse"}}}
        ),
        encoding="utf-8",
    )

    async def _fake_create(**_kwargs):
        raise asyncio.CancelledError("setup failed")

    monkeypatch.setattr(mcp_loader_module, "MCP_AVAILABLE", True)
    monkeypatch.setattr(
        mcp_loader_module,
        "MCPToolset",
        type("FakeToolset", (), {"create": staticmethod(_fake_create)}),
    )

    loader = MCPToolsLoader(config_path=config_path, auto_discover=False)
    loader.load_config()
    tools = await loader.load_all_tools()

    assert tools == []
    assert loader.get_server_info()["broken"]["status"] == "failed"


@pytest.mark.asyncio
async def test_loader_marks_timeout_without_blocking_other_servers(
    monkeypatch, tmp_path: Path
):
    """A slow MCP server should time out and not block the rest of startup."""
    config_path = tmp_path / ".mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "slow": {
                        "command": "uvx",
                        "args": ["slow-server"],
                        "timeout": 0.01,
                    },
                    "fast": {
                        "command": "uvx",
                        "args": ["fast-server"],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    class _FakeTool:
        def __init__(self, name: str):
            self.name = name
            self.tool_name = name
            self.description = name
            self.inputs = {}
            self.parameters = {}

        async def forward(self, *_args, **_kwargs):
            return self.name

    class _FakeToolset:
        def __init__(self, name: str):
            self.name = name
            self.tools = [_FakeTool(f"{name}-tool")]

        async def close(self):
            return None

    async def _fake_create(connection_params, name, structured_output):
        del connection_params, structured_output
        if name == "slow":
            await asyncio.sleep(0.05)
        return _FakeToolset(name)

    monkeypatch.setattr(mcp_loader_module, "MCP_AVAILABLE", True)
    monkeypatch.setattr(
        mcp_loader_module,
        "MCPToolset",
        type("FakeToolsetFactory", (), {"create": staticmethod(_fake_create)}),
    )

    loader = MCPToolsLoader(config_path=config_path, auto_discover=False)
    loader.load_config()
    tools = await loader.load_all_tools()
    info = loader.get_server_info()

    assert len(tools) == 1
    assert tools[0].name == "fast-tool"
    assert info["slow"]["status"] == "timed_out"
    assert "timed out" in info["slow"]["error"]
    assert info["fast"]["status"] == "connected"
    assert info["fast"]["tool_count"] == 1


@pytest.mark.asyncio
async def test_cached_mcp_tool_saves_large_outputs(tmp_path: Path, monkeypatch):
    """Oversized MCP tool results should be cached instead of surfacing as raw errors."""

    class FakeTool:
        name = "demo_tool"
        tool_name = "demo_tool"
        description = "demo"
        inputs = {}
        parameters = {}
        __name__ = "demo_tool"
        __doc__ = "demo"
        __input_schema__ = {"type": "object"}

        async def forward(self, *_args, **_kwargs):
            return "x" * ((MAX_TOKEN_LIMIT + 1) * 4)

    cached_path = tmp_path / "cached-output.txt"
    monkeypatch.setattr(
        "minion_code.utils.mcp_loader.save_large_output",
        lambda content, tool_name: str(cached_path),
    )

    tool = CachedMCPTool(FakeTool(), server_name="demo-server")
    result = await tool.forward()

    assert "MCP tool output too large to inline" in result
    assert str(cached_path) in result
    assert "Use file_read with offset/limit" in result


@pytest.mark.asyncio
async def test_cached_mcp_tool_preserves_small_outputs():
    """Small MCP outputs should pass through unchanged."""

    class FakeTool:
        name = "demo_tool"
        tool_name = "demo_tool"
        description = "demo"
        inputs = {}
        parameters = {}
        __name__ = "demo_tool"
        __doc__ = "demo"
        __input_schema__ = {"type": "object"}

        async def forward(self, *_args, **_kwargs):
            return {"ok": True}

    tool = CachedMCPTool(FakeTool(), server_name="demo-server")
    assert await tool.forward() == {"ok": True}
