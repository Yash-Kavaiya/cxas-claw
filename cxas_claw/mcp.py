"""
MCPClient — wraps MCP server interactions for CX Agent Studio Playbook Server.
Optional dependency: pip install cxas-claw[mcp]
"""

from __future__ import annotations

import os
from typing import Any, Optional


class MCPClient:
    """
    Thin wrapper around the CX Agent Studio MCP server.
    Server URL is read from CXAS_MCP_SERVER_URL env var (default: http://localhost:8080/sse).
    """

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.environ.get(
            "CXAS_MCP_SERVER_URL", "http://localhost:8080/sse"
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import httpx  # type: ignore
                self._client = httpx.Client(base_url=self.server_url, timeout=30)
            except ImportError:
                raise ImportError(
                    "httpx is required for MCP support. "
                    "Install it with: pip install cxas-claw[mcp]"
                )
        return self._client

    def list_tools(self) -> list[dict]:
        client = self._get_client()
        response = client.get("/tools")
        response.raise_for_status()
        return response.json()

    def invoke_tool(self, tool_name: str, parameters: dict) -> Any:
        client = self._get_client()
        response = client.post(
            "/tools/invoke",
            json={"tool": tool_name, "parameters": parameters},
        )
        response.raise_for_status()
        return response.json()

    def health(self) -> dict:
        client = self._get_client()
        response = client.get("/health")
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
