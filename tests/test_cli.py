"""Tests for CLI functionality."""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from mcp_slim.cli import cli
from mcp_slim.config import ConfigManager, ServerConfig
from mcp_slim.formatter import Formatter, OutputFormat


@pytest.fixture
def sample_config_data() -> dict[str, Any]:
    """Sample configuration data."""
    return {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": ["-m", "test_server"],
                "env": {"TEST_VAR": "test_value"},
            },
            "another-server": {
                "command": "node",
                "args": ["server.js"],
            },
        }
    }


@pytest.fixture
def temp_config_file(tmp_path: Path, sample_config_data: dict[str, Any]) -> Path:
    """Create a temporary config file."""
    config_file = tmp_path / "claude_desktop_config.json"
    with open(config_file, "w") as f:
        json.dump(sample_config_data, f)
    return config_file


def test_config_manager_load(temp_config_file: Path) -> None:
    """Test loading configuration from file."""
    manager = ConfigManager(config_path=temp_config_file)
    servers = manager.get_all_servers()
    
    assert len(servers) == 2
    assert "test-server" in servers
    assert "another-server" in servers
    
    test_server = servers["test-server"]
    assert test_server.command == "python"
    assert test_server.args == ["-m", "test_server"]
    assert test_server.env == {"TEST_VAR": "test_value"}


def test_config_manager_get_server(temp_config_file: Path) -> None:
    """Test getting a specific server configuration."""
    manager = ConfigManager(config_path=temp_config_file)
    server = manager.get_server("test-server")
    
    assert server.command == "python"
    assert server.args == ["-m", "test_server"]


def test_config_manager_server_not_found(temp_config_file: Path) -> None:
    """Test error when server is not found."""
    from mcp_slim.config import ServerNotFoundError
    
    manager = ConfigManager(config_path=temp_config_file)
    
    with pytest.raises(ServerNotFoundError) as exc_info:
        manager.get_server("nonexistent")
    
    assert "nonexistent" in str(exc_info.value)


def test_formatter_text_output() -> None:
    """Test text formatting of tools."""
    formatter = Formatter(OutputFormat.TEXT)
    tools = [
        {
            "server": "test-server",
            "name": "test-tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                    "arg2": {"type": "integer"},
                },
                "required": ["arg1"],
            },
        }
    ]
    
    output = formatter.format_tools(tools, compare=False)
    
    assert "test-server" in output
    assert "test-tool" in output
    assert "A test tool" in output
    assert "arg1" in output


def test_formatter_json_output() -> None:
    """Test JSON formatting of tools."""
    formatter = Formatter(OutputFormat.JSON)
    tools = [
        {
            "server": "test-server",
            "name": "test-tool",
            "description": "A test tool",
            "parameters": {},
        }
    ]
    
    output = formatter.format_tools(tools, compare=False)
    parsed = json.loads(output)
    
    assert len(parsed) == 1
    assert parsed[0]["name"] == "test-tool"


def test_formatter_minimal_output() -> None:
    """Test minimal formatting of tools."""
    formatter = Formatter(OutputFormat.MINIMAL)
    tools = [
        {
            "server": "test-server",
            "name": "test-tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                },
            },
        }
    ]
    
    output = formatter.format_tools(tools, compare=False)
    
    assert "test-server.test-tool" in output
    assert "A test tool" in output


def test_formatter_token_comparison() -> None:
    """Test token comparison output."""
    formatter = Formatter(OutputFormat.TEXT)
    tools = [
        {
            "server": "test-server",
            "name": "test-tool",
            "description": "A test tool",
            "parameters": {},
        }
    ]
    
    output = formatter.format_tools(tools, compare=True)
    
    assert "Token Usage Comparison" in output
    assert "Slim format" in output
    assert "Full JSON" in output
    assert "Savings" in output


def test_cli_config_command(temp_config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config command."""
    # Monkeypatch the default config path
    monkeypatch.setattr(
        ConfigManager, "_get_default_config_path",
        staticmethod(lambda: temp_config_file),
    )
    
    runner = CliRunner()
    result = runner.invoke(cli, ["config"])
    
    assert result.exit_code == 0
    assert "test-server" in result.output
    assert "another-server" in result.output


def test_cli_config_command_json(temp_config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test config command with JSON output."""
    monkeypatch.setattr(
        ConfigManager, "_get_default_config_path",
        staticmethod(lambda: temp_config_file),
    )
    
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--output", "json"])
    
    assert result.exit_code == 0
    output_data = json.loads(result.output)
    assert "servers" in output_data
    assert "test-server" in output_data["servers"]


def test_server_config_validation() -> None:
    """Test ServerConfig validation."""
    # Valid config
    config = ServerConfig(command="python", args=["-m", "test"])
    assert config.command == "python"
    assert config.args == ["-m", "test"]
    
    # Missing required field
    with pytest.raises(Exception):
        ServerConfig()  # type: ignore


def test_parameter_summarization() -> None:
    """Test parameter schema summarization."""
    formatter = Formatter()
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "email": {"type": "string"},
        },
        "required": ["name", "age"],
    }
    
    summary = formatter._summarize_parameters(schema)
    
    assert "name:string" in summary
    assert "age:integer" in summary
    assert "email?:string" in summary  # Optional parameter
