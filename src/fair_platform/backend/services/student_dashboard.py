from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.lms_communication import CoursePost
from fair_platform.backend.data.models.lms_events import (
    CalendarEvent,
    CalendarEventVisibility,
)
from fair_platform.backend.data.models.lms_progress import (
    ItemCompletionStatus,
    UserItemCompletion,
)
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_content_service import CourseContentService
from fair_platform.backend.services.gradebook import (
    SUBMISSION_SOURCE_TYPE,
    gradebook_projection,
)


T = TypeVar("T")

ASSIGNMENT_DUE_OVERRIDE_SOURCE = "assignment_due_override"
ASSIGNMENT_CUTOFF_SOURCE = "assignment_cutoff"


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _learner_timezone(db: Session, user_id: UUID) -> str:
    user = db.get(User, user_id)
    settings = user.settings if user and isinstance(user.settings, dict) else {}
    preferences = settings.get("preferences", {})
    candidate = preferences.get("timezone") if isinstance(preferences, dict) else None
    if not isinstance(candidate, str) or not candidate.strip():
        return "UTC"
    try:
        ZoneInfo(candidate)
    except ZoneInfoNotFoundError:
        return "UTC"
    return candidate


def active_student_courses(db: Session, user_id: UUID) -> list[Course]:
    return (
        db.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == user_id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
            Course.is_archived.is_(False),
        )
        .order_by(Course.name, Course.id)
        .all()
    )


def _real_submitter_ids(db: Session, user_id: UUID) -> list[UUID]:
    return [
        row[0]
        for row in db.query(Submitter.id)
        .filter(
            Submitter.user_id == user_id,
            Submitter.is_synthetic.is_(False),
        )
        .all()
    ]


def _latest_submissions(
    db: Session, user_id: UUID, assignment_ids: list[UUID]
) -> dict[UUID, Submission]:
    submitter_ids = _real_submitter_ids(db, user_id)
    if not submitter_ids or not assignment_ids:
        return {}
    rows = (
        db.query(Submission)
        .filter(
            Submission.submitter_id.in_(submitter_ids),
            Submission.assignment_id.in_(assignment_ids),
        )
        .order_by(
            Submission.attempt_number,
            Submission.submitted_at,
            Submission.id,
        )
        .all()
    )
    return {submission.assignment_id: submission for submission in rows}


def student_course_grades(db: Session, course: Course, user_id: UUID) -> dict[str, Any]:
    categories, items, projections = gradebook_projection(db, course.id, [user_id])
    projection = projections[user_id]
    cells = {cell["grade_item_id"]: cell for cell in projection["item_cells"]}
    category_totals = {
        item["category_id"]: item for item in projection["category_totals"]
    }
    total = projection["course_total"]

    included_weight = sum(
        float(category_total["weight"])
        for category_total in projection["category_totals"]
        if category_total["weight"] is not None
        and category_total["weight"] > 0
        and category_total["percentage"] is not None
    )

    assignment_ids = [
        item["source_id"]
        for item in items
        if item["source_type"] == "assignment" and item["source_id"] is not None
    ]
    assignments_by_id = (
        {
            assignment.id: assignment
            for assignment in db.query(Assignment)
            .filter(
                Assignment.id.in_(assignment_ids), Assignment.course_id == course.id
            )
            .all()
        }
        if assignment_ids
        else {}
    )

    result_items: list[dict[str, Any]] = []
    for item in items:
        cell = cells[item["id"]]
        released = cell["release_state"] == "released"
        assignment_id = (
            item["source_id"] if item["source_type"] == "assignment" else None
        )
        published_assignment = assignments_by_id.get(assignment_id)
        safe_missing = cell["release_state"] == "absent" and assignment_id is not None
        visible = released or safe_missing
        status = (
            cell["status"] if released else "missing" if safe_missing else "unreleased"
        )
        category_total = category_totals.get(item["category_id"])
        contribution = None
        if released and status == "graded" and total["percentage"] is not None:
            if total["calculation"] == "category_weighted":
                category_weight = category_total["weight"] if category_total else None
                category_possible = (
                    category_total["points_possible"] if category_total else 0
                )
                if (
                    category_possible > 0
                    and category_weight is not None
                    and category_weight > 0
                    and included_weight > 0
                ):
                    contribution = (
                        float(cell["points_earned"])
                        / float(category_possible)
                        * (float(category_weight) / included_weight)
                        * 100
                    )
            elif total["points_possible"] > 0:
                contribution = (
                    float(cell["points_earned"]) / float(total["points_possible"]) * 100
                )
        submission_id = (
            cell.get("source_id")
            if released and cell.get("source_type") == SUBMISSION_SOURCE_TYPE
            else None
        )
        can_link_assignment = bool(
            published_assignment
            and _enum_value(published_assignment.status)
            == AssignmentStatus.published.value
        )
        result_items.append(
            {
                "grade_item_id": item["id"],
                "category_id": item["category_id"],
                # A published assignment is safe to name even when it has no grade
                # entry. Other unreleased entries deliberately expose no identity.
                "title": item["title"] if visible else None,
                "max_points": item["max_points"] if visible else None,
                "status": status,
                "points_earned": cell.get("points_earned") if released else None,
                "released_at": cell.get("released_at") if released else None,
                "note": cell.get("note") if released else None,
                "assignment_id": assignment_id
                if visible and can_link_assignment
                else None,
                "submission_id": submission_id,
                "contribution_percentage_points": contribution,
            }
        )

    return {
        "course_id": course.id,
        "course_name": course.name,
        "term": course.term,
        "total": total,
        "current_grade_label": "Final grade" if course.is_archived else "Current grade",
        "final_grade_available": course.is_archived and not total["provisional"],
        "categories": categories,
        "category_totals": projection["category_totals"],
        "items": result_items,
    }


