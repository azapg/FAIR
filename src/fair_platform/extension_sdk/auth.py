from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionCredentials:
    extension_id: str
    extension_secret: str


def build_extension_auth_headers(credentials: ExtensionCredentials) -> dict[str, str]:
    return {
        "X-FAIR-Extension-Id": credentials.extension_id,
        "Authorization": f"Bearer {credentials.extension_secret}",
    }


__all__ = ["ExtensionCredentials", "build_extension_auth_headers"]
