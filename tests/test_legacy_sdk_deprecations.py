from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import get_auth_token
from fair_platform.backend.data.models import (
    Course,
    User,
    UserRole,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)


def test_session_logs_endpoint_sets_legacy_deprecation_headers(
    test_client: TestClient,
    test_db,
):
    run_id = uuid4()
    with test_db() as db:
        user = User(
            id=uuid4(),
            name="Runner",
            email="runner-deprecation@test.com",
            role=UserRole.admin,
            password_hash="x",
        )
        course = Course(
            id=uuid4(),
            name="Deprecation course",
            description="desc",
            instructor_id=user.id,
        )
        workflow = Workflow(
            id=uuid4(),
            course_id=course.id,
            name="Deprecation workflow",
            description="desc",
            created_by=user.id,
            created_at=datetime.utcnow(),
        )
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow.id,
            run_by=user.id,
            status=WorkflowRunStatus.running,
            logs={"history": []},
        )
        db.add_all([user, course, workflow, run])
        db.commit()

    response = test_client.get(f"/api/sessions/{run_id}/logs")
    assert response.status_code == 200
    assert response.headers.get("deprecation") == "true"
    assert response.headers.get("sunset")
    assert response.headers.get("x-fair-deprecated-reason")


def test_plugins_endpoint_sets_legacy_deprecation_headers(
    test_client: TestClient,
    admin_user,
):
    token = get_auth_token(test_client, admin_user.email)
    response = test_client.get(
        "/api/plugins/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.headers.get("deprecation") == "true"
    assert response.headers.get("sunset")
    assert response.headers.get("x-fair-deprecated-reason")
