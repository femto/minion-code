#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual test for FileReadTool with format_for_observation
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import directly from the file to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "file_read_tool",
    os.path.join(os.path.dirname(__file__), "minion_code/tools/file_read_tool.py")
)
file_read_module = importlib.util.module_from_spec(spec)

# Create a mock BaseTool to satisfy the import
class MockBaseTool:
    name = "base"
    description = "Base tool"
    readonly = True
    inputs = {}
    output_type = "string"

    def format_for_observation(self, output):
        return str(output) if output is not None else ""

# Inject the mock into sys.modules before loading
import types
minion_module = types.ModuleType('minion')
minion_tools_module = types.ModuleType('minion.tools')
minion_tools_module.BaseTool = MockBaseTool
minion_module.tools = minion_tools_module
sys.modules['minion'] = minion_module
sys.modules['minion.tools'] = minion_tools_module

# Now we can load the file_read_tool module
spec.loader.exec_module(file_read_module)
FileReadTool = file_read_module.FileReadTool

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: PIL not available, skipping image tests")


def test_text_file():
    """Test reading a text file with line numbers"""
    print("\n=== Test 1: Text File ===")

    # Create test file
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("Hello World\n")
        f.write("This is line 2\n")
        f.write("This is line 3\n")

    # Create tool and read file
    tool = FileReadTool()
    result = tool.forward(test_file)

    print(f"Raw output type: {type(result)}")
    print(f"Raw output:\n{result}\n")

    # Format for observation
    formatted = tool.format_for_observation(result)
    print(f"Formatted for observation:\n{formatted}\n")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    return "✓ Text file test passed"


def test_text_file_with_offset():
    """Test reading a text file with offset"""
    print("\n=== Test 2: Text File with Offset ===")

    # Create test file
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        for i in range(1, 11):
            f.write(f"Line {i}\n")

    # Create tool and read file with offset
    tool = FileReadTool()
    result = tool.forward(test_file, offset=5, limit=3)

    print(f"Raw output:\n{result}\n")

    # Format for observation
    formatted = tool.format_for_observation(result)
    print(f"Formatted for observation:\n{formatted}\n")

    # Verify line numbers start from 6 (offset=5 means skip first 5 lines)
    assert "6→" in formatted or "    6→" in formatted, "Line 6 should be present"

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    return "✓ Text file with offset test passed"


def test_image_file():
    """Test reading an image file"""
    if not HAS_PIL:
        print("\n=== Test 3: Image File (SKIPPED - PIL not available) ===")
        return "⊘ Image file test skipped (PIL not installed)"

    print("\n=== Test 3: Image File ===")

    # Create test image
    temp_dir = tempfile.mkdtemp()
    test_image = os.path.join(temp_dir, "test.png")
    img = Image.new('RGB', (100, 100), color='red')
    img.save(test_image)

    # Create tool and read image
    tool = FileReadTool()
    result = tool.forward(test_image)

    print(f"Raw output type: {type(result)}")
    print(f"Image size: {result.size if hasattr(result, 'size') else 'N/A'}")
    print(f"Image mode: {result.mode if hasattr(result, 'mode') else 'N/A'}\n")

    # Format for observation
    formatted = tool.format_for_observation(result)
    print(f"Formatted for observation (first 500 chars):\n{formatted[:500]}...\n")

    # Verify base64 encoding is present
    assert "base64" in formatted.lower(), "Should contain base64 encoding"
    assert "100x100" in formatted, "Should contain image dimensions"

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    return "✓ Image file test passed"


def test_error_handling():
    """Test error handling"""
    print("\n=== Test 4: Error Handling ===")

    tool = FileReadTool()
    result = tool.forward("/nonexistent/file.txt")

    print(f"Error result: {result}\n")

    # Format for observation
    formatted = tool.format_for_observation(result)
    print(f"Formatted error: {formatted}\n")

    assert "Error" in result, "Should contain error message"
    assert "Error" in formatted, "Formatted output should also contain error"

    return "✓ Error handling test passed"


def main():
    print("=" * 60)
    print("FileReadTool with format_for_observation - Manual Tests")
    print("=" * 60)

    results = []

    try:
        results.append(test_text_file())
    except Exception as e:
        results.append(f"✗ Test 1 failed: {e}")

    try:
        results.append(test_text_file_with_offset())
    except Exception as e:
        results.append(f"✗ Test 2 failed: {e}")

    try:
        results.append(test_image_file())
    except Exception as e:
        results.append(f"✗ Test 3 failed: {e}")

    try:
        results.append(test_error_handling())
    except Exception as e:
        results.append(f"✗ Test 4 failed: {e}")

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for result in results:
        print(result)
    print("=" * 60)


if __name__ == "__main__":
    main()
