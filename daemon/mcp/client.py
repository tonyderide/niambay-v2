import json
import subprocess
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger("niambay.mcp")

@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict

@dataclass
class MCPResult:
    content: Any
    is_error: bool = False

class MCPClient:
    """Client MCP générique — lance un serveur MCP et appelle ses outils."""

    def __init__(self, command: list[str], env: dict = None):
        """
        command: commande pour lancer le serveur MCP, ex: ["npx", "@anthropic/mcp-gmail"]
        env: variables d'environnement additionnelles
        """
        self.command = command
        self.env = env
        self._process = None
        self._request_id = 0

    def start(self):
        """Lance le process MCP server."""
        import os
        env = os.environ.copy()
        if self.env:
            env.update(self.env)
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        # Send initialize
        self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "niambay-daemon", "version": "1.0"}}})
        resp = self._recv()
        logger.info(f"MCP server started: {resp}")
        # Send initialized notification
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return resp

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, msg: dict):
        data = json.dumps(msg)
        self._process.stdin.write(f"Content-Length: {len(data)}\r\n\r\n{data}".encode())
        self._process.stdin.flush()

    def _recv(self) -> dict:
        # Read Content-Length header
        header = b""
        while True:
            byte = self._process.stdout.read(1)
            if not byte:
                raise ConnectionError("MCP server closed")
            header += byte
            if header.endswith(b"\r\n\r\n"):
                break

        # Parse content length
        length = 0
        for line in header.decode().split("\r\n"):
            if line.startswith("Content-Length:"):
                length = int(line.split(":")[1].strip())

        # Read body
        body = self._process.stdout.read(length)
        return json.loads(body)

    def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server."""
        self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}})
        resp = self._recv()
        tools = []
        for t in resp.get("result", {}).get("tools", []):
            tools.append(MCPTool(name=t["name"], description=t.get("description", ""), input_schema=t.get("inputSchema", {})))
        return tools

    def call_tool(self, tool_name: str, arguments: dict = None) -> MCPResult:
        """Call a tool on the MCP server."""
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments or {}}
        })
        resp = self._recv()
        result = resp.get("result", {})
        content = result.get("content", [])
        is_error = result.get("isError", False)
        return MCPResult(content=content, is_error=is_error)

    def stop(self):
        """Stop the MCP server process."""
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None
