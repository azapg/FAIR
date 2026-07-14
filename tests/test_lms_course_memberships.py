from uuid import UUID, uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.user import User, UserRole
from tests.conftest import get_auth_token


def _user(session, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}-{uuid4().hex[:6]}@test.com",
        role=role,
        password_hash=hash_password("test_password_123"),
    )
    session.add(user)
    session.commit()
    return user


def _auth(client, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_auth_token(client, str(user.email))}"}


def _course(session, owner: User) -> Course:
    course = Course(id=uuid4(), name="LMS", instructor_id=owner.id)
    session.add(course)
    session.commit()
    return course


def test_course_creation_bootstraps_owner_membership(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)

    response = test_client.post(
        "/api/courses/",
        json={
            "name": "MVP Course",
            "description": "Core LMS",
            "instructor_id": str(owner.id),
            "section": "A",
            "term": "2026-2",
        },
        headers=_auth(test_client, owner),
    )

    assert response.status_code == 201
    assert response.json()["section"] == "A"
    assert response.json()["isArchived"] is False
    course_id = UUID(response.json()["id"])
    with test_db() as session:
        membership = session.query(Enrollment).filter_by(course_id=course_id).one()
        assert membership.user_id == owner.id
        assert membership.role == CourseMembershipRole.owner
        assert membership.status == EnrollmentStatus.active


def test_assistant_can_manage_students_but_not_assistants(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        assistant = _user(session, "Assistant", UserRole.instructor)
        student = _user(session, "Student", UserRole.student)
        other_assistant = _user(session, "OtherAssistant", UserRole.instructor)
        course = _course(session, owner)
        session.add(
            Enrollment(
                id=uuid4(),
                user_id=assistant.id,
                course_id=course.id,
                role=CourseMembershipRole.assistant,
            )
        )
        session.commit()

    student_response = test_client.post(
        "/api/enrollments/",
        json={"user_id": str(student.id), "course_id": str(course.id)},
        headers=_auth(test_client, assistant),
    )
    assert student_response.status_code == 201

    assistant_response = test_client.post(
        "/api/enrollments/",
        json={
            "user_id": str(other_assistant.id),
            "course_id": str(course.id),
            "role": "assistant",
        },
        headers=_auth(test_client, assistant),
    )
    assert assistant_response.status_code == 403


def test_removed_student_can_be_reactivated_without_duplicate_row(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        student = _user(session, "Student", UserRole.student)
        course = _course(session, owner)
        membership = Enrollment(id=uuid4(), user_id=student.id, course_id=course.id)
        session.add(membership)
        session.commit()
        membership_id = membership.id

    removed = test_client.delete(
        f"/api/enrollments/{membership_id}", headers=_auth(test_client, owner)
    )
    assert removed.status_code == 204
    reactivated = test_client.post(
        "/api/enrollments/",
        json={"user_id": str(student.id), "course_id": str(course.id)},
        headers=_auth(test_client, owner),
    )
    assert reactivated.status_code == 201
    assert reactivated.json()["id"] == str(membership_id)
    assert reactivated.json()["status"] == "active"


def test_owner_transfer_and_archive_lifecycle(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        next_owner = _user(session, "NextOwner", UserRole.instructor)
        course = _course(session, owner)

    transferred = test_client.put(
        f"/api/courses/{course.id}",
        json={"instructor_id": str(next_owner.id)},
        headers=_auth(test_client, owner),
    )
    assert transferred.status_code == 200
    with test_db() as session:
        memberships = {
            membership.user_id: membership.role
            for membership in session.query(Enrollment).filter_by(course_id=course.id)
        }
        assert memberships[owner.id] == CourseMembershipRole.assistant
        assert memberships[next_owner.id] == CourseMembershipRole.owner

    archived = test_client.post(
        f"/api/courses/{course.id}/archive", headers=_auth(test_client, next_owner)
    )
    assert archived.status_code == 200
    assert archived.json()["isArchived"] is True
    assert test_client.get(
        "/api/courses/", headers=_auth(test_client, next_owner)
    ).json() == []

    reopened = test_client.post(
        f"/api/courses/{course.id}/reopen", headers=_auth(test_client, next_owner)
    )
    assert reopened.status_code == 200
    assert reopened.json()["isArchived"] is False
