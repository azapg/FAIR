from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from fair_platform.backend.api.schema.course_copy import CourseCopyRequest
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.flow import Flow, FlowVersion
from fair_platform.backend.data.models.lms_content import CourseItem, CourseSection
from fair_platform.backend.data.models.lms_course_copy import CourseCopyJob
from fair_platform.backend.data.models.lms_gradebook import GradeCategory, GradeItem
from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.services import course_copy
from fair_platform.backend.services.course_copy import (
    CourseCopyConflict,
    _without_secrets,
    create_or_resume_job,
    execute,
    preview,
)
from fair_platform.backend.services.flow_service import flow_version_hash
from tests.conftest import get_auth_token


def _request(*, name: str = "Copied course", key: str = "copy-key-123"):
    return CourseCopyRequest(
        name=name,
        datePolicy="shift",
        dateShiftDays=7,
        idempotencyKey=key,
    )


def test_course_copy_deep_copies_authoring_graph_and_excludes_learners(
    test_db, professor_user, student_user
) -> None:
    with test_db() as db:
        source = Course(
            id=uuid4(),
            name="Source",
            instructor_id=professor_user.id,
            enrollment_code="PRIVATE-CODE",
            icon_key="chemistry",
        )
        rubric = Rubric(
            id=uuid4(),
            name="Essay rubric",
            created_by_id=professor_user.id,
            content={"criteria": [], "levels": []},
        )
        assignment = Assignment(
            id=uuid4(),
            course_id=source.id,
            title="Essay",
            max_grade={"type": "points", "value": 20},
            rubric_id=rubric.id,
            status="published",
        )
        section = CourseSection(
            id=uuid4(), course_id=source.id, title="Week 1", position=0
        )
        category = GradeCategory(
            id=uuid4(), course_id=source.id, name="Work", position=0
        )
        grade_item = GradeItem(
            id=uuid4(),
            course_id=source.id,
            category_id=category.id,
            title="Essay",
            position=0,
            max_points=20,
            source_type="assignment",
            source_id=assignment.id,
        )
        flow = Flow(
            id=uuid4(),
            owner_user_id=professor_user.id,
            course_id=source.id,
            name="Feedback flow",
        )
        version = FlowVersion(
            id=uuid4(),
            flow_id=flow.id,
            ordinal=1,
            state="published",
            definition={
                "courseId": str(source.id),
                "assignmentId": str(assignment.id),
                "assignmentUrl": f"https://fair.test/assignments/{assignment.id}",
                "Authorization": "Bearer no",
            },
            capability_pins=[],
            config_snapshot={"clientSecretValue": "no", "safe": True},
            created_by_user_id=professor_user.id,
        )
        db.add_all([source, rubric, assignment, section, category, grade_item, flow])
        db.flush()
        db.add_all(
            [
                version,
                Enrollment(id=uuid4(), course_id=source.id, user_id=student_user.id),
                CourseItem(
                    id=uuid4(),
                    course_id=source.id,
                    section_id=section.id,
                    title="Essay",
                    position=0,
                    kind="assignment",
                    resource_type="assignment",
                    resource_id=assignment.id,
                ),
            ]
        )
        db.commit()

        copy_preview = preview(db, source, _request())
        assert copy_preview["copied"]["rubrics"] == 1
        assert copy_preview["skipped"]["enrollments"] == 1
        assert any(
            item["object_type"] == "assignment" for item in copy_preview["objects"]
        )

        job = execute(db, source, professor_user.id, _request())
        assert job.status == "completed"
        destination_id = job.destination_course_id
        assert destination_id and destination_id != source.id

        destination = db.get(Course, destination_id)
        assert destination.copied_from_id == source.id
        assert destination.enrollment_code is None
        assert destination.is_enrollment_enabled is False
        assert destination.icon_key == "chemistry"
        memberships = db.query(Enrollment).filter_by(course_id=destination_id).all()
        assert [(row.user_id, str(row.role)) for row in memberships] == [
            (professor_user.id, "owner")
        ]

        copied_assignment = (
            db.query(Assignment).filter_by(course_id=destination_id).one()
        )
        assert copied_assignment.status == "draft"
        assert copied_assignment.id != assignment.id
        assert copied_assignment.rubric_id != rubric.id
        copied_grade_item = (
            db.query(GradeItem).filter_by(course_id=destination_id).one()
        )
        assert copied_grade_item.source_id == copied_assignment.id

        copied_flow = db.query(Flow).filter_by(course_id=destination_id).one()
        copied_version = copied_flow.versions[0]
        assert copied_version.state == "draft"
        assert copied_version.definition == {
            "courseId": str(destination_id),
            "assignmentId": str(copied_assignment.id),
            "assignmentUrl": (f"https://fair.test/assignments/{copied_assignment.id}"),
        }
        assert copied_version.config_snapshot == {"safe": True}
        assert copied_version.definition_hash == flow_version_hash(
            copied_version.definition,
            copied_version.capability_pins,
            copied_version.config_snapshot,
        )

        repeated = execute(db, source, professor_user.id, _request())
        assert repeated.destination_course_id == destination_id
        assert db.query(Course).filter_by(copied_from_id=source.id).count() == 1
        with pytest.raises(CourseCopyConflict):
            execute(db, source, professor_user.id, _request(name="Changed"))


