"""Todo Write Tool for managing todo items."""

import uuid
import json
from typing import List, Dict, Any, Optional
from minion.tools import BaseTool
from minion.types import AgentState

from ..utils.todo_storage import (
    TodoItem, TodoStatus, TodoPriority, 
    get_todos, set_todos
)





class ValidationResult:
    """Result of todo validation."""
    def __init__(self, result: bool, error_code: int = 0, message: str = "", meta: Dict[str, Any] = None):
        self.result = result
        self.error_code = error_code
        self.message = message
        self.meta = meta or {}


def validate_todos(todos: List[TodoItem]) -> ValidationResult:
    """Validate a list of todos."""
    # Check for duplicate IDs
    ids = [todo.id for todo in todos]
    unique_ids = set(ids)
    if len(ids) != len(unique_ids):
        duplicate_ids = [id for id in ids if ids.count(id) > 1]
        return ValidationResult(
            result=False,
            error_code=1,
            message="Duplicate todo IDs found",
            meta={"duplicate_ids": list(set(duplicate_ids))}
        )
    
    # Check for multiple in_progress tasks
    in_progress_tasks = [todo for todo in todos if todo.status == TodoStatus.IN_PROGRESS]
    if len(in_progress_tasks) > 1:
        return ValidationResult(
            result=False,
            error_code=2,
            message="Only one task can be in_progress at a time",
            meta={"in_progress_task_ids": [t.id for t in in_progress_tasks]}
        )
    
    # Validate each todo
    for todo in todos:
        if not todo.content.strip():
            return ValidationResult(
                result=False,
                error_code=3,
                message=f'Todo with ID "{todo.id}" has empty content',
                meta={"todo_id": todo.id}
            )
    
    return ValidationResult(result=True)


def generate_todo_summary(todos: List[TodoItem]) -> str:
    """Generate a summary of todos."""
    stats = {
        'total': len(todos),
        'pending': len([t for t in todos if t.status == TodoStatus.PENDING]),
        'in_progress': len([t for t in todos if t.status == TodoStatus.IN_PROGRESS]),
        'completed': len([t for t in todos if t.status == TodoStatus.COMPLETED])
    }
    
    summary = f"Updated {stats['total']} todo(s)"
    if stats['total'] > 0:
        summary += f" ({stats['pending']} pending, {stats['in_progress']} in progress, {stats['completed']} completed)"
    summary += ". Continue tracking your progress with the todo list."
    
    return summary


def format_todos_display(todos: List[TodoItem]) -> str:
    """Format todos for display."""
    if not todos:
        return "No todos currently"
    
    # Sort: [completed, in_progress, pending]
    order = [TodoStatus.COMPLETED, TodoStatus.IN_PROGRESS, TodoStatus.PENDING]
    sorted_todos = sorted(todos, key=lambda t: (order.index(t.status), t.content))
    
    # Find the next pending task
    next_pending_index = next(
        (i for i, todo in enumerate(sorted_todos) if todo.status == TodoStatus.PENDING),
        -1
    )
    
    lines = []
    for i, todo in enumerate(sorted_todos):
        # Determine checkbox and formatting
        if todo.status == TodoStatus.COMPLETED:
            checkbox = "☒"
            prefix = "  ⎿ "
            content = f"~~{todo.content}~~"  # Strikethrough for completed
        elif todo.status == TodoStatus.IN_PROGRESS:
            checkbox = "☐"
            prefix = "  ⎿ "
            content = f"**{todo.content}**"  # Bold for in progress
        else:  # pending
            checkbox = "☐"
            prefix = "  ⎿ "
            if i == next_pending_index:
                content = f"**{todo.content}**"  # Bold for next pending
            else:
                content = todo.content
        
        lines.append(f"{prefix}{checkbox} {content}")
    
    return "\n".join(lines)


class TodoWriteTool(BaseTool):
    """Tool for writing and managing todo items."""
    
    name = "todo_write"
    description = "Creates and manages todo items for task tracking and progress management in the current session."
    readonly = False  # Writing tool, modifies system state
    needs_state = True  # Tool needs agent state
    inputs = {
        "todos_json": {
            "type": "string", 
            "description": "JSON string containing array of todo items with id, content, status, and priority fields"
        },
    }
    output_type = "string"
    
    def _get_agent_id(self, state: AgentState) -> str:
        """Get agent ID from agent state."""
        # Try to get from metadata
        # if 'agent_id' in state.metadata:
        #     return state.metadata['agent_id']
        #
        # # Try to get from input if available
        # if state.input and hasattr(state.input, 'mind_id'):
        #     return state.input.mind_id
        #
        # # Generate a unique ID based on task or use default
        # if state.task:
        #     # Use a hash of the task as agent ID
        #      import hashlib
        #      return hashlib.md5(state.task.encode()).hexdigest()[:8]
        
        # Default fallback
        return state.agent.agent_id
    
    def forward(self, todos_json: str, *, state: AgentState) -> str:
        """Execute the todo write operation."""
        try:
            # Get agent ID from agent state
            agent_id = self._get_agent_id(state)
            
            # Parse JSON input
            try:
                todos_data = json.loads(todos_json)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON format - {str(e)}"
            
            if not isinstance(todos_data, list):
                return "Error: todos_json must be an array of todo items"
            
            # Convert to TodoItem objects and validate
            todo_items = []
            for i, todo_data in enumerate(todos_data):
                if not isinstance(todo_data, dict):
                    return f"Error: Todo item {i} must be an object"
                
                # Validate required fields
                required_fields = ['id', 'content', 'status', 'priority']
                for field in required_fields:
                    if field not in todo_data:
                        return f"Error: Todo item {i} missing required field '{field}'"
                
                # Validate status
                if todo_data['status'] not in ['pending', 'in_progress', 'completed']:
                    return f"Error: Invalid status '{todo_data['status']}' in todo item {i}"
                
                # Validate priority
                if todo_data['priority'] not in ['high', 'medium', 'low']:
                    return f"Error: Invalid priority '{todo_data['priority']}' in todo item {i}"
                
                # Validate content
                if not todo_data['content'].strip():
                    return f"Error: Todo item {i} has empty content"
                
                todo_item = TodoItem(
                    id=todo_data['id'],
                    content=todo_data['content'],
                    status=TodoStatus(todo_data['status']),
                    priority=TodoPriority(todo_data['priority'])
                )
                todo_items.append(todo_item)
            
            # Validate todos
            validation = validate_todos(todo_items)
            if not validation.result:
                return f"Validation Error: {validation.message}"
            
            # Get previous todos for comparison
            previous_todos = get_todos(agent_id)
            
            # Update todos in storage
            set_todos(todo_items, agent_id)
            
            # Update agent metadata with todo info
            state.metadata['todo_count'] = len(todo_items)
            state.metadata['last_todo_update'] = json.dumps({
                'total': len(todo_items),
                'pending': len([t for t in todo_items if t.status == TodoStatus.PENDING]),
                'in_progress': len([t for t in todo_items if t.status == TodoStatus.IN_PROGRESS]),
                'completed': len([t for t in todo_items if t.status == TodoStatus.COMPLETED])
            })
            
            # Reset iteration counter since todo tool was used
            state.metadata["iteration_without_todos"] = 0
            
            # Generate summary
            summary = generate_todo_summary(todo_items)
            
            # Format display
            display = format_todos_display(todo_items)
            
            result = f"{summary}\n\n{display}"
            return result
            
        except Exception as e:
            return f"Error updating todos: {str(e)}"