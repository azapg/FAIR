"""Test deterministic log ordering in plugin execution."""
import asyncio
import pytest
from datetime import datetime
from typing import List

from fair_platform.sdk.events import EventBus, IndexedEventBus
from fair_platform.sdk.logger import SessionLogger, LogQueue


class MockEventBus(EventBus):
    """Event bus that records all emitted events for testing."""
    
    def __init__(self):
        super().__init__()
        self.events: List[dict] = []
    
    async def emit(self, event_name: str, data):
        # Record the raw data before any processing
        event = {"event_name": event_name, "data": data, "received_at": datetime.now()}
        self.events.append(event)
        await super().emit(event_name, data)


@pytest.mark.asyncio
async def test_log_queue_fifo_ordering():
    """Test that LogQueue maintains FIFO ordering of log entries."""
    bus = MockEventBus()
    queue = LogQueue(bus)
    queue.start()
    
    # Enqueue multiple logs
    for i in range(5):
        queue.enqueue("log", {"message": f"Message {i}"}, level="info")
    
    # Wait for all logs to be processed
    await queue.flush()
    await queue.stop()
    
    # Verify FIFO ordering
    assert len(bus.events) == 5
    for i, event in enumerate(bus.events):
        assert event["data"]["payload"]["message"] == f"Message {i}"


@pytest.mark.asyncio
async def test_session_logger_deterministic_ordering():
    """Test that SessionLogger maintains deterministic log ordering."""
    bus = MockEventBus()
    logger = SessionLogger("test-session", bus)
    
    # Emit multiple logs rapidly
    logger.info("First message")
    logger.info("Second message")
    logger.warning("Third message")
    logger.error("Fourth message")
    logger.debug("Fifth message")
    
    # Flush and stop
    await logger.flush()
    await logger.stop()
    
    # Verify ordering
    assert len(bus.events) == 5
    expected_messages = [
        "First message",
        "Second message", 
        "Third message",
        "Fourth message",
        "Fifth message"
    ]
    for i, event in enumerate(bus.events):
        assert event["data"]["payload"]["message"] == expected_messages[i]


@pytest.mark.asyncio
async def test_plugin_logger_shares_parent_queue():
    """Test that PluginLogger shares the parent SessionLogger's queue."""
    bus = MockEventBus()
    session_logger = SessionLogger("test-session", bus)
    plugin_logger = session_logger.get_child("test-plugin")
    
    # Emit logs from both loggers
    session_logger.info("Session log 1")
    plugin_logger.info("Plugin log 1")
    session_logger.info("Session log 2")
    plugin_logger.info("Plugin log 2")
    
    # Flush and stop
    await session_logger.flush()
    await session_logger.stop()
    
    # Verify ordering is preserved across both loggers
    assert len(bus.events) == 4
    assert bus.events[0]["data"]["payload"]["message"] == "Session log 1"
    assert bus.events[1]["data"]["payload"]["message"] == "Plugin log 1"
    assert bus.events[1]["data"]["payload"]["plugin"] == "test-plugin"
    assert bus.events[2]["data"]["payload"]["message"] == "Session log 2"
    assert bus.events[3]["data"]["payload"]["message"] == "Plugin log 2"


@pytest.mark.asyncio
async def test_log_timestamps_captured_at_call_time():
    """Test that log timestamps are captured when log() is called, not when processed."""
    bus = MockEventBus()
    logger = SessionLogger("test-session", bus)
    
    # Log first message
    logger.info("First message")
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Log second message
    logger.info("Second message")
    
    # Flush and verify
    await logger.flush()
    await logger.stop()
    
    # First log's timestamp should be before second log's timestamp
    first_ts = datetime.fromisoformat(bus.events[0]["data"]["ts"])
    second_ts = datetime.fromisoformat(bus.events[1]["data"]["ts"])
    assert first_ts < second_ts


