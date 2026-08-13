from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock, RLock
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import event, func
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.lms_gradebook import (
    GradeAggregationStrategy,
    GradeCategory,
    GradeEntry,
    GradeEntryStatus,
    GradeItem,
    GradeReleaseState,
)
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User


DEFAULT_CATEGORY_POLICY_KEY = "fairDefaultCategory"
DEFAULT_CATEGORY_POLICY_VALUE = "assignments"
ASSIGNMENT_SOURCE_TYPE = "assignment"
SUBMISSION_SOURCE_TYPE = "submission"
MANUAL_ENTRY_SOURCE_TYPE = "manual"
_SQLITE_ORDER_LOCKS: dict[UUID, RLock] = {}
_SQLITE_ORDER_LOCKS_GUARD = Lock()
_SESSION_ORDER_LOCKS_KEY = "fair_gradebook_order_locks"


def _release_sqlite_order_locks(session: Session, transaction: Any) -> None:
    if transaction.parent is not None:
        return
    locks = session.info.pop(_SESSION_ORDER_LOCKS_KEY, {})
    for lock in reversed(list(locks.values())):
        lock.release()


event.listen(Session, "after_transaction_end", _release_sqlite_order_locks)


def _decimal(value: int | float | Decimal) -> Decimal:
    return Decimal(str(value))


def _float(value: Decimal | int | float | None) -> float | None:
    return float(value) if value is not None else None


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _lock_course_order(db: Session, course_id: UUID) -> None:
    if db.get_bind().dialect.name == "sqlite":
        held_locks: dict[UUID, RLock] = db.info.setdefault(_SESSION_ORDER_LOCKS_KEY, {})
        if course_id not in held_locks:
            with _SQLITE_ORDER_LOCKS_GUARD:
                lock = _SQLITE_ORDER_LOCKS.setdefault(course_id, RLock())
            lock.acquire()
            held_locks[course_id] = lock
    db.query(Course.id).filter(Course.id == course_id).with_for_update().one()


def _next_position(db: Session, model: type, course_id: UUID) -> int:
    _lock_course_order(db, course_id)
    current = (
        db.query(func.max(model.position)).filter(model.course_id == course_id).scalar()
    )
    return int(current) + 1 if current is not None else 0


def legacy_course_grading_data(
    db: Session, course_id: UUID
) -> tuple[
    list[Assignment],
    list[Enrollment],
    dict[UUID, User],
    dict[tuple[UUID, UUID], list[Submission]],
]:
    """Read the original assignment/latest-attempt gradebook projection."""

    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id == course_id,
            Assignment.status.in_(
                [AssignmentStatus.published, AssignmentStatus.closed]
            ),
        )
        .order_by(Assignment.deadline, Assignment.title)
        .all()
    )
    memberships = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
        )
        .all()
    )
    user_ids = [item.user_id for item in memberships]
    users = {
        user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()
    }
    submitter_users = {
        item.id: item.user_id
        for item in db.query(Submitter)
        .filter(
            Submitter.user_id.in_(users.keys()),
            Submitter.is_synthetic.is_(False),
        )
        .all()
    }
    assignment_ids = [item.id for item in assignments]
    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id.in_(assignment_ids))
        .order_by(
            Submission.attempt_number,
            Submission.submitted_at,
            Submission.id,
        )
        .all()
        if assignment_ids
        else []
    )
    by_student_assignment: dict[tuple[UUID, UUID], list[Submission]] = {}
    for submission in submissions:
        user_id = submitter_users.get(submission.submitter_id)
        if user_id is not None:
            by_student_assignment.setdefault(
                (user_id, submission.assignment_id), []
            ).append(submission)
    return assignments, memberships, users, by_student_assignment


def is_default_category(category: GradeCategory) -> bool:
    return (category.calculation_policy or {}).get(
        DEFAULT_CATEGORY_POLICY_KEY
    ) == DEFAULT_CATEGORY_POLICY_VALUE


