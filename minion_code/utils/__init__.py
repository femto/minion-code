"""Utility exports with lazy loading to avoid import-time filesystem writes."""

from importlib import import_module


_EXPORTS = {
    # Todo file utilities
    "get_todo_file_path": ".todo_file_utils",
    "get_default_storage_dir": ".todo_file_utils",
    "ensure_storage_dir_exists": ".todo_file_utils",
    "list_todo_files": ".todo_file_utils",
    "extract_agent_id_from_todo_file": ".todo_file_utils",
    "is_todo_file": ".todo_file_utils",
    # Todo storage
    "TodoItem": ".todo_storage",
    "TodoStatus": ".todo_storage",
    "TodoPriority": ".todo_storage",
    "TodoStorage": ".todo_storage",
    "get_todos": ".todo_storage",
    "set_todos": ".todo_storage",
    "add_todo": ".todo_storage",
    "update_todo": ".todo_storage",
    "remove_todo": ".todo_storage",
    "clear_todos": ".todo_storage",
    # Output truncator
    "truncate_output": ".output_truncator",
    "check_file_size_before_read": ".output_truncator",
    "check_mcp_output": ".output_truncator",
    "save_large_output": ".output_truncator",
    "cleanup_cache": ".output_truncator",
    "OutputTooLargeError": ".output_truncator",
    "MCPContentTooLargeError": ".output_truncator",
    "FileTooLargeError": ".output_truncator",
    "MAX_OUTPUT_SIZE": ".output_truncator",
    "MAX_FILE_SIZE": ".output_truncator",
    "MAX_TOKEN_LIMIT": ".output_truncator",
    "CACHE_DIR": ".output_truncator",
}


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value

__all__ = [
    # Todo file utilities
    "get_todo_file_path",
    "get_default_storage_dir",
    "ensure_storage_dir_exists",
    "list_todo_files",
    "extract_agent_id_from_todo_file",
    "is_todo_file",
    # Todo storage
    "TodoItem",
    "TodoStatus",
    "TodoPriority",
    "TodoStorage",
    "get_todos",
    "set_todos",
    "add_todo",
    "update_todo",
    "remove_todo",
    "clear_todos",
    # Output truncator
    "truncate_output",
    "check_file_size_before_read",
    "check_mcp_output",
    "save_large_output",
    "cleanup_cache",
    "OutputTooLargeError",
    "MCPContentTooLargeError",
    "FileTooLargeError",
    "MAX_OUTPUT_SIZE",
    "MAX_FILE_SIZE",
    "MAX_TOKEN_LIMIT",
    "CACHE_DIR",
]
