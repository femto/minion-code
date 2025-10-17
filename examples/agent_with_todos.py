#!/usr/bin/env python3
"""Example of using Todo tools with MinionCodeAgent."""

import sys
import os
import asyncio
import uuid
import json

# Add the parent directory to the path so we can import minion_code
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from minion_code.agents.code_agent import MinionCodeAgent


async def demonstrate_todo_workflow():
    """Demonstrate using Todo tools with MinionCodeAgent."""
    print("=== MinionCodeAgent Todo Workflow Demo ===\n")
    
    # Create agent
    print("1. Creating MinionCodeAgent...")
    agent = await MinionCodeAgent.create(
        name="Todo Demo Agent",
        llm="gpt-4o-mini"
    )
    print("✓ Agent created successfully\n")
    
    # Show available tools
    print("2. Available tools:")
    tools_info = agent.get_tools_info()
    todo_tools = [tool for tool in tools_info if 'todo' in tool['name'].lower()]
    for tool in todo_tools:
        readonly_icon = "🔒" if tool['readonly'] else "✏️"
        print(f"  {readonly_icon} {tool['name']}: {tool['description']}")
    print()
    
    # Define project tasks
    tasks = [
        "Analyze project requirements",
        "Design system architecture", 
        "Implement core functionality",
        "Write unit tests",
        "Create documentation",
        "Deploy to production"
    ]
    
    # Create initial todos using agent
    print("3. Creating initial todos...")
    todos_data = []
    for i, task in enumerate(tasks):
        todos_data.append({
            "id": str(uuid.uuid4()),
            "content": task,
            "status": "pending" if i > 0 else "in_progress",  # First task in progress
            "priority": "high" if i < 2 else "medium"
        })
    
    todos_json = json.dumps(todos_data)
    
    # Use agent to create todos
    create_message = f"""Please use the todo_write tool to create these todos:
{todos_json}"""
    
    response = await agent.run_async(create_message)
    print(f"✓ Agent response: {response.answer if hasattr(response, 'answer') else str(response)}\n")
    
    # Read current todos
    print("4. Reading current todos...")
    read_message = """Please use the todo_read tool to show current todos."""
    
    response = await agent.run_async(read_message)
    print(f"✓ Current todos:\n{response.answer if hasattr(response, 'answer') else str(response)}\n")
    
    # Simulate completing a few tasks
    print("5. Completing tasks...")
    
    # Complete first task and start next
    for i in range(3):  # Complete 3 tasks
        print(f"   Step {i+1}: Completing current task and starting next...")
        
        # Get current todos from storage to update them
        from minion_code.utils.todo_storage import get_todos, TodoStatus
        # Use the same agent ID logic as the tool
        import hashlib
        agent_id = "demo_agent"  # We'll use a consistent ID for this demo
        current_todos = get_todos(agent_id)
        
        if not current_todos:
            print("   No todos found")
            break
        
        # Update todos: complete in_progress, start next pending
        updated_todos = []
        found_in_progress = False
        started_next = False
        
        for todo in current_todos:
            if todo.status == TodoStatus.IN_PROGRESS:
                # Mark as completed
                todo_data = {
                    "id": todo.id,
                    "content": todo.content,
                    "status": "completed",
                    "priority": todo.priority.value
                }
                found_in_progress = True
            elif todo.status == TodoStatus.PENDING and not started_next:
                # Start next pending task
                todo_data = {
                    "id": todo.id,
                    "content": todo.content,
                    "status": "in_progress",
                    "priority": todo.priority.value
                }
                started_next = True
            else:
                # Keep as is
                todo_data = {
                    "id": todo.id,
                    "content": todo.content,
                    "status": todo.status.value,
                    "priority": todo.priority.value
                }
            
            updated_todos.append(todo_data)
        
        if not found_in_progress:
            print("   No in_progress task found")
            break
        
        # Update todos using agent
        updated_json = json.dumps(updated_todos)
        update_message = f"""Please use the todo_write tool to update todos:
{updated_json}"""
        
        response = await agent.run_async(update_message)
        print(f"   ✓ Updated: {response.answer if hasattr(response, 'answer') else str(response)}")
    
    print()
    
    # Final status
    print("6. Final todo status...")
    final_message = """Please use the todo_read tool to show final todos."""
    
    response = await agent.run_async(final_message)
    print(f"✓ Final todos:\n{response.answer if hasattr(response, 'answer') else str(response)}\n")
    
    # Show conversation history
    print("7. Conversation summary:")
    history = agent.get_conversation_history()
    print(f"   Total interactions: {len(history)}")
    for i, interaction in enumerate(history, 1):
        print(f"   {i}. User: {interaction['user_message'][:50]}...")
        print(f"      Agent: {str(interaction['agent_response'])[:50]}...")
    
    print("\n=== Demo Complete ===")


def main():
    """Run the async demo."""
    asyncio.run(demonstrate_todo_workflow())


if __name__ == "__main__":
    main()