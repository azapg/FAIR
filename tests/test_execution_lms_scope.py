from __future__ import annotations

from uuid import uuid4

import pytest

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    Submitter,
    User,
    UserRole,
)
from fair_platform.backend.main import app
from fair_platform.backend.services.execution_store import (
    ExecutionStoreError,
    create_execution,
)


def _user(*, role: UserRole = UserRole.instructor) -> User:
    identifier = uuid4()
    return User(
        id=identifier,
        name="Execution Scope User",
        email=f"{identifier}@example.test",
        role=role,
        is_verified=True,
        settings={},
    )


def _course_assignment_submission(session, *, instructor: User, suffix: str):
    course = Course(
        id=uuid4(),
        name=f"Course {suffix}",
        instructor_id=instructor.id,
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title=f"Assignment {suffix}",
        max_grade={"value": 100},
    )
    submitter = Submitter(
        id=uuid4(),
        name=f"Student {suffix}",
        is_synthetic=True,
    )
    submission = Submission(
        id=uuid4(),
        assignment_id=assignment.id,
        submitter_id=submitter.id,
        created_by_id=instructor.id,
    )
    session.add_all([course, assignment, submitter, submission])
    session.flush()
    return course, assignment, submission


def test_execution_infers_typed_scope_from_submissions(test_db):
    with test_db() as session:
        instructor = _user()
        session.add(instructor)
        session.flush()
        course, assignment, submission = _course_assignment_submission(
            session,
            instructor=instructor,
            suffix="A",
        )

        execution = create_execution(
            session,
            kind="flow",
            initiated_by_user_id=instructor.id,
            submission_ids=[submission.id],
        )
        session.commit()

        assert execution.course_id == course.id
        assert execution.assignment_id == assignment.id
        assert [item.id for item in execution.submissions] == [submission.id]


def test_execution_rejects_submissions_from_multiple_assignments(test_db):
    with test_db() as session:
        instructor = _user()
        session.add(instructor)
        session.flush()
        _, _, first = _course_assignment_submission(
            session,
            instructor=instructor,
            suffix="A",
        )
        _, _, second = _course_assignment_submission(
            session,
            instructor=instructor,
            suffix="B",
        )

        with pytest.raises(
            ExecutionStoreError,
            match="multiple assignments",
        ):
            create_execution(
                session,
                kind="flow",
                initiated_by_user_id=instructor.id,
                submission_ids=[first.id, second.id],
            )


def test_child_execution_inherits_root_lms_scope(test_db):
    with test_db() as session:
        instructor = _user()
        session.add(instructor)
        session.flush()
        course, assignment, submission = _course_assignment_submission(
            session,
            instructor=instructor,
            suffix="A",
        )
        root = create_execution(
            session,
            kind="flow",
            initiated_by_user_id=instructor.id,
            submission_ids=[submission.id],
        )
        child = create_execution(
            session,
            kind="flow_step",
            parent_execution_id=root.id,
        )

        assert child.root_execution_id == root.id
        assert child.course_id == course.id
        assert child.assignment_id == assignment.id
        assert [item.id for item in child.submissions] == [submission.id]


def test_execution_list_filters_by_typed_scope_and_course_owner(
    test_client,
    test_db,
):
    with test_db() as session:
        instructor = _user()
        other_instructor = _user()
        session.add_all([instructor, other_instructor])
        session.flush()
        course, _, submission = _course_assignment_submission(
            session,
            instructor=instructor,
            suffix="owned",
        )
        other_course, _, other_submission = _course_assignment_submission(
            session,
            instructor=other_instructor,
            suffix="other",
        )
        owned_execution = create_execution(
            session,
            kind="flow",
            initiated_by_user_id=None,
            submission_ids=[submission.id],
        )
        create_execution(
            session,
            kind="flow",
            initiated_by_user_id=None,
            submission_ids=[other_submission.id],
        )
        session.commit()

    app.dependency_overrides[get_current_user] = lambda: instructor
    try:
        response = test_client.get(
            "/api/v1/executions",
            params={"course_id": str(course.id), "submission_id": str(submission.id)},
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [str(owned_execution.id)]

        forbidden_scope = test_client.get(
            "/api/v1/executions",
            params={"course_id": str(other_course.id)},
        )
        assert forbidden_scope.status_code == 200
        assert forbidden_scope.json() == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)
