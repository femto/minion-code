#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP server entry point for minion-code.

This module provides the main entry point for running minion-code
as an ACP agent over stdio.

Usage:
    mcode acp
    python -m minion_code.acp.main
"""

import asyncio
import logging
import os
import sys
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


def main(log_level: str = "INFO") -> None:
    """
    Main entry point for running minion-code as an ACP agent.

    This function:
    1. Redirects stdout to stderr (stdout is reserved for ACP)
    2. Sets up logging
    3. Creates the MinionACPAgent
    4. Runs the ACP server over stdio
    """
    setup_logging(log_level)
    pid = os.getpid()
    logger.info(f"Starting minion-code ACP agent [PID={pid}]")

    # Create the agent
    agent = MinionACPAgent()

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
    main()
