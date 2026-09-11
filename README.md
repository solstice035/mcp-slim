# MCP Slim

> **Built by [The Foundry](https://github.com/solstice035/the-foundry)**, an autonomous build pipeline I run. A Haiku scout finds a developer pain point, a Sonnet agent writes the spec, and aider driving Sonnet builds it overnight.
>
> This repo was produced end to end by that pipeline. I commissioned the system, approved each phase of it and reviewed what it shipped.

A lightweight CLI proxy for AI agents that dramatically reduces token usage compared to full MCP. Instead of verbose JSON-RPC tool schemas flooding the context window, mcp-slim exposes tools as compact CLI commands with minimal descriptions — cutting token overhead by 60-80% while maintaining tool functionality.

## Installation

```bash
pip install mcp-slim
# or
pipx install mcp-slim
# or from source
git clone https://github.com/solstice035/mcp-slim.git
cd mcp-slim && pip install -e .
```

## Configuration

MCP Slim reads server configurations from the Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Example config:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "your-token-here" }
    }
  }
}
```

## Usage

### Show configured servers

```bash
mcp-slim config
mcp-slim config --output json
```

### List available tools

```bash
mcp-slim list                      # All servers
mcp-slim list filesystem           # Specific server
mcp-slim list --compare            # Show token savings
mcp-slim list --output minimal     # One line per tool
mcp-slim list --output json        # Full JSON
```

Example output (text):

```
Available Tools:
====================================================================================================
Server               Tool                      Description
----------------------------------------------------------------------------------------------------
filesystem           read_file                 Read the complete contents of a file
                                               Args: path:string
filesystem           write_file                Create a new file or overwrite existing
                                               Args: path:string, content:string
====================================================================================================
Total: 2 tools
```

Example output (minimal):

```
filesystem.read_file (path:string) - Read the complete contents of a file
filesystem.write_file (path:string, content:string) - Create a new file or overwrite existing
```

### Call a tool

```bash
# Key=value arguments
mcp-slim call filesystem read_file path=/path/to/file.txt

# JSON arguments
mcp-slim call github create_issue '{"owner":"user","repo":"project","title":"Bug report"}'

# With output format
mcp-slim call filesystem read_file path=/file.txt --output json
```

## Token Savings

| Format | Example Tool | ~Tokens |
|--------|-------------|---------|
| Full MCP JSON Schema | `{"name":"read_file","description":"Read the complete contents...","inputSchema":{"type":"object","properties":{"path":{"type":"string","description":"Path to the file"}},"required":["path"]}}` | ~50 |
| MCP Slim (minimal) | `filesystem.read_file (path:string) - Read the complete contents of a file` | ~15 |

**~70% reduction per tool.** For a server with 10-20 tools, that's 300-500 tokens saved per listing.

## Development

```bash
pip install -e ".[dev]"
pytest
black src tests
mypy src
```

## Requirements

- Python 3.10+
- MCP servers configured in Claude Desktop format

## License

MIT
