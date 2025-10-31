#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger as _logger

from ..const import MINION_ROOT

_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d")
    log_name = f"{name}_{formatted_date}" if name else formatted_date  # name a log with prefix name

    _logger.remove()
    _logger.add(sys.stdout, level=print_level)
    _logger.add(MINION_ROOT / f"logs/{log_name}.txt", level=logfile_level)
    return _logger


def setup_tui_logging():
    """Setup logging for TUI mode - removes console output to prevent UI interference"""
    global _print_level
    
    # Remove all existing handlers
    _logger.remove()
    
    # Only add file logging for TUI mode
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d")
    log_name = f"{formatted_date}"
    
    # Ensure logs directory exists
    logs_dir = MINION_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    _logger.add(logs_dir / f"{log_name}.txt", level="DEBUG")
    _print_level = "DEBUG"  # Set to DEBUG for file logging
    
    return _logger


logger = define_log_level()