def ensure_default_category(db: Session, course_id: UUID) -> GradeCategory:
    _lock_course_order(db, course_id)
    categories = (
        db.query(GradeCategory)
        .filter(GradeCategory.course_id == course_id)
        .order_by(GradeCategory.position, GradeCategory.created_at)
        .all()
    )
    default = next((item for item in categories if is_default_category(item)), None)
    if default is not None:
        return default
    default = GradeCategory(
        id=uuid4(),
        course_id=course_id,
        name="Assignments",
        description="Automatically linked assignment grades.",
        position=_next_position(db, GradeCategory, course_id),
        aggregation_strategy=GradeAggregationStrategy.sum,
        weight=None,
        calculation_policy={
            DEFAULT_CATEGORY_POLICY_KEY: DEFAULT_CATEGORY_POLICY_VALUE,
        },
    )
    db.add(default)
    db.flush()
    return default


def ensure_assignment_grade_item(db: Session, assignment: Assignment) -> GradeItem:
    _lock_course_order(db, assignment.course_id)
    default = ensure_default_category(db, assignment.course_id)
    item = (
        db.query(GradeItem)
        .filter(
            GradeItem.course_id == assignment.course_id,
            GradeItem.source_type == ASSIGNMENT_SOURCE_TYPE,
            GradeItem.source_id == assignment.id,
        )
        .one_or_none()
    )
    max_points = _decimal(assignment.max_grade["value"])
    if item is None:
        item = GradeItem(
            id=uuid4(),
            course_id=assignment.course_id,
            category_id=default.id,
            title=assignment.title,
            description=assignment.description,
            position=_next_position(db, GradeItem, assignment.course_id),
            max_points=max_points,
            source_type=ASSIGNMENT_SOURCE_TYPE,
            source_id=assignment.id,
            calculation_policy={},
            release_policy={},
        )
        db.add(item)
    else:
        item.title = assignment.title
        item.description = assignment.description
        item.max_points = max_points
        if item.category_id is None:
            item.category_id = default.id
    db.flush()
    return item


def delete_assignment_grade_item(db: Session, assignment: Assignment) -> None:
    item = (
        db.query(GradeItem)
        .filter(
            GradeItem.course_id == assignment.course_id,
            GradeItem.source_type == ASSIGNMENT_SOURCE_TYPE,
            GradeItem.source_id == assignment.id,
        )
        .one_or_none()
    )
    if item is not None:
        db.delete(item)
        db.flush()


def sync_assignment_user_grade_entry(
    db: Session,
    assignment: Assignment,
    user_id: UUID,
    actor: User,
) -> GradeEntry | None:
    """Project the learner's latest attempt into the released grade entry.

    Submission.published_score remains the compatibility source of truth for
    assignment grading during this slice. Draft scores are never read here,
    and returning or deleting an older attempt cannot replace a newer attempt's
    canonical legacy state.
    """

    item = ensure_assignment_grade_item(db, assignment)
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == assignment.course_id,
            Enrollment.user_id == user_id,
        )
        .one_or_none()
    )
    if enrollment is None:
        return None

    entry = (
        db.query(GradeEntry)
        .filter(
            GradeEntry.grade_item_id == item.id,
            GradeEntry.user_id == user_id,
        )
        .one_or_none()
    )
    submission = (
        db.query(Submission)
        .join(Submitter, Submitter.id == Submission.submitter_id)
        .filter(
            Submission.assignment_id == assignment.id,
            Submitter.user_id == user_id,
            Submitter.is_synthetic.is_(False),
        )
        .order_by(
            Submission.attempt_number.desc(),
            Submission.submitted_at.desc(),
            Submission.id.desc(),
        )
        .first()
    )
    if submission is None:
        if entry is not None:
            db.delete(entry)
            db.flush()
        return None
    if submission.status == SubmissionStatus.excused:
        status = GradeEntryStatus.excused
        points = None
    elif (
        submission.status == SubmissionStatus.returned
        and submission.published_score is not None
    ):
        status = GradeEntryStatus.graded
        points = _decimal(submission.published_score)
    else:
        if entry is not None:
            db.delete(entry)
            db.flush()
        return None

    released_at = submission.returned_at or datetime.now(timezone.utc)
    if released_at.tzinfo is None:
        released_at = released_at.replace(tzinfo=timezone.utc)
    if entry is None:
        entry = GradeEntry(
            id=uuid4(),
            course_id=assignment.course_id,
            grade_item_id=item.id,
            user_id=user_id,
            status=status,
            points_earned=points,
            release_state=GradeReleaseState.released,
            released_at=released_at,
            graded_at=released_at,
            source_type=SUBMISSION_SOURCE_TYPE,
            source_id=submission.id,
            source_version=released_at.isoformat(),
            recorded_by_user_id=actor.id,
        )
        db.add(entry)
    else:
        entry.status = status
        entry.points_earned = points
        entry.release_state = GradeReleaseState.released
        entry.released_at = released_at
        entry.graded_at = released_at
        entry.source_type = SUBMISSION_SOURCE_TYPE
        entry.source_id = submission.id
        entry.source_version = released_at.isoformat()
        entry.recorded_by_user_id = actor.id
    db.flush()
    if status == GradeEntryStatus.graded:
        assert submission.published_score is not None
        assert entry.points_earned == _decimal(submission.published_score)
    return entry


