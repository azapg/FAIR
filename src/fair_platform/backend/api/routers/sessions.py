import contextlib
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import UUID

from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User, Workflow, WorkflowRun
from fair_platform.backend.services.session_manager import session_manager

router = APIRouter()


class SessionCreateRequest(BaseModel):
    workflow_id: UUID
    submission_ids: List[UUID]


class SessionResponse(BaseModel):
    session: WorkflowRunRead
    status: str
    ws_url: str


class SessionLogItem(BaseModel):
    index: int
    type: str
    ts: str | None = None
    level: str | None = None
    plugin: str | None = None
    message: str | None = None
    object: str | None = None
    payload: dict | None = None


@router.post("/", response_model=SessionResponse)
async def create_session(
    payload: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    if not payload.submission_ids:
        raise HTTPException(
            status_code=400, detail="At least one submission ID must be provided"
        )

    workflow = db.get(Workflow, payload.workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    session = session_manager.create_session(workflow.id, payload.submission_ids, user)
    return {
        "session": session,
        "status": "pending",
        "ws_url": f"ws://localhost:8000/api/sessions/{session.id}",
    }


@router.get("/{session_id}/logs", response_model=list[SessionLogItem])
def get_session_logs(
    session_id: UUID,
    after: int | None = Query(
        None, description="Return logs with index greater than this value"
    ),
    db: Session = Depends(session_dependency),
):
    # Prefer persisted DB logs when available
    run: WorkflowRun | None = db.get(WorkflowRun, session_id)
    if run and isinstance(run.logs, dict):
        history = run.logs.get("history")
        if isinstance(history, list):
            items: list[SessionLogItem] = []
            for i, entry in enumerate(history):
                if not isinstance(entry, dict):
                    if after is not None:
                        continue
                    items.append(
                        SessionLogItem(
                            index=-1, type="event", payload={"raw": str(entry)}
                        )
                    )
                    continue

                idx = entry.get("index")
                if not isinstance(idx, int):
                    idx = i  # derive a stable index if missing
                if after is not None and idx <= after:
                    continue

                typ = entry.get("type", "event")
                ts = entry.get("ts")
                level = entry.get("level")
                payload = (
                    entry.get("payload")
                    if isinstance(entry.get("payload"), dict)
                    else None
                )
                plugin = None
                message = None
                if typ == "log" and payload:
                    plugin = payload.get("plugin")
                    message = payload.get("message")

                items.append(
                    SessionLogItem(
                        index=idx,
                        type=typ,
                        ts=ts,
                        level=level,
                        plugin=plugin,
                        message=message,
                        object=entry.get("object"),
                        payload=payload or entry,
                    )
                )
            return items

    # Fallback to in-memory buffer if DB not available or empty
    session = session_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    items: list[SessionLogItem] = []
    for entry in session.buffer:
        if not isinstance(entry, dict):
            if after is not None:
                continue
            items.append(
                SessionLogItem(index=-1, type="event", payload={"raw": str(entry)})
            )
            continue

        idx = entry.get("index", -1)
        if after is not None and idx <= after:
            continue
        typ = entry.get("type", "event")
        ts = entry.get("ts")
        level = entry.get("level")
        payload = (
            entry.get("payload") if isinstance(entry.get("payload"), dict) else None
        )
        plugin = payload.get("plugin") if (typ == "log" and payload) else None
        message = payload.get("message") if (typ == "log" and payload) else None

        items.append(
            SessionLogItem(
                index=idx,
                type=typ,
                ts=ts,
                level=level,
                plugin=plugin,
                message=message,
                object=entry.get("object"),
                payload=payload or entry,
            )
        )

    return items


@router.websocket("/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: UUID):
    await websocket.accept()

    session = session_manager.sessions.get(session_id)
    if not session:
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {"type": "close", "reason": "Session not found", "index": -1}
            )
            await websocket.close()
        return

    # Active state to prevent sends after close
    active = True

    async def _send_safe(message: dict):
        nonlocal active
        if not active:
            return
        try:
            await websocket.send_json(message)
        except Exception:
            # Any failure implies we should stop sending further messages
            active = False

    async def _close_handler(data):
        nonlocal active
        if not active:
            return
        reason = ""
        index = -1
        if isinstance(data, dict):
            reason = data.get("reason", "")
            index = data.get("index", -1)
        try:
            await _send_safe({"type": "close", "reason": reason, "index": index})
        finally:
            active = False
            with contextlib.suppress(Exception):
                await websocket.close()
            with contextlib.suppress(Exception):
                session.bus.off("log", _handler)
                session.bus.off("update", _handler)
                session.bus.off("close", _close_handler)

    for log in session.buffer:
        await _send_safe(log)
        if not active:
            break

    async def _handler(data: dict):
        await _send_safe(data)

    # TODO: I should just be able to do this with a wildcard, but for now, explicitly subscribe to known events
    session.bus.on("log", _handler)
    session.bus.on("update", _handler)
    session.bus.on("close", _close_handler)

    try:
        while active:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        active = False
        with contextlib.suppress(Exception):
            session.bus.off("log", _handler)
            session.bus.off("update", _handler)
            session.bus.off("close", _close_handler)
        with contextlib.suppress(Exception):
            await websocket.close()
