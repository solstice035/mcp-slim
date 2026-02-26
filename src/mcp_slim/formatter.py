"""Output formatting utilities for compact tool listings."""

import json
from enum import Enum
from typing import Any


class OutputFormat(Enum):
    """Output format options."""
    
    TEXT = "text"
    JSON = "json"
    MINIMAL = "minimal"


class Formatter:
    """Formats tool information and results in various output formats."""
    
    def __init__(self, output_format: OutputFormat = OutputFormat.TEXT) -> None:
        """Initialize formatter with output format.
        
        Args:
            output_format: Desired output format
        """
        self.output_format = output_format
    
    def format_tools(self, tools: list[dict[str, Any]], compare: bool = False) -> str:
        """Format a list of tools for display.
        
        Args:
            tools: List of tool dictionaries with server, name, description, parameters
            compare: Whether to include token count comparison
            
        Returns:
            Formatted string representation of tools
        """
        if self.output_format == OutputFormat.JSON:
            return json.dumps(tools, indent=2)
        
        if self.output_format == OutputFormat.MINIMAL:
            return self._format_tools_minimal(tools)
        
        # TEXT format
        return self._format_tools_text(tools, compare)
    
    def _format_tools_text(self, tools: list[dict[str, Any]], compare: bool) -> str:
        """Format tools in human-readable text table."""
        if not tools:
            return "No tools available."
        
        lines = []
        
        # Header
        lines.append("Available Tools:")
        lines.append("=" * 100)
        lines.append(f"{'Server':<20} {'Tool':<25} {'Description':<55}")
        lines.append("-" * 100)
        
        # Tools
        for tool in tools:
            server = tool["server"][:19]
            name = tool["name"][:24]
            desc = tool["description"][:54] if tool["description"] else "(no description)"
            lines.append(f"{server:<20} {name:<25} {desc:<55}")
            
            # Show parameter summary
            params = self._summarize_parameters(tool["parameters"])
            if params:
                lines.append(f"{'':20} {'':25} Args: {params}")
        
        lines.append("=" * 100)
        lines.append(f"Total: {len(tools)} tools")
        
        # Add token comparison if requested
        if compare:
            lines.append("")
            lines.append(self._format_token_comparison(tools))
        
        return "\n".join(lines)
    
    def _format_tools_minimal(self, tools: list[dict[str, Any]]) -> str:
        """Format tools in minimal one-line-per-tool format."""
        lines = []
        for tool in tools:
            params = self._summarize_parameters(tool["parameters"])
            param_str = f" ({params})" if params else ""
            desc = tool["description"] or "no description"
            lines.append(f"{tool['server']}.{tool['name']}{param_str} - {desc}")
        return "\n".join(lines)
    
    def _summarize_parameters(self, schema: dict[str, Any]) -> str:
        """Create a compact summary of parameter schema.
        
        Args:
            schema: JSON schema for parameters
            
        Returns:
            Compact string summary like "name:str, age:int"
        """
        if not schema or "properties" not in schema:
            return ""
        
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        
        params = []
        for name, prop in properties.items():
            type_str = prop.get("type", "any")
            optional = "" if name in required else "?"
            params.append(f"{name}{optional}:{type_str}")
        
        return ", ".join(params)
    
    def _format_token_comparison(self, tools: list[dict[str, Any]]) -> str:
        """Format token count comparison between slim and full formats.
        
        Args:
            tools: List of tool dictionaries
            
        Returns:
            Formatted comparison string
        """
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        slim_output = self._format_tools_minimal(tools)
        slim_tokens = len(slim_output) // 4
        
        full_output = json.dumps(tools, indent=2)
        full_tokens = len(full_output) // 4
        
        savings = full_tokens - slim_tokens
        savings_pct = (savings / full_tokens * 100) if full_tokens > 0 else 0
        
        lines = [
            "Token Usage Comparison:",
            f"  Slim format:  ~{slim_tokens:,} tokens",
            f"  Full JSON:    ~{full_tokens:,} tokens",
            f"  Savings:      ~{savings:,} tokens ({savings_pct:.1f}%)",
        ]
        
        return "\n".join(lines)
    
    def format_result(self, result: Any) -> str:
        """Format a tool call result.
        
        Args:
            result: Result from tool call
            
        Returns:
            Formatted string representation
        """
        if self.output_format == OutputFormat.JSON:
            # Convert result to JSON-serializable format
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif hasattr(result, "__dict__"):
                result_dict = result.__dict__
            else:
                result_dict = {"result": str(result)}
            return json.dumps(result_dict, indent=2)
        
        # For TEXT and MINIMAL, extract content
        if hasattr(result, "content"):
            content = result.content
            if isinstance(content, list):
                # Handle list of content items
                parts = []
                for item in content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    elif hasattr(item, "type") and hasattr(item, "data"):
                        parts.append(f"[{item.type}]: {item.data}")
                    else:
                        parts.append(str(item))
                return "\n".join(parts)
            return str(content)
        
        return str(result)
