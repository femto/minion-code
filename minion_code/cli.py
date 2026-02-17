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
    rich_markup_mode="rich",
)


def run_console_cli(
    verbose: bool = False,
    mcp_config: Optional[Path] = None,
    resume_session_id: Optional[str] = None,
    continue_last: bool = False,
    initial_prompt: Optional[str] = None,
    print_output: bool = False,
    model: Optional[str] = None,
):
    """Run the traditional console CLI interface"""
    from minion_code.cli_simple import InterruptibleCLI

    cli = InterruptibleCLI(
        verbose=verbose,
        mcp_config=mcp_config,
        resume_session_id=resume_session_id,
        continue_last=continue_last,
        initial_prompt=initial_prompt,
        print_output=print_output,
        model=model,
    )
    return asyncio.run(cli.run())


def run_tui_repl(
    debug: bool = False,
    verbose: bool = False,
    initial_prompt: Optional[str] = None,
    dir: Optional[str] = None,
    resume_session_id: Optional[str] = None,
    continue_last: bool = False,
    model: Optional[str] = None,
):
    """Run the modern TUI REPL interface"""
    try:
        from minion_code.screens.REPL import run

        run(
            initial_prompt=initial_prompt,
            debug=debug,
            verbose=verbose,
            resume_session_id=resume_session_id,
            continue_last=continue_last,
            model=model,
        )
    except ImportError as e:
        console = Console()
        console.print(f"❌ [bold red]TUI dependencies not available: {e}[/bold red]")
        console.print(
            "💡 [italic]Install TUI dependencies with: pip install textual rich[/italic]"
        )
        console.print("🔄 [italic]Falling back to console interface...[/italic]")
        # Fallback to console CLI
        run_console_cli(
            verbose=verbose,
            resume_session_id=resume_session_id,
            continue_last=continue_last,
            model=model,
        )
    except Exception as e:
        console = Console()
        console.print(f"❌ [bold red]TUI error: {e}[/bold red]")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def main(
    prompt_arg: Optional[str] = typer.Argument(
        None, help="Initial prompt to send to the agent (like 'claude \"prompt\"')"
    ),
    dir: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Change to specified directory before starting"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use (e.g., gpt-4o, claude-3-5-sonnet). If not specified, uses config file setting.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with additional debugging information",
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug mode for development"
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="Initial prompt to send to the agent (alternative to positional arg)",
    ),
    console: bool = typer.Option(
        False, "--console", help="Use console interface instead of TUI"
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to MCP configuration file (JSON format)"
    ),
    continue_session: bool = typer.Option(
        False, "--continue", help="Continue the most recent session for this project"
    ),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Resume a specific session by ID"
    ),
    print_output: bool = typer.Option(
        False,
        "--print",
        help="Print output and exit (non-interactive mode, console only)",
    ),
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
                console_obj.print(
                    f"❌ [bold red]Directory does not exist: {dir}[/bold red]"
                )
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(
                    f"❌ [bold red]Path is not a directory: {dir}[/bold red]"
                )
                raise typer.Exit(1)

            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(
                    f"📁 [bold green]Changed to directory: {target_dir}[/bold green]"
                )
        except Exception as e:
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]Failed to change directory: {e}[/bold red]"
            )
            raise typer.Exit(1)

    # Validate MCP config if provided
    mcp_config_path = None
    if config:
        mcp_config_path = Path(config).resolve()
        if not mcp_config_path.exists():
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]MCP config file does not exist: {config}[/bold red]"
            )
            raise typer.Exit(1)
        if not mcp_config_path.is_file():
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]MCP config path is not a file: {config}[/bold red]"
            )
            raise typer.Exit(1)

        if verbose:
            console_obj = Console()
            console_obj.print(
                f"🔌 [bold green]Using MCP config: {mcp_config_path}[/bold green]"
            )

    # Combine prompt sources (positional arg takes precedence)
    initial_prompt = prompt_arg or prompt

    # Choose interface based on flags
    if console:
        # Use console interface
        run_console_cli(
            verbose=verbose,
            mcp_config=mcp_config_path,
            resume_session_id=resume,
            continue_last=continue_session,
            initial_prompt=initial_prompt,
            print_output=print_output,
            model=model,
        )
    else:
        # Use TUI interface (default)
        run_tui_repl(
            debug=debug,
            verbose=verbose,
            initial_prompt=initial_prompt,
            dir=dir,
            resume_session_id=resume,
            continue_last=continue_session,
            model=model,
        )


