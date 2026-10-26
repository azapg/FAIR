from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.artifact import (
    AccessLevel,
    Artifact,
    ArtifactStatus,
)
from fair_platform.backend.data.models.assignment import (
    Assignment,
    AssignmentStatus,
)
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment, EnrollmentStatus
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseItem,
    CourseSection,
)
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.artifact_manager import ArtifactManager
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
    token = get_auth_token(client, str(user.email))
    return {"Authorization": f"Bearer {token}"}


def _course(session, owner: User, *, archived: bool = False) -> Course:
    course = Course(
        id=uuid4(),
        name="Course builder",
        instructor_id=owner.id,
        is_archived=archived,
    )
    session.add(course)
    session.commit()
    return course


def test_staff_crud_and_exact_membership_reorder(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        course = _course(session, owner)
    headers = _auth(test_client, owner)

    section_ids = []
    for title in ("Week one", "Week two"):
        response = test_client.post(
            f"/api/lms/courses/{course.id}/sections",
            json={"title": title, "visibility": "published"},
            headers=headers,
        )
        assert response.status_code == 201
        section_ids.append(response.json()["id"])

    rejected = test_client.put(
        f"/api/lms/courses/{course.id}/sections/order",
        json={"orderedIds": [section_ids[0]]},
        headers=headers,
    )
    assert rejected.status_code == 409

    reordered = test_client.put(
        f"/api/lms/courses/{course.id}/sections/order",
        json={"orderedIds": list(reversed(section_ids))},
        headers=headers,
    )
    assert reordered.status_code == 200
    assert [section["id"] for section in reordered.json()] == list(
        reversed(section_ids)
    )
    assert [section["position"] for section in reordered.json()] == [0, 1]

    item_ids = []
    for payload in (
        {
            "title": "Read this first",
            "kind": "page",
            "visibility": "published",
            "payload": {"body": "Welcome to **FAIR**."},
        },
        {
            "title": "Reference",
            "kind": "link",
            "visibility": "published",
            "payload": {"url": "https://example.com/reference"},
        },
    ):
        response = test_client.post(
            f"/api/lms/courses/{course.id}/sections/{section_ids[0]}/items",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 201
        item_ids.append(response.json()["id"])

    duplicate_order = test_client.put(
        f"/api/lms/courses/{course.id}/sections/{section_ids[0]}/items/order",
        json={"orderedIds": [item_ids[0], item_ids[0]]},
        headers=headers,
    )
    assert duplicate_order.status_code == 409

    reordered_items = test_client.put(
        f"/api/lms/courses/{course.id}/sections/{section_ids[0]}/items/order",
        json={"orderedIds": list(reversed(item_ids))},
        headers=headers,
    )
    assert reordered_items.status_code == 200
    assert [item["id"] for item in reordered_items.json()] == list(reversed(item_ids))

    deleted = test_client.delete(
        f"/api/lms/courses/{course.id}/items/{item_ids[1]}", headers=headers
    )
    assert deleted.status_code == 204
    outline = test_client.get(
        f"/api/lms/courses/{course.id}/content", headers=headers
    ).json()
    first_section = next(
        section for section in outline["sections"] if section["id"] == section_ids[0]
    )
    assert [(item["id"], item["position"]) for item in first_section["items"]] == [
        (item_ids[0], 0)
    ]


def test_visibility_permissions_and_archived_read_only(test_client, test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        student = _user(session, "Student", UserRole.student)
        outsider = _user(session, "Outsider", UserRole.student)
        course = _course(session, owner)
        published_assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Published assignment",
            max_grade={"type": "points", "value": 100},
            status=AssignmentStatus.published,
        )
        draft_assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Draft assignment",
            max_grade={"type": "points", "value": 100},
            status=AssignmentStatus.draft,
        )
        published_section = CourseSection(
            id=uuid4(),
            course_id=course.id,
            title="Published section",
            position=0,
            visibility=CourseContentVisibility.published,
        )
        draft_section = CourseSection(
            id=uuid4(),
            course_id=course.id,
            title="Draft section",
            position=1,
            visibility=CourseContentVisibility.draft,
        )
        session.add_all(
            [published_assignment, draft_assignment, published_section, draft_section]
        )
        session.flush()
        session.add_all(
            [
                Enrollment(id=uuid4(), user_id=student.id, course_id=course.id),
                CourseItem(
                    id=uuid4(),
                    course_id=course.id,
                    section_id=published_section.id,
                    title="Welcome",
                    position=0,
                    kind="page",
                    visibility=CourseContentVisibility.published,
                    payload_schema_uri="urn:fair:lms:course-item:page:v1",
                    payload={"body": "Visible page"},
                ),
                CourseItem(
                    id=uuid4(),
                    course_id=course.id,
                    section_id=published_section.id,
                    title="Published assignment",
                    position=1,
                    kind="assignment",
                    visibility=CourseContentVisibility.published,
                    resource_type="assignment",
                    resource_id=published_assignment.id,
                    payload={},
                ),
                CourseItem(
                    id=uuid4(),
                    course_id=course.id,
                    section_id=published_section.id,
                    title="Draft item",
                    position=2,
                    kind="heading",
                    visibility=CourseContentVisibility.draft,
                    payload={},
                ),
                CourseItem(
                    id=uuid4(),
                    course_id=course.id,
                    section_id=published_section.id,
                    title="Draft assignment",
                    position=3,
                    kind="assignment",
                    visibility=CourseContentVisibility.published,
                    resource_type="assignment",
                    resource_id=draft_assignment.id,
                    payload={},
                ),
                CourseItem(
                    id=uuid4(),
                    course_id=course.id,
                    section_id=draft_section.id,
                    title="Hidden by section",
                    position=0,
                    kind="heading",
                    visibility=CourseContentVisibility.published,
                    payload={},
                ),
            ]
        )
        session.commit()

    student_view = test_client.get(
        f"/api/lms/courses/{course.id}/content", headers=_auth(test_client, student)
    )
    assert student_view.status_code == 200
    assert student_view.json()["canManage"] is False
    assert [section["title"] for section in student_view.json()["sections"]] == [
        "Published section"
    ]
    assert [item["title"] for item in student_view.json()["sections"][0]["items"]] == [
        "Welcome",
        "Published assignment",
    ]

    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/content",
            headers=_auth(test_client, outsider),
        ).status_code
        == 403
    )
    assert (
        test_client.post(
            f"/api/lms/courses/{course.id}/sections",
            json={"title": "No access"},
            headers=_auth(test_client, student),
        ).status_code
        == 403
    )

    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    owner_headers = _auth(test_client, owner)
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/content", headers=owner_headers
        ).status_code
        == 200
    )
    assert (
        test_client.post(
            f"/api/lms/courses/{course.id}/sections",
            json={"title": "Archived edit"},
            headers=owner_headers,
        ).status_code
        == 409
    )


