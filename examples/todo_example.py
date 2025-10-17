#!/usr/bin/env python3
"""Example usage of Todo tools."""

import sys
import os
import uuid
import json

# Add the parent directory to the path so we can import minion_code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from minion_code.tools.todo_write_tool import TodoWriteTool
from minion_code.tools.todo_read_tool import TodoReadTool
from minion.types import AgentState


def main():
    """Demonstrate todo tools functionality."""
    print("=== Todo Tools Example ===\n")
    
    # Initialize tools
    write_tool = TodoWriteTool()
    read_tool = TodoReadTool()
    
    # Create agent state for testing
    agent_state = AgentState(
        task="Todo management example",
        metadata={"agent_id": "example_agent"}
    )
    
    print("1. Creating initial todos...")
    
    # Create some sample todos
    todos_data = [
        {
            "id": str(uuid.uuid4()),
            "content": "Set up project structure",
            "status": "completed",
            "priority": "high"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Implement todo storage system",
            "status": "completed",
            "priority": "high"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Create todo write tool",
            "status": "in_progress",
            "priority": "medium"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Create todo read tool",
            "status": "pending",
            "priority": "medium"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Add tests for todo tools",
            "status": "pending",
            "priority": "low"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Write documentation",
            "status": "pending",
            "priority": "low"
        }
    ]
    
    todos_json = json.dumps(todos_data)
    
    # Execute write operation
    result = write_tool.forward(todos_json, agent_state)
    
    if not result.startswith("Error"):
        print(f"✓ Success!")
        print(f"Result:\n{result}\n")
    else:
        print(f"✗ {result}")
        return
    
    print("2. Reading current todos...")
    
    # Read todos
    read_result = read_tool.forward(agent_state)
    
    if not read_result.startswith("Error"):
        print(f"✓ Success!")
        print(f"Result:\n{read_result}\n")
    else:
        print(f"✗ {read_result}")
        return
    
    print("3. Updating todo status...")
    
    # Update a todo (mark the in_progress one as completed and start the next one)
    updated_todos = []
    for todo_data in todos_data:
        if todo_data["status"] == "in_progress":
            # Mark current in_progress as completed
            todo_data["status"] = "completed"
        elif todo_data["status"] == "pending" and todo_data["content"] == "Create todo read tool":
            # Mark next pending as in_progress
            todo_data["status"] = "in_progress"
        updated_todos.append(todo_data)
    
    updated_json = json.dumps(updated_todos)
    update_result = write_tool.forward(updated_json, agent_state)
    
    if not update_result.startswith("Error"):
        print(f"✓ Success!")
        print(f"Result:\n{update_result}\n")
    else:
        print(f"✗ {update_result}")
        return
    
    print("4. Testing validation (duplicate IDs)...")
    
    # Test validation with duplicate IDs
    invalid_todos = [
        {
            "id": "duplicate_id",
            "content": "First task",
            "status": "pending",
            "priority": "high"
        },
        {
            "id": "duplicate_id",  # Duplicate ID
            "content": "Second task",
            "status": "pending",
            "priority": "medium"
        }
    ]
    
    invalid_json = json.dumps(invalid_todos)
    invalid_result = write_tool.forward(invalid_json, agent_state)
    
    if invalid_result.startswith("Validation Error"):
        print(f"✓ Validation caught error: {invalid_result}")
    else:
        print("✗ Validation should have failed")
    
    print("\n5. Testing validation (multiple in_progress)...")
    
    # Test validation with multiple in_progress tasks
    invalid_todos2 = [
        {
            "id": str(uuid.uuid4()),
            "content": "First in progress task",
            "status": "in_progress",
            "priority": "high"
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Second in progress task",
            "status": "in_progress",
            "priority": "medium"
        }
    ]
    
    invalid_json2 = json.dumps(invalid_todos2)
    invalid_result2 = write_tool.forward(invalid_json2, agent_state)
    
    if invalid_result2.startswith("Validation Error"):
        print(f"✓ Validation caught error: {invalid_result2}")
    else:
        print("✗ Validation should have failed")
    
    print("\n=== Todo Tools Example Complete ===")


if __name__ == "__main__":
    main()