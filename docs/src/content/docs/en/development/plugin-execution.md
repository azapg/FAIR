---
title: Plugin Execution
description: Understanding how plugins execute in FAIR Platform
---

FAIR Platform plugins run within a workflow execution context managed by the Session Manager. This document covers plugin lifecycle, logging behavior, and best practices for plugin development.

## Plugin Lifecycle

When a workflow is executed, the Session Manager orchestrates plugin execution through several phases:

### 1. Initialization

When a workflow run starts, the Session Manager:

1. Creates a `Session` object with a unique session ID
2. Initializes an `IndexedEventBus` for event communication
3. Creates a `SessionLogger` for the workflow run
4. Loads and instantiates plugins (transcriber, grader, validator)

```python
# Plugin initialization example
transcriber_instance = transcriber_cls(
    session.logger.get_child(workflow.transcriber_plugin_id)
)
transcriber_instance.set_values(workflow.transcriber_settings or {})
```

### 2. Settings Configuration

Each plugin instance receives settings via `set_values()`. These settings come from the workflow configuration and must match the plugin's declared settings fields:

```python
class MyTranscriber(TranscriptionPlugin):
    instructions = TextField(label="Instructions", required=True)
    
    def transcribe(self, submission):
        # Access settings via self.instructions.value
        prompt = self.instructions.value
        ...
```

### 3. Execution

Plugins can implement either individual or batch processing methods:

- **Individual processing**: `transcribe()`, `grade()`, `validate_one()`
- **Batch processing**: `transcribe_batch()`, `grade_batch()`, `validate_batch()`

The Session Manager detects which method is overridden and uses the appropriate execution strategy.

### 4. Sync vs Async Execution

Plugins can be either synchronous or asynchronous:

```python
# Synchronous plugin (runs in executor)
def transcribe(self, submission) -> TranscribedSubmission:
    result = do_sync_work(submission)
    return TranscribedSubmission(transcription=result, confidence=0.95)

# Asynchronous plugin (runs directly)
async def transcribe(self, submission) -> TranscribedSubmission:
    result = await do_async_work(submission)
    return TranscribedSubmission(transcription=result, confidence=0.95)
```

The Session Manager automatically handles both:
- Async methods run directly with `await`
- Sync methods run in a thread pool executor via `loop.run_in_executor()`

## Logging System

### Overview

FAIR Platform provides a deterministic logging system that ensures logs appear in the exact order they are invoked, regardless of whether the plugin is synchronous or asynchronous.

### How It Works

The logging system uses an internal async queue (`LogQueue`) to ensure FIFO ordering:

1. **Immediate timestamp capture**: When `logger.info()` is called, the timestamp is captured immediately
2. **Queue-based processing**: Log entries are enqueued in order
3. **Background flusher**: A background task consumes entries in FIFO order
4. **Flush on completion**: All pending logs are flushed before session completion

```python
# Plugin logging example
class MyGrader(GradePlugin):
    def grade(self, transcribed, original) -> GradeResult:
        self.logger.info("Starting grade computation")
        
        # Do grading work...
        score = compute_score(transcribed)
        
        self.logger.info(f"Computed score: {score}")
        return GradeResult(score=score, feedback="Good work!")
```

### Logging Methods

The plugin logger provides standard logging methods:

| Method | Use Case |
|--------|----------|
| `self.logger.info(msg)` | Informational messages |
| `self.logger.warning(msg)` | Warning conditions |
| `self.logger.error(msg)` | Error conditions |
| `self.logger.debug(msg)` | Debug information |

### Log Ordering Guarantees

The logging system provides these guarantees:

1. **Deterministic ordering**: Logs appear in the exact order they are called
2. **Preserved across plugins**: Logs from different plugins in the same workflow maintain their relative order
3. **Sync-safe**: Sync plugins running in executors maintain log ordering
4. **Indexed events**: Each log entry receives a sequential index for frontend ordering

### Best Practices

**Do:**
```python
def grade(self, transcribed, original):
    self.logger.info("Processing submission")
    
    # Work...
    
    self.logger.info("Processing complete")
    return result
```

**Avoid:**
- Don't use `print()` for logging (won't appear in the UI)
- Don't spawn separate threads that log independently

## Event System

### IndexedEventBus

The session uses an `IndexedEventBus` that adds sequential indices to all events:

