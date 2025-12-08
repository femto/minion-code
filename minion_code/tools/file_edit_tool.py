#!/usr/bin/env python3
"""
File editing tool based on TypeScript FileEditTool implementation.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from minion.tools import BaseTool
from minion_code.services import record_file_read, record_file_edit, check_file_freshness


class FileEditTool(BaseTool):
    """
    A tool for editing files with string replacement.
    Based on the TypeScript FileEditTool implementation.
    """

    name = "file_edit"
    description = "A tool for editing files by replacing old_string with new_string with freshness tracking. For large strings (>2000 chars), consider using MultiEditTool or breaking into smaller edits."
    readonly = False

    inputs = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to modify"
        },
        "old_string": {
            "type": "string",
            "description": "The text to replace (must be unique within the file)"
        },
        "new_string": {
            "type": "string",
            "description": "The text to replace it with"
        }
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir) if workdir else None

    def _resolve_path(self, file_path: str) -> str:
        """Resolve path using workdir if path is relative."""
        if os.path.isabs(file_path):
            return file_path
        if self.workdir:
            return str(self.workdir / file_path)
        return os.path.abspath(file_path)  # Fallback to cwd (backward compatible)

    def forward(self, file_path: str, old_string: str, new_string: str) -> str:
        """Execute file edit operation."""
        try:
            # Validate inputs
            validation_result = self._validate_input(file_path, old_string, new_string)
            if not validation_result["valid"]:
                return f"Error: {validation_result['message']}"
            
            # Check for warnings about large strings
            warning_message = ""
            if "warning" in validation_result:
                warning_message = f"⚠️  Warning: {validation_result['warning']}\n\n"
            
            # Apply the edit
            result = self._apply_edit(file_path, old_string, new_string)
            
            # Prepend warning if present
            if warning_message:
                result = warning_message + result
            
            return result
            
        except Exception as e:
            return f"Error during file edit: {str(e)}"
    
    def _validate_input(self, file_path: str, old_string: str, new_string: str) -> Dict[str, Any]:
        """Validate input parameters."""
        
        # Check if old_string and new_string are the same
        if old_string == new_string:
            return {
                "valid": False,
                "message": "No changes to make: old_string and new_string are exactly the same."
            }
        
        # Check for large strings and suggest better alternatives
        large_string_threshold = 2000  # characters
        very_large_threshold = 5000   # characters
        
        old_string_size = len(old_string)
        new_string_size = len(new_string)
        max_size = max(old_string_size, new_string_size)
        
        if max_size > very_large_threshold:
            suggestions = self._suggest_alternatives_for_large_edit(old_string, new_string)
            return {
                "valid": False,
                "message": f"String is very large ({max_size} characters). For better performance and reliability, "
                         f"large single edits should be avoided as they can be error-prone and difficult to debug.\n\n"
                         f"{suggestions}"
            }
        elif max_size > large_string_threshold:
            # Allow but warn
            lines_count = max(old_string.count('\n'), new_string.count('\n'))
            suggestions = self._suggest_alternatives_for_large_edit(old_string, new_string)
            warning_msg = f"Large string detected ({max_size} characters, ~{lines_count} lines). "
            if suggestions:
                warning_msg += f"Consider these alternatives:\n{suggestions}"
            else:
                warning_msg += "Consider using MultiEditTool for multiple smaller edits or breaking this into smaller chunks for better reliability and easier debugging."
            
            return {
                "valid": True,
                "warning": warning_msg
            }
        
        # Resolve path using workdir if relative
        resolved_path = self._resolve_path(file_path)

        # Handle new file creation
        if not os.path.exists(resolved_path) and old_string == "":
            return {"valid": True}
        
        # Check if file exists for existing file edits
        if not os.path.exists(resolved_path):
            return {
                "valid": False,
                "message": "File does not exist."
            }

        # Check if it's a Jupyter notebook
        if resolved_path.endswith('.ipynb'):
            return {
                "valid": False,
                "message": "File is a Jupyter Notebook. Use NotebookEdit tool instead."
            }

        # Check file freshness (if we have tracking)
        try:
            freshness_result = check_file_freshness(resolved_path)
            if freshness_result.conflict:
                return {
                    "valid": False,
                    "message": "File has been modified since last read. Read it again before editing."
                }
        except Exception:
            # If freshness checking fails, continue with basic validation
            pass

        # Check if file is binary
        if self._is_binary_file(resolved_path):
            return {
                "valid": False,
                "message": "Cannot edit binary files."
            }

        # For existing files, validate old_string exists and is unique
        if old_string != "":
            try:
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if old_string not in content:
                    return {
                        "valid": False,
                        "message": "String to replace not found in file."
                    }
                
                # Check for multiple matches
                matches = content.count(old_string)
                if matches > 1:
                    return {
                        "valid": False,
                        "message": f"Found {matches} matches of the string to replace. "
                                 "For safety, this tool only supports replacing exactly one occurrence at a time. "
                                 "Add more lines of context to your edit and try again."
                    }
                
            except UnicodeDecodeError:
                return {
                    "valid": False,
                    "message": "Cannot read file - appears to be binary or has encoding issues."
                }
        
        return {"valid": True}
    
    def _apply_edit(self, file_path: str, old_string: str, new_string: str) -> str:
        """Apply the edit to the file."""

        # Resolve path using workdir if relative
        resolved_path = self._resolve_path(file_path)

        # Handle new file creation
        if old_string == "":
            # Create new file
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)

            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(new_string)

            # Record the file edit
            record_file_edit(resolved_path, new_string)

            return f"Successfully created new file: {resolved_path}"
        
        # Edit existing file
        try:
            # Read current content
            with open(resolved_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Apply replacement
            if new_string == "":
                # Handle deletion - check if we need to remove trailing newline
                if (not old_string.endswith('\n') and
                    original_content.find(old_string + '\n') != -1):
                    updated_content = original_content.replace(old_string + '\n', new_string)
                else:
                    updated_content = original_content.replace(old_string, new_string)
            else:
                updated_content = original_content.replace(old_string, new_string)

            # Verify the replacement worked
            if updated_content == original_content:
                return "Error: Original and edited file match exactly. Failed to apply edit."

            # Write updated content
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            # Record the file edit
            record_file_edit(resolved_path, updated_content)

            # Generate result message with snippet
            snippet_info = self._get_snippet(original_content, old_string, new_string)

            result = f"The file {resolved_path} has been updated. Here's the result of the edit:\n"
            result += self._add_line_numbers(snippet_info['snippet'], snippet_info['start_line'])

            return result

        except Exception as e:
            return f"Error applying edit: {str(e)}"
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False
    
    def _get_snippet(self, original_content: str, old_string: str, new_string: str, 
                    context_lines: int = 4) -> Dict[str, Any]:
        """Get a snippet of the file showing the change with context."""
        
        # Find the replacement position
        before_replacement = original_content.split(old_string)[0]
        replacement_line = before_replacement.count('\n')
        
        # Create the new content
        new_content = original_content.replace(old_string, new_string)
        new_lines = new_content.split('\n')
        
        # Calculate snippet boundaries
        start_line = max(0, replacement_line - context_lines)
        end_line = min(len(new_lines), replacement_line + context_lines + new_string.count('\n') + 1)
        
        # Extract snippet
        snippet_lines = new_lines[start_line:end_line]
        snippet = '\n'.join(snippet_lines)
        
        return {
            'snippet': snippet,
            'start_line': start_line + 1  # Convert to 1-based line numbers
        }
    
    def _suggest_alternatives_for_large_edit(self, old_string: str, new_string: str) -> str:
        """Suggest alternative approaches for large string edits."""
        old_lines = old_string.count('\n') + 1
        new_lines = new_string.count('\n') + 1
        
        suggestions = []
        
        if old_lines > 20 or new_lines > 20:
            suggestions.append(
                "• Use MultiEditTool to break this into multiple smaller string replacements"
            )
        
        if len(old_string) > 3000 or len(new_string) > 3000:
            suggestions.append(
                "• Consider using FileWriteTool to rewrite the entire file if making extensive changes"
            )
        
        if old_lines > 10:
            suggestions.append(
                "• Break the edit into smaller, more focused string replacements"
            )
            suggestions.append(
                "• Use more specific context to make smaller, safer edits"
            )
        
        if suggestions:
            return "Alternative approaches for large edits:\n" + "\n".join(suggestions)
        
        return ""
    
    def _add_line_numbers(self, content: str, start_line: int = 1) -> str:
        """Add line numbers to content."""
        lines = content.split('\n')
        numbered_lines = []
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:6d}  {line}")
        
        return '\n'.join(numbered_lines)