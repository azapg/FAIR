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


def test_log_image_emits_image_event_with_payload():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "image")

    logger.log_image(
        description="Input frame",
        src="https://example.com/frame.png",
        alt="Video frame with worksheet",
    )

    assert len(captured) == 1
    message = captured[0]
    assert message["type"] == "image"
    assert message["level"] == "info"
    assert message["payload"]["description"] == "Input frame"
    assert message["payload"]["image"]["src"] == "https://example.com/frame.png"
    assert message["payload"]["image"]["alt"] == "Video frame with worksheet"


def test_log_image_normalizes_raw_base64_to_data_url():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "image")

    logger.log_image(
        description="Frame",
        src="aGVsbG8=",
        alt="Raw frame bytes",
        mime_type="image/jpeg",
    )

    assert len(captured) == 1
    src = captured[0]["payload"]["image"]["src"]
    assert src.startswith("data:image/jpeg;base64,")
    assert src.endswith("aGVsbG8=")


def test_log_image_group_emits_multiple_images():
    bus = EventBus()
    logger = SessionLogger("session-1", bus)
    captured = _capture(bus, "image_group")

    logger.log_image_group(
        description="Frames sampled from clip",
        images=[
            {"src": "https://example.com/1.png", "alt": "First frame"},
            {"src": "https://example.com/2.png", "alt": "Second frame"},
        ],
    )

    assert len(captured) == 1
    message = captured[0]
    assert message["type"] == "image_group"
    assert message["payload"]["description"] == "Frames sampled from clip"
    assert len(message["payload"]["images"]) == 2
    assert message["payload"]["images"][0]["alt"] == "First frame"
    assert message["payload"]["images"][1]["alt"] == "Second frame"


def test_plugin_logger_adds_plugin_metadata_to_image_payloads():
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
    captured = _capture(bus, "image")

    logger.log_image(
        description="Input frame",
        src="https://example.com/frame.png",
        alt="Frame",
    )

    assert len(captured) == 1
    plugin_payload = captured[0]["payload"]["plugin"]
    assert plugin_payload["id"] == plugin.id
    assert plugin_payload["name"] == plugin.name
    assert plugin_payload["hash"] == plugin.hash


@pytest.mark.parametrize(
    "kwargs",
    [
        {"description": "", "src": "https://example.com/1.png", "alt": "a"},
        {"description": "desc", "src": "", "alt": "a"},
        {"description": "desc", "src": "https://example.com/1.png", "alt": ""},
        {"description": "desc", "src": "not base64%%%?", "alt": "a"},
    ],
)
def test_log_image_validates_inputs(kwargs):
    logger = SessionLogger("session-1", EventBus())
    with pytest.raises(ValueError):
        logger.log_image(**kwargs)


def test_log_image_group_validates_inputs():
    logger = SessionLogger("session-1", EventBus())

    with pytest.raises(ValueError):
        logger.log_image_group(description="desc", images=[])

    with pytest.raises(ValueError):
        logger.log_image_group(
            description="desc",
            images=[{"src": "https://example.com/1.png", "alt": ""}],
        )
