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
import sys
from typing import Optional

# Redirect stdout to stderr BEFORE any other imports
# This is critical for ACP - stdout is reserved for JSON-RPC communication
_original_stdout = sys.stdout
sys.stdout = sys.stderr

# Now import everything else
from acp import run_agent

from .agent import MinionACPAgent

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging to stderr (stdout is used for ACP protocol)."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )


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
    logger.info("Starting minion-code ACP agent")

    # Create the agent
    agent = MinionACPAgent()

    # Restore stdout for ACP communication
    sys.stdout = _original_stdout

    # Run the ACP agent
    try:
        run_agent(agent)
    except KeyboardInterrupt:
        logger.info("Shutting down ACP agent")
    except Exception as e:
        logger.error(f"ACP agent error: {e}")
        raise


if __name__ == "__main__":
    main()
