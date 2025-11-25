#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone test to demonstrate FileReadTool functionality
This demonstrates the key features without requiring package installation
"""

import os
import tempfile
import base64
from pathlib import Path
from typing import Optional, Union, Any

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Note: PIL not available, image tests will be skipped")


# Minimal BaseTool mock for demonstration
class BaseTool:
    """Mock BaseTool for standalone testing"""
    name = "base"
    description = "Base tool"
    readonly = True
    inputs = {}
    output_type = "string"

    def format_for_observation(self, output: Any) -> str:
        """Default format_for_observation - just convert to string"""
        return str(output) if output is not None else ""


# Copy of the FileReadTool implementation
class FileReadTool(BaseTool):
    """File reading tool with image support"""

    name = "file_read"
    description = "Read file content, supports text files and image files"
    readonly = True
    inputs = {
        "file_path": {"type": "string", "description": "File path to read"},
        "offset": {
            "type": "integer",
            "description": "Starting line number (optional, for text files)",
            "nullable": True,
        },
        "limit": {
            "type": "integer",
            "description": "Line count limit (optional, for text files)",
            "nullable": True,
        },
    }
    output_type = "any"

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._last_file_path = None
        self._last_offset = None
        self._last_limit = None
        self._last_total_lines = None

    def forward(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Union[str, Any]:
        """Read file content"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File does not exist - {file_path}"

            if not path.is_file():
                return f"Error: Path is not a file - {file_path}"

            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
            if path.suffix.lower() in image_extensions:
                return self._read_image(path)

            return self._read_text(path, offset, limit)

        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _read_image(self, path: Path) -> Union[Any, str]:
        """Read image file and return PIL.Image object"""
        if not HAS_PIL:
            return f"Error: PIL (Pillow) is not installed. Cannot read image file: {path}"

        try:
            image = Image.open(path)
            self._last_file_path = str(path)
            self._last_offset = None
            self._last_limit = None
            self._last_total_lines = None
            return image
        except Exception as e:
            return f"Error opening image file {path}: {str(e)}"

    def _read_text(self, path: Path, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
        """Read text file and return content"""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        self._last_file_path = str(path)
        self._last_offset = offset
        self._last_limit = limit
        self._last_total_lines = total_lines

        if offset is not None:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[:limit]

        content = "".join(lines)
        return content

    def format_for_observation(self, output: Any) -> str:
        """Format tool output for LLM observation."""
        if isinstance(output, str) and output.startswith("Error:"):
            return output

        if HAS_PIL and isinstance(output, Image.Image):
            return self._format_image_for_observation(output)

        if isinstance(output, str):
            return self._format_text_for_observation(output)

        return str(output) if output is not None else ""

    def _format_image_for_observation(self, image: Any) -> str:
        """Format PIL Image as base64 for LLM observation"""
        import io

        try:
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')

            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            buffer.seek(0)

            img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            result = f"Image file: {self._last_file_path}\n"
            result += f"Size: {image.size[0]}x{image.size[1]} pixels\n"
            result += f"Mode: {image.mode}\n"
            result += f"Format: {image.format}\n"
            result += f"\nBase64 encoded image:\n"
            result += f"data:image/png;base64,{img_base64}"

            return result
        except Exception as e:
            return f"Error formatting image for observation: {str(e)}"

    def _format_text_for_observation(self, content: str) -> str:
        """Format text content with line numbers for LLM observation"""
        if not content:
            return f"File: {self._last_file_path}\n(empty file)"

        lines = content.splitlines(keepends=True)

        start_line = 1
        if self._last_offset is not None:
            start_line = self._last_offset + 1

        numbered_lines = []
        for i, line in enumerate(lines, start=start_line):
            numbered_lines.append(f"{i:5d}→{line}")

        result = f"File: {self._last_file_path}\n"
        if self._last_total_lines is not None:
            result += f"Total lines: {self._last_total_lines}\n"
        if self._last_offset is not None or self._last_limit is not None:
            result += f"Displayed lines: {len(lines)}"
            if self._last_offset is not None:
                result += f" (starting from line {start_line})"
            result += "\n"
        result += "\n"
        result += "".join(numbered_lines)

        return result


def demo_text_file():
    """Demonstrate text file reading with line numbers"""
    print("\n" + "="*60)
    print("DEMO 1: Text File with Line Numbers")
    print("="*60)

    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "example.py")

    # Create a sample Python file
    with open(test_file, "w") as f:
        f.write("def hello_world():\n")
        f.write("    print('Hello, World!')\n")
        f.write("\n")
        f.write("def add(a, b):\n")
        f.write("    return a + b\n")
        f.write("\n")
        f.write("if __name__ == '__main__':\n")
        f.write("    hello_world()\n")

    tool = FileReadTool()

    # Read the file
    raw_output = tool.forward(test_file)
    print("\n📄 Raw output (returned from forward()):")
    print("-" * 60)
    print(raw_output)

    # Format for observation (what LLM sees)
    formatted_output = tool.format_for_observation(raw_output)
    print("\n👁️  Formatted for observation (with line numbers):")
    print("-" * 60)
    print(formatted_output)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_text_with_offset():
    """Demonstrate text file reading with offset"""
    print("\n" + "="*60)
    print("DEMO 2: Text File with Offset (lines 3-5)")
    print("="*60)

    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "data.txt")

    with open(test_file, "w") as f:
        for i in range(1, 11):
            f.write(f"This is line {i}\n")

    tool = FileReadTool()

    # Read with offset and limit
    raw_output = tool.forward(test_file, offset=2, limit=3)
    print("\n📄 Raw output (lines 3-5):")
    print("-" * 60)
    print(raw_output)

    formatted_output = tool.format_for_observation(raw_output)
    print("\n👁️  Formatted for observation (note line numbers start at 3):")
    print("-" * 60)
    print(formatted_output)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def demo_image_file():
    """Demonstrate image file reading"""
    if not HAS_PIL:
        print("\n" + "="*60)
        print("DEMO 3: Image File (SKIPPED - PIL not installed)")
        print("="*60)
        print("Install Pillow to test image support: pip install Pillow")
        return

    print("\n" + "="*60)
    print("DEMO 3: Image File with Base64 Encoding")
    print("="*60)

    temp_dir = tempfile.mkdtemp()
    test_image = os.path.join(temp_dir, "test_image.png")

    # Create a simple colored image
    img = Image.new('RGB', (200, 150), color=(255, 100, 50))
    img.save(test_image)

    tool = FileReadTool()

    # Read the image
    raw_output = tool.forward(test_image)
    print(f"\n📄 Raw output type: {type(raw_output)}")
    print(f"   Image size: {raw_output.size}")
    print(f"   Image mode: {raw_output.mode}")

    # Format for observation
    formatted_output = tool.format_for_observation(raw_output)
    print("\n👁️  Formatted for observation (base64 for LLM):")
    print("-" * 60)
    # Print first 500 chars to avoid cluttering output
    if len(formatted_output) > 500:
        print(formatted_output[:500] + "\n... (truncated)")
    else:
        print(formatted_output)

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def main():
    print("="*60)
    print("FileReadTool with format_for_observation")
    print("Demonstration of new features")
    print("="*60)

    demo_text_file()
    demo_text_with_offset()
    demo_image_file()

    print("\n" + "="*60)
    print("Summary of Features")
    print("="*60)
    print("✓ Text files: forward() returns plain string")
    print("✓ Text files: format_for_observation() adds line numbers")
    print("✓ Images: forward() returns PIL.Image object")
    print("✓ Images: format_for_observation() converts to base64")
    print("✓ State tracking: line numbers stored in tool instance")
    print("="*60)


if __name__ == "__main__":
    main()
