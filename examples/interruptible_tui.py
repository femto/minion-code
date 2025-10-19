#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interruptible TUI without requiring admin privileges

This example shows how to add task interruption support using standard input
without requiring global keyboard hooks.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code import MinionCodeAgent
from minion_code.commands import command_registry
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt


class InterruptibleTUI:
    """TUI with task interruption support using standard input."""
    
    def __init__(self):
        self.agent = None
        self.running = True
        self.console = Console()
        self.current_task = None
        self.task_cancelled = False
        self.interrupt_requested = False
        
    async def setup(self):
        """Setup the agent."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("🔧 Setting up MinionCodeAgent...", total=None)
            
            self.agent = await MinionCodeAgent.create(
                name="Interruptible Code Assistant",
                llm="claude",
            )
            
            progress.update(task, completed=True)
        
        success_panel = Panel(
            f"✅ Agent ready with [bold green]{len(self.agent.tools)}[/bold green] tools!\n"
            f"⚠️  [bold yellow]Press Ctrl+C during processing to interrupt tasks[/bold yellow]",
            title="[bold green]Setup Complete[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
    
    def show_help(self):
        """Show help information."""
        help_table = Table(title="📚 Interruptible TUI Help", show_header=True, header_style="bold blue")
        help_table.add_column("Command/Key", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        
        help_table.add_row("help", "Show this help")
        help_table.add_row("tools", "List available tools")
        help_table.add_row("history", "Show conversation history")
        help_table.add_row("clear", "Clear history")
        help_table.add_row("quit", "Exit")
        help_table.add_row("Ctrl+C", "Interrupt current task or exit")
        
        self.console.print(help_table)
        self.console.print("\n💡 [italic]Just type your message to chat with the AI agent![/italic]")
        self.console.print("⚠️  [italic]During task processing, press Ctrl+C to interrupt the current task[/italic]")
    
    async def process_input_with_interrupt(self, user_input: str):
        """Process user input with interrupt support."""
        self.task_cancelled = False
        self.interrupt_requested = False
        
        try:
            # Create the actual processing task
            async def processing_task():
                response = await self.agent.run_async(user_input)
                return response
            
            # Start the task
            self.current_task = asyncio.create_task(processing_task())
            
            # Monitor for cancellation while task runs
            while not self.current_task.done():
                if self.interrupt_requested:
                    self.current_task.cancel()
                    try:
                        await self.current_task
                    except asyncio.CancelledError:
                        pass
                    return None
                
                await asyncio.sleep(0.1)  # Check every 100ms
            
            # Get the result
            response = await self.current_task
            return response
            
        except asyncio.CancelledError:
            return None
        finally:
            self.current_task = None
    
    def interrupt_current_task(self):
        """Interrupt the current running task."""
        if self.current_task and not self.current_task.done():
            self.interrupt_requested = True
            self.console.print("\n⚠️  [bold yellow]Task interruption requested...[/bold yellow]")
    
    async def process_input(self, user_input: str):
        """Process user input."""
        user_input = user_input.strip()
        
        # Check if it's a command (starts with /)
        if user_input.startswith('/'):
            await self.process_command(user_input)
            return
        
        # Process with agent
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description} (Ctrl+C to interrupt)"),
                console=self.console,
            ) as progress:
                task = progress.add_task("🤖 Processing...", total=None)
                
                response = await self.process_input_with_interrupt(user_input)
                
                progress.update(task, completed=True)
            
            if response is None:
                # Task was cancelled
                cancelled_panel = Panel(
                    "⚠️  [bold yellow]Task was interrupted![/bold yellow]",
                    title="[bold yellow]Interrupted[/bold yellow]",
                    border_style="yellow"
                )
                self.console.print(cancelled_panel)
                return
            
            # Display agent response with rich formatting
            if "```" in response.answer:
                agent_content = Markdown(response.answer)
            else:
                agent_content = response.answer
            
            response_panel = Panel(
                agent_content,
                title="🤖 [bold green]Agent Response[/bold green]",
                border_style="green"
            )
            self.console.print(response_panel)
            
        except KeyboardInterrupt:
            # Handle Ctrl+C during processing
            self.interrupt_current_task()
            cancelled_panel = Panel(
                "⚠️  [bold yellow]Task interrupted by user![/bold yellow]",
                title="[bold yellow]Interrupted[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(cancelled_panel)
        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error: {e}[/bold red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
    
    async def process_command(self, command_input: str):
        """Process a command input."""
        # Remove the leading /
        command_input = command_input[1:] if command_input.startswith('/') else command_input
        
        # Split command and arguments
        parts = command_input.split(' ', 1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Get command class
        command_class = command_registry.get_command(command_name)
        if not command_class:
            error_panel = Panel(
                f"❌ [bold red]Unknown command: /{command_name}[/bold red]\n"
                f"💡 [italic]Use '/help' to see available commands[/italic]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
            return
        
        # Create and execute command
        try:
            command_instance = command_class(self.console, self.agent)
            
            # Special handling for quit command
            if command_name in ["quit", "exit", "q", "bye"]:
                command_instance._tui_instance = self
            
            await command_instance.execute(args)
            
        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error executing command /{command_name}: {e}[/bold red]",
                title="[bold red]Command Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
    
    def show_tools(self):
        """Show available tools in a beautiful table."""
        if not self.agent or not self.agent.tools:
            self.console.print("❌ No tools available")
            return
        
        tools_table = Table(title="🛠️ Available Tools", show_header=True, header_style="bold magenta")
        tools_table.add_column("Tool Name", style="cyan", no_wrap=True)
        tools_table.add_column("Description", style="white")
        tools_table.add_column("Type", style="yellow")
        
        for tool in self.agent.tools:
            tool_type = "Read-only" if getattr(tool, 'readonly', False) else "Read-write"
            tools_table.add_row(
                tool.name,
                tool.description[:60] + "..." if len(tool.description) > 60 else tool.description,
                tool_type
            )
        
        self.console.print(tools_table)
    
    def show_history(self):
        """Show conversation history in a beautiful format."""
        if not self.agent:
            return
            
        history = self.agent.get_conversation_history()
        if not history:
            no_history_panel = Panel(
                "📝 [italic]No conversation history yet.[/italic]",
                title="[bold blue]History[/bold blue]",
                border_style="blue"
            )
            self.console.print(no_history_panel)
            return
        
        history_panel = Panel(
            f"📝 [bold blue]Conversation History ({len(history)} messages)[/bold blue]",
            border_style="blue"
        )
        self.console.print(history_panel)
        
        for i, entry in enumerate(history[-5:], 1):  # Show last 5 messages
            # User message
            user_panel = Panel(
                entry['user_message'][:200] + "..." if len(entry['user_message']) > 200 else entry['user_message'],
                title=f"👤 [bold cyan]You (Message {len(history)-5+i})[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(user_panel)
            
            # Agent response
            agent_response = entry['agent_response'][:200] + "..." if len(entry['agent_response']) > 200 else entry['agent_response']
            agent_panel = Panel(
                agent_response,
                title="🤖 [bold green]Agent[/bold green]",
                border_style="green"
            )
            self.console.print(agent_panel)
            self.console.print()  # Add spacing
    
    async def run(self):
        """Run the TUI."""
        # Welcome banner
        welcome_panel = Panel(
            "🚀 [bold blue]Interruptible MinionCodeAgent TUI[/bold blue]\n"
            "💡 [italic]Use '/help' for commands or just chat with the agent![/italic]\n"
            "⚠️  [italic]Press Ctrl+C during processing to interrupt tasks[/italic]\n"
            "🛑 [italic]Type '/quit' to exit[/italic]",
            title="[bold magenta]Welcome[/bold magenta]",
            border_style="magenta"
        )
        self.console.print(welcome_panel)
        
        await self.setup()
        
        while self.running:
            try:
                # Use rich prompt for better input experience
                user_input = Prompt.ask(
                    "\n[bold cyan]👤 You[/bold cyan]",
                    console=self.console
                ).strip()
                
                if user_input:
                    await self.process_input(user_input)
                    
            except (EOFError, KeyboardInterrupt):
                # Handle Ctrl+C at input prompt
                if self.current_task and not self.current_task.done():
                    # If there's a running task, interrupt it
                    self.interrupt_current_task()
                else:
                    # If no running task, exit
                    goodbye_panel = Panel(
                        "\n👋 [bold yellow]Goodbye![/bold yellow]",
                        title="[bold red]Exit[/bold red]",
                        border_style="red"
                    )
                    self.console.print(goodbye_panel)
                    break


async def main():
    """Main function."""
    tui = InterruptibleTUI()
    await tui.run()


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()