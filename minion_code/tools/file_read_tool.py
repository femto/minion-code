#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File reading tool
"""

import base64
from pathlib import Path
from typing import Optional, Union, Any
from minion.tools import BaseTool
from ..utils.output_truncator import (
    check_file_size_before_read,
    FileTooLargeError,
    truncate_output,
)

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class FileReadTool(BaseTool):
    """File reading tool with image support"""

    name = "file_read"
    description = "Read file content, supports text files and image files"
    readonly = True  # Read-only tool, does not modify system state
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
    output_type = "any"  # Can return string or PIL.Image

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir) if workdir else None
        # State tracking for last execution
        self._last_file_path = None
        self._last_offset = None
        self._last_limit = None
        self._last_total_lines = None

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve path using workdir if path is relative."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        if self.workdir:
            return self.workdir / path
        return path  # Relative to cwd (backward compatible)

    def forward(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Union[str, Any]:
        """Read file content

        Returns:
            - For text files: returns the text content as string
            - For image files: returns PIL.Image object (or error string if PIL not available)
        """
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File does not exist - {file_path}"

            if not path.is_file():
                return f"Error: Path is not a file - {file_path}"

            # Check if it's an image file
            image_extensions = {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".webp",
                ".tiff",
                ".svg",
            }
            if path.suffix.lower() in image_extensions:
                return self._read_image(path)

            # 执行前检查文件大小（仅对非分页读取）
            if offset is None and limit is None:
                try:
                    check_file_size_before_read(file_path)
                except FileTooLargeError as e:
                    return f"Error: {str(e)}"

            # Read text file
            return self._read_text(path, offset, limit)

        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _read_image(self, path: Path) -> Union[Any, str]:
        """Read image file and return PIL.Image object"""
        if not HAS_PIL:
            return (
                f"Error: PIL (Pillow) is not installed. Cannot read image file: {path}"
            )

        try:
            image = Image.open(path)
            # Store state for format_for_observation
            self._last_file_path = str(path)
            self._last_offset = None
            self._last_limit = None
            self._last_total_lines = None
            return image
        except Exception as e:
            return f"Error opening image file {path}: {str(e)}"

    def _read_text(
        self, path: Path, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """Read text file and return content"""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)

        # Store state for format_for_observation
        self._last_file_path = str(path)
        self._last_offset = offset
        self._last_limit = limit
        self._last_total_lines = total_lines

        # Apply offset and limit
        if offset is not None:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[:limit]

        content = "".join(lines)
        return content

    def format_for_observation(self, output: Any) -> str:
        """Format tool output for LLM observation.

        For images: Convert PIL.Image to base64 encoded format
        For text: Add line numbers and metadata
        """
        # Handle error strings
        if isinstance(output, str) and output.startswith("Error:"):
            return output

        # Handle PIL Image
        if HAS_PIL and isinstance(output, Image.Image):
            return self._format_image_for_observation(output)

        # Handle text content
        if isinstance(output, str):
            return self._format_text_for_observation(output)

        # Fallback
        return str(output) if output is not None else ""

    def _format_image_for_observation(self, image: Any) -> str:
        """Format PIL Image as base64 for LLM observation"""
        import io

        try:
            # Convert image to RGB if necessary (for PNG with transparency, etc.)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Save image to bytes buffer
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)

            # Encode as base64
            img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            # Format for LLM observation
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

        # Calculate starting line number
        start_line = 1
        if self._last_offset is not None:
            start_line = self._last_offset + 1

        # Add line numbers
        numbered_lines = []
        for i, line in enumerate(lines, start=start_line):
            # Format: line_number→content
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

        # 应用输出截断
        return truncate_output(result, tool_name=self.name)
