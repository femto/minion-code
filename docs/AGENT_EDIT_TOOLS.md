# MinionCodeAgent Edit Tools Integration

## Overview

The MinionCodeAgent now includes enhanced file editing capabilities through the integration of FileEditToolNew and MultiEditTool. These tools provide robust, freshness-tracked file editing with conflict detection and atomic operations.

## Available Edit Tools

### 1. FileEditTool (Original)
- **Name**: `file_edit`
- **Type**: Advanced file operations
- **Use Cases**: Search/replace, insert lines, delete lines, append content
- **Features**: Regex support, line-based operations

### 2. FileEditToolNew (StringEditTool)
- **Name**: `string_edit`
- **Type**: String replacement with freshness tracking
- **Use Cases**: Precise single-string replacements
- **Features**: Conflict detection, binary file protection, context snippets

### 3. MultiEditTool
- **Name**: `multi_edit`
- **Type**: Atomic multi-edit operations
- **Use Cases**: Multiple changes to same file
- **Features**: Atomic operations, replace_all option, sequential processing

## Agent Integration

### System Prompt Guidelines

The agent is configured with specific guidelines for edit tool selection:

```
- For edits, choose the right tool: file_edit for single changes, multi_edit for multiple changes to same file.
- Always read files before editing to establish freshness tracking.
- Apply the smallest change that satisfies the request.
```

### Tool Selection Logic

The agent automatically selects the appropriate edit tool based on the task:

| Scenario | Recommended Tool | Reason |
|----------|------------------|---------|
| Single string replacement | `string_edit` | Freshness tracking, conflict detection |
| Multiple changes to same file | `multi_edit` | Atomic operations, efficiency |
| Line-based operations | `file_edit` (original) | Advanced line manipulation |
| Cross-file changes | Multiple `string_edit` calls | Independent file operations |

## Usage Examples

### Creating an Agent with Edit Tools

```python
from minion_code.agents.code_agent import MinionCodeAgent

# Create agent with all edit tools
agent = await MinionCodeAgent.create(
    name="Code Editor Agent",
    llm="gpt-4o-mini"
)

# Check available tools
tools_info = agent.get_tools_info()
edit_tools = [tool for tool in tools_info if 'edit' in tool['name'].lower()]
print(f"Available edit tools: {[tool['name'] for tool in edit_tools]}")
```

### Agent Workflow Examples

#### Single Edit Task
```python
# Agent will automatically use string_edit for single replacements
response = await agent.run_async(
    "Replace 'TODO: implement' with the actual implementation in main.py"
)
```

#### Multi-Edit Task
```python
# Agent will automatically use multi_edit for multiple changes
response = await agent.run_async(
    "Add logging, error handling, and docstrings to calculator.py"
)
```

#### Cross-File Task
```python
# Agent will use multiple string_edit calls
response = await agent.run_async(
    "Update the function names in both utils.py and main.py to use snake_case"
)
```

## Event Monitoring

The agent automatically integrates with the FileFreshnessService event system:

```python
from minion_code.services import add_event_listener

def on_file_edited(context):
    print(f"Agent edited: {context.data['file_path']}")

def on_file_conflict(context):
    print(f"Conflict detected: {context.data['file_path']}")

add_event_listener('file:edited', on_file_edited)
add_event_listener('file:conflict', on_file_conflict)

# Now agent operations will trigger these events
agent = await MinionCodeAgent.create()
```

## Best Practices

### For Agent Users

1. **Be Specific**: Clearly describe what changes you want
   ```python
   # Good
   "Replace the print statement in line 15 with a logger.info call"
   
   # Better
   "In main.py, replace 'print(\"Starting process\")' with 'logger.info(\"Starting process\")'"
   ```

2. **Provide Context**: Help the agent understand the scope
   ```python
   # Good
   "Add error handling to all functions in utils.py"
   
   # Better  
   "Add try-catch blocks to handle ValueError in all functions in utils.py"
   ```

3. **Trust Tool Selection**: The agent will choose the right tool
   ```python
   # Let the agent decide
   "Make these three changes to config.py: update version, add new setting, fix typo"
   ```

### For Agent Developers

1. **File Reading**: Always read files before editing
   ```python
   # The agent automatically does this, but for manual tool use:
   from minion_code.services import record_file_read
   record_file_read("file.py")
   ```

2. **Error Handling**: Check tool responses
   ```python
   result = tool.forward(file_path="test.py", old_string="old", new_string="new")
   if "Error:" in result:
       # Handle error appropriately
   ```

3. **Event Integration**: Monitor file operations
   ```python
   # Set up monitoring before agent operations
   add_event_listener('file:edited', your_handler)
   ```

## Tool Comparison

### When to Use Each Tool

| Tool | Best For | Advantages | Limitations |
|------|----------|------------|-------------|
| FileEditTool (original) | Line operations, regex | Flexible operations | No freshness tracking |
| StringEditTool | Single replacements | Conflict detection | Single edit only |
| MultiEditTool | Multiple changes | Atomic operations | Same file only |

### Performance Considerations

- **Single Edit**: StringEditTool is optimal
- **Multiple Edits**: MultiEditTool is more efficient than multiple single edits
- **Cross-File**: Multiple StringEditTool calls are necessary
- **Large Files**: All tools handle large files efficiently

## Configuration

### Custom System Prompts

You can customize the agent's edit behavior:

```python
custom_prompt = """
You are a careful code editor. Always:
1. Read files before editing
2. Use multi_edit for multiple changes to same file
3. Prefer small, focused changes
4. Validate changes don't break syntax
"""

agent = await MinionCodeAgent.create(
    system_prompt=custom_prompt
)
```

### Additional Tools

Add custom edit tools alongside the defaults:

```python
from your_tools import CustomEditTool

agent = await MinionCodeAgent.create(
    additional_tools=[CustomEditTool()]
)
```

## Troubleshooting

### Common Issues

1. **File Conflicts**
   ```
   Error: File has been modified since last read
   ```
   **Solution**: Agent will automatically re-read the file

2. **String Not Found**
   ```
   Error: String to replace not found in file
   ```
   **Solution**: Agent will adjust the search string or read file again

3. **Multiple Matches**
   ```
   Error: Found N matches of the string to replace
   ```
   **Solution**: Agent will add more context to make the match unique

### Debug Information

Enable debug logging to see tool selection:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now you'll see which tools the agent chooses
agent = await MinionCodeAgent.create()
```

## Migration Guide

### From Original FileEditTool

If you were using the original FileEditTool directly:

```python
# Old way
tool = FileEditTool()
result = tool.forward(
    file_path="test.py",
    operation="replace",
    search_text="old",
    replacement_text="new"
)

# New way (agent handles tool selection)
agent = await MinionCodeAgent.create()
response = await agent.run_async(
    "In test.py, replace 'old' with 'new'"
)
```

### Benefits of Agent Integration

1. **Automatic Tool Selection**: Agent chooses the right tool
2. **Freshness Tracking**: Automatic conflict detection
3. **Error Recovery**: Agent can retry with different approaches
4. **Context Awareness**: Agent understands file relationships

## Examples

See the `examples/` directory for complete usage examples:
- `agent_with_edit_tools.py` - Basic integration testing
- `agent_edit_demo.py` - Comprehensive demonstration
- `integrated_edit_example.py` - Manual tool usage with events

## Future Enhancements

Planned improvements:
- **Smart Conflict Resolution**: Automatic merge conflict handling
- **Batch Operations**: Cross-file atomic operations
- **Undo/Redo**: Operation history and rollback
- **Preview Mode**: Show changes before applying
- **Template Support**: Common edit patterns