def test_removed_membership_cannot_open_course_artifact(test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        student = _user(session, "Removed", UserRole.student)
        course = _course(session, owner)
        enrollment = Enrollment(
            id=uuid4(),
            user_id=student.id,
            course_id=course.id,
            status=EnrollmentStatus.removed,
        )
        artifact = Artifact(
            id=uuid4(),
            title="Syllabus",
            artifact_type="document",
            creator_id=owner.id,
            status="attached",
            access_level=AccessLevel.course,
            course_id=course.id,
        )
        session.add_all([enrollment, artifact])
        session.commit()

        manager = ArtifactManager(session, storage_provider=object())
        assert manager.can_view(student, artifact) is False

        enrollment.status = EnrollmentStatus.active
        session.commit()
        assert manager.can_view(student, artifact) is True


def test_resource_deletion_removes_outline_links_and_compacts_positions(
    test_client, test_db
):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        course = _course(session, owner)
        assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Disposable assignment",
            max_grade={"type": "points", "value": 100},
            status=AssignmentStatus.draft,
        )
        deleted_artifact = Artifact(
            id=uuid4(),
            title="Disposable file",
            artifact_type="document",
            creator_id=owner.id,
            status=ArtifactStatus.attached,
            access_level=AccessLevel.course,
            course_id=course.id,
        )
        archived_artifact = Artifact(
            id=uuid4(),
            title="Archivable file",
            artifact_type="document",
            creator_id=owner.id,
            status=ArtifactStatus.attached,
            access_level=AccessLevel.course,
            course_id=course.id,
        )
        section = CourseSection(
            id=uuid4(),
            course_id=course.id,
            title="Resources",
            position=0,
            visibility=CourseContentVisibility.published,
        )
        session.add_all(
            [assignment, deleted_artifact, archived_artifact, section]
        )
        session.flush()
        assignment_item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title=assignment.title,
            position=0,
            kind="assignment",
            visibility=CourseContentVisibility.draft,
            resource_type="assignment",
            resource_id=assignment.id,
            payload={},
        )
        deleted_artifact_item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title=deleted_artifact.title,
            position=1,
            kind="file",
            visibility=CourseContentVisibility.published,
            resource_type="artifact",
            resource_id=deleted_artifact.id,
            payload={},
        )
        archived_artifact_item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title=archived_artifact.title,
            position=2,
            kind="file",
            visibility=CourseContentVisibility.published,
            resource_type="artifact",
            resource_id=archived_artifact.id,
            payload={},
        )
        surviving_item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title="Keep me",
            position=3,
            kind="page",
            visibility=CourseContentVisibility.published,
            copied_from_id=assignment_item.id,
            payload_schema_uri="urn:fair:lms:course-item:page:v1",
            payload={"body": "Still here"},
        )
        session.add_all(
            [
                assignment_item,
                deleted_artifact_item,
                archived_artifact_item,
                surviving_item,
            ]
        )
        session.commit()

    headers = _auth(test_client, owner)
    response = test_client.delete(
        f"/api/assignments/{assignment.id}", headers=headers
    )
    assert response.status_code == 204

    with test_db() as session:
        assert session.get(Assignment, assignment.id) is None
        assert session.get(CourseItem, assignment_item.id) is None
        remaining = (
            session.query(CourseItem)
            .filter(CourseItem.section_id == section.id)
            .order_by(CourseItem.position)
            .all()
        )
        assert [item.id for item in remaining] == [
            deleted_artifact_item.id,
            archived_artifact_item.id,
            surviving_item.id,
        ]
        assert [item.position for item in remaining] == [0, 1, 2]
        assert session.get(CourseItem, surviving_item.id).copied_from_id is None

    response = test_client.delete(
        f"/api/v1/artifacts/{deleted_artifact.id}", headers=headers
    )
    assert response.status_code == 204

    with test_db() as session:
        assert (
            session.get(Artifact, deleted_artifact.id).status
            == ArtifactStatus.archived
        )
        assert session.get(CourseItem, deleted_artifact_item.id) is None

    response = test_client.put(
        f"/api/v1/artifacts/{archived_artifact.id}",
        json={"status": "archived"},
        headers=headers,
    )
    assert response.status_code == 200

    with test_db() as session:
        assert (
            session.get(Artifact, archived_artifact.id).status
            == ArtifactStatus.archived
        )
        assert session.get(CourseItem, archived_artifact_item.id) is None
        remaining = (
            session.query(CourseItem)
            .filter(CourseItem.section_id == section.id)
            .order_by(CourseItem.position)
            .all()
        )
        assert [(item.id, item.position) for item in remaining] == [
            (surviving_item.id, 0)
        ]


def test_orphan_cleanup_removes_outline_link(test_db):
    with test_db() as session:
        owner = _user(session, "Owner", UserRole.instructor)
        course = _course(session, owner)
        artifact = Artifact(
            id=uuid4(),
            title="Expired orphan",
            artifact_type="document",
            creator_id=owner.id,
            status=ArtifactStatus.orphaned,
            access_level=AccessLevel.course,
            course_id=course.id,
            updated_at=datetime.now() - timedelta(days=8),
        )
        section = CourseSection(
            id=uuid4(),
            course_id=course.id,
            title="Resources",
            position=0,
            visibility=CourseContentVisibility.published,
        )
        session.add_all([artifact, section])
        session.flush()
        item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title=artifact.title,
            position=0,
            kind="file",
            visibility=CourseContentVisibility.published,
            resource_type="artifact",
            resource_id=artifact.id,
            payload={},
        )
        session.add(item)
        session.commit()

        manager = ArtifactManager(session, storage_provider=object())
        assert manager.cleanup_orphaned() == 1
        session.commit()

        assert session.get(Artifact, artifact.id).status == ArtifactStatus.archived
        assert session.get(CourseItem, item.id) is None
