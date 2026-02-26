"""MCP client implementation using stdio transport."""

import asyncio
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool, CallToolResult

from mcp_slim.config import ServerConfig


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class ToolNotFoundError(MCPClientError):
    """Raised when a requested tool is not found."""
    pass


class MCPClient:
    """Client for connecting to MCP servers via stdio transport."""
    
    def __init__(self, config: ServerConfig) -> None:
        """Initialize MCP client with server configuration.
        
        Args:
            config: Server configuration containing command, args, and env
        """
        self.config = config
        self.session: Optional[ClientSession] = None
        self._read_stream: Optional[Any] = None
        self._write_stream: Optional[Any] = None
        self._exit_stack: Optional[Any] = None
    
    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Connect to the MCP server."""
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args or [],
            env=self.config.env or {},
        )
        
        try:
            # Create stdio connection
            from contextlib import AsyncExitStack
            
            self._exit_stack = AsyncExitStack()
            self._read_stream, self._write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # Initialize session
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(self._read_stream, self._write_stream)
            )
            
            # Initialize the connection
            await self.session.initialize()
            
        except Exception as e:
            if self._exit_stack:
                await self._exit_stack.aclose()
            raise MCPClientError(f"Failed to connect to MCP server: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self.session = None
        self._read_stream = None
        self._write_stream = None
    
    async def list_tools(self) -> list[Tool]:
        """List all available tools from the server.
        
        Returns:
            List of Tool objects
            
        Raises:
            MCPClientError: If not connected or request fails
        """
        if not self.session:
            raise MCPClientError("Not connected to server")
        
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            raise MCPClientError(f"Failed to list tools: {e}") from e
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Call a tool on the server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Result from the tool call
            
        Raises:
            MCPClientError: If not connected or request fails
            ToolNotFoundError: If the tool doesn't exist
        """
        if not self.session:
            raise MCPClientError("Not connected to server")
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower() or "unknown tool" in error_msg.lower():
                raise ToolNotFoundError(f"Tool '{tool_name}' not found") from e
            raise MCPClientError(f"Failed to call tool '{tool_name}': {e}") from e