def work_projection(
    db: Session, courses: list[Course], user_id: UUID, now: datetime
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    course_ids = [course.id for course in courses]
    if not course_ids:
        return [], []
    courses_by_id = {course.id: course for course in courses}
    timezone_name = _learner_timezone(db, user_id)
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id.in_(course_ids),
            Assignment.status == AssignmentStatus.published,
        )
        .order_by(Assignment.deadline, Assignment.title)
        .all()
    )
    submissions = _latest_submissions(
        db, user_id, [assignment.id for assignment in assignments]
    )

    assignment_ids = [assignment.id for assignment in assignments]
    calendar_rows = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.owner_user_id == user_id,
            CalendarEvent.course_id.in_(course_ids),
            CalendarEvent.visibility == CalendarEventVisibility.private,
            CalendarEvent.source_id.in_(assignment_ids),
            CalendarEvent.source_type.in_(
                [ASSIGNMENT_DUE_OVERRIDE_SOURCE, ASSIGNMENT_CUTOFF_SOURCE]
            ),
        )
        .order_by(CalendarEvent.updated_at, CalendarEvent.id)
        .all()
        if assignment_ids
        else []
    )
    calendar_by_source = {
        (event.source_type, event.course_id, event.source_id): event
        for event in calendar_rows
    }

    visible_content = {
        course.id: CourseContentService(db).list_sections(course.id, staff_view=False)
        for course in courses
    }
    assignment_items: dict[UUID, set[UUID]] = {}
    visible_item_ids: set[UUID] = set()
    for sections in visible_content.values():
        for _section, items in sections:
            for item in items:
                visible_item_ids.add(item.id)
                if item.kind == "assignment" and item.resource_id is not None:
                    assignment_items.setdefault(item.resource_id, set()).add(item.id)
    completed_item_ids = (
        set(
            row[0]
            for row in db.query(UserItemCompletion.course_item_id)
            .filter(
                UserItemCompletion.user_id == user_id,
                UserItemCompletion.course_item_id.in_(visible_item_ids),
                UserItemCompletion.status == ItemCompletionStatus.completed,
            )
            .all()
        )
        if visible_item_ids
        else set()
    )

    upcoming: list[dict[str, Any]] = []
    overdue: list[dict[str, Any]] = []
    for assignment in assignments:
        if assignment_items.get(assignment.id, set()) & completed_item_ids:
            continue
        submission = submissions.get(assignment.id)
        if submission and submission.status in {
            SubmissionStatus.returned,
            SubmissionStatus.excused,
        }:
            continue
        cutoff = calendar_by_source.get(
            (ASSIGNMENT_CUTOFF_SOURCE, assignment.course_id, assignment.id)
        )
        if cutoff is not None and _aware(cutoff.starts_at) <= now:
            continue
        override = calendar_by_source.get(
            (ASSIGNMENT_DUE_OVERRIDE_SOURCE, assignment.course_id, assignment.id)
        )
        deadline = override.starts_at if override is not None else assignment.deadline
        if deadline is not None:
            deadline = _aware(deadline)
        state = "submitted" if submission else "upcoming"
        if submission is None and deadline is not None and deadline < now:
            state = "overdue"
        payload = {
            "assignment_id": assignment.id,
            "course_id": assignment.course_id,
            "course_name": courses_by_id[assignment.course_id].name,
            "title": assignment.title,
            "deadline": deadline,
            "timezone_name": (
                override.timezone_name
                if override and override.timezone_name
                else timezone_name
            ),
            "state": state,
            "submission_id": submission.id if submission else None,
        }
        (overdue if state == "overdue" else upcoming).append(payload)
    return upcoming[:20], overdue[:20]


def feedback_projection(
    db: Session, courses: list[Course], user_id: UUID
) -> list[dict[str, Any]]:
    course_ids = [course.id for course in courses]
    if not course_ids:
        return []
    courses_by_id = {course.id: course for course in courses}
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id.in_(course_ids),
            Assignment.status.in_(
                [AssignmentStatus.published, AssignmentStatus.closed]
            ),
        )
        .all()
    )
    assignments_by_id = {assignment.id: assignment for assignment in assignments}
    latest = _latest_submissions(db, user_id, list(assignments_by_id))
    rows = sorted(
        [
            (submission, assignments_by_id[assignment_id])
            for assignment_id, submission in latest.items()
            if submission.status == SubmissionStatus.returned
            and submission.returned_at is not None
        ],
        key=lambda row: _aware(row[0].returned_at),
        reverse=True,
    )[:10]
    return [
        {
            "assignment_id": assignment.id,
            "submission_id": submission.id,
            "course_id": assignment.course_id,
            "course_name": courses_by_id[assignment.course_id].name,
            "assignment_title": assignment.title,
            "points_earned": submission.published_score,
            "max_points": float(assignment.max_grade["value"]),
            "feedback_available": bool(submission.published_feedback),
            "returned_at": submission.returned_at,
            "link": (
                f"/courses/{assignment.course_id}/assignments/{assignment.id}"
                if _enum_value(assignment.status) == AssignmentStatus.published.value
                else f"/courses/{assignment.course_id}/grades"
            ),
        }
        for submission, assignment in rows
    ]