@pytest.mark.asyncio
async def test_sync_plugin_logging_maintains_order():
    """
    Test that sync plugin code logging maintains order.
    
    This simulates what happens when a sync plugin method runs in an executor
    and logs multiple messages.
    """
    bus = MockEventBus()
    logger = SessionLogger("test-session", bus)
    
    async def simulate_sync_plugin_in_executor():
        """Simulate sync plugin code that logs inside an executor."""
        loop = asyncio.get_running_loop()
        
        def sync_plugin_work():
            # This simulates a sync plugin method that logs
            logger.info("Sync log 1")
            logger.info("Sync log 2")
            logger.info("Sync log 3")
            return "done"
        
        result = await loop.run_in_executor(None, sync_plugin_work)
        return result
    
    # Log before sync work
    logger.info("Before sync work")
    
    # Run sync work in executor
    await simulate_sync_plugin_in_executor()
    
    # Log after sync work
    logger.info("After sync work")
    
    # Flush and stop
    await logger.flush()
    await logger.stop()
    
    # Verify ordering - logs should appear in order
    assert len(bus.events) == 5
    expected_order = [
        "Before sync work",
        "Sync log 1",
        "Sync log 2", 
        "Sync log 3",
        "After sync work"
    ]
    for i, event in enumerate(bus.events):
        assert event["data"]["payload"]["message"] == expected_order[i], \
            f"Expected '{expected_order[i]}' at position {i}, got '{event['data']['payload']['message']}'"


@pytest.mark.asyncio
async def test_indexed_event_bus_adds_indices():
    """Test that IndexedEventBus adds sequential indices to events."""
    bus = IndexedEventBus()
    events_received = []
    
    def record_event(data):
        events_received.append(data)
    
    bus.on("log", record_event)
    
    logger = SessionLogger("test-session", bus)
    
    # Emit multiple logs
    logger.info("First")
    logger.info("Second")
    logger.info("Third")
    
    # Flush and stop
    await logger.flush()
    await logger.stop()
    
    # Verify indices are sequential
    assert len(events_received) == 3
    for i, event in enumerate(events_received):
        assert event["index"] == i


@pytest.mark.asyncio
async def test_log_queue_handles_stop_with_pending_items():
    """Test that LogQueue processes all pending items before stopping."""
    bus = MockEventBus()
    queue = LogQueue(bus)
    queue.start()
    
    # Enqueue many logs
    for i in range(20):
        queue.enqueue("log", {"message": f"Message {i}"}, level="info")
    
    # Stop without explicit flush - should still process all items
    await queue.stop()
    
    # All items should be processed
    assert len(bus.events) == 20


@pytest.mark.asyncio
async def test_multiple_plugin_loggers_maintain_order():
    """Test that multiple plugin loggers sharing a session maintain order."""
    bus = MockEventBus()
    session_logger = SessionLogger("test-session", bus)
    plugin1_logger = session_logger.get_child("plugin-1")
    plugin2_logger = session_logger.get_child("plugin-2")
    
    # Interleave logs from different plugins
    plugin1_logger.info("P1: Start")
    plugin2_logger.info("P2: Start")
    plugin1_logger.info("P1: Middle")
    plugin2_logger.info("P2: Middle")
    plugin1_logger.info("P1: End")
    plugin2_logger.info("P2: End")
    
    # Flush and stop
    await session_logger.flush()
    await session_logger.stop()
    
    # Verify ordering
    assert len(bus.events) == 6
    expected = [
        ("P1: Start", "plugin-1"),
        ("P2: Start", "plugin-2"),
        ("P1: Middle", "plugin-1"),
        ("P2: Middle", "plugin-2"),
        ("P1: End", "plugin-1"),
        ("P2: End", "plugin-2"),
    ]
    for i, (msg, plugin) in enumerate(expected):
        assert bus.events[i]["data"]["payload"]["message"] == msg
        assert bus.events[i]["data"]["payload"]["plugin"] == plugin
