# MinionCodeAgent

An enhanced AI code assistant built on the Minion framework, pre-configured with rich development tools, optimized for code development tasks.

## Features

- 🤖 **Intelligent Code Assistant**: Pre-configured AI agent designed for programming tasks
- 🔧 **Rich Toolset**: Automatically includes 12+ tools for file operations, command execution, web search, etc.
- ⚡ **Ready to Use**: One-line creation, no complex configuration needed
- 📝 **Conversation History**: Built-in conversation history tracking and management
- 🎯 **Optimized Prompts**: System prompts optimized for code development tasks
- 🛡️ **Security by Design**: Built-in security checks to prevent dangerous operations
- 🔌 **ACP Protocol Support**: Seamless integration with ACP clients like Zed editor

## Installation

### Option 1: Install from source (recommended for development)

```bash
# Clone the dependency repository
git clone https://github.com/femto/minion

# Clone this repository
git clone https://github.com/femto/minion-code

# Enter the directory
cd minion-code

# Install minion dependency
pip install -e ../minion

# Install minion-code
pip install -e .
```

In this case, `MINION_ROOT` is located at `../minion`

### Option 2: Direct installation (recommended for general use)

```bash
# Clone this repository
git clone https://github.com/femto/minion-code
cd minion-code

# Install dependencies
pip install minionx

# Install minion-code
pip install -e .
```

In this case, `MINION_ROOT` is located at the current startup location

On startup, the actual path of `MINION_ROOT` will be displayed:
```
2025-11-13 12:21:48.042 | INFO     | minion.const:get_minion_root:44 - MINION_ROOT set to: <some_path>
```

# LLM Configuration

Please refer to https://github.com/femto/minion?tab=readme-ov-file#get-started

Make sure the config file is in `MINION_ROOT/config/config.yaml` or `~/.minion/config.yaml`

## Quick Start

### CLI Usage

```bash
# Basic usage
mcode

# Specify working directory
mcode --dir /path/to/project

# Specify LLM model
mcode --model gpt-4o
mcode --model claude-3-5-sonnet

# Enable verbose output
mcode --verbose

# Load additional tools using MCP config file
mcode --config mcp.json

# Combined usage
mcode --dir /path/to/project --model gpt-4o --config mcp.json --verbose
```

### Configuration

Configure the default LLM model used by minion-code:

```bash
# View current default model
mcode model

# Set default model (saved to ~/.minion/minion-code.json)
mcode model gpt-4o
mcode model claude-3-5-sonnet

# Clear default model (use built-in default)
mcode model --clear
```

**Model Priority:**
1. CLI `--model` argument (highest priority)
2. Config file `~/.minion/minion-code.json`
3. Built-in default (lowest priority)

### ACP Protocol Support

MinionCodeAgent supports the [ACP (Agent Communication Protocol)](https://agentcommunicationprotocol.dev/) protocol, enabling integration with ACP-compatible clients like Zed editor.

```bash
# Start ACP server (stdio mode)
mcode acp

# Specify working directory
mcode acp --dir /path/to/project

# Specify LLM model
mcode acp --model gpt-4o

# Enable verbose logging
mcode acp --verbose

# Skip tool permission prompts (auto-allow all tools)
mcode acp --dangerously-skip-permissions

# Combined usage
mcode acp --dir /path/to/project --model claude-3-5-sonnet --verbose
```

#### Using with Zed Editor

Add the following to Zed's `settings.json`:

```json
{
  "agent_servers": {
    
    "minion-code": {
      "type": "custom",
      "command": "/path/to/mcode",
      "args": [
        "acp"
      ],
      "env": {}
    }
  }
}
```

#### Permission Management

In ACP mode, tool calls will request user permission:
- **Allow once**: Allow this time only
- **Always allow**: Permanently allow this tool (saved to `~/.minion/sessions/`)
- **Reject**: Deny execution

### Programming Interface

```python
import asyncio
from minion_code import MinionCodeAgent

async def main():
    # Create AI code assistant with all tools auto-configured
    agent = await MinionCodeAgent.create(
        name="My Code Assistant",
        llm="gpt-4.1"
    )

    # Chat with the AI assistant
    response = await agent.run_async("List files in current directory")
    print(response.answer)

    response = await agent.run_async("Read the README.md file")
    print(response.answer)

asyncio.run(main())
```

### Custom Configuration

```python
# Custom system prompt and working directory
agent = await MinionCodeAgent.create(
    name="Python Expert",
    llm="gpt-4.1",
    system_prompt="You are a specialized Python developer assistant.",
    workdir="/path/to/project",
    additional_tools=[MyCustomTool()]
)
```

### View Available Tools

```python
# Print tools summary
agent.print_tools_summary()

# Get tools info
tools_info = agent.get_tools_info()
for tool in tools_info:
    print(f"{tool['name']}: {tool['description']}")
```

## Built-in Tools

MinionCodeAgent automatically includes the following tool categories:

### 📁 File and Directory Tools
- **FileReadTool**: Read file contents
- **FileWriteTool**: Write files
- **GrepTool**: Search text in files
- **GlobTool**: File pattern matching
- **LsTool**: List directory contents

### 💻 System and Execution Tools
- **BashTool**: Execute shell commands
- **PythonInterpreterTool**: Execute Python code

### 🌐 Network and Search Tools
- **WebSearchTool**: Web search
- **WikipediaSearchTool**: Wikipedia search
- **VisitWebpageTool**: Visit webpages

### 🔧 Other Tools
- **UserInputTool**: User input
- **TodoWriteTool**: Task management write
- **TodoReadTool**: Task management read

## MCP Tool Integration

MinionCodeAgent supports loading additional tools via MCP (Model Context Protocol) configuration files.

### MCP Configuration File Format

Create a JSON configuration file (e.g., `mcp.json`):

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "/tmp"],
      "disabled": true,
      "autoApprove": ["read_file", "list_directory"]
    },
    "git": {
      "command": "uvx", 
      "args": ["mcp-server-git"],
      "disabled": false,
      "autoApprove": ["git_status", "git_log"]
    }
  }
}
```

### Configuration Options

- `command`: Command to start the MCP server
- `args`: List of command arguments
- `env`: Environment variables (optional)
- `disabled`: Whether to disable this server (default: false)
- `autoApprove`: List of tool names to auto-approve (optional)

### Using MCP Configuration

```bash
# Use MCP config file
minion-code --config examples/mcp_config.json

