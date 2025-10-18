#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple TUI using MinionCodeAgent

This example shows how the new MinionCodeAgent class simplifies
the TUI implementation by handling all the tool setup internally.

Compare this with minion_agent_tui.py to see the reduction in boilerplate code.
"""

import asyncio
import sys
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


class SimpleTUI:
    """Simplified TUI using MinionCodeAgent."""
    
    def __init__(self):
        self.agent = None
        self.running = True
        self.console = Console()
    
    async def setup(self):
        """Setup the agent."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("🔧 Setting up MinionCodeAgent...", total=None)
            
            # Much simpler setup - no manual tool configuration needed
            self.agent = await MinionCodeAgent.create(
                name="Simple Code Assistant",
                llm="gpt-4.1",
            )
            
            progress.update(task, completed=True)
        
        success_panel = Panel(
            f"✅ Agent ready with [bold green]{len(self.agent.tools)}[/bold green] tools!",
            title="[bold green]Setup Complete[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
    
    def show_help(self):
        """Show help information."""
        help_table = Table(title="📚 Simple TUI Help", show_header=True, header_style="bold blue")
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        
        help_table.add_row("help", "Show this help")
        help_table.add_row("tools", "List available tools")
        help_table.add_row("history", "Show conversation history")
        help_table.add_row("clear", "Clear history")
        help_table.add_row("quit", "Exit")
        
        self.console.print(help_table)
        self.console.print("\n💡 [italic]Just type your message to chat with the AI agent![/italic]")
    
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
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                task = progress.add_task("🤖 Processing...", total=None)
                response = await self.agent.run_async(user_input)
                progress.update(task, completed=True)
            
            # Display agent response with rich formatting
            if "```" in response.answer:
                # If response contains code blocks, render as markdown
                agent_content = Markdown(response.answer)
            else:
                agent_content = response.answer
            
            response_panel = Panel(
                agent_content,
                title="🤖 [bold green]Agent Response[/bold green]",
                border_style="green"
            )
            self.console.print(response_panel)
            
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
            "🚀 [bold blue]Simple MinionCodeAgent TUI[/bold blue]\n"
            "💡 [italic]Use '/help' for commands or just chat with the agent![/italic]\n"
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
                goodbye_panel = Panel(
                    "\n👋 [bold yellow]Goodbye![/bold yellow]",
                    title="[bold red]Exit[/bold red]",
                    border_style="red"
                )
                self.console.print(goodbye_panel)
                break


async def main():
    """Main function."""
    tui = SimpleTUI()
    await tui.run()


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()