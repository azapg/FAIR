# Extension Messaging Protocol - Implementation Spec

**Target File for Agent:** `src/fair_platform/backend/api/schema/job.py`
**Scope:** Update the Pydantic schema definitions to enforce a standardized messaging protocol for jobs.

## 1. Objective

Transition the `payload` fields in the Jobs API from free-form dictionaries (`dict[str, Any]`) to strongly typed, predictable structures using Pydantic Discriminated Unions.

## 2. Protocol Definitions

### A. Job Creation (Frontend -> API)

**Schema Name:** `ActionPayload`
**Fields:**

* `action` (str): The specific method to run on the extension (e.g., `"rubric.create"`). Required.
* `params` (dict[str, Any]): Strongly typed arguments for the action. Defaults to an empty dict.

*Integration:* Update `JobCreateRequest.payload` to use `ActionPayload` instead of `dict[str, Any]`.

### B. Job Updates (Extension -> API)

Define the following schemas for the different types of update payloads:

1. **`ProgressPayload`**
* `percent` (int): Required. (0-100)
* `message` (str | None): Optional.


2. **`LogPayload`**
* `level` (Literal["debug", "info", "warn", "error"]): Required.
* `output` (str): Required.


3. **`TokenPayload`**
* `text` (str): Required.


4. **`ResultPayload`**
* `data` (dict[str, Any]): Required.


5. **`ErrorPayload`**
* `error` (str): Required.
* `traceback` (str | None): Optional.



### C. Discriminated Union Wrapper

Create wrapper models that tie the literal `event` string to its specific payload:

```python
class JobUpdateProgress(BaseModel):
    event: Literal["progress"]
    payload: ProgressPayload

class JobUpdateLog(BaseModel):
    event: Literal["log"]
    payload: LogPayload

class JobUpdateToken(BaseModel):
    event: Literal["token"]
    payload: TokenPayload

class JobUpdateResult(BaseModel):
    event: Literal["result"]
    payload: ResultPayload

class JobUpdateError(BaseModel):
    event: Literal["error"]
    payload: ErrorPayload

# The router will accept any of these valid update types
JobUpdateEvent = Union[
    JobUpdateProgress, 
    JobUpdateLog, 
    JobUpdateToken, 
    JobUpdateResult, 
    JobUpdateError
]

```

*Integration:* Modify `JobUpdateRequest`. Replace `event: str` and `payload: dict` with:
`update: JobUpdateEvent = Field(..., discriminator="event")`

*(Note for Agent: Ensure the `jobs.py` router unpacks `payload.update.event` and `payload.update.payload.model_dump()` correctly before passing to `JobQueue.publish_update` to maintain backwards compatibility with the queue).*

## 3. Example: Rubric Generation

This is how the new protocol will look over the wire when generating a rubric. Also, see how we currently generate rubrics in the rubric_service.py for reference. The protocol should be able to support all of the same interactions and more.

**1. Frontend requests a rubric (POST `/api/jobs/`)**

```json
{
  "target": "fair-official-grader",
  "payload": {
    "action": "rubric.create",
    "params": {
      "assignment_topic": "History of the Panama Canal",
    }
  }
}

```

**2. Extension streams progress (POST `/api/jobs/{job_id}/updates`)**

```json
{
  "event": "progress",
  "payload": {
    "percent": 10,
    "message": "Analyzing assignment topic..."
  }
}

```

**3. Extension streams logs (POST `/api/jobs/{job_id}/updates`)**

```json
{
  "event": "log",
  "payload": {
    "level": "info",
    "output": "Targeting University level with 100 max points."
  }
}

```

**4. Extension returns final rubric (POST `/api/jobs/{job_id}/updates`)**

```json
{
  "event": "result",
  "status": "completed",
  "payload": {
    "data": {
      "rubric_matrix": // see rubric_service.py for example structure of this field
    }
  }
}

```