#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI interface for MinionCodeAgent using Typer

This CLI provides command-line arguments support including --dir and --verbose options.
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
from minion_code.types import InputMode
from minion_code.adapters.rich_adapter import RichOutputAdapter

app = typer.Typer(
    name="minion-code",
    help="🤖 MinionCodeAgent CLI - An AI-powered code assistant",
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
        
        # Add mode support
        self.current_mode = InputMode.PROMPT

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
                llm="sonnet",  # 使用更稳定的模型配置
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

    def show_help(self):
        """Show help information."""
        help_table = Table(title="📚 MinionCode CLI Help", show_header=True, header_style="bold blue")
        help_table.add_column("Command/Key", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")

        help_table.add_row("help", "Show this help")
        help_table.add_row("tools", "List available tools")
        help_table.add_row("history", "Show conversation history")
        help_table.add_row("clear", "Clear history")
        help_table.add_row("quit", "Exit")
        help_table.add_row("Ctrl+C", "Interrupt current task or exit")
        
        # Add mode information
        help_table.add_row("", "")  # Separator
        help_table.add_row("[bold]Input Modes:[/bold]", "")
        help_table.add_row("> [text]", "Prompt mode - Chat with AI assistant")
        help_table.add_row("! [command]", "Bash mode - Execute shell commands")
        help_table.add_row("# [note]", "Koding mode - Add notes to AGENTS.md")
        help_table.add_row("", "")  # Separator
        help_table.add_row("[bold]Koding Mode Types:[/bold]", "")
        help_table.add_row("# [simple note]", "Direct note (simple write)")
        help_table.add_row("# put/create/generate...", "AI processing with query_quick")

        self.console.print(help_table)
        self.console.print("\n💡 [italic]Just type your message to chat with the AI agent![/italic]")
        self.console.print("⚠️  [italic]During task processing, press Ctrl+C to interrupt the current task[/italic]")
        self.console.print("🔄 [italic]Use prefixes !, # to switch modes, or just type normally for prompt mode[/italic]")

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

    def _detect_and_set_mode(self, user_input: str) -> tuple[InputMode, str]:
        """Detect input mode and return mode and cleaned input."""
        if user_input.startswith('!'):
            self.current_mode = InputMode.BASH
            return InputMode.BASH, user_input[1:].strip()
        elif user_input.startswith('#'):
            self.current_mode = InputMode.KODING
            return InputMode.KODING, user_input[1:].strip()
        else:
            self.current_mode = InputMode.PROMPT
            return InputMode.PROMPT, user_input

    def _get_mode_indicator(self, mode: InputMode) -> str:
        """Get colored mode indicator for display."""
        if mode == InputMode.BASH:
            return "[bold yellow]![/bold yellow]"
        elif mode == InputMode.KODING:
            return "[bold cyan]#[/bold cyan]"
        else:
            return "[bold green]>[/bold green]"

    async def _handle_bash_mode(self, command: str):
        """Handle bash mode input."""
        if not command:
            self.console.print("❌ [bold red]Empty bash command[/bold red]")
            return

        try:
            import subprocess
            
            # Show what command is being executed
            command_panel = Panel(
                f"[bold white]{command}[/bold white]",
                title=f"{self._get_mode_indicator(InputMode.BASH)} [bold yellow]Bash Command[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(command_panel)

            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Format output
            if result.returncode == 0:
                output = result.stdout.strip() if result.stdout else "Command executed successfully"
                if output:
                    output_panel = Panel(
                        output,
                        title="✅ [bold green]Command Output[/bold green]",
                        border_style="green"
                    )
                    self.console.print(output_panel)
            else:
                error_output = result.stderr.strip() if result.stderr else f"Command failed with exit code {result.returncode}"
                error_panel = Panel(
                    error_output,
                    title="❌ [bold red]Command Error[/bold red]",
                    border_style="red"
                )
                self.console.print(error_panel)

        except subprocess.TimeoutExpired:
            timeout_panel = Panel(
                "⏰ [bold yellow]Command timed out after 30 seconds[/bold yellow]",
                title="[bold yellow]Timeout[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(timeout_panel)
        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error executing command: {e}[/bold red]",
                title="[bold red]Execution Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)

    async def _handle_koding_mode(self, note_content: str):
        """Handle koding mode input - consistent with REPL logic."""
        if not note_content:
            self.console.print("❌ [bold red]Empty note content[/bold red]")
            return

        try:
            # Show what note is being processed
            note_panel = Panel(
                f"[bold white]{note_content}[/bold white]",
                title=f"{self._get_mode_indicator(InputMode.KODING)} [bold cyan]Processing Koding Request[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(note_panel)

            # Check if this is an action prompt (put, create, generate, etc.)
            # Add safety check to prevent NoneType iteration error
            action_words = ['put', 'create', 'generate', 'write', 'give', 'provide']
            note_lower = note_content.lower() if note_content else ""
            is_action_request = any(word in note_lower for word in action_words)

            if is_action_request:
                # Handle as AI request using query_quick for lightweight processing
                await self._handle_koding_ai_request(note_content)
            else:
                # Handle as direct note to AGENTS.md (simple write)
                await self._handle_koding_note(note_content)

        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error processing koding request: {e}[/bold red]",
                title="[bold red]Koding Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)

    async def _handle_koding_ai_request(self, content: str):
        """Handle AI request for koding mode using query_quick for lightweight processing."""
        if not self.agent:
            self.console.print("❌ [bold red]Agent not available for AI requests[/bold red]")
            return

        try:
            # Import query_quick for lightweight AI processing
            from minion_code.agents.code_agent import query_quick

            # Show processing indicator
            processing_panel = Panel(
                "🤖 [italic]Processing AI request with query_quick...[/italic]",
                title="[bold cyan]Processing[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(processing_panel)

            # Create system prompt for AI content generation
            system_prompt = [
                "The user is using Koding mode. Format your response as a comprehensive,",
                "well-structured document suitable for adding to AGENTS.md. Use proper",
                "markdown formatting with headings, lists, code blocks, etc."
            ]

            # Use query_quick for lightweight AI processing
            result = await query_quick(
                agent=self.agent,
                user_prompt=content,
                system_prompt=system_prompt,
            )

            # Extract formatted content
            if isinstance(result, str):
                formatted_content = result
            else:
                formatted_content = str(result)

            # Add timestamp if not already present
            import time
            timestamp = time.strftime('%m/%d/%Y, %I:%M:%S %p')
            if "_Added on" not in formatted_content:
                formatted_content += f"\n\n_Added on {timestamp}_"

            # Write to AGENTS.md
            agents_md_path = Path("AGENTS.md")
            
            # Create file if it doesn't exist
            if not agents_md_path.exists():
                with open(agents_md_path, "w", encoding="utf-8") as f:
                    f.write("# Agent Development Guidelines\n\n")

            # Append the formatted content
            with open(agents_md_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{formatted_content}\n")

            success_panel = Panel(
                f"✅ [bold green]AI-generated content added to AGENTS.md[/bold green]\n"
                f"📝 [italic]{len(formatted_content)} characters written[/italic]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            )
            self.console.print(success_panel)

        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error processing AI request: {e}[/bold red]",
                title="[bold red]AI Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)

    async def _handle_koding_note(self, content: str):
        """Handle direct note to AGENTS.md - simple write without AI processing."""
        try:
            # Show what note is being added
            note_panel = Panel(
                f"[bold white]{content}[/bold white]",
                title=f"{self._get_mode_indicator(InputMode.KODING)} [bold cyan]Adding Direct Note[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(note_panel)

            # Simple direct write to AGENTS.md
            import time
            timestamp = time.strftime('%m/%d/%Y, %I:%M:%S %p')
            formatted_content = f"# {content}\n\n_Added on {timestamp}_"

            agents_md_path = Path("AGENTS.md")
            
            # Create file if it doesn't exist
            if not agents_md_path.exists():
                with open(agents_md_path, "w", encoding="utf-8") as f:
                    f.write("# Agent Development Guidelines\n\n")

            # Append the content
            with open(agents_md_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{formatted_content}\n")

            success_panel = Panel(
                f"✅ [bold green]Direct note added to AGENTS.md[/bold green]\n"
                f"📝 [italic]{len(formatted_content)} characters written[/italic]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            )
            self.console.print(success_panel)

        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error writing direct note: {e}[/bold red]",
                title="[bold red]File Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)

    async def _write_simple_note(self, content: str):
        """Write a simple formatted note to AGENTS.md as fallback."""
        try:
            import time
            timestamp = time.strftime('%m/%d/%Y, %I:%M:%S %p')
            formatted_content = f"# {content}\n\n_Added on {timestamp}_"

            agents_md_path = Path("AGENTS.md")
            
            # Create file if it doesn't exist
            if not agents_md_path.exists():
                with open(agents_md_path, "w", encoding="utf-8") as f:
                    f.write("# Agent Development Guidelines\n\n")

            # Append the content
            with open(agents_md_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{formatted_content}\n")

            success_panel = Panel(
                f"✅ [bold green]Simple note added to AGENTS.md[/bold green]\n"
                f"📝 [italic]{len(formatted_content)} characters written[/italic]",
                title="[bold green]Success[/bold green]",
                border_style="green"
            )
            self.console.print(success_panel)

        except Exception as e:
            error_panel = Panel(
                f"❌ [bold red]Error writing simple note: {e}[/bold red]",
                title="[bold red]File Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)

    async def process_input(self, user_input: str):
        """Process user input with mode detection."""
        user_input = user_input.strip()

        if self.verbose:
            self.console.print(f"[dim]Processing input: {user_input[:50]}{'...' if len(user_input) > 50 else ''}[/dim]")

        # Check if it's a command (starts with /)
        if user_input.startswith('/'):
            await self.process_command(user_input)
            return

        # Detect mode and get cleaned input
        mode, cleaned_input = self._detect_and_set_mode(user_input)

        # Handle different modes
        if mode == InputMode.BASH:
            await self._handle_bash_mode(cleaned_input)
            return
        elif mode == InputMode.KODING:
            await self._handle_koding_mode(cleaned_input)
            return

        # Handle prompt mode (regular AI chat)
        try:
            with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description} (Ctrl+C to interrupt)"),
                    console=self.console,
            ) as progress:
                task = progress.add_task("🤖 Processing...", total=None)

                response = await self.process_input_with_interrupt(cleaned_input)

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
        """Process a command input."""
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

        # Create and execute command
        try:
            # Wrap console in RichOutputAdapter for commands
            output_adapter = RichOutputAdapter(self.console)
            command_instance = command_class(output_adapter, self.agent)

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

    def show_tools(self):
        """Show available tools in a beautiful table."""
        if not self.agent or not self.agent.tools:
            self.console.print("❌ No tools available")
            return

        tools_table = Table(title="🛠️ Available Tools", show_header=True, header_style="bold magenta")
        tools_table.add_column("Tool Name", style="cyan", no_wrap=True)
        tools_table.add_column("Description", style="white")
        tools_table.add_column("Source", style="yellow")
        tools_table.add_column("Type", style="green")

        # Separate MCP tools from built-in tools
        mcp_tool_names = {tool.name for tool in self.mcp_tools} if self.mcp_tools else set()

        for tool in self.agent.tools:
            tool_type = "Read-only" if getattr(tool, 'readonly', False) else "Read-write"
            source = "MCP" if tool.name in mcp_tool_names else "Built-in"

            tools_table.add_row(
                tool.name,
                tool.description[:60] + "..." if len(tool.description) > 60 else tool.description,
                source,
                tool_type
            )

        self.console.print(tools_table)

        # Show summary
        total_tools = len(self.agent.tools)
        mcp_count = len(self.mcp_tools) if self.mcp_tools else 0
        builtin_count = total_tools - mcp_count

        summary_text = f"[dim]Total: {total_tools} tools"
        if mcp_count > 0:
            summary_text += f" (Built-in: {builtin_count}, MCP: {mcp_count})"
        summary_text += "[/dim]"

        self.console.print(summary_text)

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

        display_count = 5 if not self.verbose else 10
        for i, entry in enumerate(history[-display_count:], 1):
            # User message
            user_panel = Panel(
                entry['user_message'][:200] + "..." if len(entry['user_message']) > 200 else entry['user_message'],
                title=f"👤 [bold cyan]You (Message {len(history) - display_count + i})[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(user_panel)

            # Agent response
            agent_response = entry['agent_response'][:200] + "..." if len(entry['agent_response']) > 200 else entry[
                'agent_response']
            agent_panel = Panel(
                agent_response,
                title="🤖 [bold green]Agent[/bold green]",
                border_style="green"
            )
            self.console.print(agent_panel)
            self.console.print()  # Add spacing

    async def run(self):
        """Run the CLI."""
        # Welcome banner
        welcome_panel = Panel(
            "🚀 [bold blue]MinionCodeAgent CLI[/bold blue]\n"
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
                # Show current mode in prompt
                mode_indicator = self._get_mode_indicator(self.current_mode)
                prompt_text = f"\n{mode_indicator} [bold cyan]You[/bold cyan]"
                
                # Use rich prompt for better input experience
                user_input = Prompt.ask(
                    prompt_text,
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
    🤖 Start the MinionCodeAgent CLI interface

    An AI-powered code assistant with task interruption support and MCP tools integration.
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
    app()
if __name__ == "__main__":
    app()