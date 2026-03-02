import asyncio
import json

import httpx

from fair_platform.backend.main import app
from fair_platform.extension_sdk import ExtensionCredentials, FairExtension, JobContext, build_extension_auth_headers
from tests.conftest import extension_auth_headers


def test_build_extension_auth_headers(extension_client_credentials):
    credentials = ExtensionCredentials(
        extension_id=extension_client_credentials["extension_id"],
        extension_secret=extension_client_credentials["extension_secret"],
    )
    assert build_extension_auth_headers(credentials) == extension_auth_headers(extension_client_credentials)


def test_job_context_posts_protocol_envelope(extension_client_credentials):
    captured: dict[str, str] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["extension_id"] = request.headers["X-FAIR-Extension-Id"]
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(200, json={"accepted": True})

    transport = httpx.MockTransport(_handler)
    credentials = ExtensionCredentials(
        extension_id=extension_client_credentials["extension_id"],
        extension_secret=extension_client_credentials["extension_secret"],
    )

    async def _run():
        async with JobContext(job_id="job-ctx-1", platform_url="http://platform.test", credentials=credentials) as ctx:
            original = ctx._api
            ctx._api = httpx.AsyncClient(transport=transport, base_url="http://platform.test", headers=original.headers)
            await original.aclose()
            await ctx.progress(10, "step one", status="running")

    asyncio.run(_run())

    assert captured["path"] == "/api/jobs/job-ctx-1/updates"
    assert captured["authorization"] == f"Bearer {extension_client_credentials['extension_secret']}"
    assert captured["extension_id"] == extension_client_credentials["extension_id"]
    payload = json.loads(captured["body"])
    assert payload["update"]["event"] == "progress"
    assert payload["update"]["payload"]["percent"] == 10
    assert payload["status"] == "running"


def test_fair_extension_connect_returns_registered_extension(extension_client_credentials):
    extension = FairExtension(
        extension_id=extension_client_credentials["extension_id"],
        platform_url="http://testserver",
        extension_secret=extension_client_credentials["extension_secret"],
        webhook_url="http://localhost:9101/hooks/jobs",
        requested_scopes=["jobs:write"],
    )

    async def _run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            return await extension.connect(client=client)

    registered = asyncio.run(_run())
    assert registered.extension_id == extension_client_credentials["extension_id"]
    assert registered.requested_scopes == ["jobs:write"]