def sync_released_submission_entry(
    db: Session,
    submission: Submission,
    actor: User,
) -> GradeEntry | None:
    """Synchronize the latest attempt after a submission release mutation."""

    assignment = db.get(Assignment, submission.assignment_id)
    if assignment is None:
        raise RuntimeError("Submission assignment is missing")
    submitter = db.get(Submitter, submission.submitter_id)
    if submitter is None or submitter.user_id is None or submitter.is_synthetic:
        return None
    return sync_assignment_user_grade_entry(
        db,
        assignment,
        submitter.user_id,
        actor,
    )


def _resequence(db: Session, records: list[Any], target: Any, position: int) -> None:
    records.remove(target)
    records.insert(min(position, len(records)), target)
    temporary_start = (
        max((record.position for record in records), default=-1) + len(records) + 1
    )
    for index, record in enumerate(records):
        record.position = temporary_start + index
    db.flush()
    for index, record in enumerate(records):
        record.position = index
    db.flush()


def move_category(db: Session, category: GradeCategory, position: int) -> GradeCategory:
    _lock_course_order(db, category.course_id)
    records = (
        db.query(GradeCategory)
        .filter(GradeCategory.course_id == category.course_id)
        .order_by(GradeCategory.position, GradeCategory.created_at)
        .all()
    )
    _resequence(db, records, category, position)
    return category


def move_item(db: Session, item: GradeItem, position: int) -> GradeItem:
    _lock_course_order(db, item.course_id)
    records = (
        db.query(GradeItem)
        .filter(GradeItem.course_id == item.course_id)
        .order_by(GradeItem.position, GradeItem.created_at)
        .all()
    )
    _resequence(db, records, item, position)
    return item


def create_category(
    db: Session,
    course_id: UUID,
    *,
    name: str,
    description: str | None,
    weight: float | None,
) -> GradeCategory:
    category = GradeCategory(
        id=uuid4(),
        course_id=course_id,
        name=name.strip(),
        description=description,
        position=_next_position(db, GradeCategory, course_id),
        aggregation_strategy=GradeAggregationStrategy.sum,
        weight=_decimal(weight) if weight is not None else None,
        calculation_policy={},
    )
    db.add(category)
    db.flush()
    return category


def update_category(
    db: Session, category: GradeCategory, data: dict[str, Any]
) -> GradeCategory:
    position = data.pop("position", None)
    if "name" in data:
        category.name = data["name"].strip()
    if "description" in data:
        category.description = data["description"]
    if "weight" in data:
        category.weight = (
            _decimal(data["weight"]) if data["weight"] is not None else None
        )
    if position is not None and position != category.position:
        move_category(db, category, position)
    db.flush()
    return category


