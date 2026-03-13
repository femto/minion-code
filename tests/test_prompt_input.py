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
