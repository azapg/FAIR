from typing import Any

import httpx

from fair_platform.extension_sdk.auth import ExtensionCredentials
from fair_platform.extension_sdk.client import build_platform_client
from fair_platform.extension_sdk.contracts.job import (
    ErrorPayload,
    JobUpdateError,
    JobUpdateLog,
    JobUpdateProgress,
    JobUpdateRequest,
    JobUpdateResult,
    JobUpdateToken,
    LogPayload,
    ProgressPayload,
    ResultPayload,
    TokenPayload,
)


class JobContext:
    def __init__(
        self,
        job_id: str,
        platform_url: str,
        credentials: ExtensionCredentials,
        timeout: float = 20.0,
    ):
        self.job_id = job_id
        self._api = build_platform_client(platform_url=platform_url, credentials=credentials, timeout=timeout)

    async def __aenter__(self) -> "JobContext":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._api.aclose()

    async def _post_update(self, request: JobUpdateRequest) -> None:
        response = await self._api.post(
            f"/api/jobs/{self.job_id}/updates",
            json=request.model_dump(by_alias=True, mode="json"),
        )
        response.raise_for_status()

    async def progress(self, percent: int, message: str | None = None, status: str | None = None) -> None:
        await self._post_update(
            JobUpdateRequest(
                update=JobUpdateProgress(event="progress", payload=ProgressPayload(percent=percent, message=message)),
                status=status,
            )
        )

    async def log(self, level: str, output: str, status: str | None = None) -> None:
        await self._post_update(
            JobUpdateRequest(
                update=JobUpdateLog(event="log", payload=LogPayload(level=level, output=output)),
                status=status,
            )
        )

    async def token(self, text: str) -> None:
        await self._post_update(
            JobUpdateRequest(update=JobUpdateToken(event="token", payload=TokenPayload(text=text)))
        )

    async def result(self, data: dict[str, Any], status: str = "completed") -> None:
        await self._post_update(
            JobUpdateRequest(
                update=JobUpdateResult(event="result", payload=ResultPayload(data=data)),
                status=status,
            )
        )

    async def error(self, error: str, traceback: str | None = None, status: str = "failed") -> None:
        await self._post_update(
            JobUpdateRequest(
                update=JobUpdateError(event="error", payload=ErrorPayload(error=error, traceback=traceback)),
                status=status,
            )
        )


__all__ = ["JobContext"]
