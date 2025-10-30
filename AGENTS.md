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
##
 Textual UI Component CSS Standards

### DEFAULT_CSS Convention

When creating custom Textual UI components, always use `DEFAULT_CSS` instead of `CSS` for styling. This follows Textual best practices and ensures proper CSS inheritance and component isolation.

#### Correct Implementation

```python
class CustomTextArea(TextArea):
    """Custom TextArea with adaptive height and key event posting"""
    
    DEFAULT_CSS = """
    CustomTextArea {
        height: auto;
        min-height: 1;
        max-height: 10;
        width: 1fr;
    }
    """
    
    # Component implementation...

class PromptInput(Container):
    """Main input component with mode switching"""
    
    DEFAULT_CSS = """
    PromptInput {
        dock: bottom;
        height: auto;
        min-height: 4;
        max-height: 15;
        margin: 1;
        border: solid white;
        padding: 1;
    }
    
    .mode-bash PromptInput {
        border: solid yellow;
    }
    
    .mode-koding PromptInput {
        border: solid cyan;
    }
    
    #mode_prefix {
        width: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    .help-text {
        color: gray;
        text-style: dim;
        margin-bottom: 1;
    }
    """
```

#### Why DEFAULT_CSS?

1. **Component Isolation**: `DEFAULT_CSS` ensures styles are scoped to the component
2. **Inheritance Control**: Allows proper CSS inheritance from parent components
3. **Override Safety**: Prevents accidental style conflicts with global CSS
4. **Textual Best Practice**: Follows official Textual framework conventions

#### Adaptive Height Components

For components that need to adapt their height based on content:

```python
DEFAULT_CSS = """
ComponentName {
    height: auto;          # Allow automatic height calculation
    min-height: 1;         # Minimum height (1 line for text inputs)
    max-height: 10;        # Maximum height before scrolling
    width: 1fr;            # Take available width
}
"""
```

#### Common CSS Patterns

**Input Components**:
```css
CustomInput {
    height: auto;
    min-height: 1;
    max-height: 10;
    width: 1fr;
    border: solid white;
}
```

**Container Components**:
```css
CustomContainer {
    dock: bottom;
    height: auto;
    min-height: 4;
    margin: 1;
    padding: 1;
}
```

**Mode-based Styling**:
```css
.mode-bash ComponentName {
    border: solid yellow;
}

.mode-koding ComponentName {
    border: solid cyan;
}
```

### Key Event Handling in Custom Components

When creating custom widgets that need to handle key events and communicate with parent components:

```python
class CustomWidget(Widget):
    class KeyPressed(Message):
        """Message posted when a key is pressed"""
        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key
    
    def on_key(self, event: Key) -> bool:
        # Post key event to parent for handling
        self.post_message(self.KeyPressed(event.key))
        
        # Handle specific keys
        if event.key == "enter":
            return True  # Prevent default handling
        
        return False  # Allow default handling
```

Parent component handling:
```python
@on(CustomWidget.KeyPressed)
def on_custom_widget_key(self, event: CustomWidget.KeyPressed):
    if event.key == "enter":
        # Handle enter key
        pass
```

This pattern ensures proper event propagation and component communication in Textual applications.
## Agent A
rchitecture Best Practices

### App-Level Agent Management

Agents should be managed at the **Application level**, not within UI components. This ensures proper separation of concerns and makes the architecture more maintainable.

#### Correct Architecture

```python
class REPLApp(App):
    """Main application manages agent lifecycle"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # App-level agent management
        self.agent = None
        self.agent_ready = False
    
    def compose(self) -> ComposeResult:
        # Pass agent to components as props
        repl_props_with_agent = {**self.repl_props, "agent": self.agent}
        yield REPL(**repl_props_with_agent)
    
    def on_mount(self):
        # Initialize agent at app level
        self.run_worker(self._initialize_agent())
    
    async def _initialize_agent(self):
        """Initialize agent at app level"""
        try:
            from minion_code import MinionCodeAgent
            self.agent = await MinionCodeAgent.create(
                name="App Assistant",
                llm="sonnet"
            )
            self.agent_ready = True
            
            # Update components with agent
            repl_component = self.query_one(REPL)
            repl_component.set_agent(self.agent)
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self.agent_ready = False

class REPL(Container):
    """UI component receives agent as prop"""
    
    def __init__(self, agent=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent  # Received from app level
    
    def set_agent(self, agent):
        """Set agent from app level"""
        self.agent = agent
    
    async def query_api(self, messages):
        """Use agent for queries"""
        if not self.agent:
            # Handle agent not ready case
            error_message = "❌ Agent not initialized yet"
            return
        
        # Use agent for processing
        response = await self.agent.run_async(user_input)
```

#### Why App-Level Management?

1. **Single Responsibility**: App manages infrastructure, components handle UI
2. **Lifecycle Control**: App controls when agent is created/destroyed
3. **Resource Sharing**: Multiple components can share the same agent
4. **Error Handling**: Centralized agent error handling
5. **Testing**: Easier to mock agent at app level

#### Anti-Pattern: Component-Level Agent

```python
# ❌ DON'T DO THIS
class REPL(Container):
    async def on_mount(self):
        # Wrong: UI component initializing agent
        self.agent = await MinionCodeAgent.create(...)
    
    async def query_api(self, messages):
        # Wrong: Agent lifecycle mixed with UI logic
        if not hasattr(self, 'agent'):
            await self._initialize_agent()
```

#### Benefits of Proper Architecture

- **Separation of Concerns**: UI components focus on presentation
- **Testability**: Easy to inject mock agents for testing
- **Scalability**: Can support multiple agents or agent switching
- **Maintainability**: Clear ownership of agent lifecycle
- **Performance**: Avoid duplicate agent initialization

### Agent Prop Passing Pattern

```python
# App level
def compose(self):
    component_props = {
        "agent": self.agent,
        "other_props": self.other_data
    }
    yield MyComponent(**component_props)

# Component level
class MyComponent(Container):
    def __init__(self, agent=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
    
    def set_agent(self, agent):
        """Allow dynamic agent updates"""
        self.agent = agent
```

This pattern ensures clean architecture and proper separation between infrastructure (agent) and presentation (UI components).