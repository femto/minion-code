from __future__ import annotations

import asyncio
from types import SimpleNamespace

from minion.types.history import History

from minion_code.commands.mode_command import ModeCommand
from minion_code.session_mode_controller import LocalSessionModeController


class _DummyAgent:
    def __init__(self, tool_names=None):
        self.tools = [SimpleNamespace(name=name) for name in (tool_names or [])]
        self.state = SimpleNamespace(history=History(), metadata={}, agent=self)
        self.conversation_history = []

    def get_conversation_history(self):
        return list(self.conversation_history)


class _DummyOutput:
    def __init__(self):
        self.choice_calls = []
        self.successes = []
        self.infos = []
        self.texts = []
        self.errors = []
        self.tables = []
        self._choice_result = 0

    async def choice(self, message, choices, title="Select", default_index=0):
        self.choice_calls.append((message, choices, title, default_index))
        return self._choice_result

    def success(self, content):
        self.successes.append(content)

    def info(self, content):
        self.infos.append(content)

    def text(self, content, style=""):
        self.texts.append((content, style))

    def error(self, content):
        self.errors.append(content)

    def table(self, headers, rows, title=""):
        self.tables.append((headers, rows, title))

    def panel(self, content, title="", border_style="blue"):
        self.texts.append((content, border_style))


def test_local_session_mode_controller_preserves_history():
    build_calls = []

    async def _build_agent(mode_spec):
        build_calls.append(mode_spec.id)
        return _DummyAgent(tool_names=[mode_spec.id])

    controller = LocalSessionModeController("default", _build_agent)

    async def _scenario():
        agent = await controller.initialize()
        agent.state.history.append({"role": "user", "content": "keep"})
        agent.conversation_history.append({"user_message": "u", "agent_response": "a"})
        agent.state.metadata["custom"] = "value"

        await controller.set_mode("plan")

        assert build_calls == ["default", "plan"]
        assert controller.agent.state.history.to_list() == [
            {"role": "user", "content": "keep"}
        ]
        assert controller.agent.conversation_history == [
            {"user_message": "u", "agent_response": "a"}
        ]
        assert controller.agent.state.metadata["custom"] == "value"
        assert controller.agent.state.metadata["session_mode_id"] == "plan"
        assert controller.agent.state.metadata["mode_controller"] is controller

    asyncio.run(_scenario())


def test_mode_command_switches_mode_via_choice():
    output = _DummyOutput()

    async def _build_agent(mode_spec):
        return _DummyAgent(tool_names=[mode_spec.id])

    controller = LocalSessionModeController("default", _build_agent)

    async def _scenario():
        agent = await controller.initialize()
        output._choice_result = 2  # Plan Mode
        command = ModeCommand(output, agent)
        await command.execute("")

        assert controller.current_mode_id == "plan"
        assert output.choice_calls
        assert output.successes == ["Switched to Plan Mode."]
        assert "Tools available: 1" in output.texts[-1][0]

    asyncio.run(_scenario())


def test_local_session_mode_controller_rebuild_current_preserves_history():
    build_calls = []

    async def _build_agent(mode_spec):
        build_calls.append(mode_spec.id)
        return _DummyAgent(tool_names=[mode_spec.id, f"build-{len(build_calls)}"])

    controller = LocalSessionModeController("default", _build_agent)

    async def _scenario():
        agent = await controller.initialize()
        agent.state.history.append({"role": "user", "content": "keep"})
        agent.conversation_history.append({"user_message": "u", "agent_response": "a"})
        agent.state.metadata["custom"] = "value"

        rebuilt = await controller.rebuild_current()

        assert build_calls == ["default", "default"]
        assert rebuilt.state.history.to_list() == [{"role": "user", "content": "keep"}]
        assert rebuilt.conversation_history == [
            {"user_message": "u", "agent_response": "a"}
        ]
        assert rebuilt.state.metadata["custom"] == "value"
        assert rebuilt.state.metadata["session_mode_id"] == "default"

    asyncio.run(_scenario())