def activity_projection(db: Session, courses: list[Course]) -> list[dict[str, Any]]:
    course_ids = [course.id for course in courses]
    if not course_ids:
        return []
    courses_by_id = {course.id: course for course in courses}
    posts = (
        db.query(CoursePost)
        .filter(CoursePost.course_id.in_(course_ids))
        .order_by(CoursePost.created_at.desc())
        .limit(15)
        .all()
    )
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id.in_(course_ids),
            Assignment.status == AssignmentStatus.published,
            Assignment.published_at.is_not(None),
        )
        .order_by(Assignment.published_at.desc())
        .limit(15)
        .all()
    )
    result = [
        {
            "id": post.id,
            "course_id": post.course_id,
            "course_name": courses_by_id[post.course_id].name,
            "kind": _enum_value(post.kind),
            "title": post.title,
            "occurred_at": post.created_at,
            "link": f"/courses/{post.course_id}/stream",
        }
        for post in posts
    ]
    result.extend(
        {
            "id": assignment.id,
            "course_id": assignment.course_id,
            "course_name": courses_by_id[assignment.course_id].name,
            "kind": "assignment",
            "title": assignment.title,
            "occurred_at": assignment.published_at,
            "link": f"/courses/{assignment.course_id}/assignments/{assignment.id}",
        }
        for assignment in assignments
    )
    return sorted(result, key=lambda item: item["occurred_at"], reverse=True)[:15]


def progress_projection(
    db: Session, courses: list[Course], user_id: UUID
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for course in courses:
        visible_sections = CourseContentService(db).list_sections(
            course.id, staff_view=False
        )
        visible_item_ids = {
            item.id for _section, items in visible_sections for item in items
        }
        tracked_items = len(visible_item_ids)
        completed = (
            db.query(UserItemCompletion)
            .filter(
                UserItemCompletion.course_id == course.id,
                UserItemCompletion.user_id == user_id,
                UserItemCompletion.course_item_id.in_(visible_item_ids),
                UserItemCompletion.status == ItemCompletionStatus.completed,
            )
            .count()
            if visible_item_ids
            else 0
        )
        grades = student_course_grades(db, course, user_id)
        total = grades["total"]
        result.append(
            {
                "course_id": course.id,
                "course_name": course.name,
                "term": course.term,
                "completed_items": completed,
                "tracked_items": tracked_items,
                "completion_percentage": (
                    completed / tracked_items * 100 if tracked_items else None
                ),
                "current_grade": total["percentage"],
                "points_earned": total["points_earned"],
                "points_possible": total["points_possible"],
                "grade_is_provisional": total["provisional"],
            }
        )
    return result


def resilient_student_dashboard(
    db: Session, user_id: UUID, *, now: datetime | None = None
) -> dict[str, Any]:
    generated_at = now or datetime.now(timezone.utc)
    courses = active_student_courses(db, user_id)
    values: dict[str, Any] = {
        "upcoming_work": [],
        "overdue_work": [],
        "returned_feedback": [],
        "recent_activity": [],
        "course_progress": [],
    }
    statuses: list[dict[str, Any]] = []

    def run(source: str, target: str, loader: Callable[[], T]) -> None:
        try:
            values[target] = loader()
            statuses.append({"source": source, "available": True})
        except Exception:
            db.rollback()
            statuses.append(
                {
                    "source": source,
                    "available": False,
                    "message": f"{source.title()} data is temporarily unavailable",
                }
            )

    def load_work() -> None:
        upcoming, overdue = work_projection(db, courses, user_id, generated_at)
        values["upcoming_work"] = upcoming
        values["overdue_work"] = overdue

    try:
        load_work()
        statuses.append({"source": "work", "available": True})
    except Exception:
        db.rollback()
        statuses.append(
            {
                "source": "work",
                "available": False,
                "message": "Work data is temporarily unavailable",
            }
        )
    run(
        "feedback",
        "returned_feedback",
        lambda: feedback_projection(db, courses, user_id),
    )
    run("activity", "recent_activity", lambda: activity_projection(db, courses))
    run(
        "progress", "course_progress", lambda: progress_projection(db, courses, user_id)
    )
    return {"generated_at": generated_at, **values, "sources": statuses}


__all__ = [
    "active_student_courses",
    "activity_projection",
    "feedback_projection",
    "progress_projection",
    "resilient_student_dashboard",
    "student_course_grades",
    "work_projection",
]
