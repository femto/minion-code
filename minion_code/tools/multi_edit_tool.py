#!/usr/bin/env python3
"""
Multi-edit tool based on TypeScript MultiEditTool implementation.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from minion.tools import BaseTool
from minion_code.services import record_file_read, record_file_edit, check_file_freshness


class MultiEditTool(BaseTool):
    """
    A tool for making multiple edits to a single file atomically.
    Based on the TypeScript MultiEditTool implementation.
    """
    
    name = "multi_edit"
    description = "A tool for making multiple edits to a single file in one operation"
    readonly = False
    
    inputs = {
        "file_path": {
            "type": "string",
            "description": "The absolute path to the file to modify"
        },
        "edits": {
            "type": "array",
            "description": "Array of edit operations to perform sequentially",
            "items": {
                "type": "object",
                "properties": {
                    "old_string": {
                        "type": "string",
                        "description": "The text to replace"
                    },
                    "new_string": {
                        "type": "string", 
                        "description": "The text to replace it with"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences of old_string (default: false)"
                    }
                },
                "required": ["old_string", "new_string"]
            }
        }
    }
    output_type = "string"
    
    def forward(self, file_path: str, edits: List[Dict[str, Any]]) -> str:
        """Execute multi-edit operation."""
        try:
            # Validate inputs
            validation_result = self._validate_input(file_path, edits)
            if not validation_result["valid"]:
                return f"Error: {validation_result['message']}"
            
            # Apply all edits atomically
            result = self._apply_multi_edit(file_path, edits)
            return result
            
        except Exception as e:
            return f"Error during multi-edit: {str(e)}"
    
    def _validate_input(self, file_path: str, edits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate input parameters."""
        
        # Check if we have edits
        if not edits or len(edits) == 0:
            return {
                "valid": False,
                "message": "At least one edit operation is required."
            }
        
        # Resolve absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Check if it's a Jupyter notebook
        if file_path.endswith('.ipynb'):
            return {
                "valid": False,
                "message": "File is a Jupyter Notebook. Use NotebookEdit tool instead."
            }
        
        # Handle new file creation
        if not os.path.exists(file_path):
            # For new files, ensure parent directory can be created
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except Exception as e:
                    return {
                        "valid": False,
                        "message": f"Cannot create parent directory: {str(e)}"
                    }
            
            # For new files, first edit must create the file (empty old_string)
            if len(edits) == 0 or edits[0].get("old_string", "") != "":
                return {
                    "valid": False,
                    "message": "For new files, the first edit must have an empty old_string to create the file content."
                }
        else:
            # For existing files, check freshness
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
            
            # Pre-validate that all old_strings exist in the file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                
                for i, edit in enumerate(edits):
                    old_string = edit.get("old_string", "")
                    if old_string != "" and old_string not in current_content:
                        return {
                            "valid": False,
                            "message": f"Edit {i + 1}: String to replace not found in file: \"{old_string[:100]}{'...' if len(old_string) > 100 else ''}\""
                        }
                        
            except UnicodeDecodeError:
                return {
                    "valid": False,
                    "message": "Cannot read file - appears to be binary or has encoding issues."
                }
        
        # Validate each edit
        for i, edit in enumerate(edits):
            old_string = edit.get("old_string", "")
            new_string = edit.get("new_string", "")
            
            if old_string == new_string:
                return {
                    "valid": False,
                    "message": f"Edit {i + 1}: old_string and new_string cannot be the same"
                }
        
        return {"valid": True}
    
    def _apply_multi_edit(self, file_path: str, edits: List[Dict[str, Any]]) -> str:
        """Apply all edits to the file atomically."""
        
        # Resolve absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Read current file content (or empty for new files)
        file_exists = os.path.exists(file_path)
        
        if file_exists:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()
            except UnicodeDecodeError:
                return "Error: Cannot read file - appears to be binary or has encoding issues."
        else:
            current_content = ""
            # Ensure parent directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Apply all edits sequentially
        modified_content = current_content
        applied_edits = []
        
        for i, edit in enumerate(edits):
            old_string = edit.get("old_string", "")
            new_string = edit.get("new_string", "")
            replace_all = edit.get("replace_all", False)
            
            try:
                result = self._apply_content_edit(
                    modified_content, old_string, new_string, replace_all
                )
                modified_content = result["new_content"]
                applied_edits.append({
                    "edit_index": i + 1,
                    "success": True,
                    "old_string": old_string[:100] + ("..." if len(old_string) > 100 else ""),
                    "new_string": new_string[:100] + ("..." if len(new_string) > 100 else ""),
                    "occurrences": result["occurrences"]
                })
                
            except Exception as e:
                # If any edit fails, abort the entire operation
                error_message = str(e)
                return f"Error in edit {i + 1}: {error_message}"
        
        # Write the modified content
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
        except Exception as e:
            return f"Error writing file: {str(e)}"
        
        # Record the file edit
        record_file_edit(file_path, modified_content)
        
        # Generate result summary
        operation = "create" if not file_exists else "update"
        summary = f"Successfully applied {len(edits)} edits to {file_path}"
        
        # Add details about each edit
        details = []
        for edit_info in applied_edits:
            details.append(
                f"Edit {edit_info['edit_index']}: Replaced {edit_info['occurrences']} occurrence(s)"
            )
        
        if details:
            summary += "\n" + "\n".join(details)
        
        return summary
    
    def _apply_content_edit(self, content: str, old_string: str, new_string: str, 
                           replace_all: bool = False) -> Dict[str, Any]:
        """Apply a single content edit."""
        
        if replace_all:
            # Replace all occurrences
            import re
            # Escape special regex characters in old_string
            escaped_old = re.escape(old_string)
            pattern = re.compile(escaped_old)
            matches = pattern.findall(content)
            occurrences = len(matches)
            new_content = pattern.sub(new_string, content)
            
            return {
                "new_content": new_content,
                "occurrences": occurrences
            }
        else:
            # Replace single occurrence
            if old_string in content:
                new_content = content.replace(old_string, new_string, 1)  # Replace only first occurrence
                return {
                    "new_content": new_content,
                    "occurrences": 1
                }
            else:
                raise Exception(f"String not found: {old_string[:50]}...")
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False