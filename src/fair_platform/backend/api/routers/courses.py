from uuid import UUID, uuid4
from typing import Optional, Union
import secrets
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload, selectinload

from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.api.schema.course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    CourseDetailRead,
    CourseSettingsUpdate,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.core.security.dependencies import require_capability

router = APIRouter()

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = int(os.getenv("FAIR_ENROLLMENT_CODE_LENGTH", "4"))
MAX_CODE_ATTEMPTS = 10


def _generate_enrollment_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _generate_unique_enrollment_code(db: Session) -> str:
    for _ in range(MAX_CODE_ATTEMPTS):
        code = _generate_enrollment_code()
        exists = (
            db.query(Course)
            .filter(Course.enrollment_code == code)
            .first()
        )
        if not exists:
            return code
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate enrollment code, please try again",
    )


def _course_to_response(course: Course, include_code: bool) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.name if course.instructor else "",
        "assignments_count": len(course.assignments or []),
        "enrollment_code": course.enrollment_code if include_code else None,
        "is_enrollment_enabled": course.is_enrollment_enabled if include_code else None,
    }


@router.post(
    "/",
    response_model=CourseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability("create_course"))],
)
def create_course(
    course: CourseCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    instructor = db.get(User, course.instructor_id)
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found"
        )

    if not has_capability(instructor, "create_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user cannot own courses in the current deployment mode",
        )

    if not has_capability(current_user, "create_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create courses",
        )

    if (
        current_user.id != course.instructor_id
        and not has_capability(current_user, "update_any_course")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create a course for this instructor",
        )

    enrollment_code = _generate_unique_enrollment_code(db)
    db_course = Course(
        id=uuid4(),
        name=course.name,
        description=course.description,
        instructor_id=course.instructor_id,
        enrollment_code=enrollment_code,
        is_enrollment_enabled=True,
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return _course_to_response(db_course, include_code=True)


@router.get("/", response_model=list[CourseRead])
def list_courses(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
    instructor_id: Optional[UUID] = None,
):
    is_admin = has_capability(current_user, "update_any_course")
    if is_admin:
        query = db.query(Course).options(
            joinedload(Course.instructor),
            selectinload(Course.assignments),
        )

        if instructor_id is not None:
            query = query.filter(Course.instructor_id == instructor_id)
        courses = query.all()
        return [
            _course_to_response(c, include_code=True)
            for c in courses
        ]

    # Students see only courses they are enrolled in
    if not has_capability(current_user, "create_course"):
        courses = (
            db.query(Course)
            .options(joinedload(Course.instructor), selectinload(Course.assignments))
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == current_user.id)
            .all()
        )
        return [
            _course_to_response(c, include_code=False)
            for c in courses
        ]

    courses = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .filter(
            or_(
                Course.instructor_id == current_user.id,
                Enrollment.user_id == current_user.id,
            )
        )
        .distinct()
        .all()
    )
    return [
        _course_to_response(c, include_code=(c.instructor_id == current_user.id))
        for c in courses
    ]


@router.get("/{course_id}", response_model=Union[CourseRead, CourseDetailRead])
def get_course(
    course_id: UUID,
    detailed: bool = False,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .options(
            joinedload(Course.instructor),
            selectinload(Course.assignments),
            selectinload(Course.workflows),
        )
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    is_admin = has_capability(current_user, "update_any_course")
    owns_course = course.instructor_id == current_user.id
    can_manage_course = is_admin or owns_course

    if not can_manage_course:
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course_id,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only enrolled users, the course owner, or admin can view this course",
            )

    include_code = can_manage_course
    if detailed and can_manage_course:
        from fair_platform.backend.api.routers.workflows import _db_workflow_to_read

        return {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "instructor": course.instructor,
            "assignments": course.assignments or [],
            "workflows": [_db_workflow_to_read(workflow, db) for workflow in (course.workflows or [])],
            "enrollment_code": course.enrollment_code if include_code else None,
            "is_enrollment_enabled": course.is_enrollment_enabled if include_code else None,
        }

    if detailed and not can_manage_course:
        # Limited view for enrolled/non-owner users.
        return _course_to_response(course, include_code=False)

    return _course_to_response(course, include_code=include_code)


@router.put("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not has_capability_and_owner(current_user, "update_own_course", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update this course",
        )

    if payload.instructor_id is not None:
        instructor = db.get(User, payload.instructor_id)
        if not instructor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found"
            )

        if (
            not has_capability(instructor, "create_course")
            and instructor.id != course.instructor_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user cannot be assigned as course owner",
            )

        course.instructor_id = payload.instructor_id
        course.instructor = instructor

    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description

    db.add(course)
    db.commit()
    db.refresh(course)
    include_code = has_capability(current_user, "update_any_course") or course.instructor_id == current_user.id
    return _course_to_response(course, include_code=include_code)


@router.post("/{course_id}/reset-code", response_model=CourseRead)
def reset_enrollment_code(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not has_capability_and_owner(current_user, "manage_course_settings_own", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can reset this code",
        )

    course.enrollment_code = _generate_unique_enrollment_code(db)
    db.add(course)
    db.commit()
    db.refresh(course)
    include_code = has_capability(current_user, "update_any_course") or course.instructor_id == current_user.id
    return _course_to_response(course, include_code=include_code)


@router.patch("/{course_id}/settings", response_model=CourseRead)
def update_course_settings(
    course_id: UUID,
    payload: CourseSettingsUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not has_capability_and_owner(current_user, "manage_course_settings_own", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update course settings",
        )

    if payload.is_enrollment_enabled is not None:
        if payload.is_enrollment_enabled and not course.enrollment_code:
            course.enrollment_code = _generate_unique_enrollment_code(db)
        course.is_enrollment_enabled = payload.is_enrollment_enabled

    db.add(course)
    db.commit()
    db.refresh(course)
    include_code = has_capability(current_user, "update_any_course") or course.instructor_id == current_user.id
    return _course_to_response(course, include_code=include_code)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not has_capability_and_owner(current_user, "delete_own_course", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this course",
        )

    db.delete(course)
    db.commit()
    return None


__all__ = ["router"]
