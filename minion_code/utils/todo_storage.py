"""Todo storage utilities for managing todo items."""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TodoPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TodoItem:
    id: str
    content: str
    status: TodoStatus
    priority: TodoPriority
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        return cls(
            id=data["id"],
            content=data["content"],
            status=TodoStatus(data["status"]),
            priority=TodoPriority(data["priority"])
        )


class TodoStorage:
    def __init__(self, storage_dir: str = ".minion_workspace"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def _get_file_path(self, agent_id: Optional[str] = None) -> str:
        filename = f"todos_{agent_id}.json" if agent_id else "todos_default.json"
        return os.path.join(self.storage_dir, filename)
    
    def get_todos(self, agent_id: Optional[str] = None) -> List[TodoItem]:
        """Get all todos for a specific agent or default."""
        file_path = self._get_file_path(agent_id)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [TodoItem.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []
    
    def set_todos(self, todos: List[TodoItem], agent_id: Optional[str] = None) -> None:
        """Set todos for a specific agent or default."""
        file_path = self._get_file_path(agent_id)
        
        data = [todo.to_dict() for todo in todos]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_todo(self, todo: TodoItem, agent_id: Optional[str] = None) -> None:
        """Add a new todo."""
        todos = self.get_todos(agent_id)
        todos.append(todo)
        self.set_todos(todos, agent_id)
    
    def update_todo(self, todo_id: str, updates: Dict[str, Any], agent_id: Optional[str] = None) -> bool:
        """Update a specific todo. Returns True if found and updated."""
        todos = self.get_todos(agent_id)
        
        for todo in todos:
            if todo.id == todo_id:
                if 'content' in updates:
                    todo.content = updates['content']
                if 'status' in updates:
                    todo.status = TodoStatus(updates['status'])
                if 'priority' in updates:
                    todo.priority = TodoPriority(updates['priority'])
                
                self.set_todos(todos, agent_id)
                return True
        
        return False
    
    def remove_todo(self, todo_id: str, agent_id: Optional[str] = None) -> bool:
        """Remove a todo by ID. Returns True if found and removed."""
        todos = self.get_todos(agent_id)
        original_length = len(todos)
        
        todos = [todo for todo in todos if todo.id != todo_id]
        
        if len(todos) < original_length:
            self.set_todos(todos, agent_id)
            return True
        
        return False
    
    def clear_todos(self, agent_id: Optional[str] = None) -> None:
        """Clear all todos for a specific agent."""
        self.set_todos([], agent_id)


# Global storage instance
_storage = TodoStorage()

def get_todos(agent_id: Optional[str] = None) -> List[TodoItem]:
    """Get todos from global storage."""
    return _storage.get_todos(agent_id)

def set_todos(todos: List[TodoItem], agent_id: Optional[str] = None) -> None:
    """Set todos in global storage."""
    _storage.set_todos(todos, agent_id)

def add_todo(todo: TodoItem, agent_id: Optional[str] = None) -> None:
    """Add todo to global storage."""
    _storage.add_todo(todo, agent_id)

def update_todo(todo_id: str, updates: Dict[str, Any], agent_id: Optional[str] = None) -> bool:
    """Update todo in global storage."""
    return _storage.update_todo(todo_id, updates, agent_id)

def remove_todo(todo_id: str, agent_id: Optional[str] = None) -> bool:
    """Remove todo from global storage."""
    return _storage.remove_todo(todo_id, agent_id)

def clear_todos(agent_id: Optional[str] = None) -> None:
    """Clear all todos in global storage."""
    _storage.clear_todos(agent_id)