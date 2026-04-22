"""
api_server.py — HTTP/SSE wrapper for email-mcp.

Exposes the FastMCP server over HTTP (SSE transport) so it can be proxied by the Java backend.

Endpoints (when served with uvicorn):
  - GET  /health
  - GET  /mcp/sse
  - POST /mcp/messages/?session_id=...
"""

import os

# Must be set before importing `fastmcp` (it reads settings from env on import).
os.environ.setdefault("FASTMCP_MESSAGE_PATH", "/mcp/messages/")

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.mcp_server.server import mcp


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "email-mcp"})


# Serve MCP over SSE at /mcp/sse (message endpoint is controlled via FASTMCP_MESSAGE_PATH).
app = mcp.http_app(path="/mcp/sse", transport="sse")

