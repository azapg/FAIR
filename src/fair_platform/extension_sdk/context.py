import re
from typing import Any, Optional

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
    JobUpdateSubmissionResult,
    JobUpdateToken,
    LogPayload,
    ProgressPayload,
    ResultPayload,
    SubmissionResultPayload,
    TokenPayload,
)


class JobContext:
    def __init__(
        self,
        job_id: str,
        platform_url: str,
        credentials: ExtensionCredentials,
        timeout: float = 20.0,
        metadata: dict[str, Any] | None = None,
    ):
        self.job_id = job_id
        self._platform_url = platform_url.rstrip("/")
        self._credentials = credentials
        self._timeout = timeout
        self._metadata: dict[str, Any] = metadata or {}
        self._delegation_token: str | None = self._metadata.get("_delegation_token")
        self._api = build_platform_client(platform_url=platform_url, credentials=credentials, timeout=timeout)

    async def __aenter__(self) -> "JobContext":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._api.aclose()

    async def download_artifact(self, artifact_id: str) -> tuple[bytes, str, str]:
        """Download the original derivative of an artifact on behalf of the delegating user.

        When a delegation token is present (injected by the platform at job creation),
        this calls the unified GET /api/artifacts/{id}/download endpoint using the token
        as Bearer auth. The platform resolves the user from the token and enforces their
        normal can_view() permissions — the extension can only access what the user can.

        Returns:
            A (bytes, filename, content_type) tuple.

        Raises:
            httpx.HTTPStatusError: if the platform returns 403/404 (permission denied
                or artifact not found), or if the token has expired.
        """
        if self._delegation_token:
            async with httpx.AsyncClient(
                base_url=self._platform_url,
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self._delegation_token}"},
                follow_redirects=True,
            ) as http:
                response = await http.get(f"/api/artifacts/{artifact_id}/download")
                response.raise_for_status()
                content_type = response.headers.get("content-type") or "application/octet-stream"
                filename = _parse_content_disposition(
                    response.headers.get("content-disposition")
                ) or str(artifact_id)
                return response.content, filename, content_type
        else:
            raise RuntimeError(
                "Cannot download artifact: no delegation token available. "
                "Artifacts can only be downloaded when the extension is dispatched through the platform. "
                "Ensure your job is created via POST /api/jobs."
            )

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

    async def submission_result(
        self,
        submission_id: str,
        data: dict[str, Any],
        status: str | None = None,
    ) -> None:
        await self._post_update(
            JobUpdateRequest(
                update=JobUpdateSubmissionResult(
                    event="submission_result",
                    payload=SubmissionResultPayload(submission_id=submission_id, data=data),
                ),
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


def _parse_content_disposition(header: str | None) -> Optional[str]:
    if not header:
        return None
    match = re.search(r'filename="([^"]+)"', header)
    if match:
        return match.group(1)
    match = re.search(r"filename=([^;]+)", header)
    if match:
        return match.group(1).strip().strip('"')
    return None


__all__ = ["JobContext"]
