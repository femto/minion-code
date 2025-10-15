#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text search tool
"""

import re
from pathlib import Path
from typing import List, Optional
from minion.tools import BaseTool


class GrepTool(BaseTool):
    """Text search tool"""

    name = "grep"
    description = "Search for text patterns in files"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "pattern": {"type": "string", "description": "Regular expression pattern to search for"},
        "path": {"type": "string", "description": "Search path (file or directory)"},
        "include": {
            "type": "string",
            "description": "File pattern to include (optional)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self, pattern: str, path: str = ".", include: Optional[str] = None
    ) -> str:
        """Search for text pattern"""
        try:
            search_path = Path(path)
            if not search_path.exists():
                return f"Error: Path does not exist - {path}"

            matches = []

            if search_path.is_file():
                # Search single file
                matches.extend(self._search_file(search_path, pattern))
            else:
                # Search directory
                if include:
                    # Filter using file pattern
                    for file_path in search_path.rglob(include):
                        if file_path.is_file():
                            matches.extend(self._search_file(file_path, pattern))
                else:
                    # Search all text files
                    for file_path in search_path.rglob("*"):
                        if file_path.is_file() and self._is_text_file(file_path):
                            matches.extend(self._search_file(file_path, pattern))

            if not matches:
                return f"No content found matching pattern '{pattern}'"

            # Group results by file
            result = f"Search results for pattern '{pattern}':\n\n"
            current_file = None
            for file_path, line_num, line_content in matches:
                if file_path != current_file:
                    result += f"File: {file_path}\n"
                    current_file = file_path
                result += f"  Line {line_num}: {line_content.strip()}\n"

            result += f"\nTotal {len(matches)} matches found"
            return result

        except Exception as e:
            return f"Error during search: {str(e)}"

    def _search_file(self, file_path: Path, pattern: str) -> List[tuple]:
        """Search pattern in a single file"""
        matches = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((str(file_path), line_num, line))
        except Exception:
            # Ignore files that cannot be read
            pass
        return matches

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is a text file"""
        text_extensions = {
            ".txt",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".md",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".conf",
        }
        return file_path.suffix.lower() in text_extensions
