"""
Smoke test for the local Java backend + MCP proxies.

This runs *no real Gmail/Calendar actions* by default:
  - Checks Java health endpoints (/health/mcp and /health/mcp2)
  - Connects to MCP SSE endpoints (/mcp/sse and /mcp2/sse)
  - Lists available tools for each MCP server
  - Calls a safe Email MCP tool (employee_list) which uses local SQLite + stub Gmail by default

Usage:
  ./.venv-mcp/bin/python scripts/smoke_test_backend.py

If your Java backend is on a different port, override with:
  JAVA_BASE_URL=http://127.0.0.1:8080 ./.venv-mcp/bin/python scripts/smoke_test_backend.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client


JAVA_BASE_URL = os.environ.get("JAVA_BASE_URL", "http://127.0.0.1:8082").rstrip("/")


async def get_json(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5) as client:
        res = await client.get(url)
        res.raise_for_status()
        return res.json()


async def list_tools(sse_url: str) -> list[str]:
    async with sse_client(sse_url, timeout=5, sse_read_timeout=20) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [t.name for t in (result.tools or [])]


async def call_tool(sse_url: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    async with sse_client(sse_url, timeout=5, sse_read_timeout=20) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            # Prefer structured content if provided by the server.
            if result.structuredContent is not None:
                return {"structuredContent": result.structuredContent, "isError": result.isError}
            return {
                "content": [c.model_dump() for c in (result.content or [])],
                "isError": result.isError,
            }


async def main() -> int:
    mcp1_health = await get_json(f"{JAVA_BASE_URL}/health/mcp")
    mcp2_health = await get_json(f"{JAVA_BASE_URL}/health/mcp2")

    print("Java base:", JAVA_BASE_URL)
    print("health/mcp:", mcp1_health)
    print("health/mcp2:", mcp2_health)

    mcp1_sse = f"{JAVA_BASE_URL}/mcp/sse"
    mcp2_sse = f"{JAVA_BASE_URL}/mcp2/sse"

    mcp1_tools = await list_tools(mcp1_sse)
    mcp2_tools = await list_tools(mcp2_sse)

    print()
    print("MCP1 tools:", mcp1_tools)
    print("MCP2 tools:", mcp2_tools)

    # Safe call: uses local SQLite + stub gmail by default.
    if "employee_list" in mcp2_tools:
        print()
        result = await call_tool(mcp2_sse, "employee_list", {"limit": 5})
        print("MCP2 employee_list(limit=5):", result)
    else:
        print()
        print("MCP2 missing expected tool: employee_list")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

