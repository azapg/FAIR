import asyncio
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

import fair_platform.backend.services.session_manager as session_manager_module
from fair_platform.backend.services.session_manager import Session
from fair_platform.backend.data.models import (
    Course,
    User,
    UserRole,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)


def test_session_bus_captures_file_events(monkeypatch):
    class _FakeDb:
        def get(self, *_args, **_kwargs):
            return None

    @contextmanager
    def _fake_get_session():
        yield _FakeDb()

    monkeypatch.setattr(session_manager_module, "get_session", _fake_get_session)

    session = Session(session_id=uuid4(), task=None)

    payload = {
        "level": "info",
        "payload": {
            "description": "Prompt",
            "file": {
                "name": "prompt.md",
                "content": "# Prompt",
                "file_type": "markdown",
                "mime_type": "text/markdown",
                "encoding": "utf-8",
                "size_bytes": 8,
            },
        },
    }
    asyncio.run(session.bus.emit("file", payload))

    assert len(session.buffer) == 1
    entry = session.buffer[0]
    assert entry["type"] == "file"
    assert entry["payload"]["file"]["name"] == "prompt.md"


def test_get_session_logs_returns_file_entries_from_persisted_history(
    test_client: TestClient,
    test_db,
):
    run_id = uuid4()
    with test_db() as db:
        user = User(
            id=uuid4(),
            name="Runner",
            email="runner-logs@test.com",
            role=UserRole.admin,
            password_hash="x",
        )
        course = Course(
            id=uuid4(),
            name="Logs course",
            description="desc",
            instructor_id=user.id,
        )
        workflow = Workflow(
            id=uuid4(),
            course_id=course.id,
            name="Logs workflow",
            description="desc",
            created_by=user.id,
            created_at=datetime.utcnow(),
        )
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow.id,
            run_by=user.id,
            status=WorkflowRunStatus.running,
            logs={
                "history": [
                    {
                        "index": 0,
                        "ts": datetime.utcnow().isoformat(),
                        "type": "file",
                        "level": "info",
                        "payload": {
                            "description": "Prompt",
                            "file": {
                                "name": "prompt.md",
                                "content": "# Prompt",
                                "file_type": "markdown",
                                "mime_type": "text/markdown",
                                "encoding": "utf-8",
                                "size_bytes": 8,
                            },
                        },
                    }
                ]
            },
        )
        db.add_all([user, course, workflow, run])
        db.commit()

    response = test_client.get(f"/api/sessions/{run_id}/logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["type"] == "file"
    assert logs[0]["payload"]["file"]["name"] == "prompt.md"
