#!/usr/bin/env python3
"""Example usage of the FileFreshnessService with event system."""

import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minion_code.services import (
    file_freshness_service,
    add_event_listener,
    emit_event,
    record_file_read,
    record_file_edit,
    check_file_freshness,
)


def main():
    """Demonstrate FileFreshnessService usage."""
    
    # Create a test file
    test_file = "test_file.txt"
    with open(test_file, "w") as f:
        f.write("Initial content")
    
    print("=== File Freshness Service Demo ===\n")
    
    # Set up event listeners to monitor what's happening
    def on_file_read(context):
        print(f"📖 File read event: {context.data['file_path']}")
    
    def on_file_edited(context):
        print(f"✏️  File edited event: {context.data['file_path']}")
    
    def on_file_conflict(context):
        print(f"⚠️  File conflict detected: {context.data['file_path']}")
    
    add_event_listener('file:read', on_file_read)
    add_event_listener('file:edited', on_file_edited)
    add_event_listener('file:conflict', on_file_conflict)
    
    # 1. Record initial file read
    print("1. Recording initial file read...")
    record_file_read(test_file)
    
    # 2. Check freshness (should be fresh)
    print("\n2. Checking file freshness...")
    result = check_file_freshness(test_file)
    print(f"   Is fresh: {result.is_fresh}, Conflict: {result.conflict}")
    
    # 3. Simulate external modification
    print("\n3. Simulating external file modification...")
    time.sleep(0.1)  # Small delay to ensure different timestamp
    with open(test_file, "w") as f:
        f.write("Modified content externally")
    
    # 4. Check freshness again (should detect conflict)
    print("\n4. Checking freshness after external modification...")
    result = check_file_freshness(test_file)
    print(f"   Is fresh: {result.is_fresh}, Conflict: {result.conflict}")
    
    # 5. Record agent edit (should clear conflict)
    print("\n5. Recording agent edit...")
    record_file_edit(test_file, "Agent modified content")
    
    # 6. Check freshness after agent edit
    print("\n6. Checking freshness after agent edit...")
    result = check_file_freshness(test_file)
    print(f"   Is fresh: {result.is_fresh}, Conflict: {result.conflict}")
    
    # 7. Show session files and conflicts
    print("\n7. Session summary:")
    session_files = file_freshness_service.get_session_files()
    conflicted_files = file_freshness_service.get_conflicted_files()
    important_files = file_freshness_service.get_important_files()
    
    print(f"   Session files: {session_files}")
    print(f"   Conflicted files: {conflicted_files}")
    print(f"   Important files: {important_files}")
    
    # 8. Test session reset
    print("\n8. Resetting session...")
    emit_event('session:startup', {'context': {}})
    
    session_files_after = file_freshness_service.get_session_files()
    print(f"   Session files after reset: {session_files_after}")
    
    # Cleanup
    os.remove(test_file)
    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    main()