def test_failed_course_copy_rolls_back_and_same_key_retries(
    test_db, professor_user, monkeypatch
) -> None:
    with test_db() as db:
        source = Course(id=uuid4(), name="Source", instructor_id=professor_user.id)
        db.add(source)
        db.commit()
        original = course_copy._copy_graph

        def fail(*_args, **_kwargs):
            raise RuntimeError("injected copy failure")

        monkeypatch.setattr(course_copy, "_copy_graph", fail)
        failed = execute(db, source, professor_user.id, _request(key="retry-key-123"))
        assert failed.status == "failed"
        assert failed.destination_course_id is None
        assert db.query(Course).filter_by(copied_from_id=source.id).count() == 0

        monkeypatch.setattr(course_copy, "_copy_graph", original)
        retried = execute(db, source, professor_user.id, _request(key="retry-key-123"))
        assert retried.status == "completed"
        assert retried.destination_course_id is not None


def test_course_copy_api_is_staff_only(
    test_client, test_db, professor_user, student_user
) -> None:
    with test_db() as db:
        source = Course(id=uuid4(), name="Source", instructor_id=professor_user.id)
        db.add(source)
        db.commit()
    payload = _request().model_dump(mode="json", by_alias=True)
    owner_headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, professor_user.email)}"
    }
    student_headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"
    }
    assert (
        test_client.post(
            f"/api/lms/courses/{source.id}/copy-preview",
            json=payload,
            headers=owner_headers,
        ).status_code
        == 200
    )
    assert (
        test_client.post(
            f"/api/lms/courses/{source.id}/copy-preview",
            json=payload,
            headers=student_headers,
        ).status_code
        == 403
    )


def test_course_copy_strips_secret_configuration_recursively() -> None:
    copied = _without_secrets(
        {
            "safe": {"token": "nope", "keep": 1},
            "items": [
                {
                    "password": "nope",
                    "Authorization": "Bearer nope",
                    "accessKey": "nope",
                    "title": "ok",
                }
            ],
            "headers": {
                "X-Api-Key": "nope",
                "Cookie": "session=nope",
                "X-Trace-Id": "keep",
            },
            "requestHeaders": {
                "X-Custom-Auth": "nope",
                "Accept": "application/json",
            },
            "authentication": {"scheme": "basic", "value": "nope"},
            "environment": {"OPENAI_API_KEY": "nope", "SAFE_MODE": "yes"},
            "connectionString": "postgresql://user:password@example.test/db",
        }
    )
    assert copied == {
        "safe": {"keep": 1},
        "items": [{"title": "ok"}],
        "headers": {"X-Trace-Id": "keep"},
        "requestHeaders": {"Accept": "application/json"},
        "environment": {"SAFE_MODE": "yes"},
    }


def test_course_copy_strips_secrets_from_list_style_headers() -> None:
    copied = _without_secrets(
        {
            "nodes": [
                {
                    "config": {
                        "headers": [
                            {"name": "Authorization", "value": "Bearer nope"},
                            {"key": "Cookie", "value": "session=nope"},
                            ["Proxy-Authorization", "Basic nope"],
                            ["X-Api-Key", "nope"],
                            {"name": "Accept", "value": "application/json"},
                            ["X-Trace-Id", "keep"],
                        ]
                    }
                }
            ],
            "headers": ["Authorization", "Bearer nope"],
        }
    )

    assert copied == {
        "nodes": [
            {
                "config": {
                    "headers": [
                        {"name": "Accept", "value": "application/json"},
                        ["X-Trace-Id", "keep"],
                    ]
                }
            }
        ],
        "headers": [],
    }


