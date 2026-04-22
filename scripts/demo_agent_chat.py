"""
Demo client for the Java backend -> Python agent bridge.

This calls the Spring Boot proxy endpoint:
  POST /api/agent/chat

Which should be proxied to the Python FastAPI bridge (api_server.py) running on port 8001.

Usage:
  ./.venv-mcp/bin/python scripts/demo_agent_chat.py "List my next 5 events"

Override backend base URL:
  JAVA_BASE_URL=http://127.0.0.1:8082 ./.venv-mcp/bin/python scripts/demo_agent_chat.py "..."
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default="List my next 5 events", help="Prompt to send to the agent")
    parser.add_argument("--session-id", default="session_default", help="Conversation/session id")
    args = parser.parse_args(argv)

    base_url = os.environ.get("JAVA_BASE_URL", "http://127.0.0.1:8082").rstrip("/")
    url = f"{base_url}/api/agent/chat"
    payload = {"message": args.prompt, "session_id": args.session_id}

    print("Request URL:", url)
    print("Request JSON:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()

    try:
        res = httpx.post(url, json=payload, timeout=60.0)
    except Exception as e:
        print("Request failed:", str(e))
        return 1

    print("Response HTTP:", res.status_code)
    content_type = (res.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            data = res.json()
        except Exception:
            print("Response body (non-JSON):")
            print(res.text)
            return 2
        print("Response JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Response body:")
        print(res.text)

    return 0 if res.status_code >= 200 and res.status_code < 300 else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

