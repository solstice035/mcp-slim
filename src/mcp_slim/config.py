"""Configuration management for MCP servers."""

import json
import os
import platform
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    
    command: str = Field(..., description="Command to execute the server")
    args: Optional[list[str]] = Field(default=None, description="Command arguments")
    env: Optional[dict[str, str]] = Field(default=None, description="Environment variables")


class ServerNotFoundError(Exception):
    """Raised when a requested server is not found in configuration."""
    pass


class ConfigManager:
    """Manages MCP server configurations from Claude Desktop config format."""
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize configuration manager.
        
        Args:
            config_path: Optional path to config file. If not provided, uses default location.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._servers: Optional[dict[str, ServerConfig]] = None
    
    @staticmethod
    def _get_default_config_path() -> Path:
        """Get the default configuration path based on the operating system.
        
        Returns:
            Path to the Claude Desktop configuration file
        """
        system = platform.system()
        
        if system == "Darwin":  # macOS
            base_path = Path.home() / "Library" / "Application Support" / "Claude"
        elif system == "Windows":
            app_data = os.getenv("APPDATA")
            if not app_data:
                raise RuntimeError("APPDATA environment variable not set")
            base_path = Path(app_data) / "Claude"
        else:  # Linux and others
            config_home = os.getenv("XDG_CONFIG_HOME")
            if config_home:
                base_path = Path(config_home) / "claude"
            else:
                base_path = Path.home() / ".config" / "claude"
        
        return base_path / "claude_desktop_config.json"
    
    def _load_config(self) -> dict[str, ServerConfig]:
        """Load and parse the configuration file.
        
        Returns:
            Dictionary mapping server names to ServerConfig objects
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                "Please configure MCP servers in Claude Desktop first."
            )
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        
        # Extract mcpServers section
        mcp_servers = config_data.get("mcpServers", {})
        
        if not isinstance(mcp_servers, dict):
            raise ValueError("'mcpServers' must be a dictionary")
        
        # Parse each server configuration
        servers: dict[str, ServerConfig] = {}
        for name, server_data in mcp_servers.items():
            try:
                servers[name] = ServerConfig(**server_data)
            except Exception as e:
                raise ValueError(f"Invalid configuration for server '{name}': {e}") from e
        
        return servers
    
    def get_all_servers(self) -> dict[str, ServerConfig]:
        """Get all configured servers.
        
        Returns:
            Dictionary mapping server names to ServerConfig objects
        """
        if self._servers is None:
            try:
                self._servers = self._load_config()
            except FileNotFoundError:
                self._servers = {}
        
        return self._servers
    
    def get_server(self, name: str) -> ServerConfig:
        """Get configuration for a specific server.
        
        Args:
            name: Name of the server
            
        Returns:
            ServerConfig for the requested server
            
        Raises:
            ServerNotFoundError: If server is not found in configuration
        """
        servers = self.get_all_servers()
        
        if name not in servers:
            available = ", ".join(servers.keys()) if servers else "(none)"
            raise ServerNotFoundError(
                f"Server '{name}' not found in configuration.\n"
                f"Available servers: {available}"
            )
        
        return servers[name]
