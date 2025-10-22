#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual UI for MinionCodeAgent

A modern terminal user interface using the Textual library for the MinionCodeAgent.
Features include:
- Real-time chat interface
- Tool management
- Conversation history
- Task interruption support
- Rich text formatting
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Input, Button, Static, DataTable, 
    TabbedContent, TabPane, Log, ProgressBar, Label
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from textual import events
from textual.screen import ModalScreen
from rich.text import Text
from rich.markdown import Markdown
from rich.console import Console
from rich.panel import Panel

from minion_code import MinionCodeAgent
from minion_code.utils.mcp_loader import MCPToolsLoader


class ToolsModal(ModalScreen):
    """Modal screen to display available tools."""
    
    def __init__(self, tools: List):
        super().__init__()
        self.tools = tools
    
    def compose(self) -> ComposeResult:
        with Container(id="tools-modal"):
            yield Static("🛠️ Available Tools", classes="modal-title")
            
            table = DataTable()
            table.add_columns("Name", "Description", "Type")
            
            for tool in self.tools:
                tool_type = "Read-only" if getattr(tool, 'readonly', False) else "Read-write"
                description = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
                table.add_row(tool.name, description, tool_type)
            
            yield table
            yield Button("Close", id="close-tools", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-tools":
            self.dismiss()


class HistoryModal(ModalScreen):
    """Modal screen to display conversation history."""
    
    def __init__(self, history: List):
        super().__init__()
        self.history = history
    
    def compose(self) -> ComposeResult:
        with Container(id="history-modal"):
            yield Static("📝 Conversation History", classes="modal-title")
            
            with ScrollableContainer():
                if not self.history:
                    yield Static("No conversation history yet.", classes="empty-history")
                else:
                    for i, entry in enumerate(self.history[-10:], 1):  # Show last 10
                        yield Static(f"👤 You (Message {len(self.history)-10+i}):", classes="user-label")
                        yield Static(entry['user_message'][:200] + "..." if len(entry['user_message']) > 200 else entry['user_message'], classes="user-message")
                        yield Static("🤖 Agent:", classes="agent-label")
                        yield Static(entry['agent_response'][:200] + "..." if len(entry['agent_response']) > 200 else entry['agent_response'], classes="agent-message")
                        yield Static("", classes="message-separator")
            
            yield Button("Close", id="close-history", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-history":
            self.dismiss()


class MinionCodeTUI(App):
    """Textual UI for MinionCodeAgent."""
    
    CSS = """
    #main-container {
        layout: vertical;
        height: 100%;
    }
    
    #chat-container {
        layout: vertical;
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #chat-log {
        height: 1fr;
        scrollbar-gutter: stable;
        border: solid $accent;
        margin: 1;
    }
    
    #input-container {
        layout: horizontal;
        height: 3;
        margin: 1;
    }
    
    #user-input {
        width: 1fr;
        margin-right: 1;
    }
    
    #send-button {
        width: 10;
    }
    
    #status-bar {
        height: 3;
        background: $surface;
        border: solid $primary;
        margin: 1;
    }
    
    #tools-modal, #history-modal {
        align: center middle;
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
    }
    
    .modal-title {
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
        height: 3;
        content-align: center middle;
    }
    
    .user-message {
        background: $primary 20%;
        margin: 1;
        padding: 1;
    }
    
    .agent-message {
        background: $success 20%;
        margin: 1;
        padding: 1;
    }
    
    .user-label {
        text-style: bold;
        color: $primary;
        margin-top: 1;
    }
    
    .agent-label {
        text-style: bold;
        color: $success;
        margin-top: 1;
    }
    
    .message-separator {
        height: 1;
    }
    
    .empty-history {
        text-align: center;
        text-style: italic;
        margin: 2;
    }
    
    .status-text {
        text-align: center;
        content-align: center middle;
    }
    
    .error-message {
        color: $error;
        text-style: bold;
    }
    
    .success-message {
        color: $success;
        text-style: bold;
    }
    
    .processing-message {
        color: $warning;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+t", "show_tools", "Tools"),
        Binding("ctrl+h", "show_history", "History"),
        Binding("ctrl+c", "interrupt", "Interrupt"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
    ]
    
    agent_status = reactive("Initializing...")
    processing = reactive(False)
    
    def __init__(self, mcp_config: Optional[Path] = None, verbose: bool = False):
        super().__init__()
        self.agent = None
        self.mcp_config = mcp_config
        self.verbose = verbose
        self.mcp_tools = []
        self.mcp_loader = None
        self.current_task = None
        self.interrupt_requested = False
    
    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        
        with Container(id="main-container"):
            with Container(id="chat-container"):
                yield Log(id="chat-log", auto_scroll=True)
            
            with Horizontal(id="input-container"):
                yield Input(placeholder="Type your message here...", id="user-input")
                yield Button("Send", id="send-button", variant="primary")
            
            yield Static(self.agent_status, id="status-bar", classes="status-text")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application."""
        self.title = "🤖 MinionCodeAgent TUI"
        self.sub_title = "AI-powered code assistant"
        
        # Start agent setup
        asyncio.create_task(self.setup_agent())
        
        # Focus on input
        self.query_one("#user-input").focus()
    
    async def setup_agent(self) -> None:
        """Setup the MinionCodeAgent."""
        try:
            self.agent_status = "🔧 Setting up MinionCodeAgent..."
            
            # Load MCP tools if config provided
            if self.mcp_config:
                self.agent_status = "🔌 Loading MCP tools..."
                try:
                    self.mcp_loader = MCPToolsLoader(self.mcp_config)
                    self.mcp_loader.load_config()
                    self.mcp_tools = await self.mcp_loader.load_all_tools()
                    
                    if self.mcp_tools:
                        self.log_message(f"✅ Loaded {len(self.mcp_tools)} MCP tools", "success")
                    else:
                        self.log_message("⚠️ No MCP tools loaded", "warning")
                        
                except Exception as e:
                    self.log_message(f"❌ Failed to load MCP tools: {e}", "error")
            
            # Create agent
            self.agent_status = "🤖 Creating agent..."
            self.agent = await MinionCodeAgent.create(
                name="TUI Code Assistant",
                llm="sonnet",
                additional_tools=self.mcp_tools if self.mcp_tools else None
            )
            
            # Update status
            total_tools = len(self.agent.tools)
            mcp_count = len(self.mcp_tools)
            builtin_count = total_tools - mcp_count
            
            self.agent_status = f"✅ Ready! {total_tools} tools available"
            
            # Log welcome message
            welcome_msg = f"🚀 MinionCodeAgent TUI Ready!\n"
            welcome_msg += f"🛠️ Total tools: {total_tools}"
            if mcp_count > 0:
                welcome_msg += f" (Built-in: {builtin_count}, MCP: {mcp_count})"
            welcome_msg += f"\n💡 Type your message and press Enter or click Send"
            welcome_msg += f"\n⚠️ Use Ctrl+C to interrupt tasks, Ctrl+Q to quit"
            
            self.log_message(welcome_msg, "success")
            
        except Exception as e:
            self.agent_status = f"❌ Setup failed: {e}"
            self.log_message(f"❌ Failed to setup agent: {e}", "error")
    
    def log_message(self, message: str, msg_type: str = "info") -> None:
        """Add a message to the chat log."""
        chat_log = self.query_one("#chat-log", Log)
        
        if msg_type == "error":
            chat_log.write(Text(message, style="bold red"))
        elif msg_type == "success":
            chat_log.write(Text(message, style="bold green"))
        elif msg_type == "warning":
            chat_log.write(Text(message, style="bold yellow"))
        elif msg_type == "user":
            chat_log.write(Text(f"👤 You: {message}", style="bold cyan"))
        elif msg_type == "agent":
            # Handle markdown in agent responses
            if "```" in message:
                chat_log.write(Text(f"🤖 Agent:", style="bold green"))
                # For now, just display as text - could enhance with proper markdown rendering
                chat_log.write(Text(message, style="green"))
            else:
                chat_log.write(Text(f"🤖 Agent: {message}", style="bold green"))
        else:
            chat_log.write(Text(message))
    
    async def process_user_input(self, message: str) -> None:
        """Process user input with the agent."""
        if not self.agent:
            self.log_message("❌ Agent not ready yet", "error")
            return
        
        if not message.strip():
            return
        
        # Log user message
        self.log_message(message, "user")
        
        # Check for commands
        if message.startswith('/'):
            await self.process_command(message)
            return
        
        # Process with agent
        try:
            self.processing = True
            self.agent_status = "🤖 Processing... (Ctrl+C to interrupt)"
            self.interrupt_requested = False
            
            # Create processing task
            async def processing_task():
                response = await self.agent.run_async(message)
                return response
            
            self.current_task = asyncio.create_task(processing_task())
            
            # Monitor for interruption
            while not self.current_task.done():
                if self.interrupt_requested:
                    self.current_task.cancel()
                    try:
                        await self.current_task
                    except asyncio.CancelledError:
                        pass
                    self.log_message("⚠️ Task interrupted by user", "warning")
                    return
                
                await asyncio.sleep(0.1)
            
            # Get result
            response = await self.current_task
            self.log_message(response.answer, "agent")
            
        except asyncio.CancelledError:
            self.log_message("⚠️ Task was cancelled", "warning")
        except Exception as e:
            self.log_message(f"❌ Error: {e}", "error")
        finally:
            self.processing = False
            self.current_task = None
            total_tools = len(self.agent.tools) if self.agent else 0
            self.agent_status = f"✅ Ready! {total_tools} tools available"
    
    async def process_command(self, command: str) -> None:
        """Process a command."""
        command = command[1:].lower().strip()  # Remove leading /
        
        if command == "help":
            help_msg = """📚 Available Commands:
/help - Show this help
/tools - Show available tools  
/history - Show conversation history
/clear - Clear chat log
/quit - Exit application

🔧 Keyboard Shortcuts:
Ctrl+T - Show tools
Ctrl+H - Show history  
Ctrl+L - Clear chat
Ctrl+C - Interrupt current task
Ctrl+Q - Quit application"""
            self.log_message(help_msg, "info")
            
        elif command == "tools":
            await self.action_show_tools()
            
        elif command == "history":
            await self.action_show_history()
            
        elif command == "clear":
            await self.action_clear_chat()
            
        elif command in ["quit", "exit", "q"]:
            await self.action_quit()
            
        else:
            self.log_message(f"❌ Unknown command: /{command}. Use /help for available commands.", "error")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "user-input":
            message = event.value
            event.input.clear()
            asyncio.create_task(self.process_user_input(message))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "send-button":
            user_input = self.query_one("#user-input", Input)
            message = user_input.value
            user_input.clear()
            asyncio.create_task(self.process_user_input(message))
    
    async def action_show_tools(self) -> None:
        """Show available tools."""
        if not self.agent:
            self.log_message("❌ Agent not ready yet", "error")
            return
        
        await self.push_screen(ToolsModal(self.agent.tools))
    
    async def action_show_history(self) -> None:
        """Show conversation history."""
        if not self.agent:
            self.log_message("❌ Agent not ready yet", "error")
            return
        
        history = self.agent.get_conversation_history()
        await self.push_screen(HistoryModal(history))
    
    async def action_clear_chat(self) -> None:
        """Clear the chat log."""
        chat_log = self.query_one("#chat-log", Log)
        chat_log.clear()
        self.log_message("🧹 Chat cleared", "info")
    
    async def action_interrupt(self) -> None:
        """Interrupt current task."""
        if self.current_task and not self.current_task.done():
            self.interrupt_requested = True
            self.log_message("⚠️ Interruption requested...", "warning")
        else:
            self.log_message("ℹ️ No task to interrupt", "info")
    
    async def action_quit(self) -> None:
        """Quit the application."""
        if self.mcp_loader:
            try:
                await self.mcp_loader.close()
            except Exception:
                pass
        
        self.exit()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MinionCodeAgent Textual UI")
    parser.add_argument("--config", "-c", type=str, help="Path to MCP configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    mcp_config = None
    if args.config:
        mcp_config = Path(args.config)
        if not mcp_config.exists():
            print(f"❌ MCP config file does not exist: {args.config}")
            sys.exit(1)
    
    app = MinionCodeTUI(mcp_config=mcp_config, verbose=args.verbose)
    app.run()


if __name__ == "__main__":
    main()