# Todo File Utilities Documentation

## Overview

The todo file utilities provide a centralized way to manage todo file paths and operations across the minion_code project. This refactoring extracts common todo file handling logic from both the todo storage system and the file freshness service.

## Motivation

Previously, todo file path generation was duplicated between:
- `TodoStorage._get_file_path()` in `minion_code/utils/todo_storage.py`
- Hard-coded path logic in `minion_code/services/file_freshness_service.py`

This refactoring centralizes the logic in `minion_code/utils/todo_file_utils.py` for better maintainability and consistency.

## API Reference

### Core Functions

#### `get_todo_file_path(agent_id, storage_dir)`
```python
def get_todo_file_path(agent_id: Optional[str] = None, storage_dir: str = ".minion_workspace") -> str:
    """
    Get the file path for todo storage for a specific agent.
    
    Args:
        agent_id: Agent identifier. If None, uses default.
        storage_dir: Directory where todo files are stored.
        
    Returns:
        Full path to the todo file for the agent.
    """
```

**Examples:**
```python
# Default agent
path = get_todo_file_path()  # ".minion_workspace/todos_default.json"

# Specific agent
path = get_todo_file_path("agent123")  # ".minion_workspace/todos_agent123.json"

# Custom storage directory
path = get_todo_file_path("agent123", "/custom/path")  # "/custom/path/todos_agent123.json"
```

#### `get_default_storage_dir()`
```python
def get_default_storage_dir() -> str:
    """Get the default storage directory for todo files."""
```

Returns `".minion_workspace"` - the standard directory for minion workspace files.

#### `ensure_storage_dir_exists(storage_dir)`
```python
def ensure_storage_dir_exists(storage_dir: Optional[str] = None) -> str:
    """
    Ensure the storage directory exists and return its path.
    
    Args:
        storage_dir: Directory path. If None, uses default.
        
    Returns:
        The storage directory path.
    """
```

### File Discovery Functions

#### `list_todo_files(storage_dir)`
```python
def list_todo_files(storage_dir: Optional[str] = None) -> list[str]:
    """
    List all todo files in the storage directory.
    
    Args:
        storage_dir: Directory to search. If None, uses default.
        
    Returns:
        List of todo file paths.
    """
```

#### `extract_agent_id_from_todo_file(file_path)`
```python
def extract_agent_id_from_todo_file(file_path: str) -> Optional[str]:
    """
    Extract agent ID from a todo file path.
    
    Args:
        file_path: Path to the todo file.
        
    Returns:
        Agent ID if found, None if it's the default file.
    """
```

**Examples:**
```python
extract_agent_id_from_todo_file("todos_agent123.json")  # "agent123"
extract_agent_id_from_todo_file("todos_default.json")   # None
extract_agent_id_from_todo_file("not_a_todo.txt")       # None
```

#### `is_todo_file(file_path)`
```python
def is_todo_file(file_path: str) -> bool:
    """
    Check if a file path is a todo file.
    
    Args:
        file_path: Path to check.
        
    Returns:
        True if it's a todo file, False otherwise.
    """
```

## File Naming Convention

Todo files follow a consistent naming pattern:

| Agent ID | Filename | Description |
|----------|----------|-------------|
| `None` (default) | `todos_default.json` | Default agent todos |
| `"agent123"` | `todos_agent123.json` | Specific agent todos |
| `"my_agent"` | `todos_my_agent.json` | Named agent todos |

## Integration Points

### TodoStorage Integration

The `TodoStorage` class now uses the centralized utilities:

```python
# Before
class TodoStorage:
    def _get_file_path(self, agent_id: Optional[str] = None) -> str:
        filename = f"todos_{agent_id}.json" if agent_id else "todos_default.json"
        return os.path.join(self.storage_dir, filename)

# After
class TodoStorage:
    def _get_file_path(self, agent_id: Optional[str] = None) -> str:
        return get_todo_file_path(agent_id, self.storage_dir)
```

### FileFreshnessService Integration

The file freshness service now uses the utilities for todo file watching:

```python
# Before
def start_watching_todo_file(self, agent_id: str, file_path: Optional[str] = None):
    if file_path is None:
        file_path = f"todos/{agent_id}.json"  # Hard-coded logic

# After
def start_watching_todo_file(self, agent_id: str, file_path: Optional[str] = None):
    if file_path is None:
        file_path = get_todo_file_path(agent_id)  # Centralized logic
```

## Usage Examples

### Basic Usage

```python
from minion_code.utils.todo_file_utils import get_todo_file_path, list_todo_files

# Get path for specific agent
agent_path = get_todo_file_path("my_agent")
print(f"Agent todo file: {agent_path}")

# List all todo files
todo_files = list_todo_files()
print(f"Found {len(todo_files)} todo files")
```

### Integration with File Watching

```python
from minion_code.services import start_watching_todo_file
from minion_code.utils.todo_file_utils import get_todo_file_path

# Start watching using centralized path logic
agent_id = "my_agent"
start_watching_todo_file(agent_id)  # Uses get_todo_file_path internally

# Or provide custom path
custom_path = get_todo_file_path(agent_id, "/custom/storage")
start_watching_todo_file(agent_id, custom_path)
```

### File Discovery and Management

```python
from minion_code.utils.todo_file_utils import (
    list_todo_files, 
    extract_agent_id_from_todo_file,
    is_todo_file
)

# Find all agents with todo files
todo_files = list_todo_files()
agents = []
for file_path in todo_files:
    if is_todo_file(file_path):
        agent_id = extract_agent_id_from_todo_file(file_path)
        agents.append(agent_id or "default")

print(f"Agents with todos: {agents}")
```

## Benefits

### 1. Centralized Logic
- Single source of truth for todo file path generation
- Consistent naming conventions across the project
- Easier to modify file naming scheme in the future

### 2. Improved Maintainability
- No more duplicated path generation logic
- Clear separation of concerns
- Easier testing and validation

### 3. Enhanced Functionality
- File discovery capabilities
- Agent ID extraction from file paths
- File type validation

### 4. Better Integration
- Seamless integration with existing TodoStorage
- Enhanced FileFreshnessService capabilities
- Consistent behavior across all components

## Migration Guide

### For TodoStorage Users
No changes required - the API remains the same. The implementation now uses centralized utilities internally.

### For FileFreshnessService Users
No changes required - the service now automatically uses proper todo file paths.

### For Direct File Path Users
Replace manual path construction with utility functions:

```python
# Before
todo_file = f".minion_workspace/todos_{agent_id}.json"

# After
from minion_code.utils.todo_file_utils import get_todo_file_path
todo_file = get_todo_file_path(agent_id)
```

## Testing

The utilities include comprehensive tests covering:
- Path generation for various agent IDs
- Directory creation and management
- File listing and discovery
- Agent ID extraction
- File type validation
- Integration with existing services

Run tests with:
```bash
python examples/todo_file_utils_example.py
```

## Future Enhancements

Potential improvements:
1. **Custom Naming Schemes**: Support for different file naming patterns
2. **Storage Backends**: Support for different storage systems (database, cloud)
3. **File Validation**: Validate todo file format and structure
4. **Migration Tools**: Utilities for migrating between storage formats
5. **Backup/Restore**: Automated backup and restore capabilities

## Dependencies

- **Standard Library**: `os`, `typing`
- **Project Dependencies**: None (pure utility functions)

## Compatibility

- **Python Version**: 3.7+
- **Backward Compatible**: All existing APIs remain unchanged
- **Cross-Platform**: Works on Windows, macOS, and Linux