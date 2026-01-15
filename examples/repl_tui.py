#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REPL TUI Entry Point

This is the main entry point for the modern TUI REPL interface.
It provides a clean way to start the REPL from examples/ directory.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run():
    """Main entry point for REPL TUI"""
    try:
        # Setup TUI-friendly logging before importing REPL
        from minion_code.utils.logs import setup_tui_logging

        setup_tui_logging()

        from minion_code.screens.REPL import run as run_repl

        run_repl()
    except ImportError as e:
        print(f"❌ TUI dependencies not available: {e}")
        print("💡 Install with: pip install textual rich")
        print("🔄 Falling back to console interface...")
        # Fallback to console
        from minion_code.cli_simple import app

        app()
    except Exception as e:
        print(f"❌ Error starting REPL: {e}")
        sys.exit(1)


def run_with_args():
    """Entry point that handles command line arguments"""
    import argparse

    parser = argparse.ArgumentParser(
        description="🤖 MinionCodeAgent REPL TUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/repl_tui.py
  python examples/repl_tui.py --debug --verbose
  python examples/repl_tui.py --prompt "Help me analyze this code"
  python examples/repl_tui.py --dir /path/to/project
        """,
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--prompt", "-p", type=str, help="Initial prompt to send to the agent"
    )

    parser.add_argument(
        "--dir", "-d", type=str, help="Change to specified directory before starting"
    )

    parser.add_argument(
        "--test-messages",
        action="store_true",
        help="Start with test messages for development",
    )

    args = parser.parse_args()

    # Change directory if specified
    if args.dir:
        import os

        try:
            target_dir = Path(args.dir).resolve()
            if not target_dir.exists():
                print(f"❌ Directory does not exist: {args.dir}")
                sys.exit(1)
            if not target_dir.is_dir():
                print(f"❌ Path is not a directory: {args.dir}")
                sys.exit(1)

            os.chdir(target_dir)
            if args.verbose:
                print(f"📁 Changed to directory: {target_dir}")
        except Exception as e:
            print(f"❌ Failed to change directory: {e}")
            sys.exit(1)

    # Start REPL with arguments
    try:
        # Setup TUI-friendly logging before importing REPL
        from minion_code.utils.logs import setup_tui_logging

        setup_tui_logging()

        if args.test_messages:
            # Use the test messages version
            from examples.repl_with_test_messages import main as run_test_repl

            run_test_repl()
        else:
            from minion_code.screens.REPL import run as run_repl

            run_repl(initial_prompt=args.prompt, debug=args.debug, verbose=args.verbose)
    except ImportError as e:
        print(f"❌ TUI dependencies not available: {e}")
        print("💡 Install with: pip install textual rich")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting REPL: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_with_args()
