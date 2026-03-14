"""CLI tests for MCP config forwarding."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from minion_code import cli as cli_module


def test_run_tui_repl_forwards_mcp_config(monkeypatch, tmp_path: Path):
    """Default TUI entrypoint should forward MCP config to the REPL runner."""
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)

    monkeypatch.setitem(
        sys.modules,
        "minion_code.screens.REPL",
        SimpleNamespace(run=fake_run),
    )

    config_path = tmp_path / "mcp.json"
    cli_module.run_tui_repl(
        debug=True,
        verbose=True,
        initial_prompt="hi",
        resume_session_id="session-1",
        continue_last=True,
        model="demo-model",
        mcp_config=config_path,
        dangerously_skip_permissions=True,
    )

    assert captured["mcp_config"] == config_path
    assert captured["dangerously_skip_permissions"] is True
    assert captured["initial_prompt"] == "hi"


def test_run_console_cli_forwards_skip_permissions(monkeypatch):
    """Console entrypoint should forward bypass-permissions to InterruptibleCLI."""
    captured = {}

    class FakeCLI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def run(self):
            return None

    monkeypatch.setattr("minion_code.cli_simple.InterruptibleCLI", FakeCLI)

    cli_module.run_console_cli(
        verbose=True,
        dangerously_skip_permissions=True,
        initial_prompt="hi",
    )

    assert captured["auto_accept"] is True
    assert captured["initial_prompt"] == "hi"
