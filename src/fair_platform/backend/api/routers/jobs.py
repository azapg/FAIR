import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from fair_platform.backend.api.schema.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobStateRead,
    JobUpdateRequest,
    JobUpdateResponse,
)
from fair_platform.backend.services.job_queue import (
    JobMessage,
    JobQueue,
    JobStatus,
    JobUpdate,
    create_job_queue,
)

router = APIRouter()


async def get_job_queue(request: Request) -> JobQueue:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        queue = await create_job_queue()
        request.app.state.job_queue = queue
    return queue


@router.post("/", status_code=status.HTTP_202_ACCEPTED, response_model=JobCreateResponse)
async def create_job(
    payload: JobCreateRequest,
    queue: JobQueue = Depends(get_job_queue),
):
    # TODO(auth): enforce extension/action authorization before enqueueing jobs.
    # This should validate actor permissions against the target extension and
    # requested action once extension auth/policies are introduced.
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
        payload=payload.payload,
        metadata=payload.metadata,
    )
    await queue.enqueue(job)
    return JobCreateResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/{job_id}", response_model=JobStateRead)
async def get_job_state(job_id: str, queue: JobQueue = Depends(get_job_queue)):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
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
    queue: JobQueue = Depends(get_job_queue),
):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    update = JobUpdate(
        job_id=job_id,
        event=payload.event,
        payload=payload.payload,
    )
    await queue.publish_update(update)

    next_status = None
    if payload.status is not None:
        next_state = await queue.set_state(
            job_id=job_id,
            status=payload.status,
            details=payload.details,
        )
        next_status = next_state.status

    return JobUpdateResponse(job_id=job_id, accepted=True, status=next_status)


@router.get("/{job_id}/stream")
async def stream_job_updates(job_id: str, queue: JobQueue = Depends(get_job_queue)):
    state = await queue.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    async def event_stream():
        subscription = await queue.subscribe_updates(job_id)
        async with subscription:
            try:
                while True:
                    update = await subscription.get(timeout=15.0)
                    if update is None:
                        yield ": keep-alive\n\n"
                        continue
                    data = json.dumps(asdict(update))
                    yield f"event: {update.event}\ndata: {data}\n\n"
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
