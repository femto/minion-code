#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) Tools Loader

This module provides functionality to load MCP tools from configuration files
and integrate them with MinionCodeAgent.
"""

import json
import logging
import subprocess
import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from minion.tools.mcp.mcp_toolset import MCPToolset, StdioServerParameters

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPToolset = None
    StdioServerParameters = None

logger = logging.getLogger(__name__)


def find_mcp_config(project_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Auto-discover MCP configuration file.

    Searches in the following order (first found wins):

    Project scope (current working directory or specified project_dir):
    1. .mcp.json
    2. .claude/mcp.json
    3. .minion/mcp.json

    User scope (home directory):
    4. ~/.claude-code/mcp.json
    5. ~/.minion-code/mcp.json
    6. ~/.config/minion-code/mcp.json (XDG standard)

    Args:
        project_dir: Project directory to search in (defaults to cwd)

    Returns:
        Path to config file if found, None otherwise
    """
    # Project scope locations
    project_root = project_dir or Path.cwd()
    project_locations = [
        project_root / ".mcp.json",
        project_root / ".claude" / "mcp.json",
        project_root / ".minion" / "mcp.json",
    ]

    # User scope locations
    home = Path.home()
    user_locations = [
        home / ".claude-code" / "mcp.json",
        home / ".minion-code" / "mcp.json",
        home / ".config" / "minion-code" / "mcp.json",
    ]

    # Search project scope first
    for config_path in project_locations:
        if config_path.exists():
            logger.info(f"Found MCP config at project scope: {config_path}")
            return config_path

    # Then search user scope
    for config_path in user_locations:
        if config_path.exists():
            logger.info(f"Found MCP config at user scope: {config_path}")
            return config_path

    logger.debug("No MCP config file found in any standard location")
    return None


def get_mcp_config_locations() -> Dict[str, List[Path]]:
    """
    Get all standard MCP config file locations.

    Returns:
        Dictionary with 'project' and 'user' scope locations
    """
    project_root = Path.cwd()
    home = Path.home()

    return {
        "project": [
            project_root / ".mcp.json",
            project_root / ".claude" / "mcp.json",
            project_root / ".minion" / "mcp.json",
        ],
        "user": [
            home / ".claude-code" / "mcp.json",
            home / ".minion-code" / "mcp.json",
            home / ".config" / "minion-code" / "mcp.json",
        ],
    }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None
    disabled: bool = False
    auto_approve: List[str] = None

    def __post_init__(self):
        if self.auto_approve is None:
            self.auto_approve = []


class MCPToolsLoader:
    """Loader for MCP tools from configuration files."""

    def __init__(self, config_path: Optional[Path] = None, auto_discover: bool = True):
        """
        Initialize MCP tools loader.

        Args:
            config_path: Path to MCP configuration file. If None and auto_discover=True,
                        will search standard locations.
            auto_discover: If True and config_path is None, automatically search for
                          config in standard locations (.mcp.json, .claude/, .minion/, etc.)
        """
        if config_path:
            self.config_path = config_path
        elif auto_discover:
            self.config_path = find_mcp_config()
        else:
            self.config_path = None

        self.servers: Dict[str, MCPServerConfig] = {}
        self.loaded_tools = []
        self.toolsets: List[Any] = []  # Store MCPToolset instances for cleanup

    def load_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, MCPServerConfig]:
        """
        Load MCP configuration from JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Dictionary of server configurations
        """
        if config_path:
            self.config_path = config_path

        if not self.config_path or not self.config_path.exists():
            logger.warning(f"MCP config file not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            servers_config = config_data.get("mcpServers", {})

            for server_name, server_data in servers_config.items():
                self.servers[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_data.get("command", ""),
                    args=server_data.get("args", []),
                    env=server_data.get("env", {}),
                    disabled=server_data.get("disabled", False),
                    auto_approve=server_data.get("autoApprove", []),
                )

            logger.info(f"Loaded {len(self.servers)} MCP server configurations")
            return self.servers

        except Exception as e:
            logger.error(f"Failed to load MCP config from {self.config_path}: {e}")
            return {}

    async def load_tools_from_server(self, server_config: MCPServerConfig) -> List[Any]:
        """
        Load tools from an MCP server.

        Args:
            server_config: Server configuration

        Returns:
            List of loaded tools
        """
        if server_config.disabled:
            logger.info(f"Skipping disabled MCP server: {server_config.name}")
            return []

        if not MCP_AVAILABLE:
            logger.warning("MCP framework not available, skipping MCP server loading")
            return []

        try:
            logger.info(f"Loading tools from MCP server: {server_config.name}")
            logger.info(
                f"Command: {server_config.command} {' '.join(server_config.args)}"
            )

            # Create MCPToolset with StdioServerParameters
            toolset = await MCPToolset.create(
                connection_params=StdioServerParameters(
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env or {},
                ),
                name=server_config.name,
                structured_output=False,  # Set to False as requested
            )

            # Store toolset for cleanup
            self.toolsets.append(toolset)

            # Get tools from the toolset
            tools = toolset.tools if hasattr(toolset, "tools") else []

            logger.info(
                f"Successfully loaded {len(tools)} tools from {server_config.name}"
            )
            return tools

        except Exception as e:
            logger.error(
                f"Failed to load tools from MCP server {server_config.name}: {e}"
            )
            return []

    async def load_all_tools(self) -> List[Any]:
        """
        Load tools from all configured MCP servers.

        Returns:
            List of all loaded MCP tools
        """
        all_tools = []

        for server_name, server_config in self.servers.items():
            if not server_config.disabled:
                tools = await self.load_tools_from_server(server_config)
                all_tools.extend(tools)
                logger.info(f"Loaded {len(tools)} tools from {server_name}")

        self.loaded_tools = all_tools
        logger.info(f"Total MCP tools loaded: {len(all_tools)}")
        return all_tools

    def get_server_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about configured servers.

        Returns:
            Dictionary with server information
        """
        info = {}
        for name, config in self.servers.items():
            info[name] = {
                "command": config.command,
                "args": config.args,
                "disabled": config.disabled,
                "auto_approve_count": len(config.auto_approve),
            }
        return info

    async def close(self):
        """
        Close all MCP toolsets and clean up resources.
        """
        logger.info(f"Closing {len(self.toolsets)} MCP toolsets...")

        for toolset in self.toolsets:
            try:
                await toolset.close()
                logger.debug(f"Closed toolset: {getattr(toolset, 'name', 'unknown')}")
            except Exception as e:
                logger.error(f"Error closing toolset: {e}")

        self.toolsets.clear()
        logger.info("All MCP toolsets closed")


# Convenience function
async def load_mcp_tools(config_path: Path) -> List[Any]:
    """
    Convenience function to load MCP tools from a configuration file.

    Args:
        config_path: Path to MCP configuration file

    Returns:
        List of loaded MCP tools
    """
    loader = MCPToolsLoader(config_path)
    loader.load_config()
    return await loader.load_all_tools()
