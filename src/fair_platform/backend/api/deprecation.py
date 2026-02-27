from fastapi import Response


LEGACY_SDK_DEPRECATION_MESSAGE = (
    "This endpoint belongs to the legacy FAIR SDK/API flow and is deprecated. "
    "Migrate to the new /api/jobs and extension registration flow."
)
LEGACY_SDK_DEPRECATION_DOCS_URL = "/docs/en/api-reference/overview"
LEGACY_SDK_SUNSET_HTTP_DATE = "Mon, 01 Jun 2026 00:00:00 GMT"


def apply_legacy_sdk_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = LEGACY_SDK_SUNSET_HTTP_DATE
    response.headers["Warning"] = f'299 FAIR "{LEGACY_SDK_DEPRECATION_MESSAGE}"'
    response.headers["X-FAIR-Deprecated-Reason"] = LEGACY_SDK_DEPRECATION_MESSAGE
    response.headers["Link"] = f'<{LEGACY_SDK_DEPRECATION_DOCS_URL}>; rel="deprecation"'