@app.command()
def repl(
    dir: Optional[str] = typer.Option(
        None, "--dir", "-d", help="🗂️  Change to specified directory before starting"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="🤖 LLM model to use (e.g., gpt-4o, claude-3-5-sonnet)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="🔍 Enable verbose output with additional debugging information",
    ),
    debug: bool = typer.Option(
        False, "--debug", help="🐛 Enable debug mode for development"
    ),
    prompt: Optional[str] = typer.Option(
        None, "--prompt", "-p", help="💬 Initial prompt to send to the agent"
    ),
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
                console_obj.print(
                    f"❌ [bold red]Directory does not exist: {dir}[/bold red]"
                )
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(
                    f"❌ [bold red]Path is not a directory: {dir}[/bold red]"
                )
                raise typer.Exit(1)

            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(
                    f"📁 [bold green]Changed to directory: {target_dir}[/bold green]"
                )
        except Exception as e:
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]Failed to change directory: {e}[/bold red]"
            )
            raise typer.Exit(1)

    # Run TUI REPL
    run_tui_repl(
        debug=debug, verbose=verbose, initial_prompt=prompt, dir=dir, model=model
    )


@app.command()
def console(
    dir: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Change to specified directory before starting"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="LLM model to use (e.g., gpt-4o, claude-3-5-sonnet)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with additional debugging information",
    ),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to MCP configuration file (JSON format)"
    ),
    continue_session: bool = typer.Option(
        False, "--continue", help="Continue the most recent session for this project"
    ),
    resume: Optional[str] = typer.Option(
        None, "--resume", "-r", help="Resume a specific session by ID"
    ),
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
                console_obj.print(
                    f"❌ [bold red]Directory does not exist: {dir}[/bold red]"
                )
                raise typer.Exit(1)
            if not target_dir.is_dir():
                console_obj = Console()
                console_obj.print(
                    f"❌ [bold red]Path is not a directory: {dir}[/bold red]"
                )
                raise typer.Exit(1)

            os.chdir(target_dir)
            if verbose:
                console_obj = Console()
                console_obj.print(
                    f"📁 [bold green]Changed to directory: {target_dir}[/bold green]"
                )
        except Exception as e:
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]Failed to change directory: {e}[/bold red]"
            )
            raise typer.Exit(1)

    # Validate MCP config if provided
    mcp_config_path = None
    if config:
        mcp_config_path = Path(config).resolve()
        if not mcp_config_path.exists():
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]MCP config file does not exist: {config}[/bold red]"
            )
            raise typer.Exit(1)
        if not mcp_config_path.is_file():
            console_obj = Console()
            console_obj.print(
                f"❌ [bold red]MCP config path is not a file: {config}[/bold red]"
            )
            raise typer.Exit(1)

        if verbose:
            console_obj = Console()
            console_obj.print(
                f"🔌 [bold green]Using MCP config: {mcp_config_path}[/bold green]"
            )

    # Run console CLI
    run_console_cli(
        verbose=verbose,
        mcp_config=mcp_config_path,
        resume_session_id=resume,
        continue_last=continue_session,
        model=model,
    )


@app.command(name="model")
def model_cmd(
    model_name: Optional[str] = typer.Argument(
        None,
        help="Model name to set (e.g., gpt-4o, claude-3-5-sonnet). If not provided, shows current model.",
    ),
    clear: bool = typer.Option(
        False, "--clear", "-c", help="Clear the saved model (use default)"
    ),
):
    """
    🤖 Configure the default LLM model.

    Set, view, or clear the default model used by minion-code.
    The model setting is saved to ~/.minion/minion-code.json.

    Examples:
        # View current model
        mcode model

        # Set default model
        mcode model gpt-4o
        mcode model claude-3-5-sonnet

        # Clear model (use default)
        mcode model --clear
    """
    import json
    from pathlib import Path
    from rich.console import Console

    console_obj = Console()
    config_dir = Path.home() / ".minion"
    config_file = config_dir / "minion-code.json"

    # Load current config
    config = {}
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
        except Exception:
            pass

    if clear:
        # Clear model setting
        if "model" in config:
            del config["model"]
            config_dir.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            console_obj.print(
                "✅ [green]Model setting cleared. Will use default model.[/green]"
            )
        else:
            console_obj.print("ℹ️  [dim]No model setting to clear.[/dim]")
    elif model_name:
        # Set model
        config["model"] = model_name
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        console_obj.print(
            f"✅ [green]Default model set to:[/green] [bold cyan]{model_name}[/bold cyan]"
        )
        console_obj.print(f"📁 [dim]Config saved to: {config_file}[/dim]")
    else:
        # Show current model
        current_model = config.get("model")
        if current_model:
            console_obj.print(
                f"🤖 [bold]Current default model:[/bold] [cyan]{current_model}[/cyan]"
            )
        else:
            console_obj.print(
                "🤖 [bold]No default model set[/bold] (using built-in default)"
            )
        console_obj.print(f"\n💡 [dim]Set with: mcode model <model-name>[/dim]")
        console_obj.print(f"💡 [dim]Clear with: mcode model --clear[/dim]")


