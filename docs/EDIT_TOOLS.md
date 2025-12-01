# File Edit Tools Documentation

## Overview

This document describes the Python implementations of FileEditTool and MultiEditTool, based on their TypeScript counterparts from the Kode project. These tools provide robust file editing capabilities with built-in freshness tracking and conflict detection.

## FileEditTool

### Description
A tool for editing files by replacing a single occurrence of `old_string` with `new_string`. This tool is designed for precise, single-edit operations.

### Features
- **Single Edit Operations** - Replace one occurrence of text at a time
- **File Creation** - Create new files by using empty `old_string`
- **Freshness Tracking** - Integrates with FileFreshnessService for conflict detection
- **Binary File Detection** - Prevents editing of binary files
- **Jupyter Notebook Protection** - Redirects notebook edits to appropriate tools
- **Context Snippets** - Shows edited content with line numbers

### Usage

```python
from minion_code.tools.file_edit_tool import FileEditTool

tool = FileEditTool()

# Create new file
result = tool.forward(
    file_path="/path/to/new_file.py",
    old_string="",
    new_string="print('Hello, World!')"
)

# Edit existing file
result = tool.forward(
    file_path="/path/to/existing_file.py",
    old_string="old_text_to_replace",
    new_string="new_replacement_text"
)
```

### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Absolute path to the file to modify |
| `old_string` | string | Text to replace (must be unique in file) |
| `new_string` | string | Replacement text |

### Validation Rules

1. **Uniqueness** - `old_string` must appear exactly once in the file
2. **File Existence** - File must exist for edits (unless creating new file)
3. **Freshness** - File must not have been modified since last read
4. **Binary Protection** - Cannot edit binary files
5. **Notebook Protection** - Cannot edit `.ipynb` files

### Error Handling

- **String Not Found** - Returns error if `old_string` not in file
- **Multiple Matches** - Returns error if `old_string` appears multiple times
- **File Conflicts** - Returns error if file modified since last read
- **Binary Files** - Returns error for binary file edit attempts

## MultiEditTool

### Description
A tool for making multiple edits to a single file atomically. All edits are applied sequentially, and if any edit fails, the entire operation is aborted.

### Features
- **Atomic Operations** - All edits succeed or none are applied
- **Sequential Processing** - Edits applied in order provided
- **Replace All Option** - Can replace all occurrences of a string
- **File Creation** - Create new files with first edit having empty `old_string`
- **Comprehensive Validation** - Pre-validates all edits before applying any
- **Detailed Results** - Reports success/failure for each edit

### Usage

```python
from minion_code.tools.multi_edit_tool import MultiEditTool

tool = MultiEditTool()

# Multiple edits to existing file
edits = [
    {
        "old_string": "old_function_name",
        "new_string": "new_function_name",
        "replace_all": True  # Replace all occurrences
    },
    {
        "old_string": "print('debug')",
        "new_string": "logger.debug('debug')"
    }
]

result = tool.forward(file_path="/path/to/file.py", edits=edits)
```

### Input Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Absolute path to the file to modify |
| `edits` | array | Array of edit operations |

### Edit Object Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `old_string` | string | Yes | Text to replace |
| `new_string` | string | Yes | Replacement text |
| `replace_all` | boolean | No | Replace all occurrences (default: false) |

### Validation Rules

1. **Non-Empty Edits** - At least one edit must be provided
2. **New File Creation** - First edit must have empty `old_string` for new files
3. **String Existence** - All `old_string` values must exist in file
4. **No Duplicates** - `old_string` and `new_string` cannot be identical
5. **File Freshness** - File must not be modified since last read

### Sequential Processing

Edits are applied in the order provided:
1. Edit 1 is applied to original content
2. Edit 2 is applied to result of Edit 1
3. Edit 3 is applied to result of Edit 2
4. And so on...

**Important**: Later edits operate on the results of earlier edits, so plan accordingly.

## Integration with FileFreshnessService

Both tools integrate seamlessly with the FileFreshnessService:

### Automatic Event Emission
- **File Edit Events** - Emitted when files are successfully edited
- **Conflict Detection** - Automatic detection of external file modifications
- **Agent Tracking** - Distinguishes between agent and external modifications

### Event Data Structure

```python
{
    'file_path': '/path/to/file.py',
    'timestamp': 1634567890.123,
    'content_length': 1024,
    'source': 'agent'
}
```

### Usage with Event Listeners

```python
from minion_code.services import add_event_listener

def on_file_edited(context):
    print(f"File edited: {context.data['file_path']}")

def on_file_conflict(context):
    print(f"Conflict detected: {context.data['file_path']}")

add_event_listener('file:edited', on_file_edited)
add_event_listener('file:conflict', on_file_conflict)
```

## Best Practices

### FileEditTool
1. **Include Context** - Use sufficient context in `old_string` to ensure uniqueness
2. **Read First** - Always read files before editing to establish freshness baseline
3. **Handle Errors** - Check return values for error messages
4. **Use Absolute Paths** - Always provide absolute file paths

### MultiEditTool
1. **Plan Sequence** - Consider how earlier edits affect later ones
2. **Use Replace All** - Use `replace_all: true` for renaming variables/functions
3. **Validate First** - Tool pre-validates all edits before applying any
4. **Atomic Nature** - Remember that all edits succeed or all fail

### General Guidelines
1. **File Freshness** - Use `record_file_read()` after reading files
2. **Error Handling** - Always check tool return values for errors
3. **Event Monitoring** - Set up event listeners for comprehensive tracking
4. **Path Management** - Use absolute paths consistently

## Error Messages

### Common FileEditTool Errors
- `"No changes to make: old_string and new_string are exactly the same"`
- `"File does not exist"`
- `"String to replace not found in file"`
- `"Found N matches of the string to replace. For safety, this tool only supports replacing exactly one occurrence at a time"`
- `"File has been modified since last read. Read it again before editing"`

### Common MultiEditTool Errors
- `"At least one edit operation is required"`
- `"For new files, the first edit must have an empty old_string to create the file content"`
- `"Edit N: String to replace not found in file"`
- `"Edit N: old_string and new_string cannot be the same"`
- `"Error in edit N: [specific error message]"`

## Examples

See the `examples/` directory for complete usage examples:
- `edit_tools_example.py` - Basic tool functionality
- `integrated_edit_example.py` - Integration with freshness tracking

## Comparison with TypeScript Version

### Equivalent Functionality
- Same validation rules and error handling
- Compatible input/output formats
- Identical conflict detection logic
- Same atomic operation behavior for MultiEditTool

### Python-Specific Adaptations
- Uses Python file I/O and path handling
- Integrates with Python FileFreshnessService
- Python-style error handling and logging
- Type hints and Python coding conventions

### API Mapping

| TypeScript | Python |
|------------|--------|
| `FileEditTool.call()` | `FileEditTool.forward()` |
| `MultiEditTool.call()` | `MultiEditTool.forward()` |
| `validateInput()` | `_validate_input()` |
| `applyEdit()` | `_apply_edit()` |

## Dependencies

### Required
- Python 3.7+
- `minion.tools.BaseTool`
- `minion_code.services` (FileFreshnessService)

### Optional
- File watching capabilities (for enhanced freshness tracking)

## Performance Considerations

### FileEditTool
- Single file read/write operation
- Minimal memory usage for small to medium files
- O(n) complexity for string replacement

### MultiEditTool
- Single file read, multiple in-memory edits, single write
- More efficient than multiple FileEditTool calls
- Memory usage scales with file size and number of edits
- Pre-validation prevents partial application failures

## Security Considerations

1. **Path Validation** - Tools validate file paths and prevent directory traversal
2. **Binary Protection** - Prevents corruption of binary files
3. **Freshness Checking** - Prevents overwriting external changes
4. **Atomic Operations** - MultiEditTool ensures consistency
5. **Error Isolation** - Failed operations don't leave files in inconsistent states