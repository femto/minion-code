#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Textual TUI with Minion CodeAgent

This example demonstrates:
1. A rich TUI interface using the Textual library
2. Integration with Minion CodeAgent and minion_code tools
3. Real-time chat interface with the AI agent
4. Tool usage visualization and history

Requirements:
    pip install textual rich

Key features:
- Rich TUI with panels, input, and scrollable output
- Real-time chat with CodeAgent
- Tool usage indicators
- Conversation history
- Help system
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import traceback

# Add project root and minion framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import (
        Header,
        Footer,
        Input,
        RichLog,
        Static,
        Button,
        TabbedContent,
        TabPane,
        DataTable,
        Pretty,
    )
    from textual.binding import Binding
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.syntax import Syntax
except ImportError:
    print("❌ Missing dependencies. Please install:")
    print("pip install textual rich")
    sys.exit(1)

from minion.agents import CodeAgent

# Import our custom tools
from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    WebSearchTool,
    WikipediaSearchTool,
    VisitWebpageTool,
    UserInputTool,
    FinalAnswerTool,
    TOOL_MAPPING,
)


# Using only minion_code tools - no additional raw functions needed


class MinionCodeAgentApp(App):
    """Advanced Textual TUI for Minion CodeAgent."""

    CSS = """
    .chat-container {
        height: 1fr;
    }
    
    .input-container {
        height: 3;
        dock: bottom;
    }
    
    .sidebar {
        width: 30;
        dock: left;
    }
    
    .main-content {
        width: 1fr;
    }
    
    RichLog {
        height: 1fr;
        scrollbar-gutter: stable;
    }
    
    Input {
        margin: 1;
    }
    
    DataTable {
        height: 1fr;
    }
    
    .status-bar {
        height: 1;
        background: $primary;
        color: $text;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+h", "toggle_help", "Help"),
        Binding("ctrl+t", "show_tools", "Tools"),
        Binding("ctrl+r", "clear_chat", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self.agent: Optional[CodeAgent] = None
        self.conversation_history = []
        self.agent_ready = False

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Horizontal():
            # Sidebar with tools and info
            with Vertical(classes="sidebar"):
                yield Static("🛠️ Tools", id="tools-header")
                yield DataTable(id="tools-table")
                yield Static("📊 Status", id="status-header")
                yield Static(
                    "🔧 Setting up agent...", id="status", classes="status-bar"
                )

            # Main chat area
            with Vertical(classes="main-content"):
                with TabbedContent():
                    with TabPane("💬 Chat", id="chat-tab"):
                        yield RichLog(id="chat-log", classes="chat-container")

                    with TabPane("📝 History", id="history-tab"):
                        yield RichLog(id="history-log")

                    with TabPane("❓ Help", id="help-tab"):
                        yield RichLog(id="help-log")

        # Input area at bottom
        with Container(classes="input-container"):
            yield Input(placeholder="Type your message here...", id="chat-input")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application."""
        # Setup chat log
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("🚀 Welcome to Minion CodeAgent TUI!")
        chat_log.write("🔧 Setting up AI agent with tools...")

        # Setup help
        self.setup_help()

        # Setup agent asynchronously
        asyncio.create_task(self.setup_agent())

    def setup_help(self):
        """Setup help content."""
        help_log = self.query_one("#help-log", RichLog)
        help_content = """
# Minion CodeAgent TUI Help

## 🤖 Chat Commands
Just type your message and the AI agent will respond using available tools.

## 📁 File Operations
- "Read the contents of README.md"
- "Write 'Hello World' to test.txt"
- "List files in the current directory"
- "Search for 'import' in all Python files"

## 💻 System Operations
- "Execute 'ls -la' command"
- "Run Python code: print(2 + 2)"
- "Get system information"
- "Calculate 15 + 27 * 3"

## 🌐 Web Operations
- "Search the web for Python tutorials"
- "Look up 'machine learning' on Wikipedia"

## ⌨️ Keyboard Shortcuts
- **Ctrl+C**: Quit application
- **Ctrl+H**: Toggle help
- **Ctrl+T**: Show tools
- **Ctrl+R**: Clear chat
- **Enter**: Send message

## 💡 Tips
- Be specific about what you want to accomplish
- The agent will choose the best tools for your task
- Check the Tools tab to see available capabilities
"""
        help_log.write(Markdown(help_content))

    async def setup_agent(self):
        """Setup the CodeAgent with tools."""
        try:
            # Get all tools
            custom_tools = [
                FileReadTool(),
                FileWriteTool(),
                BashTool(),
                GrepTool(),
                GlobTool(),
                LsTool(),
                PythonInterpreterTool(),
                WebSearchTool(),
                WikipediaSearchTool(),
                VisitWebpageTool(),
                UserInputTool(),
                FinalAnswerTool(),
            ]

            all_tools = custom_tools

            # Create agent
            self.agent = await CodeAgent.create(
                name="Minion Code Assistant", llm="gpt-4o-mini", tools=all_tools
            )

            self.agent_ready = True

            # Update UI
            await self.update_status("✅ Agent ready!")
            await self.update_tools_table()

            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write("✅ AI agent is ready! Start chatting below.")
            chat_log.write(f"🛠️ Loaded {len(self.agent.tools)} tools")

        except Exception as e:
            await self.update_status(f"❌ Setup failed: {str(e)}")
            chat_log = self.query_one("#chat-log", RichLog)
            chat_log.write(f"❌ Error setting up agent: {e}")

    async def update_status(self, message: str):
        """Update status bar."""
        status = self.query_one("#status", Static)
        status.update(message)

    async def update_tools_table(self):
        """Update the tools table."""
        if not self.agent:
            return

        table = self.query_one("#tools-table", DataTable)
        table.add_columns("Tool", "Type")

        for tool in self.agent.tools:
            readonly_status = "🔒 RO" if getattr(tool, "readonly", None) else "✏️ RW"
            table.add_row(tool.name, readonly_status)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if not self.agent_ready:
            await self.update_status("⏳ Agent not ready yet...")
            return

        user_input = event.value.strip()
        if not user_input:
            return

        # Clear input
        event.input.value = ""

        # Add user message to chat
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(Panel(user_input, title="👤 You", border_style="blue"))

        # Update status
        await self.update_status("🤖 AI is thinking...")

        try:
            # Get agent response
            response = await self.agent.run_async(user_input)

            # Add agent response to chat
            chat_log.write(
                Panel(
                    Markdown(response.answer),
                    title="🤖 Assistant",
                    border_style="green",
                )
            )

            # Add to history
            self.conversation_history.append((user_input, response.answer))
            await self.update_history()

            await self.update_status("✅ Ready for next message")

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            chat_log.write(Panel(error_msg, title="❌ Error", border_style="red"))
            await self.update_status("❌ Error occurred")

    async def update_history(self):
        """Update conversation history."""
        history_log = self.query_one("#history-log", RichLog)
        history_log.clear()

        for i, (user_msg, agent_response) in enumerate(self.conversation_history, 1):
            history_log.write(f"--- Conversation {i} ---")
            history_log.write(Panel(user_msg, title="👤 You", border_style="blue"))
            history_log.write(
                Panel(
                    Markdown(agent_response), title="🤖 Assistant", border_style="green"
                )
            )

    def action_toggle_help(self) -> None:
        """Toggle help tab."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "help-tab"

    def action_show_tools(self) -> None:
        """Show tools information."""
        chat_log = self.query_one("#chat-log", RichLog)
        if self.agent:
            tools_info = f"🛠️ Available Tools ({len(self.agent.tools)} total):\n"
            for tool in self.agent.tools:
                readonly = "🔒" if getattr(tool, "readonly", None) else "✏️"
                tools_info += f"  {readonly} {tool.name}: {tool.description}\n"
            chat_log.write(Panel(tools_info, title="🛠️ Tools", border_style="yellow"))

    def action_clear_chat(self) -> None:
        """Clear chat log."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        chat_log.write("🗑️ Chat cleared. Start a new conversation!")


async def main():
    """Main function to run the TUI."""
    try:
        app = MinionCodeAgentApp()
        await app.run_async()
    except Exception as e:
        print(f"❌ Error running TUI: {e}")
        traceback.print_exc()


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
