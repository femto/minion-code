"""Utilities for todo file path management."""

import os
from typing import Optional


def get_todo_file_path(agent_id: Optional[str] = None, storage_dir: str = ".minion") -> str:
    """
    Get the file path for todo storage for a specific agent.
    
    Args:
        agent_id: Agent identifier. If None, uses default.
        storage_dir: Directory where todo files are stored.
        
    Returns:
        Full path to the todo file for the agent.
    """
    # Ensure storage directory exists
    os.makedirs(storage_dir, exist_ok=True)
    
    # Generate filename based on agent_id
    if agent_id:
        filename = f"todos_{agent_id}.json"
    else:
        filename = "todos_default.json"
    
    return os.path.join(storage_dir, filename)


def get_default_storage_dir() -> str:
    """Get the default storage directory for todo files."""
    return ".minion"


def ensure_storage_dir_exists(storage_dir: Optional[str] = None) -> str:
    """
    Ensure the storage directory exists and return its path.
    
    Args:
        storage_dir: Directory path. If None, uses default.
        
    Returns:
        The storage directory path.
    """
    if storage_dir is None:
        storage_dir = get_default_storage_dir()
    
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir


def list_todo_files(storage_dir: Optional[str] = None) -> list[str]:
    """
    List all todo files in the storage directory.
    
    Args:
        storage_dir: Directory to search. If None, uses default.
        
    Returns:
        List of todo file paths.
    """
    if storage_dir is None:
        storage_dir = get_default_storage_dir()
    
    if not os.path.exists(storage_dir):
        return []
    
    todo_files = []
    for filename in os.listdir(storage_dir):
        if filename.startswith("todos_") and filename.endswith(".json"):
            todo_files.append(os.path.join(storage_dir, filename))
    
    return todo_files


def extract_agent_id_from_todo_file(file_path: str) -> Optional[str]:
    """
    Extract agent ID from a todo file path.
    
    Args:
        file_path: Path to the todo file.
        
    Returns:
        Agent ID if found, None if it's the default file.
    """
    filename = os.path.basename(file_path)
    
    if filename == "todos_default.json":
        return None
    
    if filename.startswith("todos_") and filename.endswith(".json"):
        # Extract agent_id from "todos_{agent_id}.json"
        agent_id = filename[6:-5]  # Remove "todos_" prefix and ".json" suffix
        return agent_id if agent_id else None
    
    return None


def is_todo_file(file_path: str) -> bool:
    """
    Check if a file path is a todo file.
    
    Args:
        file_path: Path to check.
        
    Returns:
        True if it's a todo file, False otherwise.
    """
    filename = os.path.basename(file_path)
    return (filename.startswith("todos_") and filename.endswith(".json")) or filename == "todos_default.json"