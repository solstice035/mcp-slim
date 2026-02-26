"""CLI interface for mcp-slim."""

import asyncio
import json
import sys
from typing import Any, Optional

import click

from mcp_slim.client import MCPClient
from mcp_slim.config import ConfigManager, ServerNotFoundError
from mcp_slim.formatter import Formatter, OutputFormat


@click.group()
@click.version_option()
def cli() -> None:
    """MCP Slim - Lightweight CLI proxy for AI agents.
    
    Reduces token usage by providing compact tool listings and streamlined interactions
    with MCP servers.
    """
    pass


@cli.command()
@click.argument("server", required=False)
@click.option(
    "--compare",
    is_flag=True,
    help="Show token count comparison between slim and full formats",
)
@click.option(
    "--output",
    type=click.Choice(["text", "json", "minimal"]),
    default="text",
    help="Output format",
)
def list(server: Optional[str], compare: bool, output: str) -> None:
    """List available tools from MCP servers.
    
    If SERVER is provided, lists tools from that specific server.
    Otherwise, lists tools from all configured servers.
    """
    try:
        asyncio.run(_list_tools(server, compare, OutputFormat(output)))
    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def _list_tools(
    server_name: Optional[str], compare: bool, output_format: OutputFormat
) -> None:
    """Async implementation of list command."""
    config_manager = ConfigManager()
    formatter = Formatter(output_format)
    
    if server_name:
        servers = {server_name: config_manager.get_server(server_name)}
    else:
        servers = config_manager.get_all_servers()
    
    if not servers:
        click.echo("No MCP servers configured.", err=True)
        click.echo(
            f"Please configure servers in: {config_manager.config_path}",
            err=True,
        )
        sys.exit(1)
    
    all_tools = []
    
    for name, server_config in servers.items():
        try:
            async with MCPClient(server_config) as client:
                tools = await client.list_tools()
                for tool in tools:
                    tool_info = {
                        "server": name,
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    }
                    all_tools.append(tool_info)
        except Exception as e:
            click.echo(f"Warning: Failed to connect to server '{name}': {e}", err=True)
            continue
    
    if not all_tools:
        click.echo("No tools available from configured servers.", err=True)
        sys.exit(1)
    
    output = formatter.format_tools(all_tools, compare)
    click.echo(output)


@cli.command()
@click.argument("server")
@click.argument("tool")
@click.argument("args", nargs=-1)
@click.option(
    "--output",
    type=click.Choice(["text", "json", "minimal"]),
    default="text",
    help="Output format",
)
def call(server: str, tool: str, args: tuple[str, ...], output: str) -> None:
    """Call a tool on an MCP server.
    
    SERVER: Name of the MCP server
    TOOL: Name of the tool to call
    ARGS: Tool arguments in key=value format or as JSON
    
    Examples:
        mcp-slim call myserver mytool arg1=value1 arg2=value2
        mcp-slim call myserver mytool '{"arg1": "value1", "arg2": "value2"}'
    """
    try:
        asyncio.run(_call_tool(server, tool, args, OutputFormat(output)))
    except KeyboardInterrupt:
        click.echo("\nInterrupted", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def _call_tool(
    server_name: str, tool_name: str, args: tuple[str, ...], output_format: OutputFormat
) -> None:
    """Async implementation of call command."""
    config_manager = ConfigManager()
    formatter = Formatter(output_format)
    
    try:
        server_config = config_manager.get_server(server_name)
    except ServerNotFoundError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    
    # Parse arguments
    tool_args = _parse_arguments(args)
    
    async with MCPClient(server_config) as client:
        result = await client.call_tool(tool_name, tool_args)
        output = formatter.format_result(result)
        click.echo(output)


def _parse_arguments(args: tuple[str, ...]) -> dict[str, Any]:
    """Parse command-line arguments into a dictionary.
    
    Supports both key=value format and JSON format.
    """
    if not args:
        return {}
    
    # If single argument, try to parse as JSON
    if len(args) == 1:
        try:
            parsed = json.loads(args[0])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Parse as key=value pairs
    result: dict[str, Any] = {}
    for arg in args:
        if "=" not in arg:
            raise click.BadParameter(
                f"Invalid argument format: '{arg}'. Use key=value or JSON format."
            )
        
        key, value = arg.split("=", 1)
        
        # Try to parse value as JSON for complex types
        try:
            result[key] = json.loads(value)
        except json.JSONDecodeError:
            # Keep as string if not valid JSON
            result[key] = value
    
    return result


@cli.command()
@click.option(
    "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def config(output: str) -> None:
    """Show discovered MCP server configurations."""
    try:
        config_manager = ConfigManager()
        servers = config_manager.get_all_servers()
        
        if output == "json":
            output_data = {
                "config_path": str(config_manager.config_path),
                "servers": {
                    name: {
                        "command": server.command,
                        "args": server.args,
                        "env": server.env,
                    }
                    for name, server in servers.items()
                },
            }
            click.echo(json.dumps(output_data, indent=2))
        else:
            click.echo(f"Configuration file: {config_manager.config_path}")
            click.echo(f"\nConfigured servers ({len(servers)}):")
            
            if not servers:
                click.echo("  (none)")
            else:
                for name, server in servers.items():
                    click.echo(f"\n  {name}:")
                    click.echo(f"    Command: {server.command}")
                    if server.args:
                        click.echo(f"    Args: {' '.join(server.args)}")
                    if server.env:
                        click.echo(f"    Env vars: {len(server.env)} defined")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
