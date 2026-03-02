"""Run a mock FAIR extension server for communications testing.

Example:
    uv run python scripts/mock_extension.py --platform-url http://127.0.0.1:8000 --id mock.echo --secret <issued-secret> --port 9101 --auto-register
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager


@dataclass
class ExtensionConfig:
    platform_url: str
    extension_id: str
    extension_secret: str
    host: str
    port: int
    auto_register: bool
    stream_seconds: float
    progress_events: int

    @property
    def webhook_url(self) -> str:
        return f"http://{self.host}:{self.port}/hooks/jobs"

    @property
    def platform_api(self) -> str:
        return f"{self.platform_url.rstrip('/')}/api"


def build_app(config: ExtensionConfig) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if config.auto_register:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{config.platform_api}/extensions/connect",
                    json={
                        "extensionId": config.extension_id,
                        "webhookUrl": config.webhook_url,
                        "intents": ["jobs.test", "mock.echo"],
                        "capabilities": ["mock"],
                        "requestedScopes": ["jobs:read", "jobs:write", "extensions:connect"],
                        "metadata": {"runtime": "python", "kind": "mock-extension"},
                    },
                    headers=_platform_auth_headers(config),
                )
                response.raise_for_status()
        try:
            yield
        finally:
            pass

    app = FastAPI(title=f"Mock Extension ({config.extension_id})", lifespan=lifespan)
    app.state.config = config
    app.state.received_jobs: list[dict[str, Any]] = []

    @app.get("/health")
    async def health():
        return {"status": "ok", "extensionId": config.extension_id}

    @app.get("/jobs")
    async def jobs():
        return {"received": app.state.received_jobs}

    @app.post("/hooks/jobs")
    async def receive_job(payload: dict[str, Any]):
        if "job_id" not in payload:
            raise HTTPException(status_code=400, detail="job_id is required")
        app.state.received_jobs.append(payload)
        asyncio.create_task(_simulate_work(config, payload))
        return {"accepted": True, "job_id": payload["job_id"]}

    return app


async def _simulate_work(config: ExtensionConfig, job_payload: dict[str, Any]) -> None:
    """Emit mock updates back to the platform for a received job."""
    job_id = str(job_payload["job_id"])
    input_payload = job_payload.get("payload", {})

    steps = max(1, int(config.progress_events))
    total_seconds = max(0.0, float(config.stream_seconds))
    delay = total_seconds / steps if steps else 0.0

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i in range(steps):
            percent = int(((i + 1) / steps) * 100)
            payload = {
                "percent": percent,
                "message": f"mock progress {i + 1}/{steps}",
            }
            status = "running" if i == 0 else None
            response = await client.post(
                f"{config.platform_api}/jobs/{job_id}/updates",
                json={
                    "event": "progress",
                    "status": status,
                    "payload": payload,
                },
                headers=_platform_auth_headers(config),
            )
            _raise_for_platform_error("progress", job_id, response)
            if delay > 0 and i < steps - 1:
                await asyncio.sleep(delay)

        response = await client.post(
            f"{config.platform_api}/jobs/{job_id}/updates",
            json={
                "event": "result",
                "status": "completed",
                "payload": {
                    "echo": input_payload,
                    "extensionId": config.extension_id,
                    "message": "mock result generated",
                },
            },
            headers=_platform_auth_headers(config),
        )
        _raise_for_platform_error("result", job_id, response)


def _platform_auth_headers(config: ExtensionConfig) -> dict[str, str]:
    return {
        "X-FAIR-Extension-Id": config.extension_id,
        "Authorization": f"Bearer {config.extension_secret}",
    }


def _raise_for_platform_error(stage: str, job_id: str, response: httpx.Response) -> None:
    if response.is_success:
        return
    body = response.text.strip()
    detail = body if body else "<empty>"
    raise RuntimeError(
        f"platform rejected {stage} update for job {job_id}: "
        f"status={response.status_code} body={detail}"
    )


def parse_args() -> ExtensionConfig:
    parser = argparse.ArgumentParser(description="Run a mock FAIR extension for testing")
    parser.add_argument("--platform-url", default="http://127.0.0.1:8000", help="Base URL for FAIR platform backend")
    parser.add_argument("--id", dest="extension_id", default="mock.echo", help="Extension id for registration/targeting")
    parser.add_argument(
        "--secret",
        dest="extension_secret",
        required=True,
        help="Extension secret issued by /api/extensions/admin/clients",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind extension server")
    parser.add_argument("--port", type=int, default=9101, help="Port to bind extension server")
    parser.add_argument("--auto-register", action="store_true", help="Register extension in platform on startup")
    parser.add_argument(
        "--stream-seconds",
        type=float,
        default=1.0,
        help="Approximate total seconds for progress stream before final result",
    )
    parser.add_argument(
        "--progress-events",
        type=int,
        default=4,
        help="Number of progress events to emit before final result",
    )
    args = parser.parse_args()
    return ExtensionConfig(
        platform_url=args.platform_url,
        extension_id=args.extension_id,
        extension_secret=args.extension_secret,
        host=args.host,
        port=args.port,
        auto_register=args.auto_register,
        stream_seconds=args.stream_seconds,
        progress_events=args.progress_events,
    )


def main() -> None:
    config = parse_args()
    app = build_app(config)
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
