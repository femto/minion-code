# Agent Development Guidelines

## UI Component Implementation

### Textual UI Components as React Simulation

This project uses **Textual UI components** to simulate React controls and interfaces. When implementing UI components:

- Use Textual widgets and containers to create React-like component structures
- Leverage Textual's reactive system to mimic React's state management
- Implement component composition patterns similar to React components
- Use Textual's CSS-like styling system for component appearance

### Logging Setup

For logging functionality, use the logger from the minion package:

```python
from minion.logs import logger
```

This provides centralized logging across all components and maintains consistency with the project's logging infrastructure.

## File System Usage

### MCP Filesystem Tools for External File Access

When developing agents that need to access files outside the current workspace, you can use **MCP filesystem tools** which provide broader file system access compared to standard workspace-restricted tools.

#### Available MCP Filesystem Tools

- `mcp_filesystem_read_text_file` - Read text files from anywhere on the system
- `mcp_filesystem_read_multiple_files` - Read multiple files simultaneously
- `mcp_filesystem_write_file` - Write files outside workspace
- `mcp_filesystem_list_directory` - List directories outside workspace
- `mcp_filesystem_search_files` - Search for files across the system
- `mcp_filesystem_get_file_info` - Get file metadata from any location

#### Usage Examples

```python
# Reading user's global config file
config_content = mcp_filesystem_read_text_file("~/.kiro/settings/mcp.json")

# Reading system files
system_info = mcp_filesystem_read_text_file("/etc/hosts")

# Listing user's home directory
home_contents = mcp_filesystem_list_directory("~")

# Writing to user's global settings
mcp_filesystem_write_file("~/.myapp/config.json", json_content)
```

#### When to Use MCP Filesystem Tools

- Accessing user's global configuration files (e.g., `~/.kiro/settings/`)
- Reading system configuration files
- Working with files in user's home directory
- Cross-workspace file operations
- Backup and sync operations across different locations

#### Security Considerations

- MCP filesystem tools have broader access - use responsibly
- Always validate file paths and permissions
- Be cautious when writing files outside the workspace
- Consider user privacy when accessing personal directories

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

Could you please provide the note you'd like me to transform for your KODING.md file?

_Added on 10/26/2025, 9:05:40 PM GMT+8_