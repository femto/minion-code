#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Text search tool
"""

import re
from pathlib import Path
from typing import List, Optional, Any
from minion.tools import BaseTool
from ..utils.output_truncator import truncate_output


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
        "output_mode": {
            "type": "string",
            "description": "Output mode: 'content' (show matching lines), 'files_with_matches' (show file paths), 'count' (show match counts)",
            "nullable": True,
        },
        "head_limit": {
            "type": "integer",
            "description": "Limit output to first N entries",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        pattern: str,
        path: str = ".",
        include: Optional[str] = None,
        output_mode: Optional[str] = None,
        head_limit: Optional[int] = None
    ) -> str:
        """Search for text pattern"""
        try:
            # Default to 'content' mode for backward compatibility
            if output_mode is None:
                output_mode = "content"

            # Validate output_mode
            if output_mode not in ["content", "files_with_matches", "count"]:
                return f"Error: Invalid output_mode '{output_mode}'. Must be 'content', 'files_with_matches', or 'count'"

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

            # Format output based on mode
            if output_mode == "files_with_matches":
                result = self._format_files_with_matches(matches, pattern, head_limit)
            elif output_mode == "count":
                result = self._format_count(matches, pattern, head_limit)
            else:  # content mode
                result = self._format_content(matches, pattern, head_limit)

            return self.format_for_observation(result)

        except Exception as e:
            return f"Error during search: {str(e)}"

    def _format_content(self, matches: List[tuple], pattern: str, head_limit: Optional[int]) -> str:
        """Format matches as content with line numbers"""
        result = f"Search results for pattern '{pattern}':\n\n"
        current_file = None
        count = 0

        for file_path, line_num, line_content in matches:
            if head_limit and count >= head_limit:
                result += f"\n(Output limited to {head_limit} lines)"
                break

            if file_path != current_file:
                result += f"File: {file_path}\n"
                current_file = file_path
            result += f"  Line {line_num}: {line_content.strip()}\n"
            count += 1

        result += f"\nTotal {len(matches)} matches found"
        return result

    def _format_files_with_matches(self, matches: List[tuple], pattern: str, head_limit: Optional[int]) -> str:
        """Format matches as list of unique file paths"""
        # Get unique file paths
        unique_files = []
        seen = set()
        for file_path, _, _ in matches:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)
                if head_limit and len(unique_files) >= head_limit:
                    break

        result = f"Files matching pattern '{pattern}':\n\n"
        for file_path in unique_files:
            result += f"{file_path}\n"

        if head_limit and len(seen) > head_limit:
            result += f"\n(Output limited to {head_limit} files)"
        result += f"\nTotal {len(seen)} files with matches"
        return result

    def _format_count(self, matches: List[tuple], pattern: str, head_limit: Optional[int]) -> str:
        """Format matches as count per file"""
        # Count matches per file
        file_counts = {}
        for file_path, _, _ in matches:
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

        result = f"Match counts for pattern '{pattern}':\n\n"
        count = 0
        for file_path, match_count in file_counts.items():
            if head_limit and count >= head_limit:
                result += f"\n(Output limited to {head_limit} files)"
                break
            result += f"{file_path}: {match_count} matches\n"
            count += 1

        result += f"\nTotal {sum(file_counts.values())} matches in {len(file_counts)} files"
        return result

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

    def format_for_observation(self, output: Any) -> str:
        """Format output, auto-truncate if too large"""
        if isinstance(output, str):
            return truncate_output(output, tool_name=self.name)
        return str(output)
