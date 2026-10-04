"""End-to-end check: a pinned, reproducible Flow.

Builds the demo Flow (extract -> score -> summarize), publishes it, runs it,
and prints the pinned capability versions plus the definition hash.

The point of the demo is the *pinning*, not the steps. Publishing freezes the
exact CapabilityDefinition of every node, so re-running this Flow -- next week,
or against a different cohort -- runs the same pipeline. That is what makes
comparing two Flows a measurement rather than an anecdote.

    uv run python scripts/e2e_flow_demo.py
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

ESSAY = (
    "A derivative measures the instantaneous rate of change of a function. "
    "It is defined as the limit of the difference quotient as the interval "
    "shrinks toward zero."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8099")
    parser.add_argument("--email", default="e2e@test.com")
    parser.add_argument("--password", default="e2e_password_123")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    client = httpx.Client(base_url=args.url.rstrip("/"), timeout=30.0)

    login = client.post(
        "/api/auth/login",
        data={"username": args.email, "password": args.password},
    )
    if login.status_code != 200:
        print(f"FAIL login: {login.status_code} {login.text}")
        return 1
    auth = {"Authorization": f"Bearer {login.json()['access_token']}"}

    capabilities = client.get("/api/v1/extensions/capabilities", headers=auth).json()
    by_id = {item["capabilityId"]: item for item in capabilities}
    wanted = ["extract.text", "score.text", "summarize.result"]
    missing = [name for name in wanted if name not in by_id]
    if missing:
        print(f"FAIL: missing flow steps {missing}. Is the core extension running?")
        return 1

    flow = client.post(
        "/api/v1/flows",
        headers=auth,
        json={"name": "Demo grading flow", "description": "extract -> score -> summarize"},
    )
    if flow.status_code != 201:
        print(f"FAIL flow: {flow.status_code} {flow.text}")
        return 1
    flow_id = flow.json()["id"]
    print(f"flow: {flow_id}")

    version = client.post(
        f"/api/v1/flows/{flow_id}/versions",
        headers=auth,
        json={
            "definition": {
                "mode": "ordered",
                "nodes": [
                    {"id": name.split(".")[0], "capabilityDefinitionId": by_id[name]["id"]}
                    for name in wanted
                ],
            },
            "configSnapshot": {},
        },
    )
    if version.status_code != 201:
        print(f"FAIL version: {version.status_code} {version.text}")
        return 1
    version_id = version.json()["id"]
    print(f"version: {version_id}  hash={version.json()['definitionHash'][:16]}...")
    for pin in version.json()["capabilityPins"]:
        print(
            f"  pinned {pin['nodeId']}: {pin['capabilityId']}@{pin['capabilityVersion']} "
            f"({pin['surface']})"
        )

    published = client.post(
        f"/api/v1/flows/{flow_id}/versions/{version_id}/publish", headers=auth
    )
    if published.status_code != 200:
        print(f"FAIL publish: {published.status_code} {published.text}")
        return 1
    print(f"published: state={published.json()['state']}")

    started = client.post(
        f"/api/v1/flows/{flow_id}/executions",
        headers=auth,
        json={"flowVersionId": version_id, "input": {"text": ESSAY}},
    )
    if started.status_code != 202:
        print(f"FAIL start: {started.status_code} {started.text}")
        return 1
    execution_id = started.json()["executionId"]
    print(f"root execution: {execution_id}")

    deadline = time.time() + args.timeout
    status = "queued"
    while time.time() < deadline:
        read = client.get(f"/api/v1/executions/{execution_id}", headers=auth)
        if read.status_code != 200:
            print(f"FAIL read: {read.status_code} {read.text}")
            return 1
        status = read.json()["status"]
        if status in {"completed", "failed", "cancelled", "expired"}:
            break
        time.sleep(0.4)

    events = client.get(
        f"/api/v1/executions/{execution_id}/events", headers=auth
    ).json()
    print("-" * 60)
    for event in events:
        if event["type"].startswith("flow."):
            payload = event.get("payload") or {}
            node = payload.get("nodeId") or payload.get("node_id") or ""
            print(f"  {event['type']:<28} {node}")
    print("-" * 60)
    print(f"status={status}")

    if status != "completed":
        print("FAIL: flow did not complete")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
