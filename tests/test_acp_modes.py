from __future__ import annotations

import asyncio
from types import SimpleNamespace

from minion.types.history import History

from minion_code.acp_server.agent import MinionACPAgent
from minion_code.acp_server.agent import ACPSession
from minion_code.acp_server.session_modes import build_session_mode_state
from minion_code.agents.code_agent import MinionCodeAgent


class _DummyPermissionStore:
    def __init__(self, cwd: str):
        self.cwd = cwd


class _DummyAgent:
    def __init__(self, prompt_name: str):
        self.prompt_name = prompt_name
        self.state = SimpleNamespace(history=History(), metadata={}, agent=self)
        self.conversation_history = []

    def get_conversation_history(self):
        return list(self.conversation_history)


def test_build_session_mode_state_exposes_default_and_plan():
    state = build_session_mode_state("default")

    assert state.currentModeId == "default"
    assert [mode.id for mode in state.availableModes] == [
        "default",
        "accept-edits",
        "plan",
        "dont-ask",
        "bypass-permissions",
    ]
    assert [mode.name for mode in state.availableModes] == [
        "Default",
        "Accept Edits",
        "Plan Mode",
        "Don't Ask",
        "Bypass Permissions",
    ]


def test_acp_session_switches_to_plan_mode_and_preserves_history(monkeypatch):
    create_calls = []

    async def _fake_create(cls, **kwargs):
        create_calls.append(kwargs)
        return _DummyAgent(prompt_name=kwargs["prompt_name"])

    monkeypatch.setattr(MinionCodeAgent, "create", classmethod(_fake_create))
    monkeypatch.setattr(
        "minion_code.acp_server.permissions.PermissionStore",
        _DummyPermissionStore,
    )
    monkeypatch.setattr("minion_code.acp_server.auth.get_credentials", lambda: None)

    async def _scenario():
        session = ACPSession(
            session_id="session-1",
            cwd="/tmp/project",
            client=None,
            mcp_servers=[],
        )
        await session.initialize()
        assert create_calls[0]["readonly_only"] is False
        assert create_calls[0]["prompt_name"] == "default"

        session.agent.state.history.append({"role": "user", "content": "keep history"})
        session.agent.state.metadata["custom"] = "value"
        session.agent.conversation_history.append(
            {"user_message": "hi", "agent_response": "hello"}
        )

        await session.set_mode("plan")

        assert session.current_mode_id == "plan"
        assert create_calls[1]["readonly_only"] is True
        assert create_calls[1]["prompt_name"] == "plan"
        assert session.agent.state.history.to_list() == [
            {"role": "user", "content": "keep history"}
        ]
        assert session.agent.state.metadata["custom"] == "value"
        assert session.agent.conversation_history == [
            {"user_message": "hi", "agent_response": "hello"}
        ]

    asyncio.run(_scenario())


def test_acp_agent_skip_permissions_changes_initial_mode():
    agent = MinionACPAgent(skip_permissions=True)
    assert agent.initial_mode_id == "dont-ask"


def test_acp_session_mode_policies(monkeypatch):
    create_calls = []
    hook_calls = []

    async def _fake_create(cls, **kwargs):
        create_calls.append(kwargs)
        return _DummyAgent(prompt_name=kwargs["prompt_name"])

    def _fake_create_acp_hooks(**kwargs):
        hook_calls.append(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(MinionCodeAgent, "create", classmethod(_fake_create))
    monkeypatch.setattr(
        "minion_code.acp_server.permissions.PermissionStore",
        _DummyPermissionStore,
    )
    monkeypatch.setattr("minion_code.acp_server.auth.get_credentials", lambda: None)
    monkeypatch.setattr("minion_code.acp_server.hooks.create_acp_hooks", _fake_create_acp_hooks)

    async def _scenario():
        session = ACPSession(
            session_id="session-2",
            cwd="/tmp/project",
            client=SimpleNamespace(),
            mcp_servers=[],
            mode_id="accept-edits",
        )
        await session.initialize()
        assert hook_calls[0]["request_permission"] is True
        assert hook_calls[0]["include_dangerous_check"] is True
        assert set(hook_calls[0]["auto_allow_tools"]) == {
            "file_write",
            "file_edit",
            "multi_edit",
            "todo_write",
        }

        await session.set_mode("dont-ask")
        assert hook_calls[1]["request_permission"] is False
        assert hook_calls[1]["include_dangerous_check"] is True
        assert tuple(hook_calls[1]["auto_allow_tools"]) == ()

        await session.set_mode("bypass-permissions")
        assert hook_calls[2]["request_permission"] is False
        assert hook_calls[2]["include_dangerous_check"] is False
        assert tuple(hook_calls[2]["auto_allow_tools"]) == ()

    asyncio.run(_scenario())
