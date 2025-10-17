"""Todo Read Tool for viewing current todo items."""

from typing import Optional
from minion.tools import BaseTool
from minion.types import AgentState

from ..utils.todo_storage import get_todos, TodoStatus


def format_todos_display(todos):
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


class TodoReadTool(BaseTool):
    """Tool for reading and displaying current todo items."""
    
    name = "todo_read"
    description = "View current todo items and their status."
    readonly = True  # Read-only tool, does not modify system state
    needs_state = True  # Tool needs agent state
    inputs = {}
    output_type = "string"
    
    def _get_agent_id(self, state: AgentState) -> str:
        """Get agent ID from agent state."""
        # Try to get from metadata
        return state.agent.agent_id
    
    def forward(self, state: AgentState) -> str:
        """Execute the todo read operation."""
        try:
            # Get agent ID from agent state
            agent_id = self._get_agent_id(state)
            
            # Get current todos
            todos = get_todos(agent_id)
            
            if not todos:
                return "No todos currently"
            
            # Generate statistics
            stats = {
                'total': len(todos),
                'pending': len([t for t in todos if t.status == TodoStatus.PENDING]),
                'in_progress': len([t for t in todos if t.status == TodoStatus.IN_PROGRESS]),
                'completed': len([t for t in todos if t.status == TodoStatus.COMPLETED])
            }
            
            # Update agent metadata with current todo stats
            state.metadata['current_todo_stats'] = stats
            
            # Format display
            display = format_todos_display(todos)
            
            # Generate summary
            summary = f"Found {stats['total']} todo(s): {stats['pending']} pending, {stats['in_progress']} in progress, {stats['completed']} completed"
            
            result = f"{summary}\n\n{display}"
            return result
            
        except Exception as e:
            return f"Error reading todos: {str(e)}"