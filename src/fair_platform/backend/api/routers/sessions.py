from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from sqlalchemy.orm import Session
from starlette.websockets import WebSocket

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.workflow import WorkflowBase
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import User

router = APIRouter()


class SessionCreateRequest(BaseModel):
    workflow_id: Optional[UUID] = None
    workflow_draft = Optional[WorkflowBase] = False
    submission_ids: List[UUID]


class SessionResponse(BaseModel):
    session_id: UUID
    status: str
    ws_url: str


@router.post("/")
def create_session(payload: SessionCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(session_dependency)):
    if payload.workflow_id:
        raise HTTPException(status_code=501, detail="Creating a session from an existing workflow is not implemented")

    if not payload.workflow_draft:
        raise HTTPException(status_code=400, detail="Creating a session from a non-draft workflow is not implemented")

    if not payload.submission_ids:
        raise HTTPException(status_code=400, detail="At least one submission ID must be provided")

    workflow = payload.workflow_draft

    # TODO: From here, we need to:
    #   1. Create some sort of task that will manage the session lifecycle
    #   2. Create a session entry in the database
    #   3. Make that task start processing the submissions with the workflow. It should go through
    #      plugins step by step, running each plugin on all submissions before moving to the next plugin.
    #   4. The websocket should be able to manage and retrieve the status of the session and stream logs.

    return None

# ws://HOST/api/sessions/{session_id}
@router.websocket("{session_id}")
def websocket_session(websocket: WebSocket, session_id: UUID, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented")