def test_course_copy_preserves_token_metrics_but_strips_credentials() -> None:
    copied = _without_secrets(
        {
            "maxTokens": 4096,
            "min_tokens": 32,
            "tokenizer": "cl100k_base",
            "tokenCount": 17,
            "inputTokens": 12,
            "completion_tokens": 5,
            "tokensUsed": 17,
            "authToken": "nope",
            "access_token": "nope",
            "refreshToken": "nope",
            "githubToken": "nope",
            "token": "nope",
        }
    )

    assert copied == {
        "maxTokens": 4096,
        "min_tokens": 32,
        "tokenizer": "cl100k_base",
        "tokenCount": 17,
        "inputTokens": 12,
        "completion_tokens": 5,
        "tokensUsed": 17,
    }


def test_course_copy_rejects_unmapped_source_course_flow_references(
    test_client, test_db, professor_user
) -> None:
    with test_db() as db:
        source = Course(id=uuid4(), name="Source", instructor_id=professor_user.id)
        assignment = Assignment(
            id=uuid4(),
            course_id=source.id,
            title="Source-only assignment",
            max_grade={"type": "points", "value": 10},
            status="draft",
        )
        section = CourseSection(
            id=uuid4(), course_id=source.id, title="Source-only section", position=0
        )
        resource = CourseItem(
            id=uuid4(),
            course_id=source.id,
            section_id=section.id,
            title="Source-only resource",
            position=0,
            kind="assignment",
            resource_type="assignment",
            resource_id=assignment.id,
        )
        flow = Flow(
            id=uuid4(),
            owner_user_id=professor_user.id,
            course_id=source.id,
            name="Unsafe partial flow",
        )
        version = FlowVersion(
            id=uuid4(),
            flow_id=flow.id,
            ordinal=1,
            state="draft",
            definition={"assignmentId": str(assignment.id).upper()},
            capability_pins=[],
            config_snapshot={"courseItemId": str(resource.id)},
            created_by_user_id=professor_user.id,
        )
        db.add_all([source, assignment, section, resource, flow])
        db.flush()
        db.add(version)
        db.commit()
        request = CourseCopyRequest(
            name="Flows only",
            idempotencyKey="unsafe-flow-copy",
            selection={
                "content": False,
                "assignments": False,
                "rubrics": False,
                "gradebook": False,
                "quizzes": False,
                "flows": True,
            },
        )

        with pytest.raises(CourseCopyConflict, match="source-course resources"):
            preview(db, source, request)
        response = test_client.post(
            f"/api/lms/courses/{source.id}/copy-preview",
            json=request.model_dump(mode="json", by_alias=True),
            headers={
                "Authorization": (
                    f"Bearer {get_auth_token(test_client, professor_user.email)}"
                )
            },
        )
        assert response.status_code == 409
        assert "source-course resources" in response.json()["detail"]
        with pytest.raises(CourseCopyConflict, match="source-course resources"):
            execute(db, source, professor_user.id, request)
        assert db.query(CourseCopyJob).count() == 0
        assert db.query(Course).filter_by(copied_from_id=source.id).count() == 0


@pytest.mark.parametrize("has_expired_lease", [False, True])
def test_stale_course_copy_job_is_reclaimed_but_live_lease_is_not(
    test_db, professor_user, has_expired_lease: bool
) -> None:
    with test_db() as db:
        source = Course(id=uuid4(), name="Source", instructor_id=professor_user.id)
        db.add(source)
        db.commit()

        stale_request = _request(key="stale-copy-key")
        stale = create_or_resume_job(db, source, professor_user.id, stale_request)
        stale.status = "running"
        if has_expired_lease:
            stale.lease_token = uuid4()
            stale.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

        recovered = execute(db, source, professor_user.id, stale_request)
        assert recovered.status == "completed"
        assert recovered.destination_course_id is not None
        assert recovered.lease_token is None
        assert recovered.lease_expires_at is None

        live_request = _request(name="Live copy", key="live-copy-key")
        live = create_or_resume_job(db, source, professor_user.id, live_request)
        live.status = "running"
        live.lease_token = uuid4()
        live.lease_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        live_token = live.lease_token
        db.commit()

        unchanged = execute(db, source, professor_user.id, live_request)
        assert unchanged.id == live.id
        assert unchanged.status == "running"
        assert unchanged.lease_token == live_token
        assert unchanged.destination_course_id is None
        assert db.query(Course).filter_by(copied_from_id=source.id).count() == 1
