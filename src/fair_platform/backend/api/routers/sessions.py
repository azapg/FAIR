from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID

from starlette.websockets import WebSocket

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import User

router = APIRouter()


class SessionCreateRequest(BaseModel):
    workflow_id: UUID
    submission_ids: List[UUID]


class SessionResponse(BaseModel):
    session_id: UUID
    status: str
    ws_url: str


@router.post("/")
def create_session(payload: SessionCreateRequest, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented")


# ws://HOST/api/sessions/{session_id}
@router.websocket("{session_id}")
def websocket_session(websocket: WebSocket, session_id: UUID, user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented")
