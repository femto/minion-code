#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File editing tool for advanced file manipulation operations
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from minion.tools import BaseTool


class FileEditTool(BaseTool):
    """Advanced file editing tool with search, replace, insert, and delete operations"""

    name = "file_edit"
    description = "Advanced file editing operations: search and replace, insert lines, delete lines, append content"
    readonly = False  # Editing tool, modifies system state
    inputs = {
        "file_path": {"type": "string", "description": "File path to edit"},
        "operation": {
            "type": "string", 
            "description": "Edit operation: 'replace', 'insert', 'delete', 'append', 'prepend'"
        },
        "search_text": {
            "type": "string", 
            "description": "Text to search for (required for 'replace' operation)",
            "nullable": True
        },
        "replacement_text": {
            "type": "string", 
            "description": "Replacement text (required for 'replace' operation)",
            "nullable": True
        },
        "content": {
            "type": "string", 
            "description": "Content to insert/append/prepend",
            "nullable": True
        },
        "line_number": {
            "type": "integer", 
            "description": "Line number for insert/delete operations (1-based)",
            "nullable": True
        },
        "line_count": {
            "type": "integer", 
            "description": "Number of lines to delete (for delete operation)",
            "nullable": True
        },
        "regex": {
            "type": "boolean", 
            "description": "Use regex for search (default: false)",
            "nullable": True
        },
        "case_sensitive": {
            "type": "boolean", 
            "description": "Case sensitive search (default: true)",
            "nullable": True
        }
    }
    output_type = "string"

    def forward(
        self, 
        file_path: str, 
        operation: str,
        search_text: Optional[str] = None,
        replacement_text: Optional[str] = None,
        content: Optional[str] = None,
        line_number: Optional[int] = None,
        line_count: Optional[int] = None,
        regex: Optional[bool] = False,
        case_sensitive: Optional[bool] = True
    ) -> str:
        """Execute file editing operation"""
        try:
            path = Path(file_path)
            
            # Validate operation
            valid_operations = ['replace', 'insert', 'delete', 'append', 'prepend']
            if operation not in valid_operations:
                return f"Error: Invalid operation '{operation}'. Valid operations: {', '.join(valid_operations)}"
            
            # Check if file exists for operations that require it
            if operation in ['replace', 'insert', 'delete'] and not path.exists():
                return f"Error: File does not exist - {file_path}"
            
            # Create file if it doesn't exist for append/prepend operations
            if operation in ['append', 'prepend'] and not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            
            # Execute the operation
            if operation == 'replace':
                return self._replace_text(path, search_text, replacement_text, regex, case_sensitive)
            elif operation == 'insert':
                return self._insert_lines(path, line_number, content)
            elif operation == 'delete':
                return self._delete_lines(path, line_number, line_count)
            elif operation == 'append':
                return self._append_content(path, content)
            elif operation == 'prepend':
                return self._prepend_content(path, content)
                
        except Exception as e:
            return f"Error during file edit operation: {str(e)}"

    def _replace_text(
        self, 
        path: Path, 
        search_text: str, 
        replacement_text: str, 
        use_regex: bool, 
        case_sensitive: bool
    ) -> str:
        """Replace text in file"""
        if not search_text:
            return "Error: search_text is required for replace operation"
        if replacement_text is None:
            replacement_text = ""
        
        try:
            # Read file content
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            original_content = content
            replacements = 0
            
            if use_regex:
                # Use regex replacement
                flags = 0 if case_sensitive else re.IGNORECASE
                content, replacements = re.subn(search_text, replacement_text, content, flags=flags)
            else:
                # Simple string replacement
                if case_sensitive:
                    replacements = content.count(search_text)
                    content = content.replace(search_text, replacement_text)
                else:
                    # Case-insensitive replacement
                    pattern = re.escape(search_text)
                    content, replacements = re.subn(pattern, replacement_text, content, flags=re.IGNORECASE)
            
            if replacements == 0:
                return f"No matches found for '{search_text}' in {path}"
            
            # Write back to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully replaced {replacements} occurrence(s) of '{search_text}' with '{replacement_text}' in {path}"
            
        except Exception as e:
            return f"Error during text replacement: {str(e)}"

    def _insert_lines(self, path: Path, line_number: int, content: str) -> str:
        """Insert content at specified line number"""
        if line_number is None:
            return "Error: line_number is required for insert operation"
        if content is None:
            content = ""
        
        try:
            # Read file lines
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Validate line number (1-based)
            if line_number < 1 or line_number > len(lines) + 1:
                return f"Error: Invalid line number {line_number}. File has {len(lines)} lines"
            
            # Insert content (convert to 0-based index)
            insert_index = line_number - 1
            new_lines = content.split('\n')
            
            # Add newline to each line except the last one if content doesn't end with newline
            formatted_lines = []
            for i, line in enumerate(new_lines):
                if i == len(new_lines) - 1 and not content.endswith('\n'):
                    formatted_lines.append(line + '\n')
                else:
                    formatted_lines.append(line + '\n' if not line.endswith('\n') else line)
            
            # Insert the new lines
            lines[insert_index:insert_index] = formatted_lines
            
            # Write back to file
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"Successfully inserted {len(new_lines)} line(s) at line {line_number} in {path}"
            
        except Exception as e:
            return f"Error during line insertion: {str(e)}"

    def _delete_lines(self, path: Path, line_number: int, line_count: int = 1) -> str:
        """Delete specified lines from file"""
        if line_number is None:
            return "Error: line_number is required for delete operation"
        if line_count is None:
            line_count = 1
        
        try:
            # Read file lines
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            # Validate line number and count
            if line_number < 1 or line_number > len(lines):
                return f"Error: Invalid line number {line_number}. File has {len(lines)} lines"
            
            # Calculate end line
            start_index = line_number - 1  # Convert to 0-based
            end_index = min(start_index + line_count, len(lines))
            actual_deleted = end_index - start_index
            
            # Delete lines
            del lines[start_index:end_index]
            
            # Write back to file
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"Successfully deleted {actual_deleted} line(s) starting from line {line_number} in {path}"
            
        except Exception as e:
            return f"Error during line deletion: {str(e)}"

    def _append_content(self, path: Path, content: str) -> str:
        """Append content to end of file"""
        if content is None:
            content = ""
        
        try:
            # Append content to file
            with open(path, 'a', encoding='utf-8') as f:
                if content and not content.endswith('\n'):
                    content += '\n'
                f.write(content)
            
            line_count = content.count('\n')
            return f"Successfully appended {len(content)} characters ({line_count} lines) to {path}"
            
        except Exception as e:
            return f"Error during content append: {str(e)}"

    def _prepend_content(self, path: Path, content: str) -> str:
        """Prepend content to beginning of file"""
        if content is None:
            content = ""
        
        try:
            # Read existing content
            existing_content = ""
            if path.exists():
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    existing_content = f.read()
            
            # Prepend content
            if content and not content.endswith('\n'):
                content += '\n'
            
            new_content = content + existing_content
            
            # Write back to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            line_count = content.count('\n')
            return f"Successfully prepended {len(content)} characters ({line_count} lines) to {path}"
            
        except Exception as e:
            return f"Error during content prepend: {str(e)}"