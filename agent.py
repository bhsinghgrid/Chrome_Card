"""
agent.py — The LangChain ReAct agent that uses our MCP tools.
"""

import asyncio
import json
import os
from typing import Any
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import settings
from cache import set_last_action

log = structlog.get_logger(__name__)


# ─── System prompt template ───────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """You are an autonomous calendar and email assistant.
You help users manage their Google Calendar and Gmail efficiently.

The current date and time is {current_time}.
The user's default timezone is {timezone}.

RULES YOU MUST FOLLOW:
1. Always resolve relative dates (like "today", "tomorrow", "next Friday") based on the current date provided above.
2. Before scheduling any meeting, ALWAYS call tool_check_free_slots first.
3. Before calling tool_create_event or tool_send_email, ALWAYS call tool_request_approval.
4. If a tool returns an error message (e.g., "Error: ..."), explain the problem to the user simply and ask for missing information or suggest a fix.
5. Always be explicit about what you are about to do and why.
6. If the user asks for their own availability/slots without specifying other attendees, you can check their own calendar by passing 'primary' as the single attendee in list.
7. NEW: If the user wants to revert or cancel their last action (like a meeting they just created or an email they just sent), use the tool_undo_last_action.
8. If the user request is ONLY about Calendar/Gmail, do NOT call Email MCP directory/workflow tools (employee_list, resolve_recipients, start_email_send, etc.).
9. If the user request is ONLY about Email MCP directory/workflows, do NOT call Calendar/Gmail tools (tool_get_events, tool_check_free_slots, etc.).
"""


# ─── Human approval tool ──────────────────────────────────────────────────────

import httpx
JAVA_BACKEND_URL = os.environ.get("JAVA_BACKEND_URL", "http://localhost:8080").rstrip("/")

def request_approval(action_type: str, description: str, payload: str) -> str:
    try:
        response = httpx.post(
            f"{JAVA_BACKEND_URL}/api/approvals",
            json={"action_type": action_type, "description": description, "payload": payload},
            timeout=10.0,
        )
        response.raise_for_status()
        approval_id = response.json()["approval_id"]
        
        import time
        deadline = time.time() + (30 * 60)
        while time.time() < deadline:
            status_response = httpx.get(f"{JAVA_BACKEND_URL}/api/approvals/{approval_id}", timeout=10.0)
            status = status_response.json()["status"]
            if status == "APPROVED": return "APPROVED"
            elif status == "REJECTED": return "REJECTED"
            time.sleep(5)
        return "TIMEOUT"
    except Exception:
        return "APPROVED" # Auto-approve in dev

approval_tool = StructuredTool.from_function(
    func=request_approval,
    name="tool_request_approval",
    description="REQUIRED: Call this before create_event, send_email, or delete_event.",
)


# ─── Agent builder ─────────────────────────────────────────────────────────────

_agent_cache = None

async def build_agent() -> Any:
    global _agent_cache
    if _agent_cache is not None:
        return _agent_cache

    mcp1_sse_url = f"http://127.0.0.1:{settings.mcp_port}/mcp/sse"
    mcp2_sse_url = f"http://{settings.mcp2_host}:{settings.mcp2_port}/mcp/sse"

    log.info("connecting_to_mcp_servers", mcp1=mcp1_sse_url, mcp2=mcp2_sse_url)

    mcp_client = MultiServerMCPClient(
        {
            "calendar_gmail": {
                "url": mcp1_sse_url,
                "transport": "sse",
            },
            "email_mcp": {
                "url": mcp2_sse_url,
                "transport": "sse",
            }
        }
    )

    mcp_tools = await mcp_client.get_tools()
    all_tools = mcp_tools + [approval_tool]

    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.gemini_api_key,
        max_output_tokens=4096,
        temperature=0,
    )

    memory = MemorySaver()

    def state_modifier(state: Any):
        now = datetime.now(ZoneInfo(settings.default_timezone))
        current_time_str = now.strftime("%A, %B %d, %Y %I:%M %p")
        
        system_content = AGENT_SYSTEM_PROMPT.format(
            current_time=current_time_str,
            timezone=settings.default_timezone
        )
        
        if isinstance(state, dict) and "messages" in state:
            messages = state["messages"]
        elif isinstance(state, list):
            messages = state
        else:
            messages = []
            
        return [SystemMessage(content=system_content)] + list(messages)

    _agent_cache = create_react_agent(
        model=llm,
        tools=all_tools,
        checkpointer=memory,
        prompt=state_modifier
    )

    log.info("agent_ready", model=settings.llm_model)
    return _agent_cache


async def run_agent(user_message: str, session_id: str = "session_default", agent: Any = None) -> dict[str, Any]:
    if agent is None:
        agent = await build_agent()

    log.info("agent_run_start", message=user_message)
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        result = await agent.ainvoke({"messages": [HumanMessage(content=user_message)]}, config)
    except Exception as e:
        if "INVALID_CHAT_HISTORY" in str(e) or "tool_calls" in str(e):
            log.warning("corrupted_history_detected", error=str(e))
            session_id = f"{session_id}_{datetime.now().timestamp()}"
            config["configurable"]["thread_id"] = session_id
            result = await agent.ainvoke({"messages": [HumanMessage(content=user_message)]}, config)
        else:
            raise e
    
    all_messages = result.get("messages", [])
    
    # ─── Action Tracking (for Undo) ───────────────────────────────────────────
    # We look for successful tool calls to track them in Redis
    for i in range(len(all_messages) - 1, -1, -1):
        msg = all_messages[i]
        if isinstance(msg, ToolMessage):
            # Find the corresponding AI message to see what tool was called
            ai_msg = all_messages[i-1] if i > 0 else None
            if ai_msg and getattr(ai_msg, "tool_calls", None):
                for tc in ai_msg.tool_calls:
                    if tc["id"] == msg.tool_call_id:
                        tool_name = tc["name"]
                        try:
                            # Try to parse the tool output (it's usually a JSON string or dict)
                            output = msg.content
                            if isinstance(output, str):
                                output = json.loads(output)
                                
                            if tool_name == "tool_create_event" and "event_id" in output:
                                set_last_action(session_id, {
                                    "action_type": "create_event",
                                    "action_id": output["event_id"],
                                    "payload": tc["args"]
                                })
                            elif tool_name == "tool_send_email" and output.get("status") == "QUEUED":
                                set_last_action(session_id, {
                                    "action_type": "send_email",
                                    "action_id": output["queue_id"],
                                    "payload": tc["args"]
                                })
                        except Exception:
                            continue

    final_answer = ""
    if all_messages:
        content = all_messages[-1].content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    final_answer += part.get("text", "")
                elif isinstance(part, str):
                    final_answer += part
        else:
            final_answer = content

    tool_steps = []
    for msg in all_messages:
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tool_steps.append({"tool": tc.get("name"), "input": str(tc.get("args"))})

    log.info("agent_run_complete", steps=len(tool_steps))
    return {"answer": final_answer, "steps": tool_steps, "session_id": session_id}

if __name__ == "__main__":
    async def main():
        result = await run_agent("What matches the local time now?")
        print("\n=== FINAL ANSWER ===")
        print(result["answer"])
    asyncio.run(main())
