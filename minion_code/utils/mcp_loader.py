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
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

try:
    from minion.mcp import MCPToolset, StdioServerParameters
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPToolset = None
    StdioServerParameters = None

logger = logging.getLogger(__name__)


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
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize MCP tools loader.
        
        Args:
            config_path: Path to MCP configuration file
        """
        self.config_path = config_path
        self.servers: Dict[str, MCPServerConfig] = {}
        self.loaded_tools = []
        self.toolsets: List[Any] = []  # Store MCPToolset instances for cleanup
    
    def load_config(self, config_path: Optional[Path] = None) -> Dict[str, MCPServerConfig]:
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
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            servers_config = config_data.get('mcpServers', {})
            
            for server_name, server_data in servers_config.items():
                self.servers[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_data.get('command', ''),
                    args=server_data.get('args', []),
                    env=server_data.get('env', {}),
                    disabled=server_data.get('disabled', False),
                    auto_approve=server_data.get('autoApprove', [])
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
            logger.info(f"Command: {server_config.command} {' '.join(server_config.args)}")
            
            # Create MCPToolset with StdioServerParameters
            toolset = await MCPToolset.create(
                connection_params=StdioServerParameters(
                    command=server_config.command,
                    args=server_config.args,
                    env=server_config.env or {}
                ),
                name=server_config.name,
                structured_output=False  # Set to False as requested
            )
            
            # Store toolset for cleanup
            self.toolsets.append(toolset)
            
            # Get tools from the toolset
            tools = toolset.tools if hasattr(toolset, 'tools') else []
            
            logger.info(f"Successfully loaded {len(tools)} tools from {server_config.name}")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to load tools from MCP server {server_config.name}: {e}")
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
                'command': config.command,
                'args': config.args,
                'disabled': config.disabled,
                'auto_approve_count': len(config.auto_approve)
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