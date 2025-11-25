#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple CLI interface for MinionCodeAgent using Typer (Console-based)

This is the original console-based CLI interface, preserved for compatibility.
For the modern TUI interface, use cli.py or the 'repl' command.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code import MinionCodeAgent
from minion_code.commands import command_registry
from minion_code.utils.mcp_loader import MCPToolsLoader
from minion_code.adapters import RichOutputAdapter

app = typer.Typer(
    name="minion-code-simple",
    help="🤖 MinionCodeAgent Simple CLI - Console-based interface",
    add_completion=False,
    rich_markup_mode="rich"
)


class InterruptibleCLI:
    """CLI with task interruption support using standard input."""
    
    def __init__(self, verbose: bool = False, mcp_config: Optional[Path] = None):
        self.agent = None
        self.running = True
        self.console = Console()
        self.verbose = verbose
        self.mcp_config = mcp_config
        self.mcp_tools = []
        self.mcp_loader = None
        self.current_task = None
        self.task_cancelled = False
        self.interrupt_requested = False

        # Create output adapter for commands
        self.output_adapter = RichOutputAdapter(self.console)
        
    async def setup(self):
        """Setup the agent."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            # Load MCP tools if config provided
            mcp_task = None
            if self.mcp_config:
                mcp_task = progress.add_task("🔌 Loading MCP tools...", total=None)
                try:
                    self.mcp_loader = MCPToolsLoader(self.mcp_config)
                    self.mcp_loader.load_config()
                    self.mcp_tools = await self.mcp_loader.load_all_tools()
                    
                    if self.mcp_tools:
                        self.console.print(f"✅ Loaded {len(self.mcp_tools)} MCP tools")
                    else:
                        server_info = self.mcp_loader.get_server_info()
                        if server_info:
                            self.console.print(f"📋 Found {len(server_info)} MCP server(s) configured")
                            for name, info in server_info.items():
                                status = "disabled" if info['disabled'] else "enabled"
                                self.console.print(f"  - {name}: {info['command']} ({status})")
                        else:
                            self.console.print("⚠️  No MCP servers found in config")
                    
                    progress.update(mcp_task, completed=True)
                except Exception as e:
                    self.console.print(f"❌ Failed to load MCP tools: {e}")
                    if self.verbose:
                        import traceback
                        self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            
            agent_task = progress.add_task("🔧 Setting up MinionCodeAgent...", total=None)
            
            self.agent = await MinionCodeAgent.create(
                name="CLI Code Assistant",
                llm="sonnet",
                additional_tools=self.mcp_tools if self.mcp_tools else None
            )
            
            progress.update(agent_task, completed=True)
        
        # Show setup summary
        total_tools = len(self.agent.tools)
        mcp_count = len(self.mcp_tools)
        builtin_count = total_tools - mcp_count
        
        summary_text = f"✅ Agent ready with [bold green]{total_tools}[/bold green] tools!"
        if mcp_count > 0:
            summary_text += f"\n🔌 MCP tools: [bold cyan]{mcp_count}[/bold cyan]"
            summary_text += f"\n🛠️  Built-in tools: [bold blue]{builtin_count}[/bold blue]"
        summary_text += f"\n⚠️  [bold yellow]Press Ctrl+C during processing to interrupt tasks[/bold yellow]"
        
        success_panel = Panel(
            summary_text,
            title="[bold green]Setup Complete[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
        
        if self.verbose:
            self.console.print(f"[dim]Working directory: {os.getcwd()}[/dim]")
    
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
    
    async def cleanup(self):
        """Clean up resources."""
        if self.mcp_loader:
            try:
                await self.mcp_loader.close()
            except Exception as e:
                if self.verbose:
                    self.console.print(f"[dim]Error during MCP cleanup: {e}[/dim]")
    
    async def process_input(self, user_input: str):
        """Process user input."""
        user_input = user_input.strip()
        
        if self.verbose:
            self.console.print(f"[dim]Processing input: {user_input[:50]}{'...' if len(user_input) > 50 else ''}[/dim]")
        
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
            
            if self.verbose:
                self.console.print(f"[dim]Response length: {len(response.answer)} characters[/dim]")
            
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
            
            if self.verbose:
                import traceback
                self.console.print(f"[dim]Full traceback:\n{traceback.format_exc()}[/dim]")
    
    async def process_command(self, command_input: str):
        """Process a command input with support for different command types."""
        from minion_code.commands import CommandType

        # Remove the leading /
        command_input = command_input[1:] if command_input.startswith('/') else command_input

        # Split command and arguments
        parts = command_input.split(' ', 1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if self.verbose:
            self.console.print(f"[dim]Executing command: {command_name} with args: {args}[/dim]")

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

        # Get command type and is_skill
        command_type = getattr(command_class, 'command_type', CommandType.LOCAL)
        is_skill = getattr(command_class, 'is_skill', False)

        # Handle PROMPT type commands - expand and send to LLM
        if command_type == CommandType.PROMPT:
            try:
                command_instance = command_class(self.output_adapter, self.agent)
                expanded_prompt = await command_instance.get_prompt(args)

                # Process expanded prompt through AI
                if self.verbose:
                    self.console.print(f"[dim]Expanded prompt: {expanded_prompt[:100]}...[/dim]")
                await self.process_input(expanded_prompt)

            except Exception as e:
                error_panel = Panel(
                    f"❌ [bold red]Error expanding command /{command_name}: {e}[/bold red]",
                    title="[bold red]Command Error[/bold red]",
                    border_style="red"
                )
                self.console.print(error_panel)
            return

        # Handle LOCAL and LOCAL_JSX type commands - direct execution
        try:
            # Show status message based on is_skill
            if is_skill:
                status_text = f"⚙️ /{command_name} skill is executing..."
            else:
                status_text = f"⚙️ /{command_name} is executing..."

            self.console.print(f"[dim]{status_text}[/dim]")

            command_instance = command_class(self.output_adapter, self.agent)

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

            if self.verbose:
                import traceback
                self.console.print(f"[dim]Full traceback:\n{traceback.format_exc()}[/dim]")
    
    async def run(self):
        """Run the CLI."""
        # Welcome banner
        welcome_panel = Panel(
            "🚀 [bold blue]MinionCodeAgent Simple CLI[/bold blue]\n"
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
        
        # Cleanup resources
        await self.cleanup()


@app.command()
def main(
    dir: Optional[str] = typer.Option(
        None,
        "--dir",
        "-d",
        help="🗂️  Change to specified directory before starting"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="🔍 Enable verbose output with additional debugging information"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="🔌 Path to MCP configuration file (JSON format)"
    )
):
    """
    🤖 Start the MinionCodeAgent Simple CLI interface
    
    Console-based AI-powered code assistant with task interruption support.
    """
    console = Console()
    
    # Change directory if specified
    if dir:
        try:
            target_dir = Path(dir).resolve()
            if not target_dir.exists():
                console.print(f"❌ [bold red]Directory does not exist: {dir}[/bold red]")
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console.print(f"❌ [bold red]Path is not a directory: {dir}[/bold red]")
                raise typer.Exit(1)
            
            os.chdir(target_dir)
            if verbose:
                console.print(f"📁 [bold green]Changed to directory: {target_dir}[/bold green]")
        except Exception as e:
            console.print(f"❌ [bold red]Failed to change directory: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Validate MCP config if provided
    mcp_config_path = None
    if config:
        mcp_config_path = Path(config).resolve()
        if not mcp_config_path.exists():
            console.print(f"❌ [bold red]MCP config file does not exist: {config}[/bold red]")
            raise typer.Exit(1)
        if not mcp_config_path.is_file():
            console.print(f"❌ [bold red]MCP config path is not a file: {config}[/bold red]")
            raise typer.Exit(1)
        
        if verbose:
            console.print(f"🔌 [bold green]Using MCP config: {mcp_config_path}[/bold green]")
    
    # Create and run CLI
    cli = InterruptibleCLI(verbose=verbose, mcp_config=mcp_config_path)
    
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        console.print("\n👋 [bold yellow]Goodbye![/bold yellow]")


def run():
    """Entry point for pyproject.toml scripts."""
    app()


if __name__ == "__main__":
    app()