@app.command()
def logout():
    """
    🚪 Log out and clear stored credentials.

    Removes the OAuth credentials stored at ~/.minion/credentials.json.
    You will need to sign in again next time you use minion-code.
    """
    from rich.console import Console
    from minion_code.acp_server.auth import logout as auth_logout, CREDENTIALS_FILE

    console_obj = Console()

    if CREDENTIALS_FILE.exists():
        auth_logout()
        console_obj.print("✅ [green]Successfully logged out.[/green]")
        console_obj.print(f"📁 [dim]Removed: {CREDENTIALS_FILE}[/dim]")
    else:
        console_obj.print("ℹ️  [dim]No credentials found. You are not logged in.[/dim]")


@app.command()
def serve(
    host: str = typer.Option(
        "0.0.0.0", "--host", "-H", help="Host to bind the server to"
    ),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(
        False, "--reload", "-r", help="Enable auto-reload for development"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", "-l", help="Logging level (debug, info, warning, error)"
    ),
):
    """
    🌐 Start the Web API server.

    Provides HTTP/SSE API for cross-process frontend communication.
    Similar to claude.ai, uses Server-Sent Events for streaming responses.

    Examples:
        # Start server on default port (8000)
        mcode serve

        # Start on custom port with auto-reload
        mcode serve --port 3001 --reload

        # Production mode with specific host
        mcode serve --host 127.0.0.1 --port 8080
    """
    from rich.console import Console

    console_obj = Console()

    console_obj.print(f"🌐 [bold green]Starting Minion Code Web API[/bold green]")
    console_obj.print(f"📡 Server: http://{host}:{port}")
    console_obj.print(f"📚 API Docs: http://{host}:{port}/docs")
    console_obj.print()

    from minion_code.web.server import run_server

    run_server(host=host, port=port, reload=reload, log_level=log_level)


@app.command()
def acp(
    directory: Optional[str] = typer.Option(
        None, "--dir", "-d", help="Working directory for the agent"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model to use (e.g., gpt-4o, claude-3-5-sonnet). If not specified, uses config file setting.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose (debug) logging"
    ),
    log_level: str = typer.Option(
        "info", "--log-level", "-l", help="Logging level (debug, info, warning, error)"
    ),
    dangerously_skip_permissions: bool = typer.Option(
        False,
        "--dangerously-skip-permissions",
        help="Skip permission prompts for tool calls (dangerous!)",
    ),
):
    """
    🔌 Start as ACP (Agent Client Protocol) agent.

    Runs minion-code as an ACP-compatible agent over stdio.
    This allows integration with ACP clients like Zed editor.

    The agent communicates via JSON-RPC over stdin/stdout,
    with all other output redirected to stderr.

    Examples:
        # Start ACP agent
        mcode acp

        # Start with specific working directory
        mcode acp --dir /path/to/project

        # Start with specific model
        mcode acp --model gpt-4o

        # Start with verbose logging
        mcode acp --verbose

        # Start without permission prompts (dangerous!)
        mcode acp --dangerously-skip-permissions
    """
    # Handle verbose flag
    if verbose:
        log_level = "debug"

    from minion_code.acp_server.main import main as acp_main

    acp_main(
        log_level=log_level,
        dangerously_skip_permissions=dangerously_skip_permissions,
        cwd=directory,
        model=model,
    )


def run():
    """Entry point for pyproject.toml scripts."""
    _maybe_insert_main_command()
    app()


def _maybe_insert_main_command():
    """Insert 'main' command if not provided, to enable 'mcode "prompt"' usage."""
    known_commands = {
        "main",
        "repl",
        "console",
        "serve",
        "acp",
        "model",
        "logout",
        "--help",
        "-h",
    }
    args = sys.argv[1:]

    if not args:
        # No args, insert 'main'
        sys.argv.insert(1, "main")
    elif args[0] in ("--help", "-h"):
        # Help requested, don't modify
        pass
    elif args[0] not in known_commands:
        # First arg is not a known command - could be a prompt or option
        # Insert 'main' to treat it as: mcode main "prompt" or mcode main --option
        sys.argv.insert(1, "main")


if __name__ == "__main__":
    _maybe_insert_main_command()
    app()
