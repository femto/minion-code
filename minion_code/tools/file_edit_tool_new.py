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
    
    name = "string_edit"
    description = "A tool for editing files by replacing old_string with new_string with freshness tracking"
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
    
    def forward(self, file_path: str, old_string: str, new_string: str) -> str:
        """Execute file edit operation."""
        try:
            # Validate inputs
            validation_result = self._validate_input(file_path, old_string, new_string)
            if not validation_result["valid"]:
                return f"Error: {validation_result['message']}"
            
            # Apply the edit
            result = self._apply_edit(file_path, old_string, new_string)
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
        
        # Resolve absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Handle new file creation
        if not os.path.exists(file_path) and old_string == "":
            return {"valid": True}
        
        # Check if file exists for existing file edits
        if not os.path.exists(file_path):
            return {
                "valid": False,
                "message": "File does not exist."
            }
        
        # Check if it's a Jupyter notebook
        if file_path.endswith('.ipynb'):
            return {
                "valid": False,
                "message": "File is a Jupyter Notebook. Use NotebookEdit tool instead."
            }
        
        # Check file freshness (if we have tracking)
        try:
            freshness_result = check_file_freshness(file_path)
            if freshness_result.conflict:
                return {
                    "valid": False,
                    "message": "File has been modified since last read. Read it again before editing."
                }
        except Exception:
            # If freshness checking fails, continue with basic validation
            pass
        
        # Check if file is binary
        if self._is_binary_file(file_path):
            return {
                "valid": False,
                "message": "Cannot edit binary files."
            }
        
        # For existing files, validate old_string exists and is unique
        if old_string != "":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
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
        
        # Resolve absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Handle new file creation
        if old_string == "":
            # Create new file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_string)
            
            # Record the file edit
            record_file_edit(file_path, new_string)
            
            return f"Successfully created new file: {file_path}"
        
        # Edit existing file
        try:
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
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
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Record the file edit
            record_file_edit(file_path, updated_content)
            
            # Generate result message with snippet
            snippet_info = self._get_snippet(original_content, old_string, new_string)
            
            result = f"The file {file_path} has been updated. Here's the result of the edit:\n"
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
    
    def _add_line_numbers(self, content: str, start_line: int = 1) -> str:
        """Add line numbers to content."""
        lines = content.split('\n')
        numbered_lines = []
        
        for i, line in enumerate(lines):
            line_num = start_line + i
            numbered_lines.append(f"{line_num:6d}  {line}")
        
        return '\n'.join(numbered_lines)