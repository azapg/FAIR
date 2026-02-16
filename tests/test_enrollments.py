"""
Tests for enrollment feature — CRUD API, course/assignment visibility for enrolled students,
and artifact permission checks based on enrollment.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.api.routers.auth import hash_password
from tests.conftest import get_auth_token


# ──────────────────────────── helpers ────────────────────────────

def _make_users(session):
    """Create admin, professor and two students."""
    admin = User(id=uuid4(), name="Admin", email="admin@test.com",
                 role=UserRole.admin, password_hash=hash_password("test_password_123"))
    prof = User(id=uuid4(), name="Professor", email="prof@test.com",
                role=UserRole.professor, password_hash=hash_password("test_password_123"))
    stu1 = User(id=uuid4(), name="Student One", email="stu1@test.com",
                role=UserRole.student, password_hash=hash_password("test_password_123"))
    stu2 = User(id=uuid4(), name="Student Two", email="stu2@test.com",
                role=UserRole.student, password_hash=hash_password("test_password_123"))
    session.add_all([admin, prof, stu1, stu2])
    session.commit()
    return admin, prof, stu1, stu2


def _make_course(session, prof):
    course = Course(id=uuid4(), name="Test Course", description="desc", instructor_id=prof.id)
    session.add(course)
    session.commit()
    return course


def _make_course_with_code(session, prof, code="ABCD", enabled=True):
    course = Course(
        id=uuid4(),
        name="Test Course",
        description="desc",
        instructor_id=prof.id,
        enrollment_code=code,
        is_enrollment_enabled=enabled,
    )
    session.add(course)
    session.commit()
    return course


def _auth(client, email):
    return {"Authorization": f"Bearer {get_auth_token(client, email)}"}


# ──────────────── Enrollment CRUD Tests ────────────────────────


class TestEnrollmentCRUD:

    def test_instructor_can_enroll_student(self, test_client, test_db):
        with test_db() as s:
            admin, prof, stu1, _ = _make_users(s)
            course = _make_course(s, prof)

        headers = _auth(test_client, prof.email)
        resp = test_client.post("/api/enrollments/", json={
            "user_id": str(stu1.id), "course_id": str(course.id)
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["userId"] == str(stu1.id)
        assert data["courseId"] == str(course.id)
        assert data["userName"] == "Student One"

    def test_admin_can_enroll_student(self, test_client, test_db):
        with test_db() as s:
            admin, prof, stu1, _ = _make_users(s)
            course = _make_course(s, prof)

        headers = _auth(test_client, admin.email)
        resp = test_client.post("/api/enrollments/", json={
            "user_id": str(stu1.id), "course_id": str(course.id)
        }, headers=headers)
        assert resp.status_code == 201

    def test_student_cannot_enroll_themselves(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            course = _make_course(s, prof)

        headers = _auth(test_client, stu1.email)
        resp = test_client.post("/api/enrollments/", json={
            "user_id": str(stu1.id), "course_id": str(course.id)
        }, headers=headers)
        assert resp.status_code == 403

    def test_duplicate_enrollment_rejected(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            course = _make_course(s, prof)

        headers = _auth(test_client, prof.email)
        payload = {"user_id": str(stu1.id), "course_id": str(course.id)}
        resp1 = test_client.post("/api/enrollments/", json=payload, headers=headers)
        assert resp1.status_code == 201
        resp2 = test_client.post("/api/enrollments/", json=payload, headers=headers)
        assert resp2.status_code == 409

    def test_list_enrollments_student_sees_own(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, stu2 = _make_users(s)
            course = _make_course(s, prof)
            s.add(Enrollment(id=uuid4(), user_id=stu1.id, course_id=course.id))
            s.add(Enrollment(id=uuid4(), user_id=stu2.id, course_id=course.id))
            s.commit()

        headers = _auth(test_client, stu1.email)
        resp = test_client.get("/api/enrollments/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["userId"] == str(stu1.id)

    def test_instructor_can_delete_enrollment(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            course = _make_course(s, prof)
            enrollment = Enrollment(id=uuid4(), user_id=stu1.id, course_id=course.id)
            s.add(enrollment)
            s.commit()
            eid = enrollment.id

        headers = _auth(test_client, prof.email)
        resp = test_client.delete(f"/api/enrollments/{eid}", headers=headers)
        assert resp.status_code == 204

    def test_bulk_enroll(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, stu2 = _make_users(s)
            course = _make_course(s, prof)

        headers = _auth(test_client, prof.email)
        resp = test_client.post("/api/enrollments/bulk", json={
            "user_ids": [str(stu1.id), str(stu2.id)],
            "course_id": str(course.id),
        }, headers=headers)
        assert resp.status_code == 201
        assert len(resp.json()) == 2


class TestSelfEnrollment:

    def test_student_can_join_with_valid_code(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            course = _make_course_with_code(s, prof, code="ABCD", enabled=True)

        headers = _auth(test_client, stu1.email)
        resp = test_client.post("/api/enrollments/join", json={"code": "ABCD"}, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["courseId"] == str(course.id)
        assert data["userId"] == str(stu1.id)

    def test_join_rejects_invalid_code(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            _make_course_with_code(s, prof, code="REAL", enabled=True)

        headers = _auth(test_client, stu1.email)
        resp = test_client.post("/api/enrollments/join", json={"code": "FAKE"}, headers=headers)
        assert resp.status_code == 404

    def test_join_rejects_when_disabled(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            _make_course_with_code(s, prof, code="OFFF", enabled=False)

        headers = _auth(test_client, stu1.email)
        resp = test_client.post("/api/enrollments/join", json={"code": "OFFF"}, headers=headers)
        assert resp.status_code == 400

    def test_join_rejects_duplicate_enrollment(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            _make_course_with_code(s, prof, code="DUPL", enabled=True)

        headers = _auth(test_client, stu1.email)
        first = test_client.post("/api/enrollments/join", json={"code": "DUPL"}, headers=headers)
        assert first.status_code == 201
        second = test_client.post("/api/enrollments/join", json={"code": "DUPL"}, headers=headers)
        assert second.status_code == 409

    def test_non_students_cannot_join_by_code(self, test_client, test_db):
        with test_db() as s:
            _, prof, _, _ = _make_users(s)
            _make_course_with_code(s, prof, code="PROF", enabled=True)

        headers = _auth(test_client, prof.email)
        resp = test_client.post("/api/enrollments/join", json={"code": "PROF"}, headers=headers)
        assert resp.status_code == 403

    def test_instructor_can_reset_and_toggle_enrollment(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, _ = _make_users(s)
            course = _make_course_with_code(s, prof, code="INIT", enabled=True)

        headers = _auth(test_client, prof.email)
        reset = test_client.post(f"/api/courses/{course.id}/reset-code", headers=headers)
        assert reset.status_code == 200
        new_code = reset.json().get("enrollmentCode")
        assert new_code and new_code != "INIT"
        assert len(new_code) == 4

        disable = test_client.patch(f"/api/courses/{course.id}/settings", json={"is_enrollment_enabled": False}, headers=headers)
        assert disable.status_code == 200
        assert disable.json().get("isEnrollmentEnabled") is False

    def test_course_creation_returns_enabled_code(self, test_client, test_db):
        with test_db() as s:
            _, prof, _, _ = _make_users(s)

        headers = _auth(test_client, prof.email)
        resp = test_client.post("/api/courses/", json={
            "name": "New Course",
            "description": "desc",
            "instructor_id": str(prof.id),
        }, headers=headers)

        assert resp.status_code == 201
        body = resp.json()
        assert body.get("enrollmentCode")
        assert body.get("isEnrollmentEnabled") is True


# ────────────── Course / Assignment Visibility ──────────────────


class TestEnrollmentVisibility:

    def _setup(self, test_db):
        with test_db() as s:
            admin, prof, stu1, stu2 = _make_users(s)
            course = _make_course(s, prof)
            assignment = Assignment(
                id=uuid4(), course_id=course.id, title="HW1",
                description="Homework", deadline=datetime.now() + timedelta(days=7),
                max_grade={"points": 100},
            )
            s.add(assignment)
            # Only enroll stu1
            s.add(Enrollment(id=uuid4(), user_id=stu1.id, course_id=course.id))
            s.commit()
            return admin, prof, stu1, stu2, course, assignment

    def test_enrolled_student_sees_course_list(self, test_client, test_db):
        admin, prof, stu1, stu2, course, _ = self._setup(test_db)
        headers = _auth(test_client, stu1.email)
        resp = test_client.get("/api/courses/", headers=headers)
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert str(course.id) in ids

    def test_non_enrolled_student_sees_empty_course_list(self, test_client, test_db):
        _, _, _, stu2, course, _ = self._setup(test_db)
        headers = _auth(test_client, stu2.email)
        resp = test_client.get("/api/courses/", headers=headers)
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()]
        assert str(course.id) not in ids

    def test_enrolled_student_can_view_course_detail(self, test_client, test_db):
        _, _, stu1, _, course, _ = self._setup(test_db)
        headers = _auth(test_client, stu1.email)
        resp = test_client.get(f"/api/courses/{course.id}", headers=headers)
        assert resp.status_code == 200

    def test_non_enrolled_student_cannot_view_course_detail(self, test_client, test_db):
        _, _, _, stu2, course, _ = self._setup(test_db)
        headers = _auth(test_client, stu2.email)
        resp = test_client.get(f"/api/courses/{course.id}", headers=headers)
        assert resp.status_code == 403

    def test_enrolled_student_sees_assignments(self, test_client, test_db):
        _, _, stu1, _, course, assignment = self._setup(test_db)
        headers = _auth(test_client, stu1.email)
        resp = test_client.get(f"/api/assignments/?course_id={course.id}", headers=headers)
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        assert str(assignment.id) in ids

    def test_non_enrolled_student_cannot_see_assignments(self, test_client, test_db):
        _, _, _, stu2, course, assignment = self._setup(test_db)
        headers = _auth(test_client, stu2.email)
        resp = test_client.get(f"/api/assignments/?course_id={course.id}", headers=headers)
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        assert str(assignment.id) not in ids


# ──────────── Artifact Permission with Enrollment ───────────────


class TestArtifactEnrollmentPermissions:

    def test_enrolled_student_can_view_course_artifact(self, test_client, test_db):
        with test_db() as s:
            _, prof, stu1, stu2 = _make_users(s)
            course = _make_course(s, prof)
            s.add(Enrollment(id=uuid4(), user_id=stu1.id, course_id=course.id))

            artifact = Artifact(
                id=uuid4(), title="Course Material", artifact_type="document",
                mime="application/pdf", storage_path="/path/material.pdf",
                storage_type="local", creator_id=prof.id,
                course_id=course.id, status="attached", access_level="course",
            )
            s.add(artifact)
            s.commit()
            art_id = artifact.id

        # Enrolled student can view
        headers = _auth(test_client, stu1.email)
        resp = test_client.get(f"/api/artifacts/{art_id}", headers=headers)
        assert resp.status_code == 200

        # Non-enrolled student cannot view
        headers = _auth(test_client, stu2.email)
        resp = test_client.get(f"/api/artifacts/{art_id}", headers=headers)
        assert resp.status_code == 403
