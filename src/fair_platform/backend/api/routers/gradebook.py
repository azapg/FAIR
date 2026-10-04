from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.gradebook import (
    CourseGradebook,
    GradebookAssignment,
    GradebookCategoryCreate,
    GradebookCategoryRead,
    GradebookCategoryUpdate,
    GradebookCell,
    GradebookEntryCell,
    GradebookEntryUpsert,
    GradebookItemCreate,
    GradebookItemRead,
    GradebookItemUpdate,
    GradebookRow,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.lms_gradebook import (
    GradeCategory,
    GradeEntry,
    GradeItem,
)
from fair_platform.backend.data.models.submission import SubmissionStatus
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_access import can_manage_course
from fair_platform.backend.services.gradebook import (
    create_category,
    create_manual_item,
    ensure_default_category,
    gradebook_projection,
    is_default_category,
    legacy_course_grading_data,
    update_category,
    update_item,
    upsert_manual_entry,
)


router = APIRouter()


def _managed_course(db: Session, course_id: UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_manage_course(db, course, user):
        raise HTTPException(
            status_code=403,
            detail="Only course staff can view or manage the gradebook",
        )
    return course


def _mutable_course(db: Session, course_id: UUID, user: User) -> Course:
    course = _managed_course(db, course_id, user)
    if course.is_archived:
        raise HTTPException(status_code=400, detail="Archived courses are read-only")
    return course


def _category(db: Session, course_id: UUID, category_id: UUID) -> GradeCategory:
    category = db.get(GradeCategory, category_id)
    if category is None or category.course_id != course_id:
        raise HTTPException(status_code=404, detail="Grade category not found")
    return category


def _item(db: Session, course_id: UUID, item_id: UUID) -> GradeItem:
    item = db.get(GradeItem, item_id)
    if item is None or item.course_id != course_id:
        raise HTTPException(status_code=404, detail="Grade item not found")
    return item


def _category_read(category: GradeCategory) -> GradebookCategoryRead:
    return GradebookCategoryRead(
        id=category.id,
        name=category.name,
        description=category.description,
        position=category.position,
        weight=float(category.weight) if category.weight is not None else None,
        aggregation_strategy=(
            category.aggregation_strategy.value
            if hasattr(category.aggregation_strategy, "value")
            else str(category.aggregation_strategy)
        ),
        is_default=is_default_category(category),
    )


def _item_read(item: GradeItem) -> GradebookItemRead:
    return GradebookItemRead(
        id=item.id,
        category_id=item.category_id,
        title=item.title,
        description=item.description,
        position=item.position,
        max_points=float(item.max_points),
        source_type=item.source_type,
        source_id=item.source_id,
        is_manual=item.source_type is None,
    )


def _entry_read(entry: GradeEntry) -> GradebookEntryCell:
    status_value = (
        entry.status.value if hasattr(entry.status, "value") else str(entry.status)
    )
    release_value = (
        entry.release_state.value
        if hasattr(entry.release_state, "value")
        else str(entry.release_state)
    )
    return GradebookEntryCell(
        grade_item_id=entry.grade_item_id,
        status=status_value,
        release_state=release_value,
        points_earned=(
            float(entry.points_earned) if entry.points_earned is not None else None
        ),
        source_type=entry.source_type,
        source_id=entry.source_id,
        released_at=entry.released_at,
        note=entry.note,
    )


@router.get("/courses/{course_id}/gradebook", response_model=CourseGradebook)
def get_course_gradebook(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseGradebook:
    _managed_course(db, course_id, current_user)
    assignments, memberships, users, attempts = legacy_course_grading_data(
        db, course_id
    )
    user_ids = [membership.user_id for membership in memberships]
    categories, items, projections = gradebook_projection(db, course_id, user_ids)
    rows: list[GradebookRow] = []
    for membership in memberships:
        user = users.get(membership.user_id)
        if user is None:
            continue
        legacy_cells: list[GradebookCell] = []
        for assignment in assignments:
            student_attempts = attempts.get((user.id, assignment.id), [])
            latest = student_attempts[-1] if student_attempts else None
            if latest is None:
                cell_state = "missing"
            elif latest.status == SubmissionStatus.returned:
                cell_state = "returned"
            elif latest.status == SubmissionStatus.excused:
                cell_state = "excused"
            else:
                cell_state = "submitted"
            legacy_cells.append(
                GradebookCell(
                    assignment_id=assignment.id,
                    state=cell_state,
                    submission_id=latest.id if latest else None,
                    score=(
                        latest.published_score
                        if latest and cell_state == "returned"
                        else None
                    ),
                    submitted_at=latest.submitted_at if latest else None,
                    is_late=latest.is_late if latest else False,
                    attempt_count=len(student_attempts),
                )
            )
        projection = projections.get(user.id, {})
        rows.append(
            GradebookRow(
                user_id=user.id,
                name=user.name,
                email=str(user.email),
                cells=legacy_cells,
                **projection,
            )
        )
    return CourseGradebook(
        course_id=course_id,
        assignments=[GradebookAssignment.model_validate(item) for item in assignments],
        rows=rows,
        categories=categories,
        items=items,
    )


@router.post(
    "/courses/{course_id}/gradebook/categories",
    response_model=GradebookCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_gradebook_category(
    course_id: UUID,
    payload: GradebookCategoryCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> GradebookCategoryRead:
    _mutable_course(db, course_id, current_user)
    category = create_category(
        db,
        course_id,
        name=payload.name,
        description=payload.description,
        weight=payload.weight,
    )
    db.commit()
    db.refresh(category)
    return _category_read(category)


@router.patch(
    "/courses/{course_id}/gradebook/categories/{category_id}",
    response_model=GradebookCategoryRead,
)
def update_gradebook_category(
    course_id: UUID,
    category_id: UUID,
    payload: GradebookCategoryUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> GradebookCategoryRead:
    _mutable_course(db, course_id, current_user)
    category = _category(db, course_id, category_id)
    category = update_category(db, category, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(category)
    return _category_read(category)


@router.post(
    "/courses/{course_id}/gradebook/items",
    response_model=GradebookItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_gradebook_item(
    course_id: UUID,
    payload: GradebookItemCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> GradebookItemRead:
    _mutable_course(db, course_id, current_user)
    category = (
        _category(db, course_id, payload.category_id)
        if payload.category_id is not None
        else ensure_default_category(db, course_id)
    )
    item = create_manual_item(
        db,
        course_id,
        category=category,
        title=payload.title,
        description=payload.description,
        max_points=payload.max_points,
    )
    db.commit()
    db.refresh(item)
    return _item_read(item)


@router.patch(
    "/courses/{course_id}/gradebook/items/{item_id}",
    response_model=GradebookItemRead,
)
def update_gradebook_item(
    course_id: UUID,
    item_id: UUID,
    payload: GradebookItemUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> GradebookItemRead:
    _mutable_course(db, course_id, current_user)
    item = _item(db, course_id, item_id)
    data = payload.model_dump(exclude_unset=True)
    category = None
    if "category_id" in data:
        category_id = data.pop("category_id")
        category = (
            _category(db, course_id, category_id)
            if category_id is not None
            else ensure_default_category(db, course_id)
        )
    item = update_item(db, item, data, category=category)
    db.commit()
    db.refresh(item)
    return _item_read(item)


@router.put(
    "/courses/{course_id}/gradebook/items/{item_id}/entries/{user_id}",
    response_model=GradebookEntryCell,
)
def upsert_gradebook_entry(
    course_id: UUID,
    item_id: UUID,
    user_id: UUID,
    payload: GradebookEntryUpsert,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> GradebookEntryCell:
    _mutable_course(db, course_id, current_user)
    item = _item(db, course_id, item_id)
    entry = upsert_manual_entry(
        db,
        item,
        user_id=user_id,
        status=payload.status,
        points_earned=payload.points_earned,
        note=payload.note,
        actor=current_user,
    )
    db.commit()
    db.refresh(entry)
    return _entry_read(entry)


__all__ = ["router"]
