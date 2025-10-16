#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minion Code Tools Package

A collection of tools and enhanced agents for the Minion framework including 
file operations, system commands, web interactions, and specialized agents
with dynamic system prompts and state management.
"""

from . import tools
from . import agents
from .agents import MinionCodeAgent, create_minion_code_agent

__version__ = "0.1.0"
__all__ = ["tools", "agents", "MinionCodeAgent", "create_minion_code_agent"]
