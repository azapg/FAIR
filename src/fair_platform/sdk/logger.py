import asyncio
import threading
from datetime import datetime
from typing import Optional

from fair_platform.sdk.events import EventBus


class LogQueue:
    """
    Async FIFO queue for log entries that ensures deterministic ordering.
    
    This solves the problem where synchronous plugin code running in an executor
    creates fire-and-forget log tasks that get processed out of order.
    
    Usage:
        - Logs are enqueued immediately with their timestamp
        - A background flusher task consumes logs in FIFO order
        - Call `flush()` to ensure all pending logs are processed
        - Call `stop()` to stop the flusher task
    """
    
    def __init__(self, bus: EventBus):
        self.bus = bus
        self._queue: asyncio.Queue = asyncio.Queue()
        self._flusher_task: Optional[asyncio.Task] = None
        self._running = False
        self._started = False
        self._loop_thread_id: Optional[int] = None
    
    @property
    def is_started(self) -> bool:
        """Check if the queue flusher has been started."""
        return self._started
    
    def start(self):
        """Start the background flusher task."""
        if self._started:
            return
        self._running = True
        self._started = True
        # Record the event loop thread ID for thread-safe enqueuing
        self._loop_thread_id = threading.current_thread().ident
        self._flusher_task = asyncio.create_task(self._flusher())
    
    async def _flusher(self):
        """Background task that consumes log entries in FIFO order."""
        while self._running or not self._queue.empty():
            try:
                # Use a timeout so we can check _running periodically
                entry = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._emit_entry(entry)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                # Drain remaining items before exiting
                while not self._queue.empty():
                    try:
                        entry = self._queue.get_nowait()
                        await self._emit_entry(entry)
                        self._queue.task_done()
                    except asyncio.QueueEmpty:
                        break
                raise
    
    async def _emit_entry(self, entry: dict):
        """Emit a single log entry to the event bus."""
        await self.bus.emit(
            entry["event_type"],
            data={
                "type": "log",
                "ts": entry["ts"],
                "level": entry["level"],
                "payload": entry["payload"],
            },
        )
    
    def enqueue(self, event_type: str, payload: dict, *, level: str = "info"):
        """
        Enqueue a log entry with the current timestamp.
        
        This is safe to call from sync code running in an executor.
        The timestamp is captured immediately to preserve ordering.
        """
        entry = {
            "event_type": event_type,
            "ts": datetime.now().isoformat(),
            "level": level,
            "payload": payload,
        }
        
        # Check if we're on the event loop thread
        current_thread_id = threading.current_thread().ident
        if self._loop_thread_id is not None and current_thread_id == self._loop_thread_id:
            # Same thread as event loop - put directly (no race condition)
            self._queue.put_nowait(entry)
        else:
            # Different thread (e.g., from executor) - use thread-safe scheduling
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(self._queue.put_nowait, entry)
            except RuntimeError:
                # No running loop - put directly
                self._queue.put_nowait(entry)
    
    async def flush(self):
        """Wait for all pending log entries to be processed."""
        if self._queue.empty():
            return
        await self._queue.join()
    
    async def stop(self):
        """Stop the flusher task and process remaining logs."""
        self._running = False
        if self._flusher_task:
            # Wait for the flusher to finish processing remaining items
            try:
                await asyncio.wait_for(self._flusher_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._flusher_task.cancel()
                try:
                    await self._flusher_task
                except asyncio.CancelledError:
                    pass
            self._flusher_task = None
        self._started = False


class SessionLogger:
    """
    Logger for workflow sessions that ensures deterministic log ordering.
    
    This logger uses an internal async queue (LogQueue) to ensure that logs
    appear in the same order they are invoked, regardless of whether the caller
    is sync or async code.
    
    The queue captures timestamps immediately when log() is called, then
    processes entries in FIFO order via a background flusher task.
    """
    
    def __init__(self, session_id: str, bus: EventBus):
        self.session_id = session_id
        self.bus = bus
        self._log_queue: Optional[LogQueue] = None
    
    def _ensure_queue(self):
        """Lazily initialize and start the log queue."""
        if self._log_queue is None:
            self._log_queue = LogQueue(self.bus)
        if not self._log_queue.is_started:
            try:
                asyncio.get_running_loop()
                self._log_queue.start()
            except RuntimeError:
                # No event loop - queue will be started later
                pass

    def log(self, level: str, message: str):
        return self.emit("log", {"message": message}, level=level)

    def info(self, message: str):
        return self.log("info", message)

    def warning(self, message: str):
        return self.log("warning", message)

    def error(self, message: str):
        return self.log("error", message)

    def debug(self, message: str):
        return self.log("debug", message)

    async def _emit_async(self, event_type: str, payload: dict, *, level: str = "info"):
        """Direct async emission - used when await is possible."""
        await self.bus.emit(
            event_type,
            data={
                "type": "log",
                "ts": datetime.now().isoformat(),
                "level": level,
                "payload": payload,
            },
        )

    def emit(self, event_type: str, payload: dict, *, level: str = "info"):
        """
        Emit a log entry.
        
        Uses the log queue to ensure deterministic ordering when called from
        sync plugin code. The timestamp is captured immediately.
        """
        try:
            asyncio.get_running_loop()
            # Running in async context - use the queue for ordering
            self._ensure_queue()
            self._log_queue.enqueue(event_type, payload, level=level)
            return None
        except RuntimeError:
            # No running loop - emit directly (blocking)
            return asyncio.run(self._emit_async(event_type, payload, level=level))
    
    async def flush(self):
        """
        Flush all pending log entries.
        
        Call this before session completion to ensure all logs are processed.
        """
        if self._log_queue:
            await self._log_queue.flush()
    
    async def stop(self):
        """
        Stop the logger and process remaining logs.
        
        Call this when the session is complete.
        """
        if self._log_queue:
            await self._log_queue.stop()
            self._log_queue = None

    def get_child(self, plugin_id: str):
        """Return a logger for a specific plugin"""
        return PluginLogger(plugin_id, self.session_id, bus=self.bus, parent=self)


class PluginLogger(SessionLogger):
    """
    Logger for individual plugins that shares the parent session's log queue.
    
    Plugin logs include the plugin identifier in the payload for filtering
    and attribution in the frontend.
    """
    
    def __init__(
        self, 
        identifier: str, 
        session_id: str, 
        bus: EventBus,
        parent: Optional[SessionLogger] = None
    ):
        super().__init__(session_id, bus)
        self.identifier = identifier
        self._parent = parent
        # Share the parent's log queue if available
        if parent and parent._log_queue:
            self._log_queue = parent._log_queue

    def _ensure_queue(self):
        """Share the parent's queue or create our own."""
        if self._parent:
            self._parent._ensure_queue()
            self._log_queue = self._parent._log_queue
        else:
            super()._ensure_queue()

    def log(self, level: str, message: str):
        return self.emit(
            "log", {"message": message, "plugin": self.identifier}, level=level
        )
