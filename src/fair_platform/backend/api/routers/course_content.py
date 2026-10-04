from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.course_content import (
    CourseContentRead,
    CourseItemCreate,
    CourseItemRead,
    CourseItemUpdate,
    CourseSectionCreate,
    CourseSectionRead,
    CourseSectionUpdate,
    ExactOrderUpdate,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.lms_content import CourseItem, CourseSection
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_access import can_manage_course, can_view_course
from fair_platform.backend.services.course_content_service import (
    CourseContentConflict,
    CourseContentError,
    CourseContentNotFound,
    CourseContentService,
)


router = APIRouter()


def _course(db: Session, course_id: UUID, user: User, *, manage: bool) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    allowed = (
        can_manage_course(db, course, user)
        if manage
        else can_view_course(db, course, user)
    )
    if not allowed:
        detail = (
            "Only course staff can manage course content"
            if manage
            else "Only active course members can view course content"
        )
        raise HTTPException(status_code=403, detail=detail)
    if manage and course.is_archived:
        raise HTTPException(status_code=409, detail="Archived courses are read-only")
    return course


def _item_read(item: CourseItem) -> CourseItemRead:
    return CourseItemRead.model_validate(item)


def _section_read(
    section: CourseSection, items: list[CourseItem] | None = None
) -> CourseSectionRead:
    return CourseSectionRead(
        id=section.id,
        course_id=section.course_id,
        title=section.title,
        summary=section.summary,
        position=section.position,
        visibility=section.visibility,
        created_at=section.created_at,
        updated_at=section.updated_at,
        items=[_item_read(item) for item in (items if items is not None else section.items)],
    )


def _raise_service_error(db: Session, error: Exception) -> None:
    db.rollback()
    if isinstance(error, CourseContentNotFound):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, CourseContentConflict):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, IntegrityError):
        raise HTTPException(
            status_code=409, detail="Course content changed; refresh and try again"
        ) from error
    if isinstance(error, CourseContentError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    raise error


@router.get("/courses/{course_id}/content", response_model=CourseContentRead)
def get_course_content(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseContentRead:
    course = _course(db, course_id, current_user, manage=False)
    can_manage = can_manage_course(db, course, current_user)
    sections = CourseContentService(db).list_sections(
        course_id, staff_view=can_manage
    )
    return CourseContentRead(
        course_id=course_id,
        can_manage=can_manage,
        sections=[_section_read(section, items) for section, items in sections],
    )


@router.post(
    "/courses/{course_id}/sections",
    response_model=CourseSectionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course_section(
    course_id: UUID,
    payload: CourseSectionCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseSectionRead:
    _course(db, course_id, current_user, manage=True)
    try:
        section = CourseContentService(db).create_section(
            course_id,
            title=payload.title,
            summary=payload.summary,
            visibility=payload.visibility,
        )
        db.commit()
        return _section_read(section, [])
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.patch(
    "/courses/{course_id}/sections/{section_id}",
    response_model=CourseSectionRead,
)
def update_course_section(
    course_id: UUID,
    section_id: UUID,
    payload: CourseSectionUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseSectionRead:
    _course(db, course_id, current_user, manage=True)
    try:
        section = CourseContentService(db).update_section(
            course_id,
            section_id,
            payload.model_dump(exclude_unset=True),
        )
        db.commit()
        db.refresh(section)
        return _section_read(section)
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.delete(
    "/courses/{course_id}/sections/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_course_section(
    course_id: UUID,
    section_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> None:
    _course(db, course_id, current_user, manage=True)
    try:
        CourseContentService(db).delete_section(course_id, section_id)
        db.commit()
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.put(
    "/courses/{course_id}/sections/order",
    response_model=list[CourseSectionRead],
)
def reorder_course_sections(
    course_id: UUID,
    payload: ExactOrderUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[CourseSectionRead]:
    _course(db, course_id, current_user, manage=True)
    try:
        sections = CourseContentService(db).reorder_sections(
            course_id, payload.ordered_ids
        )
        db.commit()
        return [_section_read(section) for section in sections]
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/sections/{section_id}/items",
    response_model=CourseItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_course_item(
    course_id: UUID,
    section_id: UUID,
    payload: CourseItemCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseItemRead:
    _course(db, course_id, current_user, manage=True)
    try:
        item = CourseContentService(db).create_item(
            course_id,
            section_id,
            title=payload.title,
            kind=payload.kind,
            visibility=payload.visibility,
            resource_id=payload.resource_id,
            payload=payload.payload,
        )
        db.commit()
        return _item_read(item)
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.patch(
    "/courses/{course_id}/items/{item_id}", response_model=CourseItemRead
)
def update_course_item(
    course_id: UUID,
    item_id: UUID,
    payload: CourseItemUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> CourseItemRead:
    _course(db, course_id, current_user, manage=True)
    try:
        item = CourseContentService(db).update_item(
            course_id,
            item_id,
            payload.model_dump(exclude_unset=True),
        )
        db.commit()
        return _item_read(item)
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.delete(
    "/courses/{course_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_course_item(
    course_id: UUID,
    item_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> None:
    _course(db, course_id, current_user, manage=True)
    try:
        CourseContentService(db).delete_item(course_id, item_id)
        db.commit()
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.put(
    "/courses/{course_id}/sections/{section_id}/items/order",
    response_model=list[CourseItemRead],
)
def reorder_course_items(
    course_id: UUID,
    section_id: UUID,
    payload: ExactOrderUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[CourseItemRead]:
    _course(db, course_id, current_user, manage=True)
    try:
        items = CourseContentService(db).reorder_items(
            course_id, section_id, payload.ordered_ids
        )
        db.commit()
        return [_item_read(item) for item in items]
    except (CourseContentError, IntegrityError) as error:
        _raise_service_error(db, error)


__all__ = ["router"]
