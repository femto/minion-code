from __future__ import annotations

import asyncio

from minion_code.commands.mcp_command import MCPCommand


class _DummyOutput:
    def __init__(self):
        self.tables = []
        self.panels = []
        self.texts = []

    def table(self, headers, rows, title=""):
        self.tables.append((headers, rows, title))

    def panel(self, content, title="", border_style="blue"):
        self.panels.append((content, title, border_style))

    def text(self, content, style=""):
        self.texts.append((content, style))

    def info(self, content):
        self.text(content)


class _DummyHost:
    def __init__(self):
        self.reload_calls = []
        self.status = {
            "deepwiki": {
                "status": "timed_out",
                "tool_count": 0,
                "transport": "sse",
                "url": "https://mcp.deepwiki.com/sse",
                "command": "",
                "args": [],
                "error": "MCP startup timed out after 15.0s",
                "last_duration_ms": 15000,
            }
        }

    def get_mcp_status(self):
        return self.status

    def get_mcp_config_path(self):
        return "/tmp/.mcp.json"

    async def reload_mcp(self, server_name=None):
        self.reload_calls.append(server_name)
        self.status["deepwiki"]["status"] = "connected"
        self.status["deepwiki"]["tool_count"] = 3
        self.status["deepwiki"]["error"] = None
        self.status["deepwiki"]["last_duration_ms"] = 42
        return self.status


def test_mcp_command_renders_status_table():
    output = _DummyOutput()
    host = _DummyHost()
    command = MCPCommand(output, agent=None, host=host)

    asyncio.run(command.execute(""))

    assert len(output.tables) == 1
    headers, rows, title = output.tables[0]
    assert headers == ["Server", "Status", "Tools", "Transport", "Last Load", "Details"]
    assert rows[0][0] == "deepwiki"
    assert rows[0][1] == "timed_out"
    assert "MCP Status" in title


def test_mcp_command_retries_single_server():
    output = _DummyOutput()
    host = _DummyHost()
    command = MCPCommand(output, agent=None, host=host)

    asyncio.run(command.execute("retry deepwiki"))

    assert host.reload_calls == ["deepwiki"]
    assert len(output.tables) == 1
    assert output.tables[0][1][0][1] == "connected"
