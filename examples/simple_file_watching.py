#!/usr/bin/env python3
"""Simple file watching example."""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.services import (
    start_watching_todo_file,
    stop_watching_todo_file,
    add_event_listener,
    record_file_read,
)


def main():
    """Simple file watching demonstration."""
    
    # Set up event listener
    def on_file_changed(context):
        print(f"📁 File changed: {context.data['file_path']}")
        print(f"💡 {context.data['reminder']}")
    
    add_event_listener('todo:file_changed', on_file_changed)
    
    # Create test file
    test_file = "simple_todo.json"
    with open(test_file, "w") as f:
        f.write('{"task": "initial"}')
    
    print(f"✅ Created {test_file}")
    
    # Start watching
    start_watching_todo_file("test_agent", test_file)
    record_file_read(test_file)
    print("👀 Started watching file")
    
    # Wait and modify
    time.sleep(1)
    print("✏️  Modifying file...")
    with open(test_file, "w") as f:
        f.write('{"task": "modified"}')
    
    # Wait for detection
    time.sleep(2)
    
    # Stop watching and cleanup
    stop_watching_todo_file("test_agent")
    os.remove(test_file)
    print("🧹 Cleaned up")


if __name__ == "__main__":
    main()