```python
# Events include an index field for ordering
{
    "type": "log",
    "ts": "2024-01-15T10:30:00.000000",
    "level": "info",
    "payload": {"message": "Processing...", "plugin": "my-plugin-id"},
    "index": 42
}
```

### Event Types

| Event | Description |
|-------|-------------|
| `log` | Log entries from plugins and session manager |
| `update` | Status updates for submissions and workflow runs |
| `close` | Session completion notification |

## Error Handling

### Plugin Exceptions

If a plugin raises an exception, the Session Manager:

1. Logs the error with context
2. Marks the affected submission as `failure`
3. Continues processing remaining submissions (for individual mode)
4. Reports failure if batch processing fails entirely

```python
def transcribe(self, submission):
    try:
        result = process(submission)
        return TranscribedSubmission(transcription=result, confidence=0.95)
    except ExternalAPIError as e:
        # The exception will be caught by Session Manager
        # It will be logged and the submission marked as failed
        raise RuntimeError(f"Transcription failed: {e}")
```

### Graceful Degradation

The validation step is designed for graceful degradation:

- If validation fails for a single submission, other submissions continue
- If batch validation fails entirely, the error is logged but doesn't fail the workflow
- Validation results are optional modifiers to grades

## Parallelism

### Configuration

Workflow runs accept a `parallelism` parameter that controls concurrent processing:

```python
session_manager.create_session(
    workflow_id=workflow_id,
    submission_ids=submission_ids,
    user=current_user,
    parallelism=10  # Process up to 10 submissions concurrently
)
```

### Batch vs Individual

- **Batch methods** ignore the parallelism setting—the plugin handles batching
- **Individual methods** use an `asyncio.Semaphore` to limit concurrent executions

### Plugin Considerations

When implementing batch methods:
- Handle your own parallelism if needed (e.g., for API rate limits)
- Return results in the same order as inputs
- Process all items or raise an exception (no partial results)

## Session Completion

When a workflow completes:

1. All pending logs are flushed
2. The logger is stopped
3. A close event is emitted
4. The workflow run status is updated to `success` or `failure`

This ensures all logs appear before the "Session completed" message in the frontend.

## Example Plugin

Here's a complete example demonstrating best practices:

```python
from abc import ABC
from typing import List
from fair_platform.sdk import (
    TranscriptionPlugin,
    TextField,
    TranscribedSubmission,
    FairPlugin,
    Submission,
)

@FairPlugin(
    id="example.transcriber",
    name="Example Transcriber",
    version="1.0.0",
    author="Your Name",
    description="Example transcriber with proper logging",
)
class ExampleTranscriber(TranscriptionPlugin, ABC):
    instructions = TextField(
        label="Instructions",
        required=True,
        default="Transcribe the following content.",
    )

    def transcribe(self, submission: Submission) -> TranscribedSubmission:
        self.logger.info(f"Starting transcription for {submission.id}")
        
        # Do transcription work
        transcription = f"{self.instructions.value} - Content from {submission.id}"
        confidence = 0.95
        
        self.logger.info(f"Transcription completed for {submission.id}")
        
        return TranscribedSubmission(
            transcription=transcription,
            confidence=confidence,
        )

    def transcribe_batch(
        self, submissions: List[Submission]
    ) -> List[TranscribedSubmission]:
        self.logger.info(f"Starting batch transcription for {len(submissions)} items")
        results = [self.transcribe(sub) for sub in submissions]
        self.logger.info("Batch transcription completed")
        return results
```

## Debugging

### Log Inspection

Workflow run logs are stored in the database and accessible via:
- The workflow run detail page in the UI
- The `/api/workflows/runs/{run_id}` endpoint
- Direct database inspection of the `workflow_runs.logs` column

### Common Issues

1. **Logs appearing out of order**: This should not happen with the current implementation. If it does, ensure you're using the provided logger and not custom async logging.

2. **Missing logs**: Ensure you're using `self.logger` and not `print()` or standard Python logging.

3. **Plugin crashes**: Check the error logs for exceptions. Common causes:
   - Missing required settings
   - External API failures
   - Invalid input data

4. **Slow execution**: Consider:
   - Implementing batch methods for bulk operations
   - Adjusting the parallelism setting
   - Optimizing external API calls
