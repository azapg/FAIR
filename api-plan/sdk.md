# FAIR Python SDK - Minimal Implementation Specification

**Target Directory:** `src/fair_platform/sdk/`
**Goal:** Implement a lightweight, zero-backend-dependency extension SDK that handles the Extension Messaging Protocol (FAP) webhook routing, strongly typed contracts, and domain-specific wrappers.

## 1. Directory Structure

The agent should create or update the following files inside `src/fair_platform/sdk/`:

```text
src/fair_platform/sdk/
├── __init__.py           # Public exports
├── context.py            # JobContext for API communication
├── extension.py          # FairExtension (FastAPI server & routers)
└── contracts/
    ├── __init__.py
    └── rubric.py         # Pydantic models for rubric generation

```

## 2. File Specifications

### A. The Communication Layer: `context.py`

This class abstracts the HTTP requests to the FAIR API to publish protocol-compliant events.

**Requirements:**

* Must use `httpx.AsyncClient`.
* Must implement methods for `progress`, `log`, and `complete`.
* Payloads must exactly match the Extension Messaging Protocol definitions.

```python
# src/fair_platform/sdk/context.py
import httpx
from typing import Any, Optional

class JobContext:
    def __init__(self, job_id: str, api_url: str, api_key: str):
        self.job_id = job_id
        self._api = httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )

    async def progress(self, percent: int, message: Optional[str] = None) -> None:
        """Emits a standardized progress update."""
        await self._api.post(
            f"/api/jobs/{self.job_id}/updates",
            json={
                "event": "progress",
                "payload": {"percent": percent, "message": message}
            }
        )

    async def log(self, level: str, output: str) -> None:
        """Emits a terminal log stream."""
        await self._api.post(
            f"/api/jobs/{self.job_id}/updates",
            json={
                "event": "log",
                "payload": {"level": level, "output": output}
            }
        )

    async def complete(self, data: dict[str, Any]) -> None:
        """Marks the job as successful with the final data."""
        await self._api.post(
            f"/api/jobs/{self.job_id}/updates",
            json={
                "event": "result",
                "status": "completed",
                "payload": {"data": data}
            }
        )

```

### B. The Data Contracts: `contracts/rubric.py`

These are the strictly typed Pydantic models that ensure extensions input and output exactly what the FAIR platform expects.

```python
# src/fair_platform/sdk/contracts/rubric.py
from pydantic import BaseModel, Field

class RubricParams(BaseModel):
    """Input parameters provided by FAIR to the extension."""
    assignment_topic: str
    max_points: int
    grade_level: str | None = None

class RubricRow(BaseModel):
    criterion: str
    max_points: int
    description: str | None = None

class RubricResult(BaseModel):
    """Strictly typed output expected back by FAIR."""
    rows: list[RubricRow] = Field(default_factory=list)

```

### C. The Application Server: `extension.py`

This is the core FastAPI wrapper that receives webhooks from the FAIR dispatcher and routes them to the developer's functions. It includes the generic `action` router and the domain-specific `rubric_generator` wrapper.

```python
# src/fair_platform/sdk/extension.py
import asyncio
import functools
import traceback
from typing import Callable, Awaitable, Type, Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from .context import JobContext
from .contracts.rubric import RubricParams, RubricResult

class StreamHelper:
    """A stripped-down context for domain wrappers, preventing manual completion."""
    def __init__(self, ctx: JobContext):
        self._ctx = ctx
        
    async def log(self, level: str, msg: str) -> None:
        await self._ctx.log(level, msg)
        
    async def progress(self, percent: int, msg: str | None = None) -> None:
        await self._ctx.progress(percent, msg)

class FairExtension:
    def __init__(self, extension_id: str, api_url: str, api_key: str):
        self.extension_id = extension_id
        self.api_url = api_url
        self.api_key = api_key
        
        self.app = FastAPI(title=f"FAIR Extension: {extension_id}")
        self._actions: dict[str, tuple[Callable, Type[BaseModel]]] = {}

        @self.app.post("/webhook")
        async def handle_webhook(request: Request):
            data = await request.json()
            job_id = data["job_id"]
            action_name = data["payload"]["action"]
            raw_params = data["payload"].get("params", {})
            
            # Fire and forget to free the FAIR dispatcher instantly
            asyncio.create_task(self._execute(job_id, action_name, raw_params))
            return {"accepted": True}

    def action(self, name: str):
        """Generic, base-level action routing."""
        def decorator(func: Callable):
            import inspect
            sig = inspect.signature(func)
            schema = sig.parameters["params"].annotation
            self._actions[name] = (func, schema)
            return func
        return decorator

    def rubric_generator(self, func: Callable[[RubricParams, StreamHelper], Awaitable[RubricResult]]):
        """Domain-specific wrapper enforcing the Rubric Contract."""
        @self.action("rubric.create")
        @functools.wraps(func)
        async def wrapper(ctx: JobContext, params: RubricParams):
            stream = StreamHelper(ctx)
            
            result: RubricResult = await func(params, stream)
            
            if not isinstance(result, RubricResult):
                raise ValueError(f"rubric_generator must return RubricResult, got {type(result)}")
                
            # Automatically unpack the Pydantic model for the generic completion
            return result.model_dump()
            
        return wrapper

    async def _execute(self, job_id: str, action_name: str, raw_params: dict):
        ctx = JobContext(job_id, self.api_url, self.api_key)
        try:
            if action_name not in self._actions:
                raise ValueError(f"Action '{action_name}' not registered on this extension.")
                
            handler, schema = self._actions[action_name]
            validated_params = schema(**raw_params)
            
            result = await handler(ctx, validated_params)
            
            # If the handler returned data (like the rubric wrapper does), complete it
            if result is not None:
                if hasattr(result, "model_dump"):
                    result = result.model_dump()
                await ctx.complete(result)

        except Exception as e:
            # Protocol-compliant error boundary
            await ctx._api.post(
                f"/api/jobs/{job_id}/updates",
                json={
                    "event": "error",
                    "status": "failed",
                    "payload": {
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                }
            )

```

### D. The Public API: `__init__.py`

Make imports clean and easy for developers.

```python
# src/fair_platform/sdk/__init__.py
from .extension import FairExtension, StreamHelper
from .context import JobContext

__all__ = ["FairExtension", "JobContext", "StreamHelper"]

```