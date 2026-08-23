from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from fair_platform.backend.data.models import (
    ActivityEvent,
    CalendarEvent,
    Cohort,
    CohortMembership,
    Course,
    CourseGroup,
    CourseGroupMembership,
    CourseItem,
    CourseSection,
    Enrollment,
    ExternalIdentifier,
    GradeCategory,
    GradeEntry,
    GradeItem,
    Organization,
    OrganizationMembership,
    User,
    UserItemCompletion,
    UserRole,
)


def _user(*, role: UserRole = UserRole.student) -> User:
    return User(
        id=uuid4(),
        name="LMS primitives user",
        email=f"{uuid4()}@example.test",
        role=role,
    )


def _course(instructor: User, *, name: str, organization_id=None) -> Course:
    return Course(
        id=uuid4(),
        name=name,
        instructor_id=instructor.id,
        organization_id=organization_id,
    )


def _enroll(user: User, course: Course) -> Enrollment:
    return Enrollment(id=uuid4(), user_id=user.id, course_id=course.id)


def test_course_content_is_stably_ordered_and_course_scoped(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        first_course = _course(instructor, name="First")
        second_course = _course(instructor, name="Second")
        session.add_all([instructor, first_course, second_course])
        session.flush()

        section = CourseSection(
            course_id=first_course.id,
            title="Week 1",
            position=0,
            visibility="published",
        )
        session.add(section)
        session.flush()

        item = CourseItem(
            course_id=first_course.id,
            section_id=section.id,
            title="Assignment",
            position=0,
            kind="activity",
            visibility="published",
            resource_type="assignment",
            resource_id=uuid4(),
            payload_schema_uri="urn:fair:course-item:assignment:v1",
            payload={"show_description": True},
        )
        session.add(item)
        session.commit()

        assert first_course.sections[0].items[0].resource_type == "assignment"
        assert first_course.sections[0].items[0].payload_schema_uri.endswith(":v1")

        session.add(
            CourseItem(
                course_id=second_course.id,
                section_id=section.id,
                title="Cross-course item",
                position=1,
                kind="quiz",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_course_content_positions_are_unique_per_parent(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        course = _course(instructor, name="Ordering")
        session.add_all([instructor, course])
        session.flush()
        session.add_all(
            [
                CourseSection(course_id=course.id, title="One", position=0),
                CourseSection(course_id=course.id, title="Duplicate", position=0),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


@pytest.mark.parametrize(
    "invalid",
    [
        {"type": "percentage", "value": 100},
        {"type": "points", "value": 100},
        "100",
        True,
        0,
        -1,
        float("inf"),
        float("nan"),
    ],
)
def test_grade_item_rejects_noncanonical_point_maximums(invalid) -> None:
    with pytest.raises(ValueError, match="max_points"):
        GradeItem(
            course_id=uuid4(),
            title="Invalid grade item",
            position=0,
            max_points=invalid,
        )


def test_grade_entries_store_points_and_release_state_only(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        learner = _user()
        course = _course(instructor, name="Gradebook")
        session.add_all([instructor, learner, course])
        session.flush()
        session.add(_enroll(learner, course))
        category = GradeCategory(
            course_id=course.id,
            name="Assignments",
            position=0,
            aggregation_strategy="weighted_mean",
            weight=1,
            calculation_policy={"drop_lowest": 1},
        )
        session.add(category)
        session.flush()
        item = GradeItem(
            course_id=course.id,
            category_id=category.id,
            title="A1",
            position=0,
            max_points=100,
            source_type="assignment",
            source_id=uuid4(),
        )
        session.add(item)
        session.flush()
        returned_at = datetime.now(timezone.utc)
        entry = GradeEntry(
            course_id=course.id,
            grade_item_id=item.id,
            user_id=learner.id,
            status="graded",
            points_earned=87.5,
            release_state="released",
            released_at=returned_at,
            graded_at=returned_at,
            source_type="submission",
            source_id=uuid4(),
            source_version="published_score:v1",
            recorded_by_user_id=instructor.id,
        )
        session.add(entry)
        session.commit()

        assert float(entry.points_earned) == 87.5
        assert item.category is not None
        assert item.category.id == category.id
        assert category.items[0].id == item.id
        assert entry.release_state == "released"
        assert entry.source_version == "published_score:v1"
        assert "percentage" not in GradeEntry.__table__.columns
        assert "letter" not in GradeEntry.__table__.columns
        assert "pass_fail" not in GradeEntry.__table__.columns


def test_grade_entry_requires_item_and_enrollment_in_same_course(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        learner = _user()
        first_course = _course(instructor, name="First")
        second_course = _course(instructor, name="Second")
        session.add_all([instructor, learner, first_course, second_course])
        session.flush()
        session.add(_enroll(learner, second_course))
        item = GradeItem(
            course_id=first_course.id,
            title="A1",
            position=0,
            max_points=100,
        )
        session.add(item)
        session.flush()
        session.add(
            GradeEntry(
                course_id=second_course.id,
                grade_item_id=item.id,
                user_id=learner.id,
                status="missing",
                release_state="unreleased",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_grade_category_hierarchy_cannot_cross_courses(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        first_course = _course(instructor, name="First hierarchy")
        second_course = _course(instructor, name="Second hierarchy")
        session.add_all([instructor, first_course, second_course])
        session.flush()
        parent = GradeCategory(course_id=first_course.id, name="Parent", position=0)
        session.add(parent)
        session.flush()
        valid_child = GradeCategory(
            course_id=first_course.id,
            parent_category_id=parent.id,
            name="Valid child",
            position=1,
        )
        session.add(valid_child)
        session.flush()
        assert valid_child.parent is not None
        assert valid_child.parent.id == parent.id
        child = GradeCategory(
            course_id=second_course.id,
            parent_category_id=parent.id,
            name="Cross-course child",
            position=0,
        )
        session.add(child)
        with pytest.raises(IntegrityError):
            session.commit()


def test_group_and_completion_membership_cannot_cross_courses(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        learner = _user()
        first_course = _course(instructor, name="First")
        second_course = _course(instructor, name="Second")
        session.add_all([instructor, learner, first_course, second_course])
        session.flush()
        session.add(_enroll(learner, second_course))
        group = CourseGroup(course_id=first_course.id, name="Team A")
        section = CourseSection(course_id=first_course.id, title="Week 1", position=0)
        session.add_all([group, section])
        session.flush()
        item = CourseItem(
            course_id=first_course.id,
            section_id=section.id,
            title="Read",
            position=0,
            kind="page",
        )
        session.add(item)
        session.flush()

        session.add(
            CourseGroupMembership(
                course_id=second_course.id,
                group_id=group.id,
                user_id=learner.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        learner = _user()
        first_course = _course(instructor, name="First again")
        second_course = _course(instructor, name="Second again")
        session.add_all([instructor, learner, first_course, second_course])
        session.flush()
        session.add(_enroll(learner, second_course))
        section = CourseSection(course_id=first_course.id, title="Week 1", position=0)
        session.add(section)
        session.flush()
        item = CourseItem(
            course_id=first_course.id,
            section_id=section.id,
            title="Read",
            position=0,
            kind="page",
        )
        session.add(item)
        session.flush()
        session.add(
            UserItemCompletion(
                course_id=first_course.id,
                course_item_id=item.id,
                user_id=learner.id,
                status="not_started",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_cohort_and_external_identifiers_are_organization_scoped(test_db) -> None:
    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        learner = _user()
        first_org = Organization(name="First University", slug="first-university")
        second_org = Organization(name="Second University", slug="second-university")
        session.add_all([instructor, learner, first_org, second_org])
        session.flush()
        session.add(
            OrganizationMembership(
                organization_id=first_org.id,
                user_id=learner.id,
                role="member",
            )
        )
        cohort = Cohort(organization_id=second_org.id, name="2026")
        session.add(cohort)
        session.flush()
        session.add(
            CohortMembership(
                organization_id=first_org.id,
                cohort_id=cohort.id,
                user_id=learner.id,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    with test_db() as session:
        instructor = _user(role=UserRole.instructor)
        org = Organization(name="Third University", slug="third-university")
        session.add_all([instructor, org])
        session.flush()
        course = _course(
            instructor, name="Institutional course", organization_id=org.id
        )
        session.add(course)
        session.flush()
        external = ExternalIdentifier(
            organization_id=org.id,
            system="sis",
            subject_type="course",
            external_id="COURSE-101",
            course_id=course.id,
        )
        session.add(external)
        session.commit()
        assert external.external_id == "COURSE-101"


def test_activity_events_are_append_only_and_calendar_times_are_valid(test_db) -> None:
    with test_db() as session:
        actor = _user(role=UserRole.instructor)
        session.add(actor)
        session.flush()
        activity = ActivityEvent(
            event_type="course.created",
            actor_user_id=actor.id,
            object_type="course",
            object_id=uuid4(),
            source_type="course_copy",
            source_id=uuid4(),
            payload={"copied_from_id": str(uuid4())},
        )
        session.add(activity)
        session.commit()

        activity.payload = {"changed": True}
        with pytest.raises(ValueError, match="append-only"):
            session.commit()

    with test_db() as session:
        actor = _user(role=UserRole.instructor)
        session.add(actor)
        session.flush()
        starts_at = datetime.now(timezone.utc)
        session.add(
            CalendarEvent(
                owner_user_id=actor.id,
                title="Invalid",
                starts_at=starts_at,
                ends_at=starts_at - timedelta(minutes=1),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
