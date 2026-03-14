from minion_code.components.PromptInput import PromptInput
from minion_code.type_defs import InputMode


def test_prefix_triggered_bash_mode_exits_when_prefix_removed():
    prompt_input = PromptInput()
    mode_changes = []
    prompt_input.on_mode_change = mode_changes.append

    prompt_input._sync_mode_from_text("!")
    assert prompt_input.mode == InputMode.BASH
    assert prompt_input._prefix_triggered_mode == InputMode.BASH

    prompt_input._sync_mode_from_text("")
    assert prompt_input.mode == InputMode.PROMPT
    assert prompt_input._prefix_triggered_mode is None
    assert mode_changes == [InputMode.BASH, InputMode.PROMPT]


def test_manual_mode_is_not_reset_by_plain_text():
    prompt_input = PromptInput(mode=InputMode.BASH)
    mode_changes = []
    prompt_input.on_mode_change = mode_changes.append

    prompt_input._sync_mode_from_text("echo hi")
    assert prompt_input.mode == InputMode.BASH
    assert prompt_input._prefix_triggered_mode is None
    assert mode_changes == []


def test_watch_is_disabled_syncs_text_area_and_focuses_when_enabled(monkeypatch):
    prompt_input = PromptInput(is_disabled=True)

    class _FakeTextArea:
        def __init__(self):
            self.disabled = True
            self.focus_calls = 0

        def focus(self):
            self.focus_calls += 1

    fake_text_area = _FakeTextArea()

    def _fake_query_one(selector, expect_type=None):
        assert selector == "#main_input"
        return fake_text_area

    monkeypatch.setattr(prompt_input, "query_one", _fake_query_one)

    prompt_input.watch_is_disabled(False)

    assert fake_text_area.disabled is False
    assert fake_text_area.focus_calls == 1
