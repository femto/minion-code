# Agent Development Guidelines

## File System Usage

### Workspace Directory Convention

When developing agents and tools that need to store persistent data or work with files, **always use `.minion_workspace`** as the default directory instead of other directory names.

#### Why .minion_workspace?

- **Consistency**: All agents and tools use the same workspace directory
- **Organization**: Keeps agent-related files separate from project files
- **Predictability**: Users know where to find agent-generated files
- **Cleanup**: Easy to identify and manage agent workspace files

#### Examples

**✅ Correct Usage:**
```python
# In todo storage
class TodoStorage:
    def __init__(self, storage_dir: str = ".minion_workspace"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

# In file tools
def save_agent_data(data, filename):
    workspace_dir = ".minion_workspace"
    os.makedirs(workspace_dir, exist_ok=True)
    filepath = os.path.join(workspace_dir, filename)
    # ... save data
```

**❌ Avoid:**
```python
# Don't use custom directory names
storage_dir = ".minion_todos"  # Too specific
storage_dir = ".agent_data"   # Not standardized
storage_dir = "temp_files"    # Not clearly agent-related
```

### File Naming Conventions

Within `.minion_workspace`, use descriptive filenames that include:
- Agent ID or identifier when relevant
- File type or purpose
- Appropriate file extensions

Examples:
- `todos_agent123.json` - Todo data for specific agent
- `todos_default.json` - Default agent todo storage
- `memory_default.json` - Default memory storage
- `logs_session_456.txt` - Session logs

### Implementation Notes

- Always create the `.minion_workspace` directory if it doesn't exist
- Handle file permissions and access errors gracefully
- Use appropriate file formats (JSON for structured data, TXT for logs)
- Include proper error handling for file operations

### Migration

If you have existing tools using other directory names:
1. Update the default directory to `.minion_workspace`
2. Consider migration logic for existing data
3. Update documentation and examples
4. Test with existing agent configurations
#
# Migration from .minion_todos

If you have existing data in `.minion_todos`, you can migrate it to `.minion_workspace`:

```bash
# Copy existing todo files
mkdir -p .minion_workspace
cp .minion_todos/*.json .minion_workspace/

# Verify migration
ls -la .minion_workspace/
```

The todo tools have been updated to use `.minion_workspace` by default, so existing todo data will continue to work after migration.