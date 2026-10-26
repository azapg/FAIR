from uuid import uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.user import User, UserRole
from tests.conftest import get_auth_token


def _user(session, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}-{uuid4().hex[:6]}@test.com",
        role=role,
        password_hash=hash_password("test_password_123"),
        is_verified=True,
    )
    session.add(user)
    session.commit()
    return user


def _auth(client, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_auth_token(client, str(user.email))}"}


def test_course_post_comments_and_notification_inbox(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        student = _user(session, "Student", UserRole.student)
        outsider = _user(session, "Outsider", UserRole.student)
        course = Course(id=uuid4(), name="LMS", instructor_id=owner.id)
        session.add(course)
        session.flush()
        session.add(Enrollment(id=uuid4(), user_id=student.id, course_id=course.id))
        session.commit()

    created = test_client.post(
        f"/api/lms/courses/{course.id}/posts",
        json={
            "kind": "announcement",
            "title": "Welcome",
            "body": "Read the syllabus before Friday.",
        },
        headers=_auth(test_client, owner),
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    stream = test_client.get(
        f"/api/lms/courses/{course.id}/posts", headers=_auth(test_client, student)
    )
    assert stream.status_code == 200
    assert stream.json()[0]["title"] == "Welcome"
    assert test_client.get(
        f"/api/lms/courses/{course.id}/posts", headers=_auth(test_client, outsider)
    ).status_code == 403

    inbox = test_client.get(
        "/api/lms/notifications?unread_only=true", headers=_auth(test_client, student)
    )
    assert inbox.status_code == 200
    assert inbox.json()[0]["kind"] == "course_post"
    notification_id = inbox.json()[0]["id"]
    assert test_client.post(
        f"/api/lms/notifications/{notification_id}/read", headers=_auth(test_client, student)
    ).status_code == 200
    assert test_client.get(
        "/api/lms/notifications?unread_only=true", headers=_auth(test_client, student)
    ).json() == []

    comment = test_client.post(
        f"/api/lms/posts/{post_id}/comments",
        json={"body": "Will do!"},
        headers=_auth(test_client, student),
    )
    assert comment.status_code == 201
    comments = test_client.get(
        f"/api/lms/posts/{post_id}/comments", headers=_auth(test_client, owner)
    )
    assert comments.status_code == 200
    assert comments.json()[0]["authorName"] == "Student"
    owner_inbox = test_client.get(
        "/api/lms/notifications", headers=_auth(test_client, owner)
    ).json()
    assert owner_inbox[0]["kind"] == "course_comment"


def test_students_cannot_publish_or_comment_in_archived_course(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        student = _user(session, "Student", UserRole.student)
        course = Course(id=uuid4(), name="LMS", instructor_id=owner.id)
        session.add(course)
        session.flush()
        session.add(Enrollment(id=uuid4(), user_id=student.id, course_id=course.id))
        session.commit()

    post = test_client.post(
        f"/api/lms/courses/{course.id}/posts",
        json={"title": "Final notice"},
        headers=_auth(test_client, owner),
    ).json()
    test_client.post(f"/api/courses/{course.id}/archive", headers=_auth(test_client, owner))
    response = test_client.post(
        f"/api/lms/posts/{post['id']}/comments",
        json={"body": "Too late"},
        headers=_auth(test_client, student),
    )
    assert response.status_code == 400
