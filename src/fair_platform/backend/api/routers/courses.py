from uuid import UUID, uuid4
from typing import Optional, Union
import secrets
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload, selectinload

from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User, UserRole
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
        "is_enrollment_enabled": course.is_enrollment_enabled,
    }


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
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

    if instructor.role == UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot create courses",
        )

    if current_user.role != UserRole.admin and current_user.id != course.instructor_id:
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
    if current_user.role == UserRole.admin:
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
    if current_user.role == UserRole.student:
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
        # Instructors (non-admin, non-student) see only their own courses.
        # maybe in the future we should just send all courses a user is enrolled or is instructing,
        # without caring about the role.
        .filter(Course.instructor_id == current_user.id)
        .all()
    )
    return [
        _course_to_response(c, include_code=True)
        for c in courses
    ]


@router.get("/{course_id}", response_model=Union[CourseRead, CourseDetailRead])
def get_course(
    course_id: UUID,
    detailed: bool = False,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    # Students can access course details only if enrolled
    if current_user.role == UserRole.student:
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
                detail="Students can only view courses they are enrolled in",
            )

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

    # Authorization: admin, course instructor, or enrolled student (checked above)
    if (
        current_user.role != UserRole.admin
        and current_user.role != UserRole.student
        and course.instructor_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can view this course",
        )

    include_code = current_user.role == UserRole.admin or course.instructor_id == current_user.id
    if detailed:
        return {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "instructor": course.instructor,
            "assignments": course.assignments or [],
            "workflows": course.workflows or [],
            "enrollment_code": course.enrollment_code if include_code else None,
            "is_enrollment_enabled": course.is_enrollment_enabled,
        }

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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
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

        if instructor.role == UserRole.student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot be assigned as instructors",
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
    include_code = current_user.role == UserRole.admin or course.instructor_id == current_user.id
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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can reset this code",
        )

    course.enrollment_code = _generate_unique_enrollment_code(db)
    db.add(course)
    db.commit()
    db.refresh(course)
    include_code = current_user.role == UserRole.admin or course.instructor_id == current_user.id
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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
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
    include_code = current_user.role == UserRole.admin or course.instructor_id == current_user.id
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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this course",
        )

    db.delete(course)
    db.commit()
    return None


__all__ = ["router"]