def create_manual_item(
    db: Session,
    course_id: UUID,
    *,
    category: GradeCategory | None,
    title: str,
    description: str | None,
    max_points: float,
) -> GradeItem:
    category = category or ensure_default_category(db, course_id)
    item = GradeItem(
        id=uuid4(),
        course_id=course_id,
        category_id=category.id,
        title=title.strip(),
        description=description,
        position=_next_position(db, GradeItem, course_id),
        max_points=_decimal(max_points),
        calculation_policy={},
        release_policy={},
        source_type=None,
        source_id=None,
    )
    db.add(item)
    db.flush()
    return item


def update_item(
    db: Session,
    item: GradeItem,
    data: dict[str, Any],
    *,
    category: GradeCategory | None = None,
) -> GradeItem:
    position = data.pop("position", None)
    if category is not None:
        item.category_id = category.id
    protected = {"title", "description", "max_points"}.intersection(data)
    if item.source_type is not None and protected:
        raise HTTPException(
            status_code=409,
            detail="Assignment-linked item title and points are managed by the assignment",
        )
    if "title" in data:
        item.title = data["title"].strip()
    if "description" in data:
        item.description = data["description"]
    if "max_points" in data:
        max_points = _decimal(data["max_points"])
        highest_released = (
            db.query(func.max(GradeEntry.points_earned))
            .filter(
                GradeEntry.grade_item_id == item.id,
                GradeEntry.status == GradeEntryStatus.graded,
                GradeEntry.release_state == GradeReleaseState.released,
            )
            .scalar()
        )
        if highest_released is not None and highest_released > max_points:
            raise HTTPException(
                status_code=400,
                detail="Maximum points cannot be lower than an existing released entry",
            )
        item.max_points = max_points
    if position is not None and position != item.position:
        move_item(db, item, position)
    db.flush()
    return item


