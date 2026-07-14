from uuid import UUID, uuid4
from typing import Optional, Union
import secrets
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload, selectinload

from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.api.schema.course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    CourseDetailRead,
    CourseSettingsUpdate,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.core.security.dependencies import require_capability
from fair_platform.backend.services.course_access import (
    can_manage_course,
    can_own_course,
    can_view_course,
    course_role,
)

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


def _course_to_response(
    course: Course,
    include_code: bool,
    membership_role: CourseMembershipRole | None = None,
) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.name if course.instructor else "",
        "assignments_count": len(course.assignments or []),
        "enrollment_code": course.enrollment_code if include_code else None,
        "is_enrollment_enabled": course.is_enrollment_enabled if include_code else None,
        "section": course.section,
        "term": course.term,
        "is_archived": course.is_archived,
        "created_at": course.created_at,
        "updated_at": course.updated_at,
        "membership_role": membership_role,
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
        section=course.section,
        term=course.term,
    )
    db.add(db_course)
    db.add(
        Enrollment(
            id=uuid4(),
            user_id=course.instructor_id,
            course_id=db_course.id,
            role=CourseMembershipRole.owner,
            status=EnrollmentStatus.active,
        )
    )
    db.commit()
    db.refresh(db_course)
    return _course_to_response(db_course, include_code=True)


@router.get("/", response_model=list[CourseRead])
def list_courses(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
    instructor_id: Optional[UUID] = None,
    include_archived: bool = Query(False),
):
    is_admin = has_capability(current_user, "update_any_course")
    if is_admin:
        query = db.query(Course).options(
            joinedload(Course.instructor),
            selectinload(Course.assignments),
        )

        if instructor_id is not None:
            query = query.filter(Course.instructor_id == instructor_id)
        if not include_archived:
            query = query.filter(Course.is_archived.is_(False))
        courses = query.all()
        return [
            _course_to_response(c, include_code=True, membership_role=course_role(db, c, current_user))
            for c in courses
        ]

    # Students see only courses they are enrolled in
    if not has_capability(current_user, "create_course"):
        courses = (
            db.query(Course)
            .options(joinedload(Course.instructor), selectinload(Course.assignments))
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(
                Enrollment.user_id == current_user.id,
                Enrollment.status == EnrollmentStatus.active,
            )
            .all()
        )
        if not include_archived:
            courses = [course for course in courses if not course.is_archived]
        return [
            _course_to_response(c, include_code=False, membership_role=course_role(db, c, current_user))
            for c in courses
        ]

    courses = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .outerjoin(
            Enrollment,
            and_(
                Enrollment.course_id == Course.id,
                Enrollment.status == EnrollmentStatus.active,
            ),
        )
        .filter(
            or_(
                Course.instructor_id == current_user.id,
                Enrollment.user_id == current_user.id,
            )
        )
        .distinct()
        .all()
    )
    if not include_archived:
        courses = [course for course in courses if not course.is_archived]
    return [
        _course_to_response(
            c,
            include_code=can_manage_course(db, c, current_user),
            membership_role=course_role(db, c, current_user),
        )
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

    manages_course = can_manage_course(db, course, current_user)
    if not can_view_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active course members or admin can view this course",
        )

    include_code = manages_course
    if detailed and manages_course:
        from fair_platform.backend.api.routers.workflows import _db_workflow_to_read

        return {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "instructor": course.instructor,
            "assignments": course.assignments or [],
            "workflows": [_db_workflow_to_read(workflow) for workflow in (course.workflows or [])],
            "enrollment_code": course.enrollment_code if include_code else None,
            "is_enrollment_enabled": course.is_enrollment_enabled if include_code else None,
            "section": course.section,
            "term": course.term,
            "is_archived": course.is_archived,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "membership_role": course_role(db, course, current_user),
        }

    if detailed and not manages_course:
        # Limited view for enrolled/non-owner users.
        return _course_to_response(
            course,
            include_code=False,
            membership_role=course_role(db, course, current_user),
        )

    return _course_to_response(
        course,
        include_code=include_code,
        membership_role=course_role(db, course, current_user),
    )


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

    if not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update this course",
        )

    if payload.instructor_id is not None:
        if not can_own_course(db, course, current_user):
            raise HTTPException(status_code=403, detail="Only the course owner or admin can transfer ownership")
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

        previous_owner = (
            db.query(Enrollment)
            .filter(Enrollment.course_id == course.id, Enrollment.user_id == course.instructor_id)
            .first()
        )
        if previous_owner is None:
            previous_owner = Enrollment(
                id=uuid4(), user_id=course.instructor_id, course_id=course.id
            )
            db.add(previous_owner)
        previous_owner.role = CourseMembershipRole.assistant
        previous_owner.status = EnrollmentStatus.active
        next_owner = (
            db.query(Enrollment)
            .filter(Enrollment.course_id == course.id, Enrollment.user_id == payload.instructor_id)
            .first()
        )
        if next_owner is None:
            next_owner = Enrollment(
                id=uuid4(), user_id=payload.instructor_id, course_id=course.id
            )
            db.add(next_owner)
        next_owner.role = CourseMembershipRole.owner
        next_owner.status = EnrollmentStatus.active
        course.instructor_id = payload.instructor_id
        course.instructor = instructor

    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description
    if payload.section is not None:
        course.section = payload.section
    if payload.term is not None:
        course.term = payload.term

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

    if not can_manage_course(db, course, current_user):
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

    if not can_manage_course(db, course, current_user):
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

    if not can_own_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course owner or admin can archive this course",
        )

    course.is_archived = True
    course.is_enrollment_enabled = False
    db.commit()
    return None


@router.post("/{course_id}/archive", response_model=CourseRead)
def archive_course(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_own_course(db, course, current_user):
        raise HTTPException(status_code=403, detail="Only the course owner or admin can archive this course")
    course.is_archived = True
    course.is_enrollment_enabled = False
    db.commit()
    db.refresh(course)
    return _course_to_response(course, include_code=True)


@router.post("/{course_id}/reopen", response_model=CourseRead)
def reopen_course(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_own_course(db, course, current_user):
        raise HTTPException(status_code=403, detail="Only the course owner or admin can reopen this course")
    course.is_archived = False
    db.commit()
    db.refresh(course)
    return _course_to_response(course, include_code=True)


__all__ = ["router"]
