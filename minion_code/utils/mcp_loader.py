#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) Tools Loader

This module provides functionality to load MCP tools from configuration files
and integrate them with MinionCodeAgent.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from minion.tools import AsyncBaseTool

try:
    from minion.tools.mcp.mcp_toolset import (
        MCPToolset,
        SSEServerParameters,
        StdioServerParameters,
        StreamableHTTPServerParameters,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPToolset = None
    SSEServerParameters = None
    StdioServerParameters = None
    StreamableHTTPServerParameters = None

from minion_code.utils.output_truncator import (
    MAX_TOKEN_LIMIT,
    MCPContentTooLargeError,
    check_mcp_output,
    save_large_output,
)

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
    4. ~/.minion.json
    5. ~/.claude/mcp.json
    6. ~/.claude-code/mcp.json
    7. ~/.minion-code/mcp.json
    8. ~/.config/minion-code/mcp.json (XDG standard)

    Args:
        project_dir: Project directory to search in (defaults to cwd)

    Returns:
        Path to config file if found, None otherwise
    """
    locations = get_mcp_config_locations(project_dir=project_dir)

    # Search project scope first
    for config_path in locations["project"]:
        if config_path.exists():
            logger.info(f"Found MCP config at project scope: {config_path}")
            return config_path

    # Then search user scope
    for config_path in locations["user"]:
        if config_path.exists():
            logger.info(f"Found MCP config at user scope: {config_path}")
            return config_path

    logger.debug("No MCP config file found in any standard location")
    return None


def get_mcp_config_locations(project_dir: Optional[Path] = None) -> Dict[str, List[Path]]:
    """
    Get all standard MCP config file locations.

    Returns:
        Dictionary with 'project' and 'user' scope locations
    """
    project_root = project_dir or Path.cwd()
    home = Path.home()
    xdg_config_home = Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    )

    return {
        "project": [
            project_root / ".mcp.json",
            project_root / ".claude" / "mcp.json",
            project_root / ".minion" / "mcp.json",
        ],
        "user": [
            home / ".minion.json",
            home / ".claude" / "mcp.json",
            home / ".claude-code" / "mcp.json",
            home / ".minion-code" / "mcp.json",
            xdg_config_home / "minion-code" / "mcp.json",
        ],
    }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    transport: str = "stdio"
    command: str = ""
    args: List[str] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None
    sse_read_timeout: Optional[float] = None
    disabled: bool = False
    auto_approve: List[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.auto_approve is None:
            self.auto_approve = []


class CachedMCPTool(AsyncBaseTool):
    """Wrap an MCP tool and materialize oversized output into a cache file."""

    def __init__(self, tool: Any, server_name: str):
        super().__init__()
        self._tool = tool
        self.server_name = server_name
        self.name = getattr(tool, "name", "mcp_tool")
        self.tool_name = getattr(tool, "tool_name", self.name)
        self.description = getattr(tool, "description", "")
        self.inputs = getattr(tool, "inputs", {})
        self.parameters = getattr(tool, "parameters", None)
        self.__name__ = getattr(tool, "__name__", self.name)
        self.__doc__ = getattr(tool, "__doc__", self.description)
        self.__input_schema__ = getattr(tool, "__input_schema__", None)

    async def forward(self, *args, **kwargs):
        result = await self._tool.forward(*args, **kwargs)
        output = _stringify_mcp_output(result)

        try:
            check_mcp_output(output)
            return result
        except MCPContentTooLargeError as exc:
            return _build_large_mcp_output_message(
                output=output,
                tool_name=self.tool_name,
                server_name=self.server_name,
                token_count=exc.token_count,
            )


def _stringify_mcp_output(result: Any) -> str:
    """Convert MCP tool output into text for size checks and caching."""
    if isinstance(result, str):
        return result
    if result is None:
        return ""
    if isinstance(result, (int, float, bool)):
        return str(result)
    try:
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(result)


def _build_large_mcp_output_message(
    output: str,
    tool_name: str,
    server_name: str,
    token_count: Optional[int],
) -> str:
    """Persist oversized MCP output and return a file_read-oriented fallback."""
    preview_limit = 4_000
    preview = output[:preview_limit]
    if len(output) > preview_limit:
        preview += "\n...[truncated preview]..."

    try:
        cache_tool_name = f"mcp-{server_name}-{tool_name}".replace("/", "-")
        saved_path = save_large_output(output, cache_tool_name)
    except Exception as exc:
        logger.warning("Failed to save oversized MCP output: %s", exc)
        saved_path = None

    lines = [
        (
            "MCP tool output too large to inline "
            f"(approx {token_count or 'unknown'} tokens > {MAX_TOKEN_LIMIT} limit)."
        ),
    ]
    if preview:
        lines.extend(["Preview:", preview])
    if saved_path:
        lines.append(f"Full output saved to: {saved_path}")
        lines.append("Use file_read with offset/limit to inspect the cached result.")
    else:
        lines.append("Full output could not be cached; narrow the MCP query and retry.")
    return "\n".join(lines)


class MCPToolsLoader:
    """Loader for MCP tools from configuration files."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        auto_discover: bool = True,
        project_dir: Optional[Path] = None,
    ):
        """
        Initialize MCP tools loader.

        Args:
            config_path: Path to MCP configuration file. If None and auto_discover=True,
                        will search standard locations.
            auto_discover: If True and config_path is None, automatically search for
                          config in standard locations (.mcp.json, .claude/, .minion/, etc.)
        """
        self.project_dir = (project_dir or Path.cwd()).resolve()

        if config_path:
            self.config_path = Path(config_path).expanduser().resolve()
        elif auto_discover:
            self.config_path = find_mcp_config(project_dir=self.project_dir)
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
            self.config_path = Path(config_path).expanduser().resolve()

        if not self.config_path or not self.config_path.exists():
            logger.warning(f"MCP config file not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            self.servers = {}
            servers_config = self._extract_servers_config(config_data)

            for server_name, server_data in servers_config.items():
                parsed = self._parse_server_config(server_name, server_data)
                if parsed is not None:
                    self.servers[server_name] = parsed

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
            logger.info(self._describe_server(server_config))

            toolset = await MCPToolset.create(
                connection_params=self._build_connection_params(server_config),
                name=server_config.name,
                structured_output=False,  # Set to False as requested
            )

            # Store toolset for cleanup
            self.toolsets.append(toolset)

            # Get tools from the toolset
            tools = []
            if hasattr(toolset, "tools"):
                tools = [
                    CachedMCPTool(tool, server_config.name) for tool in toolset.tools
                ]
                toolset.tools = tools

            logger.info(
                f"Successfully loaded {len(tools)} tools from {server_config.name}"
            )
            return tools

        except Exception as e:
            logger.error(
                f"Failed to load tools from MCP server {server_config.name}: {e}"
            )
            return []

    def _extract_servers_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract effective mcpServers from root config and matched Claude project blocks."""
        effective_servers: Dict[str, Any] = {}

        root_servers = config_data.get("mcpServers", {})
        if isinstance(root_servers, dict):
            effective_servers.update(root_servers)

        matching_project = self._find_matching_project_config(config_data)
        if matching_project:
            project_servers = matching_project.get("mcpServers", {})
            if isinstance(project_servers, dict):
                effective_servers.update(project_servers)

        return effective_servers

    def _find_matching_project_config(
        self, config_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Return the closest matching Claude-style per-project config block."""
        projects = config_data.get("projects")
        if not isinstance(projects, dict):
            return None

        current = self.project_dir
        matches: List[tuple[int, Dict[str, Any]]] = []
        for raw_path, project_config in projects.items():
            if not isinstance(project_config, dict):
                continue
            try:
                candidate = Path(raw_path).expanduser().resolve()
            except Exception:
                continue

            if candidate == current or candidate in current.parents:
                matches.append((len(str(candidate)), project_config))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def _parse_server_config(
        self, server_name: str, server_data: Any
    ) -> Optional[MCPServerConfig]:
        """Parse one MCP server entry from Claude-style or legacy config JSON."""
        if not isinstance(server_data, dict):
            logger.warning("Skipping MCP server %s with invalid config", server_name)
            return None

        transport = str(server_data.get("type") or "").strip().lower()
        if not transport:
            transport = "stdio" if server_data.get("command") else "http"
        if transport == "streamable_http":
            transport = "streamable-http"

        return MCPServerConfig(
            name=server_name,
            transport=transport,
            command=str(server_data.get("command", "")),
            args=[str(arg) for arg in server_data.get("args", [])],
            env={
                str(key): str(value)
                for key, value in (server_data.get("env") or {}).items()
            },
            cwd=server_data.get("cwd"),
            url=server_data.get("url"),
            headers=server_data.get("headers"),
            timeout=server_data.get("timeout"),
            sse_read_timeout=server_data.get("sse_read_timeout"),
            disabled=server_data.get("disabled", False),
            auto_approve=server_data.get("autoApprove", []),
        )

    def _build_connection_params(self, server_config: MCPServerConfig) -> Any:
        """Build minion MCP connection params for stdio, SSE, or streamable HTTP."""
        if server_config.transport == "stdio":
            return StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env or {},
                cwd=server_config.cwd,
            )

        if server_config.transport == "sse":
            return SSEServerParameters(
                url=server_config.url or "",
                headers=server_config.headers or {},
                timeout=server_config.timeout,
                sse_read_timeout=server_config.sse_read_timeout,
            )

        if server_config.transport in {"http", "streamable-http"}:
            return StreamableHTTPServerParameters(
                url=server_config.url or "",
                headers=server_config.headers or {},
                timeout=server_config.timeout,
                sse_read_timeout=server_config.sse_read_timeout,
            )

        raise ValueError(
            f"Unsupported MCP transport '{server_config.transport}' for {server_config.name}"
        )

    def _describe_server(self, server_config: MCPServerConfig) -> str:
        """Return a concise human-readable server description for logs."""
        if server_config.transport == "stdio":
            return f"Command: {server_config.command} {' '.join(server_config.args)}"
        return (
            f"Transport: {server_config.transport} "
            f"URL: {server_config.url or '<missing>'}"
        )

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
                "transport": config.transport,
                "command": config.command,
                "args": config.args,
                "url": config.url,
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
