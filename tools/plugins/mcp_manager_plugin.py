"""MCP manager plugin for AgenticOs.

Exposes two tools:
- ``connect_mcp_server`` — dynamically connect to an MCP server at runtime
- ``list_mcp_tools`` — list all tools discovered from all connected MCP servers
"""

from core.tool_registry import tool

_MCP_CLIENT = None


def _get_client():
    global _MCP_CLIENT
    if _MCP_CLIENT is None:
        try:
            from core.mcp_client import MCPClient

            _MCP_CLIENT = MCPClient()
        except Exception:
            pass
    return _MCP_CLIENT


@tool(
    name="connect_mcp_server",
    desc="Connect to an MCP server at runtime. Args: name, command, args_str (space-separated), env_json (optional JSON string).",
    category="meta",
    version="1.0.0",
)
def connect_mcp_server(
    name: str,
    command: str,
    args_str: str = "",
    env_json: str = "",
) -> str:
    """Connect to an MCP server and register its tools.

    Args:
        name: Server name (used as prefix for tool names, e.g. 'github').
        command: Executable to launch (e.g. 'npx').
        args_str: Space-separated arguments for the command.
        env_json: Optional JSON string of environment variables.

    Returns:
        Status message listing discovered tools.
    """
    import json as _json

    client = _get_client()
    if client is None:
        return "Error: MCPClient could not be initialised."

    args = args_str.split() if args_str else []
    env = {}
    if env_json:
        try:
            env = _json.loads(env_json)
        except Exception:
            return f"Error: env_json is not valid JSON: {env_json}"

    config = {"name": name, "command": command, "args": args, "env": env}
    ok = client.connect_server(config)
    if not ok:
        return f"Failed to connect to MCP server '{name}'. Check the command and arguments."

    tools = [t for t in client.list_all_tools() if t["server"] == name]
    if not tools:
        return f"Connected to '{name}' but no tools were discovered."

    lines = [f"Connected to MCP server '{name}'. Discovered {len(tools)} tools:"]
    for t in tools:
        lines.append(f"  • {t['full_name']}: {t['description']}")
    return "\n".join(lines)


@tool(
    name="list_mcp_tools",
    desc="List all tools available from all connected MCP servers.",
    category="meta",
    version="1.0.0",
)
def list_mcp_tools() -> str:
    """Return a formatted list of all MCP tools across all connected servers.

    Returns:
        Human-readable list of server/tool names and descriptions.
    """
    client = _get_client()
    if client is None:
        return "No MCP client initialised."

    tools = client.list_all_tools()
    if not tools:
        return "No MCP servers connected or no tools discovered."

    lines = ["MCP Tools:"]
    current_server = None
    for t in tools:
        if t["server"] != current_server:
            current_server = t["server"]
            lines.append(f"\n  Server: {current_server}")
        lines.append(f"    • {t['tool']}: {t['description']}")
    return "\n".join(lines)
