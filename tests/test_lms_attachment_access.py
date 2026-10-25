"""Exercise the real HTTP auth and storage boundaries with disposable LMS data."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from jose import jwt

from fair_platform.backend.api.routers.auth import (
    ACTION_TOKEN_TYPE,
    ALGORITHM,
    EXTENSION_JOB_TOKEN_TYPE,
    SECRET_KEY,
    USER_SESSION_TOKEN_TYPE,
    create_extension_job_token,
    hash_password,
)
from fair_platform.backend.data.models import Assignment, Course, User
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.storage import storage
from tests.conftest import get_auth_token


@pytest.fixture
def attachment_course(test_db, professor_user, student_user, monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "data_dir", tmp_path)
    with test_db() as db:
        assistant = User(
            id=uuid4(),
            name="Assistant",
            email="assistant@test.com",
            role="user",
            password_hash=hash_password("test_password_123"),
            is_verified=True,
        )
        other = User(
            id=uuid4(),
            name="Other learner",
            email="other@test.com",
            role="user",
            password_hash=hash_password("test_password_123"),
            is_verified=True,
        )
        course = Course(
            id=uuid4(), name="Attachment access", instructor_id=professor_user.id
        )
        db.add_all([assistant, other, course])
        db.flush()
        for user, role in [
            (student_user, "student"),
            (assistant, "assistant"),
            (other, "student"),
        ]:
            db.add(
                Enrollment(id=uuid4(), course_id=course.id, user_id=user.id, role=role)
            )
        db.commit()
        return course, assistant, other


def _login(client, user):
    # Deliberately use the HttpOnly cookie set by login, with no bearer header.
    get_auth_token(client, user.email)


def _assignment(client, course, owner, name="exam.txt"):
    _login(client, owner)
    response = client.post(
        "/api/assignments/",
        data={
            "course_id": str(course.id),
            "title": name,
            "max_grade": '{"type":"points","value":100}',
        },
        files={"files": (name, b"Disposable assignment content", "text/plain")},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    artifacts = client.get("/api/v1/artifacts", params={"assignment_id": data["id"]})
    assert artifacts.status_code == 200
    return UUID(data["id"]), UUID(artifacts.json()[0]["id"])


def _status(test_db, assignment_id, status):
    with test_db() as db:
        db.get(Assignment, assignment_id).status = status
        db.commit()


def _file_paths(test_db, artifact_id):
    with test_db() as db:
        artifact = db.get(Artifact, artifact_id)
        derivative = artifact.original_derivative
        return (
            f"/api/v1/artifacts/{artifact_id}",
            f"/api/v1/artifacts/{artifact_id}/download",
            f"/api/v1/artifacts/{artifact_id}/derivatives/{derivative.id}/download",
            f"/api/v1/artifact-storage/local/{derivative.storage_path}",
        )


def _assert_file_access(client, test_db, artifact_id, expected, content):
    metadata, download, derivative, local = _file_paths(test_db, artifact_id)
    for path in (metadata, download, derivative, local):
        response = client.get(path, headers={"Accept": "application/json"})
        assert response.status_code == expected, (path, response.text)
        if expected == 200 and path in (download, derivative):
            file_response = client.get(response.json()["url"])
            assert file_response.status_code == 200
            assert file_response.content == content
    # Also exercise the redirect-following download, not just URL generation.
    response = client.get(download)
    assert response.status_code == expected
    if expected == 200:
        assert response.content == content


@pytest.mark.parametrize("assignment_status", ["draft", "published", "closed"])
def test_assignment_attachment_visibility_every_boundary(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
    assignment_status,
):
    course, assistant, other = attachment_course
    assignment_id, artifact_id = _assignment(test_client, course, professor_user)
    _status(test_db, assignment_id, assignment_status)
    for user in (professor_user, assistant, student_user, other):
        _login(test_client, user)
        allowed = user in (professor_user, assistant) or assignment_status != "draft"
        for params in (
            {},
            {"course_id": str(course.id)},
            {"assignment_id": str(assignment_id)},
        ):
            response = test_client.get("/api/v1/artifacts", params=params)
            assert response.status_code == 200
            assert (str(artifact_id) in {a["id"] for a in response.json()}) == allowed
        _assert_file_access(
            test_client,
            test_db,
            artifact_id,
            200 if allowed else 403,
            b"Disposable assignment content",
        )


def test_cookie_only_course_resource_download(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
):
    course, _, _ = attachment_course
    _, artifact_id = _assignment(test_client, course, professor_user, "resource.txt")
    with test_db() as db:
        artifact = db.get(Artifact, artifact_id)
        artifact.assignments.clear()
        artifact.assignment_id = None
        artifact.access_level = "course"
        db.commit()
    _login(test_client, student_user)
    _assert_file_access(
        test_client, test_db, artifact_id, 200, b"Disposable assignment content"
    )
    assert not test_client.headers.get("Authorization")


def test_shared_assignment_file_uses_a_readable_link_in_its_actual_course(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
):
    course, _, _ = attachment_course
    published_id, artifact_id = _assignment(test_client, course, professor_user)
    _status(test_db, published_id, "published")
    with test_db() as db:
        other_course = Course(
            id=uuid4(), name="Unrelated course", instructor_id=professor_user.id
        )
        draft = Assignment(
            id=uuid4(),
            course=other_course,
            title="Draft",
            status="draft",
            max_grade={"type": "points", "value": 100},
        )
        db.add_all([other_course, draft])
        db.flush()
        artifact = db.get(Artifact, artifact_id)
        artifact.assignments.append(draft)
        # attach_to_assignment updates these hints to the most recent link.
        artifact.assignment_id = draft.id
        artifact.course_id = other_course.id
        db.commit()
        draft_id = draft.id
    _login(test_client, student_user)
    _assert_file_access(
        test_client, test_db, artifact_id, 200, b"Disposable assignment content"
    )
    for params in ({"course_id": str(course.id)}, {"assignment_id": str(published_id)}):
        response = test_client.get("/api/v1/artifacts", params=params)
        assert response.status_code == 200
        assert str(artifact_id) in {a["id"] for a in response.json()}
    # A published link in a course the learner cannot read grants no access.
    _status(test_db, published_id, "draft")
    _status(test_db, draft_id, "published")
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")


def test_direct_assignment_scope_without_join_link_still_checks_publication(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
):
    course, _, _ = attachment_course
    assignment_id, artifact_id = _assignment(test_client, course, professor_user)
    with test_db() as db:
        artifact = db.get(Artifact, artifact_id)
        artifact.assignments.clear()
        db.commit()
    _login(test_client, student_user)
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")
    _status(test_db, assignment_id, "published")
    _assert_file_access(
        test_client, test_db, artifact_id, 200, b"Disposable assignment content"
    )
    with test_db() as db:
        db.get(Artifact, artifact_id).assignment_id = None
        db.commit()
    # A course hint with no assignment association cannot grant access.
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")


@pytest.mark.parametrize("access_level", ["private", "course", "public"])
def test_draft_link_preserves_explicit_file_sharing_policy(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
    access_level,
):
    course, assistant, _ = attachment_course
    assignment_id, artifact_id = _assignment(test_client, course, professor_user)
    with test_db() as db:
        db.get(Artifact, artifact_id).access_level = access_level
        db.commit()
    _login(test_client, student_user)
    expected = 403 if access_level == "private" else 200
    _assert_file_access(
        test_client, test_db, artifact_id, expected, b"Disposable assignment content"
    )
    _status(test_db, assignment_id, "published")
    # Linking a private file does not silently make it an assignment resource.
    _assert_file_access(
        test_client, test_db, artifact_id, expected, b"Disposable assignment content"
    )
    if access_level == "private":
        _login(test_client, assistant)
        _assert_file_access(test_client, test_db, artifact_id, 403, b"")


def test_submission_attachment_staff_access_uses_actual_submission(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
):
    course, assistant, other = attachment_course
    assignment_id, _ = _assignment(test_client, course, professor_user)
    _status(test_db, assignment_id, "published")
    _login(test_client, student_user)
    response = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment_id)},
        files={"files": ("answer.txt", b"Private student answer", "text/plain")},
    )
    assert response.status_code == 201, response.text
    submission_id = response.json()["id"]
    artifact_id = UUID(response.json()["artifacts"][0]["id"])
    # Even missing scope hints must not break staff access through the submission.
    with test_db() as db:
        artifact = db.get(Artifact, artifact_id)
        artifact.course_id = None
        artifact.assignment_id = None
        db.commit()
    for user in (professor_user, assistant, student_user):
        _login(test_client, user)
        assert test_client.get(f"/api/submissions/{submission_id}").status_code == 200
        _assert_file_access(
            test_client, test_db, artifact_id, 200, b"Private student answer"
        )
    _login(test_client, other)
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")
    with test_db() as db:
        membership = (
            db.query(Enrollment)
            .filter_by(course_id=course.id, user_id=assistant.id)
            .one()
        )
        membership.status = "removed"
        db.commit()
    _login(test_client, assistant)
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")
    # Being an assistant somewhere else is insufficient.
    with test_db() as db:
        unrelated = Course(id=uuid4(), name="Other", instructor_id=professor_user.id)
        db.add(unrelated)
        db.flush()
        db.add(
            Enrollment(
                id=uuid4(),
                course_id=unrelated.id,
                user_id=assistant.id,
                role="assistant",
            )
        )
        db.commit()
    _assert_file_access(test_client, test_db, artifact_id, 403, b"")


@pytest.mark.parametrize("transport", ["cookie", "bearer"])
@pytest.mark.parametrize(
    "token_case",
    [
        "invalid",
        "expired",
        "password_reset",
        "verify_email",
        "wrong_type",
        "session_with_purpose",
        "incomplete_delegation",
        "delegation",
    ],
)
def test_download_token_restrictions(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    transport,
    token_case,
):
    course, _, _ = attachment_course
    _, artifact_id = _assignment(test_client, course, professor_user)
    payload = {
        "sub": str(professor_user.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token_type = USER_SESSION_TOKEN_TYPE
    if token_case == "expired":
        payload["exp"] = datetime.now(timezone.utc) - timedelta(hours=1)
    elif token_case in ("password_reset", "verify_email"):
        payload["purpose"] = token_case
        token_type = ACTION_TOKEN_TYPE
    elif token_case == "wrong_type":
        token_type = "JWT"
    elif token_case == "session_with_purpose":
        payload["purpose"] = "password_reset"
    elif token_case == "incomplete_delegation":
        payload["purpose"] = "ext_job"
        token_type = EXTENSION_JOB_TOKEN_TYPE
    token = jwt.encode(
        payload, SECRET_KEY, algorithm=ALGORITHM, headers={"typ": token_type}
    )
    if token_case == "invalid":
        token = "invalid-token"
    elif token_case == "delegation":
        token = create_extension_job_token(
            user_id=str(professor_user.id), job_id=str(uuid4()), extension_id="test"
        )
    # Keep a valid login cookie for bearer cases to verify invalid explicit
    # credentials cannot silently fall back to the ambient session.
    headers = {"Accept": "application/json"}
    if transport == "cookie":
        test_client.cookies.clear()
        test_client.cookies.set("fair_session", token, path="/api")
    else:
        headers["Authorization"] = f"Bearer {token}"
    response = test_client.get(
        f"/api/v1/artifacts/{artifact_id}/download", headers=headers
    )
    assert response.status_code == (
        200 if token_case == "delegation" and transport == "bearer" else 401
    )
    if token_case == "delegation" and transport == "bearer":
        # Delegation remains download-only; it is not a normal session.
        assert (
            test_client.get(
                f"/api/v1/artifacts/{artifact_id}", headers=headers
            ).status_code
            == 401
        )


def test_delegated_download_does_not_bypass_draft_authorization(
    test_client,
    test_db,
    attachment_course,
    professor_user,
    student_user,
):
    course, _, _ = attachment_course
    _, artifact_id = _assignment(test_client, course, professor_user)
    token = create_extension_job_token(
        user_id=str(student_user.id), job_id=str(uuid4()), extension_id="test"
    )
    response = test_client.get(
        f"/api/v1/artifacts/{artifact_id}/download",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    assert response.status_code == 403
