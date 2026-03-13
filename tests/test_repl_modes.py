from __future__ import annotations

import pytest

from minion_code.screens.REPL import REPL
from minion_code.type_defs import InputMode, Message, MessageContent, MessageType


@pytest.mark.asyncio
async def test_bash_mode_runs_through_repl_pipeline(monkeypatch):
    repl = REPL()
    saved_messages = []

    async def fake_execute(command: str) -> str:
        assert command == "ls"
        return "file-a\nfile-b"

    monkeypatch.setattr(repl, "execute_bash_command", fake_execute)
    monkeypatch.setattr(repl, "_refresh_messages", lambda: None)
    monkeypatch.setattr(
        repl,
        "_save_message_to_session",
        lambda role, content: saved_messages.append((role, content)),
    )

    await repl._process_special_mode_batch(
        [
            Message(
                type=MessageType.USER,
                message=MessageContent("!ls"),
                options={"mode": InputMode.BASH.value},
            )
        ],
        InputMode.BASH,
    )

    assert repl.messages[-1].message.content == "file-a\nfile-b"
    assert saved_messages[-1] == ("assistant", "file-a\nfile-b")


@pytest.mark.asyncio
async def test_memory_mode_direct_note_writes_agents_md(tmp_path, monkeypatch):
    repl = REPL()
    saved_messages = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(repl, "_refresh_messages", lambda: None)
    monkeypatch.setattr(
        repl,
        "_save_message_to_session",
        lambda role, content: saved_messages.append((role, content)),
    )

    await repl._process_special_mode_batch(
        [
            Message(
                type=MessageType.USER,
                message=MessageContent("#sth to remember"),
                options={"mode": InputMode.MEMORY.value},
            )
        ],
        InputMode.MEMORY,
    )

    agents_md = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "sth to remember" in agents_md
    assert repl.messages[-1].message.content == "✅ Memory added to AGENTS.md"
    assert saved_messages[-1] == ("assistant", "✅ Memory added to AGENTS.md")
