import asyncio
import contextlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.workflow import WorkflowBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User, Workflow, Course
from fair_platform.backend.services.session_manager import session_manager

router = APIRouter()


class SessionCreateRequest(BaseModel):
    workflow_id: Optional[UUID] = None
    workflow_draft: Optional[WorkflowBase] = None
    submission_ids: List[UUID]


class SessionResponse(BaseModel):
    session: WorkflowRunRead
    status: str
    ws_url: str


@router.post("/", response_model=Optional[SessionResponse])
async def create_session(payload: SessionCreateRequest, user: User = Depends(get_current_user),
                         db: Session = Depends(session_dependency)):
    if payload.workflow_id:
        raise HTTPException(status_code=501, detail="Creating a session from an existing workflow is not implemented")

    if not payload.workflow_draft:
        raise HTTPException(status_code=400, detail="Creating a session from a non-draft workflow is not implemented")

    if not payload.submission_ids:
        raise HTTPException(status_code=400, detail="At least one submission ID must be provided")

    # TODO: The main reason I am allowing drafts here is to simplify frontend, but it might be better to
    #  save the draft as a workflow first and then create a session from that workflow. This right
    #  now doesn't allow for reruns.
    draft = payload.workflow_draft

    if not draft.plugins or not any(plugin in draft.plugins for plugin in ["transcriber", "grader", "validator"]):
        raise HTTPException(status_code=400,
                            detail="At least one plugin (transcriber, grader, or validator) must be specified in the workflow draft")

    workflow_course = db.get(Course, draft.course_id)
    if not workflow_course:
        raise HTTPException(status_code=404, detail="Course not found")

    if user.role != "admin" and workflow_course.instructor_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to create a session for this course")

    workflow = Workflow(
        id=uuid4(),
        name=draft.name,
        description=draft.description,
        course_id=draft.course_id,
        created_by=user.id,
        created_at=datetime.now(),

        transcriber_plugin_id=draft.plugins.get(
            "transcriber").id if draft.plugins and "transcriber" in draft.plugins else None,
        grader_plugin_id=draft.plugins.get("grader").id if draft.plugins and "grader" in draft.plugins else None,
        validator_plugin_id=draft.plugins.get(
            "validator").id if draft.plugins and "validator" in draft.plugins else None,

        transcriber_settings=draft.plugins.get(
            "transcriber").settings if draft.plugins and "transcriber" in draft.plugins else None,
        grader_settings=draft.plugins.get("grader").settings if draft.plugins and "grader" in draft.plugins else None,
        validator_settings=draft.plugins.get(
            "validator").settings if draft.plugins and "validator" in draft.plugins else None,
    )

    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    session = session_manager.create_session(workflow.id, payload.submission_ids, user)
    return {"session": session, "status": "pending", "ws_url": f"ws://localhost:8000/api/sessions/{session.id}"}



@router.websocket("/{session_id}")
async def websocket_session(websocket: WebSocket, session_id: UUID):
    await websocket.accept()

    session = session_manager.sessions.get(session_id)
    if not session:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "close", "reason": "Session not found"})
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
        if isinstance(data, dict):
            reason = data.get("reason", "")
        try:
            await _send_safe({"type": "close", "reason": reason})
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
