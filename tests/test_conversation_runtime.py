"""Tests for buffered prompt and system reminder runtime state."""

from __future__ import annotations

from minion_code.utils.conversation_runtime import ConversationRuntimeState


def test_prompt_queue_preserves_order():
    """Buffered prompts should be drained FIFO."""
    runtime = ConversationRuntimeState()

    assert runtime.queue_prompt("first") == 1
    assert runtime.queue_prompt("second") == 2

    assert runtime.pop_prompt().content == "first"
    assert runtime.pop_prompt().content == "second"
    assert runtime.pop_prompt() is None


def test_clear_pending_prompts_returns_dropped_count():
    """Interrupt handlers should be able to discard buffered prompts explicitly."""
    runtime = ConversationRuntimeState()
    runtime.queue_prompt("first")
    runtime.queue_prompt("second")

    assert runtime.clear_pending_prompts() == 2
    assert runtime.pop_prompt() is None


def test_one_shot_reminder_is_consumed_once():
    """Non-persistent reminders should only be injected into the next turn."""
    runtime = ConversationRuntimeState()
    runtime.enqueue_system_reminder("todo_nag", "Use todos.", "todos")

    first = runtime.prepare_user_message("hello")
    second = runtime.prepare_user_message("hello again")

    assert "Use todos." in first
    assert "Use todos." not in second


def test_persistent_file_reminder_repeats_until_cleared(monkeypatch):
    """File freshness reminders should keep appearing until the file is re-read."""
    runtime = ConversationRuntimeState()

    monkeypatch.setattr(
        "minion_code.utils.conversation_runtime.file_freshness_service.get_session_files",
        lambda: ["/tmp/demo.py"],
    )
    monkeypatch.setattr(
        "minion_code.utils.conversation_runtime.file_freshness_service.generate_file_modification_reminder",
        lambda _path: "Note: /tmp/demo.py changed outside this session.",
    )

    first = runtime.prepare_user_message("one")
    second = runtime.prepare_user_message("two")

    assert "demo.py" in first
    assert "demo.py" in second
    assert first.count("demo.py") == 1
    assert second.count("demo.py") == 1


def test_persistent_file_reminder_clears_after_refresh(monkeypatch):
    """File reminders should disappear once the freshness warning is gone."""
    runtime = ConversationRuntimeState()
    reminder_state = {"active": True}

    monkeypatch.setattr(
        "minion_code.utils.conversation_runtime.file_freshness_service.get_session_files",
        lambda: ["/tmp/demo.py"],
    )

    def fake_reminder(_path: str):
        if reminder_state["active"]:
            return "Note: /tmp/demo.py changed outside this session."
        return None

    monkeypatch.setattr(
        "minion_code.utils.conversation_runtime.file_freshness_service.generate_file_modification_reminder",
        fake_reminder,
    )

    first = runtime.prepare_user_message("before reread")
    reminder_state["active"] = False
    second = runtime.prepare_user_message("after reread")

    assert "demo.py" in first
    assert "demo.py" not in second
