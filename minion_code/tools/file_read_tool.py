#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File reading tool
"""

from pathlib import Path
from typing import Optional
from minion.tools import BaseTool


class FileReadTool(BaseTool):
    """File reading tool"""

    name = "file_read"
    description = "Read file content, supports text files and image files"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "file_path": {"type": "string", "description": "File path to read"},
        "offset": {
            "type": "integer",
            "description": "Starting line number (optional)",
            "nullable": True,
        },
        "limit": {
            "type": "integer",
            "description": "Line count limit (optional)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """Read file content"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File does not exist - {file_path}"

            if not path.is_file():
                return f"Error: Path is not a file - {file_path}"

            # Check if it's an image file
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
            if path.suffix.lower() in image_extensions:
                return f"Image file: {file_path} (size: {path.stat().st_size} bytes)"

            # Read text file
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Apply offset and limit
            if offset is not None:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]

            content = "".join(lines)

            result = f"File: {file_path}\n"
            result += f"Total lines: {total_lines}\n"
            if offset is not None or limit is not None:
                result += f"Displayed lines: {len(lines)}\n"
            result += f"Content:\n{content}"

            return result

        except Exception as e:
            return f"Error reading file: {str(e)}"