def upsert_manual_entry(
    db: Session,
    item: GradeItem,
    *,
    user_id: UUID,
    status: str,
    points_earned: float | None,
    note: str | None,
    actor: User,
) -> GradeEntry:
    if item.source_type is not None:
        raise HTTPException(
            status_code=409,
            detail="Assignment-linked entries are released through submission grading",
        )
    require_active_student_enrollment(db, item.course_id, user_id)
    points = _decimal(points_earned) if points_earned is not None else None
    try:
        entry_status = GradeEntryStatus(status)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid grade entry status"
        ) from exc
    if entry_status == GradeEntryStatus.graded and points is None:
        raise HTTPException(status_code=400, detail="A graded entry requires points")
    if entry_status != GradeEntryStatus.graded and points is not None:
        raise HTTPException(
            status_code=400,
            detail=f"A {entry_status.value} entry cannot include points",
        )
    if points is not None and points > item.max_points:
        raise HTTPException(
            status_code=400,
            detail="Manual points cannot exceed the item's maximum points",
        )
    entry = (
        db.query(GradeEntry)
        .filter(
            GradeEntry.grade_item_id == item.id,
            GradeEntry.user_id == user_id,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if entry is None:
        entry = GradeEntry(
            id=uuid4(),
            course_id=item.course_id,
            grade_item_id=item.id,
            user_id=user_id,
            status=entry_status,
            points_earned=points,
            release_state=GradeReleaseState.released,
            released_at=now,
            graded_at=now,
            source_type=MANUAL_ENTRY_SOURCE_TYPE,
            source_id=item.id,
            source_version=now.isoformat(),
            recorded_by_user_id=actor.id,
            note=note,
        )
        db.add(entry)
    else:
        entry.status = entry_status
        entry.points_earned = points
        entry.release_state = GradeReleaseState.released
        entry.released_at = now
        entry.graded_at = now
        entry.source_type = MANUAL_ENTRY_SOURCE_TYPE
        entry.source_id = item.id
        entry.source_version = now.isoformat()
        entry.recorded_by_user_id = actor.id
        entry.note = note
    db.flush()
    return entry


def _released_entry(entry: GradeEntry | None) -> bool:
    return bool(entry and _enum_value(entry.release_state) == "released")


def _total_for_items(
    items: Iterable[GradeItem], entries: dict[UUID, GradeEntry]
) -> dict[str, Any]:
    earned = Decimal("0")
    possible = Decimal("0")
    graded_count = 0
    excused_count = 0
    missing_count = 0
    for item in items:
        entry = entries.get(item.id)
        if not _released_entry(entry):
            missing_count += 1
            continue
        status = _enum_value(entry.status)
        if status == "excused":
            excused_count += 1
        elif status == "graded" and entry.points_earned is not None:
            earned += entry.points_earned
            possible += item.max_points
            graded_count += 1
        else:
            missing_count += 1
    percentage = (earned / possible * Decimal("100")) if possible > 0 else None
    reasons = (
        [
            f"{missing_count} relevant grade entr{'y is' if missing_count == 1 else 'ies are'} not released"
        ]
        if missing_count
        else []
    )
    return {
        "points_earned": _float(earned),
        "points_possible": _float(possible),
        "percentage": _float(percentage),
        "provisional": bool(missing_count),
        "graded_item_count": graded_count,
        "excused_item_count": excused_count,
        "missing_entry_count": missing_count,
        "reasons": reasons,
    }


def _course_total(
    categories: list[GradeCategory], category_totals: list[dict[str, Any]]
) -> dict[str, Any]:
    earned = sum(
        (_decimal(item["points_earned"]) for item in category_totals), Decimal("0")
    )
    possible = sum(
        (_decimal(item["points_possible"]) for item in category_totals), Decimal("0")
    )
    graded = sum(item["graded_item_count"] for item in category_totals)
    excused = sum(item["excused_item_count"] for item in category_totals)
    missing = sum(item["missing_entry_count"] for item in category_totals)
    explicit_weights = [
        category.weight for category in categories if category.weight is not None
    ]
    reasons = [reason for item in category_totals for reason in item["reasons"]]

    if explicit_weights:
        configured_weight_total = sum(explicit_weights, Decimal("0"))
        weighted = Decimal("0")
        included_weight = Decimal("0")
        category_by_id = {category.id: category for category in categories}
        for item in category_totals:
            category = category_by_id[item["category_id"]]
            if (
                category.weight is not None
                and category.weight > 0
                and item["percentage"] is None
            ):
                reasons.append(
                    f"category {category.name} has positive weight but no calculable released points"
                )
            if (
                category.weight is None
                or category.weight <= 0
                or item["percentage"] is None
            ):
                continue
            weighted += _decimal(item["percentage"]) * category.weight
            included_weight += category.weight
        percentage = weighted / included_weight if included_weight > 0 else None
        missing_weights = sum(category.weight is None for category in categories)
        if missing_weights:
            reasons.append(
                f"{missing_weights} categor{'y has' if missing_weights == 1 else 'ies have'} no configured weight"
            )
        if configured_weight_total != Decimal("100"):
            reasons.append(
                f"configured category weights total {_float(configured_weight_total):g}, not 100"
            )
        calculation = "category_weighted"
        configured_total = _float(configured_weight_total)
    else:
        percentage = earned / possible * Decimal("100") if possible > 0 else None
        calculation = "points"
        configured_total = None

    return {
        "points_earned": _float(earned),
        "points_possible": _float(possible),
        "percentage": _float(percentage),
        "provisional": bool(reasons),
        "graded_item_count": graded,
        "excused_item_count": excused,
        "missing_entry_count": missing,
        "reasons": list(dict.fromkeys(reasons)),
        "calculation": calculation,
        "configured_weight_total": configured_total,
    }


def gradebook_projection(
    db: Session,
    course_id: UUID,
    user_ids: list[UUID],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[UUID, dict[str, Any]]]:
    categories = (
        db.query(GradeCategory)
        .filter(GradeCategory.course_id == course_id)
        .order_by(GradeCategory.position, GradeCategory.created_at)
        .all()
    )
    assignments = {
        assignment.id: assignment
        for assignment in db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .all()
    }
    items = (
        db.query(GradeItem)
        .filter(GradeItem.course_id == course_id)
        .order_by(GradeItem.position, GradeItem.created_at)
        .all()
    )
    visible_items: list[GradeItem] = []
    for item in items:
        if item.source_type != ASSIGNMENT_SOURCE_TYPE:
            visible_items.append(item)
            continue
        assignment = assignments.get(item.source_id)
        if assignment and assignment.status in {
            AssignmentStatus.published,
            AssignmentStatus.closed,
        }:
            visible_items.append(item)

    entries = (
        db.query(GradeEntry)
        .filter(
            GradeEntry.course_id == course_id,
            GradeEntry.user_id.in_(user_ids),
            GradeEntry.grade_item_id.in_([item.id for item in visible_items]),
        )
        .all()
        if user_ids and visible_items
        else []
    )
    entries_by_user: dict[UUID, dict[UUID, GradeEntry]] = {}
    for entry in entries:
        entries_by_user.setdefault(entry.user_id, {})[entry.grade_item_id] = entry

    category_payloads = [
        {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "position": category.position,
            "weight": _float(category.weight),
            "aggregation_strategy": _enum_value(category.aggregation_strategy),
            "is_default": is_default_category(category),
        }
        for category in categories
    ]
    item_payloads = [
        {
            "id": item.id,
            "category_id": item.category_id,
            "title": item.title,
            "description": item.description,
            "position": item.position,
            "max_points": _float(item.max_points),
            "source_type": item.source_type,
            "source_id": item.source_id,
            "is_manual": item.source_type is None,
        }
        for item in visible_items
    ]
    category_items = {
        category.id: [item for item in visible_items if item.category_id == category.id]
        for category in categories
    }
    row_payloads: dict[UUID, dict[str, Any]] = {}
    for user_id in user_ids:
        user_entries = entries_by_user.get(user_id, {})
        cells: list[dict[str, Any]] = []
        for item in visible_items:
            entry = user_entries.get(item.id)
            if entry is None:
                cells.append(
                    {
                        "grade_item_id": item.id,
                        "status": "absent",
                        "release_state": "absent",
                    }
                )
                continue
            released = _released_entry(entry)
            cells.append(
                {
                    "grade_item_id": item.id,
                    "status": _enum_value(entry.status),
                    "release_state": _enum_value(entry.release_state),
                    "points_earned": _float(entry.points_earned) if released else None,
                    "source_type": entry.source_type,
                    "source_id": entry.source_id,
                    "released_at": entry.released_at,
                    "note": entry.note,
                }
            )
        totals: list[dict[str, Any]] = []
        for category in categories:
            total = _total_for_items(category_items[category.id], user_entries)
            total.update(
                {
                    "category_id": category.id,
                    "weight": _float(category.weight),
                }
            )
            totals.append(total)
        row_payloads[user_id] = {
            "item_cells": cells,
            "category_totals": totals,
            "course_total": _course_total(categories, totals),
        }
    return category_payloads, item_payloads, row_payloads


def require_active_student_enrollment(
    db: Session, course_id: UUID, user_id: UUID
) -> Enrollment:
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
        )
        .one_or_none()
    )
    if enrollment is None:
        raise HTTPException(
            status_code=400,
            detail="User is not an active student in this course",
        )
    return enrollment


__all__ = [
    "ASSIGNMENT_SOURCE_TYPE",
    "DEFAULT_CATEGORY_POLICY_KEY",
    "DEFAULT_CATEGORY_POLICY_VALUE",
    "MANUAL_ENTRY_SOURCE_TYPE",
    "SUBMISSION_SOURCE_TYPE",
    "delete_assignment_grade_item",
    "ensure_assignment_grade_item",
    "ensure_default_category",
    "gradebook_projection",
    "is_default_category",
    "legacy_course_grading_data",
    "move_category",
    "move_item",
    "create_category",
    "create_manual_item",
    "require_active_student_enrollment",
    "sync_assignment_user_grade_entry",
    "sync_released_submission_entry",
    "update_category",
    "update_item",
    "upsert_manual_entry",
]
