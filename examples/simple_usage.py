#!/usr/bin/env python3
"""Simple usage example of FileFreshnessService."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.services import (
    record_file_read,
    record_file_edit,
    check_file_freshness,
    generate_file_modification_reminder,
    add_event_listener,
    emit_event,
)


def main():
    """Simple usage demonstration."""
    
    # Set up a simple event listener
    def on_conflict(context):
        print(f"⚠️  Conflict: {context.data['file_path']}")
    
    add_event_listener('file:conflict', on_conflict)
    
    # Create test file
    test_file = "example.py"
    with open(test_file, "w") as f:
        f.write("print('Hello, World!')")
    
    # Record reading the file
    record_file_read(test_file)
    print(f"✅ Recorded reading {test_file}")
    
    # Check freshness (should be fresh)
    result = check_file_freshness(test_file)
    print(f"📊 File is fresh: {result.is_fresh}")
    
    # Simulate external modification
    with open(test_file, "w") as f:
        f.write("print('Modified externally!')")
    
    # Check freshness again (should detect conflict)
    result = check_file_freshness(test_file)
    print(f"📊 After external change - Fresh: {result.is_fresh}, Conflict: {result.conflict}")
    
    # Generate reminder for external modification
    reminder = generate_file_modification_reminder(test_file)
    if reminder:
        print(f"💡 Reminder: {reminder}")
    
    # Record agent edit (resolves conflict)
    record_file_edit(test_file, "print('Agent fixed this!')")
    print(f"✅ Agent edited {test_file}")
    
    # Check freshness after agent edit
    result = check_file_freshness(test_file)
    print(f"📊 After agent edit - Fresh: {result.is_fresh}, Conflict: {result.conflict}")
    
    # Cleanup
    os.remove(test_file)
    print("🧹 Cleaned up test file")


if __name__ == "__main__":
    main()