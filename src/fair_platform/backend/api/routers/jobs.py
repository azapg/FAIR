import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobStateRead,
    JobUpdateRequest,
    JobUpdateResponse,
)
from fair_platform.backend.api.schema.rubric import RubricGenerateResponse
from fair_platform.backend.services.job_queue import (
    JobMessage,
    JobQueue,
    JobStatus,
    JobUpdate,
    create_job_queue,
)
from fair_platform.backend.core.security.dependencies import require_extension_client
from fair_platform.backend.data.models import ExtensionClient, User

router = APIRouter()
TERMINAL_JOB_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


async def get_job_queue(request: Request) -> JobQueue:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        queue = await create_job_queue()
        request.app.state.job_queue = queue
    return queue


@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreateResponse)
async def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    queue: JobQueue = Depends(get_job_queue),
):
    job_id = payload.job_id or str(uuid4())
    existing = await queue.get_state(job_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job with id {job_id!r} already exists",
        )

    job = JobMessage(
        job_id=job_id,
        target=payload.target,
        payload=payload.payload.model_dump(),
        metadata=payload.metadata,
    )
    await queue.enqueue(job)
    await queue.set_state(
        job_id=job_id,
        status=JobStatus.QUEUED,
        details={
            "target": payload.target,
            "action": payload.payload.action,
            "owner_user_id": str(current_user.id),
            "owner_extension_id": payload.target,
        },
    )
    return JobCreateResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/{job_id}", response_model=JobStateRead)
async def get_job_state(
    job_id: str,
    current_user: User = Depends(get_current_user),
    queue: JobQueue = Depends(get_job_queue),
):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    owner_user_id = state.details.get("owner_user_id")
    if owner_user_id and owner_user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user cannot access this job",
        )
    return JobStateRead(
        job_id=state.job_id,
        status=state.status,
        updated_at=state.updated_at,
        details=state.details,
    )


@router.post("/{job_id}/updates", response_model=JobUpdateResponse)
async def publish_job_update(
    job_id: str,
    payload: JobUpdateRequest,
    _extension_client: ExtensionClient = Depends(require_extension_client),
    queue: JobQueue = Depends(get_job_queue),
):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    owner_extension_id = state.details.get("owner_extension_id")
    if owner_extension_id and owner_extension_id != _extension_client.extension_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated extension cannot update this job",
        )

    normalized_update_payload = payload.update.payload.model_dump()
    job_action = state.details.get("action")
    if job_action == "rubric.create" and payload.update.event == "result":
        try:
            rubric_result = RubricGenerateResponse.model_validate(normalized_update_payload["data"])
        except (KeyError, ValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rubric result payload must match RubricGenerateResponse schema",
            ) from exc
        normalized_update_payload = {"data": rubric_result.model_dump()}

    update = JobUpdate(
        job_id=job_id,
        event=payload.update.event,
        payload=normalized_update_payload,
    )
    await queue.publish_update(update)

    next_status = None
    if payload.status is not None:
        merged_details = dict(state.details)
        merged_details.update(payload.details)
        next_state = await queue.set_state(
            job_id=job_id,
            status=payload.status,
            details=merged_details,
        )
        next_status = next_state.status

    return JobUpdateResponse(job_id=job_id, accepted=True, status=next_status)


@router.get("/{job_id}/stream")
async def stream_job_updates(
    job_id: str,
    current_user: User = Depends(get_current_user),
    queue: JobQueue = Depends(get_job_queue),
):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    owner_user_id = state.details.get("owner_user_id")
    if owner_user_id and owner_user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user cannot stream this job",
        )

    async def event_stream():
        subscription = await queue.subscribe_updates(job_id)
        async with subscription:
            try:
                initial_state = await queue.get_state(job_id)
                if initial_state is not None and initial_state.status in TERMINAL_JOB_STATUSES:
                    end_data = json.dumps(
                        {
                            "job_id": job_id,
                            "status": initial_state.status,
                            "updated_at": initial_state.updated_at,
                        }
                    )
                    yield f"event: end\ndata: {end_data}\n\n"
                    return
                while True:
                    update = await subscription.get(timeout=15.0)
                    if update is None:
                        latest_state = await queue.get_state(job_id)
                        if latest_state is not None and latest_state.status in TERMINAL_JOB_STATUSES:
                            end_data = json.dumps(
                                {
                                    "job_id": job_id,
                                    "status": latest_state.status,
                                    "updated_at": latest_state.updated_at,
                                }
                            )
                            yield f"event: end\ndata: {end_data}\n\n"
                            return
                        yield ": keep-alive\n\n"
                        continue
                    data = json.dumps(asdict(update))
                    yield f"event: {update.event}\ndata: {data}\n\n"
                    latest_state = await queue.get_state(job_id)
                    if latest_state is not None and latest_state.status in TERMINAL_JOB_STATUSES:
                        end_data = json.dumps(
                            {
                                "job_id": job_id,
                                "status": latest_state.status,
                                "updated_at": latest_state.updated_at,
                            }
                        )
                        yield f"event: end\ndata: {end_data}\n\n"
                        return
            except asyncio.CancelledError:
                return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router", "get_job_queue"]
