import asyncio
import inspect
import traceback
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel

from fair_platform.extension_sdk.auth import ExtensionCredentials
from fair_platform.extension_sdk.auth import build_extension_auth_headers
from fair_platform.extension_sdk.client import build_platform_client
from fair_platform.extension_sdk.context import JobContext
from fair_platform.extension_sdk.contracts.extension import ExtensionRead, ExtensionRegisterRequest


class FairExtension:
    def __init__(
        self,
        extension_id: str,
        platform_url: str,
        extension_secret: str,
        *,
        webhook_path: str = "/hooks/jobs",
        webhook_url: str | None = None,
        auto_connect: bool = False,
        requested_scopes: list[str] | None = None,
        intents: list[str] | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.extension_id = extension_id
        self.platform_url = platform_url.rstrip("/")
        self.webhook_path = webhook_path if webhook_path.startswith("/") else f"/{webhook_path}"
        self.webhook_url = webhook_url
        self.credentials = ExtensionCredentials(extension_id=extension_id, extension_secret=extension_secret)

        self._requested_scopes = list(requested_scopes or [])
        self._intents = list(intents or [])
        self._capabilities = list(capabilities or [])
        self._metadata = dict(metadata or {})
        self._actions: dict[str, tuple[Callable[..., Awaitable[Any]], type[BaseModel]]] = {}

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            if auto_connect:
                await self.connect()
            yield

        self.app = FastAPI(title=f"FAIR Extension: {extension_id}", lifespan=lifespan)

        @self.app.post(self.webhook_path)
        async def _handle_webhook(request: Request):
            body = await request.json()
            job_id = str(body["job_id"])
            payload = body.get("payload", {})
            action_name = str(payload["action"])
            raw_params = payload.get("params", {})
            asyncio.create_task(self._execute(job_id=job_id, action_name=action_name, raw_params=raw_params))
            return {"accepted": True}

    def action(self, name: str):
        def decorator(func: Callable[..., Awaitable[Any]]):
            signature = inspect.signature(func)
            params = list(signature.parameters.values())
            if len(params) < 2:
                raise ValueError("Action handlers must accept (ctx, params)")
            schema = params[1].annotation
            if not inspect.isclass(schema) or not issubclass(schema, BaseModel):
                raise ValueError("Action handler params annotation must be a Pydantic model")
            self._actions[name] = (func, schema)
            return func

        return decorator

    async def connect(
        self,
        *,
        webhook_url: str | None = None,
        requested_scopes: list[str] | None = None,
        intents: list[str] | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> ExtensionRead:
        resolved_webhook_url = webhook_url or self.webhook_url
        if not resolved_webhook_url:
            raise ValueError("webhook_url is required for extension.connect()")
        payload = ExtensionRegisterRequest(
            extension_id=self.extension_id,
            webhook_url=resolved_webhook_url,
            requested_scopes=requested_scopes if requested_scopes is not None else self._requested_scopes,
            intents=intents if intents is not None else self._intents,
            capabilities=capabilities if capabilities is not None else self._capabilities,
            metadata=metadata if metadata is not None else self._metadata,
        )

        owns_client = client is None
        http = client or build_platform_client(self.platform_url, self.credentials)
        try:
            response = await http.post(
                "/api/extensions/connect",
                json=payload.model_dump(by_alias=True, mode="json"),
                headers=build_extension_auth_headers(self.credentials),
            )
            response.raise_for_status()
            return ExtensionRead.model_validate(response.json())
        finally:
            if owns_client:
                await http.aclose()

    async def _execute(self, job_id: str, action_name: str, raw_params: dict[str, Any]) -> None:
        async with JobContext(job_id=job_id, platform_url=self.platform_url, credentials=self.credentials) as ctx:
            try:
                if action_name not in self._actions:
                    raise ValueError(f"Action '{action_name}' is not registered")
                handler, schema = self._actions[action_name]
                params = schema.model_validate(raw_params)
                result = await handler(ctx, params)
                if result is None:
                    return
                if isinstance(result, BaseModel):
                    result_data = result.model_dump(by_alias=True, mode="json")
                elif isinstance(result, dict):
                    result_data = result
                else:
                    raise ValueError(f"Action '{action_name}' returned unsupported result type: {type(result)}")
                await ctx.result(result_data, status="completed")
            except Exception as exc:
                await ctx.error(error=str(exc), traceback=traceback.format_exc(), status="failed")


__all__ = ["FairExtension"]
