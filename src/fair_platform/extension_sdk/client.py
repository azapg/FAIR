import httpx

from fair_platform.extension_sdk.auth import (
    ExtensionCredentials,
    build_extension_auth_headers,
)


def build_platform_client(
    platform_url: str,
    credentials: ExtensionCredentials,
    timeout: float = 20.0,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=platform_url.rstrip("/"),
        timeout=timeout,
        headers=build_extension_auth_headers(credentials),
    )


__all__ = ["build_platform_client"]
