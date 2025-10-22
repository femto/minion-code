#!/usr/bin/env python3
"""Example usage of file watching functionality."""

import os
import sys
import time
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.services import (
    start_watching_todo_file,
    stop_watching_todo_file,
    add_event_listener,
    record_file_read,
    file_freshness_service,
)


def main():
    """Demonstrate file watching functionality."""
    
    print("=== File Watching Demo ===\n")
    
    # Set up event listeners
    def on_todo_file_changed(context):
        data = context.data
        print(f"🔔 Todo file changed for agent {data['agent_id']}")
        print(f"   File: {data['file_path']}")
        print(f"   Reminder: {data['reminder']}")
        print()
    
    add_event_listener('todo:file_changed', on_todo_file_changed)
    
    # Create test directory and file
    test_dir = "test_todos"
    os.makedirs(test_dir, exist_ok=True)
    
    test_file = os.path.join(test_dir, "agent1.json")
    agent_id = "agent1"
    
    # Create initial todo file
    with open(test_file, "w") as f:
        f.write('{"todos": [{"id": 1, "content": "Initial task", "status": "pending"}]}')
    
    print(f"1. Created test todo file: {test_file}")
    
    # Start watching the file
    print(f"2. Starting to watch todo file for agent: {agent_id}")
    start_watching_todo_file(agent_id, test_file)
    
    # Record initial read
    record_file_read(test_file)
    print("3. Recorded initial file read")
    
    # Check if we're watching
    watched_files = file_freshness_service.get_watched_files()
    print(f"4. Currently watching files: {watched_files}")
    
    # Wait a bit for watcher to initialize
    time.sleep(1)
    
    # Simulate external modification
    print("\n5. Simulating external file modification...")
    
    def modify_file():
        time.sleep(0.5)  # Small delay
        with open(test_file, "w") as f:
            f.write('{"todos": [{"id": 1, "content": "Modified task", "status": "completed"}]}')
        print("   ✏️  File modified externally")
    
    # Run modification in separate thread to avoid blocking
    modifier_thread = threading.Thread(target=modify_file)
    modifier_thread.start()
    
    # Wait for modification and watcher to detect it
    modifier_thread.join()
    time.sleep(2)  # Give watcher time to detect change
    
    # Modify file again
    print("6. Another external modification...")
    time.sleep(0.5)
    with open(test_file, "w") as f:
        f.write('{"todos": [{"id": 2, "content": "Another task", "status": "pending"}]}')
    
    # Wait for detection
    time.sleep(2)
    
    # Stop watching
    print("7. Stopping file watcher...")
    stop_watching_todo_file(agent_id)
    
    # Verify we're no longer watching
    watched_files_after = file_freshness_service.get_watched_files()
    print(f"8. Files being watched after stop: {watched_files_after}")
    
    # Cleanup
    try:
        os.remove(test_file)
        os.rmdir(test_dir)
        print("\n🧹 Cleaned up test files")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
    
    print("\n✅ File watching demo completed!")


if __name__ == "__main__":
    main()