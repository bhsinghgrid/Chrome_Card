"""
api_server.py — FastAPI Bridge for Java Integration.

This file:
1. Imports the MCP server capability.
2. Mounts the MCP SSE endpoint.
3. Exposes a REST API for the LangGraph agent to integrate with Java backends.
4. Runs the background worker for delayed emails.
"""

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from mcp_server import mcp
from agent import run_agent
from tools.gmail import process_pending_emails

# ─── Logging setup ────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger(__name__)


# ─── FastAPI Server setup ─────────────────────────────────────────────────────

app = FastAPI(
    title="Google Calendar / Gmail API Bridge",
    description="REST API for Java integration with autonomous AI agents.",
    version="1.2.0"
)

# Enable CORS for Java backend (adjust origins in production if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REST Schemas ─────────────────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    message: str
    session_id: str = "session_default"

class AgentChatResponse(BaseModel):
    answer: str
    steps: list[dict]
    session_id: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/agent/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    REST endpoint to talk to the AI Agent.
    Use this for integrating the autonomous calendar/email logic into Java apps.
    """
    log.info("api_request_received", message=request.message, session_id=request.session_id)
    try:
        result = await run_agent(request.message, session_id=request.session_id)
        return AgentChatResponse(**result)
    except Exception as e:
        # Surface a friendly error message to callers (extension + Java proxy),
        # instead of a blank "Internal Server Error".
        msg = str(e) or e.__class__.__name__
        log.exception("agent_chat_failed", error=msg, session_id=request.session_id)

        # Common failure: Gemini quota/spend cap exceeded.
        if "RESOURCE_EXHAUSTED" in msg and "spending cap" in msg:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API quota/spend cap exceeded for this project. "
                    "Update `GEMINI_API_KEY` or increase the spend cap in Google AI Studio."
                ),
            )

        # Generic failure.
        raise HTTPException(status_code=500, detail="Agent error: " + msg[:400])


@app.get("/health")
def health() -> JSONResponse:
    """Standard health check for backend monitoring."""
    return JSONResponse({
        "status": "ok", 
        "components": ["mcp_sse", "rest_api", "background_worker"],
        "version": "1.2.0"
    })


# ─── Mount the MCP SSE Server ─────────────────────────────────────────────────

# This allows MCP clients (like Claude Desktop) to still connect via SSE while
# the REST API is also running.
app.mount("/mcp", mcp.sse_app())


# ─── Background Worker ────────────────────────────────────────────────────────

import asyncio
@app.on_event("startup")
async def start_background_worker():
    """Starts the task loop that delivers delayed emails after the 5-min window."""
    async def worker_loop():
        log.info("starting_background_email_worker")
        while True:
            await process_pending_emails()
            await asyncio.sleep(30) # Poll every 30 seconds
            
    asyncio.create_task(worker_loop())


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info(
        "starting_api_bridge_server",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )
    uvicorn.run(
        "api_server:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
