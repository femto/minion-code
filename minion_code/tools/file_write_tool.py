#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File writing tool
"""

from pathlib import Path
from minion.tools import BaseTool


class FileWriteTool(BaseTool):
    """File writing tool"""

    name = "file_write"
    description = "Write content to file"
    readonly = False  # Writing tool, modifies system state
    inputs = {
        "file_path": {"type": "string", "description": "File path to write to"},
        "content": {"type": "string", "description": "Content to write"},
    }
    output_type = "string"

    def forward(self, file_path: str, content: str) -> str:
        """Write file content"""
        try:
            path = Path(file_path)
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote to file: {file_path} ({len(content)} characters)"

        except Exception as e:
            return f"Error writing file: {str(e)}"
