import asyncio
import binascii
from typing import Optional
from urllib.parse import urlparse
from typing_extensions import deprecated

from fair_platform.backend.data.models.submission_result import TYPE_CHECKING
from fair_platform.sdk.events import EventBus

# TODO: Maybe a Logger interface so you can have a PluginLogger without a session?
# TODO: Bro what? Why the base logger is a session logger?
if TYPE_CHECKING:
    from fair_platform.backend.data.models.plugin import Plugin

LEGACY_SDK_LOGGER_DEPRECATION_MESSAGE = (
    "SessionLogger/PluginLogger are part of the legacy FAIR SDK runtime and are "
    "deprecated. Migrate to the new extension jobs/event API."
)


@deprecated(LEGACY_SDK_LOGGER_DEPRECATION_MESSAGE)
class SessionLogger:
    _FILE_CONTENT_MAX_BYTES = 256000
    _ALLOWED_FILE_TYPES = {"text", "markdown"}
    _ALLOWED_FILE_MIME_TYPES = {"text/plain", "text/markdown"}

    def __init__(self, session_id: str, bus: EventBus):
        self.session_id = session_id
        self.bus = bus

    @staticmethod
    def _require_non_empty(value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"'{field_name}' must be a non-empty string")
        return value.strip()

    @staticmethod
    def _is_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @classmethod
    def _normalize_image_src(cls, src: str, mime_type: Optional[str] = None) -> str:
        src = cls._require_non_empty(src, "src")
        if src.startswith("data:") or cls._is_url(src):
            return src

        normalized = "".join(src.split())
        try:
            binascii.a2b_base64(normalized)
        except binascii.Error as exc:
            raise ValueError(
                "'src' must be a URL, a data URL, or valid base64 image data"
            ) from exc

        content_type = mime_type.strip() if isinstance(mime_type, str) and mime_type.strip() else "image/png"
        return f"data:{content_type};base64,{normalized}"

    def _decorate_payload(self, payload: dict) -> dict:
        """Hook for subclasses to modify or enrich the payload before emission.

        The base implementation returns the payload unchanged. Subclasses can override
        this method to attach contextual information (for example, `PluginLogger`
        adds plugin metadata) or otherwise transform the payload.

        Implementations should return a JSON-serializable mapping (typically a
        `dict`) that represents the final payload to be emitted.
        """
        return payload

    @classmethod
    def _normalize_file_name(cls, name: str) -> str:
        name = cls._require_non_empty(name, "name")
        if "/" in name or "\\" in name:
            raise ValueError("'name' must be a file name, not a path")
        return name

    @classmethod
    def _infer_file_type_from_name(cls, name: str) -> str:
        lower_name = name.lower()
        if lower_name.endswith(".md") or lower_name.endswith(".markdown"):
            return "markdown"
        return "text"

    @classmethod
    def _normalize_file_type(
        cls,
        file_type: Optional[str],
        *,
        name: str,
    ) -> str:
        normalized = (
            file_type.strip().lower()
            if isinstance(file_type, str) and file_type.strip()
            else cls._infer_file_type_from_name(name)
        )
        if normalized not in cls._ALLOWED_FILE_TYPES:
            raise ValueError("'file_type' must be one of: text, markdown")
        return normalized

    @classmethod
    def _normalize_file_mime_type(
        cls,
        mime_type: Optional[str],
        *,
        file_type: str,
    ) -> str:
        if isinstance(mime_type, str) and mime_type.strip():
            normalized = mime_type.strip().lower()
            if normalized not in cls._ALLOWED_FILE_MIME_TYPES:
                raise ValueError("'mime_type' must be one of: text/plain, text/markdown")
            return normalized
        return "text/markdown" if file_type == "markdown" else "text/plain"

    @classmethod
    def _normalize_file_content(cls, content: str) -> tuple[str, int]:
        content = cls._require_non_empty(content, "content")
        encoded = content.encode("utf-8")
        size_bytes = len(encoded)
        if size_bytes > cls._FILE_CONTENT_MAX_BYTES:
            raise ValueError(
                f"'content' exceeds maximum allowed size of {cls._FILE_CONTENT_MAX_BYTES} bytes"
            )
        return content, size_bytes

    def log(self, level: str, message: str):
        message = self._require_non_empty(message, "message")
        payload = self._decorate_payload({"message": message})
        return self.emit("log", payload, level=level)

    def info(self, message: str):
        return self.log("info", message)

    def warning(self, message: str):
        return self.log("warning", message)

    def error(self, message: str):
        return self.log("error", message)

    def debug(self, message: str):
        return self.log("debug", message)

    def log_image(
        self,
        description: str,
        src: str,
        alt: str,
        *,
        level: str = "info",
        mime_type: Optional[str] = None,
    ):
        description = self._require_non_empty(description, "description")
        alt = self._require_non_empty(alt, "alt")
        normalized_src = self._normalize_image_src(src, mime_type=mime_type)
        payload = self._decorate_payload(
            {
                "description": description,
                "image": {
                    "src": normalized_src,
                    "alt": alt,
                },
            }
        )
        if isinstance(mime_type, str) and mime_type.strip():
            payload["image"]["mime_type"] = mime_type.strip()
        return self.emit("image", payload, level=level)

    def log_image_group(
        self,
        description: str,
        images: list[dict],
        *,
        level: str = "info",
    ):
        description = self._require_non_empty(description, "description")
        if not isinstance(images, list) or len(images) == 0:
            raise ValueError("'images' must be a non-empty list")

        normalized_images = []
        for idx, image in enumerate(images):
            if not isinstance(image, dict):
                raise ValueError(f"'images[{idx}]' must be an object")
            src = self._normalize_image_src(
                image.get("src"),
                mime_type=image.get("mime_type"),
            )
            alt = self._require_non_empty(image.get("alt"), f"images[{idx}].alt")
            item = {"src": src, "alt": alt}
            if isinstance(image.get("mime_type"), str) and image.get("mime_type").strip():
                item["mime_type"] = image.get("mime_type").strip()
            normalized_images.append(item)

        payload = self._decorate_payload(
            {
                "description": description,
                "images": normalized_images,
            }
        )
        return self.emit("image_group", payload, level=level)

    def log_file(
        self,
        description: str,
        name: str,
        content: str,
        *,
        level: str = "info",
        file_type: Optional[str] = None,
        mime_type: Optional[str] = None,
        encoding: str = "utf-8",
        language: Optional[str] = None,
    ):
        description = self._require_non_empty(description, "description")
        name = self._normalize_file_name(name)
        content, size_bytes = self._normalize_file_content(content)
        normalized_type = self._normalize_file_type(file_type, name=name)
        normalized_mime_type = self._normalize_file_mime_type(
            mime_type,
            file_type=normalized_type,
        )
        encoding = self._require_non_empty(encoding, "encoding")

        payload = self._decorate_payload(
            {
                "description": description,
                "file": {
                    "name": name,
                    "content": content,
                    "file_type": normalized_type,
                    "mime_type": normalized_mime_type,
                    "encoding": encoding,
                    "size_bytes": size_bytes,
                },
            }
        )
        if isinstance(language, str) and language.strip():
            payload["file"]["language"] = language.strip()
        return self.emit("file", payload, level=level)

    def log_md_file(
        self,
        description: str,
        name: str,
        content: str,
        *,
        level: str = "info",
    ):
        return self.log_file(
            description=description,
            name=name,
            content=content,
            level=level,
            file_type="markdown",
            mime_type="text/markdown",
            encoding="utf-8",
        )

    def log_text_file(
        self,
        description: str,
        name: str,
        content: str,
        *,
        level: str = "info",
        language: Optional[str] = None,
    ):
        return self.log_file(
            description=description,
            name=name,
            content=content,
            level=level,
            file_type="text",
            mime_type="text/plain",
            encoding="utf-8",
            language=language,
        )

    async def _emit_async(self, event_type: str, payload: dict, *, level: str = "info"):
        await self.bus.emit(
            event_type,
            data={
                "level": level,
                "payload": payload or {},
            },
        )

    def emit(self, event_type: str, payload: dict, *, level: str = "info"):
        coro = self._emit_async(event_type, payload, level=level)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        task = asyncio.create_task(coro)
        return task

    def get_child(self, plugin: Optional["Plugin"] = None):
        """Return a logger for a specific plugin"""
        return PluginLogger(session_id=self.session_id, bus=self.bus, plugin=plugin)


@deprecated(LEGACY_SDK_LOGGER_DEPRECATION_MESSAGE)
class PluginLogger(SessionLogger):
    def __init__(
        self, session_id: str, bus: EventBus, plugin: Optional["Plugin"] = None
    ):
        super().__init__(session_id, bus)
        self.plugin = plugin

    def _decorate_payload(self, payload: dict) -> dict:
        merged = dict(payload)
        if self.plugin is not None:
            merged["plugin"] = {
                "id": self.plugin.id,
                "name": self.plugin.name,
                "hash": self.plugin.hash,
                "author": self.plugin.author,
                "version": self.plugin.version,
                "source": self.plugin.source,
                "type": self.plugin.type,
            }
        return merged
