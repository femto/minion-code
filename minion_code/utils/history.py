"""History management utilities for minion-code.

This module provides command history functionality similar to the TypeScript
history.ts file, adapted for Python and the minion-code project structure.
"""

from typing import List
from .config import get_current_project_config, save_current_project_config

MAX_HISTORY_ITEMS = 100


def get_history() -> List[str]:
    """Get command history for the current project.

    Returns:
        List of command history strings, with most recent first.
    """
    project_config = get_current_project_config()
    return project_config.history or []


def add_to_history(command: str) -> None:
    """Add a command to the history.

    Args:
        command: The command string to add to history.

    Note:
        - Commands are added to the beginning of the history list
        - Duplicate consecutive commands are not added
        - History is limited to MAX_HISTORY_ITEMS entries
    """
    if not command or not command.strip():
        return

    command = command.strip()
    project_config = get_current_project_config()
    history = project_config.history or []

    # Don't add if it's the same as the most recent command
    if history and history[0] == command:
        return

    # Add to beginning and limit to MAX_HISTORY_ITEMS
    history.insert(0, command)
    project_config.history = history[:MAX_HISTORY_ITEMS]

    save_current_project_config(project_config)


def clear_history() -> None:
    """Clear all command history for the current project."""
    project_config = get_current_project_config()
    project_config.history = []
    save_current_project_config(project_config)


def remove_from_history(command: str) -> bool:
    """Remove a specific command from history.

    Args:
        command: The command string to remove from history.

    Returns:
        True if the command was found and removed, False otherwise.
    """
    if not command or not command.strip():
        return False

    command = command.strip()
    project_config = get_current_project_config()
    history = project_config.history or []

    if command in history:
        history.remove(command)
        project_config.history = history
        save_current_project_config(project_config)
        return True

    return False


def get_history_item(index: int) -> str:
    """Get a specific history item by index.

    Args:
        index: The index of the history item (0 is most recent).

    Returns:
        The command string at the specified index, or empty string if not found.
    """
    history = get_history()
    if 0 <= index < len(history):
        return history[index]
    return ""


def search_history(query: str) -> List[str]:
    """Search history for commands containing the query string.

    Args:
        query: The search query string.

    Returns:
        List of matching commands, with most recent first.
    """
    if not query or not query.strip():
        return []

    query = query.strip().lower()
    history = get_history()

    return [cmd for cmd in history if query in cmd.lower()]
