from types import SimpleNamespace

import pytest

from fair_platform.sdk.events import EventBus
from fair_platform.sdk.logger import PluginLogger, SessionLogger


def _capture(bus: EventBus, event_name: str):
    captured = []

    def _handler(data):
        captured.append(data)

    bus.on(event_name, _handler)
    return captured


def test_log_file_emits_file_event_with_payload():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "file")

    logger.log_file(
        description="Prompt source",
        name="prompt.md",
        content="# Prompt\nUse OCR.",
    )

    assert len(captured) == 1
    message = captured[0]
    assert message["type"] == "file"
    assert message["level"] == "info"
    assert message["payload"]["description"] == "Prompt source"
    assert message["payload"]["file"]["name"] == "prompt.md"
    assert message["payload"]["file"]["content"] == "# Prompt\nUse OCR."
    assert message["payload"]["file"]["file_type"] == "markdown"
    assert message["payload"]["file"]["mime_type"] == "text/markdown"
    assert message["payload"]["file"]["encoding"] == "utf-8"
    assert message["payload"]["file"]["size_bytes"] == len(
        "# Prompt\nUse OCR.".encode("utf-8")
    )


def test_log_file_defaults_to_text_type_when_name_is_not_markdown():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "file")

    logger.log_file(
        description="Raw OCR text",
        name="ocr.txt",
        content="line1\nline2",
    )

    assert len(captured) == 1
    payload_file = captured[0]["payload"]["file"]
    assert payload_file["file_type"] == "text"
    assert payload_file["mime_type"] == "text/plain"


def test_log_md_file_wrapper_emits_markdown_defaults():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "file")

    logger.log_md_file(
        description="Prompt",
        name="prompt.md",
        content="## Header",
    )

    assert len(captured) == 1
    payload_file = captured[0]["payload"]["file"]
    assert payload_file["file_type"] == "markdown"
    assert payload_file["mime_type"] == "text/markdown"
    assert payload_file["encoding"] == "utf-8"


def test_log_text_file_wrapper_emits_text_defaults_and_language():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "file")

    logger.log_text_file(
        description="Model output",
        name="output.txt",
        content="ok",
        language="plain",
    )

    assert len(captured) == 1
    payload_file = captured[0]["payload"]["file"]
    assert payload_file["file_type"] == "text"
    assert payload_file["mime_type"] == "text/plain"
    assert payload_file["encoding"] == "utf-8"
    assert payload_file["language"] == "plain"


def test_plugin_logger_adds_plugin_metadata_to_file_payloads():
    bus = EventBus()
    plugin = SimpleNamespace(
        id="plugin.id",
        name="VisionTranscriber",
        hash="abc123",
        author="Author",
        version="1.0.0",
        source="repo://vision",
        type="transcriber",
    )
    logger = PluginLogger("session-1", bus, plugin=plugin)
    captured = _capture(bus, "file")

    logger.log_md_file(
        description="Prompt",
        name="prompt.md",
        content="body",
    )

    assert len(captured) == 1
    plugin_payload = captured[0]["payload"]["plugin"]
    assert plugin_payload["id"] == plugin.id
    assert plugin_payload["name"] == plugin.name
    assert plugin_payload["hash"] == plugin.hash


@pytest.mark.parametrize(
    "kwargs",
    [
        {"description": "", "name": "a.txt", "content": "x"},
        {"description": "desc", "name": "", "content": "x"},
        {"description": "desc", "name": "a.txt", "content": ""},
        {"description": "desc", "name": "nested/path.txt", "content": "x"},
        {
            "description": "desc",
            "name": "a.txt",
            "content": "x",
            "file_type": "json",
        },
        {
            "description": "desc",
            "name": "a.txt",
            "content": "x",
            "mime_type": "application/json",
        },
    ],
)
def test_log_file_validates_inputs(kwargs):
    logger = SessionLogger("session-1", EventBus())
    with pytest.raises(ValueError):
        logger.log_file(**kwargs)


def test_log_file_rejects_content_larger_than_max_bytes():
    logger = SessionLogger("session-1", EventBus())
    content = "pecas♥️" * 256000
    with pytest.raises(ValueError):
        logger.log_file(
            description="Too large",
            name="large.txt",
            content=content,
        )
