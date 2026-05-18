"""MCP (Model Context Protocol) client for AgenticOs.

Connects to external MCP servers (e.g. GitHub, databases, Slack) via the
JSON-RPC 2.0 protocol over stdio, discovers their tools, and registers them
in the AgenticOs ToolRegistry under an ``mcp:<server_name>`` namespace.

Config example (config.yaml)::

    mcp_servers:
      - name: github
        command: npx
        args: ["-y", "@modelcontextprotocol/server-github"]
        env:
          GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_TOKEN}"
      - name: filesystem
        command: npx
        args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]

Reference: https://modelcontextprotocol.io/docs/concepts/transports
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPServerProcess:
    """Wraps a single MCP server subprocess and handles JSON-RPC communication.

    Protocol:
    - Requests/responses are newline-delimited JSON-RPC 2.0 objects written to
      the process's stdin/stdout.
    - Notifications and errors are logged but do not block callers.
    """

    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = self._build_env(env or {})
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._id_counter = 0
        self.tools: List[Dict[str, Any]] = []
        self._ready = False

    def _build_env(self, extra: Dict[str, str]) -> Dict[str, str]:
        """Merge extra env vars (expanding ${VAR} references) with the current env."""
        merged = dict(os.environ)
        for k, v in extra.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                merged[k] = os.environ.get(env_key, "")
            else:
                merged[k] = str(v)
        return merged

    def start(self) -> bool:
        """Start the subprocess. Returns True on success."""
        try:
            cmd = [self.command] + self.args
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.env,
                text=True,
            )
            # Allow process to initialise
            time.sleep(0.3)
            if self._proc.poll() is not None:
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                logger.error("MCP server '%s' exited immediately: %s", self.name, stderr)
                return False
            self._ready = True
            logger.info("MCP server '%s' started (pid=%d)", self.name, self._proc.pid)
            return True
        except FileNotFoundError:
            logger.error(
                "MCP server '%s': command not found: '%s'", self.name, self.command
            )
            return False
        except Exception as exc:
            logger.error("MCP server '%s' failed to start: %s", self.name, exc)
            return False

    def stop(self):
        """Terminate the subprocess."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._ready = False

    # ------------------------------------------------------------------
    # JSON-RPC helpers
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _send(self, method: str, params: Any = None) -> Any:
        """Send a JSON-RPC request and return the result field."""
        if not self._ready or self._proc is None:
            raise RuntimeError(f"MCP server '{self.name}' is not running")
        if self._proc.poll() is not None:
            raise RuntimeError(f"MCP server '{self.name}' has exited")

        rpc_id = self._next_id()
        request = {"jsonrpc": "2.0", "id": rpc_id, "method": method}
        if params is not None:
            request["params"] = params

        with self._lock:
            line = json.dumps(request) + "\n"
            try:
                self._proc.stdin.write(line)
                self._proc.stdin.flush()
            except BrokenPipeError as exc:
                raise RuntimeError(f"MCP server '{self.name}' stdin closed") from exc

            # Read until we get the response for our id
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                raw = self._proc.stdout.readline()
                if not raw:
                    raise RuntimeError(f"MCP server '{self.name}' stdout closed")
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == rpc_id:
                    if "error" in msg:
                        raise RuntimeError(
                            f"MCP error: {msg['error'].get('message', msg['error'])}"
                        )
                    return msg.get("result")
            raise TimeoutError(f"MCP server '{self.name}' did not respond in 30s")

    # ------------------------------------------------------------------
    # MCP protocol
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Send the MCP initialize handshake and discover tools."""
        try:
            self._send("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AgenticOs", "version": "2.1"},
            })
            self._send("notifications/initialized")
        except Exception as exc:
            logger.warning("MCP '%s' initialize failed: %s", self.name, exc)
            # Some servers skip initialize — try listing tools directly.

        return self.list_tools()

    def list_tools(self) -> bool:
        """Fetch the server's tool list and store in ``self.tools``."""
        try:
            result = self._send("tools/list")
            if result and isinstance(result, dict):
                self.tools = result.get("tools", [])
                logger.info(
                    "MCP '%s': discovered %d tools", self.name, len(self.tools)
                )
                return True
        except Exception as exc:
            logger.error("MCP '%s' tools/list failed: %s", self.name, exc)
        return False

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the server and return its result content."""
        result = self._send("tools/call", {"name": tool_name, "arguments": arguments})
        if result is None:
            return ""
        # MCP returns {"content": [...], "isError": bool}
        content = result.get("content", [])
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts) if parts else str(result)


# ---------------------------------------------------------------------------
# MCPClient — manages multiple servers
# ---------------------------------------------------------------------------


class MCPClient:
    """Manages multiple MCP server connections.

    Args:
        cfg: Agent configuration dict (reads ``mcp_servers`` list).
        register_fn: Optional callback to register a new tool into ToolRegistry.
                     Signature: ``(full_tool_name: str, fn: Callable) -> None``.
    """

    def __init__(
        self,
        cfg: Optional[Dict] = None,
        register_fn: Optional[Callable[[str, Callable], None]] = None,
    ):
        self.cfg = cfg or {}
        self.register_fn = register_fn
        self._servers: Dict[str, MCPServerProcess] = {}

    def connect_all(self):
        """Start all configured MCP servers and register their tools."""
        server_configs = self.cfg.get("mcp_servers") or []
        for sc in server_configs:
            name = sc.get("name", "")
            if not name:
                continue
            self.connect_server(sc)

    def connect_server(self, server_config: Dict[str, Any]) -> bool:
        """Start a single MCP server and register its tools.

        Returns True if the server started and tools were discovered.
        """
        name = server_config.get("name", "")
        command = server_config.get("command", "")
        args = server_config.get("args") or []
        env = server_config.get("env") or {}

        if not name or not command:
            logger.error("MCP server config missing 'name' or 'command': %s", server_config)
            return False

        server = MCPServerProcess(name=name, command=command, args=args, env=env)
        if not server.start():
            return False

        server.initialize()

        if self.register_fn:
            for tool_def in server.tools:
                self._register_tool(server, tool_def)

        self._servers[name] = server
        logger.info("MCP: connected to '%s' (%d tools)", name, len(server.tools))
        return True

    def _register_tool(self, server: MCPServerProcess, tool_def: Dict[str, Any]):
        """Create a wrapper callable and register it with the ToolRegistry."""
        tool_name = tool_def.get("name", "")
        if not tool_name or not self.register_fn:
            return

        full_name = f"mcp:{server.name}:{tool_name}"
        desc = tool_def.get("description", f"MCP tool from server '{server.name}'")

        def _caller(**kwargs):
            return server.call_tool(tool_name, kwargs)

        _caller.__name__ = full_name
        _caller.__doc__ = desc

        try:
            self.register_fn(full_name, _caller)
            logger.debug("MCP: registered tool '%s'", full_name)
        except Exception as exc:
            logger.warning("MCP: could not register '%s': %s", full_name, exc)

    def list_all_tools(self) -> List[Dict[str, Any]]:
        """Return a list of all discovered tools across all servers."""
        result = []
        for name, server in self._servers.items():
            for tool_def in server.tools:
                result.append({
                    "server": name,
                    "tool": tool_def.get("name"),
                    "description": tool_def.get("description", ""),
                    "full_name": f"mcp:{name}:{tool_def.get('name')}",
                })
        return result

    def stop_all(self):
        """Stop all running MCP servers."""
        for server in self._servers.values():
            server.stop()
        self._servers.clear()
