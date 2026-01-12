#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP server entry point for minion-code.

This module provides the main entry point for running minion-code
as an ACP agent over stdio.

Usage:
    mcode acp
    mcode acp --dangerously-skip-permissions
    python -m minion_code.acp_server.main
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Save original stdout for ACP communication
_original_stdout = sys.stdout

# Configure loguru to use stderr BEFORE any imports that use it
# This is critical for ACP - stdout is reserved for JSON-RPC communication
from loguru import logger as loguru_logger
loguru_logger.remove()  # Remove default handler
loguru_logger.add(sys.stderr, format="{time} | {level} | {name}:{function}:{line} - {message}")

# Also redirect standard stdout to stderr for any stray prints
sys.stdout = sys.stderr

# Now import everything else
from acp import run_agent

from .agent import MinionACPAgent

logger = logging.getLogger(__name__)

# Config directory
MINION_CONFIG_DIR = Path.home() / ".minion"
MINION_CODE_CONFIG = MINION_CONFIG_DIR / "minion-code.json"


def ensure_config_dir() -> Path:
    """Ensure ~/.minion directory exists."""
    MINION_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return MINION_CONFIG_DIR


def load_config() -> dict:
    """Load minion-code config from ~/.minion/minion-code.json"""
    if MINION_CODE_CONFIG.exists():
        try:
            with open(MINION_CODE_CONFIG, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    return {}


def save_config(config: dict) -> None:
    """Save minion-code config to ~/.minion/minion-code.json"""
    ensure_config_dir()
    try:
        with open(MINION_CODE_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save config: {e}")


def get_session_log_dir(cwd: str) -> Path:
    """Get session log directory for a project."""
    # Hash the cwd to create a unique folder name
    import hashlib
    cwd_hash = hashlib.md5(cwd.encode()).hexdigest()[:8]
    project_name = Path(cwd).name
    session_dir = MINION_CONFIG_DIR / "sessions" / f"{project_name}-{cwd_hash}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def setup_logging(level: str = "INFO") -> None:
    """Setup logging to stderr and file (stdout is used for ACP protocol)."""
    # Log to stderr
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    # Also log to file for debugging
    debug_log = os.path.expanduser("~/minion-code-acp-debug.log")
    file_handler = logging.FileHandler(debug_log, mode='a')
    file_handler.setFormatter(logging.Formatter("%(asctime)s - PID=%(process)d - %(name)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)


def main(log_level: str = "INFO", dangerously_skip_permissions: bool = False) -> None:
    """
    Main entry point for running minion-code as an ACP agent.

    This function:
    1. Redirects stdout to stderr (stdout is reserved for ACP)
    2. Sets up logging
    3. Creates the MinionACPAgent
    4. Runs the ACP server over stdio

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        dangerously_skip_permissions: If True, skip permission prompts for tool calls
    """
    setup_logging(log_level)
    pid = os.getpid()
    logger.info(f"Starting minion-code ACP agent [PID={pid}]")

    # Load config
    config = load_config()

    # Check if permissions should be skipped
    skip_permissions = dangerously_skip_permissions or config.get("skip_permissions", False)
    if skip_permissions:
        logger.warning("Permission prompts DISABLED (--dangerously-skip-permissions)")

    # Create the agent with config
    agent = MinionACPAgent(
        skip_permissions=skip_permissions,
        config=config,
    )

    # Restore stdout for ACP communication
    sys.stdout = _original_stdout

    # Run the ACP agent (run_agent is an async function)
    try:
        asyncio.run(run_agent(agent))
    except KeyboardInterrupt:
        logger.info("Shutting down ACP agent")
    except Exception as e:
        logger.error(f"ACP agent error: {e}")
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Minion Code ACP Agent")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--dangerously-skip-permissions", action="store_true",
                       help="Skip permission prompts for tool calls")
    args = parser.parse_args()
    main(log_level=args.log_level, dangerously_skip_permissions=args.dangerously_skip_permissions)