# View loaded tools (including MCP tools)
# In CLI, type: tools
```

### Using MCP Tools in Programming Interface

```python
from minion_code.utils.mcp_loader import load_mcp_tools
from pathlib import Path

async def main():
    # Load MCP tools
    mcp_tools = await load_mcp_tools(Path("mcp.json"))

    # Create agent with MCP tools
    agent = await MinionCodeAgent.create(
        name="Enhanced Assistant",
        llm="gpt-4o-mini",
        additional_tools=mcp_tools
    )
```

## Conversation History Management

```python
# Get conversation history
history = agent.get_conversation_history()
for entry in history:
    print(f"User: {entry['user_message']}")
    print(f"Agent: {entry['agent_response']}")

# Clear history
agent.clear_conversation_history()
```

## Comparison with Original Implementation

### Before (Complex manual configuration)
```python
# Need to manually import and configure all tools
from minion_code.tools import (
    FileReadTool, FileWriteTool, BashTool,
    GrepTool, GlobTool, LsTool,
    PythonInterpreterTool, WebSearchTool,
    # ... more tools
)

# Manually create tool instances
custom_tools = [
    FileReadTool(),
    FileWriteTool(),
    BashTool(),
    # ... more tool configuration
]

# Manually set system prompt
SYSTEM_PROMPT = "You are a coding agent..."

# Create agent (~50 lines of code)
agent = await CodeAgent.create(
    name="Minion Code Assistant",
    llm="gpt-4o-mini",
    system_prompt=SYSTEM_PROMPT,
    tools=custom_tools,
)
```

### Now (Using MinionCodeAgent)
```python
# One line of code completes all setup
agent = await MinionCodeAgent.create(
    name="Minion Code Assistant",
    llm="gpt-4o-mini"
)
```

## API Reference

### MinionCodeAgent.create()

```python
async def create(
    name: str = "Minion Code Assistant",
    llm: str = "gpt-4o-mini",
    system_prompt: Optional[str] = None,
    workdir: Optional[Union[str, Path]] = None,
    additional_tools: Optional[List[Any]] = None,
    **kwargs
) -> MinionCodeAgent
```

**Parameters:**
- `name`: Agent name
- `llm`: LLM model to use
- `system_prompt`: Custom system prompt (optional)
- `workdir`: Working directory (optional, defaults to current directory)
- `additional_tools`: List of additional tools (optional)
- `**kwargs`: Other parameters passed to CodeAgent.create()

### Instance Methods

- `run_async(message: str)`: Run agent asynchronously
- `run(message: str)`: Run agent synchronously
- `get_conversation_history()`: Get conversation history
- `clear_conversation_history()`: Clear conversation history
- `get_tools_info()`: Get tools info
- `print_tools_summary()`: Print tools summary

### Properties

- `agent`: Access underlying CodeAgent instance
- `tools`: Get available tools list
- `name`: Get agent name

## Security Features

- **Command Execution Safety**: BashTool prohibits dangerous commands (e.g., `rm -rf`, `sudo`, etc.)
- **Python Execution Restrictions**: PythonInterpreterTool runs in a restricted environment, allowing only safe built-in functions and specified modules
- **File Access Control**: All file operations have path validation and error handling

## Examples

See complete examples in the `examples/` directory:

- `simple_code_agent.py`: Basic MinionCodeAgent usage example
- `simple_tui.py`: Simplified TUI implementation
- `advanced_textual_tui.py`: Advanced TUI interface (using Textual library)
- `minion_agent_tui.py`: Original complex implementation (for comparison)
- `mcp_config.json`: MCP configuration file example
- `test_mcp_config.py`: MCP configuration loading test
- `demo_mcp_cli.py`: MCP CLI feature demo

Run examples:

```bash
# Basic usage example
python examples/simple_code_agent.py

# Simple TUI
python examples/simple_tui.py

# Advanced TUI (requires textual: pip install textual rich)
python examples/advanced_textual_tui.py

# Test MCP config loading
python examples/test_mcp_config.py

# MCP CLI feature demo
python examples/demo_mcp_cli.py
```

## Documentation

- [LLM Configuration Guide](LLM_CONFIG.md) - How to configure Large Language Models (LLM)
- [MCP Tool Integration Guide](docs/MCP_GUIDE.md) - Detailed MCP configuration and usage guide

## Contributing

Issues and Pull Requests are welcome to improve this project!

## License

MIT License