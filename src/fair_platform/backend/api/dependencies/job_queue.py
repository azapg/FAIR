from fastapi import Request

from fair_platform.backend.services.job_queue import JobQueue, create_job_queue


async def get_job_queue(request: Request) -> JobQueue:
    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        queue = await create_job_queue()
        request.app.state.job_queue = queue
    return queue


__all__ = ["get_job_queue"]
