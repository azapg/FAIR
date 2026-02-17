import contextlib
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import UUID

from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User, Workflow, WorkflowRun
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.core.security.permissions import has_capability_or_owner
from fair_platform.backend.core.security.dependencies import require_capability
from fair_platform.backend.services.session_manager import session_manager
from fair_platform.sdk.events import normalize_event_message

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
    ts: str
    type: str
    level: str
    payload: dict | None = None

@router.post("/", response_model=SessionResponse, dependencies=[Depends(require_capability("run_workflow"))])
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
    if not workflow or workflow.archived:
        raise HTTPException(status_code=404, detail="Workflow not found")
    course = db.get(Course, workflow.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not has_capability_or_owner(user, "run_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Not authorized to run this workflow")

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
    def _normalize_entry(entry, fallback_index: int) -> SessionLogItem:
        if isinstance(entry, dict):
            event_name = (
                entry.get("type")
                if isinstance(entry.get("type"), str) and entry.get("type")
                else "event"
            )
        else:
            event_name = "event"

        normalized = normalize_event_message(event_name, entry)
        if not isinstance(normalized.get("index"), int):
            normalized["index"] = fallback_index
        return SessionLogItem.model_validate(normalized)

    # Prefer persisted DB logs when available
    run: WorkflowRun | None = db.get(WorkflowRun, session_id)
    if run and isinstance(run.logs, dict):
        history = run.logs.get("history")
        if isinstance(history, list):
            items: list[SessionLogItem] = []
            for i, entry in enumerate(history):
                item = _normalize_entry(entry, i)
                idx = item.index
                if after is not None and idx <= after:
                    continue
                items.append(item)
            return items

    # Fallback to in-memory buffer if DB not available or empty
    session = session_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    items: list[SessionLogItem] = []
    for i, entry in enumerate(session.buffer):
        item = _normalize_entry(entry, i)
        idx = item.index
        if after is not None and idx <= after:
            continue
        items.append(item)

    return items


@router.websocket("/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: UUID):
    await websocket.accept()

    session = session_manager.sessions.get(session_id)
    if not session:
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {
                    "index": -1,
                    "ts": datetime.now().isoformat(),
                    "type": "close",
                    "level": "error",
                    "payload": {"reason": "Session not found"},
                }
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
        if isinstance(data, dict):
            message = data
        else:
            message = normalize_event_message("close", data)
        if not isinstance(message.get("index"), int):
            message["index"] = -1
        if not isinstance(message.get("level"), str) or not message.get("level"):
            message["level"] = "info"
        if not isinstance(message.get("ts"), str) or not message.get("ts"):
            message["ts"] = datetime.now().isoformat()
        try:
            await _send_safe(message)
        finally:
            active = False
            with contextlib.suppress(Exception):
                await websocket.close()
            with contextlib.suppress(Exception):
                session.bus.off("log", _handler)
                session.bus.off("image", _handler)
                session.bus.off("image_group", _handler)
                session.bus.off("file", _handler)
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
    session.bus.on("image", _handler)
    session.bus.on("image_group", _handler)
    session.bus.on("file", _handler)
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
            session.bus.off("image", _handler)
            session.bus.off("image_group", _handler)
            session.bus.off("file", _handler)
            session.bus.off("update", _handler)
            session.bus.off("close", _close_handler)
        with contextlib.suppress(Exception):
            await websocket.close()
