"""End-to-end check: a chat turn streams from an SDK extension into FAIR.

Exercises the whole path a browser would take:

    login -> discover capability -> create Thread -> create Turn
      -> FAIR queues an Execution and dispatches it
      -> the extension runner claims it over its outbound connection
      -> the extension streams message.delta events back
      -> we replay the durable event log and reassemble the text

Run against a live backend:

    uv run python scripts/e2e_chat_demo.py --capability echo
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    # Model output is arbitrary Unicode; a Windows cp1252 console would raise
    # on the first superscript or em dash and lose an otherwise passing run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8099")
    parser.add_argument("--email", default="e2e@test.com")
    parser.add_argument("--password", default="e2e_password_123")
    parser.add_argument("--capability", default="echo")
    parser.add_argument("--message", default="What is a derivative?")
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    api = args.url.rstrip("/")
    client = httpx.Client(base_url=api, timeout=30.0)

    login = client.post(
        "/api/auth/login",
        data={"username": args.email, "password": args.password},
    )
    if login.status_code != 200:
        print(f"FAIL login: {login.status_code} {login.text}")
        return 1
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    print("logged in")

    capabilities = client.get("/api/v1/extensions/capabilities", headers=auth)
    if capabilities.status_code != 200:
        print(f"FAIL capabilities: {capabilities.status_code} {capabilities.text}")
        return 1
    match = next(
        (
            item
            for item in capabilities.json()
            if item["capabilityId"] == args.capability
        ),
        None,
    )
    if match is None:
        available = [item["capabilityId"] for item in capabilities.json()]
        print(f"FAIL: no capability {args.capability!r}. Available: {available}")
        return 1
    print(f"capability: {match['capabilityId']} ({match['surface']}) -> {match['id']}")

    thread = client.post(
        "/api/v1/threads", headers=auth, json={"title": "E2E demo"}
    )
    if thread.status_code != 201:
        print(f"FAIL thread: {thread.status_code} {thread.text}")
        return 1
    thread_id = thread.json()["id"]

    turn = client.post(
        f"/api/v1/threads/{thread_id}/turns",
        headers=auth,
        json={"content": args.message, "capabilityDefinitionId": match["id"]},
    )
    if turn.status_code != 202:
        print(f"FAIL turn: {turn.status_code} {turn.text}")
        return 1
    execution_id = turn.json()["executionId"]
    print(f"execution: {execution_id}")

    # Replay the durable log until the Execution reaches a terminal state.
    deadline = time.time() + args.timeout
    seen: set[int] = set()
    text_parts: list[str] = []
    status = "queued"
    observations: list[str] = []

    while time.time() < deadline:
        events = client.get(
            f"/api/v1/executions/{execution_id}/events", headers=auth
        )
        if events.status_code != 200:
            print(f"FAIL events: {events.status_code} {events.text}")
            return 1
        for event in events.json():
            if event["sequence"] in seen:
                continue
            seen.add(event["sequence"])
            kind = event["type"]
            payload = event.get("payload") or {}
            if kind == "message.delta":
                text_parts.append(payload.get("text", ""))
            elif kind.startswith("execution."):
                status = kind.split(".", 1)[1]
                print(f"  <- {kind}")
                if kind == "execution.failed":
                    print(f"     error: {payload.get('error')}")
            elif kind.startswith("agent.") or kind == "extension.log":
                observations.append(kind)

        if status in {"completed", "failed", "cancelled", "expired"}:
            break
        time.sleep(0.3)

    body = "".join(text_parts)
    print("-" * 60)
    print(body if body else "(no text streamed)")
    print("-" * 60)
    print(f"status={status} deltas={len(text_parts)} chars={len(body)}")
    if observations:
        print(f"observations: {sorted(set(observations))}")

    if status != "completed":
        print("FAIL: execution did not complete")
        return 1
    if not body.strip():
        print("FAIL: no streamed text")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
