#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern CLI interface for MinionCodeAgent with Textual TUI support

This CLI provides both console and TUI interfaces:
- Default: Modern REPL TUI interface
- Console: Traditional console interface (--console flag)
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = typer.Typer(
    name="minion-code",
    help="🤖 MinionCodeAgent CLI - Modern AI-powered code assistant",
    add_completion=False,
    rich_markup_mode="rich"
)


def run_console_cli(verbose: bool = False, mcp_config: Optional[Path] = None):
    """Run the traditional console CLI interface"""
    from minion_code.cli_simple import InterruptibleCLI
    cli = InterruptibleCLI(verbose=verbose, mcp_config=mcp_config)
    return asyncio.run(cli.run())


def run_tui_repl(
    debug: bool = False,
    verbose: bool = False,
    initial_prompt: Optional[str] = None,
    dir: Optional[str] = None
):
    """Run the modern TUI REPL interface"""
    try:
        from minion_code.screens.REPL import run
        run(initial_prompt=initial_prompt, debug=debug, verbose=verbose)
    except ImportError as e:
        console = Console()
        console.print(f"❌ [bold red]TUI dependencies not available: {e}[/bold red]")
        console.print("💡 [italic]Install TUI dependencies with: pip install textual rich[/italic]")
        console.print("🔄 [italic]Falling back to console interface...[/italic]")
        # Fallback to console CLI
        run_console_cli(verbose=verbose)
    except Exception as e:
        console = Console()
        console.print(f"❌ [bold red]TUI error: {e}[/bold red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)



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
    debug: bool = typer.Option(
        False,
        "--debug",
        help="🐛 Enable debug mode for development"
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="💬 Initial prompt to send to the agent"
    ),
    console: bool = typer.Option(
        False,
        "--console",
        help="🖥️  Use console interface instead of TUI"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="🔌 Path to MCP configuration file (JSON format)"
    )
):
    """
    🤖 Start MinionCodeAgent - Modern AI-powered code assistant
    
    By default starts the modern TUI REPL interface.
    Use --console for traditional console interface.
    """
    # Change directory if specified
    if dir:
        try:
            target_dir = Path(dir).resolve()
            if not target_dir.exists():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Directory does not exist: {dir}[/bold red]")
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Path is not a directory: {dir}[/bold red]")
                raise typer.Exit(1)
            
            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(f"📁 [bold green]Changed to directory: {target_dir}[/bold green]")
        except Exception as e:
            console_obj = Console()
            console_obj.print(f"❌ [bold red]Failed to change directory: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Validate MCP config if provided
    mcp_config_path = None
    if config:
        mcp_config_path = Path(config).resolve()
        if not mcp_config_path.exists():
            console_obj = Console()
            console_obj.print(f"❌ [bold red]MCP config file does not exist: {config}[/bold red]")
            raise typer.Exit(1)
        if not mcp_config_path.is_file():
            console_obj = Console()
            console_obj.print(f"❌ [bold red]MCP config path is not a file: {config}[/bold red]")
            raise typer.Exit(1)
        
        if verbose:
            console_obj = Console()
            console_obj.print(f"🔌 [bold green]Using MCP config: {mcp_config_path}[/bold green]")
    
    # Choose interface based on flags
    if console:
        # Use console interface
        run_console_cli(verbose=verbose, mcp_config=mcp_config_path)
    else:
        # Use TUI interface (default)
        run_tui_repl(
            debug=debug,
            verbose=verbose,
            initial_prompt=prompt,
            dir=dir
        )


@app.command()
def repl(
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
    debug: bool = typer.Option(
        False,
        "--debug",
        help="🐛 Enable debug mode for development"
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="💬 Initial prompt to send to the agent"
    )
):
    """
    🖥️  Start the REPL (Read-Eval-Print Loop) TUI interface
    
    A modern terminal interface with streaming responses and interactive features.
    """
    # Change directory if specified
    if dir:
        try:
            target_dir = Path(dir).resolve()
            if not target_dir.exists():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Directory does not exist: {dir}[/bold red]")
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Path is not a directory: {dir}[/bold red]")
                raise typer.Exit(1)
            
            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(f"📁 [bold green]Changed to directory: {target_dir}[/bold green]")
        except Exception as e:
            console_obj = Console()
            console_obj.print(f"❌ [bold red]Failed to change directory: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Run TUI REPL
    run_tui_repl(
        debug=debug,
        verbose=verbose,
        initial_prompt=prompt,
        dir=dir
    )


@app.command()
def console(
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
    🖥️  Start the traditional console CLI interface
    
    Console-based interface for environments without TUI support.
    """
    # Change directory if specified
    if dir:
        try:
            target_dir = Path(dir).resolve()
            if not target_dir.exists():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Directory does not exist: {dir}[/bold red]")
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(f"❌ [bold red]Path is not a directory: {dir}[/bold red]")
                raise typer.Exit(1)
            
            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(f"📁 [bold green]Changed to directory: {target_dir}[/bold green]")
        except Exception as e:
            console_obj = Console()
            console_obj.print(f"❌ [bold red]Failed to change directory: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Validate MCP config if provided
    mcp_config_path = None
    if config:
        mcp_config_path = Path(config).resolve()
        if not mcp_config_path.exists():
            console_obj = Console()
            console_obj.print(f"❌ [bold red]MCP config file does not exist: {config}[/bold red]")
            raise typer.Exit(1)
        if not mcp_config_path.is_file():
            console_obj = Console()
            console_obj.print(f"❌ [bold red]MCP config path is not a file: {config}[/bold red]")
            raise typer.Exit(1)
        
        if verbose:
            console_obj = Console()
            console_obj.print(f"🔌 [bold green]Using MCP config: {mcp_config_path}[/bold green]")
    
    # Run console CLI
    run_console_cli(verbose=verbose, mcp_config=mcp_config_path)


if __name__ == "__main__":
    app()